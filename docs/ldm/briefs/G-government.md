# Stream G — government transactions, bodies and courts, company records

Port 8102 · database `ldm_g` · config `odoo19_ldm_g.conf`
Read: SPEC §4.3, §4.5 (documents), §4.6 (company documents, document types, obligations), §5.6,
§9.2, §14.3 (government switch), §14.4 (visits are steps, waiting_on, target days), §14.6
(coverage, readiness); research 02 §5 (the 10 × 28 Iraqi service catalogue), 03 §4 areas C, I, J
and §6.5–6.7, 06 cards B1, B5, C3, C10, C11.

## You own
`models/gov_government.py` (+ `models/gov_*.py` you import from it), `wizards/gov_wizards.py`
(+ `wizards/gov_*.py`), `views/gov_views.xml`, `views/legal_department_views.xml` (SAG's file:
rewrite it, keep every record xmlid in it), `data/gov_data.xml`, `security/ir.model.access-gov.csv`,
`tests/test_gov.py` (+ siblings), `docs/ldm/tools/seed_gov.py`, `docs/ldm/evidence/03-gov/`,
`docs/ldm/handback/gov.md`.

## Build
1. **Bodies and courts screens** (rewrite `legal_department_views.xml`; keep `view_legal_ministry_*`,
   `view_legal_department_*`, `action_legal_ministry`, `action_legal_department`): flat department list
   with a search panel (ministry, kind), kind/degree/governorate filters; body form with kind, court
   degree, higher court, governorate, calendar, opening hours, map link, usual answer time, letter
   addressee, editable contacts, services (matter types), open matters stat button. A read-only
   directory view for `action_ldm_body_directory` (redefine the action with your views).
   Department pickers must find a body by its ministry's name too and show the ministry as secondary
   text (`_rec_names_search`, display name "Body · Ministry" when useful).
2. **Document types**: seed about 25 (research 03 §6.6) in `gov_data.xml` (`noupdate="1"`), with
   category and validity; list/form views.
3. **Documents to collect** (`legal.task.document`): state flow missing → received → verified
   ("confirmed genuine", صحة صدور) / expired / not needed; received date and expiry; taking a copy
   from the client's vault; a daily cron marks expired; setting a document to "waiting for
   verification" sets the matter's `waiting_on = verification`. Improve the foundation's Documents
   page by view inheritance (W will add a widget on top; keep field names stable).
4. **Counter visits** (a visit is a step with `is_visit`): replace `legal.task.step.action_ldm_log_visit`
   with a visit dialog (`legal.visit.wizard`): result (done / still pending / rejected), receipt
   number, fee and currency, photo of the receipt (file upload, `capture` friendly), next step and
   date, what the body is waiting for. One transaction: the step is updated (done if result done),
   **exactly one** expense line is created when a fee is given (category "government fee", linked to
   the step), `waiting_on` / `date_submitted` are set, and a chatter line is posted. Usable on a phone
   (390 px): big targets, few fields.
5. **Government matters**: `days_at_body` shown on the cockpit (inheritance), `target_days` fallback
   template → body, a search filter "At the body past target" and a method
   `legal.task._ldm_past_target_domain()` that W uses for the manager band.
6. **Company records** (behind `group_ldm_corporate`, in the client dossier by view inheritance):
   identifiers, the document vault (`legal.company.document`) with expiry states and a daily cron that
   keeps one `legal.deadline` (kind expiry, `legal_company_id`, no matter) per expiring document;
   recurring obligations (`legal.obligation`) with a daily idempotent cron that opens a matter through
   `create_from_template` `lead_days` before `next_date` and rolls `next_date`; list/form views.
7. **Coverage**: an `_auto = False` SQL view `legal.company.coverage` (company × matter types with a
   new `track_coverage` flag already on the template) showing for each pair the latest matter's state,
   last done date and whether it is due this year; a dossier tab and a grouped list with a "Start"
   button that opens the quick-create prefilled. Respect the jsonb/translate gotcha (SKILL.md).
8. **Readiness at a date**: a dialog — client, date, matter type used as a "document pack" — that
   lists each required document type and whether the vault holds one valid on that date.
9. **Iraqi reference library**: override `res.config.settings.action_ldm_load_reference_data`. Loads
   ministries and departments (research 02 §5, 03 §6.5), the Baghdad courts under the Supreme Judicial
   Council with degrees and higher courts, and one government-transaction matter type per service
   with its steps (working-day offsets, visits) and documents to collect. **Idempotent**, merges by
   code then by normalised Arabic name (`models/ldm_text.normalize`), never duplicates, never shipped
   as upgrade data. Show a notification with what was created and merged.
10. Extend `_ldm_reminder_items` for document and obligation expiries (activity type
    `ldm_activity_expiry`).

## Acceptance (tests + screenshots)
- A clerk logs a visit with a fee from a phone-width screen in ≤ 6 taps; exactly one expense line.
- The reference import run twice creates nothing the second time and merges into existing bodies
  whose names differ only by hamza/taa marbuta/spacing.
- A document expiring in 20 days creates one expiry deadline, and the cron is idempotent.
- The coverage list shows "not done this year" rows for a tracked service.
- Screens (1440 and 390 where relevant): body list, body form (court and government), directory as a
  clerk, the visit dialog, a government matter with documents and visits, dossier with vault and
  coverage, readiness dialog, obligations list.
