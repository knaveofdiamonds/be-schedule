# This generates a 'realistic' example dataset as far as possible to be used as
# an example for the optimizer.

import json

from faker import Faker
import numpy as np


# No Belgium locale sadly :( but we use this to generate some pan-european
# names :)
LOCALES = [
    'nl_NL',
    'fr_FR',
    'it_IT',
    'de_DE',
    'en_GB',
    'es_ES',
    'cs_CZ',
    'dk_DK',
    'sv_SE',
    'pl_PL',
]

FAKES = [Faker(l) for l in LOCALES]


def fake():
    return FAKES[np.random.choice(len(LOCALES))]


def names(n=40):
    name_set = set()

    while len(name_set) < n:
        name_set.add(fake().first_name())

    return name_set


def random_games(n, games_db, games_distribution):
    games = np.random.choice(
        games_db,
        size=n,
        replace=False,
        p=games_distribution
    )

    return [g['name'] for g in games]


def owned_games(games_db, games_distribution):
    n = np.random.choice(6, p=[0.5, 0.2, 0.1, 0.1, 0.05, 0.05])

    return random_games(n, games_db, games_distribution)


def want_to_play(games_db, games_owned, games_distribution):
    n = np.random.choice(8)
    return list(set(games_owned + random_games(n, games_db, games_distribution)))


if __name__ == '__main__':
    with open('games.json', 'r') as f:
        games_db = json.load(f)

    # Only take the most owned to make the dataset a bit more realistic.
    games_db = sorted(games_db, key=lambda g: g['owned'], reverse=True)

    total_owned = sum([g['owned'] for g in games_db])
    games_distribution = [g['owned'] / total_owned for g in games_db]

    people = names()
    result = []

    for person in people:
        games_owned = owned_games(games_db, games_distribution)
        interests = want_to_play(games_db, games_owned, games_distribution)

        result.append(
            {
                'name': person,
                'owns': games_owned,
                'interests': interests
            }
        )

    with open('sample.json', 'w') as f:
        json.dump(result, f, indent=2)
