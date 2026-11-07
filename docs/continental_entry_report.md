# Continental entry implementation

Added three real-engine preliminary editions: PRE1 has six entrants/three ties,
PRE2 adds thirteen direct entrants to the three winners (sixteen/eight ties),
PRE3 uses eight winners/four ties. Every tie has two legs. The test actually
simulated **6 + 16 + 8 = 30 fixtures**, exported, restored and independently
replayed them. Winners have dependency-checked qualification routes to the next
stage and then LIB; PRE3 losers have a recorded SULA route. No past scores or
foreign domestic tables were invented. These test entry pools remain explicitly
proposed; this is not a combined qualification-to-both-finals rehearsal.

`continental_policy.py` implements a proposed 45 domestic-slot + two title-route
allocation, duplicate-title-route replacements from remaining country ranking
depth, and deterministic four-pot/eight-group country-constrained draws. Search
is bounded and never relaxes constraints. Explicit PRE3 exceptions are supported.
`schedule_country_groups` derives nationality from existing club records and
persists real fixtures only after a feasible draw. An integration test proves
missing nationality fails with **zero fixtures written**. The allocator itself
transforms supplied ranking evidence; it does not invent or authenticate missing
national tables. It is not yet a complete source-to-entry qualification service.

The material data/policy blocker is still missing foreign domestic qualification
evidence and unknown nationalities. A final integrated run must supply recorded
or explicitly modeled prospective qualification, or separately approved
administrative evidence. Existing arbitrary test pools are not a solution to
that blocker. Country allocation, preliminaries and the prior 266-match main
stage are tested components, not one completed full continental world.

Also fixed the relevant PR #10 episode continuation issue: a blocker or disabled
automatic mode now retains the unfinished Vasco round just as a progress bound
does. Disconnected signed-journal regression cases verify that resumption yields
the original round table rather than another Vasco match. Old cached responses
are unchanged; no installed worker was replaced.

Local validation: 23 preliminary/episode tests passed, the missing-nationality
integration case passed, and 20 historical reporting tests passed. The existing
main-stage proof remains 125 LIB + 141 SULA matches, separate from the new 30
preliminary fixtures. No new full 2028/2029 rehearsal, domestic/offseason work or
performance improvement is claimed in this continuation. Production state and
configuration were untouched. The project remains **not 2028-ready**.
