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
| `fb1cb1d`…`30bd574` | The five build streams (government, litigation, workspace, money, registers) merged and integrated |
| `07832f5` | The Arabic catalogue |
| `5f44a2c` | One demo data set for every role (`seed_all.py`) and the database helper |
| `0da1cf6`…`0af417c` | The first verification round and its fixes |
| `ecc4b88` | The design pass's structure (analytics board, service overview) |
| `d8350cb`, `3402976` | The ANU identity, reports in it, the analytics board in Arabic |
| `e36ff22` | Instalment reminders, one per agreement |
| `2fc459b`, `4ce5124` | Catalogue marks and check, harness robustness; initials that name the person |
| (this commit) | Final round, recheck, renewal title wording, hand-over |

Baseline screens: `docs/ldm/evidence/00-baseline/` (eight screens, zero errors).

## Running now

No agent. Briefs of the finished streams are in `docs/ldm/briefs/`, their
hand-backs in `docs/ldm/handback/`.

### Status (updated 25 Sep 2026, 12:00)

The work is complete for 19.0.7: every stream, the design pass's structure
and the ANU identity are on main, the final round is clean, and the hand-over
is written and published as a page. What remains is SAG's answers and the
next version.

- **The first screen as a dashboard with actions; sharp edges** (the owner, 25
  Sep: SAG's mockup opened on "a dashboard with actions ... things to press to
  take you places, see things", and ANU's style means "white, black and blue
  and the sharp edges", not anu.ltd's home page). My Day, redesigned in place
  (`models/ws_home.py`, `static/src/my_day/`): the black band with a blue edge
  (date, Hijri date, what is due, the search, a manager's scope); up to six
  **actions** per role, the first one primary (a lawyer: new matter, record a
  session with its count, write a letter, agenda, powers of attorney, clients;
  a clerk: today's visits, register a letter, bodies, advances; billing: to
  invoice, fee agreements, client money, time; an auditor: analytics, matters,
  registers, reports, nothing that creates); up to six **tiles**, each opening
  exactly what it counted (a band of the list, or the records); for managers
  and auditors, **where the open work is** by kind, lawyer (with the late part
  in red) and body, each bar opening its matters; then the work list and the
  next seven days. Every role now starts there (auditor and billing too; billing
  gets its money, not the team's court work); the auditor's approvals moved under
  Reports to keep seven top menus. Every edge in the module is square (tokens,
  buttons, pills, panels, tabs, avatars, chart bars); the primary is a solid
  blue block; anu.ltd's line network is gone from the bands. Contrast checked
  with axe-core: 0 violations. Evidence: `docs/ldm/evidence/09-home-dashboard/`
  (6 roles × Arabic/English × 1440/390: Arabic 12 of 12 clean; the English flags
  are Arabic data). Tests 380, 0 failed; SAG-shaped upgrade 43/43
  (`04-integration/upgrade_assert_home.txt`).
- **Two traps found on the way, fixed as a class**: a plain `_()` inside a
  helper function finds no language and returns English (ws_home uses
  `self.env._()`; a test checks every label in Arabic); an existing catalogue
  entry used for the first time from code lacks its `odoo-python` mark
  (`docs/ldm/tools/po_merge.py` now refreshes every entry's references and
  marks from a fresh export). And: an upgrade only adds a menu's groups, so a
  group is removed with `-group`.

- **Build streams** G, L, W, M and R merged (`fb1cb1d`…`3c58758`) and integrated
  (`30bd574`). The design agent was stopped after its structure was merged
  (`ecc4b88`: view scaffolding, analytics board, service overview, reminders by
  key, time widget). No agent is running.
- **Design: the ANU identity** (the owner, 24 Sep: the mockup-based look was
  "flat, no character"; it must follow anu.ltd with component-library finish).
  Binding brief `docs/ldm/briefs/design-anu.md` (supersedes
  `design-direction.md`). Landed in `d8350cb` and `3402976`: ANU tokens,
  self-hosted Inter Tight, Tajawal and Roboto Mono, native views dressed, the ink
  band with anu.ltd's line network, the floating control bar
  (`o_ldm_floatbar`), stat tiles, charts in one blue ramp, client monograms, and
  printed reports and letters in the same type. Work-in-progress captures:
  `docs/ldm/evidence/07-anu-wip/` (screenshots folder only, not committed).
- **Arabic**: `i18n/ar.po`, 2,658 entries, 0 empty, 0 placeholder mismatches,
  every code string marked `odoo-python`/`odoo-javascript`
  (`py -3.11 docs/ldm/tools/po_check.py`; a test checks the marks, because Odoo
  silently ignores an unmarked code entry and shows the English; two hand-added
  entries had that fault until 25 Sep).
- **Reminders** (`e36ff22`): due instalments of one fee agreement are one
  reminder per matter («أقساط مستحقة (4) منذ 1 يونيو»), and a reminder closes as
  soon as its instalments are invoiced, paid or waived. On `ldm_pro` six rows
  became two.
- **Tests**: 380, 0 failed, 0 errors, no warnings (on `ldm_t`, 25 Sep). The suite runs in the
  Asia/Baghdad timezone and in English explicitly, so it holds between midnight
  in Baghdad and midnight UTC.
- **First verification round** (`06-verify-main/`, results only) and its recheck
  (`06-verify-recheck/`, 96 Arabic captures of five roles, 0 problems): the
  fixes are listed in commits `0da1cf6`, `916a158`, `05cbfab`.
- **Final verification round** (`docs/ldm/evidence/08-verify-final/`): 25
  screens × seven roles and the administrator × Arabic/English × 1440/390 =
  264 screens. 0 failed, 0 error dialogs, 0 page or console errors, 0 English
  words on Arabic screens, 0 sideways scrolling on a phone, 0 budget breaches.
  87 flags, every one Arabic *data* on an English screen (names, bodies,
  amounts in ع.د, reminders stored in their recipient's language). The harness
  now accepts any loaded client (the administrator lands in Discuss), records a
  failed login and goes on, saves `results.json` after every user, puts each
  user's language back afterwards, and moves the mouse off the page before a
  screenshot (a tooltip from the last click had been caught in the picture).
- **Found by looking at the round and fixed** (`2fc459b`, `4ce5124`): two
  hand-added catalogue entries lacked the `odoo-python` mark, so the grouped
  reminder showed in English (a test now reads the catalogue as Odoo does);
  nearly every avatar and many client cards showed «ا», the first letter of a
  title or of the article (one rule, `ldm_text.initial`, for monograms and
  avatars; stored letter avatars are redrawn on upgrade and after a rename);
  «مديرية تنفيذ الكرخ» existed twice (the money seed filed it under the judicial
  council); two bodies' hours were in Arabic-Indic digits; the renewal title
  «جدّد … الخاص بـ…» could not agree with every document's gender (now
  «تجديد … — …»). Recheck: `08-verify-final-recheck/`, 36 screens, 0 flagged.
- **Hand-over**: `docs/ldm/HANDOVER.md`, and as a private page with
  before-and-after pictures whose link the owner holds (published 25 Sep; the
  page's source and images were built from the files named in this document). Screenshots of every stage, the final round included:
  `C:\Users\Lenovo\Documents\LDM Screenshots\`.
- **Demo**: `ldm_pro` on 8110, team in Arabic, upgraded to main.
- **Server management:** `python docs/ldm/tools/demo.py start|stop|status`.
  `taskkill` from Git Bash can fail silently and leave two servers on one
  port answering at random; the script stops them by command line and checks.

## Next, in order

1. SAG's answers to the five questions in `HANDOVER.md` (department, office or
   both; hourly billing and client money; the Bar's amounts; 2027 holidays;
   month names), then the settings they decide.
2. Next version: client money to the general ledger, Kurdistan Region bodies,
   PDF check on a server with wkhtmltopdf, Iraqi month names (أيلول).
3. When the owner decides: merge `professional-19.0.7` into SAG's `main` and
   upgrade their production database (backup and a copy first).

## How to re-run the checks

- Tests: `MSYS_NO_PATHCONV=1 PYTHONIOENCODING=utf-8 .venv_odoo19/Scripts/python.exe odoo-19.0/odoo-bin -c odoo19_ldm.conf -d ldm_t -u legal_department_management --test-enable --test-tags /legal_department_management --stop-after-init --http-port=8198 --log-level=test` (give a spare port: with `--no-http` the run still answered on 8110 next to the demo server)
- Catalogue: `py -3.11 docs/ldm/tools/po_check.py` (`--fix` adds a missing code mark)
- New strings: `odoo-bin i18n export -c odoo19_ldm.conf -d <db> -l ar_001 -o docs/ldm/i18n/<delta>/export.po legal_department_management`, write `{English: Arabic}` for the new ones in `docs/ldm/i18n/<delta>/ar.json`, then `py -3.11 docs/ldm/tools/po_merge.py <export.po> <ar.json> --drop-unused` and `po_check.py`
- Verification round: `py -3.11 docs/ldm/tools/verify_round.py --db ldm_pro --plan docs/ldm/tools/verify_plan.json --out docs/ldm/evidence/<round> [--only lawyer] [--viewports 1440x900]`, then `verify_triage.py <round>/results.json`
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
