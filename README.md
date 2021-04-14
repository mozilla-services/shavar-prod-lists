# shavar-prod-lists

[![Build Status](https://travis-ci.org/mozilla-services/shavar-prod-lists.svg?branch=master)](https://travis-ci.org/mozilla-services/shavar-prod-lists)

This repo serves as a staging area for
[shavar](https://github.com/mozilla-services/shavar) /
[tracking protection](https://wiki.mozilla.org/Security/Tracking_protection)
lists prior to
[production deployment to Firefox](https://mana.mozilla.org/wiki/display/SVCOPS/Shavar+-+aka+Mozilla's+Tracking+Protection).
This repo gives Mozilla a chance to manually review all updates before they go
live, a fail-safe to prevent accidental deployment of a list that could break
Firefox.

Not all domains in this repository are blocked in all versions of Firefox.
The master branch represents the base list blocked by Nightly. Beta, release,
and past versions of Firefox all use versions of this list, accessible as
[branches](https://github.com/mozilla-services/shavar-prod-lists/branches) of
this repository. We may also unblock certain domains through our anti-tracking
interventions temporarily when we discover site breakage. These temporary
exceptions are tracked in [Bug 1537702](https://bugzilla.mozilla.org/show_bug.cgi?id=1537702),
and the policy governing their use is [described below](#temporary-exceptions).

These lists are processed and transformed and sent to Firefox via
[Shavar](https://mana.mozilla.org/wiki/display/SVCOPS/Shavar+-+aka+Mozilla's+Tracking+Protection).

## Disconnect's Lists
Firefox's Enhanced Tracking Protection features rely on lists of trackers
maintained by [Disconnect](https://disconnect.me/trackerprotection).
Mozilla does not maintain these lists. As such, we will close all issues and
pull requests related to making changes to the list contents. These issues
should be reported to Disconnect.

#### `disconnect-blacklist.json`
A version controlled copy of Disconnect's
[list of trackers](https://github.com/disconnectme/disconnect-tracking-protection/blob/master/services.json).
This blocklist is the core of tracking protection in Firefox.

A vestige of the list is the "Disconnect" category, which contains Facebook,
Twitter, and Google domains. Domains from this category are remapped into the
Social, Advertising, or Analytics categories as described
[here](https://github.com/mozilla-services/shavar-list-creation/blob/master/disconnect_mapping.json).
This remapping occurs at the time of list creation, so the Social, Analytics,
and Advertising lists consumed by Firefox will contain these domains.

Firefox consumes the list as follows:
* **Tracking**: anything in the Advertising, Analytics, Social, Content, or
    Disconnect category. Firefox ships two versions of the tracking lists: the
    "Level 1" list, which excludes the "Content" category, and the
    "Level 2" list which includes the "Content" category.
* **Cryptomining**: anything in the Cryptomining category
* **Fingerprinting**: anything in the Fingerprinting category. By default,
    ETP's fingerprinting blocking only blocks _Tracking Fingerprinters_, that
    is domains which appear in both the Fingerprinting category and one of the
    Tracking categories.

#### `disconnect-entitylist.json`

A version controlled copy of Disconnect's
[list of entities](https://github.com/disconnectme/disconnect-tracking-protection/blob/master/entities.json).
ETP classifies a resource as a tracking resource when it is present on
blocklist and loaded as a third-party. The Entity list is used to allow
third-party subresources that are wholly owned by the same company that owns
the top-level website that the user is visiting. For example, if abcd.com owns
efgh.com and efgh.com is on the blocklist, it will not be blocked on abcd.com.
Instead, efgh.com will be treated as first party on abcd.com, since the same
company owns both. But since efgh.com is on the blocklist it will be blocked on
other third-party domains that are not all owned by the same parent company.

## Other lists

In addition, Mozilla maintains several lists for Firefox-specific features and
experiments. The lists currently in active use are:
* `social-tracking-protection-blacklist.json`: a subset of trackers from
    Disconnect's blocklist. This list is used to identify "social media"
    trackers within Firefox's UI. All of the origins on this list should also
    be included in Disconnect's `disconnect-blacklist.json` list.

## List Versioning and Release Process

As of Firefox 72, all desktop releases use versioned blocklists, i.e., each
version of Firefox uses a version of `disconnect-blacklist.json` and
`disconnect-entitylist.json` specific to that version. These versions are
tracked by [branches](https://github.com/mozilla-services/shavar-prod-lists/branches)
of this repository. For the current cycle (Dec. 2019) this means there is a
73 list (Nightly), a 72 list (Beta), a 71 list (Release), and a 68 list (ESR).

Nightly uses a staging version of the blocklist; the staging blocklist pulls in
changes from Disconnect as soon as they are available. When a new version of
Firefox is released, we will also release a new version of the list that
corresponds to the version of Firefox moving from Nightly (main branch) --> Beta
(versioned branch). That version of the list will ride the trains along with its
respective Firefox version. Releases older than Firefox 69 use the 69 version of
the blocklist.

This means that all changes will be tested for at least the full beta cycle and
part of the Nightly cycle. We may choose to shorten the testing cycle in the
future.

There are three possible exceptions to this process:
1. **Fast-tracked changes** which are deployed immediately to all channels
2. **Temporary exceptions** which are deployed using Remote Settings
3. **List freezes** for when we’d like to test changes for a longer duration.
   These are tracked in Github issues on this repository.

#### Fast-tracked changes

We will fast track breakage-related updates or policy-related updates, both
of which may only be done by Disconnect. Fast-tracked changes should have
minimal, if any, risk of breakage.

Changes that may be fast-tracked include:
* Deleting a domain from the blocklist and its respective domains from the entity list.
* Adding new domains to the entity list.
* Replacing a domain currently on the list with a new domain at the request of
  the company that owns the domain. These requests must go through Disconnect.
* Moving a domain between list categories of the same feature.

As soon as Disconnect makes changes of this type we will merge
them into each versioned list and deploy them across all channels.

#### Temporary exceptions

We me choose to grant a temporary domain-based exemption in response to website
breakage as detailed in our
[anti-tracking policy](https://wiki.mozilla.org/Security/Anti_tracking_policy#Temporary_Web_Compatibility_Interventions).

#### List freezes

We may want to let certain changes bake in our pre-release browsers for a
couple extra cycles. This provides more time for us to discover user-reported
breakage or run breakage studies on the lists. In these cases we may hold back
the changes from moving to a new release of Firefox. These freezes will either
apply to the entire blocklist, or to specific categories of the blocklist
(e.g., we shipped cookie blocking for the Level 1 list while we
[further tested](https://bugzilla.mozilla.org/show_bug.cgi?id=1501461)
the Level 2 list). We will not freeze specific domains or commits.

## List update process
This repo is configured with [Travis CI
builds](https://travis-ci.org/mozilla-services/shavar-prod-lists/builds) that
run the `scripts/json_verify.py` script to verify all pull request changes to
the list are valid.

This Travis CI status check must pass before any commit can be merged or pushed
to master.

### Making changes to the format
When making changes to the list formats, corresponding changes to the
`scripts/json_verify.py` script must also be made.

To help validate the validator (such meta!), use the list fixtures in the
`tests` directory. Run the script against a specific file like this:

```
./scripts/json_verify.py -f <filename>
```

* `tests/disconnect_blacklist_invalid.json` - copy of
  `disconnect-blacklist.json` with an invalid `"dnt"` value
* `tests/disconnect_blacklist_valid.json` - copy of `disconnect-blacklist.json`
  with all valid values


```
$ ./scripts/json_verify.py -f tests/disconnect_blacklist_valid.json

tests/disconnect_blacklist_valid.json : valid

$ ./scripts/json_verify.py -f tests/disconnect_blacklist_invalid.json

tests/disconnect_blacklist_invalid.json : invalid
Facebook has bad DNT value: bogus
```

# License
Find more details about license [here](LICENSE)
