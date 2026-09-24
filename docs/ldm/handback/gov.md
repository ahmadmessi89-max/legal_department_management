# Hand-back: stream G, government transactions, bodies and courts, company records

Branch `worktree-wf_f1763a7e-b6c-1`, built on the foundation commit `941a0be`.
Database `ldm_g`, port 8102, config `odoo19_ldm_gov.conf`.

## Result

- Full module suite: **0 failed, 0 error(s) of 104 tests** (35 from the foundation, 69 from this
  stream). It passes on a fresh database and again on the seeded one; the reference-library
  tests set aside any library records already in the database before they run.
- Install and upgrade logs: **no new warnings**. The only warning is the Postgres-version notice.
  Logs: `.odoo_logs/install2.log` (fresh install), `.odoo_logs/final_test.log`, `.odoo_logs/up8.log`.
- Journey J1 on a phone (390 × 844): a clerk logs a visit with a fee, a receipt number and a
  photo in **6 taps** (open the matter, Log visit, fee, receipt, photo, Save). Exactly one expense
  line is created and the receipt appears in the matter's history. The script is
  `docs/ldm/evidence/03-gov/j1_phone_visit.py` and its output is `j1_result.json`.

## What landed (by brief item and SPEC section)

1. **Bodies and courts** (SPEC 4.3, 5.6; research 06 B1/B3). I rewrote `legal_department_views.xml`
   and kept every xmlid. It has:
   - a flat list with a search panel (ministry, kind); filters for kind, degree and Baghdad;
     group-by ministry, kind, degree and governorate;
   - a body form with kind, court degree, higher court, governorate, calendar, opening hours,
     map link, usual answer time, letter addressee, an editable list of contacts (cards on a
     phone), services, the courts below, and stat buttons for open matters, all matters and
     services (the services button and the answer time are hidden for courts);
   - reworked ministry list and form.

   Search: `_rec_names_search = [name, code, ministry_id.name]`, plus a stored, normalised key
   (`ldm_search_key`). Every word typed must appear in the key, whatever the hamza, taa marbuta,
   alef maksura, spacing or definite article. The dropdown shows the ministry, and the
   governorate of a court, as muted secondary text through `formatted_display_name`. Everywhere
   else the display name is the body's own name.

   `action_ldm_body_directory` is redefined with read-only kanban, list and form views
   (priority 32) for everyone in the team: tap-to-call, a map link and contacts.
2. **Document types.** 30 types in `gov_data.xml` (`noupdate`), each with a code, category and
   validity (expiry date, fixed period, must be recent, none). The Arabic name is in a comment
   beside each record for the translation catalogue. There are list, form and search views; the
   foundation's action picks them up.
3. **Documents to collect** (`legal.task.document`, research 06 C3):
   - A new state, `awaiting_verification` ("Awaiting confirmation"), added with `selection_add`
     between received and verified.
   - Receiving fills the received date, and the expiry date for types valid for a fixed period.
     Uploading a scan (`file_data`) marks the document received.
   - Asking for confirmation of issuance (صحة صدور) sets the matter's `waiting_on = verification`
     and restarts its clock at the body. When nothing is waiting for confirmation any more, the
     matter goes back to `us`.
   - `verification_ref` and `verification_date` record the confirmation.
   - A document can be taken from the client's records (the valid copy that lasts longest; the
     file is copied onto the matter). The button shows only when the records hold such a copy
     (`ldm_in_vault`).
   - A lawyer can file a received document in the client's records.
   - A daily cron marks held documents expired and posts one note per matter.
   - The foundation's Documents page gets an improved list by inheritance (state chips, a scan
     column, row actions), phone cards, and a compact form. Field names are unchanged.
