import json
import math

import pulp


class GameDatabase:
    def __init__(self, games):
        self.games = games
        self.default = {
            'min_players': 3,
            'max_players': 4,
            'min_playtime': 240,
            'max_playtime': 240,
            'popularity': {
                3: 0.9,
                4: 0.9,
            }
        }

        self._preprocess_game_popularities()

    @classmethod
    def from_file(cls, path):
        with open(path) as f:
            return cls({g['name']: g for g in json.load(f)})

    def min_players(self, game):
        return self._game(game)['min_players']

    def max_players(self, game, session=None):
        g = self._game(game)

        if (
                session is None or
                g['min_players'] == g['max_players'] or
                g['min_playtime'] == g['max_playtime']
        ):
            return g['max_players']

        # playtime = a + b * number_of_players_beyond_minimum
        #
        # so:
        #
        # (playtime - a) / b = number_of_players_beyond_minimum
        a = g['min_playtime']
        b = (
            (g['max_playtime'] - g['min_playtime']) /
            (g['max_players'] - g['min_players'])
        )

        return min(
            g['max_players'],
            g['min_players'] + math.floor((session['length'] - a) / b),
        )

    def min_playtime(self, game):
        return self._game(game)['min_playtime']

    def max_playtime(self, game):
        g = self._game(game)

        return max(g['max_playtime'], g['min_playtime'])

    def popularity(self, game, n):
        try:
            return self._game[game][n]
        except KeyError:
            return 1.0

    def _game(self, game):
        if game in self.games:
            return self.games[game]
        else:
            return self.default

    def _preprocess_game_popularities(self):
        for g in self.games:
            game = self.games[g]

            popularity = {}

            for i in range(game['min_players'], game['max_players'] + 1):
                if 'popularity' in game and str(i) in game['popularity']:
                    value = game['popularity'][str(i)]
                else:
                    value = 0.9

                # Smooth popularity such that games with lots of popularity
                # ratings don't effect the objective function
                popularity[i] = min(value, 0.9)

            game['popularity'] = popularity


