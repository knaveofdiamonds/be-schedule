from collections import namedtuple
from xml.etree import ElementTree

import requests


FAMILY_URL = 'https://api.geekdo.com/xmlapi2/family?id=19&type=boardgamefamily'


def retrieve_18xx_family_xml():
    """Download the 18XX family api response, inlcuding links to games"""

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


if __name__ == '__main__':
    raw = retrieve_18xx_family_xml()

    for entry in entries_from_raw_family_xml(raw):
        print(entry)
