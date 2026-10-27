"""Versioned candidates and portable archives. No canonical database is overwritten."""
from __future__ import annotations

from contextlib import closing, contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import stat
import tempfile
import zipfile

from .calendar import validate_plan
from .db import connect_read_only, file_sha256
from .history import canonical_json, load_baseline
from .migrations import SCHEMA_VERSION, apply, diff, rows_by_key
from .payroll import financial_statement
from .profiles import authenticate_parent, load_046c_plan, verify_database, revision_for

FORMAT_VERSION = 1
REQUIRED_APPROVALS = ["calendar_72h_including_travel_and_fixed_league_exceptions",
                      "year_end_dates_and_long_interleg_gaps", "actual_day_incremental_payroll_policy"]


def plan_and_calendar(parent,revision):
    if revision == "v2":
        from .profile_v2 import load_plan
        from .calendar_v2 import validate
        plan=load_plan()
        return plan,validate(parent,plan)
    plan=load_046c_plan()
    return plan,validate_plan(parent,plan)


def finance_document(c,revision):
    value=financial_statement(c)
    if revision == "v2":
        value['player_obligations']=[dict(r) for r in c.execute("SELECT * FROM payroll_obligations ORDER BY period,player_id")]
    return value


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+"\n", encoding="utf-8")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _check_destination(destination: Path):
    destination = destination.resolve()
    protected = Path(__file__).resolve().parents[1] / "data/handoff"
    if destination.is_relative_to(protected) or destination.exists():
        raise FileExistsError(f"Refusing overwrite or write into preserved handoff: {destination}")
    return destination


