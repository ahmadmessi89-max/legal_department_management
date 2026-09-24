# Hand-back — stream M (money)

Branch `worktree-wf_f1763a7e-b6c-4`, built on the foundation `941a0be`.
Database `ldm_m` (duplicated from `ldm_tpl`), port 8105, config `odoo19_ldm_money.conf`.

**Result:** the whole module suite ends `0 failed, 0 error(s) of 104 tests` (35 foundation + 69
money), on a fresh install and on the seeded demo database. Install and upgrade logs carry no
warning except the standing Postgres-version notice. Thirty screens were captured as lawyer,
billing, manager and runner, desktop and phone, and every one was looked at; the capture metrics
record no console error, page error or error dialog.

## What landed, by brief item

| # | Item | Where | Notes |
|---|---|---|---|
| 1 | **Expenses** | `models/money_expense.py`, views | Nine categories seeded (`ldm_expense_category_*`, noupdate). `recoverable` is computed and editable: false in department mode, false when paid from client money or by the client, else the category's default (transport is not recharged by default). `paid_by = client_funds` writes exactly one client-money disbursement and keeps it in step (amount, date, receipt, removal). `paid_by = employee` takes the employee's open advance automatically; a constraint keeps advance, employee and currency consistent. With `group_ldm_accounting_links` and invoicing rights, the expense form's "Post to accounting" (never offered to the auditor) posts a journal entry (category account against the cash/bank journal) or an outgoing payment and links it. List, form, kanban (phone), search, pivot, graph; the matter's page is renamed **Money**. Invoiced expenses and those settled against an advance are locked; only managers delete expenses (SPEC 14.2). |
| 2 | **Runner advances** | `money_advance.py`, settle wizard | Draft → handed over → settled. Only a legal manager or billing (the cashier) hands over and settles. The settlement dialog proposes the runner's unlinked employee-paid receipts and the cash to return; it refuses to settle while money is unaccounted for, and records "the office owes N" when the runner spent more. **`legal.advance.ldm_my_balance()`** for My Day. A handed-over advance is read-only to the runner. |
| 3 | **Client money** | `money_funds.py`, fund wizard | Balance per client and currency, computed over every line with sudo. It never goes below zero unless a legal manager gives a reason on the line; nobody else may write that reason. Deleting a deposit that would leave a hole is refused. Receive / pay out from the list (always-visible buttons) and from the dossier/matter. Stat button on the dossier and on the matter, chip on the Money tab. An **execution collection** fires the schedule's `collection` event (and, with a success % and no collection line, creates the success-fee line). |
| 4 | **Fee agreements** | `money_engagement.py` | Sequence `FA/YYYY/NNNN`. Fee types as declared. 20% cap: fixed fee + success % × Σ value of the linked **non-criminal** matters (`law_branch`), converted to the agreement's currency; exempt when all matters are criminal; switch `ldm_fee_cap_check`. Activation over the cap needs a legal manager **and** `cap_override_reason` — enforced in `write()`, so an RPC write obeys it too. Retainers generate 12 monthly lines (or one yearly line of 12 × the monthly fee) on activation and renew a year ahead from `retainer_next_date`. Bar minimum warning (local / foreign branch, company setting). Signed flag, signed date, uploaded scan (kept in `attachment_id`). Printable **fee agreement** (`action_report_ldm_engagement`, in the Print menu). Chip "No signed fee agreement" on the cockpit (billing switch) and a register *Money → Without a signed agreement* (Arts. 59, 65). With `ldm_engagement_required`, starting such a matter posts the Art. 65 warning and schedules "Fee agreement to sign", which closes itself once a signed agreement covers the matter. |
| 5 | **Events** | `money_task.py` | Signing (flag set on an active agreement, or on activation), filing (first court-stage line), first-instance judgment, final judgment (`final_date`), execution opened (execution court stage or `court_stage = execution`), collection, closing (matter done). `per_transaction` adds a due line when a matter closes, `per_hearing` when a session is held. The close dialog (inherited) shows, in billing mode: not invoiced yet, instalments still to come, what the client owes (accounting readers only), client money held, originals we hold, the power of attorney; for settled / withdrawn / client-revoked it proposes making the remaining lines due (Art. 58), otherwise keeping them; waiving needs a reason. `legal.task._compute_billing_state` replaced (billing state and invoices, sudo). |
| 6 | **Invoicing** | `money_billable.py`, invoice wizard, `money_account.py` | **To invoice** is an SQL view (`legal.billable`) over due instalments, approved billable time and confirmed recharged expenses, grouped by *client · currency*, overdue instalments in red. The wizard creates one draft `out_invoice` per client and currency, a section per matter when there are several, untaxed lines, `invoice_user_id` = the agreement's lawyer, and links every source to its invoice line (instalments and time marked invoiced). Cancelling or deleting the invoice frees the sources. Invoices remember their matters (`account.move.ldm_task_ids`). Payments and advances are Odoo's own (gear action "Receive a payment" on the client). The Bar's 5% on retainers is a negative line. |
| 7 | **Client statement** | `money_company._ldm_statement`, `report_ldm_statement` | Per currency from the receivable lines' `amount_currency`: opening balance, invoices and payments in the period, closing balance; then not invoiced yet, instalments still to come, client money held. Dialog asks for the period; "Tell the client" sends the *statement ready* message. Only accounting readers can print it (checked in the report model, so the URL is fenced too). |
| 8 | **Time** | `money_time.py`, `static/src/money/` | Day sheet: editable list opening on *mine + today*, `float_time` accepts `1.5` and `1:30`; approval by the matter's responsible (not their own time), a legal manager or billing; states change only through the workflow; invoiced time is locked. **Systray timer** behind `group_ldm_time`: starts on the open matter or one of the user's recent matters, runs on the server (survives reloads and devices), stops into a two-answer dialog (what was done, billable) with the time correctable. |
| 9 | **Conflict check** | `money_conflict.py` | `legal.task.ldm_conflict_check(names, task_id=False, client_id=False)` — see *Interfaces*. Arabic normalisation plus "عبد ال" joining; sources: clients incl. archived, parties on every matter incl. closed/archived, counterparties, the partner group (top company and all its branches, contacts, subsidiaries), active retainer clients. Sudo search, **redaction** for what the checker cannot open ("A matter handled by another team, responsible X"). Every check recorded (creation only through the check, never typed). Decision pending / clear / override / declined by a legal manager with a reason, final afterwards; `block` policy forbids the override. A pending or declined check keeps the matter in New (also through `create_from_template` and approval, where the matter is created and simply stays New). Re-run when parties, counterparty or client change. List for managers and auditors (Reporting → Conflict checks), banner on the cockpit, activity to the managers. |
| 10 | **Client messages** | `money_whatsapp.py`, `money_message.py`, message wizard | `normalize_iraqi_phone` (07…, +964, 00964, Arabic-Indic digits, trunk zero after +964) and `wa_link`. Five templates as `legal.letter.template` (`direction = client`, `ldm_code`), rendered in the client's language by a placeholder filler that only replaces bare `{name}` (no attribute or format access). Buttons: matter stat button (suggests session result / reminder / missing documents), dossier stat button, WhatsApp icon on the matter's Sessions list, on due instalments (agreement schedule and To invoice). Each WhatsApp use posts a note; email posts the message itself. |
| 11 | **IQD in whole dinars** | `money_settings.py` | Settings → Legal → Advanced, admin only, offered only while no posted entry uses IQD (checked again on click). |

