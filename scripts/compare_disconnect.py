#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import urllib.request, json
import argparse

parser = argparse.ArgumentParser(description='Compare Shavar and Disconnect.me blacklist.')
parser.add_argument("-f", "--file", help="blacklist to verify")
args = parser.parse_args()

result = 0

def get_unique_uris(blacklist):
    unique_uris = {}
    
    for category, category_json in blacklist['categories'].items():
        for entity in category_json:
                for entity_name, entity_json in entity.items():
                    for domain, uris in entity_json.items():
                        #if domain in ['session-replay', 'dnt', 'performance']:
                        #    continue
                        
                        if not entity_name in unique_uris:
                            unique_uris[entity_name] = set()
                        
                        for uri in uris:
                            unique_uris[entity_name].add(uri)

    return unique_uris

with open(args.file, encoding='utf8') as json_file:
    shavar_blacklist = json.load(json_file)
with urllib.request.urlopen('https://raw.githubusercontent.com/disconnectme/disconnect-tracking-protection/master/services.json') as url:
    disconnect_blacklist = json.loads(url.read().decode())

shavar_uris = get_unique_uris(shavar_blacklist)
disconnect_uris = get_unique_uris(disconnect_blacklist)

entity_diff = shavar_uris.keys() ^ disconnect_uris.keys()
if len(entity_diff) > 0:
    result = 1
    print('Entities do not match – diff is ' + str(entity_diff))

for entity in shavar_uris.keys():
    uris_diff = shavar_uris[entity] ^ disconnect_uris[entity]
    if(len(uris_diff) > 0):
        result = 1
        print('URIs do not match for entity ' + entity + ' – diff is ' + str(uris_diff))
        
exit(result)