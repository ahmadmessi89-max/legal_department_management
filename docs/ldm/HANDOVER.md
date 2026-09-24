# legal_department_management 19.0.7.0.0 — hand-over

*25 September 2026. Written for the owner and for SAG Group's team. The same
hand-over also exists as a page with before-and-after pictures; the owner
shares its link.*

## What it is now

One Odoo 19 Community module that runs the whole working life of an
**in-house legal department** (قسم الشؤون القانونية) and of a **law office**
(مكتب المحاماة). One setting chooses between them, or runs both (a group legal
department that also bills its companies). It is an **in-place upgrade** of
the showcase SAG runs today: same technical name, same models and xmlids.
Nothing has to be reinstalled, and nothing already in the database is lost.

The design idea: everything is a **matter** (ملف) of a **kind**: a government
transaction, a lawsuit, an execution file, a contract, an opinion, a company
affair or an investigation. The kind decides what the screen shows. A
**matter type** fills in the steps, the documents to collect and the target
date, so opening a matter takes three to five answers. The day starts on
**مكتبي (My Day)**, which shows what is overdue, what is due today and what is
due this week, with one action per row. The Iraqi legal periods (appeal,
cassation, objection, execution, grievance) are data with their legal basis,
counted on a Sunday–Thursday calendar with official holidays rolled forward
(CCP Art. 25(2)).

## See it

| | |
|---|---|
| Address | `http://localhost:8110/web/login` (on the development machine) |
| Start / stop | `python docs/ldm/tools/demo.py start` · `stop` · `status` |
| Data | 39 matters, 12 clients, 28 court sessions, 22 deadlines, powers of attorney, letters, requests, fee agreements, client money: realistic Iraqi data, not SAG's |

One login per role (the password is the login):

| Login | Who | What they see first |
|---|---|---|
| `manager` | المستشار سعد الربيعي, legal manager | Everything; approvals, analysis, settings |
| `lawyer` | المحامية زينب الجبوري, lawyer (class A) | Her matters, sessions and deadlines on My Day |
| `lawyer2` | المحامي علي الساعدي, lawyer (class B) | His matters |
| `trainee` | المحامية المتمرنة نور علي | A trainee's view; she is warned off courts she may not appear before |
| `clerk` | حيدر عبد الأمير, clerk / runner | Today's counter visits, what to carry, his cash advance |
| `approver` | د. حسين كاظم | Matters waiting for his decision |
| `auditor` | نور الهدى السامرائي | Everything, read only |
| `billing` | مريم الحسني | Fee agreements, what is due to invoice, client money |
| `employee` | سارة محمود, another department | «طلباتي»: ask the legal team and follow the answer |

The interface is in Arabic by default. Every user can switch to English in
their preferences, and every screen works in both.

## What changed from the showcase

**The daily work**
- **مكتبي (My Day)**, a custom screen: overdue, today and this week, each row
  with its reason and one action (record the session outcome, log the visit,
  approve, save the notification date). Runners see today's counter visits by
  body with what to carry; managers see oversight counts.
- **New matter in one dialog**: type, client, body or court, and the key date.
  The type fills in the steps, the documents to collect and the target date.
  A conflict of interest, if any, is shown before the matter is created.
- **The matter as a cockpit**: where it stands, what is next and by when, who
  holds it, what it has cost. At most two buttons in the header, the rest under
  "More". Step and document checklists can be ticked in place, and a receipt
  photo can be dropped straight onto the missing document.
- **Agenda** of court sessions, counter visits and deadlines; the **Ctrl+K**
  palette finds a matter, a case number, a receipt or a letter by its number;
  an **approvals inbox** with a preview; a **hand-over** dialog for leave and
  departures.

**Government transactions**: a directory of ministries, bodies and courts with
opening hours, contacts and the services each offers (the Iraqi reference
library loads 17 ministries, 22 bodies, 27 courts and 28 services in one
click); counter visits with the fee, the receipt number and a photo; working
days at the body counted against its usual answer time; documents confirmed
genuine (صحة صدور); each company's document vault with expiry reminders;
recurring obligations (the annual tax return, the chamber ID) that open their
own matter before they fall due; a yearly coverage of the services each company
needs.

