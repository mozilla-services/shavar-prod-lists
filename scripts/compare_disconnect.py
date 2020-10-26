#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import argparse

parser = argparse.ArgumentParser(description='Compare Shavar and Disconnect.me blacklist.')
# parser.add_argument("file", type=str, help="blacklist to verify")
args = parser.parse_args()

result = 0

def get_unique_uris(blacklist):
    category_uris = {}

    for category, category_json in blacklist['categories'].items():
        unique_uris = {}
        for entity in category_json:
                for entity_name, entity_json in entity.items():
                    for domain, uris in entity_json.items():
                        if not entity_name in unique_uris:
                            unique_uris[entity_name] = set()

                        for uri in uris:
                            unique_uris[entity_name].add(uri)
        category_uris[category] = unique_uris

    return category_uris

shavar_blacklist_json = open('disconnect-blacklist.json', 'r')
shavar_blacklist = json.load(shavar_blacklist_json)
# resp = requests.get('https://raw.githubusercontent.com/disconnectme/disconnect-tracking-protection/master/services.json')
resp = requests.get('https://raw.githubusercontent.com/disconnectme/shavar-prod-lists/master/disconnect-blacklist.json')
disconnect_blacklist = json.loads(resp.content)

shavar_uris = get_unique_uris(shavar_blacklist)
disconnect_uris = get_unique_uris(disconnect_blacklist)

# check Disconnect and Shavar has the same categories
category_diff = shavar_uris.keys() ^ disconnect_uris.keys()
if len(category_diff) > 0:
    result = 1
    print('Categories do not match – diff is ' + str(category_diff))

for category, unique_uris in shavar_uris.items():
    if category in category_diff:
        continue
    entity_diff = unique_uris.keys() ^ disconnect_uris[category].keys()
    if len(entity_diff) > 0:
        result = 1
        print(
            f'{category} entities do not match – diff is ' + str(entity_diff)
        )

    for entity in unique_uris.keys():
        if entity in entity_diff:
            continue
        uris_diff = unique_uris[entity] ^ disconnect_uris[category][entity]
        if(len(uris_diff) > 0):
            result = 1
            print(
                f'URIs do not match for entity {entity} – diff is '
                    + str(uris_diff)
            )

exit(result)
