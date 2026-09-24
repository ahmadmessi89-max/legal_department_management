# Hand-back — the design pass

Worktree `.claude/worktrees/agent-a081540adc52909df`, branch `worktree-agent-a081540adc52909df`,
built on main `4cb858d`. Port 8107, database `ldm_d` (duplicated from `ldm_tpl`), config
`odoo19_ldm_design.conf` (git-ignored). Helper `ldm_odoo.sh` in the worktree root (git-ignored)
runs `odoo-bin` with that config: `bash ldm_odoo.sh -d ldm_d -u legal_department_management ...`,
`bash ldm_odoo.sh db ...`, `bash ldm_odoo.sh shell ldm_d <script>`.

## Progress (updated with every commit)

- Done:
  - environment (config, `ldm_d` installed clean, seeded with the five stream seeds; backup `ldm_d_seed`);
  - shared view theme: `o_ldm_view` on every native arch root (104 views; calendars use
    js_class `ldm_calendar`), `static/src/scss/ldm_views.scss`, the `ldm_pill` status widget
    (all 47 `badge` widgets switched), ink top bar inside the Legal app (`core/ldm_app.js`),
    `o_ldm_ltr` moved into W's tokens.
  - service overview on the client form (`ldm_service_overview` widget, `models/ds_services.py`),
    first page of the company file, replacing G's plain coverage list; tests in `tests/test_design.py`;
  - reminders: summaries in the reader's language with "24 September" dates, a stable
    `mail.activity.ldm_reminder_key` per source, closing by key (L, G, M, R, W overrides moved
    to it; keyless legacy reminders adopted by text or same day); `ldm_time` widget so a
    session without an hour shows nothing instead of 00:00 (and the hour can be typed in the form);
  - matter kanban kind spine; matter list checked at 6 columns by a test.
  - analytics board (`action_ldm_analytics`, Reporting > Analytics; `models/ds_analytics.py`,
    `static/src/analytics/`), tests in `tests/test_design_analytics.py`;
  - merged main (Arabic catalogue, `seed_all.py`); `ldm_d` rebuilt with `seed_all.py`
    (users manager, lawyer, lawyer2, trainee, clerk, approver, auditor, billing, employee;
    password = login), backup `ldm_d_seed`;
  - round 1 of the manager screens looked at (47 screens); every status pill given the meaning
    of the design direction (draft grey, work in hand ink, waiting blue, due soon amber, overdue
    red, done green; registered letters, approved matters and verified documents carry the stamp);
    Odoo's purple empty-state picture and orange bins replaced.
- In progress: dialogs and role captures (lawyer, clerk, approver, auditor, billing), phones.
- Next, in order:
  6b. Settings page and client list/kanban polish.
  7. Reports and letters (fonts, RTL, whole-dinar helper, letterhead).
  8. Mobile pass at 390x844, evidence in `docs/ldm/evidence/05-design/`, full suite.

## What changed, per area

(filled as each area lands)

## Before and after

(filled with the evidence)

## Not delivered

(filled at the end)