4. **Counter visits** (SPEC 5.8, 14.4): `legal.visit.wizard`. It asks for the result (done, still
   pending, rejected) as big badges, the fee in whole dinars, the receipt number, a receipt photo
   (`image/*`, so a phone offers the camera), the next step and date, and what the body is
   waiting for. A collapsed "More" section holds who the matter is waiting on, the date, the
   currency and a note.

   One confirmation does all of this:
   - updates the step: result, receipt, fee, photo, and done/done-by when the result is done;
   - moves a pending or rejected visit to its new date;
   - creates **exactly one** `legal.task.expense` when a fee is given (category "government fee",
     `step_id` set, the photo as receipt);
   - opens the follow-up visit when a next step or date is given;
   - sets `waiting_on` and `date_submitted` (the clock restarts whenever the file goes back to the
     body);
   - posts one history line.

   Where it opens from:
   - `legal.task.step.action_ldm_log_visit()` is replaced and opens the dialog (the interface
     name is unchanged);
   - the new `legal.task.action_ldm_log_visit()` logs the next planned visit, or an unplanned one;
   - a row button on visit steps in the cockpit, and a header button with class `o_ldm_more` for
     W's overflow menu.
5. **Government matters.**
   - `ldm_target_days`: the matter type's target, else the body's.
   - `ldm_body_due_date`: stored, counted in working days on the body's calendar from
     `date_submitted` while the file is with the body or awaiting confirmation.
   - `ldm_past_target`: a boolean you can search on.
   - **`legal.task._ldm_past_target_domain()`**, for W's managers' band on My Day.
   - An "At the body past target" filter.
   - Working days at the body and the expected answer date (red when late) on the cockpit, by
     inheritance.
6. **Company records** (behind `group_ldm_corporate`, research 06 C10/C11):
   - The dossier gets an "Expiring documents" stat button and three tabs: the document vault
     (with a "Valid on a date" button), obligations, and services this year.
   - `legal.company.document`: a list with state chips and a "Valid on a date" header button, a
     form with a scan upload, a search view, and the expiry date filled from the type's validity.
   - Expiry deadlines: each document that expires within the warning window keeps **exactly
     one** open `legal.deadline` (kind `expiry`, `legal_company_id` set, no matter,
     `source_model`/`source_id` set). The deadline follows date changes and is closed when the
     document is renewed, superseded by a newer copy, archived or deleted. A deadline that was
     already met or missed for the same expiry date is never reopened. This happens on
     create/write and in a daily, idempotent cron.
   - `legal.obligation`: a schedule check, `next_date` computed on creation (a short month uses
     its last day), `open_on`, and a responsible person. A daily cron opens the matter through
     `create_from_template` `lead_days` before the due date, **once per period** (keyed on
     `ldm_obligation_id` + `ldm_obligation_period`), then rolls `next_date` forward. It runs as
     the responsible user so record rules apply, and OdooBot never joins the team. There is an
     "Open the matter now" button, plus list, form and search views.
7. **Coverage** (`legal.company.coverage`, an `_auto = False` view): every company client ×
   every active matter type with `track_coverage`. For each pair it shows the latest matter and
   its state, the last done date, and "Done this year / In progress / Not done this year", where
   the year is Baghdad's calendar year. No translatable column is projected, so the view has no
   jsonb columns.

   Record rules follow the client's visibility, with a multi-company rule. There is a dossier
   tab, a grouped register list (menu *Registers › Services this year*, groups open), a "Start"
   button that opens the quick-create dialog with the client, type and body filled in, and an
   "Open" button for rows that have a matter.
8. **Readiness at a date** (`legal.readiness.wizard`, research 03 C10): a client, a date and a
   matter type used as the document pack; without a pack, every type the client holds. It lists
   each document as valid, expired by then, or not on file, with a one-line summary. It opens
   from the dossier and from the company documents list.
9. **Iraqi reference library** (SPEC 9.2, research 02 §5, 03 §6.1/6.5/6.6).
   `res.config.settings.action_ldm_load_reference_data` is overridden (legal manager or
   administrator only) and calls `legal.reference.library.ldm_load()`. The library loads:
   - 17 ministries, authorities and councils;
   - 22 government bodies;
   - 27 Baghdad courts and execution directorates, under the Supreme Judicial Council and the
     State Council, with degrees and higher courts;
   - 30 document types;
   - the 28 services of SAG's prototype, as government matter types with working-day steps,
     visits and documents to collect (English and Arabic names).

   The data lives in `models/gov_reference_data.py` and is never module data. Records are merged
   by code, then by normalised name (in both languages for types), and only empty fields are
   filled. A second run creates nothing. The Arabic translation of a merged document type or
   service is set only while it is missing. A sticky notification says what was added and what
   was already there.
