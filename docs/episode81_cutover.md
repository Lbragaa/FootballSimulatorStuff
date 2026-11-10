# Episode #81 alternate career

The one-time importer in `tools/register_episode81_fork.py` accepts only the
commissioner-approved February 14 archive. It pins the episode #81 source,
detached checkpoint, archive bytes, result digest and signed replay seed
commitment. It verifies the restored source against the recorded independent
replay and imports those exact historical match records. The signed import is
the trust boundary for earlier history. Independent replay from that boundary
verifies the activation and later operations.

The alternate career is `the-braga-era-alt-episode81`. It has its own signer,
registry, seed namespace, request ledger and signed acceptance chain. The
February 14 match retains engine 1.1.0. A separate signed zero-match successor
activates engine 1.2.0 for subsequent fixture commitments. The disposable
rehearsal independently restored the successor, checked Vasco's Phase 3 entry,
claimed the next kickoff group with engine 1.2.0 and tested idempotent bridge
delivery after an interrupted response. It played no matches.

The existing private GitHub repository remains the transport. Read its signed
status issue before preparing a request. A valid request must bind the advertised
career, checkpoint and next sequence. Earlier requests and replies remain
associated with the original career. Keep the original authority and backup
offline for historical inspection. Use its authenticated checkpoint in
read-only mode to inspect original results.

Worker 0.13.6 contains the fork import and read-only `fork_status` command. Its
engine and fixture execution files are byte-identical to the verified 0.13.5
candidate. Activation uses the existing signed manifest and acceptance path.