class Schedule:
    def __init__(self, games_db, players, sessions, shared_games=[], table_limit=10):
        self.games_db = games_db
        self.players = players
        self.sessions = sessions
        self.table_limit = table_limit
        self.all_games = shared_games.copy()

        for p in self.players:
            self.all_games.extend(p['owns'])

        self.session_ids = list(range(len(self.sessions)))
        self.session_players = self._make_session_players()
        self.session_games = self._make_session_games()

        self.p = pulp.LpProblem('Schedule', pulp.LpMaximize)

        # Problem Variables.
        self.choices = self._make_choice_variables()
        self.games_played = self._make_games_played_variables()

        # Objective Function.
        self._add_objective_function()

        # Constraints.
        self._add_logical_play_constraints()
        self._add_player_count_constraints()
        self._add_uniqueness_constraints()

    def solve(self):
        """Returns a solution, if one exists, for the scheduling problem.

        The result is a list of dicts - each dict is the result for a session,
        containing a mapping from game name -> set of players.

        """
        self.p.solve()

        if pulp.LpStatus[self.p.status] != 'Optimal':
            raise RuntimeError("Problem not solvable")

        result = []

        for i in self.session_ids:
            result.append([])

            for g in self.session_games[i]:
                game = self.all_games[g]

                players = [
                    self.players[p]
                    for p in self.session_players[i]
                    if self.choices[i][p][g].varValue
                ]

                if players:
                    result[i].append((game, players))

            result[i] = sorted(result[i], key=lambda x: x[0])

        return result

    def _make_session_players(self):
        for p in self.players:
            if 'sessions' not in p:
                p['sessions'] = self.session_ids

        session_players = []

        for i in self.session_ids:
            session_players.append([])

            for j, player in enumerate(self.players):
                if i in player['sessions']:
                    session_players[i].append(j)

        return session_players

    def _make_session_games(self):
        session_games = []

        for i, session in enumerate(self.sessions):
            session_games.append([])

            for j, game in enumerate(self.all_games):
                if self.games_db.min_playtime(game) <= session['length']:
                    session_games[i].append(j)

        return session_games

    def _make_choice_variables(self):
        """Returns a nested Dict containing binary decision variables X_i_j_k.

        These represent: for each session i, for each player j, for each game
        k: `1` if they are playing, `0` otherwise.

        """
        result = {}

        for i in self.session_ids:
            result[i] = {}

            for j in self.session_players[i]:
                result[i][j] = {}

                for k in self.session_games[i]:
                    result[i][j][k] = pulp.LpVariable(f'X_{i}_{j}_{k}', cat='Binary')

        return result

    def _make_games_played_variables(self):
        """Returns a nested Dict containing binary decision variables G_i_j.

        These represent: for each session i, for each game j: `1` if this game
        is part of this session, `0` otherwise.

        These are necessary (and cannot just be inferred from the choice
        decision variables) in order to support the disjoint constraints on the
        minimum number of players in a game - i.e. any particular game needs >=
        n players, but _only_ if the game is being played at all (if it isn't
        being played, 0 players is valid)!

        They also support the table limit constraints

        """
        result = {}

        for i in self.session_ids:
            result[i] = {}

            for j in self.session_games[i]:
                result[i][j] = pulp.LpVariable(f'G_{i}_{j}', cat='Binary')

        return result

    def _add_objective_function(self):
        """Build the objective function (the mathematical function to maximize).

        For each possible choice variable, multiply it by a _weight_ and
        sum. In the simple case the weight is 1.0 if the game is in the
        player's interests list, and 0.0 if it isn't.

        """
        objective = []

        for i in self.session_ids:
            for j in self.session_players[i]:
                for k in self.session_games[i]:
                    game = self.all_games[k]

                    objective.append(
                        self.choices[i][j][k] * self.weight(self.players[j], game)
                    )

        self.p += pulp.lpSum(objective)

    def _add_logical_play_constraints(self):
        """Enforce logical constraints.

        * Players can only play one game per-session.
        * A player can only play in a game if it is being played at all.
        * Do not break the table limit
        """
        for i in self.session_ids:
            for j in self.session_players[i]:
                self.p += (
                    pulp.lpSum(self.choices[i][j].values()) == 1,
                    f"Game Per Session {i} {j}",
                )

                for k in self.session_games[i]:
                    self.p += (
                        self.choices[i][j][k] <= self.games_played[i][k],
                        f"Game being played {i} {j} {k}",
                    )

            self.p += (
                pulp.lpSum(self.games_played[i].values()) <= self.table_limit,
                f"Table limit session {i}",
            )

    def _add_player_count_constraints(self):
        """Games have a minimum and maximum player count"""

        for i, session in enumerate(self.sessions):
            for j in self.session_games[i]:
                game = self.all_games[j]
                game_players = []

                for k in self.session_players[i]:
                    game_players.append(self.choices[i][k][j])

                # The minimum for a game, or 0 if not being played
                disjoint_minimum = self.games_db.min_players(game) * self.games_played[i][j]
                self.p += (
                    pulp.lpSum(game_players) >= disjoint_minimum,
                    f"Game min players {i} {j}"
                )

                self.p += (
                    pulp.lpSum(game_players) <= self.games_db.max_players(game, session),
                    f"Game max players {i} {j}"
                )

    def _add_uniqueness_constraints(self):
        """Make sure that players do not play games no more than once"""

        for i, _ in enumerate(self.players):
            unique_games = set(self.all_games)

            for game in unique_games:
                indexes = [x for x, g in enumerate(self.all_games) if g == game]
                variables = []

                for j in indexes:
                    for k in self.session_ids:
                        if i in self.choices[k] and j in self.choices[k][i]:
                            variables.append(self.choices[k][i][j])

                self.p += pulp.lpSum(variables) <= 1, f"Play once {i} {j}"

    def weight(self, player, game):
        if game in player['interests']:
            return 1.0
        else:
            return 0.0


if __name__ == '__main__':
    with open('sample.json') as f:
        players = json.load(f)

    games = GameDatabase.from_file('games.json')

    sessions = [
        {'name': 'Friday Eve', 'length': 300},
        {'name': 'Saturday', 'length': 720},
        {'name': 'Saturday Eve', 'length': 300},
        {'name': 'Sunday', 'length': 420},
    ]

    s = Schedule(games, players, sessions)
    result = s.solve()

    for i, session in enumerate(result):
        print(f"==== Session {sessions[i]['name']} ====")

        for game, players in session:
            print(f"## {game} ##")

            for player in players:
                print(player['name'])

            print("")

        print("")
