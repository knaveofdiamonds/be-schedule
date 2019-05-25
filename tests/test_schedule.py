import pytest

from schedule import GameDatabase, Schedule


@pytest.fixture
def games():
    return GameDatabase({
        '1817': {
            'name': '1817',
            'min_players': 3,
            'max_players': 6,
            'min_playtime': 360,
            'max_playtime': 540,
        },
        '1830': {
            'name': '1830',
            'min_players': 3,
            'max_players': 6,
            'min_playtime': 180,
            'max_playtime': 360,
        },
        '1860': {
            'name': '1860',
            'min_players': 3,
            'max_players': 4,
            'min_playtime': 240,
            'max_playtime': 240,
        },
    })


def session(**kwargs):
    return {'length': 600, **kwargs}


def test_single_session_2_games_3_players(games):
    players = [
        {'name': 'Alice', 'owns': [], 'interests': ['1817']},
        {'name': 'Bob', 'owns': ['1817'], 'interests': ['1817', '1849']},
        {'name': 'Charles', 'owns': ['1830'], 'interests': ['1830']},
    ]

    result = Schedule(games, players, [session()]).solve()

    assert result == [[('1817', players)]]


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

    result = Schedule(games, players, [session()]).solve()

    print(result)

    assert len(result[0][0][1]) == 4
    assert len(result[0][1][1]) == 3


def test_players_do_not_play_the_same_game_in_multiple_sessions(games):
    players = [
        {'name': 'Alice', 'owns': [], 'interests': ['1817']},
        {'name': 'Bob', 'owns': ['1817'], 'interests': ['1817', '1849']},
        {'name': 'Charles', 'owns': ['1830'], 'interests': ['1830']},
    ]

    result = Schedule(games, players, [session(), session()]).solve()
    result = result[0] + result[1]

    assert len(result) == 2
    assert ('1817', [players[0], players[1], players[2]]) in result
    assert ('1830', [players[0], players[1], players[2]]) in result


def test_table_limit(games):
    players = [
        {'name': 'Alice', 'owns': [], 'interests': ['1817']},
        {'name': 'Bob', 'owns': ['1817'], 'interests': ['1817', '1849']},
        {'name': 'Charles', 'owns': ['1830'], 'interests': ['1817']},
        {'name': 'Dick', 'owns': [], 'interests': ['1830']},
        {'name': 'Eric', 'owns': [], 'interests': ['1830']},
        {'name': 'Fred', 'owns': [], 'interests': ['1830']},
    ]

    result = Schedule(games, players, [session()], table_limit=1).solve()

    assert len(result[0]) == 1


def test_not_all_players_attend_all_sessions(games):
    players = [
        {'name': 'Alice', 'owns': ['1817'], 'interests': ['1817'], 'sessions': [0, 1]},
        {'name': 'Bob', 'owns': [], 'interests': ['1817'], 'sessions': [0]},
        {'name': 'Charles', 'owns': [], 'interests': ['1817'], 'sessions': [1]},
        {'name': 'Dick', 'owns': [], 'interests': ['1817'], 'sessions': [1]},
        {'name': 'Eric', 'owns': ['1830'], 'interests': [], 'sessions': [0]},
        {'name': 'Fred', 'owns': [], 'interests': [], 'sessions': [0]},
    ]

    result = Schedule(games, players, [session(), session()]).solve()

    assert result == [
        [('1830', [players[0], players[1], players[4], players[5]])],
        [('1817', [players[0], players[2], players[3]])],
    ]


def test_short_sessions_restrict_games_with_static_playtimes(games):
    players = [
        {'name': 'Alice', 'owns': ['1817'], 'interests': ['1817']},
        {'name': 'Bob', 'owns': ['1860'], 'interests': ['1817']},
        {'name': 'Charles', 'owns': [], 'interests': ['1817']},
        {'name': 'Dick', 'owns': [], 'interests': ['1817']},
    ]

    result = Schedule(games, players, [session(length=300)]).solve()

    assert result == [
        [('1860', players)],
    ]


def test_short_sessions_restrict_games_with_dynamic_playtimes(games):
    players = [
        {'name': 'Alice', 'owns': ['1817'], 'interests': ['1817']},
        {'name': 'Bob', 'owns': ['1860'], 'interests': ['1817']},
        {'name': 'Charles', 'owns': ['1830'], 'interests': ['1817', '1830']},
        {'name': 'Dick', 'owns': [], 'interests': ['1817', '1830']},
        {'name': 'Eric', 'owns': [], 'interests': ['1817', '1830']},
        {'name': 'Fred', 'owns': [], 'interests': ['1817', '1830']},
    ]

    result = Schedule(games, players, [session(length=240)]).solve()

    assert {x for x, _ in result[0]} == {'1830', '1860'}


def test_multiple_copies_of_a_game(games):
    players = [
        {'name': 'Alice', 'owns': ['1830'], 'interests': ['1830']},
        {'name': 'Bob', 'owns': ['1830'], 'interests': ['1830']},
        {'name': 'Charles', 'owns': ['1830'], 'interests': []},
        {'name': 'Dick', 'owns': [], 'interests': []},
        {'name': 'Eric', 'owns': [], 'interests': []},
        {'name': 'Fred', 'owns': [], 'interests': []},
        {'name': 'Georgie', 'owns': [], 'interests': []},
    ]

    result = Schedule(games, players, [session()]).solve()

    assert [x for x, _ in result[0]] == ['1830', '1830']


def test_games_only_available_if_players_are_in_session(games):
    players = [
        {'name': 'Alice', 'owns': ['1860'], 'interests': ['1860'], 'sessions': [0]},
        {'name': 'Bob', 'owns': [], 'interests': ['1860']},
        {'name': 'Charles', 'owns': [], 'interests': ['1860']},
        {'name': 'Dick', 'owns': [], 'interests': ['1860']},
        {'name': 'Eric', 'owns': [], 'interests': ['1860']},
        {'name': 'Fred', 'owns': [], 'interests': ['1860']},
        {'name': 'Georgie', 'owns': [], 'interests': ['1860']},
    ]

    result = Schedule(games, players, [session(), session()], ['1830', '1817']).solve()

    assert '1860' in {x for x, _ in result[0]}
    assert '1860' not in {x for x, _ in result[1]}
