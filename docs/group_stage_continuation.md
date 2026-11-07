# Group-stage implementation continuation

This change adds working four-club group generation, six home/away matchdays,
recorded tables, completion fences, top-two advancement, seeded knockout draws
and final resolution to the existing DEV profile. It adds no new engine or
schema migration and preserves earlier knockout/league operation replay.

The real-engine integration test completed **24 group fixtures and five
knockout fixtures** for eight TEST entrants, recorded a champion, and passed full
independent replay. The same generator supports 16/32 entrants; a 32-club main
stage would have 96 group fixtures plus 29 knockout fixtures. Those larger
counts are generated-format expectations, not a claim of a completed 32-club
rehearsal. Group third-place results can authenticate LIB→SULA entry without
waiting for the Libertadores final. This does not implement the SULA playoff
draw, group-winner byes or complete cross-competition competition progression.

Policy `four-club-groups-1` is proposed, not approved. It shuffles a previously
committed entry pool using the career seed and edition identity. It ranks by
points, wins, goal difference, goals scored, stable club identity. Country
separation, country slot allocation, preliminary entry and official group
tiebreak policy remain incomplete. Do not call this a full Libertadores or
Sul-Americana implementation.

The team reader now joins player state and edition-specific bans in one query
instead of querying each player individually. It retains ordering, missing-state
failure and all eligibility/recovery checks. The identical 20-club × 30-loading
workload on the growing development database returned the same team hash:
29,280→1,800 SELECTs, 3.604→2.959 seconds (17.9% less wall time). This is a single
paired loading benchmark, not an episode speedup. No verification was removed.
See [safe numerical evidence](validation/team_read_optimization.json).

Production state/worker/keys/registry were untouched. The earlier 417-fixture
rehearsal is not relabeled as covering these groups. All-club economics, the full
offseason, full competition ecosystem, 2029 simulation and season-aware
production bridge remain unfinished. This continuation does not change the
not-2028-ready verdict in the execution report.
