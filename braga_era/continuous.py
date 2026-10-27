"""Trusted local continuous-play CLI. Keep signing keys outside narrator inputs."""

import argparse
import json
from pathlib import Path
from . import lineage
from .checkpoints import read_json, write_json


def configure():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--registry", type=Path)
    p.add_argument("--key-file", type=Path, required=True)
    s = p.add_subparsers(dest="command", required=True)
    q = s.add_parser("init-rehearsal")
    q.add_argument("--career", required=True)
    q.add_argument("--seed", required=True)
    q.add_argument("--commissioner", default="SIMULATED TEST COMMISSIONER")
    s.add_parser("inspect")
    q = s.add_parser("prepare")
    q.add_argument("--parent", type=Path, required=True)
    q.add_argument("--until", required=True)
    q.add_argument("--execution-id", required=True)
    q.add_argument("--output", type=Path, required=True)
    q = s.add_parser("authorization-template")
    q.add_argument("--manifest", type=Path, required=True)
    q.add_argument("--output", type=Path, required=True)
    q = s.add_parser("sign-decision")
    q.add_argument("--decision", type=Path, required=True)
    q.add_argument("--output", type=Path, required=True)
    q = s.add_parser("authorize")
    q.add_argument("--parent", type=Path, required=True)
    q.add_argument("--manifest", type=Path, required=True)
    q.add_argument("--approval", type=Path, required=True)
    q = s.add_parser("execute")
    q.add_argument("--execution-id", required=True)
    q.add_argument("--directory", type=Path, required=True)
    for name in ("verify", "acceptance-template", "accept", "recover-acceptance"):
        q = s.add_parser(name)
        q.add_argument("--checkpoint", type=Path, required=True)
        if name == "verify":
            q.add_argument("--fast", action="store_true")
        if name == "acceptance-template":
            q.add_argument("--output", type=Path, required=True)
        if name == "accept":
            q.add_argument("--approval", type=Path, required=True)
    q = s.add_parser("play")
    q.add_argument("view", choices=("next", "preview", "narrate", "table", "finances"))
    q.add_argument("--fixture")
    q.add_argument("--count", type=int, default=1)
    q.add_argument("--page-id")
    q = s.add_parser("cursor-export")
    q.add_argument("--output", type=Path, required=True)
    q = s.add_parser("cursor-import")
    q.add_argument("--input", type=Path, required=True)
    q = s.add_parser("backup")
    q.add_argument("--output", type=Path, required=True)
    q.add_argument("--transfer", action="store_true")
    q = s.add_parser("restore")
    q.add_argument("--archive", type=Path, required=True)
    q.add_argument("--output", type=Path, required=True)
    q = s.add_parser("restore-backup")
    q.add_argument("--input", type=Path, required=True)
    q.add_argument("--output", type=Path, required=True)
    mode = q.add_mutually_exclusive_group(required=True)
    mode.add_argument("--test-only", action="store_true")
    mode.add_argument("--production", action="store_true")
    q.add_argument("--recover-lost-authority", action="store_true")
    return p


def main(argv=None):
    args = configure().parse_args(argv)
    try:
        key = args.key_file.read_bytes()
        if len(key) < 32:
            raise ValueError("Signing key must be at least 32 raw bytes")
        cmd = args.command
        if cmd == "restore-backup":
            result = lineage.restore_backup(
                args.input,
                key,
                args.output,
                expected_test_only=args.test_only,
                recover_lost_authority=args.recover_lost_authority,
            )
        elif cmd == "sign-decision":
            doc = read_json(args.decision)
            write_json(
                args.output, {"decision": doc, "signature": lineage.sign(key, doc)}
            )
            result = {
                "signature_file": str(args.output),
                "note": "A runtime signature is not independent commissioner approval; the human must review and supply the decision.",
            }
        else:
            if args.registry is None:
                raise ValueError("--registry is required")
            if cmd == "init-rehearsal":
                lineage.provision(
                    args.registry,
                    key,
                    test_only=True,
                    commissioner=args.commissioner,
                    career_id=args.career,
                    seed=args.seed,
                )
                result = {"test_only": True, "profile": lineage.PROFILE}
            elif cmd == "inspect":
                result = lineage.inspect(args.registry, key)
            elif cmd == "prepare":
                result = lineage.prepare(
                    args.registry,
                    key,
                    args.parent,
                    until=args.until,
                    execution_id=args.execution_id,
                )
                write_json(args.output, result)
            elif cmd == "authorization-template":
                with lineage.access(args.registry, key) as (c, trusted):
                    result = lineage.expected_authorization(
                        read_json(args.manifest), trusted
                    )
                write_json(args.output, result)
            elif cmd == "authorize":
                approval = read_json(args.approval)
                lineage.authorize(
                    args.registry,
                    key,
                    args.parent,
                    read_json(args.manifest),
                    approval["decision"],
                    approval["signature"],
                )
                result = {"authorized": True, "execution_started": False}
            elif cmd == "execute":
                result = lineage.execute(
                    args.registry, key, args.execution_id, args.directory
                )
            elif cmd == "verify":
                with lineage.access(args.registry, key) as (c, trusted):
                    result = lineage.verify_payload(
                        args.checkpoint / "payload", trusted, key, replay=not args.fast
                    )
            elif cmd == "acceptance-template":
                result = lineage.acceptance_template(
                    args.registry, key, args.checkpoint
                )
                write_json(args.output, result)
            elif cmd == "accept":
                approval = read_json(args.approval)
                result = lineage.accept(
                    args.registry,
                    key,
                    args.checkpoint,
                    approval["decision"],
                    approval["signature"],
                )
            elif cmd == "recover-acceptance":
                result = lineage.recover_acceptance(args.registry, key, args.checkpoint)
            elif cmd == "play":
                result = lineage.gameplay(
                    args.registry,
                    key,
                    args.view,
                    args.fixture,
                    args.count,
                    page_id=args.page_id,
                )
            elif cmd == "cursor-export":
                result = lineage.export_cursor(args.registry, key)
                write_json(args.output, result)
            elif cmd == "cursor-import":
                result = lineage.import_cursor(
                    args.registry, key, read_json(args.input)
                )
            elif cmd == "backup":
                result = lineage.backup(
                    args.registry, key, args.output, transfer=args.transfer
                )
            elif cmd == "restore":
                result = lineage.restore(args.registry, key, args.archive, args.output)
            else:
                raise ValueError("Unsupported command")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (
        ValueError,
        OSError,
        RuntimeError,
        KeyError,
        TypeError,
        __import__("sqlite3").DatabaseError,
        __import__("zipfile").BadZipFile,
    ) as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
