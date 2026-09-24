# 04 — What a law office needs (مكتب المحاماة)

**Stream:** research, document 04 of 6 · **Written:** 2026-09-24 · **Read-only research**. No code was changed.
**Question:** what does a law office need from practice-management software, globally and in Iraq? How
does each need map onto Odoo 19 Community? What *exactly* is different from an in-house legal department
(قسم الشؤون القانونية), expressed as configuration switches?

**Inputs read:** the showcase source (`custom_addons/legal_department_management`, commit `ccebae7`),
`docs/external-review/sag-legal-module.md`, `docs/legal-product-roadmap.md` §3–6,
`docs/phase-2-engagements-and-conflicts.md`, the React prototype's `types.ts`, the suite's
`legal_litigation` data (courts, appeal rules), the Odoo 19 Community addons tree in `odoo-19.0/addons`,
and the web sources listed in §11.

**How to read the tables.** **MUST** means an office cannot run on the product without it. **SHOULD** means
most offices will ask for it within the first months. **COULD** means it is valuable but deferrable.
*Default* is what a user sees with no extra setup (the calm, minimal screen). *Advanced* is what appears
only when it is switched on, when a "more" control is opened, or when the data calls for it
(progressive disclosure). *CE* means Odoo 19 Community. *EE* means Enterprise, which is **not
available** here.

---

## 1. Headline findings

1. **An Iraqi law office is not a US law firm.** Global products (Clio, MyCase, PracticePanther, Smokeball,
   CosmoLex) are built around **hourly time → invoice → IOLTA trust**. Iraqi practice is built around
   **a written fee contract (عقد أتعاب)**. That contract is usually a lump sum or a percentage, paid in
   **stage-linked instalments**. Beside it sit **monthly legal-adviser retainers for companies**, the
   **power of attorney (وكالة)** and the **hearing cycle** (جلسة ← تأجيل ← جلسة). Statute caps the fee at
   **20% of the value of the matter**, except in criminal cases (Advocacy Law 173/1965, Art. 56). The
   product must lead with contract, instalments, retainer, hearings and POA. Hourly time must stay
   available, but as an advanced option.
2. **Arabic-market products converge on one core feature set**, and it matches Iraqi practice more
   closely than the US products do. It has five parts:
   - a **daily hearing roster** (رول الجلسات);
   - **POA archiving with expiry warnings**;
   - **five-stage litigation**: first instance, appeal, cassation, execution;
   - **account statements (كشف حساب)** that combine fees, instalments, expenses and payments;
   - **WhatsApp/SMS reminders**.

   Mohamy Pro, Maktabi, Law Surface and CASENGINE all ship this core (§3.2).
3. **No Iraqi-specific practice-management product was found.** The Arabic products target Egypt and the
   GCC. The Iraqi judiciary's e-portal (`e-court.sjc.iq`) offers case tracking and a cassation-decision
   search, but no e-filing and no API. **Court data will be entered by hand**, so it must be fast to enter.
   The Iraqi data in §4 is a genuine differentiator.
4. **Deadline arithmetic is statutory and asymmetric.** Civil periods run from the day after **service
   (تبليغ)** of the judgment (Civil Procedure Law 83/1969, Arts. 171–172). Criminal cassation runs from
   the day after **pronouncement** (Criminal Procedure Law 23/1971, Art. 252). The periods are
   **peremptory (حتمية)**: missing one forfeits the remedy. That is why the tabligh date is the most
   important date in the product.
5. **Companies must retain a lawyer as legal adviser.** An Iraqi Bar Association administrative order
   (No. 3021, 11 April 2021) sets **minimum monthly fees of 300,000 IQD (local company) and 600,000 IQD
   (foreign company or branch)**. The fees are paid **a year in advance**. The company withholds **5%**
   and remits it to the Bar. This is almost certainly the backbone of SAG's own client book: client
   companies plus government transactions (§2). Recurring retainer invoicing is therefore a **MUST**. It
   has no Community equivalent (subscriptions are Enterprise).
6. **Money held for clients is not revenue.** Iraq has no IOLTA-style trust regime, but Art. 53 obliges the
   lawyer to return client funds and original documents on termination. Offices do hold client money:
   court fees, expert deposits, execution fees, and the 10% deposit for attachments. So the product needs
   a **client-funds liability account with a per-client ledger**, separate from **advance fee payments**.
   The Iraqi chart of accounts (`l10n_iq`) has **no such account**, and Community has **no partner-ledger
   report**. The module must create the account and build the ledger screen itself.
7. **Mixed IQD/USD is the norm.** The Central Bank of Iraq's official rate is 1,300 IQD per USD (banks sell
   at 1,310; end users pay 1,320). The street rate is about 1,478. The fee currency, the invoice currency
   and the payment currency can all differ, and the rate used must be recorded on each receipt. Odoo
   ships IQD **inactive with rounding 0.001**, which is wrong in practice. Live rates are Enterprise-only.
8. **The Iraqi profession has graded rights of audience.** A lawyer's licence (صلاحية) is one of
   **متمرن (trainee), أ, ب, ج, or مطلقة (unrestricted)**. The graduated path (التدرج) starts at (أ).
   Trainees may plead alone only in stated courts: in year 1, summary, personal-status and misdemeanour
   cases. Assigning a hearing should warn when it exceeds the assignee's licence.
9. **Conflicts are a statutory duty, not only an ethics rule.** Art. 44 bars representing opposing parties
   and extends the bar to the lawyers of the same office. Art. 45 bars a lawyer on an **annual retainer**
   from acting against that client during the term. The conflict check must therefore search
   **office-wide**, include **retainer clients**, and keep a record of every check (the Clio model).
10. **The showcase has almost none of this.** It has one `session_date`, one `expenses_amount`, and an
    optional link to one journal entry and one payment. It has no fee agreement, instalment, receivable,
    trust, time, conflict, POA, portal or client communication. `legal.company` has **no `partner_id`**,
    so it cannot be invoiced without a migration that creates partners (§9).
11. **Community covers the accounting spine.** `account` (with analytic, multi-currency, payment terms,
    cash rounding), `portal` (including a reusable **signature form**), `calendar`,
    `mail.activity.plan` (task templates) and `base_automation` are all CE. The EE gaps are timer/timesheet
    grid, subscriptions, follow-up, sign, documents, WhatsApp and financial reports. The module must build
    each one in OWL or Python.
12. **Office and department differ on about eight axes.** They are: who the client is, money billed out,
    client money held, time, conflicts, engagement/POA, client-facing channels and confidentiality
    between teams. Everything else is the same body of work. The difference is best expressed as **one
    mode plus about twenty switches, with five presets** (§8).

---

## 2. Starting point: what the showcase gives an office today

| Need | Showcase today (19.0.6.3.0) | Gap for an office |
|---|---|---|
| Client | `legal.company`: name, legal form, registration and tax numbers, contact fields, `lawyer_id`/`lawyer_ids`, `employee_ids`, attachments, computed counters, HTML "department cards" | No `res.partner` link, so no invoicing, no portal and no conflict matching. Company clients only: an individual client (فرد) cannot be recorded properly. |
| Matter | `legal.task`: title, company, ministry, department (courts are stored as departments under "مجلس القضاء الأعلى", as seen in baseline `05_task_form.png`), 5-state workflow, a separate `approval_state`, `lawyer_id`/`lawyer_ids`, one `session_date`, one `due_date`, `is_urgent` | No matter type (lawsuit, transaction, consultation, contract, execution), no court case number, no stage (first instance, appeal, cassation, execution), no parties or opponent, and **one hearing only** |
| Hearings | `session_date` plus a cron that creates an activity three days before | No hearing history, outcome, next date, attendee, substitute or roster |
| Money | `expenses_amount` (Float, "IQD"); read-only `account_move_id`, `account_payment_id`; `expense_account_id` | No fees billed, agreement, instalment, receivable, currency, trust or statement |
| Time | none | everything |
| Conflicts, POA, portal, client messaging, e-signature | none | everything |
| Reports | 3 QWeb PDFs: company file, oversight report, per-matter form | No money or productivity reporting |

**What SAG's usage looks like.** The prototype's `DEPARTMENT_METAS` names ten recurring government
windows: the Communications and Media Commission, water/electricity, the Companies Registrar, tax,
traffic, social security, the fairs company and chamber of commerce, the transporters' union, the
**notary (كتاب العدول: POAs, notices, revocations)**, and the managing director's personal tax. Together
with "client companies", this is the profile of a **corporate legal-services office**: a retained legal
adviser for companies that runs their annual government transactions (معاملات) and some litigation. That
profile makes three features core rather than optional: the retainer (finding 5), per-transaction or
tariff fees, and the government-transaction register. *Assumption to verify with SAG:* whether SAG
invoices those companies (office) or serves sister companies of its own group (in-house). The data model
is ambiguous. §8 covers both through the `hybrid` preset.

---

## 3. What the market does

### 3.1 Global practice-management products

| Product | Known for | What to take |
|---|---|---|
| **Clio Manage / Grow** | The benchmark. Matters, calendar, **conflict check** across contacts, matters, notes and billing records, with a status per hit, a note, and a **saved PDF report linked to the matter**. Multiple simultaneous timers. Invoices from time and expenses. Hourly, flat, contingency and **split billing**. **Evergreen trust** that automatically generates a top-up request. Client-level and matter-level trust ledgers with three-way reconciliation. | The conflict-check record, evergreen top-up, split billing and the trust-ledger concept |
| **MyCase** | **Client portal** with messages, documents, calendar, invoices and online payment. E-signature on the fee agreement and on any PDF. **Online intake forms**, a lead pipeline with analytics, and conversion from lead to client. Payment plans. | Intake funnel → fee agreement → signature in one flow, and a portal with payment |
| **PracticePanther** | Multiple timers across devices. Calendar events and emails convertible into time entries. **Retainer requests from the portal**, credited automatically to trust. **Conditional workflows**: a matter reaching a stage creates tasks, events and reminders. Guided three-way reconciliation. | Stage-triggered task automation, and the portal "pay retainer" button |
| **Smokeball** | **AutoTime**: passive time capture from documents, emails and calls. A library of 20,000+ forms that auto-fill from matter data. | Auto-filled document templates. Passive capture is out of scope in a browser-based Odoo. |
| **Filevine** | **Deadline chains** (completing one step creates the next deadline). Court-rules calendaring. Per-case calendar. AI extraction of deadlines from court documents. | Deadline chains, which map directly onto hearing → next hearing and judgment → appeal window |
| **CosmoLex** | **Built-in general ledger plus trust accounting** in one product, with one-click three-way reconciliation. | Keep billing and trust inside the real ledger (`account`), not in a parallel money model |
| **Actionstep** | A **workflow engine per matter type**: steps and milestones, a workflow "ribbon" across the top of the matter, data collection per step, and automation per step. | A stage ribbon per matter type. The suite's `legal_procedure` engine already does this and can be ported. |
| **Rocket Matter** | Evergreen retainer with the minimum balance printed on the invoice. Reports on realization, utilization, AR, trust activity and matter collections. | The retainer status line on invoices, and the KPI set |
| **LEAP** | 1,500+ official forms and precedents, preconfigured matter types, AI-assisted time recording, fixed-fee entries. | Preconfigured matter types that ship ready (Iraqi: see §4) |

