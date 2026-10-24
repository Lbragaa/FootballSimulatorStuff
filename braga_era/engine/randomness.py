"""Precommitted, isolated deterministic random streams; never outcome selection."""

import hashlib
import random

from ..history import digest
from .models import SeedCommitment


def commit_seeds(snapshot, config, seed: str | int) -> SeedCommitment:
    config.validate()
    root = digest(
        {
            "snapshot": snapshot.fingerprint,
            "config": config.fingerprint,
            "seed": str(seed),
            "scope": "noncanonical-sandbox",
        }
    )
    return SeedCommitment(root, snapshot.fingerprint, config.fingerprint, str(seed))


def stream(commitment: SeedCommitment, purpose: str) -> random.Random:
    seed = hashlib.sha256(
        (commitment.root_sha256 + ":" + purpose).encode("utf-8")
    ).digest()
    return random.Random(int.from_bytes(seed, "big"))


def verify_commitment(snapshot, config, seeds):
    if seeds != commit_seeds(snapshot, config, seeds.requested_seed):
        raise ValueError("Snapshot, configuration or committed seed changed")
