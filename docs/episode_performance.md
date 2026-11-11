# Episode latency and round continuation

## Evidence from the live bridge

The investigation used the completed replies and creation/closure timestamps.
No request was submitted. Issue #112 and the Windows worker were left alone.
The previously verified live installation was 0.13.6. The frozen 0.13.6 wheel
matches commit `ca26e0c` for the episode, registered gameplay, worker,
automatic advancement and season lineage modules, ignoring line endings.
The performance branch starts at that release commit and is independent of the
statistics feature branch. The running process was not re-inspected for this
investigation.

| Issue | Accepted batches | Results newly revealed | Issue open to close | Worker loop | Narration inside loop | Other loop time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| [106](https://github.com/Lbragaa/BragaEraCommandBridge/issues/106#issuecomment-6786305765) | 1 | 47 | 1,162 s | 964.944 s | 184.999 s | 779.945 s |
| [108](https://github.com/Lbragaa/BragaEraCommandBridge/issues/108#issuecomment-6786748539) | 0 | 8 | 417 s | 258.432 s | 72.313 s | 186.119 s |
| [109](https://github.com/Lbragaa/BragaEraCommandBridge/issues/109#issuecomment-6794948446) | 1 | 1 | 276 s | 224.547 s | 12.180 s | 212.367 s |
| [110](https://github.com/Lbragaa/BragaEraCommandBridge/issues/110#issuecomment-6796974159) | 1 | 21 | 953 s | 903.136 s | 208.394 s | 694.742 s |
| [111](https://github.com/Lbragaa/BragaEraCommandBridge/issues/111#issuecomment-6798872026) | 0 | 18 | 762 s | 691.990 s | 212.170 s | 479.820 s |

The legacy `episode_processing` timer wraps the episode loop with
`time.perf_counter()`. `narration` sums time in calls that read or commit a
page inside that loop. Both are worker wall-clock durations. They overlap.
For #111 the loop took 11m32s and the GitHub issue was open 12m42s. Adding
narration double-counts 3m32s. The remaining 70 seconds outside the loop
include some combination of polling and claiming, journal preparation,
post-loop table/agenda/results assembly, response signing and posting. The
reply does not break those down. The `performance` delivery sidecar records
elapsed delivery and GitHub polling/posting durations for the delivery path
only. Its private files were not needed for this investigation.

### What happened on #111

Issue #110 hit the 900-second cooperative time limit after delivering the
Vasco match. It returned completed Round 10 scores from historical projection
and a `round_pending` table marker. Historical reporting can include accepted
non-Vasco scores even when their detailed cursors remain behind. The table
requires the round's result cursors to reach the end.

The next episode inherited the finished Vasco target and its round through the
signed continuation journal. #111 ran zero advancement batches, changed no
accepted checkpoint or simulation time, and completed 18 existing result
cursors. The public response contains no detailed match section. It repeats
the ten round scores, publishes the final Round 10 table for the first time,
and reports a May 17 Vasco cup fixture still in the agenda. The result section
lists zero individual background results outside the round and flags 14 as
omitted with a historical retrieval route. The episode still did the cursor
work for those results.

#108 followed a different path through the same continuation rule. #106 had
already delivered both the complete Round 9 scores and the final table when
it hit its limit. The inherited target caused #108 to finish eight additional
background cursors and emit the same round again. This was a fresh UUID
processing a pending round tail. The ledger returns the sealed response for a
retry of the original UUID. A normal `vasco_match` completion is terminal, so
the next distinct request no longer inherits the old target. Further time
bounds can nevertheless require several requests to finish a long tail.

### What repeated and what did not

The old episode loop loads state and agenda separately after every page. Both
paths find and authenticate the same parent. The registered parent verifies
its descriptor and signed ancestry, validates materialized file hashes and
checks the signed marker. `unrevealed` also hashes the database even on a hit
in its bounded event-count cache. State scans fixtures, standings and ties.
The narration call authenticates the parent again, queries eligibility,
decodes the whole selected match result, builds a page of at most 20 events,
seals the entire cursor ledger and commits the page and cursor. The episode
journal also saves before and after each effect. For background matches, the
episode uses the final-page marker and fixture ID and discards the event
arrays. The final response independently projects historical records, then
fits them to its transport budget.

These paths verify accepted artifacts and read stored match results. They do
not regenerate the football world from its initial save or rerun the match.
The 479.820 seconds outside #111's narration calls occurred inside the
episode loop. Source inspection identifies repeated state, agenda, journal and
loop work there. Their exact individual shares on the live machine are
unknown. Antivirus, filesystem contention and GitHub wait are also unmeasured.
The no-batch response excludes match execution and successor acceptance as
explanations for those 479.820 seconds.

## Lifecycle and measurement

| Stage | Work and durability |
| --- | --- |
| Poll and claim | GitHub pagination and identity/edit checks precede local sequence, request hash and expected-head checks. A sealed worker ledger records the claim. Polling sleeps and network retries are outside the episode timer. |
| Prepare or recover | Load the signed request journal, validate the original request and adopt eligible retained commitments. New episodes inspect state, scan prior episode journals, and persist the starting head and stable child IDs. |
| Advance the world | The registered path prepares and authorizes the exact next operation, executes the next eligible group and due calendar/administrative work, and saves fixtures, performance and financial state. It chunks the successor and independently replays the authorized suffix. Acceptance verifies the candidate again and atomically advances the head. All of this stays in place. |
| Reveal results | Signed cursors bind fixture, result hash and last revealed sequence. Accepted results can await narration without advancing the head. A detailed Vasco or focused fixture retains the existing pages, chronology and final-whistle ordering. |
| Assemble and deliver | Ordered sections, standings and history are serialized with size bounds. The worker validates the public shape, signs and seals the response, finds or posts the matching comment and closes the issue. A retry with the same UUID resumes the journal or reuses the stored response. |

The candidate adds monotonic `episode_preparation`, `state_and_agenda`,
`episode_presentation`, and registered prepare/authorize/execute-and-verify/
accept stage durations to episode replies. It adds `episode_cpu` from
`time.process_time()` for the completing process attempt, through presentation
assembly. The stage timings are nested within the episode loop where
applicable. Journaled wall-clock timings can accumulate across recovered
attempts. An abrupt termination can lose a sample in progress. The final
serialization and journal write are outside the presentation timer. Existing
`execution_metrics.json` separates simulation/operations, structural
validation, chunk export and independent replay. GitHub delivery metrics
remain separate. The legacy reply gives no reliable measured split between
those real-match stages for issues #106, #109 and #110.

## Changes

1. Registered episodes obtain state and agenda together from one verified
   parent under the existing authority lock. Its signed, checked database hash
   keys the immutable event-count projection. Cursor state is still read and
   checked fresh. No verification verdict is cached across operations.
2. An eligible non-Vasco fixture that was not selected for detailed coverage
   gets one signed completion receipt. The worker checks the exact accepted
   head, earliest eligible group, stored result digest, current cursor and
   final whistle. It commits the full cursor and receipt in one existing
   registry transaction. The receipt contains the consumed range and result
   digest. It contains no event arrays or score. The original result and all
   earlier detailed pages remain in storage. Legacy pending page journals keep
   their original request and page format.
3. A continuation only carries an old round target if its complete table was
   still due. If the previous response published all ten scores, later output
   suppresses that repeated score list. Newly consumed results and the first
   final table still appear when eligible. The next eligible Vasco fixture can
   be reached in the same request once an already-delivered round is cleared,
   subject to existing calendar, milestone, time and safety rules.

The engine, match ordering, commitments, manager decisions and acceptance
policy are unchanged. An explicit `roundup` request and detailed narration
use their existing pathways. The 900-second cap remains a check between
operations and can be exceeded by one operation.

## Before/after measurement

Run `python -m tools.benchmark_episode_narration` from the repository. The
benchmark loads the deployed 0.13.6 gameplay module from `ca26e0c`, then
compares it with this branch. It alternates order over five paired runs,
using 18 synthetic accepted results with 64 events each, a 16 MiB padded
SQLite database and fresh signed TEST cursor registries. It measures actual
SQLite reads, database hashing, result validation and cursor transactions.
The parent hook measures one database hash per authentication call. This
isolates a subset of the real authentication path and omits ancestry I/O,
manifest handling, episode journals, historical assembly, network and
simulation. The five pairs produced identical final fixture/cursor/result-hash
sets and byte-identical football databases.

| Local roundup stage | Before median | After median | Before max | After max |
| --- | ---: | ---: | ---: | ---: |
| State and agenda | 4.419 s | 0.407 s | 4.509 s | 0.422 s |
| Narration and cursor commits | 2.961 s | 0.508 s | 3.120 s | 0.546 s |
| Parent hash subset, included above | 2.647 s | 0.447 s | 2.694 s | 0.455 s |
| Total wall time | 7.381 s | 0.915 s | 7.602 s | 0.968 s |
| Total process CPU time | 6.875 s | 0.797 s | 6.953 s | 0.812 s |

The measured local loop was **8.1× faster** at the median. Parent reads fell
from 218 to 37 and cursor receipts from 72 to 18. The wall/CPU gap includes
storage and scheduling waits. The result is a component benchmark, so it
does not predict the total time for a replay of #111 or an actual successor.
As a separate reference, 20 fixed-seed runs of the existing synthetic
substitution fixture on engine 1.2.0 each returned the same result digest.
Combined seed preparation, lineup planning and match simulation took
4.610 ms median and 5.954 ms maximum. This isolated engine check excludes
world operations, verification, database writes and all GitHub activity.
The patch makes no engine-speed change.

## Observability and rollout

Use the existing signed request status for queue/claim/completion and the new
stage timings for completed requests. A future progress feature should publish
only a request ID, coarse stage, process-heartbeat time and separate timestamp
of the last durable transition. Suggested stages are queued, preparing,
advancing, revealing, waiting for GitHub, publishing and recovering. At most one remote status
update per minute while active, with an immediate final update. A heartbeat
can continue while a verified batch or network retry waits. A fresh heartbeat
with an old progress timestamp means the process is alive but the operation
is taking time. If both become stale, report potentially unhealthy. A missing
heartbeat alone cannot distinguish a blocked network from a dead worker.
Keep heartbeats outside acceptance, cursor and delivery signatures, and never
include fixture scores, seeds, private paths or detailed failure payloads.
Remote heartbeat publication is a proposed follow-up. The present patch
emits stage timings without adding GitHub writes.
Before enabling it, test an idle queue, a long successful batch, a forced
network wait, a crash/restart of the same UUID and throttled updates. Assert
the heartbeat cannot change the accepted head, cursor ledger or delivery.

Before a later authorized rollout, build a versioned wheel, rehearse it with
a disposable registered save and verify an interrupted background receipt
can resume. Install during an idle bridge window using the existing Windows
task and preserve the accepted head and sealed ledger. A software rollback
uses the previous verified wheel and task configuration while idle. Resolve
any pending new-format background journal with the candidate before reverting,
because 0.13.6 expects a detailed page for the same page ID. No save migration
or match replay is required.

Remaining work in order of evidence and risk

1. Benchmark an authorized disconnected copy at realistic history size with
   new stage metrics. The isolated benchmark measures the dominant repeated
   operations but cannot attribute the exact live time.
2. Measure repeated full result projection, retained-journal enumeration and
   response formatting. Small comments may contain multiple signed historical
   continuation tokens and omit background results even after cursor work.
3. Registered candidate verification runs both during execution and during
   acceptance. Profile both independently before proposing any structural
   change. Preserve independent replay, signatures and atomic acceptance.
4. Use local timing and GitHub delivery metrics before modifying polling
   cadence. Poll delay and rate limits affect end-to-end waits but cannot
   explain time already recorded inside the local no-batch loop.
