# Build streams — common brief (read this first, then your stream's brief)

You are one of five engineers building `legal_department_management` 19.0.7.0.0
in parallel. The foundation is committed; you add one area on top of it.

## Read before you start
1. `docs/ldm/SPEC.md` — the product. **Section 14 overrides earlier sections.**
2. Your stream brief in `docs/ldm/briefs/` and the research documents it names.
3. The foundation code: `custom_addons/legal_department_management/models/`
   (`legal_task.py`, `base_*.py`, `res_company.py`), `security/`, `views/legal_task_views.xml`,
   `views/legal_menus.xml`, `tests/common.py`. Every model and field you need already exists;
   read the declarations before writing anything.
4. `.claude/skills/legal-suite-conventions/SKILL.md` — conventions and gotchas that have cost
   whole sessions (translations, kanban fields, `required=` in views, icons, Odoo 19 renames).

## Where you work
- You are in your **own git worktree** (find it with `git rev-parse --show-toplevel`). Work,
  build and commit **only there**. Never edit `C:\Users\Lenovo\Documents\odoo19` directly
  unless that *is* your worktree. Never push, never merge into main.
- Odoo source (shared, read-only): `C:\Users\Lenovo\Documents\odoo19\odoo-19.0`.
  Python: `C:\Users\Lenovo\Documents\odoo19\.venv_odoo19\Scripts\python.exe`.
- Create your own config file at `<worktree>/odoo19_ldm_<stream>.conf` (it is git-ignored):
  ```
  [options]
  addons_path = <worktree>\custom_addons,C:\Users\Lenovo\Documents\odoo19\odoo-19.0\addons
  data_dir = C:\Users\Lenovo\Documents\odoo19\.odoo_data_ldm
  db_host = 127.0.0.1
  db_port = 5432
  db_user = openpg
  db_password = openpgpwd
  admin_passwd = admin
  http_port = <your port>
  dbfilter = ^ldm_.*$
  workers = 0
  ```
- Your database: duplicate the template, then install:
  `odoo-bin db -c <conf> duplicate ldm_tpl ldm_<stream>` then
  `odoo-bin -c <conf> -d ldm_<stream> -i legal_department_management --stop-after-init --no-http --logfile=<file>`.
  The template has Iraq (IQD, `l10n_iq`), Arabic and English, HR, Invoicing. Admin is `admin`/`admin`.
- **Always** set `PYTHONIOENCODING=utf-8 PYTHONUTF8=1 MSYS_NO_PATHCONV=1` in bash, or Arabic log
  lines are dropped and `/legal_department_management` test tags become Windows paths.
- Tests: `odoo-bin -c <conf> -d ldm_<stream> -u legal_department_management --test-enable --test-tags /legal_department_management --stop-after-init --no-http --logfile=<file>`.
- **Memory is tight** (about 8 GB free, Postgres fell over twice on this machine from commit
  exhaustion). Run at most **one** Odoo process at a time; start a server only for screenshots and
  kill it straight after (`netstat -ano | grep :<port>` then `taskkill //PID <pid> //F`). If Postgres
  says "recovery mode", stop, wait two minutes and retry — it is memory, not your code.

## Ownership (hard rule)
- Edit **only the files your brief lists**. Every stream file already exists as a valid stub and is
  registered in the manifest, `models/__init__.py`, `wizards/__init__.py` and `tests/__init__.py`.
- Need more Python files? Import siblings from your stub (`from . import gov_obligations` inside
  `models/gov_government.py`). Need more tests? Import sibling test modules from your test stub.
  Need more XML? Put it in your existing view/data/report files.
- New models you add: their ACL rows go in **your** `security/ir.model.access-<stream>.csv`, their
  record rules in your data file.
- You may extend foundation models from your own files (`_inherit`), add fields there, override
  methods (calling `super()`), and extend foundation views **by inheritance** in your view file.
  Do not edit foundation files. If the foundation is wrong or missing something only it can fix,
  write it under "Requests to the foundation" in your hand-back and work around it.
- Do not touch any other module (never `custom_addons/legal_office`, where another stream has
  uncommitted work).

## Quality bar (checked by a reviewer after you)
- English source strings everywhere (Python `_()`, XML labels, OWL `_t`). No Arabic in source code
  except data records and comments; no emoji anywhere. The Arabic catalogue is produced at
  integration from your English strings, so write clear, short, human English.
- No inline `style=` in views, no `!important`, logical CSS only (`margin-inline-start`,
  `border-inline-start`, never left/right), `fa` icons with `title=` and `role="img"`.
