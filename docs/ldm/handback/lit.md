# Hand-back — stream L (litigation, sessions, judgments and Iraqi clocks)

Branch `worktree-wf_f1763a7e-b6c-2` (fast-forwarded to the foundation `941a0be` before any work:
the worktree had been created at `32e0104`, an ancestor of main that did not contain the
foundation). Database `ldm_l`, port 8103, config `odoo19_ldm_lit.conf` (git-ignored).

**Result:** full module suite `0 failed, 0 error(s) of 91 tests` (35 foundation + 56 litigation);
install and every upgrade log has no warning except the Postgres-version notice.
**Evidence:** 44 screenshots in `docs/ldm/evidence/03-lit/`, zero console errors, zero page errors,
zero error dialogs (six `*metrics.json` files), each one opened and looked at.

## What landed, by brief item

| # | Brief item | Where | State |
|---|---|---|---|
| 1 | Statutory periods as data | `data/lit_data.xml`, `models/lit_rules.py`, views | Done. 34 periods: every row of research 03 §6.2 named in the brief, with law, remedy, court degrees, length, start event, cap, holiday roll, basis, source URL and confidence as the research marks them. Chains ADM-1→ADM-2→ADM-3, ADM-4.1→ADM-4.2→ADM-4.3, EXE-3→EXE-4, TAX-4→TAX-5. Outcome-started: CIV-9 left for review, CIV-10 suspended, CIV-11 stayed (+ CIV-12 interrupted). List grouped by law (expanded), form with basis, source and confidence, a warning banner when not verified. |
| 2 | Deadline engine on `legal.judgment` | `models/lit_judgment.py`, `models/lit_deadline.py` | Done. `_ldm_generate_deadlines` from `create` and from `write` of date, notified date, presence, absence, law, degree, result, court. Rules chosen by law + court degree + presence; civil periods without service → `awaiting_service` with no dates; criminal in-presence periods count from pronouncement. Dates only from `res.company.ldm_statutory_dates` on the court's calendar. Idempotent per (judgment, rule); recounts open ones and posts what moved (old → new) on the matter to the people concerned; periods that no longer apply are cancelled. `ldm_set_notified_date` kept, now fenced to lawyers. |
| 3 | Chains and lapse | `models/lit_deadline.py`, cron `ir_cron_ldm_deadlines` | Done. Daily run: open deadlines past their legal last day → `missed`, one message to the responsible and the legal managers (`escalated` once); for a period whose next one starts at its end (the authority's time to answer) → `lapsed` and the next period starts from the last day (silence = rejection). Marking a period met starts the next one from that day, or leaves it waiting for the decision/notification date when the law counts from that. |
| 4 | Session outcome dialog | `wizards/lit_outcome_wizard.py`, view | Done. Replaces `legal.hearing.action_ldm_record_outcome`. Outcome chips (6 common + "Something else"), attendance chips, next session date (required for adjourned, pleadings, reserved, expert, witnesses) and time (defaults to the session's), a warning when the date is not a working day at that court, "needed before" → a to-do N working days before (default the company reminder days), note. Judgment: date, result, law, degree, in presence, in absence, amount, notification date, and a live preview of the periods it opens. Left for review / suspended / stayed / interrupted → the matching period, with its start (suspension: the end of the 3-month term). One transaction, one chatter line, a toast. Adjourned = open, pick a day, Save (3 interactions; the date field has focus on open). Works at 390 px. |
| 5 | Court stages | `models/lit_court_stage.py`, `models/lit_task.py`, `wizards/lit_challenge_wizard.py`, cockpit inheritance | Done. A stage line mirrors onto `court_stage` and `court_case_number` (number/year); those two become read-only on the matter once lines exist. "Lodge a challenge" on a judgment: dialog proposing the earliest open window, the higher court (`parent_id`) and the stage; marks the window met, closes the other open windows of that judgment, opens the stage line; refuses a challenge after the legal last day (Art. 171). `final_date` set by the daily run when every challenge window ended unused. An execution line with the notice date starts EXE-1. |
| 6 | Hearings | `models/lit_hearing.py`, views | Done. List, form, calendar (month/week, colour and filter by attending lawyer, Fridays/Saturdays/holidays shaded through `get_unusual_days`), kanban for phones, search. `action_ldm_hearing_calendar` (path `court-sessions`) for W's "Month". Trainee warning (banner + onchange) at appeal, cassation and felony courts. `needs_substitution_letter` and a warning when the power of attorney forbids delegation. |
| 7 | Reports | `report/lit_reports.xml`, `models/lit_report.py`, `wizards/lit_roll_wizard.py` | Done. Hearing roll (A4 landscape) for a date range or a selection: one table per court, rows grouped by the person who stands before it (a substitute counts), case, parties, purpose and room, what was needed from the previous session, substitution and licence notes. Substitution letter written as whole sentences in the reader's language. Both `web.external_layout`, reader's direction; records read under the user's rules. |
| 8 | Holidays | `models/lit_holiday.py`, data, views | Done. Manager list (grouped by year, editable) and form. Create/write/unlink keeps a global leave on the chosen calendar (sudo), recounts open rule deadlines whose last day the change can move, rolls open steps due on added days to the next working day, and tells the owners on their matters. 22 holidays for 2026–2027 seeded and linked to the foundation's leaves. December cron gives each legal manager one to-do to enter next year's holidays. |
| 9 | Reminders | `models/lit_task.py` | Done. `_ldm_reminder_items` adds: next working day's sessions with nobody attending → every manager; our open court deadlines ending by the next working day → the managers (T-1 escalation). Recording a session or closing a deadline closes its reminder activity. |

Acceptance tests (all in `tests/test_lit_*.py`): every seeded period from Thu 1 Oct 2026 against a
hand-computed table (incl. 15 d → act by Fri 16 Oct, legal last day Sun 18 Oct; 3 months → New
Year's Day 2027 → Sun 3 Jan); a last day in Eid moves after Eid; criminal cassation from
pronouncement; judgment without notification → one `awaiting_service` deadline, writing the date
counts it, changing it moves it and says so; chains ADM-1→2→3 (met, silence, explicit answer) and
EXE-3→4; missed escalated once and idempotent; the dialog through `default_get` + `new`, adjourned
in one step, nothing written on error, recorded once, clerk vs lawyer vs auditor; a holiday on a
deadline's last day moves it and notifies, moving/removing it gives the day back; December reminder
idempotent; stage mirror, challenge, late challenge refused; trainee and substitution checks;
roll grouping, record rules on the roll, both reports render.

## Decisions taken (documented judgement calls)

1. **Court degrees as tags.** Some periods cover three degrees (CIV-1: first instance, final degree,
   personal status), which the foundation's single `court_degree` cannot express. New model
   `legal.court.degree` (13 seeded rows) and `legal.appeal.rule.degree_ids` ("Judgments of", as SPEC
   §4.5 first allowed). The foundation field is still honoured if someone sets it.
2. **Research rows split where one row holds several periods:** CRM-2 → CRM-2.1 violation (added by
   hand: a court alone cannot tell a violation from a misdemeanour), 2.2 misdemeanour, 2.3 felony;
   ADM-4 (30 → 30 → 60 days) → ADM-4.1 grievance, 4.2 authority's answer, 4.3 suit.
3. **CIV-3 is proposed for judgments of the courts of appeal only**, following research §6.1 (a
   first-instance judgment is appealed within 15 days); its note says Art. 204 also names
   first-instance judgments and to add it by hand there. CIV-4 is marked *secondary* (research: V for
   the text, S for its reading); LAB-2 *unverified* (research: S/U).
4. **"Extends? no" in the research is the non-extendable badge, not the holiday roll** (otherwise the
   brief's own 15-day example could not roll to Sunday). New field `peremptory` ("Cannot be
   extended"); `extends_on_holiday` stays on for every period (the Civil Procedure Law is the general
   procedural law). The act-by date shown everywhere never rolls, so this is always conservative.
5. **Periods that are not ours to miss.** New `our_action` flag and state `lapsed` ("Ended unused",
   added with `selection_add`): a judgment in our favour opens the other side's windows (named
   "… (other side)"), the authority's 30 days to answer a grievance, the debtor's 7 days when we act
   for the creditor. They end `lapsed`, never `missed`, and never escalate.
6. **Short labels** for `verification` (Verified / Secondary / Unverified) and `start_event`
   (Notification, Pronouncement, …, End of the previous period): the long ones were cut to half a word
   in the list. Keys unchanged.
7. **The lapse cron applies to every open deadline, any stream's** (SPEC §8 says so). Holiday
   recounts touch only deadlines that follow a statutory period; deadlines other streams date by hand
   are left alone.
8. **Removing a holiday does not move steps back** (their working-day base is not stored); adding one
   rolls the steps due on it.
9. **`legal.holiday.name` made translatable** so the 22 shipped names can be translated at
   integration (the model is new in 19.0.7, no column to migrate). `legal.holiday` gains
   `mail.thread` + `mail.activity.mixin` for its history and the December to-do.
10. **Cockpit header:** "Record the session" appears only when a planned session's day has come
    (≤ 2 visible buttons with "Close matter"). W's next-step card may make it redundant; drop it at
    integration if so.
11. **`action_ldm_agenda` redefined** (next 14 days grouped by day, list/kanban/calendar) as the
    fallback until W's OWL agenda repoints `menu_ldm_agenda`.
12. **Report xmlid** `action_report_ldm_substitution` (not `…_substitution_letter`): the report's
    model table name would exceed PostgreSQL's 63 characters.
13. **Hearing roll menu** under Reporting is visible to managers only (the auditor has no wizard ACL,
    SPEC §3.3); the auditor prints the roll from the sessions list's Print menu.
14. The dialog **creates the proposed period with sudo** (a clerk records adjournments but may not
    create deadlines); only a lawyer may record a judgment.
15. Monetary fields in these views use `hide_trailing_zeros` (IQD has fils in the template); the
    shared whole-dinar helper is W's/the foundation's.

## Not done, and why

- **Client WhatsApp message in the outcome dialog** (SPEC §5.8): the `ldm_whatsapp` helper belongs to
  stream M and is not in this branch. Hook: extend `legal.hearing.outcome.wizard.action_confirm`.
- **Interruption halting running periods** (CCP Art. 84): CIV-12 is proposed, but open periods are not
  suspended automatically; a note on the rule says so.
- **Art. 216 decisions and execution decisions proposed automatically:** `legal.judgment` has no
  "decision vs judgment" flag, so CIV-5 and EXE-4 are added by hand or by chain (EXE-3→4).
- **Mobile dialog:** with the date focused on open, the phone shows the date picker first; picking a
  day is the common case (adjourned), other outcomes need one tap to close the picker.

## Requests to the foundation

1. Reminder summaries print raw ISO dates ("Court session on 2026-09-28"). Format them in the
   reader's language — and give reminders a stable key (e.g. the source model/id in the activity
   note) instead of matching text: `legal.hearing._ldm_close_reminders` and
   `legal.deadline._ldm_close_reminders` currently match the ISO date / deadline name in the summary.
2. A `ruling_type` (judgment / decision) on `legal.judgment` would let Art. 216 and execution
   decisions propose their periods (v1.1).
3. `legal.hearing.time` defaults to 0 and lists show "00:00"; consider leaving it empty until set.

## For the integrator

- **Calls other streams make:** `legal.hearing.action_ldm_record_outcome()` and
  `legal.task.action_ldm_record_outcome()` → act_window of `legal.hearing.outcome.wizard` with
  `default_hearing_id`; `legal.judgment.ldm_set_notified_date(date)` → True (lawyers only; My Day
  should offer the inline date to lawyers); `action_ldm_hearing_calendar` for the agenda's "Month";
  `action_report_ldm_hearing_roll` (docids, or `data` = date_from, date_to, user_ids, department_ids,
  include_held) and `action_ldm_hearing_roll_wizard` for "Print roll".
- **For M (money events):** judgments are created in `legal.judgment.create`; a session becomes held
  through `legal.hearing.write({'state': 'held', …})`; the first stage line in
  `legal.court.stage.create`; finality in `legal.judgment._ldm_update_final_date`.
- **For W (My Day):** deadline states now include `lapsed`; `our_action = False` marks the other
  side's windows; "awaiting notification" rows are deadlines in `awaiting_service`.
- **Data order:** `data/lit_data.xml` references the foundation's calendar leaves
  (`ldm_holiday_2026_01` …) and loads after `ldm_calendar_data.xml` (already so in the manifest).
- **New model** `legal.court.degree` (ACL in `security/ir.model.access-lit.csv`); three wizards with
  ACLs there too (no auditor access, no unlink below manager).
- **Translations:** every string is English source; sentences in messages and letters are whole
  `_()` strings with named placeholders.
- Seed for screens: `docs/ldm/tools/seed_lit.py` (`odoo-bin shell … < seed_lit.py`), users
  `lit_lawyer`, `lit_lawyer2`, `lit_trainee`, `lit_manager`, `lit_clerk`, `lit_auditor`
  (login = password, Arabic, Asia/Baghdad).

## Evidence (`docs/ldm/evidence/03-lit/`, 1440×900 unless marked)

Lawyer: `01`–`03` lawsuit cockpit Case tab (stages, judgments with "Lodge a challenge", deadlines,
parties), `04` Sessions tab, `05`–`08` outcome dialog (opened, date chosen, judgment with its
periods, left for review), `09`–`10` session calendar month and week, `11` trainee at the appeal
court, `12` agenda, `13`–`14` statutory periods list and form, `15` deadlines, `16` deadline form,
`17` judgment form, `18` challenge dialog.
Second lawyer (`l2_`): labour case sessions, substitution warning, the authority's answer period,
a judgment in our favour awaiting notification and its "other side" window.
Manager (`mgr_`): holidays list and form, roll dialog, hearing roll (`/report/html`), substitution
letter, missed deadlines, calendar of all lawyers.
Auditor (`aud_`): Case tab, Sessions tab, deadline and session forms — no action anywhere.
Clerk (`clk_`): Sessions tab and outcome dialog.
Phone 390×844 (`m_`): dialog opened / date chosen / judgment, Case tab cards, session form, agenda
and deadline cards, deadline form.
