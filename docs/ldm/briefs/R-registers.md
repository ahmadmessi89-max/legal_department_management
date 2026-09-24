# Stream R — registers and reports: powers of attorney, correspondence, letters, requests, opinions, guarantees, SAG's reports

Port 8106 · database `ldm_r` · config `odoo19_ldm_r.conf`
Read: SPEC §4.6, §5.10, §7, §14.2 (letter rendering), **§14.6 in full**, §14.4 (opinions);
research 01 §5.4 (the three SAG reports), 03 areas G, H, K, L, Q and §6.8, 04 areas K, Q,
06 cards C5, C6, C8, C9, D4, D5; the owner's correspondence code for patterns
(`custom_addons/legal_correspondence`, read-only).

## You own
`models/reg_registers.py` (+ `models/reg_*.py`), `wizards/reg_wizards.py` (+ `wizards/reg_*.py`),
`views/reg_views.xml`, `data/reg_data.xml`, `report/reg_reports.xml`, SAG's report files
`report/legal_company_report_templates.xml`, `report/legal_task_report_templates.xml`,
`report/legal_general_report_templates.xml` (keep every xmlid and `report_name`), SAG's report wizards
`models/legal_company_report_wizard.py`, `models/legal_general_report_wizard.py`,
`views/legal_company_report_wizard_views.xml`, `views/legal_general_report_wizard_views.xml` (keep
model names and xmlids), `security/ir.model.access-reg.csv`, `tests/test_reg.py` (+ siblings),
`docs/ldm/tools/seed_reg.py`, `docs/ldm/evidence/03-reg/`, `docs/ldm/handback/reg.md`.

## Build
1. **Powers of attorney**: list/kanban/form; daily cron marks expired and keeps one expiry deadline per
   power of attorney (`ldm_poa_warning_days`); revocation dialog (date, reason, state guarded with
   `engine_guard`); matters relying on a revoked or expired power of attorney are flagged; the
   "who can act for client X at body Y today" search (filter + action from the dossier); the
   authorisation (تخويل) type.
2. **Correspondence** (صادر / وارد): list by direction, form; registering allocates the number from a
   per-direction yearly `ir.sequence` (editable before registration, locked after); void with a reason,
   never delete once registered; reply due and instruction due create deadlines (working days);
   "Open matter from this letter" (quick create prefilled, linked); official letter report in the Iraqi
   format (العدد / التاريخ, addressee title from the body, reference to their letter from `reply_to_id`,
   signatory and title, copies to), printed in the letter's `lang`; register book report (date range,
   direction).
3. **Letter templates and documents**: a safe renderer — a flat dict of pre-computed, escaped strings
   (`matter_number`, `client`, `body`, `court_case_number`, `opponent`, `responsible`, `today`, …) with a
   `string.Formatter` that rejects `.` and `[` in field names; unknown placeholders stay literal; seed
   templates (letter to a body, notarial notice, general request, client update); "New document from
   template" on the matter in **every** mode, producing editable HTML and a PDF attached to the matter.
4. **Requests from other departments**: the requester app (`menu_ldm_requests_root`): a short form
   (what, kind of help, needed by, details, files) and "My requests" with status and the linked matter's
   status and next date (sudo computed, nothing else of the matter); the requester writes only name,
   description, needed_by and attachments, and only while new or returned; "Resubmit"; the legal team's
   triage queue (accept → quick create prefilled with a template chosen from `request_type`, return with
   reason, decline with reason); "Send result to requester" (copy chosen files, notify).
5. **Opinions**: `action_issue_opinion` for approvers/managers: yearly opinion number, `opinion_date`,
   question and opinion frozen through `engine_guard`, the opinion memo (مذكرة رأي قانوني) attached as
   PDF; "Issue revision" (`supersedes_id` / `superseded_by_id`); a register of issued opinions with
   full-text search on question and opinion.
6. **Letters of guarantee** (`group_ldm_corporate`): views, expiry deadlines 30 days ahead, extension and
   release actions (drafting the letter from a template).
7. **SAG's three reports, rewritten** (same xmlids and `report_name`s): client file (identifiers,
   matters by body, open items, expenses for managers), follow-up sheet (استمارة متابعة: matter, client,
   body, steps with ticks, documents, sessions and visits, expenses, space for counter remarks, a QR code
   back to the record), oversight report (grouping by client really implemented). `web.external_layout`,
   reader's language and direction, whole-dinar IQD. The report wizards become short: data passed as
   report `data` (never context), prefilled from the current selection or `active_domain`; the empty
   filter bug fixed (no matches prints nothing, not everything).
8. **Monthly status report** (موقف الدعاوى والمعاملات) with a date-range dialog: lawsuits for and
   against by count and value, matters opened and closed by kind, sessions held, judgments by result
   with amounts awarded, challenges pending, clocks missed, government transactions opened/closed/
   overdue by body, documents and powers of attorney expiring in 60 days; plus an exposure pivot action
   grouped by `our_role`.
9. Extend `_ldm_reminder_items` for powers of attorney, letters awaiting reply and guarantees.

## Acceptance (tests + screenshots)
- Tests: numbering continues per direction and year and is locked after registration; void not
  delete; a dotted or indexed placeholder is refused; requester write limits and state guards;
  request accept creates and links a matter; opinion issue freezes text and numbers; revocation flags
  matters; each SAG report renders for a real record (and the empty-filter case prints nothing).
- Screens: POA list and form (expiring chip), revocation dialog, correspondence list and form, official
  letter PDF, register book, requester app as a plain employee (form + my requests), triage queue,
  opinion issued with memo, guarantees list, the three SAG reports and the monthly report (render
  `/report/html/...` and screenshot).
