# Hikari operational runbook

**Task 03C does not authorize this procedure's production execution.** The current
accepted world remains Save 046C v2, September 26, 2027 at 23:30. Mirassol–Vasco
is officially unplayed; Vasco 3–2 Palmeiras remains final.

## Runtime and handoff

Python 3.11–3.13 and this repository are required. Runtime uses the standard
library. ChatGPT needs a Python-capable local executor or a portable file handoff
to its Python environment. The GitHub connector can inspect source and PRs; it
cannot execute this local Python process or mutate the local SQLite save.

Install exact accepted bytes with
`python tools/bootstrap_accepted.py --download --output output/accepted-046c`.
Inspect/audit with `python -m braga_era inspect --db PATH` and
`python -m braga_era audit --db PATH`. Never rebuild an approximation and call its
hash accepted. Never run a legacy reference/build script.

For a fully disposable rehearsal:

```text
python -m braga_era world create --db output/accepted-046c/database.sqlite --output output/hikari-rehearsal --seed hikari-rehearsal-fixed-v1 --policy readiness-v2
python -m braga_era.gameplay output/hikari-rehearsal next
python -m braga_era world advance output/hikari-rehearsal --until "2027-09-30 23:59"
python -m braga_era.gameplay output/hikari-rehearsal next
python -m braga_era.gameplay output/hikari-rehearsal preview --fixture lib:LIB-R16-01:L1
python -m braga_era.gameplay output/hikari-rehearsal narrate --fixture lib:LIB-R16-01:L1 --count 1
python -m braga_era.gameplay output/hikari-rehearsal table
python -m braga_era.gameplay output/hikari-rehearsal finances
```

Use a fresh directory and a fixed seed chosen before outcomes. Repeated
`advance` resumes stored commitments/results. Narration has no seek-to-final
operation: request the next 1–20 events and stop at halftime/final whistle when
appropriate. It withholds shot outcomes until the next event and postmatch data
until the final whistle. `gameplay` rejects jumping to a later fixture while
earlier narration is pending; its table uses accepted history plus revealed final
whistles only. Low-level diagnostic `world preview/report` and `private_*` files
are for engineering and contain broader state/spoilers; do not feed them to the
normal narrator.

## First production batch, only after a new explicit instruction

1. Review [commissioner decisions](task03c_decisions.md), code/CI and final season
   restoration evidence. Accept or revise exact roster, rules, timeline and model
   versions. Software acceptance alone grants no fixture authority.
2. Prepare an execution manifest through `braga_era.forward.prepare`, using exact
   046C parent, a new execution ID and seed namespace, `planned_fixtures(parent,
   until)` and a precise boundary. Recommended first boundary: **September 30
   23:59**, all 16 continental first legs plus existing month-end payroll. Do not
   include Vasco's October 3 fixture in that first authorization.
3. In the subsequently authorized trusted runtime, provision a fresh dedicated
   forward SQLite authority registry with `forward.provision(...,
   test_only=False, commissioner=...)`. This is separate from `output/canonical.json`.
   The commissioner controls a random key of at least 32 bytes outside exported
   packages. Task 03C tests use only `test_only=True` and simulated signers.
4. The commissioner signs a decision containing `action=authorize_execution`,
   exact `manifest_sha256`, all five required approvals, commissioner identity
   and the registry's `test_only` value. Pass the exact decision and HMAC to
   `forward.authorize`. An approval for rosters alone is insufficient. Review the
   manifest including its explicit financial obligations before signing.
5. Call `forward.execute(registry,key,execution_id,directory,parent)`. It binds
   the output directory, stores authorization before draws, commits every match
   snapshot/configuration/seed before execution, and resumes exactly once after
   interruption. Run it again with the **same arguments** after a crash. Never
   choose a replacement seed. Failed application rolls back its simultaneous
   group; committed results remain available for recovery.
6. `forward.verify_candidate` independently restores/replays the portable
   calculation and checks the signed authority receipt. The outer
   `official-forward-profile-1` candidate binds that exact archive, world hash,
   input manifest and receipt inventory. Its calculation profile is explicitly
   `FORWARD-CALCULATION-1`, not `DEV-03B` or a renamed development save.
7. Review the candidate hash and validation. Acceptance needs a **different**
   signed `accept_forward_candidate` decision with exact candidate and parent
   hashes. Only `forward.promote` can register it in the separate forward
   registry. Never label it Save 047 in advance; its eventual public save number
   belongs to that later acceptance decision. Do not mutate the preserved 046C
   release, bytes or approval receipt.
8. Use `forward.gameplay(registry,key,execution_id,command,fixture,count)` for
   the trusted forward handoff. It verifies the candidate and exposes its
   acceptance/test status. Generic DEV commands cannot open a scoped forward
   calculation without authenticated authority. Retain the registry, key backup,
   candidate wrapper, portable ZIP and exact accepted parent in independent
   storage. The signing key is not in the ZIP.

`forward.prepare/authorize/execute/promote` are explicit Python APIs, not hidden
side effects of `inspect`, `preview`, `narrate`, `save restore` or `world advance`.
Future fixture slots can be authorized without preassigning participants; draw
activation still waits for actual qualifiers. The initial profile supports only
the exact accepted 046C lineage. Subsequent accepted-parent registrations and
2028 rollover require separate reviewed profiles.

## Example conversational rehearsal

User: “Hikari, inspect the accepted checkpoint and show the next obligation.”

Runtime: inspect/audit exact 046C; create the disposable proposed world; `gameplay
next` identifies September 30 continentals before R26. Hikari states the accepted
date and that the working copy is noncanonical.

User: “Run the authorized rehearsal boundary and start the first match.”

Runtime: `world advance ... --until "2027-09-30 23:59"`; `gameplay next`, then
`preview` for the first returned fixture. Hikari reads both autonomous lineups,
eligibility exclusions and forecast uncertainty without a result.

User: “Continue to halftime.”

Runtime: repeatedly requests one-event narration pages (`--count 1`), stopping when
`HALF_TIME` appears. Hikari reports only delivered events. The final result is
still withheld even though it is already durably calculated.

User: “We were interrupted; continue.”

Runtime: the same `narrate` command resumes the stored cursor; no simulation or new
seed is allocated. At `FINAL_WHISTLE`, postmatch statistics become available.
Complete the remaining simultaneous/earlier fixture narration before requesting
a later preview. `table` includes only revealed finals.

User: “Show Mirassol team news.”

Runtime: after all earlier commitments and narration are handled, advance the
disposable world `--before-fixture league:332`; `gameplay next/preview` gives the
October 3 16:00 pregame handoff. Hikari does not disclose any future Vasco score.

User: “Export our rehearsal.”

Runtime: `world export ... --output output/hikari-rehearsal.zip`, followed by
`save restore ... --output output/hikari-independent-restore`. This remains a
nonpromotable development package, not an official successor.
