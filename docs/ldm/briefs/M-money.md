# Stream M — money: expenses, advances, client money, fee agreements, invoicing, time, conflicts, client messages

Port 8105 · database `ldm_m` · config `odoo19_ldm_m.conf`
Read: SPEC §4.5 (expenses), §4.7, §14.2 (billing security, account field groups), **§14.5 in full**;
research 04 §6 areas A, B, G–J, L, N, O and §4.3–4.4, §4.9, §7, §8; 03 area N; 06 cards C12, F1, F2;
`docs/phase-2-engagements-and-conflicts.md` (the owner's conflict-check design).

## You own
`models/money_money.py` (+ `models/money_*.py`), `wizards/money_wizards.py` (+ `wizards/money_*.py`),
`views/money_views.xml`, `data/money_data.xml`, `report/money_reports.xml`, `static/src/money/**`
(the timer), `security/ir.model.access-money.csv`, `tests/test_money.py` (+ siblings),
`docs/ldm/tools/seed_money.py`, `docs/ldm/evidence/03-money/`, `docs/ldm/handback/money.md`.

## Build
1. **Expenses** (both modes): categories seeded (court fee, pension stamp, expert deposit,
   publication, notary fee, execution fee, government fee, transport, other) with recoverable
   defaults; list/form/pivot views and the matter's Expenses page improved by inheritance;
   `recoverable` default by mode and category; `paid_by = client_funds` writes one client-money
   disbursement line; `paid_by = employee` links an advance; with `group_ldm_accounting_links` an
   expense can be posted (journal entry or payment) and linked.
2. **Runner advances** (`legal.advance`): views, draft → handed over → settled, a settlement dialog
   (link the employee-paid expenses, cash returned), balance; `legal.advance.ldm_my_balance()` for My Day.
3. **Client money** (`legal.client.fund.line`): views; balance per client and currency (a stat button
   and a chip on the dossier and the matter); receive money / pay out actions; the balance can never go
   below zero without a manager's override and reason; an execution collection writes a line and
   fires the `collection` schedule event.
4. **Fee agreements** (`legal.engagement` + schedule lines): views; fee types; schedule lines with
   `trigger_event`; retainer lines generated on activation (12 monthly or 1 yearly), the Bar minimum
   warning by client kind (local / foreign branch); the 20% cap (fixed + success % × value of the
   linked non-criminal matters, converted to the agreement's currency; `law_branch` criminal exempt);
   activation over the cap needs a manager and `cap_override_reason`; signed flag and copy; printable
   fee agreement; the cockpit chip "no signed fee agreement" and a report of such matters;
   `ldm_engagement_required` warns when such a matter starts.
5. **Events**: fire schedule events from the workflow by extending foundation models in your files —
   signing, filing (first court stage line), first-instance judgment, final judgment, execution opened,
   collection, closing; `per_transaction` / `per_hearing` create due lines when a matter closes / a
   session is held; settling, withdrawing or the client ending the mandate proposes the remaining lines
   (extend `legal.task.decision.wizard` by inheritance: in billing mode show unbilled expenses,
   remaining schedule, balance due, client money held, originals held, linked power of attorney; waive
   needs a reason). Replace `legal.task._compute_billing_state` (billing state and invoices, sudo).
6. **Invoicing**: "To invoice" (due lines, unbilled billable time, recoverable expenses) grouped by
   client and currency, and `legal.invoice.wizard` creating one `account.move` (out_invoice) per
   client and currency with each source linked to its invoice line; `invoice_user_id` = the
   agreement's lawyer. Payments are Odoo's own; advances are unreconciled customer payments.
7. **Client statement** (كشف حساب) report per client and currency for a date range: invoices,
   payments, unbilled expenses, future schedule, client money held.
8. **Time**: views, a day sheet (editable list accepting 1.5 and 1:30), approval, and the systray
   **timer** in `static/src/money/` (start on the open matter, stop → confirm description and billable
   → a time entry; behind `group_ldm_time`).
9. **Conflict check**: implement `legal.task.ldm_conflict_check(names, task_id=False)` — Arabic
   normalisation (`models/ldm_text`), sources: clients including archived, parties and opponents on all
   matters including closed and archived, counterparties, `commercial_partner_id` expansion, active
   retainer clients (Advocacy Law Arts. 44–45); run with sudo and **redact** hits the checker may not
   read ("a matter handled by another team" + the responsible manager); record every check; decision
   pending / clear / accepted despite a match / declined, decided by a manager with a reason, immutable
   afterwards; a matter with a pending check cannot leave New; re-run when parties, opponent,
   counterparty or client change; a list for managers and auditors.
10. **Client messages** (`group_ldm_client_messages`): an `ldm_whatsapp` helper normalising Iraqi
    phones (07…, +964, 00964 → 964…) and building `wa.me` links; message templates (hearing result,
    hearing reminder, missing documents, instalment due, statement ready) as `legal.letter.template`
    records with `direction = client`, rendered in the partner's language; buttons on the session
    outcome result, the matter's overflow menu, the dossier and To-invoice lines; each use posts a
    chatter note.
11. **IQD display**: an admin-only settings action "Show IQD in whole dinars" (sets rounding to 1),
    available only when no posted accounting entry uses IQD.

## Acceptance (tests + screenshots)
- Tests: cap (mixed currency, several matters, criminal exempt, override), events create due lines,
  retainer generation, invoice lines linked back, statement totals per currency, client money never
  negative without override, advance settlement, conflict hits + redaction + pending blocks start +
  immutability, WhatsApp phone normalisation, billing and clerk can open billed matters without
  AccessError on accounting fields.
- Screens (office preset) as lawyer, billing and manager: fee agreement with schedule and cap
  warning, To invoice, invoice created, client statement PDF, client money with balance chip, advance
  settlement, time day sheet and timer, conflict banner + manager decision, close dialog in billing mode.
