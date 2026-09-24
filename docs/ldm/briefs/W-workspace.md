# Stream W — the workspace: OWL home, quick create, cockpit, dossier, palette, approvals, agenda

Port 8104 · database `ldm_w` · config `odoo19_ldm_w.conf`
Read: SPEC §5.1–5.5, §5.9, §14.3 (terminology), §14.4 (cockpit, widgets, menus, My Day, hand-over),
§14.8 (budgets as assertions); research **05 in full** (screens S1–S16, components, primitives,
keyboard map), 06 cards E1, E2, E4, and the owner's reference code at HEAD (read-only, port, never
depend): `custom_addons/legal_office/static/src/office/` (use `git show HEAD:<path>` — the working tree
there has another stream's uncommitted changes), `custom_addons/legal_procedure/static/src/components/`
(phase rail, checklist, clock badge), `custom_addons/legal_office/static/src/scss/legal_ds.scss`.
Odoo 19 web client source: `odoo-19.0/addons/web/static/src`.

## You own
`static/src/**` **except** `static/src/money/**`, `static/tests/**`, `models/ws_workspace.py`
(+ `models/ws_*.py`), `wizards/ws_wizards.py` (+ `wizards/ws_*.py`), `models/legal_task_wizard.py`
(SAG's quick-create wizard model: keep `_name = "legal.task.create.wizard"`),
`views/legal_task_wizard_views.xml` (keep `view_legal_task_create_wizard_form` and
`action_legal_task_create_wizard` as an act_window), `views/legal_dashboard_views.xml` (keep
`action_legal_dashboard` and the tag `legal_dashboard_tag`), `views/ws_views.xml`, `data/ws_data.xml`,
`security/ir.model.access-ws.csv`, `tests/test_ws.py` (+ siblings), `docs/ldm/tools/seed_ws.py`,
`docs/ldm/evidence/03-ws/`, `docs/ldm/handback/ws.md`. Delete SAG's `static/src/dashboard/*`
(redesign in place, never alongside).

## Build (OWL with Odoo 19 primitives: `setup()`, hooks, registries, `useService`, `Record`/`Field`,
`Dialog`, `useHotkey`, `useNavigation`; loading, empty and error states; keyboard access; no new JS
library; registry keys and CSS classes prefixed `ldm_` / `o_ldm`)
1. **Design tokens**: `static/src/scss/` — a small token set (spacing, radii, semantic colours per the
   suite's fixed colour meanings: danger overdue/rejected, warning due soon/missing, success done,
   info waiting on others), logical properties only, dark-mode safe, scoped to `.o_ldm`. An IQD
   formatter that shows whole dinars (0 decimals) for use in OWL.
2. **My Day** (client action on `legal_dashboard_tag`, SPEC S1 and §14.4): one server call
   `legal.task.get_my_day(scope)` (in `ws_workspace.py`, bounded, computed as the user, counts by
   `_read_group`) returning bands overdue / today / this week / later / no date; each row: subject,
   client · body, **reason** (`next_action`), relative date, one inline action (tick a step with
   Undo; record a session outcome via `action_ldm_record_outcome`; approve), click opens the matter;
   the 7-day agenda rail; approver chip; my open activities on legal records; clerk "by body" grouping
   of today's visit steps with the documents to carry; the runner's advance balance (`legal.advance`
   where state paid, user = me); manager bands: tomorrow's sessions with no lawyer, at the body past
   target (`legal.task._ldm_past_target_domain()` if present), conflicts awaiting decision
   (`legal.conflict.check` decision pending), judgments awaiting notification with an inline date
   (`legal.judgment.ldm_set_notified_date`). Empty bands are not drawn; "all clear" state names the next
   action. Keyboard: ↑/↓/Enter, `/` to search, Alt+Shift+N.
3. **Quick create** (redesign `legal.task.create.wizard` in place as a one-step dialog, SPEC S2 and
   §14.4): matter type picker widget with recents (`res.users.settings.ldm_recent_template_ids`),
   client, key date labelled by kind, suggested title; body shown as an input when the type has no
   default body and the kind is government or litigation; litigation adds our role, opponent and
   court; «More» holds responsible, team, urgent, note; office mode with billing adds an optional fee
   agreement (existing active one of the client, or a new draft); with the conflicts switch the
   create step calls `legal.task.ldm_conflict_check(names)` and shows hits in a banner that cannot be
   dismissed (pending → "send to a partner"). Creates through `create_from_template`; "Create and open"
   and "Create and add another"; a toast with what was generated. Opens with ≤ 4 visible editable
   fields. Every register's New and the client dossier's button open it.
4. **Cockpit** (`view_legal_task_form` by inheritance, js_class `ldm_matter_form`): an overflow
   dropdown that renders buttons with class `o_ldm_more`; the advanced toggle (remembered in
   `res.users.settings.ldm_show_advanced`) making the «More» group collapsible; view widgets
   `ldm_matter_vitals` (next date with days left, documents N of M, expenses, sessions, time in this
   status from `date_state_changed`), `ldm_next_step` (the next open item with its one action; the
   approval banner replaces it while pending), `ldm_phase_rail` (litigation court stages; no progress %
   there); x2many widgets `ldm_step_checklist` (whole row clickable, one click ticks with Undo, visit
   rows offer "Log visit") and `ldm_document_checklist` (per-row drop and camera input, state chips, a
   file dropped anywhere offered to the first missing document). Client label per mode (department
   words, office words, neutral) through duplicated label nodes with positive/negative `groups`.
5. **Client dossier** (`view_legal_company_form` by inheritance): `ldm_body_windows` — one card per body
   with open/done counts and next date, from `_read_group`, clicking opens the register filtered;
   "what is happening now" (5 most urgent open matters); primary "New matter for this client".
6. **Approvals inbox** (`action_legal_task_to_approve`): a list js_class with a read-only preview pane
   of the selected matter, inline Approve / Reject, bulk approve; columns: matter, type, client,
   requested by, waiting since, value.
7. **Agenda**: an OWL client action (new xmlid) grouping sessions, visit steps and deadlines by day for
   14 days, me / all, with "Month" opening the native session calendar and "Print roll" the hearing roll;
   repoint `menu_ldm_agenda` to it by redefining the menu record in `ws_views.xml`.
8. **Command palette**: a `command_provider` with namespace `#` for matter numbers and default results
   for matters, clients and bodies; commands "New matter" (Alt+Shift+N), "My Day", "Record session
   outcome" (Alt+Shift+H on a matter); server `legal.task.ldm_palette_search(term)` with Arabic
   normalisation under record rules, matching number, court case number, body reference, title,
   client, body, step and expense receipt numbers, correspondence numbers.
9. **Hand-over wizard** (`ws_wizards.py`): from user → to user, optional end date, scope checkboxes
   (responsible/team, open steps, planned sessions, open deadlines, activities, assigned requests);
   powers of attorney where the leaver is an agent listed as "new power of attorney needed"; one
   hand-over note per matter.
10. Step completion methods for the checklist (`legal.task.step.action_ldm_toggle_done`, with undo that
    also removes an expense the visit created in the same action) in `ws_workspace.py`.

## Acceptance (tests + screenshots)
- Python tests for `get_my_day` (per role, bounded, rules respected), palette search (Arabic variants,
  rules), the quick-create wizard through `default_get` + `new`, hand-over.
- Hoot tests (`static/tests/`) for the checklist tick/undo and the vitals rendering.
- Screens as clerk, lawyer, manager, approver and auditor at 1440 and 390: My Day (≥ 7 actionable rows
  for the lawyer with seed data; auditor sees no action buttons), quick create (government, lawsuit,
  office with fee agreement), cockpit (government and lawsuit; ≤ 2 visible primary buttons; next step,
  next date and responsible visible without scrolling), client dossier, approvals inbox with preview,
  agenda, palette open with results, hand-over dialog. Check no horizontal scroll at 390 px.