- Kanban: every field a template reads is declared. OWL expressions are JavaScript (`&&`).
- Odoo `groups=` is an OR. To show something only for a role **and** a feature switch, nest it
  (feature on the parent, role on the child) or use a computed boolean (see
  `legal.task.ldm_can_decide`). Never use `base.group_no_one` as "advanced".
- No view-level `required=` on workflow-conditional fields; enforce in Python at the transition.
- Money is `Monetary` with a currency. Dates use `fields.Date.context_today`. Statutory periods use
  `res.company.ldm_statutory_dates` (calendar days, last day rolled); step offsets use
  `res.company.ldm_add_working_days`.
- Security: the auditor never gets a mutation affordance; check every button you add has the right
  `groups=` **and** is fenced in Python.
- Screen budgets (SPEC §1 and §14.8): ≤ 2 visible primary buttons, ≤ 6 default list columns,
  kanban cards ≤ 4 lines, largest text is text not a number, empty states name the next action.

## Tests
- Write tests for every behaviour you add in `tests/test_<stream>.py` (and siblings), tagged
  `@tagged("post_install", "-at_install", "ldm")`, building on `tests/common.py` (`LdmCase`).
- Test wizards through `default_get(...)` and `new({})` as well as `create`.
- Before handing back, run the **whole module suite**: it must end `0 failed, 0 error(s)`, and the
  install/upgrade log must have **zero new warnings** (the Postgres-version notice is the only
  accepted one).

## Visual verification (the owner judges by looking)
- Write `docs/ldm/tools/seed_<stream>.py` (an `odoo-bin shell` script) that creates realistic Iraqi
  demo data for your screens, including one user per role you need (use
  `with_context(no_reset_password=True)`, login = password for these local users) with `lang`
  `ar_001` and tz `Asia/Baghdad`.
- Start your server, capture with `py -3.11 docs/ldm/tools/capture.py --base http://127.0.0.1:<port>
  --db ldm_<stream> --login <user> --password <pwd> --out docs/ldm/evidence/03-<stream> --screens <json>`
  (write your screens JSON under `docs/ldm/evidence/03-<stream>/screens.json`; look up real record
  ids, test runs advance the sequences). Capture every screen you built or changed, as each
  affected role, at 1440×900 (`--width 1440 --height 900`) and, for anything a runner or lawyer uses
  on a phone, at 390×844 with `--prefix m_`.
- **Open every screenshot with the Read tool and look at it.** Fix what is wrong (overlap, clipped
  text, wrong direction, empty panels, English where data should be, raw ids, `0.000` amounts) and
  capture again. A screen counts as verified only after you have looked at it. Labels will still be
  English at this stage (translations come at integration); that is expected.

## Commits and hand-back
- Commit small and logical in your worktree branch. Author is the repository's configured identity
  (Silete1); **no** `Co-Authored-By`, no "Generated with", no AI attribution of any kind. Messages
  say why, not what. Check `git show -s --format=fuller HEAD` before finishing.
- Finish by writing `docs/ldm/handback/<stream>.md`: what landed (by SPEC item), what did not and
  why, decisions you took, requests to the foundation, test count and result, the evidence list,
  and anything the integrator must know (cross-stream calls, data order). Commit it.
- If you spawn a sub-agent, pass `model: "sonnet"`.

## Cross-stream interfaces (already exist in the foundation; the owner replaces the body)
| Method | Owner | Used by |
|---|---|---|
| `legal.hearing.action_ldm_record_outcome()` → act_window of the outcome dialog | L | W (My Day, cockpit), L |
| `legal.task.action_ldm_record_outcome()` → outcome dialog of the next planned session | L | W |
| `legal.judgment.ldm_set_notified_date(date)` → sets `notified_date`; L generates deadlines on write | L | W (My Day inline date) |
| `legal.task.step.action_ldm_log_visit()` → act_window of the visit dialog | G | W (step checklist), G |
| `legal.task.ldm_conflict_check(names, task_id=False)` → `{"hits", "policy", "check_id"}` | M | W (quick create) |
| `legal.task.create_from_template(vals)` → id (foundation, keep its contract) | F | W, G (obligations), R (requests, letters) |
| `legal.task._ldm_reminder_items(company, today, horizon)` → extend with `super()` | F | L, G, R |
Streams must not rename these. If you need a new cross-stream call, add it on **your own** model with
a safe default and list it in your hand-back.
