"""Headless world commands; every writer is confined to a marked development world."""

from pathlib import Path
from ..checkpoints import write_json


def configure(commands):
    world = commands.add_parser(
        "world", help="NONCANONICAL development-world integration only"
    )
    sub = world.add_subparsers(dest="world_command", required=True)
    for name in ("create", "demo"):
        p = sub.add_parser(name)
        p.add_argument("--db")
        p.add_argument("--output", type=Path, required=True)
        p.add_argument("--seed", required=True)
        if name == "create":
            p.add_argument("--policy", choices=("v1", "readiness-v2"), default="v1")
    for name in (
        "advance",
        "audit",
        "preflight",
        "preview",
        "narrate",
        "export",
        "report",
    ):
        p = sub.add_parser(name)
        p.add_argument("directory", type=Path)
        if name == "advance":
            boundary = p.add_mutually_exclusive_group(required=True)
            boundary.add_argument("--until")
            boundary.add_argument("--before-fixture")
        if name in ("preview", "narrate"):
            p.add_argument("--fixture", required=True)
        if name == "narrate":
            p.add_argument("--count", type=int, default=1)
        if name in ("preview", "export", "report"):
            p.add_argument("--output", type=Path, required=True)


def execute(args):
    from ..config import database_path
    from .storage import create, writer
    from .policy import ReadinessPolicy
    from .runner import advance, narrate, fixture_preview
    from .reporting import demo, report, preflight
    from .audit import audit
    from .packages import export_world

    name = args.world_command
    if name in ("create", "demo"):
        parent = database_path(args.db)
        return (
            create(
                parent,
                args.output,
                args.seed,
                ReadinessPolicy() if args.policy == "readiness-v2" else None,
            )
            if name == "create"
            else demo(parent, args.output, args.seed)
        )
    if name == "advance":
        return advance(
            args.directory, until=args.until, before_fixture=args.before_fixture
        )
    if name == "narrate":
        return narrate(args.directory, args.fixture, args.count)
    if name == "export":
        return export_world(args.directory, args.output)
    if name == "report":
        return report(args.directory, args.output)
    with writer(args.directory) as (c, policy):
        if name == "audit":
            return audit(c, args.directory / "parent.sqlite")
        if name == "preflight":
            return preflight(c, policy)
        if name == "preview":
            # Caller-visible preview is not an official execution. Its full seed commitment is included.
            value = fixture_preview(c, policy, args.fixture)
            write_json(args.output, value)
            return {
                "scope": value["scope"],
                "preview": str(args.output.resolve()),
                "postmatch_available": False,
            }
