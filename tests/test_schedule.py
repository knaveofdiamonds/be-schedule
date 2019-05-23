from collections import defaultdict

import pulp
import pytest

from schedule import GameDatabase, Schedule, owned_games

@pytest.fixture
def games():
    return GameDatabase({
        '1817': {
            'name': '1817',
            'min_players': 3,
            'max_players': 6,
        },
        '1830': {
            'name': '1830',
            'min_players': 3,
            'max_players': 6,
        },
    })


def test_owned_games():
    players = [
        {'name': 'Alice', 'owns': [], 'interests': ['1817']},
        {'name': 'Bob', 'owns': ['1817'], 'interests': ['1817', '1849']},
        {'name': 'Charles', 'owns': ['1830'], 'interests': ['1830']},
    ]

    result = owned_games(players)

    assert result == {'1817', '1830'}


def test_single_session_2_games_3_players(games):
    players = [
        {'name': 'Alice', 'owns': [], 'interests': ['1817']},
        {'name': 'Bob', 'owns': ['1817'], 'interests': ['1817', '1849']},
        {'name': 'Charles', 'owns': ['1830'], 'interests': ['1830']},
    ]

    result = Schedule(games, players, [0]).solve()

    assert result == [{'1817': {'Alice', 'Bob', 'Charles'}}]


def test_more_players_than_max_player_count(games):
    players = [
        {'name': 'Alice', 'owns': [], 'interests': ['1817']},
        {'name': 'Bob', 'owns': ['1817'], 'interests': ['1817', '1849']},
        {'name': 'Charles', 'owns': ['1830'], 'interests': ['1817']},
        {'name': 'Dick', 'owns': ['1830'], 'interests': ['1817']},
        {'name': 'Eric', 'owns': ['1830'], 'interests': ['1817']},
        {'name': 'Fred', 'owns': ['1830'], 'interests': ['1817']},
        {'name': 'Georgie', 'owns': ['1830'], 'interests': ['1817']},
    ]

    result = Schedule(games, players, [0]).solve()

    assert len(result[0]['1817']) == 4
    assert len(result[0]['1830']) == 3


def test_players_do_not_play_the_same_game_in_multiple_sessions(games):
    players = [
        {'name': 'Alice', 'owns': [], 'interests': ['1817']},
        {'name': 'Bob', 'owns': ['1817'], 'interests': ['1817', '1849']},
        {'name': 'Charles', 'owns': ['1830'], 'interests': ['1830']},
    ]

    result = Schedule(games, players, [0, 1]).solve()

    assert len(result) == 2
    assert {**result[0], **result[1]} == {
        '1817': {'Alice', 'Bob', 'Charles'},
        '1830': {'Alice', 'Bob', 'Charles'},
    }


def test_table_limit(games):
    players = [
        {'name': 'Alice', 'owns': [], 'interests': ['1817']},
        {'name': 'Bob', 'owns': ['1817'], 'interests': ['1817', '1849']},
        {'name': 'Charles', 'owns': ['1830'], 'interests': ['1817']},
        {'name': 'Dick', 'owns': [], 'interests': ['1830']},
        {'name': 'Eric', 'owns': [], 'interests': ['1830']},
        {'name': 'Fred', 'owns': [], 'interests': ['1830']},
    ]

    result = Schedule(games, players, [0], 1).solve()

    assert len(result[0]) == 1
