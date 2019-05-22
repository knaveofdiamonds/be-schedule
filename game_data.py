import argparse
import json
import re
from xml.etree import ElementTree

from boardgamegeek import BGGClient
import requests


FAMILY_URL = 'https://api.geekdo.com/xmlapi2/family?id=19&type=boardgamefamily'

REMOVE_IDS = {
    127229, # 1830 Card game
    277030, # 1824 Duplicate
    16000, # 1825 Unit 2
    15999, # 1825 Unit 3
    31013, # 1830 Lummerland ???
    183308, # 1844/54 Duplicate
    11284, # 1862, not the Hutton one, people probably won't mean this
    162067, # 18C2C duplicate
    183212, # 18Dixie duplicate
    165740, # 18OE duplicate
}

ADD_IDS = {
    219717, # 18USA
    277759, # 1822MRS
}

SHORT_NAME_PATTERN = re.compile('\A18[a-zA-Z0-9]+')


def retrieve_18xx_family_xml(args):
    """Download the 18XX family api response, inlcuding links to games

    If args.xml has a file path then read and return that instead
    """
    if args.xml:
        with open(args.xml, 'r') as f:
            return f.read()

    result = requests.get(FAMILY_URL)
    result.raise_for_status()

    return result.content


def entries_from_raw_family_xml(xml_str):
    """Extract Thing ids and names from a family xml response"""

    xml = ElementTree.fromstring(xml_str)

    return [
        int(link.attrib['id'])
        for link in xml.findall("./item/link[@inbound='true']")
    ]


def games_only(possible_games):
    """Remove expansions/accessories and return actual games"""

    return [g for g in possible_games if not (g.accessory or g.expansion)]


def build_popularity_dict(game):
    """Return a Dict of how proportionally popular each player count is"""

    popularity = {}

    for x in game.player_suggestions:
        if (
                x.numeric_player_count >= 3 and
                x.numeric_player_count >= game.min_players and
                x.numeric_player_count <= game.max_players
        ):
            positive = x.data()['best'] + x.data()['recommended']
            total = x.data()['not_recommended'] + positive

            if total == 0:
                popularity[x.numeric_player_count] = 1.0
            else:
                popularity[x.numeric_player_count] = positive / total

    return popularity


def determine_player_count(game, popularity):
    """Determine the minimum and maximum number of players for this game.

    Ignore player counts where the votes on BGG give more than 50% not recommended
    """

    min_players = max(game.min_players, 3)
    max_players = game.max_players

    while min_players in popularity and popularity[min_players] < 0.5 and min_players < max_players:
        del popularity[min_players]
        min_players = min_players + 1

    while max_players in popularity and popularity[max_players] < 0.5 and min_players < max_players:
        del popularity[max_players]
        max_players = max_players - 1

    return min_players, max_players


def extract_game_data(game):
    """Return a dict of relevant information from the BGG API response"""

    popularity = build_popularity_dict(game)
    min_players, max_players = determine_player_count(game, popularity)

    short_name_match = SHORT_NAME_PATTERN.match(game.name)

    if short_name_match:
        short_name = short_name_match.group()
    else:
        short_name = game.name

    # Assume a game takes 4 hours if not specified
    max_playtime = max(game.min_playing_time, game.max_playing_time) or 240
    min_playtime = game.min_playing_time or 240

    return {
        'id': game.id,
        'name': short_name,
        'full_name': game.name,
        'min_players': min_players,
        'max_players': max_players,
        'min_playtime': min_playtime,
        'max_playtime': max_playtime,
        'player_count_popularity': popularity,
        'owned': game.users_owned or 1,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Construct the 18xx game 'database' from BGG."
    )
    parser.add_argument(
        '--xml',
        metavar='XML_FILE',
        help='Local file BGG API response xml for family id 19 (18xx)',
    )
    parser.add_argument(
        'output',
        metavar='FILE',
        default='games.json',
        nargs='?',
        help='Output location for JSON game data.',
    )
    args = parser.parse_args()

    raw = retrieve_18xx_family_xml(args)
    possible_game_ids = set(entries_from_raw_family_xml(raw)) - REMOVE_IDS
    possible_game_ids = list(possible_game_ids | ADD_IDS)
    possible_games = BGGClient().game_list(possible_game_ids)
    games = games_only(possible_games)
    dicts = [extract_game_data(g) for g in games]

    with open(args.output, 'w') as f:
        json.dump(dicts, f, indent=2)
