#!/usr/bin/env python3
"""Verify that every entity in disconnect-entitylist.json has both 'properties' and 'resources' fields."""

import json
import sys

with open("disconnect-entitylist.json") as f:
    data = json.load(f)

entities = data.get("entities", {})
missing = []

for name, obj in entities.items():
    has_properties = "properties" in obj
    has_resources = "resources" in obj
    if not has_properties or not has_resources:
        fields = []
        if not has_properties:
            fields.append("properties")
        if not has_resources:
            fields.append("resources")
        missing.append((name, fields))

if missing:
    print(f"Found {len(missing)} entities with missing fields:\n")
    for name, fields in missing:
        print(f"  {name}: missing {', '.join(fields)}")
    sys.exit(1)
else:
    print(f"All {len(entities)} entities have both 'properties' and 'resources' fields.")
    sys.exit(0)