**KPI definitions the market uses** (Clio Legal Trends 2025 benchmarks):

- **utilisation** = billable hours ÷ available hours (average 38%);
- **realisation** = hours invoiced ÷ hours worked (88%);
- **collection** = cash collected ÷ amount invoiced (93%);
- **lockup** = WIP days + AR days (median 93 days).

### 3.2 Arabic and GCC products

| Product (market) | Concrete features found | What to take |
|---|---|---|
| **Al-Mohamy Pro / برنامج المحامي** (22 Arab countries; no Iraq-specific features; offline) | Litigation in 5 stages (initial → appeal → cassation → execution). **رول الجلسات**: a daily and weekly hearing roster ready to take to court. Proactive deadline alerts. **POA archive with issuing authority and validity, warned 30 days before expiry**. **Automatic financial posting** of task expenses to the client statement (23 templates). **كشف حساب** (account statement) with fee schedule, instalments, expenses and VAT. PDF invoices. Execution tracking. Expiry alerts for company documents. | Roster, POA expiry, statement, execution stage. These are the Arabic core. |
| **Maktabi / مكتبي** (Saudi Arabia) | Cases and legal work, appointments, **POA management**, **client portal** with file and report sharing and messaging, reports sent by **WhatsApp** and email, tasks, reminders, archive, **branches**, advanced permissions | WhatsApp delivery of client reports, and multi-branch |
| **Law Surface** (UAE, bilingual) | Lawsuits and clients, sessions with automatic reminders, legal accounting and billing, reports, **templated email and WhatsApp messages** | Templated client messages |
| **CASENGINE** (UAE, bilingual) | Leads, **conflicts and KYC**, **engagement-letter automation**, time with AI-drafted narratives, billing, expenses, **payment scheduling and debt recovery**, hearings, **obligations and renewals including appeal windows**, client portal, WhatsApp/SMS, DocuSign, dashboards (utilisation, receivables, **dormant files**). Explicitly serves **both law firms and in-house teams**. | Evidence that one product with two modes is viable, and the dormant-file metric |
| **Lexzur (formerly App4Legal)** (MENA, 67 countries) | Matters, litigation (courts, hearings, stages), contracts, time logs, expenses, multi-currency. **Modular for firms and in-house teams alike.** | Same lesson: modules switched per audience |
| **Smart Lawyer Office (Beveron)**, **Mueen**, **Dafatra**, **Tqnia "المرافع"** | Cases, sessions, SMS reminders, fees, invoices, pleading and contract templates (صيغ صحف الدعاوى والعقود والمذكرات) | A pleading-template library is expected |
| **Qanooni** (UAE) | AI drafting and review inside Word and Outlook, Arabic and English | Out of scope now. Note it as a COULD. |
| **Qanoniah / قانونية** | A legal *library* app (laws and texts), not practice management | Link out to it rather than build it |

**Iraq.** The search found **no Iraqi practice-management product**. The Iraqi judiciary's e-portal was
launched 27 October 2021 in Baghdad courts. It offers case tracking (a mobile app), a search of cassation
decisions, forms for some services and a lawyer directory. Procedures still require an in-person visit
and fee payment at the court. A law-firm guide confirms that "all filings must be made in paper form". **No
integration target exists.** Entry must be fast and manual.

---

## 4. Iraqi specifics, as concrete data

Everything in this section is **data the product should ship, with its source and a verification flag**.
The suite already follows this pattern: `legal.appeal.rule` has `legal_basis` and
`verification_status`, and the data is `noupdate="1"` so that counsel's corrections survive upgrades.
Where the sources disagree, both values are shown and the field must be editable.

### 4.1 Legal framework

| Instrument | What it governs for an office |
|---|---|
| **قانون المحاماة رقم 173 لسنة 1965** (Advocacy Law), with amendments | Profession, training, licence classes, office, conflicts, confidentiality, **fees (Arts. 55–65)**, client money and documents (Arts. 53–54) |
| **قانون المرافعات المدنية رقم 83 لسنة 1969** (Civil Procedure) | Service (Arts. 13–28), hearings, adjournment, abandonment (Art. 54), remedies and their periods (Arts. 171–230) |
| **قانون أصول المحاكمات الجزائية رقم 23 لسنة 1971** (Criminal Procedure) | Default judgments (Art. 243), cassation (Art. 252), correction (Art. 266), assigned counsel (Art. 144) |
| **قانون التنفيذ رقم 45 لسنة 1980** (Execution) | دائرة التنفيذ: executable instruments (Art. 14), opening the file (Art. 15), the notification memo (مذكرة الإخبار), voluntary period, attachment, travel ban, detention, auction |
| **قانون الرسوم العدلية رقم 114 لسنة 1981** (Judicial Fees) | Court fee on filing: **2% of claim value** in the original text (floor and ceiling amended since, so treat as data) |
| **قانون صندوق تقاعد المحامين رقم 56 لسنة 1981** (Lawyers' Pension Fund) | **Pension-fund stamp** (طابع صندوق التقاعد) on every agency, pleading or legal act; the fund also takes **1/10 of court-awarded advocacy fees** |
| **قانون الكتاب العدول رقم 33 لسنة 1998** (Notaries) | Attestation of POAs (Art. 11), the notary's retention of POA copies (Art. 26) |
| **قانون التوقيع الإلكتروني والمعاملات الإلكترونية رقم 78 لسنة 2012** (E-signature) | An e-signature has the same evidential value as a handwritten one in civil, commercial and administrative dealings, if the conditions are met (Art. 4) |
| Iraqi Bar **administrative order 3021 of 11 April 2021** | Legal-adviser retainers for companies (see §4.4) |
| Bar Council decision of **15 June 2022** | Licence classes: متمرن, أ, ب, ج, مطلقة (see §4.2) |

### 4.2 The profession and who may do what

| Rule | Source | Product consequence |
|---|---|---|
| Only lawyers on the practising roll may give legal advice or act for others | Art. 22 | A lawyer record carries the Bar registration number and roll status |
| **Training:** register "under training", then either **2 years in a senior lawyer's office (التمرين)** or **graduated practice over 3 years (التدرج)** | Art. 18 | Lawyer record: `training_path` (تمرين/تدرج), `supervisor_id`, start date |
| **What a trainee may plead alone.** Year 1: summary (الصلحية), personal status, misdemeanours and violations. Year 2: attend investigation in all criminal cases and plead first-instance (البداءة) cases. | Arts. 19–20 | Warn (default) or block (advanced) when a hearing is assigned outside the assignee's licence |
| **Licence classes (صلاحية):** متمرن → **أ** (on joining via التدرج) → **ب** (after 1 year plus 10 practice documents) → **ج** (after 1 more year plus 10 documents) → **مطلقة** (after 5 years). The تمرين path reaches مطلقة after 2 years. | Bar Council 15 Jun 2022 | Store `licence_class` per lawyer, with a date. The suite already models `legal.licence.grade`, which can be ported. |
| At the end of training, the trainee submits **certified lists of the cases worked on** | Art. 21 | **Training log** export: matters and hearings attended, per trainee. This is a small feature with high value to trainees. |
| Every non-trainee lawyer must keep an **office**, which is the address for service. Moving must be notified to the Bar. | Art. 40 | Office address on the company; print it on letters |
| A lawyer may **substitute another lawyer (إنابة)** by letter, which is not subject to stamp duty, unless the POA forbids substitution | Art. 25 | **Substitution per hearing**: attending lawyer ≠ responsible lawyer; a printable إنابة letter; a POA flag "substitution allowed" |
| **No representation of opposing parties**, during the dispute or after it, **extended to the lawyers of the same office** | Art. 44 | Conflict check across the whole office |
| **A lawyer on an annual retainer may not accept a case against that client** during the term | Art. 45 | The conflict check includes active retainer clients |
| Privilege survives termination | Art. 46 | Privileged notes hidden from accountant and portal |
| Must not accept a case before a judge related within the **4th degree** | Art. 48 | COULD: record declared judge relationships; warn when a matter's judge matches |

**Terminology note.** The owner's "محامي متدرج" is the Iraqi **التدرج** path (graduated licence from
class أ). "المحامي المتمرن" is the trainee under supervision. The product should use both terms, because
Iraqi law uses both.

### 4.3 Fees (أتعاب المحاماة) — Advocacy Law Arts. 55–65

| Art. | Rule | Product consequence |
|---|---|---|
| 55 | Fees are due for the work entrusted, **and the lawyer may recover what he spent in the client's interest** | Disbursements are recoverable by default |
| **56(1)** | Fees follow **the contract**, but outside criminal cases they may not exceed **20% of the value of the work** under the POA. They are computed on the whole amount where the aim is a benefit beyond the claim. | **Validation:** fixed fee + success % × matter value ≤ 20% × matter value. Warn, and require a reason to override. Criminal matters are exempt. |
| **56(2)** | If the fees **awarded by the court** exceed the agreed fees, **the excess belongs to the lawyer** | On a judgment, record `awarded_advocacy_fee` and allocate it (to the lawyer or the office) |
| 57 | Work outside the original scope may be charged separately | Engagement scope text, plus "additional work" lines |
| 58 | Settlement, arbitration or any other ending still entitles the lawyer to the full fee, unless agreed otherwise | The remaining instalments become due when a matter closes by settlement |
| **59** | With no agreement, fees are set at the **customary rate (أجر المثل)** | Flag matters **without a signed fee agreement** |
| 60 | Dismissal without cause means the full fee is due; early dismissal means fair compensation | Closing reason `client_revoked` triggers a fee review |
| 61 | Withdrawal for cause, or the death of the lawyer or client, means fair compensation for effort | Same review path |
| 62 | Fee disputes go to the court where the office is located | — |
| **63** | The court awards advocacy fees against the losing party. The amounts have changed across versions: the original text set 5% ≤ 500 IQD; a Supreme Judicial Council commentary cites 10% capped at 500,000, 10,000–100,000 for non-quantified claims, and 10,000–30,000 for assigned counsel; the **Council of Ministers approved an amendment on 4 Jun 2024** (announced 27 Jun 2024) setting 25,000–150,000 for non-quantified claims, 5% at 25,000–150,000 for expropriation, and 25,000–75,000 for assigned counsel; a practitioner source cites a 2,000,000 IQD cap. | Keep **as dated data** (a rate table with `effective_from`), never in code. Mark it "verify". |
| **64** | Advocacy fees have a **first-rank lien** on the money the client receives from the matter | Execution collections: deduct fees before paying the client out (from trust) |
| **65** | Limitation: **3 years for unwritten** fee claims, **15 years for written** agreements | A report of *matters with no written fee agreement* (limitation risk) |

