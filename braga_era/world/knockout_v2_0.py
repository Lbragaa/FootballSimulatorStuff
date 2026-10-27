"""Compatibility registration for the preserved preliminary ET 2.0 evidence."""

from . import knockout_v2

VERSION = "braga-knockout-2.0.0"


def resolve(snapshot, result, config, rules, prior=(0, 0)):
    return knockout_v2.resolve(
        snapshot, result, config, rules, prior, version=VERSION, equate=False
    )


def validate_bundle(snapshot, result, config, rules, prior, bundle):
    return knockout_v2.validate_bundle(
        snapshot, result, config, rules, prior, bundle, version=VERSION, equate=False
    )
