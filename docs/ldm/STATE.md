# legal_department_management — living state

Read this first when resuming. Update it whenever the state changes.

## The goal (the owner's words, 2026-09-24)

Take SAG Group's showcase module `legal_department_management`
(github.com/ahmadmessi89-max/legal_department_management) and turn it into
professional software:

- one module serving **in-house legal departments and law offices**,
  configurable between the two;
- covering the **full work** of both, researched rather than guessed;
- **ease of use first**: little clutter, very direct, with advanced fields,
  options and data still available when asked for;
- **custom OWL components** wherever they make the work easier; other
  libraries only where they truly improve the workflow;
- built as a team workflow with **visual verification of everything** and
  tests.

## Constraints discovered

- SAG runs the showcase **in production** (`odoo.sag2.group`, Odoo 19
  Community, about 10 ministries, 23 departments, 2 client companies and
  11 matters, per `docs/external-review/sag-legal-module.md`). The rebuild must
  **upgrade over that data**: keep the technical name, the models
  `legal.task`, `legal.company`, `legal.ministry`, `legal.department`, and their
  xmlids. Any renamed or dropped field needs a migration script.
- Self-contained: the module must not depend on any other `legal_*` module in
  this repository. Porting code from them is allowed (same owner).
- Arabic (`ar_001`, RTL) is the primary UI; English must also be complete.

## Delivery repository (the owner's instruction, 2026-09-24)

The work is delivered to SAG's repository
**github.com/ahmadmessi89-max/legal_department_management**, branch
**`professional-19.0.7`** (module at the repository root, documents under
`docs/ldm/`). SAG's `main` stays untouched until the owner decides to merge.
Local clone: `C:\Users\Lenovo\Documents\ldm_repo\legal_department_management`.
Publish every milestone with `bash docs/ldm/tools/sync_to_sag.sh --push` (from
this workspace): it replays new module commits with their messages and authors
and copies `docs/ldm`. Development, databases and tests stay in this workspace.

## Screenshots

All screenshots, by stage: `C:\Users\Lenovo\Documents\LDM Screenshots\`.
Refresh with `python docs/ldm/tools/collect_screenshots.py`.

## Environment

| | |
|---|---|
| Config | `odoo19_ldm.conf` (git-ignored), port **8110**, `db_name = ldm_pro`, `dbfilter ^ldm_pro$` (moved off 8095 on 24 Sep: the ANU project's `odoo19_intel.conf` also uses 8095, and on Windows two servers can hold one port, so requests landed on the wrong one) |
| Postgres | shared `PostgreSQL_For_Odoo` cluster on **5432** (12.4), user `openpg`; no `psql` here: `python docs/ldm/tools/pgdb.py list / copy <src> <dst> / drop <db>` (ldm_ databases only, copies the filestore too) |
| Baseline DB | `ldm_baseline`: the showcase exactly as received, with a few seeded records |
| Demo DB | `ldm_pro`: module installed on `ldm_tpl`, then `docs/ldm/tools/seed_all.py` (39 matters, 12 clients, 28 sessions, 22 deadlines; logins manager, lawyer, lawyer2, trainee, clerk, approver, auditor, billing, employee, password = login). `ldm_pro_base` is the clean install before seeding: reseed with `pgdb.py copy ldm_pro_base ldm_pro`, then the seed. |
| Demo URL | `http://localhost:8110/web/login` |
| Start | `.venv_odoo19\Scripts\python.exe odoo-19.0\odoo-bin -c odoo19_ldm.conf -d <db>` |
| Upgrade | `... -d <db> -u legal_department_management --stop-after-init --logfile=.odoo_logs_ldm/<name>.log` |
| Logs | `.odoo_logs_ldm/` (git-ignored) |
| Capture harness | `py -3.11 docs/ldm/tools/capture.py --db <db> --out docs/ldm/evidence/<round> --screens <json>` |
| Memory | about 8 GB of commit charge free: at most two Odoo processes and one browser at a time (Postgres fell over twice on this machine from commit exhaustion) |

Set `PYTHONIOENCODING=utf-8` when running `odoo-bin` from bash, or Arabic
module names crash the console logger (harmless, but noisy).

## What has landed

| Commit | What |
|---|---|
| `ccebae7` | The showcase imported unchanged, as the baseline every change diffs against |
| `175f610` | State document, capture harness, baseline screens |
| `2f1a381` | Six research documents and SPEC.md |
| `485432c` | Foundation 19.0.7.0.0: every model and field, roles and rules, settings and presets, Iraqi calendar and deadline arithmetic, migrations, 35 tests; SAG-shaped upgrade 43/43 |

Baseline screens: `docs/ldm/evidence/00-baseline/` (eight screens, zero errors).

## Running now

- **Build streams** (five agents, each in its own git worktree and database;
  briefs in `docs/ldm/briefs/`, hand-backs in `docs/ldm/handback/`):
  G government (ldm_g, 8102) · L litigation and clocks (ldm_l, 8103) ·
  W workspace OWL (ldm_w, 8104) · M money (ldm_m, 8105) ·
  R registers and reports (ldm_r, 8106).

### Status (updated 24 Sep, 22:10, after the machine shut down at 21:43)

