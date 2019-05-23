from collections import defaultdict
import json

import pulp

class Schedule:
    def __init__(self, games_db, players, sessions):
        self.games_db = games_db
        self.players = players
        self.sessions = sessions

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
        self.p.solve()

        if pulp.LpStatus[self.p.status] != 'Optimal':
            raise RuntimeError("Problem not solvable")

        result = []

        for i in self.choices:
            sessions = defaultdict(set)

            for j, player in enumerate(self.players):
                for k, game in enumerate(self.games):
                    if self.choices[i][j][k].varValue:
                        sessions[game].add(player['name'])

            result.append(dict(sessions))

        return result

    def _make_choice_variables(self):
        """Returns a nested Dict containing binary decision variables X_i_j_k.

        These represent: for each session i, for each player j, for each game
        k: `1` if they are playing, `0` otherwise.

        """
        return pulp.LpVariable.dicts(
            'X',
            (
                range(len(self.sessions)),
                range(len(self.players)),
                range(len(self.games)),
            ),
            cat='Binary',
        )

    def _make_games_played_variables(self):
        """Returns a nested Dict containing binary decision variables G_i_j.

        These represent: for each session i, for each game j: `1` if this game
        is part of this session, `0` otherwise.

        These are necessary (and cannot just be inferred from the choice
        decision variables) in order to support the disjoint constraints on the
        minimum number of players in a game - i.e. any particular game needs >=
        n players, but _only_ if the game is being played at all (if it isn't
        being played, 0 players is valid)!

        """
        return pulp.LpVariable.dicts(
            'G',
            (
                range(len(self.sessions)),
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

        for i, session in enumerate(self.sessions):
            for j, player in enumerate(self.players):
                for k, game in enumerate(self.games):
                    objective.append(
                        self.choices[i][j][k] * self.weight(player, game)
                    )

        self.p += pulp.lpSum(objective)

    def _add_logical_play_constraints(self):
        # Players can only play one game per-session. Equally a player can only
        # play in a game if it is being played at all.
        for i, _ in enumerate(self.sessions):
            for j, _ in enumerate(self.players):
                self.p += (
                    pulp.lpSum(self.choices[i][j].values()) == 1,
                    f"Game Per Session {i} {j}",
                )

                for k, _ in enumerate(self.games):
                    self.p += (
                        self.choices[i][j][k] <= self.games_played[i][k],
                        f"Game being played {i} {j} {k}",
                    )

    def _add_player_count_constraints(self):
        """Games have a minimum and maximum player count"""

        for i, _ in enumerate(self.sessions):
            for j, game in enumerate(self.games):
                game_players = []

                for k, _ in enumerate(self.players):
                    game_players.append(self.choices[i][k][j])


                self.p += (
                    pulp.lpSum(game_players) >= self._min_players(game) * self.games_played[i][j],
                    f"Game min players {i} {j}"
                )

                self.p += (
                    pulp.lpSum(game_players) <= self._max_players(game),
                    f"Game max players {i} {j}"
                )

    def _add_uniqueness_constraints(self):
        """Make sure that players do not play games no more than once"""

        for i, _ in enumerate(self.players):
            for j, _ in enumerate(self.games):
                variables = []

                for k, _ in enumerate(self.sessions):
                    variables.append(self.choices[k][i][j])

                self.p += pulp.lpSum(variables) <= 1, f"Play once {i} {j}"

    def _min_players(self, game):
        return self.games_db[game]['min_players']

    def _max_players(self, game):
        return self.games_db[game]['max_players']

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

    with open('games.json') as f:
        games = {g['name']: g for g in json.load(f)}

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