**Courts and deadlines**: 34 statutory periods as data, each with its law,
article, length, start event, holiday roll and confidence; the periods a
judgment opens are counted automatically from the notification date; chains
(grievance, then the authority's 30 days, then the court); the daily run marks
missed periods and tells the managers once; a session-outcome dialog in which
"adjourned" takes three clicks; court stages from first instance to execution;
a lodge-a-challenge dialog that refuses a late challenge (CCP Art. 171); the
hearing calendar; the Iraqi holidays for 2026–2027, where moving a holiday
recounts the deadlines it touches; the hearing roll and the substitution letter
(كتاب إنابة) as reports; a warning when a trainee is sent to a court they may
not appear before.

**Registers**: powers of attorney with expiry and revocation (the matters
relying on one are told); the correspondence register (الصادر والوارد) with
gap-free yearly numbers per book, working-day answer clocks and void-not-delete;
letter templates with safe placeholders; requests from other departments with
their own small app; legal opinions with yearly numbers, frozen once issued and
revised by a new version; letters of guarantee with the extension and release
letters drafted for you; SAG's three reports rebuilt (follow-up sheet, client
file, oversight), plus the monthly status of lawsuits and transactions and a
litigation exposure analysis.

**Money** (on when the office bills): expenses with receipt numbers, recharged
to the client where the law allows (Art. 55); runners' cash advances handed
over and settled against receipts; client money (أمانات) per client and
currency, which never goes below zero without a manager's reason; fee
agreements (lump sum, instalments tied to case events, success fee, retainer,
hourly) with the 20% cap of Art. 56 and the Bar's retainer minimum; "To
invoice" and one-step invoicing; the client statement; a time tracker; the
conflict-of-interest check (Arts. 44–45) with redacted results; ready-written
WhatsApp and email messages to clients; IQD shown in whole dinars.

**Security**: seven roles (manager, lawyer, clerk, approver, auditor, billing,
employee) with rules that hold through the API, not only on screens. Approvals
cannot be forged: an approver can only decide, and not on a matter they sent
themselves. Confidential matters stay with their team. Three holes in the
showcase are closed: approvals could be written directly, lawyers were granted
access through a hidden field, and administrators were made legal managers
implicitly.

**Language and look**: complete Iraqi legal Arabic (2,616 catalogue entries,
none empty) and English. The look follows ANU Software Solutions' own
identity (anu.ltd) with the finish of a professional component library
(shadcn/ui): ink bands that carry anu.ltd's line network, one electric-blue
accent for the action and the active thing, Tajawal for Arabic, Inter Tight
for Latin and Roboto Mono for numbers (all self-hosted), a control bar that
floats on the band as anu.ltd's navigation does, stat tiles, charts in one
blue ramp, and printed reports and letters in the same type. Every screen is
usable on a phone.

## How it was checked

- **Tests**: 370 automated tests, 0 failed, 0 errors, no warnings on install.
- **Upgrade**: 43 checks on a database built with the showcase's own code and
  shaped like SAG's, all passing (`docs/ldm/evidence/04-integration/`).
- **Every screen, as every role**: the final round opened 25 screens as seven
  roles and the administrator, in Arabic and English, at desk (1440 px) and
  phone (390 px) width: 264 screens. None failed or showed an error, no
  English word appeared on an Arabic screen, nothing scrolled sideways on a
  phone, and no form or list broke its budget of buttons and columns. The 87
  flags are all names and case data typed in Arabic, shown as typed on
  English screens (`docs/ldm/evidence/08-verify-final/`; recheck after the
  last fixes in `08-verify-final-recheck/`, 36 screens, none flagged).
- **Arabic**: 2,616 catalogue entries, none empty, placeholders intact, every
  code string readable by Odoo (`docs/ldm/tools/po_check.py`).

## Upgrading SAG's production database

The upgrade is `-u legal_department_management` on the existing database: no
reinstall and no data export. It was tested on a database built with the
showcase's own code and shaped like SAG's (ministries, departments, companies,
matters in every state): every record, number, attachment and follow-up
survived, and the old fields were carried into the new ones (43 checks, all
passing; `docs/ldm/evidence/04-integration/`). Take a backup first all the
same, and try it on a copy of production before production itself.

## Questions for SAG

1. **Department, office or both?** The demo runs "both". SAG's legal team is
   an in-house department; it only needs the money side if it bills its
   group companies.
2. **Hourly billing and client money**: are they wanted, or only fixed fees?
   (Both can stay switched off.)
3. **The Bar's amounts**: the monthly retainer minimums (order 3021 of 2021)
   are settings to confirm against the current figures.
4. **Official holidays**: the Eid dates for 2027 are estimates until the
   endowment offices announce them.
5. **Month names**: the interface uses Odoo's standard Arabic month names
   (سبتمبر). Iraqi names (أيلول) need a small language setup, planned next.

## Left for the next version

- Posting client money to the general ledger (it is tracked operationally now).
- Kurdistan Region bodies and procedures in the reference library.
- PDF output checked on a server with wkhtmltopdf (reports were verified as HTML
  here).
- Iraqi month names.
