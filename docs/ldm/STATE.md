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

## Environment

| | |
|---|---|
| Config | `odoo19_ldm.conf` (git-ignored), port **8095**, `dbfilter ^ldm_.*$` |
| Postgres | shared `PostgreSQL_For_Odoo` cluster on **5432** (12.4), user `openpg` |
| Baseline DB | `ldm_baseline`: the showcase exactly as received, with a few seeded records |
| Working DB | `ldm_pro` (to be created from the rebuilt module) |
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