**Fee arrangements used in practice.** These are Iraqi and Arab practice as reflected in the products
above and the Bar order. The mix should be confirmed with SAG.

| Arrangement | Arabic | Typical in Iraq? | Notes |
|---|---|---|---|
| Lump sum per matter, in stage instalments | أتعاب مقطوعة على دفعات | **Very common** | e.g. X% on signing, Y% on first-instance judgment, Z% on execution. Instalments are triggered by **stage**, not only by date. |
| Percentage of amount awarded or collected (success fee) | نسبة من المحكوم به / المستحصل | Common in debt and compensation cases | Must respect the 20% cap (Art. 56). The base must be chosen: *awarded* or *collected*. |
| Monthly legal-adviser retainer (company) | أتعاب المستشار القانوني الشهرية | **Mandatory for companies** (Bar order 2021) | Minimum 300,000 IQD (local) or 600,000 IQD (foreign) per month, **paid a year in advance**; the company withholds 5% for the Bar |
| Per transaction or per government window | أجور معاملة | Common for corporate services (SAG's profile) | Tariff by transaction type and body |
| Per hearing attended | أجور حضور جلسة | Common between lawyers (substitution); sometimes billed to clients | Used on both sides: billing the client and **paying the substitute** |
| Consultation fee | أتعاب استشارة | Common | Charged at intake, even if no matter follows |
| Hourly | بالساعة | **Rare locally**; used with foreign clients, usually in USD | Needs time tracking and rate cards |
| Capped hourly or fixed plus hourly | مختلط | Rare | Advanced |

### 4.4 Company legal-adviser retainers (Bar administrative order 3021, 11 Apr 2021)

| Item | Value |
|---|---|
| Legal basis cited | Advocacy Law Arts. 35 and 65; Bar Board decision of 31 Mar 2021, Arts. 23–24 |
| Minimum monthly fee, local company or industrial project | **300,000 IQD** |
| Minimum monthly fee, foreign company or branch in Iraq | **600,000 IQD** |
| Payment | **In advance for each year** from the appointment date |
| Bar share | **5% of the monthly fee**, **withheld by the company** and remitted to the Bar against a receipt |
| Penalty for having no legal adviser | 750,000 IQD per month (local) or 1,500,000 IQD per month (foreign), payable to the Bar fund; the Bar withholds all company requests (deregistration, liquidation, merger) until paid |

Product consequences:

- a `retainer` engagement type with a monthly amount and an annual-in-advance invoicing rule;
- a minimum-fee warning;
- the **5% Bar share modelled as a withholding** on the invoice or payment, so that the receivable
  clears at 95%;
- a certificate, or a renewal date, per client company.

*This is a 2021 order. Verify the current amounts with the Bar before shipping them as defaults.*

### 4.5 Powers of attorney (الوكالة)

| Fact | Consequence |
|---|---|
| The **general POA (وكالة عامة)**, organised at the **notary (كاتب العدل)**, is the usual instrument before courts, ministries and companies. It is issued in **three originals**: the notary keeps one, the client one, and the agent one. | POA record: type (عامة / خاصة), notary office, number, date, the original's location |
| **Criminal POAs** can be organised before the judge | POA type `judicial` |
| **Special POA (وكالة خاصة)**: limited to a named act or matter | `scope` text plus the bodies and matters it covers |
| POAs from abroad are issued by Iraqi **consulates** | `issued_by`: notary / court / consulate; legalisation note |
| A POA ends when the work is done, the term expires, the principal or agent dies, or the principal **revokes (عزل)** it. Revocation must reach the agent. | `state`: draft / active / revoked / expired; revocation date and reason; linked matters flagged |
| **Substitution** is allowed unless forbidden (Art. 25) | `substitution_allowed` flag |
| Government windows often ask for a **confirmation of issuance (صحة صدور)** of a POA (the prototype's "صحة صدور وكالات" at traffic; the showcase's state `pending_docs` is labelled "بانتظار الوثائق وصحة الصدور") | Track the confirmation request and its result as a sub-step of the POA or transaction |
| The pension-fund stamp is due on every agency | Disbursement category `pension_stamp` |

The suite's `legal.poa` (agent, bar registration, scope, bodies, state, revocation, `case_ids`,
notary office, issue date, attachments) is exactly this model and can be ported.

### 4.6 Courts and the hearing cycle

**Courts** (one court of appeal per governorate, two in Baghdad: Karkh and Rusafa; the Kurdistan Region
has its own cassation court):

- محكمة البداءة (civil first instance), including its **specialised commercial** branch;
- محكمة الأحوال الشخصية / محكمة المواد الشخصية (personal status);
- محكمة العمل (labour);
- محكمة التحقيق (investigation);
- محكمة الجنح (misdemeanours);
- محكمة الجنايات (felonies);
- محكمة الأحداث (juvenile);
- محكمة الاستئناف (appeal, federal, per governorate);
- محكمة التمييز الاتحادية (Federal Cassation);
- المحكمة الاتحادية العليا (Federal Supreme, constitutional);
- محكمة القضاء الإداري and محكمة قضاء الموظفين (under the State Council);
- دائرة التنفيذ (execution, Ministry of Justice).

The suite's `legal_litigation/data/legal_court_data.xml` already seeds 18 governorates and the principal
courts.

**The civil cycle.** Source: a Supreme Judicial Council article on the path of a civil lawsuit, and CPL
83/1969.

1. Petition (عريضة الدعوى) → the judge refers it for **fees** (2% of value) → registration with a
   **court case number** and a first hearing date.
