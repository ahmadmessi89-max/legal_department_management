# 03 — What an in-house legal department needs (قسم / دائرة الشؤون القانونية)

**Stream:** research 03 of 6 (`docs/ldm/STATE.md`) · **Date:** 2026-09-24
**Question:** what does an *in-house* legal department need from software, globally and in Iraq,
and which part of it must the everyday user see versus find on demand?
**Feeds:** `docs/ldm/SPEC.md` (next step). Sibling documents: 01 showcase audit, 02 prototype
intent, 04 law-office needs, 05 UX benchmark, 06 suite reuse map (§8 here cross-checks 06 B4).

How to read this: §0 is the answer on one page. §3 (roles), §4 (feature catalogue) and §6 (Iraqi data)
are the material the specification copies from. Every statutory figure in §6 carries a confidence
mark: **V** = read in the statute text during this research, **S** = secondary source (court
publication, law-school text, press), **U** = suite content-pack data not re-verified here.

---

## 0. The answer on one page

1. **An Iraqi in-house department's biggest job is not litigation, it is the government counter.**
   SAG's own prototype lists ten bodies and thirty services (tax clearance, registrar filings, chamber
   ID renewal, social-security contributions, traffic annual registrations, notary powers of attorney,
   the managing director's personal tax…), and the production module's ten ministries and 23
   departments are that list. Global legal-ops tools have no equivalent of this, so it is where the
   product must be better than anything bought off the shelf. (§1.2, §4 area C)
2. **Two in-house archetypes, not one.** A *private group's* legal affairs (SAG) is dominated by
   government transactions, powers of attorney and company records. A *public-sector* legal department
   (الدائرة القانونية في وزارة أو دائرة دولة) is dominated by lawsuits for and against the state,
   opinions to the minister, contracts and guarantees, administrative investigations and تضمين
   (making employees compensate damage to public funds). The configuration switch has to cover both, plus
   the law office (doc 04). (§1.1, §6.9)
3. **The matter is one record with a *kind*.** Government transaction, lawsuit, contract, opinion, power
   of attorney, corporate act, compliance filing, investigation. The kind decides which sections,
   stages, checklist and clocks appear. That single decision removes most of the clutter: the showcase
   shows a hearing date on a tax-clearance file because it has no kind. (A1)
4. **Clocks are the product's reason to exist.** A missed appeal window forfeits the right to appeal
   (Civil Procedure Art. 171, **V**). Iraq has more clocks than the two the suite models: 10-day
   cassation for personal-status and final-degree first-instance judgments, criminal cassation running
   from *pronouncement* not notification, execution clocks of 3 and 7 days, and case-abandonment clocks
   (10 days, 3 months + 15 days, 6 months). All must be data with a legal basis and a verification
   flag. (§6.2, §8.2)
5. **Everyday is small.** From vendor practice (LawVu, Checkbox, Legal Tracker) and Nielsen Norman's
   progressive-disclosure rules: at most two levels of disclosure; create a matter with 3 to 6 answers;
   a form header of about 8 facts with one primary action. Everything else sits behind one click
   (expander, optional column, tab), and configuration is manager-only. (§5)
6. **Role homes, not menus.** A runner (معقّب) needs "today's counters and what to carry", a lawyer
   needs "my hearings and closing clocks", a manager needs "what waits for my decision". The showcase
   gives all of them the same dashboard. (§3)
7. **The runner works from a phone at a counter.** Status plus receipt number plus fee plus a photo of
   the receipt must take under 20 seconds on a phone. No global product designs for this. (C4, T2)
8. **Company records are a first-class area (corporate secretarial).** Registration, tax number,
   social-security project number, chamber ID *with its grade*, managing director, general-assembly
   minutes, and every certificate's validity. A tender fails on a براءة ذمة that is valid today but
   not at the closing date. (areas I, J)
9. **Spend management is light in Iraq.** Global ELM tools centre on e-billing (LEDES/UTBMS),
   accruals and invoice review. An Iraqi department's money is government fees paid in cash by runners
   (with advances to settle) and a few external lawyers on fixed or per-stage fees. Build fees,
   advances and the accounting link. E-billing is out of scope. (area N)
10. **Iraq-specific display matters to Arabic users.** Iraqi month names (أيلول, not سبتمبر), a
    Sunday–Thursday week, holidays that follow the Hijri calendar and are fixed each year by the
    endowment offices, and IQD shown in whole dinars. The showcase gets all four wrong or leaves
    them to chance. (§6.4, §8.3)

---

## 1. Scope, method and what counts as "the department"

### 1.1 Three archetypes the one module must serve

| | A. Private group legal affairs | B. Public-sector legal department | C. Law office (doc 04) |
|---|---|---|---|
| Arabic | قسم الشؤون القانونية لمجموعة شركات | الدائرة / القسم القانوني في وزارة أو دائرة دولة | مكتب محاماة |
| Who the work is for | group companies (SAG: `legal.company`), their managing directors | the ministry or directorate itself and its formations | external clients |
| Dominant work | government transactions, powers of attorney, company records, compliance renewals; then litigation and contracts | lawsuits for and against the state, opinions to the minister, contracts, tenders and guarantees, investigation committees, تضمين, state property | litigation and advice billed to clients |
| Money | government fees paid, runner advances, a few external lawyers | court fees, recoveries, guarantees, تضمين amounts | fees billed, retainers |
| Distinctive clocks | tax, social security, registrar, chamber, residency renewals; appeal windows | appeal windows; grievance clocks (30/30/60 days); dispute-committee referrals | appeal windows; billing cycles |
| Evidence in this research | SAG production metadata review; the SAG prototype's service catalogue; the suite's five Iraqi content packs | the published structures of the Central Bank's legal department and a Ministry of Construction legal section; Laws 14/1991 and 31/2015 | doc 04 |

### 1.2 What SAG actually does (from its own prototype)

The prototype (`scratchpad/src/old/src/types.ts`, `OFFICIAL_SUB_SERVICES`) is SAG's statement of
its own work, and it matches the production module's ten ministries and 23 departments
(`docs/external-review/sag-legal-module.md` §3). That the two lists are the same is an inference: the
review read counts, not records.

| # | Body | Services SAG lists |
|---|---|---|
| 1 | هيئة الإعلام والاتصالات (CMC) | reserve or renew a `.iq` domain; P.O. box renewal |
| 2 | الماء والكهرباء | meter and subscription settlement, utility clearance (براءة ذمة خدمية) |
| 3 | دائرة تسجيل الشركات | certify company records (تصديق أوليات), file final accounts, pay fees and lodge applications, صحة صدور of records |
| 4 | الهيئة العامة للضرائب | corporate tax assessment, file tax accounts, company tax clearance, صحة صدور of clearance letters, tax on the salary of a foreign branch manager, renew company IDs |
| 5 | المديرية العامة للمرور | annual vehicle registration (السنوية) in the managing director's name, new badges (باجات), صحة صدور of POAs and papers |
| 6 | الضمان الاجتماعي | pay contributions, inspection reports, clearance, register hires and resignations |
| 7 | الشركة العامة للمعارض والخدمات التجارية | renew chamber of commerce IDs, import licences |
| 8 | اتحاد الناقلين | renew transport-company IDs |
| 9 | دائرة الكتاب العدول | POAs for drivers, lawyers and staff; certify POAs; صحة صدور of POAs; notice and revocation of POAs (إنذار وعزل) |
| 10 | personal tax of the managing director | personal tax assessment and personal clearance |

Litigation appears in SAG's data too (the baseline screens show "دعوى مطالبة بمبلغ عقد توريد" at
محكمة بداءة الكرخ and "استئناف قرار محكمة البداءة"), so the department does both.

### 1.3 Method

- **Repository:** SAG review, roadmap, UX-patterns note, the suite's models and its five Iraqi content
  packs (38 bodies, 67 document types, 23 procedures, 14 recurring obligations), the prototype, the
  baseline screenshots.
