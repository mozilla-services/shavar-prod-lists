import json
import os
import sys
import urllib2
import re

from trackingprotection_tools import DisconnectParser

CATEGORIES = [
    "Content",
    "Advertising",
    # "Disconnect",
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
      blocklist_url=shavar_url
)
disconnect_parser = DisconnectParser(
      blocklist_url=disconnect_url
)
category_domain_diff = open('domain-diff-category.txt', 'wb')
# category_domains = get_domains_from_filters(
#       parser, list_categories, excluded_categories,
#       which_dnt, desired_tags)

def get_domains_from_category_filters(parser, category_filters):
    if type(category_filters) != list:
        raise ValueError(
            "Parameter `category_filters` must be a list of strings. "
            "You passed %s of type %s" %
            (category_filters, type(category_filters))
        )
    output = parser.get_domains_with_category(category_filters[0])
    print(" * filter %s matched %d domains"
          % (category_filters[0], len(output)))
    for category_filter in category_filters[1:]:
        result = parser.get_domains_with_category(category_filter)
        output.intersection_update(result)
        print(
            " * filter %s matched %d domains. Reduced set to %d items."
            % (category_filter, len(result), len(output))
        )
    return output

def canonicalize(d):
    if (not d or d == ""):
        return d

    # remove tab (0x09), CR (0x0d), LF (0x0a)
    # TODO?: d, _subs_made = re.subn("\t|\r|\n", "", d)
    d = re.subn("\t|\r|\n", "", d)[0]

    # remove any URL fragment
    fragment_index = d.find("#")
    if (fragment_index != -1):
        d = d[0:fragment_index]

    # repeatedly unescape until no more hex encodings
    while (1):
        _d = d
        d = urllib2.unquote(_d)
        # if decoding had no effect, stop
        if (d == _d):
            break

    # extract hostname (scheme://)(username(:password)@)hostname(:port)(/...)
    # extract path
    # TODO?: use urlparse ?
    url_components = re.match(
        re.compile(
            "^(?:[a-z]+\:\/\/)?(?:[a-z]+(?:\:[a-z0-9]+)?@)?([^\/^\?^\:]+)(?:\:[0-9]+)?(\/(.*)|$)"  # noqa
        ), d)
    host = url_components.group(1)
    path = url_components.group(2) or ""
    path = re.subn(r"^(\/)+", "", path)[0]

    # remove leading and trailing dots
    # TODO?: host, _subs_made = re.subn("^\.+|\.+$", "", host)
    host = re.subn(r"^\.+|\.+$", "", host)[0]
    # replace consequtive dots with a single dot
    # TODO?: host, _subs_made = re.subn("\.+", ".", host)
    host = re.subn(r"\.+", ".", host)[0]
    # lowercase the whole thing
    host = host.lower()

    # percent-escape any characters <= ASCII 32, >= 127, or '#' or '%'
    _path = ""
    for i in path:
        if (ord(i) <= 32 or ord(i) >= 127 or i == '#' or i == '%'):
            _path += urllib2.quote(i)
        else:
            _path += i

    # Note: we do NOT append the scheme
    # because safebrowsing lookups ignore it
    return host + "/" + _path

def find_category_domain_diff():
    base_domains = set()
    content_domains = set()
    for category in CATEGORIES:
        category_domain_diff.write('!!! Checking diff for category: {} !!!\n'.format(category))
        category_domains_shavar = get_domains_from_category_filters(
            shavar_parser, [category])
        category_domains_disconnect = get_domains_from_category_filters(
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
        for domain in large_to_small_diff:
            category_domain_diff.write(domain + '\n')
        check_large_to_small_blacklist_diff = large_to_small_diff
        small_to_large_diff = set()
        category_domain_diff.write(
            '{} domains not in {}\n'.format(smaller_list_name, larger_list_name))
        for domain in smaller_list:
            if domain not in larger_list:
                small_to_large_diff.add(domain)
                # category_domain_diff.write(domain + '\n')
        for domain in small_to_large_diff:
            category_domain_diff.write(domain + '\n')
        check_small_to_large_blacklist_diff = small_to_large_diff

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
    check_large_to_small_entities_diff = large_to_small_diff

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
    check_small_to_large_entities_diff = small_to_large_diff

    #check differences in disconnect blacklist
    assert len(check_large_to_small_blacklist_diff) == 0
    assert len(check_small_to_large_blacklist_diff) == 0
    #check differences in disconnect entities
    assert len(check_large_to_small_entities_diff) == 0
    assert len(check_small_to_large_entities_diff) == 0