10. **Reminders.**
    - `_ldm_reminder_items` is extended: documents on open matters that expire within the
        horizon, activity type `ldm_activity_expiry`.
    - Client-level reminders go through `legal.company._ldm_run_company_reminders()`, chained
        from `_ldm_run_reminders`. They cover vault documents and obligations that open no
        matter, with a new activity type `ldm_activity_company_expiry` (res_model
        `legal.company`), one per (client, person, subject). Summaries are in the reminded
        person's language.

## Decisions taken (please review)

- **Obligations and coverage sit behind the company-records switch**, as the brief says. SPEC 14.3
  also lists obligations under the government switch; the two switches coincide in every
  preset, so I followed the brief.
- **Logging a visit is not hidden when the government switch is off.** An execution file can
  carry a visit step on a Solo install. Once a visit step exists, its fee must be recordable.
- **Who has the file after a visit.**
  - Rejected: us.
  - Still pending: the body.
  - Done: the body while more visits are planned, otherwise us.
  - The user can change it under "More". Entering "the body" or "confirmation" from anything else
    restarts `date_submitted`, so the days at the body measure the current round.
- The visit dialog **does not change the matter's state** (in progress / waiting); only
  `waiting_on`. An automatic state change would surprise people and could conflict with other
  streams.
- A fee paid in another currency is stored on the expense in that currency and added to the
  step's fee converted to the matter's currency.
- The expense category is looked up with `legal.expense.category._ldm_government_fee()`: first
  xmlid `ldm_expense_category_government_fee`, then code `government_fee`/`gov_fee`/`GOV`; it is
  created only if none exists (see the request to M below).
- `ldm_body_due_date` is stored for searching. A holiday added later does not move it until the
  matter's date, target or body changes.
- The coverage year is Baghdad's calendar year. "Not done this year" means no done matter closed
  this year and none open. Individuals are excluded, since the services are company filings.
