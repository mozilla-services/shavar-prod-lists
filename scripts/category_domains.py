import json
import os
import sys
import urllib2

from trackingprotection_tools import DisconnectParser
from lists2safebrowsing import (
    canonicalize,
    get_domains_from_category_filters,
    get_domains_from_filters
)

DISCONNECT_MAPPING = os.path.join(
    os.path.dirname(__file__), 'disconnect_mapping.json')
CATEGORIES = [
    "Content",
    "Advertising",
    "Disconnect",
    "Analytics",
    "Social",
    # "Facebook",
    # "Twitter",
    # "LinkedIn",
    # "YouTube",
    "Fingerprinting",
    "Cryptomining",
    # "fanBoyAnnoyance",
    # "fanBoySocial",
    # "easyList",
    # "easyPrivacy",
    # "adGuard",
]

shavar_url = 'https://raw.githubusercontent.com/mozilla-services/shavar-prod-lists/master/disconnect-blacklist.json'
disconnect_url = 'https://raw.githubusercontent.com/disconnectme/disconnect-tracking-protection/master/services.json'
shavar_parser = DisconnectParser(
      blocklist_url=shavar_url,
      disconnect_mapping=DISCONNECT_MAPPING
)
disconnect_parser = DisconnectParser(
      blocklist_url=disconnect_url,
      disconnect_mapping=DISCONNECT_MAPPING
)
category_domain_diff = open('domain-diff-category.txt', 'wb')
# category_domains = get_domains_from_filters(
#       parser, list_categories, excluded_categories,
#       which_dnt, desired_tags)

content_domains = set()
base_domains = set()

def find_category_domain_diff():
    for category in CATEGORIES:
        category_domain_diff.write('!!! Checking diff for category: {} !!!\n'.format(category))
        category_domains_shavar = get_domains_from_filters(
            shavar_parser, [category])
        category_domains_disconnect = get_domains_from_filters(
            disconnect_parser, [category])
        if category == 'Content':
            content_domains = category_domains_disconnect
        if category in ['Advertising', 'Analytics', 'Social']:
            if len(base_domains) == 0:
                base_domains = category_domains_disconnect
            else:
                base_domains = base_domains.union(category_domains_disconnect)
        if category == 'Fingerprinting':
            fingerprinting_domains = category_domains_disconnect
        larger_list = []
        smaller_list = []
        if len(category_domains_shavar) > len(category_domains_disconnect):
            category_domain_diff.write(
                'Len of Shavar: {}. Len of Disconnect: {}\n'.format(
                    len(category_domains_shavar), len(category_domains_disconnect)
                ))
            larger_list = category_domains_shavar
            smaller_list = category_domains_disconnect
            larger_list_name = 'Shavar'
            smaller_list_name = 'Disconnect'
        else:
            category_domain_diff.write(
                'Len of Shavar: {}. Len of Disconnect: {}\n'.format(
                    len(category_domains_shavar), len(category_domains_disconnect)
                ))
            larger_list = category_domains_disconnect
            smaller_list = category_domains_shavar
            larger_list_name = 'Disconnect'
            smaller_list_name = 'Shavar'
        large_to_small_diff = set()
        category_domain_diff.write(
            '{} domains not in {}\n'.format(larger_list_name, smaller_list_name))
        for domain in larger_list:
            if domain not in smaller_list:
                large_to_small_diff.add(domain)
                # category_domain_diff.write(domain + '\n')
        sorted_data = sorted(large_to_small_diff, key=lambda item: (int(item.partition(' ')[0])
                                       if item[0].isdigit() else float('inf'), item))
        for domain in large_to_small_diff:
            category_domain_diff.write(domain + '\n')
        assert len(large_to_small_diff) == 0
        small_to_large_diff = set()
        category_domain_diff.write(
            '{} domains not in {}\n'.format(smaller_list_name, larger_list_name))
        for domain in smaller_list:
            if domain not in larger_list:
                small_to_large_diff.add(domain)
                # category_domain_diff.write(domain + '\n')
        sorted_data = sorted(small_to_large_diff, key=lambda item: (int(item.partition(' ')[0])
                                       if item[0].isdigit() else float('inf'), item))
        for domain in small_to_large_diff:
            category_domain_diff.write(domain + '\n')
        assert len(small_to_large_diff) == 0
import ipdb; ipdb.set_trace()
if False:
    disconnect_entities = []
    shavar_entities = []
    entity_url = 'https://raw.githubusercontent.com/mozilla-services/shavar-prod-lists/master/disconnect-entitylist.json'

    try:
        whitelist = json.loads(urllib2.urlopen(entity_url).read())
    except Exception:
        sys.stderr.write("Error loading %s\n" % entity_url)
        sys.exit(-1)
    for name, entity in sorted(whitelist.items()):
        name = name.encode('utf-8')
        for prop in entity['properties']:
            for res in entity['resources']:
                prop = prop.encode('utf-8')
                res = res.encode('utf-8')
                if prop == res:
                    continue
                d = canonicalize('%s/?resource=%s' % (prop, res))
                shavar_entities.append(d)

    entity_url = 'https://raw.githubusercontent.com/disconnectme/disconnect-tracking-protection/master/entities.json'
    try:
        whitelist = json.loads(urllib2.urlopen(entity_url).read())
    except Exception:
        sys.stderr.write("Error loading %s\n" % entity_url)
        sys.exit(-1)
    for name, entity in sorted(whitelist.items()):
        name = name.encode('utf-8')
        for prop in entity['properties']:
            for res in entity['resources']:
                prop = prop.encode('utf-8')
                res = res.encode('utf-8')
                if prop == res:
                    continue
                d = canonicalize('%s/?resource=%s' % (prop, res))
                disconnect_entities.append(d)

    if len(disconnect_entities) > len(shavar_entities):
        larger_list = disconnect_entities
        smaller_list = shavar_entities
        larger_list_name = 'Disconnect'
        smaller_list_name = 'Shavar'
    else:
        larger_list = shavar_entities
        smaller_list = disconnect_entities
        larger_list_name = 'Shavar'
        smaller_list_name = 'Disconnect'

    large_to_small_diff = set()
    category_domain_diff.write(
        '{} entities not in {}\n'.format(larger_list_name, smaller_list_name))
    for domain in larger_list:
        if domain not in smaller_list:
            large_to_small_diff.add(domain)
            # category_domain_diff.write(domain + '\n')
    sorted_data = sorted(large_to_small_diff, key=lambda item: (int(item.partition(' ')[0])
                                   if item[0].isdigit() else float('inf'), item))
    for domain in sorted_data:
        category_domain_diff.write(domain + '\n')

    small_to_large_diff = set()
    category_domain_diff.write(
        '{} entities not in {}\n'.format(smaller_list_name, larger_list_name))
    for domain in smaller_list:
        if domain not in larger_list:
            small_to_large_diff.add(domain)
            # category_domain_diff.write(domain + '\n')
    sorted_data = sorted(small_to_large_diff, key=lambda item: (int(item.partition(' ')[0])
                                   if item[0].isdigit() else float('inf'), item))
    for domain in sorted_data:
        category_domain_diff.write(domain + '\n')
