#!/usr/bin/env python3
"""
Validation tests for Disconnect entity and services lists.

The script runs as a standalone stdlib unittest suite against the
entity and services JSON files.
"""

import argparse
import json
import re
import sys
import unittest
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit


DOMAIN_PATTERN = re.compile(
    r"^([a-zA-Z0-9]|xn--)[-a-zA-Z0-9.]*\.([a-zA-Z0-9]|xn--)[-a-zA-Z0-9]*\.([a-zA-Z]{2,}|xn--[a-zA-Z0-9]+)$|"
    r"^([a-zA-Z0-9]|xn--)[-a-zA-Z0-9]*\.([a-zA-Z]{2,}|xn--[a-zA-Z0-9]+)$"
)
IPV4_PATTERN = re.compile(r"^\d+\.\d+\.\d+\.\d+$")


class TestDisconnectLists(unittest.TestCase):
    repo_root = Path(__file__).resolve().parents[1]
    entity_file = repo_root / "disconnect-entitylist.json"
    services_file = repo_root / "disconnect-blacklist.json"

    @classmethod
    def setUpClass(cls):
        cls.entity_path = Path(cls.entity_file)
        cls.services_path = Path(cls.services_file)

        if not cls.entity_path.exists():
            raise FileNotFoundError(f"Missing entity file: {cls.entity_path}")
        if not cls.services_path.exists():
            raise FileNotFoundError(f"Missing services file: {cls.services_path}")

        try:
            with cls.entity_path.open(encoding="utf-8") as handle:
                cls.entity_data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse JSON in {cls.entity_path}: {exc}") from exc

        try:
            with cls.services_path.open(encoding="utf-8") as handle:
                cls.services_data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse JSON in {cls.services_path}: {exc}") from exc

        cls.entities = cls.entity_data.get("entities", {})
        cls.categories = cls.services_data.get("categories", {})

    @staticmethod
    def _normalize_service_domain(value):
        value = value.strip().lower()
        if "://" in value:
            parsed = urlsplit(value)
            return parsed.netloc.lower()
        return value.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]

    @classmethod
    def _entity_owns_service_domain(cls, entity_domains, service_domain):
        normalized = cls._normalize_service_domain(service_domain)
        if not normalized:
            return False

        for entity_domain in entity_domains:
            owner = entity_domain.strip().lower()
            if not owner:
                continue
            if normalized == owner or normalized.endswith(f".{owner}"):
                return True
        return False

    def test_required_top_level_fields_exist(self):
        self.assertIn("license", self.entity_data, "entities file missing license")
        self.assertIn("entities", self.entity_data, "entities file missing entities map")
        self.assertIsInstance(self.entities, dict, "entities should be a mapping")

        self.assertIn("license", self.services_data, "services file missing license")
        self.assertIn("categories", self.services_data, "services file missing categories map")
        self.assertIsInstance(self.categories, dict, "categories should be a mapping")

    def test_no_duplicate_entity_names(self):
        entity_names = list(self.entities.keys())
        self.assertEqual(
            len(entity_names),
            len(set(entity_names)),
            "Duplicate entity names found in disconnect-entitylist.json",
        )

    def test_no_duplicate_domains_across_entities(self):
        all_domains = {}

        for entity_name, entity_data in self.entities.items():
            properties = entity_data.get("properties", [])
            resources = entity_data.get("resources", [])

            for domain in set(properties) | set(resources):
                if domain in all_domains:
                    self.fail(
                        f"Duplicate domain '{domain}' found in entities "
                        f"'{all_domains[domain]}' and '{entity_name}'"
                    )
                all_domains[domain] = entity_name

    def test_no_duplicate_domains_within_entities(self):
        for entity_name, entity_data in self.entities.items():
            properties = entity_data.get("properties", [])
            resources = entity_data.get("resources", [])

            duplicate_properties = [
                domain for domain, count in Counter(properties).items() if count > 1
            ]
            duplicate_resources = [
                domain for domain, count in Counter(resources).items() if count > 1
            ]

            self.assertEqual(
                len(duplicate_properties),
                0,
                f"Duplicate domains in properties of '{entity_name}': {duplicate_properties}",
            )
            self.assertEqual(
                len(duplicate_resources),
                0,
                f"Duplicate domains in resources of '{entity_name}': {duplicate_resources}",
            )

    def test_no_properties_only_entities(self):
        offenders = []
        for entity_name, entity_data in self.entities.items():
            properties = entity_data.get("properties", [])
            resources = entity_data.get("resources", [])
            if properties and not resources:
                offenders.append(entity_name)

        self.assertEqual(
            len(offenders),
            0,
            "Entities with properties but no resources found: "
            + ", ".join(sorted(offenders)[:20]),
        )

    def test_no_resource_entities_with_empty_properties(self):
        offenders = []
        for entity_name, entity_data in self.entities.items():
            properties = entity_data.get("properties", [])
            resources = entity_data.get("resources", [])
            if resources and not properties:
                offenders.append(entity_name)

        self.assertEqual(
            len(offenders),
            0,
            "Entities with resources but empty properties found: "
            + ", ".join(sorted(offenders)[:20]),
        )

    def test_no_entities_with_both_lists_empty(self):
        offenders = []
        for entity_name, entity_data in self.entities.items():
            properties = entity_data.get("properties", [])
            resources = entity_data.get("resources", [])
            if not properties and not resources:
                offenders.append(entity_name)

        self.assertEqual(
            len(offenders),
            0,
            "Entities with empty properties and resources found: "
            + ", ".join(sorted(offenders)[:20]),
        )

    def test_valid_domain_formats(self):
        for entity_name, entity_data in self.entities.items():
            for domain_type in ("properties", "resources"):
                for domain in entity_data.get(domain_type, []):
                    if IPV4_PATTERN.match(domain):
                        continue
                    if "/" in domain:
                        continue
                    self.assertTrue(
                        DOMAIN_PATTERN.match(domain) is not None,
                        f"Invalid domain format in entity '{entity_name}': {domain}",
                    )

    def test_entities_in_services_exist(self):
        entities_in_services = set()

        for service_list in self.categories.values():
            for entry in service_list:
                entities_in_services.update(entry.keys())

        missing_entities = entities_in_services - set(self.entities.keys())
        self.assertEqual(
            len(missing_entities),
            0,
            f"Entities in services file not found in entities file: {sorted(missing_entities)}",
        )

    def test_no_duplicate_entities_in_categories(self):
        for category, services in self.categories.items():
            names = []
            for service in services:
                names.extend(service.keys())

            duplicates = [name for name, count in Counter(names).items() if count > 1]
            self.assertEqual(
                len(duplicates),
                0,
                f"Duplicate entities found in category '{category}': {duplicates}",
            )

    def test_services_domains_owned_by_same_entity(self):
        offenders = []

        for category, service_list in self.categories.items():
            for entry in service_list:
                for entity_name, urls in entry.items():
                    if entity_name not in self.entities or not isinstance(urls, dict):
                        continue

                    entity_data = self.entities.get(entity_name, {})
                    entity_domains = set(entity_data.get("properties", [])) | set(
                        entity_data.get("resources", [])
                    )

                    for _, domains in urls.items():
                        if not isinstance(domains, list):
                            continue
                        for domain in domains:
                            if not self._entity_owns_service_domain(entity_domains, domain):
                                offenders.append((category, entity_name, domain))

        self.assertEqual(
            len(offenders),
            0,
            "Blacklist domains without same-entity ownership in entities file. "
            + f"First 20 of {len(offenders)}: {offenders[:20]}",
        )

    def test_services_homepage_keys_are_absolute_urls(self):
        offenders = []

        for category, service_list in self.categories.items():
            for entry in service_list:
                for entity_name, urls in entry.items():
                    if not isinstance(urls, dict):
                        continue

                    for homepage, domains in urls.items():
                        if not isinstance(domains, list):
                            continue
                        parsed = urlsplit(homepage)
                        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                            offenders.append((category, entity_name, homepage))

        self.assertEqual(
            len(offenders),
            0,
            "Service homepage keys must be absolute http(s) URLs. "
            + f"First 20 of {len(offenders)}: {offenders[:20]}",
        )

    def test_no_orphaned_entity_references(self):
        orphaned = []

        for service_list in self.categories.values():
            for entry in service_list:
                for entity_name in entry:
                    if entity_name not in self.entities:
                        orphaned.append(entity_name)

        self.assertEqual(
            len(orphaned),
            0,
            "Found orphaned service entity references: "
            + ", ".join(sorted(set(orphaned))[:20]),
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run stdlib-only Disconnect list validation tests."
    )
    parser.add_argument(
        "--entity-file",
        default=str(TestDisconnectLists.entity_file),
        help="Path to disconnect-entitylist.json",
    )
    parser.add_argument(
        "--services-file",
        default=str(TestDisconnectLists.services_file),
        help="Path to disconnect-blacklist.json",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Run tests with verbose output.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    TestDisconnectLists.entity_file = Path(args.entity_file).expanduser()
    TestDisconnectLists.services_file = Path(args.services_file).expanduser()

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestDisconnectLists)
    runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
