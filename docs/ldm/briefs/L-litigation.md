# Stream L — litigation, sessions, judgments and Iraqi clocks

Port 8103 · database `ldm_l` · config `odoo19_ldm_l.conf`
Read: SPEC §4.5 (sessions, parties, judgments, rules, deadlines), §5.7, §5.8, §8, §14.1 (all of it),
§14.4 (court stages, hearings are court sessions only), §14.6 (substitution, licence classes);
research 03 §4 areas D–E and §6.1–6.3 (the master table of periods and how they are counted),
04 §4.6–4.8, 05 S8–S9, 06 cards B3, B4, C4, D1.

## You own
`models/lit_litigation.py` (+ `models/lit_*.py`), `wizards/lit_wizards.py` (+ `wizards/lit_*.py`),
`views/lit_views.xml`, `data/lit_data.xml`, `report/lit_reports.xml`,
`security/ir.model.access-lit.csv`, `tests/test_lit.py` (+ siblings), `docs/ldm/tools/seed_lit.py`,
`docs/ldm/evidence/03-lit/`, `docs/ldm/handback/lit.md`.

## Build
1. **Statutory periods as data** (`lit_data.xml`, `noupdate="1"`): every row of research 03 §6.2
   (CIV-1…12, CRM-1…4, ADM-1…5, LAB-1…2, EXE-1…5, TAX-4…5), with code, law, remedy, court degree,
   days/months, start event, cap, holiday roll, legal basis, source URL and confidence exactly as the
   research marks them (V → verified, S → secondary, U → unverified). Chains via `next_rule_id`
   (ADM-1 → ADM-2 → ADM-3/ADM-4); outcome-started rules via `trigger_outcome` (CIV-9 left for review,
   CIV-10 suspended, CIV-11 stayed). Views: list grouped by law, form showing basis and confidence.
2. **Deadline engine** on `legal.judgment` (`_ldm_generate_deadlines`, called from `create` and from
   `write` of `date`, `notified_date`, `pronounced_in_presence`, `law`, `court_degree`, `in_absentia`):
   choose the applicable rules (law, degree, in absence); civil periods need `notified_date` — without
   it create the deadline in state `awaiting_service` with no dates; criminal in-presence rules count
   from `date` (pronouncement). Dates come **only** from `res.company.ldm_statutory_dates` with the
   court's calendar (`legal.department._ldm_calendar`). Idempotent per (judgment, rule); changing a date
   recomputes open deadlines and posts what moved. Replace `ldm_set_notified_date` if you need more.
3. **Chains and lapse**: a daily cron marks open deadlines whose legal last day has passed as
   `missed`, notifies the responsible and the managers once (`escalated`), and for rules with
   `next_rule_id` and start `previous_deadline_end` creates the next deadline from the last day
   (silence counts as rejection). Marking a grievance deadline met starts the next one from that date.
4. **Session outcome dialog** (`legal.hearing.outcome.wizard`), replacing
   `legal.hearing.action_ldm_record_outcome`: outcome as big choice chips, attendance, next session
   date (required for adjourned and similar; creates the next planned session and links it), "needed
   before" line (creates an activity on the matter N working days before the next session), note; when
   the outcome is a judgment: date, result, law, degree, in presence, amount awarded, optional
   notification date → creates the judgment (deadlines follow); left for review / suspended / stayed →
   proposes the CIV-9/10/11 deadline. **One transaction**, one chatter line, ≤ 3 interactions from
   the cockpit for the common "adjourned to date X" case. Works at 390 px.
5. **Court stages**: creating a `legal.court.stage` line updates the matter's `court_stage` and
   `court_case_number`; a "Lodge challenge" action on a judgment opens the next stage line and marks the
   matching challenge deadline met; a judgment's `final_date` is set when all its challenge deadlines
   have lapsed unused. Views for stages and judgments (by inheritance on the cockpit's Case tab).
6. **Hearings**: list, form, calendar (month/week, colour by lawyer) and search views; an action for
   the native calendar that W's agenda can open; a warning when a trainee (`ldm_licence_class`) attends
   an appeal, cassation or felony court; `needs_substitution_letter` compute (attending lawyer not an
   agent on the matter's power of attorney, or a substitute partner set) with a warning when the POA
   does not allow substitution.
7. **Reports** (`lit_reports.xml`): the hearing roll (رول الجلسات) for a date range grouped by court and
   lawyer, with substitutes; the substitution letter (كتاب إنابة). `web.external_layout`, reader's
   language and direction.
8. **Holidays** (`legal.holiday`): list/form for managers; on create/write/unlink sync a global leave
   on the legal calendar (sudo), recompute open deadlines' legal last day and open steps' due dates in
   the affected range, and notify owners whose dates moved. Seed `legal.holiday` rows for the shipped
   2026–2027 holidays linked to the existing calendar leaves (`leave_id`), and a December cron that
   reminds legal managers to review next year's holidays.
9. Extend `_ldm_reminder_items`: tomorrow's sessions with no attending lawyer go to the managers;
   deadline escalation as above.

## Acceptance (tests + screenshots)
- Hand-computed dates for every seeded rule from a fixed event date, including service on
  Thu 2026-10-01 + 15 days → act by Fri 16 Oct, legal last day Sun 18 Oct; a last day in Eid moves
  after Eid; criminal cassation counts from pronouncement.
- Judgment without notification → one `awaiting_service` deadline without dates; writing the date
  computes it; changing it moves it.
- Chains ADM-1 → ADM-2 → ADM-3 and the missed-deadline cron (idempotent, escalates once).
- The outcome dialog through `default_get` + `new`, adjourned case in one transaction.
- Adding a holiday on a deadline's last day moves it and notifies.
- Screens: lawsuit cockpit Case tab with stages, judgments and deadlines; outcome dialog (desktop and
  390 px); hearing calendar; statutory periods list; hearing roll PDF (render `/report/html/...` and
  screenshot it); holidays list.