2. **Service (تبليغ)** on the defendant by the court process-server (المحضر), the police, registered mail
   (with the judge's leave, **but not for the petition or the judgment**), or **newspaper publication**
   when the address is unknown.
3. Hearings. Each one ends in one of these outcomes:
   - adjournment (تأجيل): in practice ≤ 20 days unless necessary, and not twice for the same cause
     (Art. 62);
   - hearing witnesses;
   - expert appointment (خبير), with an **expert-fee deposit**;
   - left for follow-up (ترك الدعوى للمراجعة) if both sides are absent;
   - **cancellation of the petition (إبطال العريضة)** if nobody reactivates it. Sources differ on the
     wait: the original text of Art. 54 says 30 days, the SJC article says 15, and secondary sources on
     the amendment say 10. **Configurable, flagged "verify".**
   - stay by agreement (وقف), ≤ 3 months, lapsing after 6 months;
   - interruption (انقطاع) on death or loss of capacity.
4. **Close of pleadings (ختام المرافعة)** → judgment within ≤ 15 days → the judgment is **served** →
   the remedy periods (§4.7) run → finality (الدرجة القطعية) → **execution** (§4.8).

**Hearing outcome vocabulary.** It is already in the suite's `legal.hearing`, so port it:

- purpose: مرافعة / استماع شهود / خبرة / نطق بالحكم / تأجيل;
- attendance: حضرنا / غياب الخصم / تغيبنا / غياب الطرفين;
- free-text `result` and `next_step`;
- **`next_hearing_date`, which creates the next hearing record** (Filevine's "deadline chain").

**Working calendar.** Asia/Baghdad is UTC+3 with no daylight saving. The government week runs
**Sunday–Thursday**; the weekend is **Friday–Saturday**. The Gregorian calendar is used in court. If a
period ends on an official holiday it extends to the next working day (CPL, cited as Art. 25 by secondary
sources; verify the article number).

### 4.7 Remedy periods (the deadline engine's seed data)

| Remedy | Period | Runs from | Basis | Confidence |
|---|---|---|---|---|
| Objection to a **default civil judgment** (الاعتراض على الحكم الغيابي) | **10 days** | day after تبليغ | CPL Arts. 177, 172 | statute text read |
| **Appeal** (استئناف) of a first-instance judgment | **15 days** | day after تبليغ | CPL Art. 187 | statute text read. One law-firm guide says 30: **the statute wins**, but keep it editable. |
| **Cassation** (تمييز) of first-instance and appeal judgments | **30 days** | day after تبليغ | CPL Art. 204 | statute text read |
| Cassation of other judgments named in Art. 204 | **10 days** | day after تبليغ | CPL Art. 204 (the original text names محاكم الصلح; the SJC commentary applies it to personal-status cases) | **verify** which judgments the current text covers |
| Cassation of **decisions** (urgent or ancillary قرارات) | **7 days** | day after تبليغ | CPL Art. 216 | statute text read |
| **Correction** of a cassation decision (تصحيح القرار التمييزي) | **7 days** (≤ 6 months from issue) | تبليغ | CPL Art. 221 | statute text read |
| **Retrial** (إعادة المحاكمة) | **15 days** | day after the ground is discovered | CPL Art. 198 | statute text read |
| Third-party objection (اعتراض الغير) | none fixed | until execution or limitation | CPL Art. 230 | statute text read |
| All civil periods are **peremptory**: missing one forfeits the remedy | — | — | CPL Art. 171 | statute text read |
| **Criminal cassation** | **30 days** | day after **pronouncement** (in-person judgment) | CrPL Art. 252 | statute text read |
| Criminal correction | 30 days | — | CrPL Art. 266 | statute text read |
| A default criminal judgment is deemed in-person if not objected to within | 30 days (مخالفة) / 3 months (جنحة) / 6 months (جناية) | from تبليغ | CrPL Art. 243 | statute text read |
| Labour-court remedy | 30 days | — | Labour Law 37/2015 (suite seed) | **unverified** |

These match the suite's `legal.appeal.rule` seeds (10/15/30/7/30), which ship `verification_status =
stale`. This research **confirms 10/15/30/7 against the statute text** and adds retrial, correction and
the criminal rules. The key product rule is to **never compute a civil deadline without a tabligh date**.
Show "awaiting service" instead of a guess.

### 4.8 Execution (دائرة التنفيذ, Execution Law 45/1980)

| Step | Data |
|---|---|
| Executable instruments: final judgments, commercial papers, acknowledged-debt documents, mortgage registry documents, and others given force by law | Art. 14 |
| Application → fee and registration → a report opens the **execution file (الإضبارة التنفيذية)**, with its own number | Art. 15 |
| **Notification memo (مذكرة الإخبار بالتنفيذ)** to the debtor | Art. 25 |
| **Voluntary period: 7 days** from the day after notification. A debtor who pays in it is exempt from the collection fee. | Multiple sources. Government debtor: 30 days (Art. 20, **verify**). |
| Enforcement: attachment of movables or real estate, salary attachment, **travel ban**, **detention of the debtor** (with age and status exclusions and a maximum term), auction | Arts. 30, 40–48, 63–106 (figures from a secondary summary: **verify** before shipping) |
| The file lapses if the creditor does not pursue it | Art. 112 (period **verify**) |
| Precautionary attachment or travel ban **before** judgment: the applicant deposits **10% of the claim** or a notarised guarantee | Practitioner guide |

Product consequences:

- the execution stage is a phase of the same matter, with its own file number and office;
- **collections received through execution** are credited to client funds (trust);
- advocacy fees are deducted first (the Art. 64 lien);
- the balance is paid out to the client, with a statement.

### 4.9 Money: currency, taxes, client funds

| Fact | Value / source | Product consequence |
|---|---|---|
| Home currency | **IQD**, ISO 368. Odoo base data ships IQD **inactive, rounding 0.001**. | Activate IQD on install (office mode); set rounding **1**; offer `account.cash.rounding` of **250** for cash receipts |
| USD use | Common for fees, especially with foreign clients | Engagement currency ≠ invoice currency ≠ payment currency; record the rate used on each payment |
| Official vs market rate | CBI official **1,300** (banks sell at 1,310; end users pay 1,320); parallel market about **1,478** | Rates are entered by hand (`currency_rate_live` is EE); per-payment rate override; a "rate used" line on receipts |
| VAT | Iraq has **no general VAT**. `l10n_iq` sale taxes are sector-specific (300% alcohol and tobacco, 15% cars and travel, 20% mobile and internet); purchase withholdings are 3.3% and 7%. | Legal fees are invoiced **untaxed by default**. The Bar's 5% (§4.4) is modelled as a withholding. |
| Client money | No IOLTA-style statute found. Art. 53 requires **returning client funds and original documents** on termination; the right to reclaim documents lapses after 5 years (Art. 54). | A **client-funds liability account (أمانات الموكلين) plus journal**, a per-client ledger, statements, and a **register of client originals received and returned** |
| Chart of accounts | `l10n_iq` has no client-funds liability; its closest account is `200401 Deferred income`, which is **wrong** for this purpose | The module creates the liability account and journal per company on first use |
| Disbursements typical in Iraq | Court fee (2%), pension-fund stamps, expert-fee deposits, publication (newspaper tabligh), notary fees, execution fees, translation, runner and transport, government transaction fees and receipts | Seeded disbursement categories; each links to a receipt number (رقم الوصل) |

### 4.10 Government transactions (المعاملات) — the SAG core

A corporate client's annual cycle, as the prototype's ten windows describe it:

- company registrar: annual accounts, capital changes;
- tax clearance (براءة ذمة);
- social security;
- chamber of commerce / import licence;
- traffic (fleet renewals, badges);
- CMC (.iq domain, P.O. box);
- water and electricity;
- transporters' union;
- notary (POAs, notices, revocations);
- the managing director's personal tax.

These are **recurring, date-driven obligations per client company**. They are office work (billed per
transaction or covered by the retainer) as much as department work. The suite's `legal_procedure` (phases,
steps, document requirements, fee rules) and its `legal_iq_*` packs (registrar, tax, social security,
chamber, residency) already model exactly this and can be ported.

---

## 5. Roles and their jobs to be done

The UX rule for every role: **the first screen answers "what do I have to do today"**. The three most
frequent actions of the role are one click from that screen. Everything else is one level down.

### 5.1 Partner / office owner (صاحب المكتب / الشريك)

| Job | Frequency | Must be one click from the first screen |
|---|---|---|
| Decide whether to accept a matter: see the conflict result and the proposed fee; approve, decline or override with a reason | daily | the intake queue ("ما ينتظر قراري") |
| Know the money: collected this month **by currency**, receivables ageing, instalments overdue, retainers due this month, client funds held, WIP (if time is on) | daily or weekly | the office money strip |
| Make sure **every hearing tomorrow has an attending lawyer** and every deadline this week has an owner | daily | the tomorrow roster with the "unassigned" gaps highlighted |
| Approve discounts, write-offs and fee overrides above the 20% cap | weekly | the approval list |
| Allocate work and see lawyer load (matters, hearings this week, overdue tasks; utilisation if time is on) | weekly | the team board |
| See silent matters: no client update in N days, no activity in N days (dormant) | weekly | the attention list |
| Per-partner / per-lawyer origination and collections; matter profitability | monthly | reports |

*Must not be forced to do:* data entry of hearings or receipts.

### 5.2 Lawyer (المحامي)

| Job | Frequency | One click |
|---|---|---|
| See **my hearings today and tomorrow**, with court, hall, case number, purpose and what to prepare | daily | "My day" |
| **Record a hearing outcome and the next date from the court corridor on a phone, in under 30 seconds** | several times a day | outcome dialog: attendance · outcome · next date · note, then "send update to client?" |
| See deadlines computed from judgments (appeal window, days left), and start the appeal | weekly | the deadline card on the matter |
| Draft a pleading (لائحة), notice (إنذار), request or letter from a template, with party and court fields auto-filled | daily | "New document from template" on the matter |
| Arrange a **substitute** for a hearing (إنابة) and print the substitution letter | weekly | on the hearing |
| Record an expense paid (court fee, stamp) with a receipt photo | daily | a quick "expense" action |
| Record time (only if enabled): a timer on the open matter, or a quick line | many times a day | systray timer |
| Ask the client for money (a top-up for fees or a disbursement advance) | weekly | "request payment" (a WhatsApp or email template) |

*Must not see* (default): other teams' confidential matters when team confidentiality is on; office-wide
financials.

### 5.3 Trainee / graduated lawyer (المحامي المتمرن / المحامي المتدرج)

| Job | One click |
|---|---|
| Attend the hearings delegated to them, **within their licence class**, and record the outcome | "My day" (same as the lawyer) |
| Run court errands: collect decisions, pay fees, photocopy the file (تصوير الإضبارة) | task list |
| Draft under supervision: the document goes to the supervisor for review | "send for review" |
| **Keep the training log** (matters, hearings attended, documents) and export it for the Bar | "My training log" |

*Must not see* (default): fees, invoices, client funds.

### 5.4 Secretary / clerk / runner (السكرتير / الموظف الإداري / المعقّب)

| Job | One click |
|---|---|
| Receive a walk-in or a call: **create an intake**, **run the conflict check**, book a consultation. **Under two minutes.** | "New client / new matter" at the top of every screen |
| Print or send **tomorrow's hearing roster (رول جلسات الغد)**, per lawyer and per court | "Roster" |
| Send reminders to clients about hearings, missing documents or overdue instalments, as WhatsApp click-to-chat with a prefilled Arabic text | from the roster or matter, one click per client |
| Register **incoming court papers** (تبليغات received, decisions) and scan them onto the matter; **entering a tabligh date must trigger the deadline** | "Register incoming" |
| Keep the **POA register** and the **register of client originals** (المستمسكات الأصلية) in and out | registers |
| Issue a **cash receipt (وصل قبض)** for a client payment, if permitted | "Receive payment" |
| Runner (معقّب): today's government-transaction list, per body, with the required documents and the fees to carry; record the receipt number and fee paid, and the step done | "My transactions today" |

### 5.5 Accountant (المحاسب)

| Job | One click |
|---|---|
| Issue invoices: instalments due, retainers (monthly, or yearly in advance), per-transaction fees, WIP and disbursements; **one draft per client, reviewed, then posted** | "To invoice" board |
| Record payments in IQD or USD at the rate used; apply advances; issue receipts | payment register |
| Manage client funds: receive deposits, pay court and expert fees out of them, transfer earned fees on invoice, **refund balances**; produce a per-client ledger | "Client funds" |
| Send a **client statement (كشف حساب)**: fees, instalments, disbursements, payments, balance, and client funds held | "Statement" |
| Receivables follow-up: overdue instalments and retainers, with reminders | "Overdue" |
| Pay substitute lawyers their per-hearing fees; remit the Bar's 5% and the pension stamps | vendor bills |

*Must not see:* privileged matter notes or document content.

### 5.6 Client (الموكّل): individual, or a company's legal contact

| Job | Channel (in order) |
|---|---|
| Know **what happened at the last hearing and when the next is** | WhatsApp or email message after each hearing (default), then the portal |
| Know what they owe and have paid; get an invoice and receipt; see the retainer or funds balance | statement PDF by WhatsApp or email, then the portal |
| Send documents that are asked for | the portal upload, or reply by email |
| **Sign the fee agreement** | wet signature (default), or portal signature (advanced) |
| Company contact: see **all matters and transactions of the company** in one list | portal |

*Must never see:* internal notes, time narratives before invoicing, other clients.

---

## 6. Feature catalogue

Columns: **ID** · **Feature** · **Pri** · **Default (minimal)** · **Advanced (on demand)** · **Odoo 19 basis**
(CE unless marked). "Mode" says where a feature is visible: **O** = office, **D** = department,
**O+D** = both.

### A. Intake and conflict of interest (O)

| ID | Feature | Pri | Default | Advanced | Odoo basis |
|---|---|---|---|---|---|
| A1 | **Quick intake**: person or company, phone, matter summary, opposing party, referral source | MUST | 5 fields, one dialog, from a top-level "new" action (the showcase's wizard idea, kept) | ID documents (national ID with mother's name, company registration), KYC notes, lead source analytics | `res.partner` + `legal.company` (showcase) + wizard |
| A2 | **Conflict check** over clients, opposing parties, related parties, **active retainer clients** (Art. 45), across the **whole office** (Art. 44) | MUST | Runs automatically on intake. It shows either "no match" or a list of hits (matter, role, responsible lawyer). Continue or decline. | Fuzzy match; related entities through `commercial_partner_id`; manual re-check; hits redacted across teams (as in the phase-2 design) | custom `legal.conflict.check`, ported from the phase-2 design |
| A3 | **Arabic name normalisation** in matching (أ/إ/آ→ا, ة→ه, ى→ي, tatweel, diacritics, the "ال" prefix, "عبد ال…" spacing) | MUST | invisible, always on | an adjustable threshold | pure Python; optional `rapidfuzz` for scoring |
| A4 | **Conflict record** kept: who, when, what was searched, hits, and decision (clear / override with reason / declined); never deleted | MUST | a line in the matter's chatter plus a record | a PDF report (the Clio model); an auditor list | custom model |
| A5 | **Consultation** (استشارة) with a fee, even without a matter | SHOULD | "consultation" matter type with a fixed fee and a receipt | conversion of the consultation into a matter | `legal.task` type + invoice |
| A6 | Lead pipeline (prospects not yet engaged) | COULD | — | kanban of intakes by stage, conversion rate | custom, or `crm` (CE) bridge |
| A7 | Public web intake form | COULD | — | website form → intake | `website` (CE), optional |

### B. Engagement and fee agreement (O)

| ID | Feature | Pri | Default | Advanced | Odoo basis |
|---|---|---|---|---|---|
| B1 | **Engagement (التكليف / عقد الأتعاب)** per client: scope, responsible lawyer, fee arrangement, currency, dates, status; a matter belongs to one | MUST | one screen: client · what we do · fee (amount + type) · currency · signed? | several matters per engagement; several engagements per client; scope exclusions | custom `legal.engagement` (phase-2 design) |
| B2 | Fee types: **lump sum**, **stage instalments**, **success %** (of awarded or collected), **monthly retainer**, **per transaction**, **per hearing**, **consultation**, **hourly** | MUST (first six); SHOULD (hourly) | a type picker showing only the types enabled in settings (default: lump sum, instalments, retainer) | combinations (lump sum + success %); capped hourly | custom fee lines |
| B3 | **Instalment schedule tied to stages or dates** (on signing / filing / judgment / final / execution / date) | MUST | "total, paid, remaining" plus the next instalment | the full schedule; auto-draft invoice when a stage is reached | custom lines → `account.move`; `account.payment.term` is date-only, so it is not enough |
| B4 | **20% cap check** (Art. 56) with criminal exemption | MUST | a warning banner when exceeded | override with a reason (partner only) | constraint + approval |
| B5 | **Signed fee-agreement flag and document**; a report of matters without one (Arts. 59, 65) | MUST | "signed ✓ / not signed" chip on the matter | a printable agreement from a template; signature on the portal (M1) | QWeb + attachment |
| B6 | **Retainer**: monthly amount, minimum-fee check (300k / 600k IQD), invoicing yearly-in-advance or monthly, renewal date | MUST | amount + frequency + start | Bar 5% withholding, auto-renewal, proration | custom schedule + cron → `account.move` (subscriptions are EE) |
| B7 | Rate cards (per lawyer grade × client × matter type) | COULD | — | only when hourly is on | custom |
| B8 | Split billing (two payers of one matter) | COULD | — | payer shares | custom invoice split |

### C. Matters and lifecycle (O+D)

| ID | Feature | Pri | Default | Advanced | Odoo basis |
|---|---|---|---|---|---|
| C1 | **Matter types**: lawsuit (civil, personal status, labour, criminal, administrative), government transaction, contract, consultation or opinion, execution, notice (إنذار) | MUST | a type picker in intake that sets the defaults (stages, tasks, templates) | custom types, per-type fields | `legal.task` (keep the model) + a type model |
| C2 | **Stage ribbon** for lawsuits: first instance → appeal → cassation → execution, with a court and **court case number per stage** | MUST | the ribbon on the matter header; the current stage's court and number | a full stage history; a new stage opened from a judgment | port `legal.lawsuit` / `legal.judgment` concepts |
| C3 | **Parties**: client role (plaintiff/defendant/…), opposing parties, **opposing counsel**, third parties | MUST | client role + one opponent | several parties with roles; feeds A2 | port `legal.lawsuit.party` |
| C4 | Matter number (office sequence) **separate from the court case number** | MUST | automatic | per-type patterns (e.g. `LIT/2026/0001`) | `ir.sequence` (the showcase has one) |
| C5 | Responsible lawyer, team, **origination** (who brought the client) | MUST (responsible); SHOULD (origination) | responsible lawyer only | team, origination credit, supervising partner | `res.users`; the showcase's `lawyer_id`/`lawyer_ids` |
| C6 | Matter value (قيمة الدعوى) and currency | MUST | one amount | awarded, collected | Monetary fields |
| C7 | Close a matter with an outcome and reason (won / lost / settled / withdrawn / client revoked / …) | MUST | a close dialog | a fee review on revocation (Arts. 60–61) | custom |
| C8 | Approval axis (the showcase's `approval_state`) | SHOULD (D), COULD (O) | hidden in office mode | "requires partner approval" per type | keep the showcase fields |

### D. Court calendar and hearings (O+D)

| ID | Feature | Pri | Default | Advanced | Odoo basis |
|---|---|---|---|---|---|
| D1 | **Hearing records** (many per matter): date and time, court, hall, purpose, attending lawyer | MUST | next hearing on the matter header; a list tab | attachments, preparation notes | port `legal.hearing` |
| D2 | **Record outcome + next date in one step** (the next hearing is created automatically) | MUST | a 4-field dialog, mobile friendly | minutes, witnesses, expert report link | custom OWL dialog |
| D3 | **Daily/weekly roster (رول الجلسات)**, printable and shareable, grouped by court and lawyer | MUST | "Tomorrow" button → PDF, or WhatsApp text per lawyer | date range, filters | QWeb + OWL list |
| D4 | Calendar view of hearings and deadlines (office, mine) | MUST | month/week with a colour per lawyer | sync to Google/Outlook | `calendar` view (CE); `google_calendar` / `microsoft_calendar` (CE) optional |
| D5 | **Substitution (إنابة)**: attending ≠ responsible lawyer; a printable substitution letter; the substitute's per-hearing fee | SHOULD | an "attending lawyer" field | letter template; payable to the substitute | custom + QWeb |
| D6 | **Licence-class check** at assignment (trainee rights) | SHOULD | warning | block | custom, using lawyer `licence_class` |
| D7 | Unassigned-hearing alert (no attendee for tomorrow) | MUST | red count on the roster and the partner dashboard | — | computed |

### E. Deadlines (O+D)

| ID | Feature | Pri | Default | Advanced | Odoo basis |
|---|---|---|---|---|---|
| E1 | **Remedy deadlines from a judgment**: pick the ruling type, enter the **tabligh date**, get the deadline and days left | MUST | a deadline card with a countdown | rule table (§4.7) editable with source and verification status | port `legal.appeal.rule` + `legal.judgment` |
| E2 | Holiday roll-forward and a Sun–Thu working calendar | MUST | automatic | holiday list per year | `resource.calendar` (CE) |
| E3 | Abandonment clock (ترك للمراجعة → إبطال) | SHOULD | a card "reactivate by …" | configurable days (sources disagree) | rule data |
| E4 | Other dated obligations: POA expiry, retainer renewal, company renewals (registrar, chamber, …) | MUST | one "upcoming" list | per-type lead times | `legal.deadline`-style union view (suite) |
| E5 | Escalation when a deadline is at risk | SHOULD | activity to the responsible lawyer at T-3 | to the partner at T-1 | cron + `mail.activity` |

### F. Tasks and templates (O+D)

| ID | Feature | Pri | Default | Advanced | Odoo basis |
|---|---|---|---|---|---|
| F1 | Tasks on a matter with an assignee and due date | MUST | activities ("to do") | checklists | `mail.activity` (CE) |
| F2 | **Task templates per matter type and stage** (e.g. "new lawsuit": prepare the petition, pay the fee, register, follow tabligh) | SHOULD | applied automatically on creation or at a stage | editing templates | `mail.activity.plan` (CE, Odoo 17+) or the ported procedure engine |
| F3 | Stage-triggered automation (a stage reached → tasks, message, invoice draft) | COULD | — | rules | `base_automation` (CE) |

### G. Time (O, optional)

| ID | Feature | Pri | Default | Advanced | Odoo basis |
|---|---|---|---|---|---|
| G1 | **Timer** in the systray on the open matter; one click to start or stop | SHOULD (MUST when hourly is enabled) | hidden unless time is on | several timers | custom OWL (the EE `timer` module is absent) |
| G2 | **Quick time line / day sheet**: matter, duration (`1.5` or `1:30`), narrative, billable | SHOULD | one-line entry | week grid (keyboard only) | `account.analytic.line` + custom fields; **not** `hr_timesheet` (it pulls in `project`) |
| G3 | WIP: unbilled time and disbursements by client, matter and lawyer, with **ageing** | SHOULD | a total on the partner dashboard | a board with "draft invoice" per client | pivot + custom OWL board |
| G4 | Utilisation, realisation, collection (the KPI definitions in §3.1) | COULD | — | report | pivot / graph |
| G5 | Cost of time (per-employee hourly cost) for profitability | COULD | — | — | `hr_hourly_cost` (CE) |

### H. Expenses and disbursements (O+D)

| ID | Feature | Pri | Default | Advanced | Odoo basis |
|---|---|---|---|---|---|
| H1 | **Disbursement line**: date, category (court fee, pension stamp, expert deposit, publication, notary, execution fee, transport, other), amount, currency, **receipt number**, photo | MUST | 4 fields + photo | paid from: office cash / lawyer pocket / client funds | custom model; replaces the showcase's single `expenses_amount` (migrate it as one line) |
| H2 | **Recoverable from the client?** (default yes, per Art. 55) → goes to the next invoice | MUST (O) | a checkbox | markup; non-recoverable policy per engagement | custom → invoice line |
| H3 | Reimbursing a lawyer's out-of-pocket expenses | SHOULD | — | expense report | `hr_expense` (CE) bridge, optional |
| H4 | Accounting posting (an expense entry or a payment out of client funds) | SHOULD | automatic on validation | account per category | `account.move`; the showcase's `expense_account_id` concept |

### I. Invoicing and payments (O)

| ID | Feature | Pri | Default | Advanced | Odoo basis |
|---|---|---|---|---|---|
| I1 | **"To invoice" board**: instalments due, retainers due, per-transaction fees, WIP, recoverable disbursements, grouped by client | MUST | one list, "create draft" per client | selection per line, write-off, carry forward | custom OWL + `account.move` |
| I2 | Invoice in **IQD or USD**, with an Arabic layout that shows the matter, stage and retainer status | MUST | the engagement's currency | a second-currency equivalent on the PDF | `account` (CE) multi-currency + QWeb |
| I3 | **Payment receipt (وصل قبض)** in cash or bank, with the rate used; partial payments; advances | MUST | "receive payment" from the matter or client | a cashier role, receipt book numbering | `account.payment` (CE) |
| I4 | **Client statement (كشف حساب)**: fees, instalments, disbursements, payments, balance, client funds held, per client or engagement | MUST | a PDF from the client page, sendable by WhatsApp or email | a date range; per matter | custom QWeb (the EE partner ledger is absent) |
| I5 | Overdue reminders for instalments and retainers | SHOULD | a list plus a one-click message | automatic schedule | custom (`account_followup` is EE) |
| I6 | Online payment from the portal | COULD | — | provider | `account_payment` + `payment` (CE); **no Iraqi providers ship**, so `payment_custom` covers manual transfer or ZainCash instructions |
| I7 | Bar 5% withholding on legal-adviser retainers | SHOULD | automatic on retainer invoices when enabled | account and rate configurable | tax (negative) or payment difference |
| I8 | Court-awarded advocacy fees (Art. 56(2), Art. 63) and the pension fund's 1/10 | COULD | a field on the judgment | allocation to lawyer or office | custom |

### J. Client funds and advances (O)

| ID | Feature | Pri | Default | Advanced | Odoo basis |
|---|---|---|---|---|---|
| J1 | **Advance on fees** (دفعة مقدمة): the client pays before the invoice; it is applied automatically to the next invoice | MUST | "receive advance" | — | `account.payment` unreconciled → outstanding credit (CE) |
| J2 | **Client funds held (أمانات الموكلين)**: a separate liability account and journal; receive, pay out on the client's behalf, transfer earned fees on invoice, refund | MUST (O) | a balance chip on client and matter; "receive funds / pay from funds" | per-matter sub-ledger; minimum balance and top-up request (evergreen) | `account` journal + liability account created by the module; ledger via `account.move.line` pivot (the EE report is absent) |
| J3 | **Never go negative** on a client's funds; block paying out more than held | MUST | hard check | partner override with a reason | constraint |
| J4 | Execution collections into client funds, fee deduction (Art. 64), payout statement | SHOULD | "collection received" on the execution stage | — | same as J2 |
| J5 | Register of client **original documents** received and returned (Arts. 53–54) | SHOULD | a list on the client | return receipt, 5-year notice | custom |

### K. Documents and templates (O+D)

| ID | Feature | Pri | Default | Advanced | Odoo basis |
|---|---|---|---|---|---|
| K1 | Matter documents, **typed** (petition, pleading, decision, judgment, tabligh, POA, contract, receipt, ID); drag-and-drop | MUST | a drop zone on the matter, with the type guessed from the name | versions, tags, a court-bundle export | `ir.attachment` + a type field; custom OWL panel (`documents` is EE) |
| K2 | **Templates with auto-fill**: petition (عريضة دعوى), pleading (لائحة), notice (إنذار عدلي), substitution letter (إنابة), fee agreement, request to a government body, client update | MUST | "new from template" on the matter → an editable document | a template editor with field placeholders; DOCX output | QWeb/HTML templates (CE); DOCX would need `docxtpl`/`python-docx` (a server dependency, so check Odoo.sh) |
| K3 | Registration of incoming and outgoing papers with a date (tabligh received → deadline) | MUST | "register incoming" | a register book | port `legal_correspondence` concepts |
| K4 | Scan or photo from a phone | SHOULD | camera upload on mobile | — | web file input |

### L. Client communication and portal (O)

| ID | Feature | Pri | Default | Advanced | Odoo basis |
|---|---|---|---|---|---|
| L1 | **Client update after each hearing**: a prefilled Arabic message (what happened, next date, what is needed), sent by **WhatsApp click-to-chat** or email | MUST | offered at the end of D2; one click opens WhatsApp with the text | message templates per type; a log in the chatter | `wa.me` link (free); `mail.template` (CE); **not** the EE `whatsapp` module or paid APIs |
| L2 | Reminders to the client: hearing tomorrow, missing documents, instalment due | MUST | from the roster and "to invoice" lists | automatic daily batch (email; SMS optional) | cron + `mail`; `sms` is CE but **IAP-paid** |
| L3 | **Client portal**: my matters (stage, next hearing), shared documents, invoices and receipts, statement, funds balance, upload | SHOULD | off; enabled per client | company-contact access to all company matters | `portal` (CE) + record rules keyed on the client/engagement; **one test per rule** |
| L4 | "Shared with client" flag on documents and events; internal notes never shared | MUST (when L3 is on) | default **not shared** | — | field + portal rule |

### M. E-signature (O)

| ID | Feature | Pri | Default | Advanced | Odoo basis |
|---|---|---|---|---|---|
| M1 | Sign the fee agreement on the portal: drawn or typed signature, name, timestamp, IP, document hash | COULD | off: print for wet signature, then upload the scan | portal signature | `portal` **signature_form** (CE) reused, or `sale` quotation signing (CE, but it pulls in `sale`); `sign` is EE |
| M2 | Evidential note: Law 78/2012 gives an e-signature the weight of a handwritten one **if** it is linked to the signer and meets the law's conditions (certification) | — | shown in help | — | — |

### N. Reminders and notifications (O+D)

| ID | Feature | Pri | Default | Advanced | Odoo basis |
|---|---|---|---|---|---|
| N1 | Internal: hearing tomorrow, deadline at T-3/T-1, instalment overdue, POA expiring in 30 days, retainer renewal | MUST | activities to the responsible person | per-type lead times, escalation to the partner | cron + `mail.activity` (the showcase's cron, generalised) |
| N2 | Daily digest for the partner | COULD | — | email digest | `digest` (CE) |

### O. Reporting (O+D)

| ID | Feature | Pri | Default | Advanced | Odoo basis |
|---|---|---|---|---|---|
| O1 | **Office dashboard** (partner): collected this month (IQD, USD), receivables ageing, overdue instalments, retainers due, client funds held, hearings this week (unassigned count), deadlines at risk, new matters/intakes | MUST | one screen, real numbers only, each tile clickable | a period picker, a lawyer filter | custom OWL client action (the showcase has a dashboard tag to keep) |
| O2 | Collections and receivables by client, lawyer and currency | MUST | pivot | graph | pivot/graph (CE) |
| O3 | Matter profitability: fees billed and collected vs cost of time + unrecovered disbursements | SHOULD | per matter on its money strip | per client, lawyer, type | analytic account per matter (CE) |
| O4 | WIP ageing (if time is on) | SHOULD | — | board | G3 |
| O5 | Lawyer workload and utilisation | SHOULD (workload) / COULD (utilisation) | counts | utilisation with time | pivot |
| O6 | Matters without a signed fee agreement; dormant matters; matters with no client update in N days | SHOULD | lists on the dashboard | thresholds | computed filters |
| O7 | Printable reports kept from the showcase (company file, oversight, per-matter follow-up form) | MUST (compatibility) | same menu | filters | QWeb |
| O8 | Spreadsheet-style custom dashboards | COULD | — | — | `spreadsheet_dashboard` (CE) |

### P. Team, structure and security (O+D)

| ID | Feature | Pri | Default | Advanced | Odoo basis |
|---|---|---|---|---|---|
| P1 | Roles: partner, lawyer, trainee, secretary/clerk, accountant, (portal) client; department roles kept | MUST | presets set by the mode | custom combinations | `res.groups` (the showcase has 2; the suite has 5) |
| P2 | Lawyer profile: Bar number, **licence class and date**, training path and supervisor, grade | MUST (Bar no., class) | 3 fields | history | `res.users` / `hr.employee` extension |
| P3 | Matter visibility: office-wide (default for small offices) or **team-only** | SHOULD | office-wide | team-only rule; ethical wall per matter | record rules (never driven by the mode switch) |
| P4 | Multi-branch (Baghdad, Erbil, Basra) and multi-company | COULD | — | branch field, per-branch sequences | `res.company` (CE) |
| P5 | Fee split between partners and origination credit | COULD | — | split % per engagement | custom |
| P6 | Trainee supervision: documents need supervisor review | SHOULD | — | review step | activity-based |

### Q. POA register (O+D)

| ID | Feature | Pri | Default | Advanced | Odoo basis |
|---|---|---|---|---|---|
| Q1 | POA record: type (general/special/judicial/consular), notary office, number, date, principal, agents, substitution allowed, scope, the original's location, scan | MUST | 6 fields + scan | bodies covered, legalisation | port `legal.poa` |
| Q2 | Validity and expiry warning (30 days), revocation with date and reason, linked matters flagged | MUST | status chip | revocation wizard | port `legal.poa.revoke` |
| Q3 | "Confirmation of issuance (صحة صدور)" requests | SHOULD | a sub-step | — | procedure step |
| Q4 | Require an active POA before the first hearing | COULD | warning | block | constraint |

### R. Execution (O+D)

| ID | Feature | Pri | Default | Advanced | Odoo basis |
|---|---|---|---|---|---|
| R1 | Execution stage: office (دائرة تنفيذ …), file number, date opened, notification date, 7-day voluntary period countdown | SHOULD | a stage on the ribbon | measures (attachment, travel ban, detention, auction) with dates | custom, on the matter |
| R2 | Collections via execution → client funds → fee deduction → payout | SHOULD | "collection received" | — | J4 |

### S. Government transactions (O+D) — SAG's core

| ID | Feature | Pri | Default | Advanced | Odoo basis |
|---|---|---|---|---|---|
| S1 | Transaction on a client company at a body (ministry → department), with steps, required documents, fees and receipt numbers | MUST | the showcase's intake (company → ministry → department) kept, plus steps | procedure templates per transaction type | showcase models + port `legal_procedure` |
| S2 | Recurring annual obligations per client company (renewals, clearances) | SHOULD | "upcoming for this client" | generation from templates | port `legal.obligation.schedule` |
| S3 | Runner's day list per body | SHOULD | a list | route by body | filter/group |
| S4 | Billing per transaction (tariff) or covered by the retainer | MUST (O) | from the engagement | tariff table | B2 |

### T. Configuration and onboarding (O+D)

| ID | Feature | Pri | Default | Advanced | Odoo basis |
|---|---|---|---|---|---|
| T1 | **Mode + presets + switches** (§8) on one settings page | MUST | a preset chosen at install (a one-question wizard) | individual switches | `res.config.settings` + `implied_group`s |
| T2 | Iraqi seed data: courts, remedy periods, disbursement categories, government bodies, fee rates (§4), all editable and `noupdate` | MUST | loaded | source and verification status visible | XML data |
| T3 | Currency setup: activate IQD (rounding 1), USD, cash rounding 250 | MUST (O) | automatic | — | `res.currency`, `account.cash.rounding` |
| T4 | Demo data per preset | SHOULD | — | — | demo XML |

---

## 7. Mapping to Odoo 19 Community

Checked against the local `odoo-19.0/addons` tree: the module directory is present, or absent (EE).

| Odoo app / module | Status here | Use for the office | Recommendation |
|---|---|---|---|
| `account` (Invoicing) | **CE, present**. The showcase already depends on it. | Invoices, payments, advances (outstanding credits), journals (client-funds journal), multi-currency, `account.payment.term`, `account.cash.rounding`, credit notes | **Core dependency** (already). Build statements, the client-funds ledger and follow-up ourselves. |
| `analytic` | **CE** (pulled in by `account`) | Analytic account per matter (profitability); `account.analytic.line` as the time-entry store | Use it directly. The analytic line has `name, date, amount, unit_amount, partner_id, user_id, company_id, currency_id, analytic_distribution`; add `matter_id, billable, rate, invoice_line_id, state`. |
| `hr` | CE; the showcase already depends on it (`employee_ids`) | Team members, lawyer profile | Keep (compatibility) |
| `hr_hourly_cost` | CE | Cost of time | Optional (only if time is on) |
| `hr_timesheet` | CE, but **depends on `project`** (`['hr','hr_hourly_cost','analytic','project','uom']`) | — | **Avoid.** A matter would become a `project.project` with competing stages (the roadmap's decision, still right). |
| `project`, `sale_timesheet`, `sale_project` | CE | — | Avoid, for the same reason |
| `hr_expense` | CE | Lawyer reimbursements | Optional bridge. `sale_expense` (re-invoice) needs `sale`: avoid. |
| `sale` / `sale_management` | CE | Quotation with online signature and payment could carry the fee agreement | Not needed: the portal signature form covers signing without pulling in `sale` |
| `portal` | **CE** (includes `static/src/signature_form`) | Client portal, and signing | **Add as a dependency** in office mode |
| `payment`, `account_payment`, `payment_custom` | CE | Pay an invoice online; manual transfer instructions | Optional. No Iraqi PSP module ships (ZainCash, FIB, Qi Card absent). |
| `calendar`, `google_calendar`, `microsoft_calendar` | CE | Calendar view; personal sync | Calendar **view** on our hearing model; `calendar.event` mirror optional |
| `mail` (activities, `mail.activity.plan`, templates, chatter) | CE | Tasks, task templates, messages, reminders | Core (already) |
| `base_automation` | CE | Stage-triggered rules | Optional |
| `resource` | CE | Working calendar Sun–Thu, holidays for deadlines | Use it |
| `sms` | CE, **IAP-paid credits** | SMS reminders | Optional only; default to WhatsApp click-to-chat and email |
| `crm`, `survey`, `website` | CE | Lead pipeline, intake questionnaire, public intake form | Optional, COULD |
| `spreadsheet_dashboard`, `digest` | CE | Dashboards, partner digest | Optional |
| `l10n_iq` | CE | Iraqi chart and taxes | Do not force it. When present, map the client-funds account next to it (it has none). |
| `whatsapp` | **EE, absent** | — | Use `wa.me` links |
| `sign` | **EE, absent** | — | Portal signature form |
| `documents`, `knowledge` | **EE, absent** | — | `ir.attachment` + custom OWL document panel |
| `account_accountant`, `account_reports`, `account_followup` | **EE, absent** | Bank reconciliation widget, partner ledger, follow-up | Build: the client statement, the client-funds ledger, overdue reminders |
| `timer`, `timesheet_grid` | **EE, absent** | — | Build: an OWL systray timer and a week grid |
| `sale_subscription` | EE | — | Build: a retainer schedule and cron |
| `approvals`, `appointment`, `helpdesk`, `web_gantt`, `web_map`, `web_cohort` | **EE, absent** | — | Not needed. Approvals stay as the showcase's own `approval_state`. |
| `currency_rate_live` | **EE, absent** | — | Manual rates plus a per-payment override |

**Dependency proposal** (office mode must not burden a department install):

- **mandatory:** `base, mail, hr, account` (as today) plus `portal, resource`;
- **optional bridges** (auto-install when both sides are present): calendar sync, `hr_expense`,
  `hr_hourly_cost`, `crm`, `website`, `sms`.

**Libraries worth considering** (only if they truly help):

- `rapidfuzz` (Python) for fuzzy conflict matching; plain normalisation may be enough;
- `docxtpl` / `python-docx` for Word output of pleadings. Offices file on paper and edit in Word, so
  DOCX output is genuinely useful. It is a server dependency, so check it on Odoo.sh before relying on it.

Everything else fits in OWL and Odoo's bundled libraries.

---

## 8. Office vs in-house department: what exactly differs, and the switches

### 8.1 The differences

| Axis | In-house department (قسم الشؤون القانونية) | Law office (مكتب المحاماة) | Consequence |
|---|---|---|---|
| **Whom the work is for** | Own company or group entities (the showcase's `legal.company` = الشركة التابعة) | **External clients**: persons and companies (الموكّل) | The same model, `legal.company`, relabelled; office clients can also be **individuals** |
| **Money out** | Government fees and expenses paid, charged to cost | Same, but **recoverable from the client** by default (Art. 55) | `recoverable` default flips with the mode |
| **Money in** | None; at most an internal recharge to group companies (analytic or inter-company) | **Fees billed**: invoices, instalments, retainers, payments | The billing features (B, I) are on in office mode |
| **Client money held** | None | **Client funds** (أمانات), advances | J is on in office mode |
| **Time** | Rarely tracked (workload only) | Optional; essential for hourly or USD clients | G is off by default except in the hourly preset |
| **Engagement** | Employment; the request comes from a business unit | **Fee contract + POA** per client; a matter requires an engagement (advanced) | B1 and Q; the "engagement required" switch |
| **Conflicts** | Not a concept (one client) | **Statutory duty** (Arts. 44–45), recorded | A is on in office mode |
| **Who initiates a matter** | An internal **request** from a department or manager, often with **approval** | A client **intake** | Intake wizard vs request wizard; the showcase's approval axis stays for department mode |
| **External counsel** | The department **instructs outside law offices** and receives their invoices (vendor bills) | The office *is* the outside counsel | Department-only feature (see document 03) |
| **Client-facing channel** | Internal (chatter, email to the business unit) | WhatsApp/email updates, statements, **portal**, e-signature | L and M are on in office mode |
| **Confidentiality** | Company-wide visibility is normal | Clients are confidential **between teams**; ethical walls possible | P3 default differs, but it is enforced by **groups and rules**, never by the mode |
| **Terminology** | الشركات التابعة، المعاملة، الطلب، الإدارة المعنية | الموكّلون، القضية / الملف، التكليف، الأتعاب | The label set follows the mode |
| **Numbering** | Transaction number (the showcase: `legal.task` sequence) | Office file number + court case number | C4 |
| **KPIs** | Turnaround, overdue transactions, SLA, spend on outside counsel, exposure | Collections, receivables ageing, WIP, retainers due, utilisation, profitability | Dashboard tiles per mode |
| **Same in both** | Courts, hearings, deadlines, POA, government bodies and transactions, documents, templates, tasks, execution, reports | same | ~70% of the product is shared |

### 8.2 The configuration: one mode, five presets, about twenty switches

`legal_mode` (company-level) drives **labels, menus and defaults**, never security (the suite's
standing rule). Each switch is a `res.config.settings` field, backed where needed by an `implied_group`
that shows or hides menus and fields. Choosing a preset sets the switches; each switch can then be
changed.

| # | Switch | Type | Solo lawyer | Law office | Hourly / international firm | Department | Hybrid (group legal serving group companies; SAG?) |
|---|---|---|---|---|---|---|---|
| 1 | `legal_mode` | office / department / hybrid | office | office | office | department | hybrid |
| 2 | Billing (fees and invoices) | bool | on | on | on | off | on (internal recharge or invoice) |
| 3 | Fee types enabled | multi | lump sum, instalments, success %, consultation | + retainer, per transaction, per hearing | + hourly, capped | — | retainer, per transaction |
| 4 | Engagement required before matter work | bool | off | on | on | off | off |
| 5 | Time tracking and timer | bool | off | off | **on** | off | off |
| 6 | Client funds (أمانات) | bool | off (advances only) | on | on | off | off |
| 7 | Advances on fees | bool | on | on | on | off | on |
| 8 | Conflict check | off / warn / block | warn | warn (partner override) | block (override) | off | off |
| 9 | 20% fee-cap check | warn / block | warn | warn | warn | — | warn |
| 10 | Bar 5% withholding on legal-adviser retainers | bool | off | on | on | — | on |
| 11 | POA register / require POA before a hearing | bool / bool | on / off | on / off | on / on | on / off | on / off |
| 12 | Client updates (WhatsApp/email templates) | bool | on | on | on | off (internal notices) | on |
| 13 | Client portal | bool | off | off (per client) | on | off | off |
| 14 | E-signature on the portal | bool | off | off | on | off | off |
| 15 | Government-transaction register and templates | bool | off | on | off | on | **on** |
| 16 | Execution stage | bool | on | on | on | on | on |
| 17 | Approval axis (the showcase's `approval_state`) | bool | off | off | off | **on** | on |
| 18 | Matter visibility | company-wide / team | company-wide | company-wide | team | company-wide | company-wide |
| 19 | Licence-class check for trainees | off / warn / block | off | warn | warn | off | off |
| 20 | Currencies | IQD + USD, rounding, cash rounding | IQD+USD | IQD+USD | USD-first | IQD | IQD |
| 21 | Analytic account per matter | bool | off | on | on | off | on |
| 22 | Terminology set | derived from 1 | office | office | office | department | department words + "client company" |

**Guarantees the configuration must give** (each needs a test):

1. Switching a department install to office mode adds menus and fields but **no new required field on
   any existing record**. This matters for SAG's 11 matters, 2 companies, 10 ministries and 23 departments.
2. A switch that is off hides its menus, fields, dashboard tiles and settings sub-sections completely.
   A department user sees **nothing** about fees or conflicts.
3. The mode never changes who can read what; only groups and record rules do.
4. Presets are not stored as separate code paths. A preset is only a set of switch values.

---

## 9. Compatibility notes against the showcase (for the spec)

| Showcase field / model | Office-mode treatment |
|---|---|
| `legal.company` (no partner) | Add `partner_id` (`res.partner`, required going forward). Migration: create one partner per existing company from `name/phone/email/address/tax_number`. Add `client_kind` (company / individual). |
| `legal.task.session_date` (one date) | Keep as a **stored computed "next hearing"** fed by hearing records. Migration: each non-empty `session_date` becomes one hearing record. |
| `legal.task.expenses_amount` (Float) | Keep read-only as a computed total of disbursement lines. Migration: one "other" disbursement per non-zero value. |
| `account_move_id`, `account_payment_id`, `expense_account_id` | Keep, deprecated in the UI. New links are one-to-many (invoices, payments, disbursements). |
| `approval_state` + `approver_id` | Kept; shown only when switch 17 is on |
| `lawyer_id` / `lawyer_ids` / `employee_ids` | `lawyer_id` = responsible lawyer; `lawyer_ids` = team; `employee_ids` kept |
| Courts stored as `legal.department` under the ministry "مجلس القضاء الأعلى" | Add a `body_kind` (court / government / notary / execution) and a court degree on `legal.department`. Seed the Iraqi courts as departments so existing links keep working. |
| `task_number` sequence | Stays the office file number; the court case number is a separate field per stage |
| Emoji in selection labels (e.g. "⏳", "✓", "⚠️") | Remove from labels (the suite convention); keep the keys |

---

## 10. Open questions to settle with the owner or SAG

1. **Is SAG an office or a group department?** The data fits both (§2). The answer picks the default
   preset for the upgrade: `hybrid` if unsure.
2. **Which fee arrangements does SAG actually use?** Confirm the §4.3 practice table. Is any work billed
   hourly or in USD?
3. **Does SAG hold client money** (court fees, expert deposits, execution collections)? If yes, J2 is
   MUST at go-live.
4. **Bar order 3021 (2021) amounts.** Are 300k/600k IQD and the 5% share still current? Does SAG act as
   legal adviser under it?
5. **Remedy-period ambiguities**: Art. 54 abandonment days (30 / 15 / 10), Art. 204's 10-day category,
   the labour-court period, and the execution figures. Ship them as editable data flagged "verify", as
   the suite already does.
6. **Art. 63 court-awarded fee rates**: which version is in force? (The 2024 Council of Ministers
   approval was of an amendment. Enactment is not confirmed.)
7. **WhatsApp:** click-to-chat only (free, no API), in line with the owner's standing preference on other
   projects, or is an API wanted later?

---

## 11. Sources

**Iraqi law and institutions**

- Advocacy Law 173/1965, full text: https://wiki.dorar-aliraq.net/iraqilaws/law/4185.html ; also https://www.eastlaws.com/legislation-full-text/ar/iraq/law/22-12-1965/no-173?type=1&id=1817032
- Fee privilege and Art. 63 rates (Supreme Judicial Council): https://www.sjc.iq/view.76105/
- Council of Ministers approval of Art. 63 amendments (Iraqi Bar, 27 Jun 2024): https://lawyers.gov.iq/news/5091/
- Bar Council licence classes (15 Jun 2022): https://lawyers.gov.iq/news/3463/
- Iraqi Bar administrative order 3021 (11 Apr 2021), legal-adviser retainers: https://ulf-iraq.com/wp-content/uploads/2021/04/Iraqi-bar-association_administrative-order_11-04-2021_English.pdf
- Civil Procedure Law 83/1969, text: https://wiki.dorar-aliraq.net/iraqilaws/law/19608.html ; https://www.eastlaws.com/legislation-full-text/ar/iraq/law/10-08-1969/no-83?type=1&id=152749
- Path of a civil lawsuit (SJC): https://sjc.iq/view.2475/
- Abandonment (ترك الدعوى للمراجعة), secondary: https://asjp.cerist.dz/en/article/253311
- Criminal Procedure Law 23/1971, text: https://wiki.dorar-aliraq.net/iraqilaws/law/4895.html
- Execution Law 45/1980: http://wiki.dorar-aliraq.net/iraqilaws/law/3121.html ; https://moj.gov.iq/tashkelat.11/ ; 7-day voluntary period (secondary): https://cm.qu.edu.iq/?page_id=17342
- Judicial Fees Law 114/1981: https://wiki.dorar-aliraq.net/iraqilaws/law/4689.html
- Lawyers' Pension Fund Law 56/1981 and the stamp: https://wiki.dorar-aliraq.net/iraqilaws/law/3069.html ; https://www.azzaman.com/%D9%82%D8%B5%D8%A9-%D8%B7%D8%A7%D8%A8%D8%B9-%D8%B5%D9%86%D8%AF%D9%88%D9%82-%D8%AA%D9%82%D8%A7%D8%B9%D8%AF-%D8%A7%D9%84%D9%85%D8%AD%D8%A7%D9%85%D9%8A%D9%86-%D8%A7%D9%84%D8%B9%D8%B1%D8%A7%D9%82%D9%8A/
- Notaries Law 33/1998: http://wiki.dorar-aliraq.net/iraqilaws/law/17106.html
- POA practice (three originals, criminal POA before a judge), secondary: https://www.ahewar.org/debat/show.art.asp?aid=520249
- Iraqi consulate POA issuance: https://mofa.gov.iq/detroit/?page_id=551&lang=en
- E-Signature and Electronic Transactions Law 78/2012: https://archive3.parliament.iq/ar/2012/09/25/%D9%82%D8%A7%D9%86%D9%88%D9%86-%D8%A7%D9%84%D8%AA%D9%88%D9%82%D9%8A%D8%B9-%D8%A7%D9%84%D8%A7%D9%84%D9%83%D8%AA%D8%B1%D9%88%D9%86%D9%8A-%D9%88%D8%A7%D9%84%D9%85%D8%B9%D8%A7%D9%85%D9%84%D8%A7%D8%AA/ ; https://www.sjc.iq/view.69844/
- Iraqi judiciary e-portal: https://e-court.sjc.iq/ ; launch (INA, 27 Oct 2021): https://ina.iq/ar/local/139643--.html
- Litigation practice (paper filing, fee-recovery cap): https://www.unpredictableblog.com/blog/iraq
- Litigation guide (10% deposit for attachments, 7-day execution): https://muayadandassociates.com/iraq-litigation-guide-qa/
- Court types: https://www.osamatumalegal.com/blog/A-Guide-to-the-Types-of-Iraqi-Courts ; https://www.sjc.iq/Judicial-system-en.php
- CBI 2026 exchange rate (1,300 official; 1,310 / 1,320; parallel ~1,478): https://shafaq.com/en/Economy/Iraq-fixes-2026-budget-at-1-300-dinars-per-dollar ; https://ina.iq/en/economy/44676-cbi-to-finance-ministry-official-exchange-rate-set-at-1300-dinars-in-2026-budget.html

**Products**

- Clio: https://lawyerist.com/reviews/law-practice-management-software/clio/ ; conflict checks: https://help.clio.com/hc/en-us/articles/41182681954331-Run-Conflict-Checks-in-Clio-Manage-and-Clio-Grow ; split billing: https://help.clio.com/hc/en-us/articles/25704317136155-Split-Billing ; evergreen trust: https://help.clio.com/hc/en-us/articles/25386185645595-Set-Up-Evergreen-Trust-Retainers ; KPI benchmarks: https://www.clio.com/resources/legal-trends/benchmarks/
- MyCase: https://www.lawnext.com/2019/10/mycase-adds-e-signatures-online-intake-lead-analytics-dashboards-for-cases-and-leads-and-more.html ; https://www.mycase.com/
- PracticePanther: https://www.practicepanther.com/legal-billing/legal-accounting-software/ ; https://www.practicepanther.com/legal-crm/client-portal/
- Smokeball: https://www.smokeball.com/features/legal-time-tracking-software ; https://www.smokeball.co.uk/feature/legal-document-automation-and-management
- Filevine: https://www.filevine.com/features/deadlines/ ; https://support.filevine.com/hc/en-us/articles/360004150372-Set-Up-Deadline-Chains
- CosmoLex: https://www.cosmolex.com/features/trust-accounting-software/
- Actionstep: https://www.actionstep.com/workflow-automation/ ; https://support.actionstep.com/support/solutions/articles/150000019783-about-actionstep-workflows-admin-
- Rocket Matter: https://www.rocketmatter.com/features/legal-billing/ ; https://lawyerist.com/reviews/law-practice-management-software/rocket-matter/
- LEAP: https://lawyerist.com/reviews/law-practice-management-software/leap/
- Al-Mohamy Pro: https://mohamy.pro/
- Maktabi: https://maktabilawyers.com/
- Law Surface roundup of Arabic products: https://lawsurface.com/%D8%A3%D9%81%D8%B6%D9%84-5-%D8%A8%D8%B1%D8%A7%D9%85%D8%AC-%D8%A5%D8%AF%D8%A7%D8%B1%D8%A9-%D8%A7%D9%84%D9%82%D8%B6%D8%A7%D9%8A%D8%A7-%D9%88%D8%A7%D9%84%D9%85%D8%AD%D8%A7%D9%85%D8%A7%D8%A9-%D9%81%D9%8A/
- CASENGINE: https://casengine.app/
- Lexzur: https://app4legal.com/app4legal-core ; https://www.getapp.com/legal-law-software/a/app4legal/
- Qanooni: https://www.qanooni.ai/ ; Qanoniah: https://qanoniah.com/en
- Other Arabic products: https://www.beveron.com/arabic/lawfirm_software_in_uae_saudi_arabia_qatar.html ; https://mazoonsoft.com/en/our_software/lawyer-system ; https://www.tqniait.com/tqnia_lawyer/ ; https://www.daftra.com/

**Local**

- Showcase: `custom_addons/legal_department_management/models/legal_task.py`, `legal_company.py`, `__manifest__.py`
- Baseline screen: `docs/ldm/evidence/00-baseline/05_task_form.png`
- `docs/external-review/sag-legal-module.md`, `docs/legal-product-roadmap.md`, `docs/phase-2-engagements-and-conflicts.md`
- Suite data: `custom_addons/legal_litigation/data/legal_appeal_rule_data.xml`, `legal_court_data.xml`, `custom_addons/legal_litigation/models/legal_hearing.py`, `legal_judgment.py`
- Odoo: `odoo-19.0/addons/hr_timesheet/__manifest__.py` (depends on `project`), `odoo-19.0/addons/l10n_iq/` (no client-funds account), `odoo-19.0/odoo/addons/base/data/res_currency_data.xml` (IQD rounding 0.001, inactive), `odoo-19.0/addons/portal/static/src/signature_form/`