- The reference data writes Arabic **body and court names** (they are Arabic proper names, like
  SAG's own data). Opening hours are written in words ("من 8:00 إلى 14:00") because "08:00–14:00"
  is reordered in a right-to-left line. `models/gov_reference_data.py` is a data module; it is the
  only Python file with Arabic outside comments.
- **Matter-type views** (list, form, search for `legal.task.template`): no brief owned them, and
  bodies need a services editor. I added them in `gov_views.xml` with default priority. If W also
  ships template views, the integrator keeps one set.
- `legal.task.action_ldm_upload_to_document(document_id, name, data)` is a small server helper W's
  document checklist can call to attach a dropped file to one required document (it marks the
  document received).

## Requests to the foundation

1. `security/ir.model.access.csv` lines 2 and 4 give `group_legal_user` read, write and create on
   `legal.ministry` and `legal.department` (SAG's rows). SPEC 3.3 says lawyers read only and
   managers edit (research 01, S6). I did not change the ACL, which is not my file. The
   directory action is read-only for everyone anyway.
2. `_ldm_run_reminders` only accepts items that hang on a matter (it reads `task.state`). I
   chained a client-level pass from my override instead. A generic `(record, …)` item would let
   the registers stream reuse the pass for powers of attorney.
3. `ldm_activity_expiry` is typed to `legal.task`, so client-level reminders use my own type
   `ldm_activity_company_expiry`. The integrator may merge them.
4. `create_from_template` links the vault document's attachment itself, while "take from the
   records" copies it onto the matter. Copying is safer: a confidential vault document would
   otherwise make the matter's file unreadable to its team. Consider copying there too.
5. `create_from_template` reads the client as the calling user. A clerk who cannot read a client
   (by record rule) cannot open a matter for it. This affects W's quick create in J1.

## Requests to other streams

- **M (money):** give the seeded government-fee category the xmlid
  `legal_department_management.ldm_expense_category_government_fee`, or the code
  `government_fee`, so visits use it instead of creating one. The visit creates expenses without
  `paid_by` or `recoverable`, so M's defaults apply.
- **W (workspace):**
  - My Day can call `legal.task._ldm_past_target_domain()` and `legal.task.step.action_ldm_log_visit()`.
  - The cockpit's "Log visit" header button has class `o_ldm_more`.
  - The step checklist's Undo should remove the expense whose `step_id` is the step, if it was
    created by the same visit.
  - The document checklist can use `ldm_in_vault`, `action_ldm_take_from_vault`,
    `action_ldm_request_verification`, `action_ldm_mark_verified` and
    `action_ldm_upload_to_document`.
  - Right-to-left layout: numbers separated by spaces (phones, "08:00–14:00") are reordered in RTL
    cells. A shared `unicode-bidi: plaintext` or `dir="ltr"` on phone and number cells would fix
    it for data users type.
- **L (litigation):** vault deadlines are created with explicit `date_safe` and `date_deadline`,
  kind `expiry`, and no rule or matter. The deadline engine should leave them as they are (L's
  "missed" marking is fine; the vault never reopens a missed one).

## Not done

- The full procedure content of the owner's `legal_iq_*` packs (phases, transitions, fee rules,
  obligations, calendars). Only the 28 services became step templates.
- SLA escalation per body (research 03 C7). The past-target filter and domain are the basis for
  it.
- Batch creation of one matter per client (research 03 C9, SPEC 14.6 "S2 may create one matter
  per selected client"): that belongs to W's quick create.
- Kurdistan Region bodies and courts.
- Translations: English source everywhere, as briefed. The Arabic names of the 30 document types
  are in XML comments for the catalogue.

## Integrator notes

- Data order has no cross-stream dependency: `gov_data.xml` (document types, activity type,
  crons, coverage rules) loads after `ldm_rules.xml`; `gov_views.xml` loads after the menus. It
  adds `menu_ldm_coverage` under Registers and redefines `action_ldm_body_directory`,
  `action_ldm_company_document` and `action_ldm_obligation`.
- New stored columns on existing tables (`legal_department.ldm_search_key`,
  `legal_ministry.ldm_search_key`, `legal_task.ldm_body_due_date`,
  `legal_company_document.category`) are computed at upgrade. SAG's data is small; no
  migration step is needed.
- Upgrading over SAG data needs nothing from this stream. The library is opt-in; the test
  `test_sag_courts_are_classified_and_linked` shows it classifies SAG's "محكمة بداءة الكرخ" as a
  first-instance court under the Karkh appeal court.
- The local seed is `docs/ldm/tools/seed_gov.py`:
  `odoo-bin shell -c odoo19_ldm_gov.conf -d ldm_g < docs/ldm/tools/seed_gov.py`. It is safe to
  run twice. Users are `gov_clerk`, `gov_lawyer`, `gov_manager` and `gov_auditor` (password =
  login, Arabic, Asia/Baghdad), plus `admin`/`admin` as legal manager. It also turns off
  OdooBot's onboarding chat for these users, because on a phone it opens over the screen.
- Seeded records on `ldm_g`: matters 1 (tax clearance, 13 working days at the body, second visit
  pending), 2 (chamber ID, one paper awaiting confirmation), 3 (final accounts, done this year),
  4 (vehicle registration, visit logged by J1), 5 (import licence, past target); clients 1 to 3;
  tax body 3; Karkh first-instance court 26; service "tax clearance" 24.

## Evidence (`docs/ldm/evidence/03-gov/`, every image opened and checked)

At 1440 × 900:
- **Manager (`mgr_`):** 01 bodies list, 02 government body, 03 court, 04 ministries, 05 matter
  types, 05b a service with its steps, 06 document types, 07 obligations, 07b obligation form,
  08 company documents, 09 services this year.
- **Clerk (`clerk_`):** 20 directory (cards), 20b directory list, 21 directory body, 22
  government matter with visits, 23 its documents, 24 visit dialog.
- **Lawyer (`lawyer_`):** 30 dossier documents, 31 obligations, 32 services this year, 33
  readiness dialog, 34 matter past target, 35 matter awaiting confirmation.
- **Auditor (`auditor_`):** 50 matter documents and 51 dossier coverage. No row buttons, no Log
  visit, no Start.
- **Admin (`admin_`):** 40 the reference-library notification in Settings.

At 390 × 844:
- **Clerk (`m_clerk_`):** directory, directory body with contact cards, matter, document cards,
  one document opened, visit dialog.
- **Lawyer (`m_lawyer_`):** dossier documents, readiness dialog.
- **Journey J1 (`m_j1_1`–`m_j1_4`):** the phone visit, step by step.

Screen lists are `screens_*.json`; the harness results are in `*metrics.json` (0 failures, 0
error dialogs, 0 page errors).
