#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import glob
import json
import re
import sys
import traceback
from collections import Counter
from urllib.parse import urlparse

SESSION_REPLAY_TAG = 'session-replay'
PERFORMANCE_TAG = 'performance'
ALL_TAGS = [
    SESSION_REPLAY_TAG,
    PERFORMANCE_TAG
]

parser = argparse.ArgumentParser(description='Verify json files for shavar.')
parser.add_argument("-f", "--file", help="filename to verify")

bad_uris = []
dupe_hosts = {
    "properties": [],
    "resources": []
}
block_host_uris = []
entity_host_uris = []
errors = []
file_contents = []
file_name = ""
result = 0


def run(file):
    global file_name
    file_name = file
    try:
        verify(file)
    except Exception:
        errors.append("\tError: Problem handling file")
    finish()


def verify(file):
    try:
        with open(file) as f:
            raw_data = f.readlines()
            # save contents of file, including line numbers
            for x in range(0, len(raw_data)):
                line_number = x+1
                file_contents.append([raw_data[x], line_number])
            # attempt to parse file as json
            json_obj = json.loads("".join(raw_data))
            try:
                # determine which schema this file uses
                if ("categories" in json_obj):
                    # disconnect_blacklist.json
                    find_uris(json_obj["categories"])
                elif ("entities" in json_obj):
                    # disconnect_entitylist.json
                    find_uris_in_entities(json_obj["entities"])
                else:
                    # disconnect_entitylist.json old structure
                    # deprecated after PR 235
                    find_uris_in_entities(json_obj)
            except Exception as e:
                excp = traceback.format_exception(*sys.exc_info())
                errors.append(
                    "---Error: Received error %s while parsing file.\n%s" % (
                        type(e), ''.join(excp))
                )
    except ValueError as e:
        # invalid json formatting
        errors.append("---Error: %s" % e)
        return
    except IOError as e:
        # non-existent file
        errors.append("---Error: Can't open file: %s" % e)
        return


def find_uris(categories_json):
    """
    `categories_json` is expected to match this format:
        "categories": {
            "Advertising": [
                {
                    "[x+1]": {
                        "http://www.xplusone.com/": [
                            "ru4.com",
                            ...
                        ]
                    }
                },
                {
                    "Google": {
                        "http://www.google.com/": [
                            "2mdn.net",
                            ...
                        ]
                    }
                },
                ...
            ],
            "Fingerprinting": [
                {
                    "Example Fingerprinter": {
                        "http://example.com/": [
                            "example.com",
                            "fingerprinting.example"
                        ]
                    }
                },
                ...
            ],
            "Cryptomining": [
                {
                    "The Best Tracker LLC": {
                        "http://tracker.example/": [
                            "tracker.example",
                            ...
                        ]
                    }
                },
                ...
            ],
            ...
        }
    """
    assert isinstance(categories_json, dict)
    for category, category_json in categories_json.items():
        assert isinstance(category, str)
        assert isinstance(category_json, list)
        for entity in category_json:
            assert isinstance(entity, dict)
            for entity_name, entity_json in entity.items():
                assert isinstance(entity_name, str)
                assert isinstance(entity_json, dict)
                # pop dnt out of the dict, so we can iteritems() over the rest
                try:
                    dnt_value = entity_json.pop('dnt', '')
                    assert dnt_value in ["w3c", "eff", ""]
                except AssertionError:
                    errors.append("%s has bad DNT value: %s" % (entity_name,
                                                                dnt_value))
                # pop sub-category tags out of the dict
                for tag in ALL_TAGS:
                    tag_value = entity_json.pop(tag, '')
                    assert tag_value in ["true", ""]
                    if tag_value == "":
                        continue
                for domain, uris in entity_json.items():
                    assert isinstance(domain, str)
                    assert isinstance(uris, list)
                    for uri in uris:
                        check_uri(uri)
                        block_host_uris.append(uri)


def find_uris_in_entities(entitylist_json):
    checked_uris = {
        "properties": [],
        "resources": []
    }
    assert len(entitylist_json.items()) > 0
    assert isinstance(entitylist_json, dict)
    for entity, types in entitylist_json.items():
        assert isinstance(entity, str)
        assert isinstance(types, dict)
        for host_type, uris in types.items():
            assert host_type in ["properties", "resources"]
            assert isinstance(uris, list)
            for uri in uris:
                if uri in checked_uris[host_type]:
                    dupe_hosts[host_type].append(uri)
                check_uri(uri)
                entity_host_uris.append(uri)
                checked_uris[host_type].append(uri)


def check_uri(uri):
    # Valid URI:
    # 	no scheme, port, fragment, path or query string
    # 	no disallowed characters
    # 	no leading/trailing garbage
    try:
        uri.decode('ascii')
    except UnicodeEncodeError:
        bad_uris.append(uri)
    parsed_uri = urlparse(uri)
    try:
        assert parsed_uri.scheme == ''
        # domains of urls without schemes are parsed into 'path' so check path
        # for port
        assert ':' not in parsed_uri.path
        assert parsed_uri.netloc == ''
        assert parsed_uri.params == ''
        assert parsed_uri.query == ''
        assert parsed_uri.fragment == ''
        assert len(parsed_uri.path) < 128
    except AssertionError:
        bad_uris.append(uri)
    return


def find_line_number(uri):
    line = 0
    try:
        for x in range(0, len(file_contents)):
            temp = file_contents[x][0].decode("utf-8", "ignore")
            if re.search(uri, temp):
                line = file_contents[x][1]
                file_contents.pop(x)
                break
    except ValueError as e:
        print(e)
        line = -1
    return str(line)


def make_errors_from_bad_uris():
    for bad_uri in bad_uris:
        errors.append("\tError: Bad URI: %s\t: in line %s" %
                      (bad_uri, find_line_number(bad_uri)))
    for host_type, hosts in dupe_hosts.items():
        for host in hosts:
            errors.append("\tDupe: Dupe host: %s\t in line %s" %
                          (host, find_line_number(host)))


def finish():
    make_errors_from_bad_uris()
    if (len(errors) == 0):
        print("\n" + file_name + " : valid")
    else:
        global result
        result = 1
        print("\n" + file_name + " : invalid")
        for error in errors:
            print(error)
    reset()


def reset():
    global bad_uris
    bad_uris = []
    global dupe_hosts
    dupe_hosts = {
        "properties": [],
        "resources": []
    }
    global errors
    errors = []
    global file_contents
    file_contents = []
    global file_name
    file_name = ""


def start(filename=None):
    if (filename):
        run(filename)
    else:
        for f in glob.glob("*.json"):
            run(f)


args = parser.parse_args()
start(args.file)
print("\n block_host_uris: %s " % len(block_host_uris))
print("\n entity_host_uris: %s " % len(entity_host_uris))
assert "itisatracker.com" in block_host_uris
exit(result)