- **Statute text:** Civil Procedure Law 83/1969 (the Ministry of Trade's published PDF, text extracted),
  Criminal Procedure Law 23/1971 (PDF, text extracted), State Employees Discipline Law 14/1991,
  Execution Law 45/1980 and Official Holidays Law 12/2024 (gazette PDF).
- **Global practice:** CLOC Core 12, ACC Legal Operations Maturity Model, the Gartner EBMM market
  guide summary, and vendor documentation from LawVu, Mitratech TeamConnect, Brightflag, SimpleLegal,
  Legal Tracker (Thomson Reuters), Checkbox, Josef, Diligent and Athennian (entity management), plus
  Nielsen Norman Group on progressive disclosure.
- **Not done:** no interviews with SAG staff; nothing from SAG's live records.

---

## 2. What the global frameworks say, and how much of it applies here

### 2.1 The functional map

CLOC's Core 12 ([cloc.org](https://cloc.org/cloc-core-12/)) and ACC's 14-function maturity model
([comparison](https://www.gls-startuplaw.com/know-how/comparing-clocs-core-12-and-accs-legal-operations-maturity-model-a-practical-assessment))
describe what a mature in-house function runs. Mapped to product features and weighted for an Iraqi
department:

| Function (CLOC / ACC) | What it means in software | Weight here | Why |
|---|---|---|---|
| Practice operations / Project & process mgmt | matters, stages, templates, checklists, workload | **High** | this is the product |
| Service delivery models | intake, triage, self-service, routing to the right person | **High** for B and larger A | the front door for business units |
| Contract management (ACC) | CLM: request, template, approval, repository, obligations, renewals | **High** in B (tenders), **Medium** in A | public contracts and guarantees |
| Information governance / Knowledge mgmt | document vault, templates, precedents, legislation library | **High** | every counter needs a document set |
| Business intelligence / Metrics & analytics | dashboards, KPIs, exposure | **Medium** | managers report monthly (موقف الدعاوى) |
| Financial management | fees, budgets, accruals, spend | **Medium, but differently shaped** | cash fees and advances, not invoices |
| Firm & vendor mgmt / External resources | outside-counsel panel, engagement, evaluation, e-billing | **Low–Medium** | few firms, paper invoices |
| Technology | integrations, automation | Medium | inside Odoo: accounting, HR, mail |
| Organization health / Training / Strategic planning | people, training, planning | Low | not a software core |
| eDiscovery, legal hold, IP management (ACC) | holds, collections, IP docket | **Low / out** | not Iraqi practice; trademarks as a renewal at most |

### 2.2 What the market converges on

Gartner's 2025 EBMM guide, as the vendors summarise it
([Mitratech](https://clc.mitratech.com/2025-gartner-market-guide-e-billing-and-matter-management),
[LawVu](https://lawvu.com/news/lawvu-recognized-in-the-2025-gartner-market-guide-for-e-billing-and-matter-management-technology/)),
names four core capabilities: e-billing and spend, external matter management, intake/triage/service
management, and workflow automation. The vendor feature sets agree:

- **Matter management:** configurable matter types and templates, triage and assignment with workload,
  deadline tracking, document and email storage, shared grids that filter and group like a
  spreadsheet, dashboards ([LawVu](https://lawvu.com/workspace/matter-management/),
  [TeamConnect](https://mitratech.com/products/teamconnect/features-benefits/)).
- **Intake:** one front door (email, chat, form), smart forms, routing by matter type, expertise,
  workload and business unit, custom statuses the requester can see, self-service for routine work
  ([Checkbox](https://www.checkbox.ai/platform/legal-intake-and-triage),
  [Josef](https://joseflegal.com/blog/3-benefits-of-automating-faqs-for-in-house-legal-teams/)).
- **Spend:** budgets by department, practice area, vendor and matter; accruals; billing-guideline
  enforcement on invoices ([Brightflag](https://brightflag.com/legal-spend-management/),
  [SimpleLegal](https://www.onit.com/products/elm/simplelegal/)).
- **Entity management:** one record per entity, directors and officers with terms, minute books and
  resolutions, a compliance calendar of filings and renewals, structure charts
  ([Diligent](https://www.diligent.com/resources/blog/best-entity-management-software),
  [MinuteBox](https://www.minutebox.com/entity-management/for-generalcounsel),
  [Athennian](https://www.athennian.com/product)).
- **CLM:** seven stages from request to renewal: intake, authoring from templates and clauses,
  negotiation, internal approval, execution, obligation tracking, renewal
  ([Onit](https://www.onit.com/blog/what-is-contract-lifecycle-management/)).
- **Metrics:** Legal Tracker's ten are spend to budget, workload per lawyer and matter cycle time,
  spend by matter type and business unit, outside-counsel evaluations, total legal spend as a share of
  revenue, invoice savings, rate increases, **litigation exposure over time**, training against
  complaints, and **lessons learned per matter**
  ([white paper](https://legal.thomsonreuters.com/content/dam/ewp-m/documents/legal-tracker/en/pdf/white-papers/legal-tracker-top-10-metrics-your-legal-department-should-track-white-paper.pdf)).

**Takeaway for Iraq:** keep matter management, intake, CLM-lite, entity management and metrics. Swap
e-billing for *government fees and runner advances*. Add what no vendor has: the government counter
(service catalogue, document checklist, صحة صدور, follow-up sheet) and the Iraqi statutory clocks.

---

## 3. Roles and jobs-to-be-done

Seven roles. The showcase has two groups, both able to write. The suite has five roles including a
read-only auditor, which the SAG review calls the most valuable part of the security model. The roles
below are *product* roles; groups may combine them.

### 3.1 Legal manager: مدير الشؤون القانونية / رئيس القسم

| # | When… | I want to… | So that… | How often |
|---|---|---|---|---|
| M1 | I open the system in the morning | see, on one screen, what waits for *my* decision and what is at risk: approvals, clocks closing within 7 days, this week's hearings, files stuck at a body past their target, requests nobody has picked up | nothing lapses on my watch | daily |
| M2 | a request or new matter arrives | assign it to a lawyer or runner with their current load visible | work is balanced and has one owner | daily |
| M3 | someone asks to file, settle, pay a fee above a threshold, sign or issue a POA | approve, return with a reason, or reject in one click from a queue | decisions are recorded and fast | daily |
| M4 | the managing director or minister asks "where are we on X?" or "how many cases are against us, and for how much?" | answer in under a minute, and print it | the department looks in control | weekly |
| M5 | a clock is about to lapse and its owner hasn't acted | be escalated to automatically | I intervene before it's lost | as needed |
| M6 | a month ends | print the monthly status report (موقف الدعاوى والمعاملات), with fees by company | management gets its report | monthly |
| M7 | a lawyer leaves or goes on leave | reassign all their matters, clocks and POAs in one action | nothing is orphaned | occasional |
| M8 | a circular changes a procedure or a fee | edit the service, checklist or fee myself | no developer, no release | occasional |

**Home:** an attention board (M1) plus the approval inbox. **Never:** has to open a file to find out
whether it needs them.

### 3.2 Lawyer: محامٍ / مشاور قانوني / حقوقي

(A حقوقي is a law-graduate employee, common in the public sector, who may represent the entity by
authorisation without being a practising advocate.)

| # | When… | I want to… | So that… | How often |
|---|---|---|---|---|
| L1 | I plan my week | see my hearings (court, case number, what is required) and my closing clocks | I'm prepared and on time | daily |
| L2 | I leave a hearing | record what happened and the next date in under 30 seconds, from a phone | the next hearing and reminder exist without re-typing | after every hearing |
| L3 | a judgment is notified to us | enter the notification date and see the last day to object, appeal or seek cassation, marked non-extendable, on my agenda and my manager's | the right to challenge isn't lost | per judgment |
| L4 | I need a letter, pleading or notice | generate it from a template with the case data (parties, court, case number, dates) | I don't retype and don't mistype | several times a week |
| L5 | a colleague or business unit asks a question | find earlier opinions on the same point, then issue mine as a numbered, frozen opinion | the advice is consistent and citable | weekly |
| L6 | a contract comes for review | see the request, the draft, the counterparty's history and earlier contracts, then approve or return it | review is quick and recorded | weekly |
| L7 | I go to court or a body for a company | know which POA authorises me, where the original is, and whether it's still valid | I'm not turned away | weekly |

**Home:** "my agenda" (hearings and clocks) plus "my files" grouped by next action.

### 3.3 Clerk / runner / registry clerk: معقّب / موظف متابعة / مخوّل مراجعة / موظف الصادر والوارد

| # | When… | I want to… | So that… | How often |
|---|---|---|---|---|
| R1 | I start my round | see today's files by body, each with the checklist of documents to carry, and print the follow-up sheet (استمارة متابعة) | one trip per counter, nothing forgotten | daily |
| R2 | I'm at the counter | update the status (submitted, returned for completion, waiting for صحة صدور, done), the receipt number, the fee paid and a photo of the receipt, from my phone, in under 20 seconds | the office knows without a call | several times a day |
| R3 | I need cash for fees | request an advance (سلفة) and settle it later against receipts | money is accounted for | weekly |
| R4 | before leaving the office | see which documents are missing or expired for today's files | I don't make a wasted trip | daily |
| R5 | a letter comes in or goes out (registry clerk) | register it with its number and date, the body and the subject, and link it to the file | "what did we send the Registrar last quarter" has an answer | daily |

**Home:** "today's counters" (a list grouped by body) on a phone-width screen.

### 3.4 Business requester: طالب الخدمة

HR, procurement, finance, projects, branch managers and the managing director's office. In the
public sector, the other directorates of the ministry.

| # | When… | I want to… | So that… |
|---|---|---|---|
| Q1 | I need something from legal (a contract review, an opinion, a POA, a government transaction, help with a dispute) | fill a short form with attachments and get a reference number | I don't have to chase by phone |
| Q2 | I'm waiting | see the status and the expected date | I can plan |
| Q3 | legal needs more information | be told what exactly, and answer in the same place | the request isn't silently stuck |
| Q4 | it's something routine (NDA, standard POA wording, a document list for a service) | help myself to the template or checklist | legal isn't a bottleneck for routine work |
| Q5 | it's done | receive the result (approved contract, opinion letter, copy of the POA) | the loop closes |

**Home:** "my requests" and one "new request" button. **Never:** sees other departments' requests,
privileged analysis or fees.

### 3.5 Executive: المدير المفوض / الرئيس التنفيذي / مجلس الإدارة (public sector: الوزير / المدير العام)

| # | Job |
|---|---|
| X1 | See exposure at a glance: the number and value of cases for and against us, the trend, the five largest |
| X2 | See compliance readiness per company: are the tax clearance, social-security clearance, chamber ID of the right grade and registration valid, today and at a given tender's closing date? |
| X3 | Decide what the rules reserve for them (settling, suing a government body, large contracts) from the same approval queue, on a phone |
| X4 | Receive a one-page monthly summary |

**Home:** a read-only summary board. **Never:** edits operational records.

### 3.6 Auditor: المدقق الداخلي / ديوان الرقابة المالية / ضابط ارتباط النزاهة

| # | Job |
|---|---|
| U1 | Read every record and change none; no write buttons shown at all |
| U2 | See the full trail: who changed which field and when, who approved what, and the reasons for returns and cancellations |
| U3 | Reconcile fees: each fee line against its receipt and its accounting entry |
| U4 | Sample and export lists; see cancelled and archived records (nothing is hard-deleted) |

### 3.7 External counsel (optional)

Assigned to a matter; reports hearing results. **MUST** work without a login (the lawyer records the
result); a portal is **COULD**.

---

## 4. Feature catalogue

**Priority** is MoSCoW for archetype **A (private group)** / **B (public sector)** where they differ.
**Everyday** is what the daily user sees without asking. **On demand** is one click away (expander,
optional column, tab, filter) or in configuration. **Refs** names the showcase field or feature
(`ldm:`), the suite donor (`suite:`) or an external source.

### A. The matter (the file): `legal.task`

| ID | Feature | Pri | Everyday | On demand | Refs / notes |
|---|---|---|---|---|---|
| A1 | **Matter kinds** (government transaction, lawsuit, contract, opinion, POA, corporate act, compliance filing, investigation, other) that decide sections, stages, checklist, numbering and clocks | MUST | create asks the kind first; the form shows only that kind's sections | kind configuration: sections enabled, stages, prefix, default approver, checklist, SLA | ldm: none. There is one form for everything, so a tax clearance carries a hearing date |
| A2 | **Header strip** | MUST | reference, title, kind, company, body/court, responsible, status, next date with days left, urgent flag | team, tags, cost centre, external references | ldm: facts split across two groups plus 7 header buttons (baseline 05) |
| A3 | **Stages per kind** in Iraqi vocabulary (§6.8) | MUST | status bar with ≤6 stages; one primary action for the current stage | stage editor; time in each stage (`statusbar_duration`); rules on entering a stage (required fields and documents) | ldm: draft / in progress / pending docs / done / cancelled, plus a separate approval_state |
| A4 | **Follow-up log (سجل المتابعة):** structured entries of date, action, result, next step, receipt number, fee | MUST | one-line quick add; newest first | attachment per entry, body officer seen, attendees | prototype had `LawyerActionStep`; ldm has chatter only |
| A5 | **Next action always owned** | MUST | next date and owner on every open matter; overdue in red | activity types, escalation rules | Odoo activities |
| A6 | **Urgency** | MUST | one toggle (عاجل) | reason | ldm: `is_urgent` (label carries an emoji) |
| A7 | **External numbers** (court case number and year, the body's file number, letter numbers) | MUST | one "رقم الدعوى / رقم المعاملة" field | several typed identifiers | |
| A8 | **Find by any number** | MUST | the search box accepts reference, case number, letter number or receipt number | the QR on the printed sheet opens the matter | suite: open-by-code |
| A9 | **Related matters** (an appeal linked to its case; a lawsuit arising from a contract) | SHOULD | "related" chips | parent/child; auto-link a challenge to its judgment | |
| A10 | **Confidential matters** visible only to named members and the manager | SHOULD / **MUST** | a lock icon | per-kind default (investigations are confidential by default) | suite: confidentiality on requests and opinions |
| A11 | **Close with an outcome** (result, amount won, lost or saved, one-line lesson) | SHOULD | outcome select plus amount | outcome taxonomy; lesson pushed to knowledge | Legal Tracker metric 10 |
| A12 | **Bulk reassign** | SHOULD | select, then reassign | handover note | M7 |
| A13 | **Extra fields per kind without code** | SHOULD | hidden until defined | Odoo 19 Community `fields.Properties` with its definition on the kind, as `project.task` does with `task_properties_definition` | answers "advanced fields available" without clutter |
| A14 | **Checklist template per kind or service** | MUST (gov. transactions) / SHOULD | checklist panel on the matter | template editor | suite: procedure engine (06 C1: take the small version) |

### B. Intake and requests

| ID | Feature | Pri | Everyday | On demand | Refs / notes |
|---|---|---|---|---|---|
| B1 | **"New" in the primary navigation**, answered in ≤4 steps: what → for whom → where → essentials | MUST | a stepper that fills the rest from defaults | full form after creation | ldm: a top-level wizard (company → ministry → department). Keep the idea; SAG review idea 1 |
| B2 | **Service catalogue per body** (§1.2): choose "تجديد هوية غرفة التجارة" and the matter knows the body, checklist, fee and clock | MUST / COULD | type-ahead search over services | catalogue editor | prototype `OFFICIAL_SUB_SERVICES` |
| B3 | **Request form for non-legal staff** (category, subject, description, attachments, needed-by) | SHOULD / **MUST** | 5 fields | confidentiality, related party, cost centre | suite `legal.request` |
| B4 | **Triage queue** | SHOULD | unassigned requests with a suggested owner and each lawyer's load | routing rules by category, company and value | Checkbox, LawVu |
| B5 | **Requester sees status and expected date** | SHOULD | "my requests" | notifications on each change | Q2 |
| B6 | **Return for completion with a reason** | MUST | a button that requires the reason | reason taxonomy | suite `legal.request.return` |
| B7 | **Convert a request into a matter, contract or opinion, keeping its history** | SHOULD | one click | mapping rules | suite `converted_ref` |
| B8 | **Email intake** (an alias creates a request) | COULD | – | one alias per category | Odoo `mail.alias` |
| B9 | **Self-service answers and templates** before asking | COULD | "before you ask" suggestions on the form | knowledge articles | Josef, Checkbox |
| B10 | **Target response date per category** | SHOULD | the due date shown on the request | SLA rules | |

### C. Government transactions: المعاملات الحكومية (the core of archetype A)

| ID | Feature | Pri | Everyday | On demand | Refs / notes |
|---|---|---|---|---|---|
| C1 | **Body tree** (ministry → directorate → section or counter) | MUST | choose a body by typing any level's name | tree admin, working hours, calendar, contacts, address, salutation (the "السيد … المحترم" line) | ldm: `legal.ministry` → `legal.department` (two levels, keep them); suite `legal.gov.body` + types |
| C2 | **Required-documents checklist per service**, drawn from the company's document vault | MUST | chips: have / missing / expired | rules per requirement: original or copy, certified or not, freshness | suite `legal.doc.requirement` |
| C3 | **Steps of the transaction** | SHOULD | a rail of 3 to 6 steps | step configuration, transitions, facts captured at a step | suite: residency pack turns the prototype's 13 visa states into data |
| C4 | **Counter visit with receipt and fee**, from a phone | MUST | quick add (status, receipt number, amount, photo) | officer's name, queue number | R2 |
| C5 | **صحة صدور (verification of issuance)** as a tracked state with its letter number | MUST | status "بانتظار صحة الصدور" | per document; for notary POAs record the QR reference (paper verification abolished October 2024) | [Alsumaria, 30 Oct 2024](https://www.alsumaria.tv/news/localnews/504835/) |
| C6 | **Printed follow-up sheet (استمارة متابعة)** | MUST | a print button | a QR that opens the matter | SAG review idea 10 |
| C7 | **Time at the body in working days**, with a target per body | SHOULD | "at the body for 6 working days" | SLA rules and escalation per body | suite `legal.sla.rule`, working calendars |
| C8 | **Coverage per company**: which bodies and services are current | SHOULD | cards on the company dossier | matrix report | suite `legal.entity.coverage`; ldm `department_cards_html` is an unsearchable HTML blob |
| C9 | **Batch creation** (the same annual renewal for 12 companies) | SHOULD | "create for companies…" | – | group reality |
| C10 | **Tender readiness**: which certificates are valid *at the closing date* for a given company | SHOULD | one check per company and date | rule sets per tender type | suite chamber and tax packs; the Baghdad Governorate tender wording |
| C11 | **Officer contacts per body** | COULD | contact list | notes | suite `legal.gov.body.contact` |

### D. Litigation: الدعاوى

| ID | Feature | Pri | Everyday | On demand | Refs / notes |
|---|---|---|---|---|---|
| D1 | **Lawsuit facts**: court, case number/year, our role (plaintiff, defendant, third party), opponent, subject, claim value in IQD, lawyer | MUST | 6 fields on create | table of parties with capacities, claim breakdown, related contract | suite `legal.lawsuit` |
| D2 | **Hearings** and the weekly hearing roll | MUST | next hearing on the card; printable roll for the week | calendar, hall or judge, attendance | ldm: one `session_date` field; suite `legal.hearing` |
| D3 | **"What happened at the hearing"** in one step: outcome, next date, task | MUST | a short dialog | minutes attached | L2 |
| D4 | **Judgment and appeal window**: notification date → last day, non-extendable | MUST | countdown with a "non-extendable" badge and the article number | rule table with verification status; the two-date display ("safe date" and "legal last day") from 06 B4 | suite `legal.judgment`, `legal.appeal.rule` (corrections in §8.2) |
| D5 | **Challenge chain** (objection → appeal → cassation → correction) linked | SHOULD | chips on the case | child records | |
| D6 | **Clocks inside a case**: left for review (10 days), agreed suspension (3 months + 15 days), interruption (6 months) | SHOULD | alerts on the agenda | rules | Civ. Proc. Arts. 54, 82, 83, 87 (**V**) |
| D7 | **Execution (التنفيذ)**: file number at the directorate, amount, collected so far, its clocks (7/3/7 days) | SHOULD / **MUST** | an execution section on the case | seizure details | Execution Law 45/1980 (**S**) |
| D8 | **Exposure**: claim value, likely outcome, provision | SHOULD | exposure on the manager's board | probability scale, provision for accounting | Legal Tracker metric 8 |
| D9 | **Criminal complaints (شكوى)** at an investigation court: embezzlement, bounced cheques, public funds | SHOULD | complaint date, court, status | the 3-month complaint clock | Crim. Proc. Art. 6 (**V**) |
| D10 | **Settlement proposal and its approval** | SHOULD | approval request | terms | M3 |
| D11 | **Court fees and expenses** | MUST | fee lines | accounting link | |
| D12 | **Employee-court and administrative cases**, with their grievance clocks | COULD / **MUST** | variants of the lawsuit kind | clocks 30/30/60 | Law 14/1991 Art. 15 (**V**) |

### E. Deadlines and calendar: المواعيد

| ID | Feature | Pri | Everyday | On demand | Refs / notes |
|---|---|---|---|---|---|
| E1 | **One agenda for every clock**: hearings, appeal windows, due dates, renewals, obligations, POA and document expiries | MUST | "my week" list plus a calendar | filters by kind, company, body | suite `legal_deadline` (a union) |
| E2 | **Working calendar** (Sunday to Thursday) and holidays held as data | MUST | invisible, but it moves computed dates | yearly holiday entry; closures per governorate (holy cities may close up to 3 days) | Law 12/2024 (**V**) |
| E3 | **Reminders and escalation**: lead days, then escalation to the manager if not done | MUST | activities and email | rules per kind | M5 |
| E4 | **Last-day computation** that rolls forward over holidays, plus the non-extendable badge | MUST | the badge | a tooltip that shows the rule and article | Civ. Proc. Arts. 25(2), 171 (**V**) |
| E5 | **Month calendar** and a weekly print | SHOULD | – | – | ldm: calendar keyed on `session_date` |
| E6 | **Hijri date shown next to the Gregorian** where useful (holidays) | COULD | – | the browser's own `Intl` supports `islamic-umalqura`; no library needed | |

### F. Contracts and guarantees

| ID | Feature | Pri | Everyday | On demand | Refs / notes |
|---|---|---|---|---|---|
| F1 | **Contract register**: parties, type, value, start, end, notice period, status, file | MUST | 6 fields | clauses, payment terms | suite `legal.contract` |
| F2 | **Request → review → approval → signature → in force** | SHOULD / **MUST** | stage rail | reviewer routing by value and type | CLM stages |
| F3 | **Arabic templates with merge fields** | SHOULD | "from template" | clause library (COULD) | |
| F4 | **Expiry and renewal alerts** | MUST | chip "ends in 30 days" | auto-renewal logic | |
| F5 | **Obligations** (payments, deliveries, reports) | COULD / SHOULD | – | recurring instances | suite `legal.contract.obligation` |
| F6 | **Letters of guarantee (خطابات الضمان)**: bid, performance, advance payment; bank, amount, expiry, release | SHOULD / **MUST** | expiry chips | extension and release workflow | Government Contracts Instructions 2/2014: performance guarantee 5% of contract value, lodged after the award letter and before signing (**S**) |
| F7 | **Amendments and annexes (ملاحق)** | SHOULD | list on the contract | – | suite `legal.contract.modification` |
| F8 | **E-signature** | WON'T | – | – | Odoo `sign` is Enterprise; Iraqi practice is wet ink and stamp |

### G. Opinions and advice: الرأي القانوني والاستشارات

| ID | Feature | Pri | Everyday | On demand | Refs / notes |
|---|---|---|---|---|---|
| G1 | **Formal opinion**: question → analysis → conclusion → issued with a register number → frozen; revisions supersede | SHOULD / **MUST** | question, conclusion | factual background, legal basis with source link and "last verified", reviewer and approver | suite `legal.opinion` (issue-then-freeze). In a ministry this is the core job: "إبداء الرأي فيما يحال من الوزير" |
| G2 | **Quick advice log** (a two-line consultation) | SHOULD | one line | – | the volume that proves the department's value |
| G3 | **Searchable precedents** | SHOULD | search | tags, subject tree | |

### H. Powers of attorney: الوكالات

| ID | Feature | Pri | Everyday | On demand | Refs / notes |
|---|---|---|---|---|---|
| H1 | **POA register**: type (general, special, advocate's, registration, authorisation of a runner), principal (company or managing director), agents, scope, notary office, number, date, expiry, QR reference, who holds the original | MUST | list with expiry chips | scope detail, bodies covered | suite `legal.poa`; prototype notary category |
| H2 | **Revocation (عزل) by notarial notice (إنذار عدلي)**, with notice to the agent | MUST | a "revoke" action that opens the notary transaction | – | the Ur portal lists "إجراءات إنذار وعزل وكيل" as a Ministry of Justice service |
| H3 | **Who can act for company X at body Y today?** | SHOULD | a lookup | – | L7 |
| H4 | **Verification of issuance** recorded | MUST | status | QR since October 2024 | C5 |
| H5 | **Advocate's POA per case (وكالة بالخصومة)** linked to lawsuits | SHOULD | – | – | |

### I. Corporate secretarial and entity management

| ID | Feature | Pri | Everyday | On demand | Refs / notes |
|---|---|---|---|---|---|
| I1 | **Group entity**: legal form, registration number, tax number, social-security project number, chamber number, capital, managing director, address | MUST / COULD | dossier header | identifier table | ldm `legal.company`; suite `legal.entity` + identifier kinds |
| I2 | **Entity document vault with validity** (certificate, articles, chamber ID and grade, clearances…) | MUST | red / amber / green chips | validity model: expiry, freshness (a utility bill goes stale) or permanent | suite `legal.expiry.mixin`, document types |
| I3 | **Officers and shareholders** (managing director, board, authorised signatories, shareholdings) with history | SHOULD | – | – | suite `legal.signatory` |
| I4 | **General-assembly and board meetings → minutes → resolutions → filing with the registrar** | SHOULD | – | – | Diligent, Athennian; Companies Law 21/1997 |
| I5 | **Group structure chart** | COULD | – | Odoo Community `web_hierarchy` view | |
| I6 | **Corporate changes as services** (capital increase, address change within 7 days, amendment of the articles, branch opening) | SHOULD | via area C | – | registrar pack (**U**) |
| I7 | **Licences and registrations per entity** (import licence, contractor classification with the Ministry of Planning, investment licence, practice licence, `.iq` domain, trademarks) | SHOULD | chips | – | |

### J. Recurring compliance obligations

| ID | Feature | Pri | Everyday | On demand | Refs / notes |
|---|---|---|---|---|---|
| J1 | **Obligations calendar per entity** (§6.7) | MUST / SHOULD | "due this month" | schedule rules with lead days | suite `legal.obligation.schedule` |
| J2 | **Each due instance becomes a matter automatically** at its lead time | SHOULD | – | – | |
| J3 | **Evidence of compliance** (the receipt) on the instance | SHOULD | – | – | |
| J4 | **Change log of circulars (تعميمات)** that altered an obligation | COULD | – | "last verified on" per rule | |
| J5 | **Foreign staff residency, work-permit and passport expiries** | SHOULD (groups with expatriates) | – | link to `hr.employee` when HR is installed | residency pack |

### K. Correspondence: الصادر والوارد

| ID | Feature | Pri | Everyday | On demand | Refs / notes |
|---|---|---|---|---|---|
| K1 | **Outgoing and incoming register** (number, date, body, subject, linked matter) | MUST | quick register | several registers; voiding with a reason | suite `legal.correspondence` |
| K2 | **Official letter** in Iraqi form: العدد / التاريخ, إلى / م, the salutation, subject, body, signature, copies to | MUST | "write letter" from the matter | letter templates | |
| K3 | **Awaiting-reply clock** | SHOULD | chip | – | |
| K4 | **Printed register book** | SHOULD / **MUST** | – | – | public-sector audit expects it |

### L. Documents and templates

| ID | Feature | Pri | Everyday | On demand | Refs / notes |
|---|---|---|---|---|---|
| L1 | **Attachments per matter, typed** | MUST | drag and drop, preview | category, scanned by | ldm many2many attachments; prototype categories |
| L2 | **Photo or scan from a phone** | SHOULD | camera upload | – | R2 |
| L3 | **Templates → PDF (QWeb) and, where the user must edit, DOCX** | SHOULD | "generate" | template editor for managers | prototype had a template editor |
| L4 | **Versions (supersede)** | COULD | – | – | |
| L5 | **Full-text search inside documents** | COULD | – | – | |

### M. Approvals and control

| ID | Feature | Pri | Everyday | On demand | Refs / notes |
|---|---|---|---|---|---|
| M-1 | **Approval rules** by kind, action and amount (file, settle, pay above a threshold, sign, issue a POA) | MUST | a "request approval" button; the approver's inbox | rule editor; several levels | ldm `approval_state`; suite `legal.approval.queue` |
| M-2 | **Approve / return / reject with a reason**, time-stamped | MUST | inline in the inbox | – | |
| M-3 | **Preparer is not the approver** (separation of duties) | SHOULD | – | – | suite |
| M-4 | **Delegation during leave** | COULD | – | – | |
| M-5 | **Lock after approval or closing**; reopening needs a reason | SHOULD | – | – | U2 |

### N. Money

| ID | Feature | Pri | Everyday | On demand | Refs / notes |
|---|---|---|---|---|---|
| N1 | **Government and court fees per matter**, each with its receipt number | MUST | fee line | fee schedule per service | ldm `expenses_amount` (a Float with no currency); suite `legal.fee.rule` |
| N2 | **Accounting link** (journal entry or payment) | SHOULD | "post" for finance | expense account per kind | ldm `account_move_id`, `account_payment_id` (keep) |
| N3 | **Runner advances (سلفة)** and their settlement against receipts | SHOULD | "my advance: balance" | – | R3 |
| N4 | **Outside counsel**: directory (with Bar registration), assignment, fee agreement (fixed, per stage, percentage), payments, evaluation at close | SHOULD | – | – | Legal Tracker metric 4 |
| N5 | **Budget per company and year**, spend against budget | COULD | – | – | Brightflag, SimpleLegal |
| N6 | **Recoveries** (collected through execution) | SHOULD | – | – | |
| N7 | **E-billing (LEDES/UTBMS), firm accruals, invoice review** | WON'T | – | – | not Iraqi practice |
| N8 | **IQD by default, shown in whole dinars; USD as a second currency** | MUST | – | – | §6.4 |

### O. Investigations and discipline (public sector)

| ID | Feature | Pri | Everyday | On demand | Refs / notes |
|---|---|---|---|---|---|
| O1 | **Investigation committee (لجنة تحقيقية)**: order number, members (one must hold a law degree), subject, employees concerned, statements, recommendation, decision | COULD / **MUST** | – | – | Law 31/2015 (**S**) |
| O2 | **تضمين proceedings**: damage amount, responsible employee, decision, challenge | – / **MUST** | – | – | [Law 31/2015](https://sjc.iq/view.70276/) |
| O3 | **Disciplinary penalty and its grievance clocks** (30 / 30 / 30 days) | – / **MUST** | – | – | Law 14/1991 Art. 15 (**V**) |
| O4 | **Requests from the Integrity Commission and the Federal Board of Supreme Audit**, and the answers | – / SHOULD | as correspondence plus a matter | – | |
| O5 | **Referral to the Ministry of Justice government-dispute committees** instead of court | – / **MUST** | a lawsuit variant | – | Council of Ministers decisions of 11 Nov 2020 and 1 Sep 2021 (**S**, [manshurat](https://manshurat.org/node/74349)) |
| O6 | **State property and leases (أملاك)** | – / COULD | – | – | appears in the Ministry of Construction's legal-section duties |

### P. Knowledge

| ID | Feature | Pri | Refs / notes |
|---|---|---|---|
| P1 | **Legislation library**: laws and circulars with a source link and "last verified" date | SHOULD | suite pattern (`legal_basis_url`, `last_verified_on`) |
| P2 | **Templates library** (letters, notices, contracts, POA wording) | SHOULD | |
| P3 | **Lessons learned per matter** | COULD | Legal Tracker metric 10 |
| P4 | **Body know-how** on the body record: what the counter actually asks for, and tips | SHOULD | the suite's `desk_hint` pattern |

### Q. Dashboards, KPIs and reports

| ID | Feature | Pri | Notes |
|---|---|---|---|
| Q1 | **Manager's attention board** (M1) | MUST | replaces the showcase's KPI cards plus recent list |
| Q2 | **KPI set**: open matters by kind and stage; overdue; clocks closing within 7 days; hearings this week; days at the body against target; requests waiting for triage; approvals waiting; expiring documents, licences and POAs (30/60 days); obligations due; fees this month by company; workload per lawyer; cycle time per kind; litigation exposure for and against; recoveries | SHOULD | every figure clickable to its list (Odoo's own dashboard-kanban pattern) |
| Q3 | **Executive summary**: exposure, readiness, top risks | SHOULD | X1, X2 |
| Q4 | **Printed reports**: company file, general oversight, follow-up sheet (all three exist in ldm); weekly hearing roll; POA register; expiring-documents list; the monthly status report (موقف الدعاوى / المعاملات) | MUST (existing three and the monthly report) / SHOULD | the monthly report is standard in ministries |
| Q5 | **Pivot and graph analyses** | SHOULD | ldm has none |
| Q6 | **Excel export** | MUST | Odoo native |

### R. Security and audit

| ID | Feature | Pri | Notes |
|---|---|---|---|
| R1 | **Roles**: manager, lawyer, clerk/runner, requester, executive (read-only boards), auditor (read-only everything), configuration admin | MUST | ldm has 2 groups; suite has 5 (06 A1) |
| R2 | **Visibility**: a lawyer sees their own and their team's matters, or the whole department, as a setting | MUST | public-sector departments are often "see all" |
| R3 | **Audit trail**: tracking on key fields, an approvals log, cancel or archive with a reason, never hard-delete | MUST | U2, U4 |
| R4 | **Several group companies** as `legal.company`, alongside Odoo's own `res.company` | MUST | keep SAG's model |
| R5 | **Confidential matters** | see A10 | |

### S. Configuration

| ID | Feature | Pri | Notes |
|---|---|---|---|
| S1 | **Mode**: private department / public-sector department / law office. It drives terminology, menus and defaults, never security | MUST | roadmap §3; 06 A2 |
| S2 | **Feature switches per area** (litigation, contracts, POA, corporate secretarial, obligations, investigations, outside counsel, budgets) | MUST | an area switched off leaves no menu and no field behind: the main anti-clutter lever |
| S3 | **Iraqi seed content** (bodies, services, document types, courts, periods, holidays) as data with a verification status | MUST | 06 B5; opt-in packs |
| S4 | **First-run checklist**: company data, users and roles, bodies | SHOULD | |

### T. Notifications and mobile

| ID | Feature | Pri | Notes |
|---|---|---|---|
| T1 | **Notifications** for assignment, approvals and due clocks (Odoo inbox and email) | MUST | |
| T2 | **Phone-usable screens** for the runner and for the lawyer at court: large targets, one column, camera | MUST | R2, L2 |
| T3 | **Share status to a requester by WhatsApp click-to-chat** | COULD | no API; the browser's `wa.me` link |
| T4 | **Daily digest email** to the manager | SHOULD | |

---

## 5. Everyday versus on demand: the rules that decide the split

### 5.1 Three tiers

| Tier | Who sees it | How it appears | Examples |
|---|---|---|---|
| **1. Everyday** | the role that does the work | without any click | status, next date, the primary action, the checklist, the countdown |
| **2. On demand** | the same role, when needed | one click: an expander ("تفاصيل إضافية"), an optional list column, a tab, a filter, a per-kind Properties field | parties table, external identifiers, cost centre, officer contacts, time in each stage |
| **3. Configuration** | manager or admin | settings, the kind and body forms, content packs | stages, checklists, fee schedules, rules, feature switches |

Nielsen Norman Group's rules ([progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/)):
the split has to come from task frequency; it must be obvious how to reach tier 2; and **no more than
two levels**, because users get lost past that. A wizard (staged disclosure) suits steps that don't
depend on each other: intake, yes; editing a live matter, no.

### 5.2 Screen budgets (proposed; the specification should test them)

| Surface | Budget |
|---|---|
| Create a matter | **3–6 answers**, depending on kind (below); everything else defaulted from kind, service, company and user |
| Form header | about **8 facts** and **one** primary button; the other actions in a single "إجراءات" menu |
| List | ≤ **6** visible columns; the rest `optional="hide"` |
| Kanban card | ≤ **4** lines |
| Menu per role | ≤ **7** top entries (the manager also gets configuration) |
| Status names | plain Arabic nouns (§6.8), no codes, no emoji |

Minimal create sets, by kind:

| Kind | Asked at creation | Defaulted |
|---|---|---|
| Government transaction | service (type-ahead), company, *(responsible)* | body, checklist, fee, target date, responsible (the company's default runner) |
| Lawsuit | company, our role, opponent, court, next hearing, *(case number)* | lawyer (the company's default), stages, clocks |
| Contract review | company, counterparty, type, value, file, needed-by | reviewer by value and type |
| Opinion | question, requesting unit, needed-by | legal officer by rota |
| POA | principal, agents, scope template, notary office | expiry from the template |
| Compliance filing | none; generated by the schedule | everything |

For contrast, the showcase's `legal.task` puts 25 business fields and 7 header buttons on one form for
every kind of work (SAG review §3, baseline 05).

### 5.3 Where custom OWL components pay off (a pointer for doc 05 and the specification)

Only where a stock Odoo view can't make the job fast:

1. **Intake stepper** (B1): one question at a time, type-ahead over services, bodies and companies,
   keyboard-first, preview before create (06 C2).
2. **Agenda and clock board** (E1, D4): countdowns, non-extendable badges, the two-date display, grouped
   by week. Test Odoo's `activity` view first (research note `docs/research/ux-patterns.md` §5).
3. **Counter checklist** (C2): chips for have, missing and expired, a print action, a camera capture.
4. **Matter header and follow-up log** (A2, A4): the log's one-line quick add ("visited X, result Y,
   next Z").
5. **Hearing-outcome dialog** (D3) and **appeal-window calculator** (D4).
6. **Approval inbox** (M-1, M-2): inline approve, return and reject.
7. **Entity dossier** (I1, I2, C8): certificate traffic lights, coverage cards, readiness for a date.

Libraries: none is required for the needs above. Hijri and Iraqi month names come from the browser's
`Intl` (§6.4). Odoo Community already bundles charts, `calendar`, `web_hierarchy` and
`spreadsheet_dashboard`.

---

## 6. Iraqi specifics as data

### 6.1 The courts an in-house department meets

| Court (Arabic) | Hears | Degree / how its rulings are challenged | Refs |
|---|---|---|---|
| محكمة البداءة (بدرجة أولى) | civil and commercial claims **over IQD 1,000,000**, flat-fee claims, unvalued claims, bankruptcy and liquidation | **appeal** to محكمة الاستئناف, 15 days | Civ. Proc. Art. 32 as amended by Law 10/2016 ([SJC](https://sjc.iq/view.5696/), **S**); Arts. 185, 187 (**V**) |
| محكمة البداءة (بدرجة أخيرة) | claims up to IQD 1,000,000 and listed matters (e.g. eviction, تخلية المأجور) | **cassation**, 10 days, heard by محكمة الاستئناف بصفتها التمييزية | Art. 204 (**V**); Law 10/2016 (**S**) |
| محكمة البداءة المتخصصة بالدعاوى التجارية (Baghdad commercial court) | commercial and investment disputes, notably where one party is foreign | as بداءة (verify) | SJC statement 14/2017 (**S**, [osamatumalegal](https://www.osamatumalegal.com/ar/blog/%D8%A7%D8%AE%D8%AA%D8%B5%D8%A7%D8%B5-%D8%A7%D9%84%D9%85%D8%AD%D9%83%D9%85%D8%A9-%D8%A7%D9%84%D8%AA%D8%AC%D8%A7%D8%B1%D9%8A%D8%A9-%D9%81%D9%8A-%D8%A7%D9%84%D8%B9%D8%B1%D8%A7%D9%82)) |
| محكمة الاستئناف (بصفتها الأصلية / التمييزية), one per region | appeals from بداءة بدرجة أولى; cassation of final-degree بداءة judgments and some decisions | its judgments go to cassation within **30 days** | Arts. 204, 216 (**V**) |
| محكمة التمييز الاتحادية | cassation | judgments **30** days; decisions under Art. 216 **7** days; correction **7** days (never after 6 months, once only) | Arts. 204, 216, 219–221 (**V**) |
| محكمة الأحوال الشخصية (Muslims) / محكمة المواد الشخصية (non-Muslims) | family status; for in-house mostly HR matters (salary deduction orders) | cassation **10 days** | Art. 204 (**V**); [SJC article](https://sjc.iq/view.2475/) (**S**) |
| محكمة العمل | employment disputes, including challenges to termination-committee decisions | 30 days (verify the article) | Labour Law 37/2015 (**S**) |
| محكمة التحقيق | where criminal complaints begin (embezzlement, bounced cheques, public funds) | – | Crim. Proc. Law 23/1971 |
| محكمة الجنح (محكمة الجزاء) / محكمة الجنايات (محكمة الجزاء الكبرى) | misdemeanours / felonies | cassation **30 days from the day after pronouncement** | Crim. Proc. Arts. 138, 249, 252 (**V**) |
| محكمة قضاء الموظفين (formerly مجلس الانضباط العام) | disciplinary penalties on civil servants | grievance 30 → decision 30 → court 30 days | Law 14/1991 Art. 15 (**V**) |
| محكمة القضاء الإداري | administrative decisions | grievance 30 → decision 30 → suit within 60 days of the rejection, actual or deemed | Council of State Law 65/1979 as amended (**S**) |
| المحكمة الإدارية العليا | challenges to the two administrative courts above | 30 days (verify) | (**S**) |
| مديرية التنفيذ (Ministry of Justice), one wherever a بداءة court sits | enforcement of judgments and executable instruments | grievance to the execution officer 3 days; cassation to the regional appeal court 7 days | Execution Law 45/1980 (**S**) |
| لجان حسم المنازعات الحكومية (Ministry of Justice) | disputes between state bodies, instead of court | – | CoM decisions 2020/2021 (**S**) |
| لجنة الاستئناف الضريبي | tax-assessment appeals | 21 days from the rejection of the objection | tax pack (**U**) |
| محكمة تمييز إقليم كوردستان and the Region's courts | Kurdistan Region | a separate ladder; configure separately | – |

**Consequence for the data model:** the suite's degree list (`first_instance, appeal, cassation,
labor, misdemeanor_felony, administrative, personal_status`) cannot tell first-degree from
final-degree بداءة (the difference between 15 and 10 days and between appeal and cassation), merges
misdemeanour and felony courts, and has no investigation court, employee court, higher administrative
court or execution directorate. Either extend the list or key the rules on *court + degree of the
judgment*.

### 6.2 Statutory periods: the master table

Day counts are calendar days unless marked. "From" is the event that starts the clock.

| ID | Clock | Period | From | Extends? | Basis | Conf. |
|---|---|---|---|---|---|---|
| **Civil: Law 83 of 1969** |||||||
| CIV-1 | Objection to an in-absentia judgment (بداءة or أحوال شخصية, not urgent matters) | 10 d | day after notification | no | Arts. 177, 172, 171 | V |
| CIV-2 | Appeal (استئناف) of بداءة بدرجة أولى | 15 d | day after notification (after discovery, if the judgment rests on fraud or forgery) | no | Arts. 185, 187 | V |
| CIV-3 | Cassation of judgments of the appeal courts and of بداءة | 30 d | day after notification | no | Art. 204 | V |
| CIV-4 | Cassation of بداءة بدرجة أخيرة and personal-status judgments | **10 d** | day after notification | no | Art. 204 | V (text), S (reading) |
| CIV-5 | Cassation of the interlocutory decisions listed in Art. 216 | 7 d | day after notification | no | Art. 216 | V |
| CIV-6 | Correction of a cassation decision (تصحيح القرار التمييزي) | 7 d; never after **6 months** from the decision; once per party | day after notification | no | Arts. 219–221 | V |
| CIV-7 | Retrial (إعادة المحاكمة) | 15 d | day after the fraud or forgery is discovered or proven | no | Art. 198 | V |
| CIV-8 | Grievance against an order on petition (أمر على عريضة) | 3 d | the order, or its notification | – | Art. 153 | V |
| CIV-9 | Case "left for review" (تُترك للمراجعة) after both parties are absent | **10 d** to renew, or the petition is void | the day it is left | – | Art. 54 | V |
| CIV-10 | Agreed suspension (وقف) | at most 3 months, then **15 d** to resume, or void | court's approval / end of the term | – | Art. 82 | V |
| CIV-11 | Stay pending another question (استئخار) continued by the plaintiff | 6 months → void | – | – | Art. 83(2) | V |
| CIV-12 | Interruption (انقطاع) without acceptable excuse | 6 months → void; the interruption also halts running clocks | – | – | Arts. 84, 87 | V |
| CIV-13 | Summons for a party abroad | lodged 15–45 days before the hearing | – | – | the article just before Art. 24, para. 3 | V (text; article number to confirm) |
| **Criminal: Law 23 of 1971** |||||||
| CRM-1 | Complaint in offences that need one (defamation, threats, some thefts and breaches of trust, etc.) | **3 months** | day the victim learns of the offence | – | Arts. 3, 6 | V |
| CRM-2 | In-absentia judgment becomes as if given in presence (no surrender or objection) | 30 d (violation) / 3 months (misdemeanour) / 6 months (felony) | notification | – | Art. 243 | V |
| CRM-3 | Cassation (تمييز) | 30 d | **day after pronouncement** if in presence (not notification) | – | Art. 252 | V |
| CRM-4 | Correction of a criminal cassation decision | 30 d | notification to the convicted, or arrival of the papers at the trial court | – | Art. 266 | V |
| **Administrative and civil service** |||||||
| ADM-1 | Grievance against a disciplinary penalty | 30 d | notification | – | Law 14/1991 Art. 15 | V |
| ADM-2 | Authority decides the grievance (silence = rejection) | 30 d | the grievance | – | idem | V |
| ADM-3 | Challenge before محكمة قضاء الموظفين | 30 d | notification of the rejection | – | idem | V |
| ADM-4 | Administrative decision: grievance → decision → suit before محكمة القضاء الإداري | 30 d → 30 d → **60 d** | notification / grievance / rejection | – | Council of State Law 65/1979 | S |
| ADM-5 | Challenge before المحكمة الإدارية العليا | 30 d | notification | – | idem | S (verify) |
| **Labour** |||||||
| LAB-1 | Termination-committee decision to the labour court | 30 d | notification | – | Law 37/2015 | S |
| LAB-2 | Cassation of a labour-court judgment | 30 d | notification | – | Law 37/2015; suite rule | S/U |
| **Execution: Law 45 of 1980** |||||||
| EXE-1 | Debtor's time to comply after the execution notice (إخبار بالتنفيذ) | 7 d | day after notification | – | Art. 18 | S (older texts may say otherwise; verify) |
| EXE-2 | Payment after seizure, before sale | 3 d | day after | – | Art. 69(1) | S |
| EXE-3 | Grievance to the execution officer | 3 d | the decision | – | Art. 120 | S |
| EXE-4 | Cassation of execution decisions (regional appeal court) | 7 d | the decision | – | Art. 122 | S |
| EXE-5 | An executable instrument lapses if inactive | 7 years | last action | – | Art. 112 | S |
| **Tax: Income Tax Law 113 of 1982 (suite pack data)** |||||||
| TAX-1 | Annual return (تصريح ضريبة الشركات) | due **31 May** of the following year; late: 10%, capped at IQD 500,000 | – | – | pack | U |
| TAX-2 | Monthly withholding remittance | within **15 days** of the following month | – | – | pack | U |
| TAX-3 | Annual withholding schedule | **31 March** | – | – | pack | U |
| TAX-4 | Objection to an assessment | **21 d**, and the assessed tax must be paid within that period or the objection isn't heard | notification | no | pack | U |
| TAX-5 | Appeal to the tax appeal committee | **21 d** | notification of the rejection | – | pack | U |
| **Social security: Law 18 of 2023 (suite pack data)** |||||||
| SS-1 | Register a new worker | **30 d** | appointment | – | Arts. 23, 93 | U |
| SS-2 | Monthly contribution | end of the following month *or* 15 days after month end (sources disagree) | – | – | pack flags the conflict | U |
| SS-3 | Late penalty | 1%/month from day 121, capped at 100%; failing to register: fine of IQD 1–5 million plus 5× the unpaid contributions | – | – | pack | U |
| **Companies registrar and chamber (suite pack data)** |||||||
| REG-1 | Notify a change of head-office address | **7 d** | the move | – | Companies Law 21/1997 (pack cites Art. 200) | U |
| REG-2 | Foreign branch: final accounts and activity report | within **8 months** of year end | year end | – | Reg. 2/2017 Art. 8 | U |
| REG-3 | Annual general assembly and filing of final accounts | annual | – | – | Law 21/1997 Arts. 86, 88, 127, 135, 139 | U |
| CHM-1 | Entry in the commercial register | **30 d** | receipt of the certificate of incorporation | – | pack | U |
| CHM-2 | Chamber of commerce ID renewal (annual, graded) | annual | – | – | tender notices | U |
| **Residency (Law 76 of 2017, suite pack data)** |||||||
| RES-1 | Use an ordinary entry visa | within **3 months** of issue | issue | – | pack | U |
| RES-2 | Work permit (one year, renewable in its last month) | annual | – | – | pack | U |
| **Government contracts (Instructions 2 of 2014)** |||||||
| GOV-1 | Performance guarantee | **5%** of contract value, lodged after the award letter and before signing | award | – | Instructions 2/2014 | S |

### 6.3 How clocks are counted (build these into the engine, not into people's heads)

1. **Start:** the day after notification (civil, Art. 172), or the day after pronouncement for a
   criminal judgment given in presence (Art. 252). A party may challenge before being notified
   (Art. 172).
2. **Exclusion:** the start day and hour are not counted; the end day and hour are (Art. 25(1)).
   Months run to the matching day of the later month.
3. **Holiday at the end:** a period ending on an official holiday extends to the next working day
   (Art. 25(2)). A hearing that falls on a holiday moves to the next working day (Art. 24).
4. **Mandatory:** challenge periods are mandatory; missing one forfeits the right, and the court rejects
   a late petition on its own motion (Art. 171).
5. **Interruption** of the case (death, loss of capacity) halts running clocks (Art. 84).
6. **Distance periods** are added for parties abroad (explanatory memorandum, **V**). A secondary
   summary cites Art. 22 and one day per 50 km (**S**, verify before modelling).
7. **Show two dates** (06 B4): the conservative calendar-day date, and the legal last day rolled
   forward over holidays. Label which is which.

### 6.4 Calendar, locale and money

| Item | Iraqi reality | Product consequence |
|---|---|---|
| Working week | **Sunday–Thursday**; Friday and Saturday are the official weekly holidays (Law 12/2024 Art. 1(أ)) | a `resource.calendar` Sun–Thu per body (the registrar pack uses 08:30–14:15) |
| General holidays (Law 12/2024 Art. 1, **V**) | 1 Jan; 6 Jan (Army Day); 16 Mar (memorial of the regime's crimes: Halabja and the rest); 21 Mar (Nowruz); 1 May; 1 Muharram; 10 Muharram (Ashura); 12 Rabi' al-Awwal (Mawlid); 1–3 Shawwal (Eid al-Fitr); 10–13 Dhu al-Hijja (Eid al-Adha); 18 Dhu al-Hijja (Ghadir) | **Hijri holidays move every year, and the Shia and Sunni endowment offices fix the Eid dates** (Art. 1(ثانياً)); where they differ, the holiday runs from the first office's first day to the other's last day. The Council of Ministers may add up to 7 days a year (Art. 3). **So holidays are yearly data entry, never computed.** 14 July and 3 October are not in the extracted text of the 2024 law (verify before seeding) |
| Local closures | the governorates holding holy cities (Najaf, Karbala, Kadhimiya, Samarra) may close offices up to 3 days around a religious holiday (Art. 1(ثالثاً)) | per-governorate calendars |
| Component holidays | Christian, Sabian and Yazidi days apply to those communities (Art. 2) | a per-employee concern, not a court calendar |
| Time zone | Asia/Baghdad (UTC+3, no daylight saving) | – |
| Month names | Iraqis write **كانون الثاني، شباط، آذار، نيسان، أيار، حزيران، تموز، آب، أيلول، تشرين الأول، تشرين الثاني، كانون الأول** | `Intl` with `ar-IQ` gives "٢٤ أيلول ٢٠٢٦"; with plain `ar`, which Odoo's `ar_001` uses, it gives "24 سبتمبر 2026". The baseline shows "٢٨ سبتمبر" (checked with Node here) |
| Digits | both Arabic-Indic (٠–٩) and Latin appear in practice; official letters mostly use Arabic-Indic | pick one per surface; the baseline mixes them (Arabic-Indic dates, Latin amounts) |
| Hijri | letters sometimes carry both dates | `Intl` `islamic-umalqura` is built into the browser |
| Currency | IQD in whole dinars; USD for foreign contracts and some fees | Odoo's IQD record has `rounding = 0.001` (fils) and ships inactive; the showcase stores money as a bare Float labelled "د.ع / $". Use `Monetary`, an active IQD, and a display rounding of 1 |

### 6.5 Government bodies an in-house department deals with

Private group (archetype A). From the prototype, the suite packs, and additions marked *(added)*.

| Ministry / parent | Body | What in-house legal does there |
|---|---|---|
| وزارة التجارة | دائرة تسجيل الشركات (sections: التأسيس، التعديل والتصديق، فروع الشركات الأجنبية) | formation, amendments, capital increase, address change, certifying records, final accounts, صحة صدور |
| وزارة التجارة | الشركة العامة للمعارض والخدمات التجارية | import licences; the chamber ID service as SAG lists it |
| وزارة المالية | الهيئة العامة للضرائب (sections: الشركات، الاستقطاع المباشر، كبار المكلفين، الحجوزات، التدقيق والفحص، القانوني، لجنة الاستئناف) | returns, withholding, clearance, كتاب عدم ممانعة, objections, the managing director's personal tax |
| وزارة المالية *(added)* | الهيئة العامة للكمارك | customs disputes and clearances |
| وزارة العمل والشؤون الاجتماعية | دائرة التقاعد والضمان الاجتماعي للعمال (sections: التسجيل، الاشتراكات، التفتيش، سلامة الموقف) | registration, contributions, inspections, clearance |
| وزارة العمل والشؤون الاجتماعية | دائرة العمل والتدريب المهني | work permits for foreign staff |
| وزارة الداخلية | مديرية شؤون الإقامة | visas, residency |
| وزارة الداخلية | المديرية العامة للمرور | annual vehicle registration, badges, صحة صدور of papers |
| وزارة الداخلية *(added)* | مديرية الجنسية والبطاقة الوطنية | identity documents of officers |
| وزارة العدل | دائرة الكتاب العدول (178 offices, per the Oct 2024 report) | POAs, notarial notices, revocations, certifications |
| وزارة العدل *(added)* | دائرة التسجيل العقاري | title deeds (سند الطابو), property transfers, mortgages |
| وزارة العدل *(added)* | دائرة التنفيذ | enforcement of judgments |
| وزارة العدل | الوقائع العراقية | publication of company acts |
| وزارة الخارجية | دائرة التصديقات؛ دائرة العلاقات القنصلية (السمات) | authentication of foreign documents; visas |
| وزارة التخطيط *(added)* | دائرة العقود الحكومية / تصنيف المقاولين | contractor classification (the suite's identifier kind) |
| *(added)* | هيئة الاستثمار الوطنية | investment licences |
| هيئة الإعلام والاتصالات (CMC) | – | `.iq` domain (the P.O. box that SAG lists under CMC is likely Iraqi Post; verify) |
| وزارة الكهرباء؛ أمانة بغداد / دوائر الماء | – | subscription transfers, utility clearance |
| غرفة تجارة بغداد؛ اتحاد الغرف التجارية العراقية | – | graded chamber ID, national trade-name check, commercial register |
| اتحاد الناقلين | – | transport-company IDs |
| نقابة المحامين العراقيين | – | the legal-adviser appointment letter needed at formation; advocates' registration |
| المصارف (مصرف الرشيد، مصرف الرافدين …) | – | capital deposit confirmation, letters of guarantee |
| *(added)* | جهاز الأمن الوطني | security clearance (الموافقة الأمنية) for foreign staff |
| *(added)* | البلديات / أمانة بغداد | building and occupancy permits, signage |
| Courts (مجلس القضاء الأعلى) | §6.1 | litigation |

Public sector (archetype B), in addition: مجلس الدولة (opinions and legislative review), الأمانة
العامة لمجلس الوزراء, ديوان الرقابة المالية الاتحادي, هيئة النزاهة الاتحادية, the Ministry of Justice's
government-dispute committees, and the ministry's own formations.

Kurdistan Region: separate registrar (the suite ships the KRG unified entity number, UEN, as an
identifier kind), separate courts and different laws. Treat it as its own jurisdiction branch.

### 6.6 Document types

| Group | Types |
|---|---|
| Persons (مستمسكات) | البطاقة الوطنية الموحدة؛ جواز السفر؛ بطاقة السكن؛ صور شخصية؛ for foreign staff: سمة الدخول، الإقامة، إجازة العمل، الفحص الطبي، الموافقة الأمنية، تبليغ الوصول |
| Incorporation and corporate | شهادة تأسيس الشركة؛ عقد التأسيس؛ إعلان النشرة اليومية؛ محضر اجتماع الهيئة العامة؛ محضر تعيين المدير المفوض؛ الحسابات الختامية المدققة؛ تأييد مصرفي بإيداع رأس المال؛ كتاب نقابة المحامين بتعيين المشاور القانوني؛ تعهد المستفيد الحقيقي؛ إجازة فرع شركة أجنبية؛ شهادة تسجيل الشركة الأم (مترجمة ومصدقة)؛ تأييد صادر من المسجل |
| Premises | عقد إيجار مصدق؛ سند الملكية (الطابو) وخارطة العقار؛ قائمة كهرباء مسددة؛ قائمة ماء مسددة (these go **stale** rather than expire) |
| Tax | البطاقة الضريبية؛ الإقرار السنوي؛ البيانات المالية لأغراض ضريبية؛ براءة الذمة الضريبية؛ كتاب عدم ممانعة؛ استمارة ض.د/4أ؛ جدول الاستقطاعات؛ إشعار التقدير؛ لائحة الاعتراض؛ وصل تسديد |
| Social security | شهادة تسجيل المشروع؛ براءة الذمة (سلامة الموقف)؛ البيان السنوي؛ استمارة ضم عامل؛ وصل الاشتراك؛ تأييد الكشف |
| Chamber | هوية غرفة التجارة **with grade** (ممتاز، أول، ثانٍ، ثالث)؛ موافقة حجز الاسم التجاري؛ كتاب الاتحاد بتثبيت الاسم؛ قيد السجل التجاري |
| POA and notary | وكالة عامة؛ وكالة خاصة؛ وكالة محامٍ / وكالة بالخصومة؛ وكالة تسجيل؛ وثيقة تخويل المراجع؛ إنذار عدلي؛ صحة صدور (now a QR reference) |
| Litigation | عريضة الدعوى؛ لائحة جوابية؛ مذكرة؛ محضر جلسة؛ ورقة تبليغ؛ قرار / حكم؛ عريضة طعن (اعتراض، استئناف، تمييز، تصحيح)؛ إخبار تنفيذي؛ محضر حجز |
| Contracts | العقد؛ ملحق؛ كتاب إحالة؛ خطاب ضمان (أولي / حسن تنفيذ / سلفة)؛ محضر استلام |
| Government correspondence | كتاب صادر؛ كتاب وارد؛ تذكير؛ إعادة للاستكمال؛ وصل استلام؛ كتاب موافقة / رفض؛ مذكرة داخلية |
| Public sector | أمر إداري بتشكيل لجنة تحقيقية؛ محضر التحقيق؛ توصيات اللجنة؛ قرار التضمين؛ قرار العقوبة؛ التظلم |

Validity models: **expiry** (a date), **freshness** (valid for N days after issue, like a paid utility
bill; registrar directive 16180 of 2024 per the pack), **permanent** (a certificate of incorporation),
**valid at a date** (a clearance must be in force at the tender's closing date, not today).

### 6.7 Recurring obligations of a private group company (the compliance calendar)

| Obligation | Rhythm | Lead time (pack default) | Body |
|---|---|---|---|
| Annual tax return | yearly, 31 May | 75 d | الهيئة العامة للضرائب |
| Withholding remittance | monthly, by the 15th | 7 d | قسم الاستقطاع المباشر |
| Annual withholding schedule | yearly, 31 March | 30 d | idem |
| Tax clearance renewal | as needed for tenders and imports | 14 d | idem |
| Social-security contribution | monthly | 10 d | الضمان الاجتماعي |
| Annual project statement | yearly | 21 d | idem |
| Social-security clearance | as needed for tenders | 10 d | idem |
| Final accounts and general assembly | yearly | 45 d | دائرة تسجيل الشركات |
| Foreign branch final accounts | yearly, year end + 8 months | 60 d | idem |
| Chamber ID renewal | yearly | 21 d | غرفة التجارة |
| Runner's authorisation, advocate's POA | per document's term | 14 d | registrar, notary |
| Foreign staff residency, work permit, passport | per document | 30 / 30 / 60 d | residency, labour |
| Vehicle annual registration (السنوية) | yearly per vehicle | *(to set)* | المرور |
| `.iq` domain | yearly | *(to set)* | CMC |

### 6.8 Status vocabulary in Iraqi practice

| Kind | Stages (proposed labels) |
|---|---|
| Government transaction | مسودة → جمع المستمسكات → مقدَّمة إلى الجهة → لدى الجهة (قيد الإنجاز) → أُعيدت للاستكمال ↺ → بانتظار صحة الصدور → منجزة (استُلم الأصل) · ملغاة |
| Lawsuit | قيد الإعداد → مُقامة → قيد المرافعة (الجلسة القادمة …) → متروكة للمراجعة / موقوفة (alerts) → محكوم فيها (بانتظار التبليغ) → في مرحلة الطعن → مكتسبة الدرجة القطعية → في التنفيذ → مغلقة |
| Contract | طلب → قيد المراجعة → بانتظار الاعتماد → موقَّع / نافذ → قارب الانتهاء → منتهٍ / مجدَّد / مفسوخ |
| Opinion | مطلوب → قيد الدراسة → بانتظار الاعتماد → صادر (مجمَّد) · مستبدَل |
| POA | قيد الإصدار → سارية → قاربت الانتهاء → منتهية · معزولة |
| Request | جديد → قيد الفرز → مُسنَد → أُعيد للاستكمال ↺ → مُنجز · ملغى |
| Investigation (B) | أمر التشكيل → قيد التحقيق → التوصيات → القرار → التظلم / الطعن → مغلق |

The showcase's "بانتظار الوثائق / صحة الصدور" joins two different waits into one state. They have
different owners (us or the body) and should be separate.

### 6.9 Public sector versus private group: what the mode switch changes

| Aspect | Private group (A) | Public sector (B) |
|---|---|---|
| "Company" axis | group companies (`legal.company`) | the ministry's formations (directorates, companies owned by the ministry) |
| Front door | managers' requests; runner services | referrals from the minister or director-general (إحالة), plus other directorates' requests |
| Litigation | as plaintiff (collections, cheques) and defendant | the state as defendant in large volume; employee-court and administrative cases; no suing other state bodies (dispute committees instead) |
| Representation | an advocate holding a POA | a legal employee (حقوقي) by the minister's authorisation (تخويل) |
| Opinions | occasional | core output, numbered and registered |
| Investigations and تضمين | rare (internal fraud) | routine, with statutory clocks |
| Contracts | commercial | tenders, award letters, guarantees, the government-contract instructions |
| Oversight | internal audit | Federal Board of Supreme Audit, Integrity Commission, the minister's office; the monthly status report |
| Default visibility | by team | department-wide |
| Terminology | الشركة / الموكل، المعاملة | الدائرة / التشكيل، الإحالة، الدعوى |

Sources for B's duties: [Central Bank of Iraq's legal department](https://cbi.iq/news/view/804) (sections
for consultations, internal and external litigation with a separate employee-court unit, contracts,
certifications and seizures) and a
[Ministry of Construction legal section](https://alimar.moch.gov.iq/qanounia.html) (representation,
opinions, contract review, investigation records, tender notices, guarantees, property).

---

## 7. Journeys to specify and test against

Each is a sequence the specification should turn into a scripted, screenshot-verified test.

1. **Tax clearance for a tender (A).** A requester asks for a clearance valid on 15 October. The
   readiness check shows the current one expires on 30 September. The manager creates the transaction
   from the service catalogue. The checklist marks the final accounts missing. The runner prints the
   sheet, visits the counters and logs three visits from a phone with receipts. The file waits for صحة
   صدور, is done, and the new clearance lands in the company's vault with its expiry. The requester
   sees "done".
2. **Lawsuit to execution (A/B).** A claim is filed at بداءة الكرخ. The lawyer logs hearings in one
   step each. A judgment is notified on a Thursday. The system shows the 15-day appeal window, rolled
   over the weekend and holidays, as non-extendable, on the lawyer's and manager's agendas. The appeal
   is lodged, then cassation, then the final judgment. An execution file opens and the 7-day clock
   runs. Collections are recorded, and exposure and recoveries update on the board.
3. **Contract request (A/B).** Procurement asks for review of a supply contract worth IQD 900 million.
   Routing by value sends it to a senior lawyer, then manager approval. The performance guarantee (5%)
   is recorded with its bank and expiry, and renewal and guarantee alerts go on the agenda.
4. **Annual chamber ID renewal for 12 companies (A).** One batch creates 12 transactions. Missing
   documents are flagged per company. The grade is recorded. The readiness board turns green company
   by company.
5. **POA issue and revocation (A).** A special POA for a new driver: from the template to the notary
   office, the QR recorded, the expiry on the agenda. The driver leaves, the "revoke" action opens a
   notarial-notice transaction, and the POA shows معزولة with the notice number.
6. **Foreign engineer (A).** A request from HR runs the visa → residency → work-permit chain. Each
   document's expiry goes on the compliance calendar. The passport expiry warns 60 days ahead.
7. **Investigation and تضمين (B).** A committee is formed by administrative order, with members
   including the required law graduate. Statements are recorded, the recommendation made, the تضمين
   decision taken. The employee's grievance clock runs 30 days, then 30 for the decision, then 30 for
   the employee court. Everything is visible to the auditor, who can change nothing.
8. **Question to an opinion (A/B).** A requester asks a question. Triage assigns it. The lawyer finds
   two precedents and issues an opinion with a register number and a frozen PDF. A later revision
   supersedes it, with the chain visible.

---

## 8. Implications for the rebuild

### 8.1 Mapping onto the compatibility surface

- `legal.task` stays the matter, gains a **kind**, and is the anchor for lawsuit, hearing, judgment,
  execution, POA and contract detail (child records or sections that the kind switches on). The
  existing fields map as follows. `session_date` becomes "next hearing" for lawsuits only. `due_date`
  becomes the generic next date. `state` plus `approval_state` fold into per-kind stages plus the
  approval queue, with a migration. `expenses_amount` becomes fee lines with `Monetary`.
- `legal.company` is the group entity or client dossier (area I). Keep its counts and replace
  `department_cards_html` with queryable coverage.
- `legal.ministry` → `legal.department` stays SAG's two-level body tree; add body type, calendar,
  contacts and service catalogue (06 B1). Courts can be departments of type "court" under مجلس
  القضاء الأعلى, as SAG already does (baseline: بداءة الكرخ under مجلس القضاء الأعلى); 06 B3 proposes
  the same.

### 8.2 Corrections for the statutory data the suite would donate (adds to 06 B4)

06 B4 found three missing civil rules (10-day cassation, correction, retrial) and the holiday
roll-forward. This research confirms those and adds:

1. **CIV-4 applies to personal-status judgments too**, and "بداءة" in the second clause of Art. 204
   means final-degree بداءة (the former magistrates' courts, merged in 1979). The rule needs the degree
   *of the judgment* (أولى / أخيرة) as a key, which the suite's degree list lacks (§6.1).
2. **Criminal clocks start at pronouncement** (Art. 252), not notification. The judgment model needs
   a `clock_starts_on` per rule: notification, the day after notification, pronouncement, or
   discovery (CIV-7).
3. **Clocks inside a case** (CIV-9 to CIV-12) and **execution clocks** (EXE-1 to EXE-5) are absent from
   the suite. They are short (3, 7 and 10 days) and lose cases in practice.
4. **Administrative chains** (ADM-1 to ADM-5) are *sequences*: each clock starts when the previous
   step ends, and one starts on *silence*. The engine must support "if no decision within N days,
   start the next clock".
5. **Holidays**: the 2024 law makes Eid dates depend on the endowment offices' announcements and
   allows up to 7 extra days by cabinet decision, so holiday entry must be yearly, easy and done by the
   manager (E2).

### 8.3 Showcase gaps against the MUST list (for the specification's backlog)

No matter kinds (A1). No structured follow-up log (A4). No checklist (A14, C2). No service catalogue
(B2). One `session_date` in place of hearings and judgments (D2–D4). No appeal windows (D4). No
agenda of all clocks (E1). No POA register (H1). No entity vault with validity (I2). No compliance
calendar (J1). No correspondence register (K1). A generic approval flag in place of approval rules
(M-1). Money as a bare Float mixing IQD and USD (N1, N8). Two write-capable groups and no auditor
(R1). No mode or feature switches (S1, S2). Month names and digits left to the locale (§6.4). Emoji in
labels and statuses (SAG review idea 12).

---

## 9. Open questions and items to verify before seeding

1. **Counsel check** of every **S** and **U** row in §6.2, above all EXE-1 (7 days, or 10 in older
   texts?), ADM-4/ADM-5, LAB-1/LAB-2, the social-security contribution date, and whether 14 July and
   3 October are still general holidays after Law 12/2024.
2. **Is SAG an A-only customer**, or does it also want B (public sector) for other clients? This
   decides whether areas O and G ship switched on.
3. **Do runners have Odoo users?** If not, the phone flow (C4, R2) needs a lightweight login or a
   runner-per-device pattern. The price of a user seat is a real constraint.
4. **Is HR installed at every customer?** The showcase links `hr.employee` (`employee_ids`). Keep that
   optional.
5. **Dates:** Arabic-Indic or Latin digits, and Iraqi month names everywhere (via a custom
   formatter) or only in the custom components?
6. **Kurdistan Region**: in scope for SAG? It changes the courts, registrar and identifiers.
7. **Outside counsel** at SAG: how many firms, and on what fee terms? This decides N4's depth.

---

## 10. Sources

**Repository**
- `docs/external-review/sag-legal-module.md` (SAG production metadata review)
- `docs/legal-product-roadmap.md`, `docs/research/ux-patterns.md`, `docs/architecture.md`, `docs/workflow.md`
- `custom_addons/legal_iq_{registrar,tax,chamber,social_security,residency}/data/*.xml` (Iraqi content packs)
- `custom_addons/legal_litigation/data/legal_{appeal_rule,court}_data.xml`, `models/legal_{court,judgment,appeal_rule}.py`
- `custom_addons/legal_{core,correspondence,contract,request,opinion,deadline}` (models listed in §4 refs)
- Prototype: `…/scratchpad/src/old/src/types.ts` (`DepartmentCategory`, `OFFICIAL_SUB_SERVICES`)
- Baseline screens `docs/ldm/evidence/00-baseline/01_dashboard.png`, `05_task_form.png`
- Sibling: `docs/ldm/research/06-suite-reuse-map.md` §B4

**Iraqi law (primary text)**
- Civil Procedure Law 83/1969 as amended (Ministry of Trade PDF): https://tasjeel.mot.gov.iq/newtasjeel/قوانين المساهمة/قانون المرافعات المدنية رقم 83 لسنة 1969 المعدل.pdf ; also https://wiki.dorar-aliraq.net/iraqilaws/law/19608.html
- Criminal Procedure Law 23/1971 (PDF): https://menarights.org/sites/default/files/2022-06/IRQ_Code%20of%20Criminal%20Procedure_AR.pdf ; https://wiki.dorar-aliraq.net/iraqilaws/law/4895.html
- State Employees Discipline Law 14/1991: https://wiki.dorar-aliraq.net/iraqilaws/law/13754.html
- Execution Law 45/1980: http://wiki.dorar-aliraq.net/iraqilaws/law/3121.html
- Official Holidays Law 12/2024, Official Gazette no. 4777 of 27 May 2024: https://www.moj.gov.iq/upload/pdf/4777_453.pdf ; list: https://ar.wikipedia.org/wiki/قائمة_العطل_الرسمية_في_العراق

**Iraqi law (secondary)**
- First-instance court, first versus final degree (Law 10/2016): https://sjc.iq/view.5696/
- Path of a civil case and its periods (SJC): https://sjc.iq/view.2475/
- Council of State grievance and suit periods: https://www.iraqilaws.com/2023/10/65-1979.html
- Labour Law 37/2015 overview: https://www.iraqilaws.com/2023/10/37-2015.html
- تضمين Law 31/2015: https://sjc.iq/view.70276/ ; https://la.uokerbala.edu.iq/2025/02/09/قانون-التضمين-رقم-31-لسنة-2015/
- Government dispute committees: https://manshurat.org/node/74349
- Government Contracts Instructions 2/2014: http://wiki.dorar-aliraq.net/iraqilaws/law/20872.html ; https://uomosul.edu.iq/public/files/datafolder_1453/_20190917_091452_680.pdf
- Baghdad commercial court: https://www.osamatumalegal.com/ar/blog/اختصاص-المحكمة-التجارية-في-العراق ; https://ina.iq/ar/political/214051--.html
- Paper صحة صدور abolished, QR on all POAs (30 Oct 2024): https://www.alsumaria.tv/news/localnews/504835/
- Notary Law 33/1998: http://wiki.dorar-aliraq.net/iraqilaws/law/17106.html ; revocation service: https://ur.gov.iq/index/show-eservice/40330/10045/org
- Public-sector legal departments: https://cbi.iq/news/view/804 ; https://alimar.moch.gov.iq/qanounia.html ; https://moj.gov.iq/tashkelat.12/

**Global legal operations and vendors**
- CLOC Core 12: https://cloc.org/cloc-core-12/
- CLOC vs ACC maturity model: https://www.gls-startuplaw.com/know-how/comparing-clocs-core-12-and-accs-legal-operations-maturity-model-a-practical-assessment
- Gartner 2025 EBMM market guide (vendor summaries): https://clc.mitratech.com/2025-gartner-market-guide-e-billing-and-matter-management ; https://lawvu.com/news/lawvu-recognized-in-the-2025-gartner-market-guide-for-e-billing-and-matter-management-technology/
- LawVu matter management: https://lawvu.com/workspace/matter-management/
- Mitratech TeamConnect: https://mitratech.com/products/teamconnect/features-benefits/
- Brightflag spend management: https://brightflag.com/legal-spend-management/
- SimpleLegal (Onit): https://www.onit.com/products/elm/simplelegal/
- Checkbox intake and triage: https://www.checkbox.ai/platform/legal-intake-and-triage
- Josef self-service: https://joseflegal.com/blog/3-benefits-of-automating-faqs-for-in-house-legal-teams/
- Legal Tracker, top 10 metrics: https://legal.thomsonreuters.com/content/dam/ewp-m/documents/legal-tracker/en/pdf/white-papers/legal-tracker-top-10-metrics-your-legal-department-should-track-white-paper.pdf
- Entity management: https://www.diligent.com/resources/blog/best-entity-management-software ; https://www.minutebox.com/entity-management/for-generalcounsel ; https://www.athennian.com/product
- CLM stages: https://www.onit.com/blog/what-is-contract-lifecycle-management/
- Progressive disclosure: https://www.nngroup.com/articles/progressive-disclosure/
