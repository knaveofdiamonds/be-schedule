from collections import defaultdict
import json

import pulp


class GameDatabase:
    def __init__(self, games):
        self.games = games

    @classmethod
    def from_file(cls, path):
        with open(path) as f:
            return cls({g['name']: g for g in json.load(f)})

    def min_players(self, game):
        try:
            return self.games[game]['min_players']
        except KeyError:
            return 3

    def max_players(self, game):
        try:
            return self.games[game]['max_players']
        except KeyError:
            return 4


class Schedule:
    def __init__(self, games_db, players, sessions, table_limit=10):
        self.games_db = games_db
        self.players = players
        self.sessions = sessions
        self.table_limit = table_limit

        self.session_ids = list(range(len(self.sessions)))
        self.session_players = self._make_session_players()
        self.games = list(owned_games(self.players))

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
            sessions = defaultdict(set)

            for j in self.session_players[i]:
                for k, game in enumerate(self.games):
                    if self.choices[i][j][k].varValue:
                        sessions[game].add(self.players[j]['name'])

            result.append(dict(sessions))

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

                for k in range(len(self.games)):
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
        return pulp.LpVariable.dicts(
            'G',
            (
                self.session_ids,
                range(len(self.games)),
            ),
            cat='Binary',
        )

    def _add_objective_function(self):
        """Build the objective function (the mathematical function to maximize).

        For each possible choice variable, multiply it by a _weight_ and
        sum. In the simple case the weight is 1.0 if the game is in the
        player's interests list, and 0.0 if it isn't.

        """
        objective = []

        for i in self.session_ids:
            for j in self.session_players[i]:
                for k, game in enumerate(self.games):
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

                for k, _ in enumerate(self.games):
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

        for i in self.session_ids:
            for j, game in enumerate(self.games):
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
                    pulp.lpSum(game_players) <= self.games_db.max_players(game),
                    f"Game max players {i} {j}"
                )

    def _add_uniqueness_constraints(self):
        """Make sure that players do not play games no more than once"""

        for i, _ in enumerate(self.players):
            for j, _ in enumerate(self.games):
                variables = []

                for k, _ in enumerate(self.sessions):
                    if i in self.choices[k]:
                        variables.append(self.choices[k][i][j])

                self.p += pulp.lpSum(variables) <= 1, f"Play once {i} {j}"

    def weight(self, player, game):
        if game in player['interests']:
            return 1.0
        else:
            return 0.0


def owned_games(players):
    result = set()

    for p in players:
        result |= set(p['owns'])

    return result


if __name__ == '__main__':
    with open('sample.json') as f:
        players = json.load(f)

    games = GameDatabase.from_file('games.json')

    s = Schedule(games, players, [0,1,2,3])
    result = s.solve()

    for i, session in enumerate(result):
        print(f"==== Session {i} ====")

        for game in session:
            print(f"## {game} ##")

            for player in session[game]:
                print(player)

            print("")

        print("")
