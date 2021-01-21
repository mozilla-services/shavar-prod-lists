#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import argparse

parser = argparse.ArgumentParser(description='Compare current against Shavar or Disconnect.me blocklist. Default compare against remote.')
parser.add_argument('-d', '--disconnect', help='Compare against Disconnect', action='store_true')
parser.add_argument('-s', '--shavar', help='Compare against Disconnect')
args = parser.parse_args()
if args.disconnect:
    github_url = 'https://raw.githubusercontent.com/disconnectme/shavar-prod-lists/master/disconnect-blacklist.json'
else:
    github_url = 'https://raw.githubusercontent.com/mozilla-services/shavar-prod-lists/master/social-tracking-protection-blacklist.json'
result = 0

def get_unique_uris(blocklist):
    category_uris = {}

    for category, category_json in blocklist['categories'].items():
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

def compare_by_categories(curr_uris, remote_uris):
    category_diff = curr_uris.keys() ^ remote_uris.keys()
    if len(category_diff) > 0:
        result = 1
        print('Categories do not match – diff is ' + str(category_diff))

    for category, unique_uris in curr_uris.items():
        if category in category_diff:
            continue
        entity_diff = unique_uris.keys() ^ remote_uris[category].keys()
        if len(entity_diff) > 0:
            result = 1
            print(
                f'{category} entities do not match – diff is ' + str(entity_diff)
            )

        for entity in unique_uris.keys():
            if entity in entity_diff:
                continue
            uris_diff = unique_uris[entity] ^ remote_uris[category][entity]
            if(len(uris_diff) > 0):
                result = 1
                print(
                    f'URIs do not match for entity {entity} – diff is '
                        + str(uris_diff)
                )

curr_blcklist_json = open('disconnect-blacklist.json', 'r')
curr_blcklist = json.load(curr_blcklist_json)
# original repo https://raw.githubusercontent.com/disconnectme/disconnect-tracking-protection/master/services.json
resp = requests.get(github_url)
remote_blocklist = json.loads(resp.content)

curr_uris = get_unique_uris(curr_blcklist)
remote_uris = get_unique_uris(remote_blocklist)

# check current and remote has the same domains in the categories
compare_by_categories(curr_uris, remote_uris)

exit(result)
