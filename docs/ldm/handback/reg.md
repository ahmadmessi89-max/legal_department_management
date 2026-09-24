# Hand-back — stream R: registers and reports

Branch `worktree-wf_f1763a7e-b6c-5`, built on the foundation `941a0be`.
Database `ldm_r`, port 8106, config `odoo19_ldm_reg.conf` (the brief says
`odoo19_ldm_r.conf`; the task said `_reg`, which is what exists).

## Result

- Full module suite: **0 failed, 0 error(s) of 96 tests** (35 foundation + 61 stream R),
  run both as a fresh install (`-i`, database duplicated from `ldm_tpl`) and as an
  upgrade (`-u`) over a seeded database.
- Install and upgrade logs: **no warning** apart from the Postgres-version notice.
- 63 screenshots in `docs/ldm/evidence/03-reg/`, every one opened and looked at; defects
  found that way were fixed and the screens captured again (see "What looking found").

## What landed, by brief item

| # | Item | Where |
|---|---|---|
| 1 | **Powers of attorney.** List (validity chips), kanban, form with the expiry warning and a scan upload box. Status moves only by date (expired / live again when the date is moved on) and by the **Revoke** dialog (date, reason); `state`, `revoked_date`, `revoke_reason` are refused outside `engine_guard` for everyone but superuser, and a revoked POA stays revoked. Daily cron (`ir_cron_ldm_register_expiry`) expires and keeps **one** open expiry deadline per POA inside `ldm_poa_warning_days`; renewal closes it (done), revocation cancels it. Revocation posts on every open matter relying on it and gives its responsible a to-do; the cockpit shows a red banner and Matters has a filter "Power of attorney not valid". "Who can act for client X at body Y today": search filter **Can act today** + **Valid before** (a POA with no bodies counts as valid everywhere) + agent search; the client dossier has a "Powers of attorney" stat button that opens the client's POAs with the filter on. The authorisation (تخويل) type hides the notary office. | `models/reg_poa.py`, `wizards/reg_poa_wizards.py` |
| 2 | **Correspondence.** List by direction (search panel) with the answer clock; form. **Register** takes the next number of the direction for the letter's year from a **no-gap** yearly sequence (`2026/1`, `2026/2`, then `2027/1`); a number typed before registration is kept, checked for duplicates in that book and year, and the book continues after it. Number, date and direction are locked after registration (a form re-saving unchanged values is not refused); status only through Register and **Void** (reason required); a registered or void letter cannot be deleted. Answer and instruction due dates are counted in **working days** (body calendar for outgoing, company calendar for incoming) and become deadlines (`reply`, `custom`), on the matter when there is one; registering a reply (`reply_to_id`) marks the original answered and closes its deadline; void cancels them. **Open a matter** from a letter (see decisions). Official letter report in the letter's language and direction: number and date, "your letter number … of …" from `reply_to_id`, addressee and the body's `addressee_title`, subject, greeting, body, closing, signatory and title, copies to. **Register book** report (period, one or both books, void entries struck through with the reason) from a list header button. | `models/reg_correspondence.py`, `wizards/reg_letter_wizards.py`, `report/reg_reports.xml` |
| 3 | **Letter templates and documents.** Safe renderer (`models/reg_render.py`): a flat dict of pre-computed, HTML-escaped strings; a `string.Formatter` subclass that refuses `.` and `[` in any field name (including inside format specs), prints unknown placeholders as written, ignores `!r` conversions, falls back to plain `{name}` substitution when the text has a stray brace; the template text itself is escaped. 29 placeholders, documented on the template form. Six seed templates (letter to a body, notarial notice, general request, update to the client, guarantee extension, guarantee release) with their **Arabic text**. **New document from a template** on the matter (Documents tab link and gear menu) in every mode: editable text in the dialog, then an outgoing draft letter linked to the matter with its printed copy filed among the matter's files. | `models/reg_render.py`, `data/reg_data.xml` |
| 4 | **Requests from other departments.** Requester app (existing `menu_ldm_requests_root`): list + kanban (phones get the kanban), a three-field form (what, kind of help, needed by) with details and files, status banners (returned with the reason, declined with the reason, accepted with the matter's number, status and next date — computed with sudo; the matter itself stays unreadable). The requester writes only name, description, needed-by and files, only on their own request and only while new or returned; state, matter, handler and reason are guarded; **Send again**. Legal side: triage queue (default "To handle"), **Take it**, **Accept** (opens the matter from the request with the type mapped from `request_type`), **Return** and **Decline** with a reason (reason dialog), **Send the result** (copies chosen files of the matter onto the request and notifies the requester). Clerks cannot triage. New requests notify the legal managers. | `models/reg_request.py`, `wizards/reg_request_wizards.py` |
| 5 | **Opinions.** `action_issue_opinion` (approvers and managers): yearly number from `legal.opinion` (no gap), `opinion_date`, `opinion_issued_by_id`, question/opinion/asking unit frozen (refused in `write` for everyone once issued), the opinion memo attached to the matter and to the chatter. **Revise opinion** (gear) creates a superseding revision (`supersedes_id` / `superseded_by_id`). Register "Legal opinions" under Registers with search in the question, the opinion and the title. | `models/reg_opinion.py` |
| 6 | **Letters of guarantee.** List (whole-dinar amounts), form with the 30-day warning; one deadline 30 days before expiry; cron expires; **Ask the bank to extend** (drafts the letter to the bank), **Record the extension** (new date, deadline closes), **Release** (date, optional letter to the beneficiary). | `models/reg_guarantee.py`, `wizards/reg_guarantee_wizard.py` |
| 7 | **SAG's three reports**, same xmlids and `report_name`s, rewritten on `web.external_layout`, in the reader's language and direction, whole-dinar IQD: follow-up sheet (facts, steps with boxes, documents, sessions and visits, expenses, notes only for those who may read them, six ruled "at the counter" rows, QR code to the matter embedded as an image), client file (identifiers, what is open and next, matters grouped by body with bodiless ones last, expenses only for managers/auditor/billing), oversight report (grouping by client really implemented). Dialogs are short, pass options as report **data**, prefill from the client (active id), from the Matters selection or from the whole filtered list (`active_domain`); **a filter that matches nothing prints "No matter matches these options."** (the old client file printed everything). | `report/legal_*`, `models/legal_*_report_wizard.py`, `models/reg_reports.py` |
| 8 | **Monthly status report** (dialog, previous month by default): lawsuits brought by / against us (open count, value of open claims per currency, opened and closed in the period), matters by kind, sessions held and still planned, judgments by result with amounts awarded, challenges pending, periods missed, government transactions by body (opened, done, open, past target), POAs and company documents expiring in 60 days. **Litigation exposure** pivot (our role × court stage, value). Both under Reporting. | `models/reg_reports.py`, `report/reg_reports.xml` |
| 9 | **Reminders** for POAs about to expire, letters waiting for an answer and guarantees about to expire, one per (record, person, kind, subject), idempotent, closed when the record is revoked/answered/released. | `models/reg_reminders.py` |

Tests (61): renderer and refusals, numbering per direction and year, typed numbers,
lock, void-not-delete, working-day clocks and their deadlines, answer closing the
clock, open matter from a letter, document from template in office mode, seed
translations, POA expiry/deadline/cron idempotence, guarded status, revocation
flags matters, who-can-act domain, scan upload, reminders once, requester write
limits and visibility, clerk cannot triage, accept creates and links a matter
(with the requester's files), return/resubmit, decline, send result, opinion
issue/freeze/numbering/revision/search, guarantee deadline/extension/release,
every report rendered for real records as the right users (billing cannot see
notes; the empty filter prints nothing; selection and select-all prefill), the
list header button called the way the web client calls it. The dialogs are tested
through `default_get` (and `new` where they compute from their source), as the client opens them.

## Decisions taken

1. **Opening a matter from a request or a letter uses a small dialog of this stream**
   (`legal.reg.matter.wizard`: type, client, title, one date, body, responsible) that
   calls `create_from_template` and links the result. W is rewriting the quick-create
   wizard in parallel and its field names were not known; a dialog that must link
   the matter back could not depend on them. The integrator may swap it for W's
   quick create later; the linking lives in `legal.request._ldm_link_matter(task)`
   and in the letter's `task_id`.
2. **Register reminders run next to the foundation's loop**, not inside
   `_ldm_reminder_items`: that loop reads `task.active`, `task.state` and
   `task.lawyer_id`, which a POA, a letter or a guarantee does not have. The stream
   overrides `_ldm_run_reminders` (calls `super()` first) and runs its own items
   through the same one-per-(record, user, type, summary) rule on the records
   themselves. Letters that belong to a matter are reminded through their deadline
   on the matter (the foundation already does that), so nothing is reminded twice.
3. **Documents are letters.** "New document from a template" creates an outgoing
   draft `legal.correspondence` (the editable HTML) and files the rendered copy on
   the matter. With the correspondence switch off the letter is simply never
   numbered (Register is hidden and refused), as SPEC §14.6 asks.
4. **PDF without wkhtmltopdf.** Filing a printed copy tries the PDF engine and falls
   back to the HTML rendering (attached as `.html`) when the server has none — this
   machine has none, so the local screenshots show `.html` files; on Odoo.sh the
   same code attaches PDFs. Report screenshots are the `/report/html/...` renders.
5. **Arabic seed-template text ships in the data file** (Arabic in data records is
   allowed), through `legal.letter.template._ldm_seed_translations(xmlid, …)`,
   called on install and on **every upgrade** (so SAG's upgrade gets it too), only
   where the template has no Arabic yet, skipping a deleted template.
6. **Uploads before the first save.** Odoo stores files uploaded on an unsaved record
   with no record id and lets only the uploader open them. Requests and letters
   re-home such files onto the record on create/write (`reg_common.adopt_attachments`),
   otherwise the legal team could not open what a requester attached.
7. **Request files are copied onto the matter**, not shared, so the matter's people
   (and billing) never need access to the requests register.
8. The **triage queue has no New button**: requests are written by the people asking,
   from their own app (the auditor, also an employee, still has "My requests").
9. **Letter number format** `YYYY/N` without padding, one book per direction, shared by
   all companies unless a company-specific sequence with the same code is added
   (it is then preferred). A typed number continues the chain only when it has the
   book's own format; any other format is kept as typed.
10. **Guarantee state has no engine guard** (the brief did not ask for one); its actions
    are fenced to lawyers.
11. Reports carry their stylesheet as a `<style>` block (`report_ldm_style`) because
    `static/src/` belongs to W; it uses no left/right and no logical properties either
    (wkhtmltopdf's engine ignores them): tables, `text-align: start/end`, symmetric padding.

## Requests to the foundation

1. `legal.task._ldm_run_reminders`: accept any `mail.activity.mixin` record in the items
   (use `getattr(record, 'active', True)`, a state check only when the record is a matter,
   and a responsible hook), so register items can join `_ldm_reminder_items`.
2. `legal.task.expense_account_id`, `account_move_id`, `account_payment_id`: mark them
   `copy=False` (the first is copyable). A lawyer without accounting rights cannot
   duplicate a matter today (`copy_data` reads the field); "Revise opinion" copies with
   sudo to work around it.
3. Register a report stylesheet (`web.report_assets_common`) under a path this stream can
   own, e.g. `static/src/reg/report.scss`, so `report_ldm_style` can move out of QWeb.
4. The matter-type form (W/G) should show `legal.task.template.request_type`
   ("Used for requests of kind"), under the requests switch. Seeds are set in
   `data/reg_data.xml`.
5. IQD in views: monetary fields show three decimals (Odoo's IQD rounding is 0.001).
   This stream uses `hide_trailing_zeros` on guarantee amounts; the pivot and other
   streams need the shared helper or the admin action of SPEC §14.3.
6. `legal.task.attachment_ids` and `legal.company.attachment_ids` (`many2many_binary`)
   have the same unsaved-upload problem as decision 6; `reg_common.adopt_attachments`
   can be reused.

## For the integrator

- **View anchors used** (by inheritance, applied after W's views because `reg_views.xml`
  loads last): on `view_legal_task_form` — `//field[@name='ldm_is_manager']`,
  `//header/field[@name='state']`, `//div[@name='button_box']`,
  `//div[hasclass('oe_title')]` (POA banner), `//page[@name='documents']/field[@name='attachment_ids']`,
  `//field[@name='question']`, `//field[@name='requesting_unit']`, `//field[@name='opinion_html']`,
  `//field[@name='opinion_date']`; on `view_legal_company_form` — `//div[@name='button_box']`;
  on `view_legal_task_search` — `//filter[@name='filter_confidential']`. If W replaces
  any of these nodes, adjust here.
- **Header buttons added to the cockpit:** "Issue opinion" (approvers, opinion matters
  not yet issued). With "Close matter" that is two. Gear: "New document from a template",
  "Revise opinion".
- **Actions redefined** (same xmlids as `ldm_actions.xml`): `action_ldm_poa` (path
  `powers-of-attorney`), `action_ldm_correspondence` (`correspondence`), `action_ldm_request`,
  `action_ldm_request_mine` (`legal-requests`), `action_ldm_letter_template`,
  `action_ldm_guarantee`, `action_legal_general_report_wizard`. New: `action_ldm_opinion_register`
  (`legal-opinions`), `action_ldm_monthly_report_wizard`, `action_ldm_exposure`,
  `action_ldm_client_file_wizard` (client gear), `action_ldm_oversight_from_matters`
  (Matters list gear). New menus: `menu_ldm_opinions`, `menu_ldm_monthly_report`, `menu_ldm_exposure`.
- **Changed on SAG's records:** report names are English now ("Follow-up sheet",
  "Client file", "Oversight report"); `action_report_legal_general_overview` moved from
  `legal.company` to `legal.task` (no binding either way); the two SAG paper formats keep
  their xmlids with Odoo's A4 letterhead margins (`default` is now False).
- **New fields on foundation models:** `legal.task.opinion_issued_by_id`, `ldm_poa_state`
  (related), `letter_count`, `opinion_memo_id`, `ldm_can_issue_opinion`;
  `legal.task.template.request_type`; `legal.correspondence.assigned_user_id`, `reply_days`,
  `reply_done`, `reply_state`, `instruction_days`, `guarantee_id`, `poa_id`, `party_display`;
  `legal.request.matter_*`, `date_submitted`; `legal.poa`/`legal.guarantee.scan`.
- **Deadlines created by this stream** carry `source_model`/`source_id` and kinds
  `expiry` (POA, guarantee), `reply`, `custom` (instruction). L's missed-deadline cron
  will treat them like any other.
- **Arabic for the report and letter terms** (for the `ar.po` pass; the letter prints in
  its own language):

| English source | Arabic |
|---|---|
| Number: / Date: | العدد: / التاريخ: |
| Your letter number … of … | كتابكم المرقم … في … |
| To: | إلى / |
| Subject: | م / |
| Greetings, | تحية طيبة وبعد، |
| With our regards. | مع التقدير. |
| Copies to: | نسخة منه إلى: |
| Follow-up sheet | استمارة متابعة |
| At the counter | لدى الجهة (ما تم في المراجعة) |
| Counter or office / Whom we met / What was said / Next step | الجهة أو الشباك / من قابلنا / ما قيل / الخطوة التالية |
| Client file | ملف الموكّل |
| Oversight report | تقرير الرقابة |
| Register book | سجل الصادر والوارد |
| Monthly status of lawsuits and transactions | موقف الدعاوى والمعاملات |
| Brought by us / Brought against us | دعاوى مقامة منا / دعاوى مقامة علينا |
| Challenges pending / Periods missed | طعون قيد النظر / مدد فائتة |
| Legal opinion memo | مذكرة رأي قانوني |
| Signature and stamp | التوقيع والختم |

## What looking found (fixed before hand-back)

The seed templates printed in English on an upgraded database (the translation call
sat in a `noupdate` block, which an upgrade skips); dates in report headers read
backwards in right-to-left pages ("31/12 – 01/01"), now "From … to …"; a void entry's
reason was struck through with it; signature lines sat at different heights; the
register-book button raised an error (a model method called with ids); the letter's
number and date sat on the wrong side; a new request showed "Sent" before being sent;
the requester's list was cramped on a phone (a kanban now); guarantee amounts showed
three decimals; the correspondence list had seven columns; the answer-due row wrapped
into three lines.

## Not done, and why

- **PDF output verified only as HTML** locally (no wkhtmltopdf on this machine). The
  templates use the letterhead layout and simple tables so they should print; check
  one PDF of each on the Odoo.sh build.
- **Report labels are English** until the integration `ar.po` pass (expected); the
  data (names, letter bodies) is Arabic.
- **Signatories with specimen signature and stamp images, the numbered subject table,
  QR verification tokens on letters, Hijri dates** (the owner's legal_correspondence has
  them): not in the brief; `signatory_id` / `signatory_title` / `cc_lines` cover v1.
- The POA "notarial notice" is a template and a letter; the revocation dialog does not
  draft it automatically.

## Evidence (`docs/ldm/evidence/03-reg/`)

Captured at 1440×900 (and 390×844 with `m_`) as each role, Arabic users, against
`ldm_r` seeded by `docs/ldm/tools/seed_reg.py`; each set has its `*metrics.json`
(no page errors, no error dialogs).

- `lawyer_01…17`: POA list, kanban, form (expiring), revoke dialog, client POA button,
  who-can-act, correspondence list, incoming and outgoing letters, official letter,
  register book, matter documents tab, POA-revoked banner, follow-up sheet, triage
  queue, request in review, accept dialog; `lawyer_18` new-document dialog with an
  Arabic template chosen (typed, captured by a small Playwright script);
  `lawyer_more_19…21` accepted request, send-result dialog, Matters filtered on invalid POAs.
- `employee_01…04` and `m_employee_01…04`: the requester app as a plain employee.
- `m_lawyer_01…04`: POAs, POA form, letter, triage queue on a phone.
- `manager_01…16`: issued opinion, register, memo, guarantees, guarantee form and
  extension dialog, client file, oversight, monthly report, exposure pivot, the three
  report dialogs, letter templates, template form and placeholders.
- `approver_01…04`: issued opinion, opinion ready to issue ("Issue opinion"), memo, register.
- `auditor_01…06`: POA, letter, request, opinions, guarantee, correspondence — no action buttons.
- `clerk_01…04`: draft letter with Register, register-book dialog, new letter, void dialog.

Reproduce: duplicate `ldm_tpl`, install, then
`odoo-bin shell -c odoo19_ldm_reg.conf -d ldm_r < docs/ldm/tools/seed_reg.py` (writes
`seed_ids.json`), start the server and run `docs/ldm/tools/capture.py` with the
`screens_*.json` files in the evidence folder (record ids there match a fresh seed).