- **All five streams merged into main** (`fb1cb1d`…`3c58758`) and integrated
  (`30bd574`): **337 tests green**, zero new warnings on a fresh install, and the
  SAG-shaped upgrade passes every check (`docs/ldm/evidence/04-integration/`).
  Published to SAG's repository, branch `professional-19.0.7` (25 commits).
- **Arabic catalogue landed**: `i18n/ar.po`, 2,552 entries, 0 empty,
  0 placeholder mismatches (`po_check.py`); Odoo loads it for `ar_001` with no
  warning. Translated in the session from compact sheets
  (`docs/ldm/tools/i18n_tsv.py`, sheets `c<n>.tsv` / `c<n>.ar.tsv` in
  `docs/ldm/i18n/work/`). The earlier translation workflow wrote nothing: its
  agents spent their time reading source for context and were interrupted.
- **Running now:** design pass, third run (one Opus agent in its own worktree,
  port 8107, db `ldm_d`). The first run stalled, the second was lost to the
  shutdown having written nothing; this one commits after every area and keeps
  a Progress section at the top of `docs/ldm/handback/design.md`. It must not
  touch `i18n/` or write `seed_all.py` (the session owns both).
- **Session, in parallel:** `docs/ldm/tools/seed_all.py` (one realistic Iraqi
  data set from the five stream seeds plus one user per role) and the demo
  instance `ldm_pro` on 8095.
- **Next:** merge the design pass; delta-translate its new strings (re-export,
  `po_split.py split` on the new entries, `i18n_tsv.py sheet/check`, merge);
  run `verify_round.py` with `docs/ldm/tools/verify_plan.json` (7 roles × 23
  screens × Arabic/English × 1440/390); fix; hand over.
- **Tests on main:** 0 failed, 0 errors of 342 (fresh install on a copy of
  `ldm_tpl`), no warnings. Commits `0da1cf6`, `916a158`, `05cbfab`.
- **First verification round on main** (`docs/ldm/evidence/06-verify-main/`,
  results only; its screenshots are in the screenshots folder): 252 captures.
  Recheck after the fixes (`06-verify-recheck/`): 96 Arabic captures of five
  roles, 0 with problems. Fixed and committed: court-stage rail labels were English
  (`ws_task.py` used the raw selection list); "Principal" and "Verified" each
  covered two legal meanings (guarantee field renamed "Applicant", statutory
  confidence "Verified in the law") and a few shared entries got Arabic that
  reads as both label and status; the module's daily jobs wrote English because
  crons run without a language (`models/ldm_cron.py` runs them in the legal
  team's language); the shipped matter types' steps had no Arabic because
  they are inline in the data file (`SHIPPED_STEPS_AR` +
  `data/ldm_template_translations.xml`); a manager's My Day opened on "me" with
  zeros (now on the whole department); the harness counted the "More" menu as
  a header button and had no retry for slow first loads.
  **Open, after the design merge:** several monthly retainer reminders for one
  matter fill a lawyer's overdue band (one row per instalment); consider one
  reminder per agreement, or billing as the recipient.
- **Server management:** `python docs/ldm/tools/demo.py start|stop|status`.
  `taskkill` from Git Bash can fail silently and leave two servers on one
  port answering at random; the script stops them by command line and checks.
- **If the machine goes down again:** the design agent's branch is
  `worktree-agent-<id>` under `.claude/worktrees/`; read the Progress section of
  its `docs/ldm/handback/design.md`, then dispatch a successor on the same
  branch rather than starting over.

Design direction (binding for every OWL screen): `docs/ldm/briefs/design-direction.md`
— an original identity around the mockup's intent (the owner: "don't copy it,
it is the idea"). A design pass after the merge applies it to every screen and
adds the analytics board and the dossier's service overview.

## Next, in order

1. Merge the five stream branches into main (the foundation pre-registered
   every stream file, so conflicts should be limited to hand-back requests).
2. Integration in the session: `i18n/ar.po` complete, demo data, demo users per
   role, final menu review, `ldm_pro` on port 8095.
3. Verification round: full suite, the SAG upgrade test, journeys J1-J8 as every
   role in Arabic and English at 1440 and 390 px, adversarial review; fix and
   verify again.
4. Hand over: URL, logins per role, what changed, open questions for SAG.

## How to re-run the checks

- Tests: `MSYS_NO_PATHCONV=1 odoo-bin -c odoo19_ldm.conf -d <db> -u legal_department_management --test-enable --test-tags /legal_department_management --stop-after-init --no-http`
- Upgrade test: `docs/ldm/tools/upgrade/` (seed with the old code via
  `odoo19_ldm_old.conf`, snapshot, `-u`, assert). `ldm_sag` is the seeded
  SAG-shaped database (keep it pristine; duplicate it for each run).
- Set `PYTHONUTF8=1` or Odoo's log file silently drops lines containing Arabic.
- Screens: `docs/ldm/tools/capture.py` with a screens JSON (look up real ids;
  test runs advance the sequences).

## Standing rules (short form)

- No Claude/Anthropic attribution in commits or files; the author is Silete1.
- Never stage `custom_addons/legal_office` (a parallel stream holds
  uncommitted work there) or any other stream's files.
- Subagents run on Opus or Sonnet, never Fable.
- A screen counts as verified when its screenshot has been looked at, not when
  the store looks right.