@contextmanager
def staged_directory(destination: Path):
    destination = _check_destination(Path(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    lock = destination.parent / f".{destination.name}.lock"
    # Exclusive sibling lock coordinates writers, while publication is one rename.
    with lock.open("x"):
        pass
    try:
        staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
        try:
            yield staging
            _check_destination(destination)
            staging.rename(destination)
        finally:
            if staging.exists():
                if staging.resolve().parent != destination.parent:
                    raise ValueError("Refusing cleanup outside checkpoint staging parent")
                shutil.rmtree(staging)
    finally:
        lock.unlink(missing_ok=True)


def _publish_file(temporary: Path, destination: Path):
    # Windows rename refuses an existing target; POSIX hard-link publication
    # provides the same no-replace guarantee. Both stay on one filesystem.
    with temporary.open("r+b") as stream:
        os.fsync(stream.fileno())
    if os.name == "nt":
        temporary.rename(destination)
    else:
        os.link(temporary, destination)
        temporary.unlink()


def operations_from_database(c):
    return [{"sequence": r["sequence"], "operation_id": r["operation_id"], "table": r["table_name"],
             "key": json.loads(r["row_key_json"]),
             "before": json.loads(r["before_json"]) if r["before_json"] is not None else None,
             "after": json.loads(r["after_json"]) if r["after_json"] is not None else None,
             "reason": r["reason"]} for r in c.execute("SELECT * FROM admin_operations ORDER BY sequence")]


def complete_changes(c, parent):
    tables = sorted({r["table_name"] for r in c.execute("SELECT table_name FROM admin_operations")} | {"admin_operations"})
    before = {t: rows_by_key(parent, t) for t in tables
              if parent.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone()}
    after = {t: rows_by_key(c, t) for t in tables}
    return diff(before, after)


def metadata_for(c, db_path: Path, version: str):
    meta = dict(c.execute("SELECT key,value FROM meta"))
    candidate = version == "046C"
    operations = operations_from_database(c) if candidate else []
    result = {"format_version": FORMAT_VERSION, "save_version": version,
            "schema_version": SCHEMA_VERSION if candidate else 0,
            "parent_save_version": "046" if candidate else None,
            "parent_sha256": load_baseline()["database_sha256"] if candidate else None,
            "database_sha256": file_sha256(db_path), "fictional_date": meta["current_date"],
            "status": "candidate" if candidate else "canonical_parent_snapshot",
            "changed_tables": sorted({op["table"] for op in operations} | ({"admin_operations"} if candidate else set())),
            "operation_count": len(operations), "validation_profile": version,
            "required_approvals": REQUIRED_APPROVALS if candidate else [],
            "canonical_promoted": False}
    if candidate and revision_for(c)=="v2":
        from .profile_v2 import APPROVALS
        result.update({"proposal_revision":"v2","supersedes_unaccepted_revision":"v1","required_approvals":APPROVALS})
    return result


def render_report(metadata, validation, calendar=None, finance=None, operations=None):
    if metadata.get('proposal_revision')=='v2':
        from .profile_v2 import report
        return report(metadata,validation,calendar,finance,operations)
    lines = [f"# Save {metadata['save_version']} — {metadata['status']}", "",
             f"Fictional date: {metadata['fictional_date']}. No matches simulated or clock advancement.",
             f"Database SHA256: `{metadata['database_sha256']}`.",
             f"Parent SHA256: `{metadata['parent_sha256']}`.", "",
             f"Validation: {validation['checks']} checks, {validation['failures']} failures, {validation['warnings']} warnings.",
             "Canonical pointer unchanged. Candidate production is separate from commissioner acceptance.", ""]
    if calendar:
        lines += ["## Calendar feasibility", "", "All new cup commitments pass the 72-hour kickoff-turnaround and rolling-workload model.",
                  "League fixtures are unchanged. This is conditional feasibility, not a claim that inherited league rest problems were repaired.",
                  "The stricter 72h + 6h travel model has no solution on the conservative stage-wide grid before year-end.",
                  f"New rest intervals: `{calendar['new_rest_distribution']}`; minimum {calendar['minimum_new_turnaround_hours']}h.",
                  f"Inherited fixed league shortfalls: {len(calendar['inherited_league_rest_exceptions'])}; minimum {calendar['minimum_all_turnaround_hours']}h.", "",
                  "| Tie / reservation | Stage | Leg | Old date | Proposed kickoff | Participants / potential qualifiers |", "|---|---|---:|---|---|---|"]
        for e in sorted(load_046c_plan()["events"], key=lambda r: (r["kickoff"], r["event_id"])):
            participants = f"{e['home']} vs {e['away']}" if e["home"] and e["away"] else f"Reserved, up to {len(e['clubs'])} possible qualifiers"
            lines.append(f"| {e['event_id']} | {e['stage']} | {e['leg']} | {e['previous_date'] or 'not assigned'} | {e['kickoff']} | {participants} |")
        lines += ["", "Unresolved constraints and commissioner decisions:", ""] + [f"- {item}" for item in calendar["unresolved"]]
        lines += ["", "The 72h interval includes travel. Travel is considered by marking international events, conservative qualifier pools and the rejected extra-buffer scenario; actual itineraries are unknown. It is not 72h of recovery after travel."]
    if finance:
        lines += ["", "## Finance before / after (BRL)", "", "| Measure | Save 046 | Candidate 046C |", "|---|---:|---:|",
                  "| Restricted cash | 31,930,000.00 | 30,550,000.00 |",
                  "| August missing incremental cash debit | 1,380,000.00 unbooked | 1,380,000.00 paid once on Sep 26 |",
                  "| September accrued unpaid incremental wages | Not separately recorded | 1,559,000.01 |",
                  "| September full-month obligation under proposed proration | Not separately recorded | 1,799,666.67 |",
                  "| Cash less recorded September liability | Not reconciled | 28,990,999.99 |",
                  "| Acquisition authority remaining | 1,400,000.00 | 1,400,000.00 |",
                  "| Annual incremental wage commitments | 21,660,000.00 | 21,660,000.00 |",
                  "| Annual wage headroom | 340,000.00 | 340,000.00 |",
                  "| Scouting / agent headroom | 2,190,000.00 | 2,190,000.00 |",
                  "| Restricted emergency reserve | 16,000,000.00 | 16,000,000.00 |", "",
                  "August covers the January three signing contracts (R$310k + R$430k + R$640k). September additionally includes Arthur Dias from Sep1 and Barreal from Sep2. Actual calendar days, inclusive start dates, half-up rounding per obligation, month-end payment. January-July historical cash entries remain untouched.",
                  "No September cash debit, invented base-roster salary, new capital or duplicated annual-commitment expense is recognized. These are candidate bookkeeping policies, not recovered facts about an unspecified historical accounting convention."]
    if operations:
        lines += ["", "## Administrative changes", "", "Cup objectives: Carioca achieved, CDB achieved, Sudamericana failed; league, youth and Finance remain pending. Finance wording reflects R$68m authority. Structured progress corrects selected stale meta notes.",
                  f"Changed tables: {', '.join(metadata['changed_tables'])}.",
                  f"`operations.json` and `admin_operations` enumerate {len(operations)} changed/inserted keyed rows, with complete before/after images and reasons. `changes.json` also includes every log row itself ({2*len(operations)} total keyed row changes). Schema DDL is recorded by migration ID/hash. Log rows are validated by independent replay, without recursive self-logging."]
    lines += ["", "## Validation findings", ""]
    lines += [f"- {f['status']} [{f['code']}]: {f['message']}" for f in validation["findings"]]
    lines += ["", "## Phase 2 readiness", "", "Checkpoint infrastructure is ready for engineering review. Resolve/accept calendar and accounting policy choices before canonical promotion or any official match simulation. No R26 execution is authorized by this artifact."]
    return "\n".join(lines)+"\n"


def manifest_for(directory: Path):
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symlinks are not permitted in checkpoints")
        if path.is_file() and path.relative_to(directory).as_posix() != "manifest.json":
            result[path.relative_to(directory).as_posix()] = file_sha256(path)
    return {"format_version": FORMAT_VERSION, "files": result}


def _materialize_reports(directory: Path, version: str):
    db = directory / "database.sqlite"
    parent_path = directory / "parent.sqlite" if version == "046C" else None
    validation = verify_database(db, version, parent_path).to_dict()
    if not validation["ok"]:
        raise ValueError(f"Candidate validation failed: {validation}")
    with connect_read_only(db) as c:
        revision=revision_for(c) if version=="046C" else "v1"
        metadata = metadata_for(c, db, version)
        operations = operations_from_database(c) if version == "046C" else None
        finance = finance_document(c,revision) if version == "046C" else None
    calendar = None
    if version == "046C":
        with connect_read_only(parent_path) as parent:
            plan,calendar = plan_and_calendar(parent,revision)
            with connect_read_only(db) as candidate:
                write_json(directory / "changes.json", complete_changes(candidate, parent))
        write_json(directory / "operations.json", operations)
        write_json(directory / "calendar.json", calendar)
        write_json(directory / "finance.json", finance)
        write_json(directory / "calendar_plan.json", plan)
    write_json(directory / "checkpoint.json", metadata)
    write_json(directory / "validation.json", validation)
    write_json(directory / "save046_baseline.json", load_baseline())
    (directory / "report.md").write_text(render_report(metadata, validation, calendar, finance, operations), encoding="utf-8")
    write_json(directory / "manifest.json", manifest_for(directory))
    return metadata


def create_candidate(parent_path: Path, destination: Path, *, version="046C", fail_after=None,revision="v2"):
    if version != "046C":
        raise ValueError("Only explicit 046 -> 046C administrative migration is registered; future profiles must be implemented")
    if revision not in ("v1","v2"):
        raise ValueError("Unknown proposal revision")
    destination = _check_destination(Path(destination))
    parent_path = Path(parent_path).resolve()
    authenticate_parent(parent_path)
    with staged_directory(destination) as stage:
        shutil.copyfile(parent_path, stage / "parent.sqlite")
        shutil.copyfile(parent_path, stage / "database.sqlite")
        # All writes target an unpublished disposable copy. No inherited scripts.
        with closing(sqlite3.connect(stage / "database.sqlite")) as scratch:
            scratch.row_factory = sqlite3.Row
            if revision=='v2':
                from .profile_v2 import load_plan
                plan=load_plan()
            else:
                plan=load_046c_plan()
            apply(scratch,plan,file_sha256(parent_path),fail_after=fail_after,revision=revision)
        metadata = _materialize_reports(stage, version)
        verify_checkpoint(stage)
        authenticate_parent(parent_path)
    return metadata


def verify_checkpoint(directory: Path):
    directory = Path(directory).resolve()
    manifest = read_json(directory / "manifest.json")
    if manifest.get("format_version") != FORMAT_VERSION or manifest != manifest_for(directory):
        raise ValueError("Checkpoint manifest mismatch, unexpected/missing file or unsupported format")
    metadata = read_json(directory / "checkpoint.json")
    if metadata.get("format_version") != FORMAT_VERSION:
        raise ValueError("Unsupported checkpoint metadata format")
    version = metadata.get("save_version")
    if version == 'DEV-03B':
        from .world.packages import verify_directory
        return verify_directory(directory)
    expected_files = {"database.sqlite", "checkpoint.json", "validation.json", "report.md", "save046_baseline.json"}
    if version == "046C":
        expected_files |= {"parent.sqlite", "operations.json", "changes.json", "calendar.json", "finance.json", "calendar_plan.json"}
    if set(manifest["files"]) != expected_files:
        raise ValueError("Unexpected checkpoint payload inventory")
    if read_json(directory / "save046_baseline.json") != load_baseline():
        raise ValueError("Permanent Save 046 baseline mismatch")
    parent_path = directory / "parent.sqlite" if version == "046C" else None
    report = verify_database(directory / "database.sqlite", version, parent_path)
    if not report.ok:
        raise ValueError(f"Checkpoint fails registered validation profile: {report.to_dict()}")
    with connect_read_only(directory / "database.sqlite") as c:
        revision=revision_for(c) if version=="046C" else "v1"
        if metadata != metadata_for(c, directory / "database.sqlite", version):
            raise ValueError("Checkpoint metadata/provenance mismatch")
        operations = operations_from_database(c) if version == "046C" else None
        finance = finance_document(c,revision) if version == "046C" else None
    calendar = None
    if version == "046C":
        with connect_read_only(parent_path) as parent:
            plan,calendar = plan_and_calendar(parent,revision)
            with connect_read_only(directory / "database.sqlite") as candidate:
                changes = complete_changes(candidate, parent)
        if read_json(directory / "changes.json") != changes:
            raise ValueError("Complete row change inventory differs from validated delta")
        for filename, expected in [("operations.json", operations), ("finance.json", finance),
                                   ("calendar.json", calendar), ("calendar_plan.json", plan)]:
            if read_json(directory / filename) != expected:
                raise ValueError(f"Reconciliation report does not match validated database: {filename}")
    if read_json(directory / "validation.json") != report.to_dict():
        raise ValueError("Stored validation differs from current registered profile")
    if (directory / "report.md").read_text(encoding="utf-8") != render_report(metadata, report.to_dict(), calendar, finance, operations):
        raise ValueError("Narrative report differs from verified reconciliation")
    return {"ok": True, "metadata": metadata, "validation": report.to_dict(),
            "acceptance_eligible":version=="046C" and revision=="v2",
            "proposal_assessment":"v1 calendar rejected by Task 02B; preserved for archival verification" if version=="046C" and revision=="v1" else "No automatic acceptance"}


def export_checkpoint(directory: Path, archive: Path):
    archive = _check_destination(Path(archive))
    verify_checkpoint(directory)
    archive.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=archive.parent, delete=False) as stream:
        temporary = Path(stream.name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
            for path in sorted(Path(directory).rglob("*")):
                if path.is_file():
                    info = zipfile.ZipInfo(path.relative_to(directory).as_posix(), date_time=(1980,1,1,0,0,0))
                    info.create_system = 3
                    info.external_attr = 0o100644 << 16
                    info.compress_type = zipfile.ZIP_DEFLATED
                    bundle.writestr(info, path.read_bytes(), compresslevel=9)
        verify_archive(temporary)
        _publish_file(temporary, archive)
    finally:
        temporary.unlink(missing_ok=True)
    return {"archive": str(archive), "sha256": file_sha256(archive)}


def export_parent(parent_path: Path, archive: Path):
    authenticate_parent(parent_path)
    _check_destination(Path(archive))
    Path(archive).resolve().parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=Path(archive).resolve().parent) as temporary:
        directory = Path(temporary)
        shutil.copyfile(parent_path, directory / "database.sqlite")
        _materialize_reports(directory, "046")
        return export_checkpoint(directory, archive)


def restore_checkpoint(archive: Path, destination: Path):
    destination = _check_destination(Path(destination))
    with zipfile.ZipFile(archive) as bundle:
        infos = bundle.infolist()
        if len(infos) > 40 or sum(i.file_size for i in infos) > 100_000_000:
            raise ValueError("Checkpoint archive exceeds format limits")
        names = set()
        for info in infos:
            name = PurePosixPath(info.filename)
            if (name.is_absolute() or ".." in name.parts or "\\" in info.orig_filename or ":" in info.orig_filename
                    or "\x00" in info.orig_filename or stat.S_ISLNK(info.external_attr >> 16)
                    or info.is_dir() or info.filename.casefold() in names):
                raise ValueError(f"Unsafe or duplicate archive path: {info.filename}")
            names.add(info.filename.casefold())
        payload = {i.filename: bundle.read(i) for i in infos}
    with staged_directory(destination) as stage:
        for name, content in payload.items():
            path = stage.joinpath(*PurePosixPath(name).parts)
            if not path.resolve().is_relative_to(stage.resolve()):
                raise ValueError("Archive path escapes staging directory")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        result = verify_checkpoint(stage)
    return result


def verify_archive(archive: Path):
    with tempfile.TemporaryDirectory(prefix="braga-verify-") as scratch:
        return restore_checkpoint(archive, Path(scratch) / "checkpoint")


def promote_candidate(directory: Path, registry: Path, *, expected_parent_sha256: str,
                      approved_candidate_sha256: str, approvals: list[str]):
    """Explicit future acceptance gate; changes a pointer only, never a save.

    There is intentionally no promotion CLI in Phase 1. Tests use a temporary
    registry. A commissioner must supply exact candidate hash and policy choices.
    """
    verified = verify_checkpoint(directory)
    metadata = verified["metadata"]
    if not verified['acceptance_eligible']:
        raise ValueError("Rejected or noncandidate proposal cannot be promoted")
    if (metadata["status"] != "candidate" or approved_candidate_sha256 != metadata["database_sha256"]
            or expected_parent_sha256 != metadata["parent_sha256"] or set(approvals) != set(metadata['required_approvals'])):
        raise ValueError("Explicit candidate hash, parent and all commissioner approvals are required")
    registry = Path(registry).resolve()
    if registry.suffix != ".json" or registry.is_relative_to(Path(__file__).resolve().parents[1] / "data/handoff"):
        raise ValueError("Canonical registry must be a separate JSON pointer outside preserved handoff")
    registry.parent.mkdir(parents=True, exist_ok=True)
    lock = registry.with_suffix(".lock")
    with lock.open("x"):
        pass
    try:
        if registry.exists():
            previous = read_json(registry)
            if previous.get("registry_format") != 1 or previous.get("database_sha256") != expected_parent_sha256:
                raise ValueError("Canonical pointer parent conflict or unrecognized registry")
        value = {"registry_format": 1, "save_version": metadata["save_version"], "database_sha256": approved_candidate_sha256,
                 "checkpoint_directory": os.path.relpath(Path(directory).resolve(), registry.parent),
                 "parent_sha256": expected_parent_sha256, "approvals": sorted(approvals)}
        with tempfile.NamedTemporaryFile(dir=registry.parent, delete=False) as stream:
            temporary = Path(stream.name)
        try:
            write_json(temporary, value)
            with temporary.open("r+b") as stream:
                os.fsync(stream.fileno())
            if registry.exists():
                temporary.replace(registry)
            else:
                _publish_file(temporary, registry)
        finally:
            temporary.unlink(missing_ok=True)
    finally:
        lock.unlink(missing_ok=True)
    return value
