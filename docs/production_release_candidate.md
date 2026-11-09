# Worker 0.13.1 and the proposed 2028 season

The release wheel is `braga_era-0.13.1-py3-none-any.whl`, SHA-256
`c3b7ba4ca429ee7d34d769c0c3338bd93043af2e8562d5c33eaa31f6e5659046`.
The clean fallback is the previously released 0.12.0 wheel, SHA-256
`8be71715cbb4b8d7cf0e9ba0f4bf25926476806a0dcf552bde82b33e89270b4d`.
Verify both wheels before using the following procedure. A wheel install and a
season activation are separate operations.

## One decision package for `supported-ecosystem-rio-venues-2`

| Decision | Recommended selection and consequence |
|---|---|
| Qualification | Use recorded champions and league results for domestic and continental berths. Admit eight modeled clubs to a prospective January playoff for four first-year Série A berths. Use the recorded 2028 division tables for later promotion and relegation. Treat missing foreign national rankings and inaugural state/regional berths as modeled administrative admissions, with explicitly fictional club identities. Subsequent CDB places use prior cup finishes and current Série A membership. |
| Formats and dates | Adopt the already implemented fictional rules for the 14-edition calendar, including the 12-club Carioca, 128-club CDB and Libertadores/Sul-Americana crossover. Keep the 72-hour club rest floor, explicit release windows and holiday blackout. This policy keeps the established fictional dates and formats. The real 2026 Série B playoffs and FIFA release windows are references and differ from the fictional policy. |
| Rio grounds | Allocate the Maracanã to Flamengo and use the Raulino de Oliveira in Volta Redonda as Fluminense's proposed licensed home for this calendar. Use São Januário for Vasco and Nilton Santos for Botafogo. This sacrifices Fluminense's shared tenancy for the season and requires commissioner approval of the venue's fictional availability and licensing. Use separately modeled grounds where the archive supplies no venue. |
| Economics and market | Preserve authenticated opening balances, reserves and obligations. Authorize a prospective modeled budget for missing information, including operating receipts and non-Vasco initial liquidity. The formula uses modeled wage cost, 40% wage headroom in monthly receipts, and a separately posted operating cost. Vasco receives zero new opening capital and no replenishment of inherited transfer/wage authority. Modeling prospective receipts changes the simulated cash ledger after activation. |
| Players | Preserve recorded identities, contracts and known ages. Approve modeled ages, January transfers and registration, development, youth, retirement, and the existing affordability and guarantee checks where observations are missing. |

Regulatory references for comparison are the [CBF national calendar and competition formats](https://www.cbf.com.br/a-cbf/noticias/informes-cbf/a/cbf-anuncia-novo-calendario-do-futebol-profissional-masculino), [CBF Série B 2026 technical documents](https://www.cbf.com.br/futebol-brasileiro/noticias/undefined/ceara-x-guarani/cbf-divulga-documentos-tecnicos-do-brasileirao-da-serie-b-de-2026), [FERJ Carioca regulation](https://fferj.com.br/noticias/carioca-2026--clubes-aprovam-regulamento), [FIFA international calendar](https://inside.fifa.com/en/organisation/fifa-council/media-releases/fifa-council-approves-international-match-calendars), [CONMEBOL Libertadores manual](https://cdn.conmebol.com/wp-content/uploads/2025/12/CL-2026-Manual-de-Clubes-POR.pdf) and [Rio legislative record of Fla–Flu shared management](https://www3.alerj.rj.gov.br/lotus_notes/default.asp?URL=L3NjcHJvMjMyNy5uc2YvMGM1NmQwMjM2MjQ1MDJlODMyNTY0ZjQwMDY1OTI0NC9iZTA1YTFkOGIxZWMwMzU3MDMyNThjZGMwMDZjZTdhMT9PcGVuRG9jdW1lbnQ%3D). The engine commits the fictional proposal in the exact-parent manifest. Review it again once 2027 has closed and the actual entrants are known.

## Controlled Windows update after approval

1. Pause client submissions and confirm the existing task and worker are stopped.
   Export the task XML to secured local backup storage. Authenticate the latest
   head, cursor seal, signed pages, automatic delegation and sealed request ledger
   with `python -m tools.preflight_live_career --config <config> --scratch <private-scratch>`.
   Check there is no incomplete request or parent claim. Check the expected head
   again immediately before publishing any repair.
2. Verify the proposed repair with `python -m tools.repair_accepted_payload
   --config <config> --expected-head <sha> --scratch <private-scratch>`. After
   explicit approval, repeat with `--apply-approved-repair` under the same
   quiescent authority. The helper publishes only absent SQLite members from the
   exact signed head archive. It rejects changed bytes, stale heads and overwrite
   attempts. An interrupted repair can resume from the same archive. Historical
   cursors can use other signed archives through disposable scratch, so older
   payloads need no bulk extraction.
3. Create an authority-aware backup with the existing `continuous backup`
   procedure. Verify its manifest and restore it in isolation with the same mode
   and a separate destination. Keep the backup inactive. Use the
   [continuous-play runbook](continuous_play_runbook.md). Separately back up the
   sealed bridge ledger, signed automatic/control journals, authenticator state,
   task export and configuration in private storage. Hash the copies. Keep the
   signer and authenticator in their existing secured custody, separate from
   ordinary archives. Preserve the Windows Credential Manager target. Never
   copy the credential into a report or GitHub.
4. Use the existing standalone interpreter to run `-m pip install --no-index
   --no-deps --force-reinstall <verified-wheel>` with the task stopped. Confirm
   `python -I -B -m braga_era.bridge --help` and all installed package bytes.
   Recheck the accepted head, next sequence, stored pages, delegation, task
   action and pinned transport before enabling or starting the task. Verify the
   first delivery with one read-only request at the current sequence once the
   commissioner authorizes the restart.
5. If a pre-season update fails, stop the task and reinstall the clean 0.12.0
   fallback wheel. Verify against the same head and live sealed state. Retain the
   restored exact head files. Code rollback leaves every newly acknowledged
   request intact. After a registered multiseason successor is accepted, keep a
   build with the registered profile. Restoring an older registry to roll back
   live gameplay would violate lineage and request ordering.

2028 activation uses `prepare_season_transition` with
`{"policy":"supported-ecosystem-rio-venues-2"}` once closure checks pass. The
commissioner signs authorization, execution and exact successor acceptance
through the existing human gate. Preparation grants no permission to play.

## Standing authorization worker candidate

0.13.3 retains the installed 0.13.2 cache fix and adds an independent,
default-off standing season grant. For this update, the verified 0.13.2 wheel
is the software rollback. Recheck the latest sequence and exact parent with
the worker idle. Include the sealed human gate, reviewed preparation and bridge
ledger in the new verified private backup. Publish a head repair only if the
authenticated dry run finds missing members. Stop the task before installing the
new wheel, verify its installed bytes, and restart the existing task. Use one
`automatic_seasons_status` probe to check that the new capability is available,
the grant remains off and the accepted checkpoint is unchanged.

Keep `automatic/season-*.json` in private worker backups once in use. The
authority backup preserves signed execution and acceptance provenance in its
decision journal. A recovery that changes the authority epoch requires a new
opt-in. Finish recovery of any outstanding 0.13.3 request before falling back
to 0.13.2, which cannot process the new request commands. Roll back software
with the current registry and ledger in place.

Follow the [phone instructions](bridge_hikari_v2.md#season-boundary) for the
separate one-time opt-in and the first transition. The opt-in and update each
leave the accepted head unchanged.