## Not delivered, or delivered differently

- **The button on the session-outcome result** (L's dialog is not in this branch). I ship
  `legal.hearing.action_ldm_client_message()` and a WhatsApp column on the cockpit's Sessions list.
  **L or W:** call it from the outcome dialog's result.
- **The matter's overflow menu:** W's `o_ldm_more` dropdown is not in this branch, so "Message the
  client" is a stat button (on a phone it sits behind the lightning menu), keeping the header at two
  buttons. W can move it into the overflow.
- **Retainer auto-draft invoices** (SPEC 8, "with auto-draft on"): the daily cron makes dated
  instalments due and renews retainers; there is no auto-draft setting, billing creates the invoices
  from To invoice.
- **Client money posted to the general ledger:** v1.1 as SPEC 14.5 says (operational ledger only).
- **Awarded advocacy fees (Art. 56(2)), rate cards, split billing:** not in v1.
- **Statement by WhatsApp as a PDF:** click-to-chat cannot attach files; the dialog sends the
  "statement ready" text and billing shares the PDF.

## Decisions taken

1. **Conflicts versus "seen before".** Only a real conflict makes a check pending: the other side is
   (or was) our client, stood on our client's side, is a retainer client; or our new client was the
   other side of someone else's matter or contract. Meeting the same opponent again is recorded as
   "seen before" and does not block. Without this every repeat opponent (a ministry, a bank) would
   need a partner's decision.
2. **`client_id` added** to `ldm_conflict_check` (optional, safe default) because names alone do not
   say which side they are on.
3. **Adoption:** a check the same user ran within 30 minutes for the same names and client, not yet
   linked, is adopted by the matter instead of running twice (keeps a manager's decision taken in the
   quick-create dialog).
4. **`superseded`** added to the decision selection: a pending check is replaced only by a newer check
   whose names include all of its names; removing a name never clears a pending decision.
5. The redacted hit names **the matter's responsible** (the person to ask). SPEC 4.7 says "the
   responsible manager"; the phase-2 design says "the responsible lawyer". Revisit with the owner.
6. **The cap counts** the fixed part of lump-sum, instalment, consultation and success agreements
   (the larger of the agreed fee and the scheduled lines) plus the success percentage; retainer,
   per-transaction, per-hearing and hourly fees are not a fee on a matter's value and add only their
   success percentage.
7. A **retainer's amount is the monthly fee**; yearly billing is one line of twelve months.
8. **Instalments of a multi-matter agreement** that name no matter show without a matter in To
   invoice; the invoice is linked to all the agreement's matters. On a single-matter agreement they
   belong to that matter.
9. Shorter **"Paid by" labels** ("The office", "An employee's advance", "Client money we hold", "The
   client directly") by redefining the selection's labels; the keys are unchanged.
10. The **office preset** now switches on `ldm_engagement_required` (research 04 §8.2 row 4); other
    presets switch it off. Done by extending `_ldm_apply_preset` and the settings onchange.
11. **Start is hidden** on the cockpit while a conflict is pending or declined (the server refuses it
    anyway). Done by an attribute override on the foundation's first `action_set_in_progress` header
    button — **W: if you restructure the header, keep that condition.**
12. The Bar's 5% is a **negative invoice line** on retainer invoices, so the receivable clears at 95%.
13. The invoice dialog creates **drafts**; the date is set on the draft (no date field in the dialog).
14. Test companies in the conflict tests have their own names so demo data cannot sway the results.

## Requests to the foundation

1. `views/legal_task_views.xml`: add `ldm_conflict_state in ('pending', 'declined')` to Start's
   `invisible` so my positional xpath can go.
2. `security/ir.model.access.csv` gives lawyers `unlink` on `legal.task.expense`; SPEC 14.2 says
   managers only. I fence it in Python; the ACL could drop it.
3. `views/legal_menus.xml`: *Cash advances* is gated by the government switch; the solo preset loses
   it although solo lawyers also advance cash. Suggest gating on the clerk role.
4. `views/ldm_decision_wizard_views.xml` uses view-level `required="mode == 'close'"` on outcome
   (the conventions warn against view-level `required`).
5. `legal.engagement` has only the multi-company rule: every lawyer reads every fee agreement. The
   phase-2 design wanted a team rule (lawyer, team, managers, auditors).
6. The client form's phone field reads right-to-left digit groups in Arabic ("4567 123 0770"); add
   `class="o_ldm_ltr"` (my SCSS rule, marked `/*rtl:ignore*/`) or move the rule to W's tokens.

## Interfaces other streams can call

| Call | Returns / does |
|---|---|
| `legal.task.ldm_conflict_check(names, task_id=False, client_id=False)` | `{"hits": [{"label", "role", "role_code", "name", "conflict", "redacted", "responsible", "model", "id"}], "policy", "check_id", "decision", "conflict_count"}`. **W (quick create):** pass the opposing names and `client_id`; do not include the client's own name. The matter created afterwards adopts the check. A pending check keeps the matter New — `create_from_template` does not fail. |
| `legal.conflict.check.ldm_decide(decision, reason)` | Manager decision (`clear`, `override`, `declined`), for W's banner. |
| `legal.advance.ldm_my_balance()` | `{"count", "lines": [{"currency_id", "currency", "balance", "amount", "spent", "text"}], "text", "action"}` — My Day's runner chip (count 0 → draw nothing). |
| `legal.hearing.action_ldm_client_message()` | Message dialog: session result once held, reminder before. |
| `legal.task.action_ldm_message()` / `legal.company.action_ldm_message()` | Message dialog with a suggested template. |
| `legal.task._ldm_fire_fee_event(event, amount=None, currency=None)` | Makes the schedule's lines of that event due; L can call it if its flows bypass `court.stage` / `judgment` create. |
| `legal.company.ldm_money_summary()` | `{"funds", "unbilled", "engagements"}` texts for W's dossier panel. |
| `legal.task` fields | `ldm_conflict_state` (stored), `ldm_no_signed_agreement` (searchable), `ldm_fund_balance_text`, `ldm_unbilled_text`, `ldm_invoice_count`, `ldm_time_hours`, `ldm_can_message`. |
| Expense category xmlids | `legal_department_management.ldm_expense_category_government_fee` (**G:** use it for the visit fee's expense line), `…_court_fee`, `…_execution_fee`, etc. |
| Activity types | `ldm_activity_conflict`, `ldm_activity_fee_unsigned`, `ldm_activity_fee_agreement` (instalments due, via `_ldm_reminder_items`). |

Overrides to keep in mind when merging: `legal.task.write/create/create_from_template/action_approve/
_ldm_check_transition/_ldm_reminder_items/_compute_billing_state`, `legal.task.party.create/write`,
`legal.court.stage.create`, `legal.judgment.create/write`, `legal.hearing.create/write`,
`legal.task.decision.wizard.action_confirm`, `res.config.settings._ldm_apply_preset`,
`account.move.button_cancel/unlink`, `account.move.line.unlink`. All call `super()`.

## Integration notes

- **Arabic for data** (put in `ar.po`): the category names and the five message templates are
  translated in `docs/ldm/tools/seed_money.py` (`AR` and `MESSAGES`); use those texts.
- R builds a letter renderer; client messages use their own filler (`render_placeholders`). They can
  be unified at integration; the placeholders are the same style.
- The timer's state lives on `res.users.settings` as `ldm_timer_task_ref` / `ldm_timer_start`, both
  excluded from the settings sent to the browser.
- `legal.billable` is an SQL view with `_depends`; any new column on its sources needs the view
  updated, not a migration.
- Data order: nothing special; `money_data.xml` holds the To-invoice record rules (non-noupdate) and
  the seeded records (noupdate).

## Tests

`tests/test_money.py` imports `test_money_fees` (18), `test_money_invoice` (10), `test_money_funds`
(10), `test_money_conflict` (16), `test_money_misc` (15); shared base `test_money_common.py`.
Wizards are exercised through `default_get` and `new` as well as `create`.
Full suite: **0 failed, 0 error(s) of 104 tests** (`.odoo_logs/final3.log` in the worktree, git-ignored).

## Evidence — `docs/ldm/evidence/03-money/`

Seed: `docs/ldm/tools/seed_money.py` (users `money_lawyer`, `money_lawyer2`, `money_clerk`,
`money_billing`, `money_manager`; password = login; Arabic, Asia/Baghdad).

| Screen | Role | Shows |
|---|---|---|
| `l_engagement_cap` / `p_engagement_cap` | lawyer / manager | Agreement above the 20% cap; no Activate for the lawyer; the manager gets the reason field |
| `l_engagement_schedule` | lawyer | Schedule with invoiced, due and planned instalments; events made them due |
| `l_matter_money` | lawyer | Money tab: agreement, billing state, client money chip, expenses; stat buttons |
| `l_matter_unsigned` | lawyer | "No signed fee agreement" chip |
| `l_conflict_banner` / `p_conflict_banner` | lawyer / manager | Pending conflict banner, no Start |
| `p_conflict_decide` | manager | Decision dialog with the match |
| `p_conflict_checks` | manager | Register of every check |
| `l_day_sheet` | lawyer | Today's time, editable, total |
| `l_timer_menu` / `l_timer_stop` | lawyer | Running timer, stop dialog |
| `l_close_dialog` | lawyer | Close dialog in billing mode (settled → instalments due) |
| `l_client_message` | lawyer | Arabic session reminder ready for WhatsApp |
| `b_to_invoice` | billing | To invoice by client · currency, overdue in red |
| `b_invoice_wizard` | billing | Create invoices dialog |
| `b_invoice_sent` | billing | Posted invoice with a partial payment |
| `b_statement` | billing | Statement of account (per currency, unbilled, to come, client money) |
| `b_client_dossier` | billing | Client money, to invoice, balance due, fee agreements buttons |
| `b_client_money` | billing | Client money by client · currency |
| `b_advance_settle` | billing | Settlement dialog |
| `b_fee_agreements`, `b_fee_agreement_pdf` | billing | Register and printed agreement |
| `m_clerk_advance`, `m_clerk_expense_new`, `m_clerk_expenses` | runner, 390 px | Advance with receipt cards, new expense, expense cards |
| `m_lawyer_matter_money`, `m_lawyer_stat_menu`, `m_lawyer_client_message`, `m_lawyer_timer_menu` | lawyer, 390 px | Money tab cards, stat menu, message, timer |

Labels are English source at this stage (translations come at integration); data is Arabic.
