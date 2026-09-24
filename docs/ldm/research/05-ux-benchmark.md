# 05 — UX benchmark: simple by default, advanced on demand

**Date:** 2026-09-24 · **Module:** `legal_department_management` (SAG Group, v19.0.6.3.0, baseline commit `ccebae7`)
**Question this answers:** what makes professional legal software *easy*, what in the
showcase works against ease, and which screens (with which OWL components on which
Odoo 19 primitives) the professional version should have. The top priority is
"easiest possible, yet advanced options available".

**Method.**
- **Web research** on Clio Manage, MyCase, PracticePanther, Smokeball, Filevine,
  Litify, LawVu, Thomson Reuters Legal Tracker, and on Linear, Superhuman and Notion.
  Sources are vendor help centres, vendor feature pages, and G2/Capterra review
  summaries, all listed at the end. **Access caveat:** `help.clio.com` and
  `support.filevine.com` returned HTTP 403 to direct fetches, so their content here
  comes from search-engine extracts of those same pages, not from reading each full page.
  Everything else was fetched or quoted from the search result for that URL.
- **Owner decisions** read and honoured: `docs/research/ux-patterns.md`,
  `docs/legal-product-roadmap.md`, `docs/ui-audit/MY_OFFICE_REDESIGN.md` (the مكتبي
  redesign, "My Office"), `docs/external-review/sag-legal-module.md`, and the sibling
  `docs/ldm/research/02-prototype-intent.md`.
- **Showcase evidence:** the 8 baseline screenshots in `docs/ldm/evidence/00-baseline/`
  (Arabic, 1440×900), plus the module source (views, models, dashboard JS).
- **Odoo 19 source** under `odoo-19.0/addons/web/static/src` (and `mail`, `html_editor`,
  `odoo/orm`). Every primitive recommended below was **found in this checkout**, and
  its path is given in §6.

Nothing in the repository was changed apart from writing this file.

---

## 0. Conclusion in one screen

Across these products, ease of use comes from **how few decisions the user must make**,
not from how few features there are. The products reviewers call easy (Clio, MyCase,
PracticePanther, LawVu) share six mechanics:

1. **The work is on the first screen.** A "today" list of what is due and what is
   waiting comes before any chart.
2. **Creating something is one global button** that asks 3–4 questions and fills in
   the rest from the context.
3. **Templates spawn the work.** Choosing a matter type creates its tasks,
   deadlines, documents and fields, with dates calculated from a trigger date.
4. **The matter page shows its vital facts on top**, with the depth behind tabs.
5. **Status changes where you see it**: inline, dragged on a board, or with one key.
6. **Search and create work from anywhere** (Ctrl/⌘+K).

The products reviewers call hard (Filevine, Litify) show what goes wrong when power
arrives without defaults. Users mention "the number of fields to fill in", say the tool
needs "a person on your staff to handle it", and call it "cumbersome for simple tasks".

The showcase breaks most of these rules. It opens on digits. Creating a matter is a
two-step wizard that saves nothing. It shows two status axes and eight coloured
buttons at once. The client form puts ten empty fields above the client's matters.
Lawyers have no menu route to the matter register at all (§2).

**Recommendation.** Rebuild the module as a **matter-centric, template-driven
workspace**:
- **مكتبي / My Day** is the home screen (keeping SAG's `legal_dashboard_tag` action).
- **A one-step quick create from a template** replaces the wizard. It takes 3 inputs
  and generates the steps, deadlines and required documents.
- **A matter cockpit** has one status axis and one "next step" card.
- **Five layers of progressive disclosure** hide advanced material by feature, role,
  mode, matter type and an "المزيد" (more) toggle (§3).
- **A legal provider for Odoo's own Ctrl+K palette** covers search and power users.

Everything required is already shipped in Odoo 19 Community: OWL 2, command palette,
hotkeys, Dialog, `Record`/`Field`, Many2XAutocomplete, activity plans, `properties`
fields, `statusbar_duration`, FullCalendar 6.1.11, Chart.js 4.4.5, pdf.js, zxing,
html_editor. Most of the custom components can be **ported from the owner's own
suite** (`legal_procedure`, `legal_office`). **No new runtime JS library is required** (§7).

---

## 1. What makes the benchmark products easy

### 1.1 Pattern catalogue

| # | Pattern | Where it appears (product → feature) | Evidence | Adopt as (this module) |
|---|---|---|---|---|
| P1 | **Matter-centric home per matter**: a dashboard tab with vitals, financials, dates and a timeline | **Clio** Matter Dashboard: "financials (WIP, outstanding balance, trust), matter details (status, responsible lawyer, dates), contacts, custom fields, conflict checks"; admins choose which widgets show and their order. **Filevine** *Vitals*: "important details of the case… accessible at a glance; nearly any field… can be summarized in a vital" | [Clio Matter's Dashboard](https://help.clio.com/hc/en-us/articles/16681289917595-Matter-s-Dashboard), [Filevine Vitals](https://support.filevine.com/hc/en-us/articles/360004183551-Vitals) | Matter cockpit S3: vitals strip + next-step card |
| P2 | **"My day" agenda** as the landing screen | **Clio** Personal Dashboard "Today's Agenda" (tasks due today + today's events). **PracticePanther** sidebar: calendar preview, "Your Agenda" (overdue + upcoming tasks), quick timer, recent matters. **LawVu** Hub: recent work, to-dos, planners, matter activity. **Linear** My Issues: "grouped in a focus order such as urgent work, SLA-bound work, blockers… Some sections only appear when they apply" | [Clio dashboards](https://support.clio.com/hc/en-us/articles/204410037-Personal-Matter-Dashboards), [PracticePanther Dashboard](https://support.practicepanther.com/en/articles/629220-dashboard-tutorial), [LawVu workspace](https://help.lawvu.com/en/articles/6636506-the-lawvu-legal-workspace-explained), [Linear My issues](https://linear.app/docs/my-issues) | مكتبي S1: focus bands (متأخر overdue / اليوم today / هذا الأسبوع this week / لاحقًا later / بلا تاريخ no date) + a 7-day agenda rail |
| P3 | **One global "create" button**, pre-filled from the context | **Clio** "Create new" in the header, next to global search, recents and the timer. **PracticePanther** green "New" button "on the top of every page"; from inside a matter it "automatically fills out the contact and matter fields". **LawVu** "+Create". **Linear** key `C` | [Clio Navigate](https://help.clio.com/hc/en-us/articles/9290390462875-Navigate-Clio-Manage), [PracticePanther Tasks](https://support.practicepanther.com/en/articles/480005-tasks-tutorial), [Linear creating issues](https://linear.app/docs/creating-issues) | G2 "+ جديد" (New) in the My Day header, the palette and every register; context pre-fill |
| P4 | **Minimal required fields at creation** | **Linear**: issues "are required to have a title and a status"; everything else is optional, and drafts are kept. **Clio** matter templates pre-populate the details so creation is mostly one choice | [Linear creating issues](https://linear.app/docs/creating-issues), [Clio Matter Templates](https://help.clio.com/hc/en-us/articles/18353050138651-Matter-Templates) | S2 quick create: type + client + key date (+ suggested title) |
| P5 | **Templates that spawn tasks and deadlines** | **Clio** matter templates set details, opening stage, custom fields, billing, document folders and **task lists**. *Automated workflows* "assign a task list" when a matter is created or moves between stages. **MyCase** Workflow: "templates that contain groups of tasks and/or calendar events… with the click of a button"; "automatic calculation of task due dates… four days before the trial date… four weekdays after the arraignment". **PracticePanther** workflows: "the due date of all the tasks… are based on the due date of the event". **Filevine** Taskflows are triggered by a phase change or a button, with tasks depending on earlier tasks. **Litify** templatized task lists per practice area. **Clio Court Rules**: pick a trigger and the deadlines are calculated; changing the trigger offers a recalculation; a deadline falling on a weekend or holiday moves | [Clio Matter Templates](https://help.clio.com/hc/en-us/articles/18353050138651-Matter-Templates), [Clio Automated Workflows](https://help.clio.com/hc/en-us/articles/35132279298843-Clio-Manage-Automated-Workflows), [MyCase Workflow overview](https://supportcenter.mycase.com/en/articles/9370082-workflow-overview), [Lawyerist on MyCase Workflows](https://lawyerist.com/news/mycase-workflows/), [PracticePanther workflows](https://support.practicepanther.com/en/articles/480078-automating-task-event-workflows), [Filevine Taskflow](https://support.filevine.com/hc/en-us/articles/360005080892-Taskflow), [Litify legal CRM](https://www.litify.com/resources/legal-crm), [Clio Court Rules](https://help.clio.com/hc/en-us/articles/9289840995867-Court-Rules), [Court Rules FAQ](https://support.clio.com/hc/en-us/articles/4409633822107-FAQ-Court-Rules-Enhancements) | `legal.task.template` + steps with **working-day** offsets (Sun–Thu, Eid as leave), generated at creation. Changing the trigger date offers recalculation. Seeded with Iraqi body templates (§4 S12) |
| P6 | **The layout follows the matter type** (fields and sections appear only when relevant) | **Smokeball**: layouts "differ from matter type to matter type"; the client field is relabelled "Buyer, Seller, Applicant, Respondent… depending on the type". **Filevine** *Flex sections* change visibility with the project's phase. **Clio** custom field *sets* per practice area (applied manually; the FAQ says fields cannot yet be applied by practice area automatically). **Notion** property visibility: "Always show / Hide when empty / Always hide" | [Smokeball Change a Matter Type](https://support.smokeball.com/hc/en-us/articles/13270415150231-Change-a-Matter-Type), [Filevine Flex Sections](https://support.filevine.com/hc/en-us/articles/360022614491-Flex-Sections), [Clio custom fields](https://help.clio.com/hc/en-us/articles/9285493193115-Get-Started-With-Custom-Fields), [Clio Custom Fields FAQ](https://support.clio.com/hc/en-us/articles/203139814-Custom-Fields-FAQ), [Notion property visibility](https://super.so/blog/hide-notion-properties) | Template `kind` (administrative / litigation / advisory / contract) drives which tabs show; template-defined `properties`; hide-when-empty in the form (§3 L3, L4) |
| P7 | **Stage board + inline stage change** | **Clio** Matter Stages: a kanban where you move matter cards "through dragging or keyboard navigation"; moves are logged. **MyCase** changes the case stage from the list through a pencil icon beside the stage name | [Clio Matter Stages](https://help.clio.com/hc/en-us/articles/15083241879195-Matter-Stages), [streamlined.legal on Clio stages](https://streamlined.legal/clio-features/transform-your-legal-practice-with-stages-clios-new-kanban-board/), [MyCase Case Stages](https://supportcenter.mycase.com/en/articles/9369886-case-stages) | Native kanban grouped by stage; `statusbar` with Alt+X; `statusbar_duration` |
| P8 | **Time capture costs seconds** (firm mode) | **Clio** header play/pause timer; the timekeeper lists the day's entries. **PracticePanther** quick-access timer, multiple timers. **Smokeball AutoTime** records "in the background… no start/stop timers" | [Clio Time Entries](https://help.clio.com/hc/en-us/articles/9289741706779-Time-Entries), [PracticePanther Dashboard](https://support.practicepanther.com/en/articles/629220-dashboard-tutorial), [Smokeball AutoTime](https://www.smokeball.com/features/legal-time-tracking-software) | Systray timer + day sheet (roadmap §6.3), firm mode only |
| P9 | **Inline next step**: the next action and its date sit on the row or card | **Filevine** vitals surface the next deadline. **MyCase** inline stage. **Linear** single-key status (`S`). The owner's own rule: "the reason is a column" (MY_OFFICE_REDESIGN §3.5) | [Filevine Vitals](https://support.filevine.com/hc/en-us/articles/360004183551-Vitals), [Linear shortcuts summary](https://keycombiner.com/collections/linear/) | Next-step card (S3), queue row actions (S1), hearing-outcome dialog (S9) |
| P10 | **Command palette + keyboard-first** | **Linear**: "Cmd+K… gives you access to every action… by name", `C`, `S`, `P`, `L`, G-chords. **Superhuman**'s palette rules: available everywhere with one key; one central place; every action discoverable; fuzzy matching with synonyms; context-aware ranking; shortcuts shown next to commands so users learn them; "blazingly fast". **Clio**: "⌘+K / Ctrl+K to open search from any screen" | [Superhuman: build a remarkable command palette](https://blog.superhuman.com/how-to-build-a-remarkable-command-palette/), [Superhuman shortcuts](https://help.superhuman.com/hc/en-us/articles/45191759067411-Speed-Up-With-Shortcuts), [Clio Global Search](https://help.clio.com/hc/en-us/articles/9290347515291-Global-Search) | G1: a legal provider on **Odoo's existing** Ctrl+K palette; `#` namespace for file numbers; keyboard map in §8 |
| P11 | **Global search with recents** | **Clio**: the search bar searches "matters, contacts, documents, notes, tasks, communications, activities, and events"; "when the search field is empty, search shows your recent matters, contacts, documents" | [Clio Global Search](https://help.clio.com/hc/en-us/articles/9290347515291-Global-Search) | Port `legal_office.search_office()` (Arabic-normalised, rule-safe); show recents when the query is empty |
| P12 | **Activity feed** | **Clio** Firm Feed: new tasks appear "in the matter timeline… on the Calendar… and in the Dashboard Firm Feed"; private tasks are excluded. **PracticePanther** "Recent Activity… across all the contacts and matters". **Filevine** Activity Feed section per project | [Clio Manage Tasks](https://help.clio.com/hc/en-us/articles/9204917906971-Manage-Tasks-in-Clio-Manage), [PracticePanther Dashboard](https://support.practicepanther.com/en/articles/629220-dashboard-tutorial), [Filevine: What is a Project](https://support.filevine.com/hc/en-us/articles/360004182091-What-is-a-Project) | Chatter per matter (already there); a manager-only "آخر النشاط" (latest activity) panel on My Day behind *advanced* |
| P13 | **Bulk actions** | **MyCase** Tasks → Actions: "Mark as read, Mark as completed, Change the due date, or Reassign tasks" | [MyCase Tasks overview](https://supportcenter.mycase.com/en/articles/9370074-tasks-overview) | List `<header>` buttons: reassign, change stage, change date, send for approval, print follow-up sheets |
| P14 | **Front door / intake queue** (in-house) | **LawVu**: requests arrive through the Business Portal, email, Slack or Teams; unassigned matters land in an **Intake queue** that someone with "Manage Intake" assigns. Business users "check or request a status update". **Litify** intake "automatically jumps to the next relevant question" | [LawVu intake queues](https://help.lawvu.com/en/articles/3105719-intake-queues-for-in-house-legal-teams), [LawVu Business Portal](https://help.lawvu.com/en/articles/5913119-the-lawvu-business-portal-for-business-users), [LawVu intake](https://lawvu.com/workspace/intake/), [Litify legal CRM](https://www.litify.com/resources/legal-crm) | S14 طلبات الأقسام (department requests, in-house mode) + the approvals inbox S7; the intake dialog asks only what the chosen type needs |
| P15 | **Forgiveness**: drafts and undo | **Linear** keeps local and saved drafts; `Esc` offers to save a draft | [Linear creating issues](https://linear.app/docs/creating-issues) | An "تراجع" (Undo) button on every one-click completion toast (Odoo notifications support `buttons`); the quick-create dialog keeps its draft |
| P16 | **Ready-made content** makes a product easy on day one | **Smokeball**: a "20,000+ form library spanning 250+ matter types". **Clio**: preconfigured accounts with practice-area custom field sets | [Smokeball Matter Types Directory](https://support.smokeball.com/hc/en-us/articles/6011499596951-Matter-Types-Directory), [Clio Preconfigured Accounts](https://help.clio.com/hc/en-us/articles/35393101722523-Preconfigured-Accounts) | Ship Iraqi templates as data: the prototype's ten body categories with their checklists (`02-prototype-intent.md` §1) |

### 1.2 What reviewers say helps and hurts

| Product | Praised for ease | Complaints that matter to us | Lesson |
|---|---|---|---|
| Clio | "easy learning curve", "ready to go immediately with very little setup"; several ways to do the same task | A learning curve "when setting up workflows, automations, and reports". Adding a related contact that does not exist yet means leaving and coming back later | Everyday use should need no setup, but the automation editor is where people struggle, so keep it to one list of steps. Allow inline create in every many2one ([Capterra](https://www.capterra.com/p/105428/Clio/reviews/), [G2](https://www.g2.com/products/clio-clio-manage/reviews?qs=pros-and-cons)) |
| MyCase | "clean and intuitive"; new staff "up to speed fast"; 4.6/5 for ease of use | Some users "preferred the old way tasks were displayed on the main dashboard… easier to see everything at a glance with less clicking" | The home screen must show the tasks themselves, not links to them ([Capterra](https://www.capterra.com/p/115613/MyCase/reviews/), [Lawyerist](https://lawyerist.com/reviews/law-practice-management-software/mycase/)) |
| PracticePanther | "easy to use on day 1", "clean interface" | "workflow automation has a bit of a learning curve"; reports are weak | The same lesson as Clio on automation ([Capterra](https://www.capterra.com/p/140231/PracticePanther-Legal-Software/reviews/?page=2)) |
| Filevine | Customisation power | "the number of fields to fill in… overwhelming"; "the amount of features on the left-hand side… overwhelming"; "you need a person on your staff to handle it" | **Power without defaults is the anti-pattern.** Every configurable thing needs a shipped default and must be hideable ([Capterra](https://www.capterra.com/p/140815/Filevine/reviews/), [Legalware summary](https://legalware.ai/blog/filevine-reviews/)) |
| Litify | Depth on Salesforce | "clunky and unintuitive"; "cumbersome for simple tasks, requiring multiple steps"; "the intake section was complicated" | A generic platform stretched over legal work reads as clunky. Simple tasks must take a single step ([G2](https://www.g2.com/products/litify/reviews?qs=pros-and-cons), [Capterra](https://www.capterra.com/p/160393/Litify/reviews/)) |
| LawVu (in-house) | G2 ease-of-use 9.2; "clean, simple UI" for lawyers **and** business requesters | Documents not viewable inside the matter; matter search | Preview documents in place (pdf.js is shipped); search must be excellent ([G2](https://www.g2.com/products/lawvu/reviews?qs=pros-and-cons), [Hyperstart summary](https://www.hyperstart.com/blog/lawvu-reviews/)) |
| Legal Tracker (in-house) | "user-friendly"; "one-click drill-down reporting" | Mainly an e-billing tool | Every count must drill through, which the owner's rule already requires ([G2](https://www.g2.com/products/thomson-reuters-legal-tracker/reviews), [TR features](https://legal.thomsonreuters.com/en/products/legal-tracker/features)) |

### 1.3 What this owner has already decided (binding)

These rules come from the documents listed at the top. This benchmark confirms them;
it does not reopen them.

- **Matter cockpit, client dossier as the second home, intake as a guided form in
  the navigation, time capture in seconds.** Deliberately *not* borrowed: chart-wall
  dashboards, document assembly and e-filing, and a separate "notes" silo next to the
  chatter (`ux-patterns.md` §1).
- **One module, one database, a mode setting.** The mode drives terminology, menus
  and defaults, **never security** (`legal-product-roadmap.md` §3, §7).
- **Screen rules** (`MY_OFFICE_REDESIGN.md` §3, §12):
  - The largest type on a screen is a subject line, never a digit.
  - Colour is earned.
  - Every count opens the records it counted.
  - The reason is a column.
  - An empty state is good news in two lines.
  - Roles differ in structure, not only in numbers.
  - CSS uses logical properties only.
  - No new runtime dependencies. The palette is Odoo's Ctrl+K.
  - Month names are Iraqi (أيلول, not سبتمبر), formatted with babel `ar_IQ`.
- **Adopt from SAG:** top-level intake, an approver queue, and a per-matter
  follow-up sheet (استمارة متابعة). **Reject:** emoji in the information
  architecture, denormalised name copies, the HTML-blob dossier
  (`sag-legal-module.md` §4–6).
- **Arabic first with zero English leakage. Native views before OWL. No fabricated
  numbers. The auditor never gets a mutation.**

**How the owner's two requests fit together.** The owner asked for "heavy use of
custom OWL components", and the earlier rule says "native views before OWL". The two
agree on one principle: **use OWL where it removes a step or a decision**, and use
native views for registers and configuration. Concretely, OWL builds the home queue,
quick create, next-step card, hearing dialog, checklist, dossier windows and palette
provider. Native views carry list, kanban, calendar, pivot and graph, and settings,
because Odoo already gives them bulk actions, export, favourites, grouping and
accessibility at no cost.

---

## 2. Anti-patterns in the showcase (baseline screenshots)

Every item cites a file in `docs/ldm/evidence/00-baseline/` and its cause in the source.

| # | Screenshot | What is seen | Cause in code | Fix (pattern) |
|---|---|---|---|---|
| A1 | 01, 02–08 (menu bar) | Emoji carry the information architecture (menu and field labels). Emoji are also baked **into selection values**, e.g. `'بانتظار موافقة المدير القانوني ⏳'`, so they leak into badges, exports and PDFs | Emoji appear on 58 lines across `views/*.xml`, `models/*.py` and `dashboard.xml` (`legal_menus.xml`: 6; `legal_task.py` `approval_state` values) | Plain labels; icons come from one component (`LegalIcon`, a Phosphor subset already bundled by the owner). Selection *values* must stay stable; only labels change |
| A2 | 04, 05 | **Two status axes at once.** Row 1 of 04 shows الموافقة (approval) = مسودة (draft) next to الحالة (status) = منجز (done): a matter finished without ever being approved | `state` and `approval_state` are independent selections, both shown as badges in the list and form | **One visible stage track.** Approval becomes a gate shown as a chip or banner only when pending or rejected. Keep both fields in the database for SAG data (§4 S3) |
| A3 | 05 | **Header button soup**: 8 buttons in 5 colours (print, approve, reject, request documents, done, reset to draft, cancel…) plus a status bar | 9 `<button>` elements in `<header>` of `view_legal_task_form`, each with its own `btn-*` colour | ≤ 2 visible actions: the *next step* and the approval (for approvers only). The rest go in an overflow menu "⋯" |
| A4 | 01 | **The dashboard leads with digits.** Five KPI cards, and the largest type is a count. "القضايا المنجزة 1" (completed matters: 1) cannot be acted on. The company filter sits *inside* a KPI card. The list is "latest registered" (by id), not "what needs me". Rows have no actions | `legal_dashboard.xml` KPI band, then `recentTasks = tasks.slice(0,8)` ordered `id desc` | مكتبي / My Day focus queue (S1); KPI numbers move to the analytics screen |
| A5 | 01 (code) | The dashboard loads **every** task and company client-side and counts in JS. It counts drafts as "in progress" (الجارية). "today" is calculated in UTC | `orm.searchRead("legal.task", [], …)` with no limit; `if state in in_progress/draft/pending_docs → inProgress`; `new Date().toISOString()` | One bounded server payload using `formattedReadGroup` for counts; dates in `Asia/Baghdad` |
| A6 | 01, 04 | **Three date formats on two screens**: `2026-09-28` (raw ISO), `06-10-2026`, `٢٨ سبتمبر` (no year, Egyptian month name). Arabic-Indic digits in dates next to Latin digits in amounts | `t-esc="task.session_date"` prints the raw ORM string; the list uses Odoo `ar_001` formatting | One formatter: `ar_IQ` month names, the year shown whenever it is not the current year, and one digit system (open question Q1) |
| A7 | 06 | **A two-step intake that saves nothing.** The wizard asks for company, ministry and department, then opens the *full* blank form. It asks neither the matter type, the title nor the key date. Ministry → department must be chosen by hand | `legal.task.create.wizard.action_proceed()` returns an `act_window` with `default_*` context | One dialog, 3 inputs, driven by a template, saved on submit (S2) |
| A8 | 08 | **The report wizard is a second search screen**: nine filters and a toggle, to print a PDF | `legal.general.report.wizard` repeats the search view's filters and group-bys | "Print what you see": a report bound to the model, applied to the selection or the current domain. The wizard keeps only layout options (S10) |
| A9 | 03 | **The client form leads with empty fields.** Ten labels without values (certificate no., tax no., activity, address, owner, phone, email…) fill the first viewport. The client's matters sit below the fold in a second tab | `legal.company` form `<group>`s render every field regardless of value | Dossier header first (S5). Registration data hidden when empty and revealed with المزيد (more) |
| A10 | 03 | **The dossier is an HTML blob**: "ministry windows" rendered as computed HTML with inline styles and hard-coded `/odoo/action-…` links, plus fake "طي/فتح" (collapse/expand) toggles. It cannot be searched, grouped, filtered or reached by keyboard | `department_cards_html = fields.Html(compute=…)`, `_compute_department_cards_html` (≈170 lines of string HTML) | OWL `BodyWindows` widget over `formattedReadGroup` (S5) |
| A11 | 04 | **The list is too wide.** 11 columns at 1440 px truncate the title, company, ministry, department, lawyer ("…ell Admin") **and the matter number** ("…/2026/009"). The identifier loses its start in RTL. Whole-row red, green and orange text competes with the badges | `view_legal_task_tree`: 12 fields, 5 `optional` (4 shown by default); row-level `decoration-*` | ≤ 6 default columns; number and title in one cell; the number never truncates; colour only on the overdue date cell |
| A12 | 07 | **Collapsed groups by default.** The first screen shows three ministry names and nothing to act on. Code, phone and employee columns are empty | `action_legal_department` context `{'search_default_group_by_ministry': 1}` | A flat, searchable list with a search panel of ministries (S6) |
| A13 | 04, 05 | **Money typed as Float** with "(د.ع)" (IQD) written into the label, and `500,000.00` shows fils nobody uses | `expenses_amount = fields.Float(…"(د.ع)")` | `Monetary` + `currency_id` (IQD, 0 decimals displayed) |
| A14 | 05 | **A state shown as an input**: the computed "متأخر" (overdue) appears as an inert checkbox | `is_overdue` placed in a form `<group>` | A `remaining_days` badge on the due date ("متأخر ٣ أيام", 3 days overdue) |
| A15 | 05 | **Three "who" fields**: main lawyer (`lawyer_id`), assigned lawyers (`lawyer_ids`) and staff (`employee_ids`). The creator is added to the first two by default | `lawyer_id` default `env.user` + `lawyer_ids` default `[uid]` | Show one "المسؤول" (responsible) with `many2one_avatar_user`, which also enables Odoo's built-in Alt+I "assign to me". The team goes behind *advanced* |
| A16 | menus | **Lawyers have no menu route to the matter register.** `action_legal_task` sits only under "الصلاحيات والموافقات" (permissions and approvals), which is manager-only. That folder also mixes *permissions* and *approvals* | `legal_menus.xml`: `menu_legal_approvals_root groups=group_legal_manager` | Register under العمل (work) for everyone; approvals as their own entry for approvers only |
| A17 | 05 | **Two document stores**: a "مرفقات" (attachments) tab with `many2many_binary`, and the chatter's attachments. Notes are plain `Text` | `attachment_ids` m2m + `<chatter/>`; `action_details = fields.Text` | One document panel (dropzone + preview + required-documents mapping); notes as an `html` field with slash commands, or as chatter log notes |
| A18 | 02 (code) | **The kanban groups by department**, so 23 production departments become 23 columns | `default_group_by="department_id"` | Group by stage (Clio stages board) |
| A19 | all (code) | **30 inline `style=` attributes and 121 `!important`**, with physical properties (`border-right: 5px`). This breaks dark mode, makes RTL mirroring fragile and makes theming impossible | kanban card arch; `legal_dashboard.scss` | SCSS tokens + logical properties (`border-inline-start`), as `legal_office` already does |
| A20 | 04 (data) | English leaks into the Arabic UI: "(LLC)", the label "تاريخ الاستحقاق (DUE_DATE)" | field `string`s | Translation coverage test; no Latin text in `ar_001` except identifiers |

**Estimated interaction counts in the showcase** (read from the views and
screenshots; to be measured in the first verification round):

| Journey | Showcase | Target |
|---|---|---|
| Open a new matter with a deadline | ≈ 9–11 interactions, a dialog and then a full form; no steps are generated | ≤ 5, one dialog, steps generated |
| Record a hearing outcome, next date and next task | ≈ 10 (edit the date, type a note, save, then schedule an activity by hand) | ≤ 4 |
| Find a matter by number from anywhere | Manager ≈ 4; **lawyer: no menu route** | 3 (Ctrl+K, type, Enter) |
| Approve one pending matter | ≈ 4 (folder → list → open → approve) | 1 from the inbox |
| Approve 10 | ≈ 40 | ≤ 3 (select all → approve → confirm) |
| See what is due today | Not answerable: the dashboard shows newest-created items | 0: it is the landing screen |

---

## 3. Simple by default, advanced on demand: five disclosure layers

Progressive disclosure is not one "Advanced" tab. The products that feel simple hide
things at several independent levels. Each layer below maps to one Odoo 19 mechanism,
and each is verified in this checkout.

| Layer | Hides | Decided by | Odoo 19 mechanism |
|---|---|---|---|
| **L0 Feature** | Whole capabilities the install does not use: approvals, accounting links, HR staff team, time and fees, client portal, business-unit requests | Manager in الإعدادات (settings, S11) | `res.config.settings` booleans with `implied_group=…`. Views and menus carry `groups="legal_department_management.group_legal_feature_x"`, so a feature that is off leaves **no field, column, button or menu**. This is how Odoo core hides, for example, multi-currency |
| **L1 Role** | What a lawyer, runner, manager, approver or auditor sees first | Security groups (never the mode) | `groups=` on menus, buttons and fields; role-aware payload on My Day (the owner's `legal_office` pattern) |
| **L2 Mode** | Vocabulary and firm-only surfaces (engagement, fees, timer, portal) | Company setting `legal_mode` = in_house / firm / both | Mode groups implied by settings. Per-mode `ir.ui.view` inheritance (a view with `group_ids`) relabels fields and actions, as roadmap §5 Phase 1 already specifies. The mode **never gates data** |
| **L3 Matter type** | Tabs, fields and sections irrelevant to this kind of matter (no hearings on a licence renewal) | The template chosen at creation (`kind`, properties, steps) | `invisible="kind != 'litigation'"` on notebook pages. **`properties` field** (`odoo/orm/fields_properties.py`): per-template extra fields defined on the template (`PropertiesDefinition`), stored as jsonb on the matter, no schema change. The Smokeball/Filevine pattern with zero migrations |
| **L4 In-form "المزيد" (more)** | Secondary fields on a matter or client: ministry (derived), staff team, accounting move, payment and account, reference numbers, approver and date | The user, per form, remembered per user | A `js_class` form controller toggles a CSS class. Fields in `class="o_legal_advanced"` groups are hidden unless the toggle is on **or the field has a value** (Notion's "hide when empty"). Modifiers can read `context` (`getBasicEvalContext` in `model/relational_model/utils.js`), so `invisible="not context.get('legal_advanced') and not expense_account_id"` works in plain arch. The preference persists via `user.setUserSettings()` (`@web/core/user`, backed by `res.users.settings`) |
| (L5 Power user) | Nothing hidden; just faster | The user | Ctrl+K palette provider, hotkeys, bulk list actions, optional columns, pivot/graph, saved favourites |

**Rule for every new field:** it must name its layer. A field that belongs to no layer
is shown to everyone, so it has to earn that place.

**Rejected mechanism:** `groups="base.group_no_one"` (debug mode). It is Odoo's own
"advanced" switch, but it is technical and global. A lawyer should never need
developer mode to see a court case number.

---

## 4. Screens: the proposal

Conventions:
- Arabic RTL: "start" means right.
- Every screen is checked at 1440×900 and 390×844, in `ar_001` and `en_US`, as
  lawyer, manager and runner (§10).
- **Compatibility:** model names (`legal.task`, `legal.company`, `legal.ministry`,
  `legal.department`) and existing xmlids (`action_legal_dashboard`,
  `legal_dashboard_tag`, `action_legal_task`, `action_legal_task_to_approve`,
  `action_legal_company`, `action_legal_department`,
  `action_legal_task_create_wizard`, `action_legal_general_report_wizard`, the view
  xmlids and the menu xmlids) are kept and repointed, never deleted.
- Models named below as *new* (`legal.task.template`, `legal.task.step`,
  `legal.hearing`) are UX needs handed to the architecture stream. This document does
  not decide their fields.

### Global layer (on every screen)

**G1. Legal provider for the Ctrl+K palette**
- **Purpose:** find or do anything from anywhere (P10, P11).
- **Default:** Ctrl+K and a query return matters (by number, title, client, body),
  clients and bodies, ranked together. An empty query shows **recent** matters.
  Commands are listed as well: «ملف جديد» (new file), «سجّل نتيجة جلسة» (record a
  hearing outcome, active when a matter is open), «اذهب إلى مكتبي» (go to My Day),
  «ابدأ المؤقت» (start the timer, firm mode only). Each command shows its hotkey
  (Superhuman's teach-as-you-go rule).
- **Advanced:** the `#` namespace (unused in Community 19) searches **file numbers
  only** (`#2026/09/007`). `/` keeps Odoo's menus and `@` keeps Discuss.
- **OWL:** `LegalCommandProvider` (a registry entry, no component) and
  `LegalCommandItem` (a row template showing number, client and body).
- **Odoo:** `registry.category("command_provider")`, `command_categories` and
  `command_setup` (`core/commands/command_service.js`, `default_providers.js`).
  `useCommand()` for context commands. The server search is a port of
  `legal_office.search_office()`: Arabic normalisation (alef, taa marbuta,
  yaa/alef maksura, tashkeel, tatweel, Arabic-Indic digits) under record rules, with
  `debounceDelay` from `command_setup`.

**G2. "+ جديد" (New) everywhere**
- **Default:** a dropdown with ملف/معاملة (file/matter), جلسة (hearing), مهمة (task),
  وثيقة (document); وقت (time) is added in firm mode. It is pre-filled from the
  context: inside a client it sets the client, inside a matter it sets the matter.
  Every register's New button (list, kanban and calendar quick create) opens the same
  S2 dialog.
- **Odoo:** `Dropdown` / `DropdownItem` (`core/dropdown`). The kanban uses
  `on_create` / `quick_create_view`, and the calendar uses `quick_create_view_id`
  (`views/kanban/kanban_arch_parser.js`, `views/calendar/calendar_arch_parser.js`).

**G3. Timer (firm mode + time feature only)**
- **Default:** a systray clock. One click starts it on the open matter; the running
  timer shows the matter number. Stopping it opens a 2-field confirmation (narrative,
  billable).
- **Advanced:** a day sheet grid (roadmap §6.3: under 5 seconds per line, `1.5` and
  `1:30` both accepted).
- **Odoo:** `registry.category("systray")` (the pattern of `mail/…/call_menu.js`),
  `account.analytic.line`. Odoo Community has **no** `timer` module, so this is custom.

**G4. Forgiveness**
- Every one-click completion (step done, approve, stage move) raises a toast with
  «تراجع» (Undo) for about 6 seconds. Uses `notification.add(…, { buttons })`
  (`core/notifications/notification_service.js`).

### S1. مكتبي / My Day (home): replaces the dashboard, same action and tag

- **Purpose:** answer "what needs me today, and what is the next thing to do on each".
- **Default layout:**

```
┌ مكتبي · الأربعاء ٢٤ أيلول ٢٠٢٦ · محامٍ ───────────────────────── [+ جديد ▾] ┐
│ [ ابحث برقم الملف أو الشركة أو الجهة…                           Ctrl+K ]     │
├──────────────────────────────────────────────────────┬──────────────────────┤
│ ● متأخر · 2                                           │ الأيام القادمة        │
│  براءة ذمة ضريبية سنوية            CASE/2026/09/006   │ اليوم                 │
│  شركة الرافدين · الهيئة العامة للضرائب                  │  جلسة · بداءة الكرخ   │
│  بانتظار: كتاب صحة الصدور — لدى الجهة منذ ٦ أيام عمل    │ الأحد ٢٨ أيلول         │
│                               [تم ✓]  [⋯]   متأخر ٣ أيام│  استحقاق · تسجيل الشركات│
│ ● اليوم · 1   …                                       │ …                     │
│ ● هذا الأسبوع · 4   …                                 │                       │
│ ▸ لاحقًا (6)     ▸ بلا تاريخ (1)                        │ [فتح التقويم]          │
└──────────────────────────────────────────────────────┴──────────────────────┘
```

  - **Rows:** each row shows subject → client · body → **reason** (the next step, and
    who is waiting on whom) → relative date. It carries at most one primary inline
    action: «تم» (done), which completes the next step, or «سجّل الجلسة» (record the
    hearing) for hearings; everything else sits under ⋯.
  - **Bands:** a band with no rows is not drawn. The initial list is capped at 7 rows.
  - **Approvers:** a chip «بانتظار اعتمادي · 2» (awaiting my approval: 2) sits above
    the bands.
- **Behind *advanced*:**
  - scope أنا / فريقي / الكل (me / my team / all, managers only);
  - filters by client, body, responsible person and kind;
  - «المؤشرات» (indicators): a count rail where every count drills through;
  - «آخر النشاط» (latest activity): a firm feed of chatter across matters (managers);
  - a link to the analytics screen (S15).
  - No charts on this screen.
- **OWL components:**
  - `LegalMyDay` (client action registered under the existing `legal_dashboard_tag`);
  - `FocusQueue` + `QueueRow`, ported from `legal_office/work_queue.js`;
  - `AgendaRail`, ported from `legal_office/agenda.js`;
  - `ApprovalChip`;
  - `LegalSearchBox` (opens the palette pre-filled);
  - `LegalClockBadge`, ported from `legal_procedure/…/clock_badge`, which separates
    "with the body for 6 working days" from "waiting on us".
- **Odoo primitives:**
  - one `orm.call("legal.task", "get_my_day")` that returns a bounded, role-aware
    payload, with `formattedReadGroup` for counts (`core/orm_service.js`);
  - `useNavigation(containerRef)` for ↑/↓/Enter (`core/navigation/navigation.js`);
  - `useHotkey("/")` to focus search;
  - `action.doAction` for drill-through;
  - notification with Undo;
  - `Layout` (`search/layout.js`), or `display={}` with its own header, as in
    MY_OFFICE §12.
- **Acceptance:**
  - ≥ 7 actionable rows in the first viewport at 1440×900;
  - the largest text is a subject line;
  - 0 Latin strings in `ar_001`;
  - every count opens its records;
  - completing a step from the queue takes 1 interaction and can be undone.

### S2. Quick create «ملف جديد» (new file): replaces the wizard (same action xmlid)

- **Purpose:** open a matter in one step, with its work generated.
- **Default layout** (Dialog, size `md`):

```
┌ ملف جديد ───────────────────────────────────────────────┐
│ النوع          [ براءة ذمة ضريبية سنوية            ▾ ]  │ ← recent types first
│ الشركة / الموكّل [ مجموعة دجلة التجارية            ▾ ]  │ ← create inline
│ الاستحقاق       [ ١٤ / ١٠ / ٢٠٢٦ ]                       │ ← label from the type: جلسة | استحقاق | لا شيء
│ العنوان         براءة ذمة ضريبية سنوية — دجلة  ✎         │ ← suggested, editable
│ ▸ المزيد: الجهة · المسؤول · الفريق · عاجل · ملاحظة       │
│                          [إنشاء وفتح]   [إنشاء وإضافة آخر] │
└─────────────────────────────────────────────────────────┘
```

  - The **type** (template) supplies:
    - body (department → ministry derived);
    - responsible person (the client's responsible lawyer, otherwise the user);
    - steps with **working-day** offsets, the required documents, the approval
      requirement, the `kind` and the properties definition.
  - **Smart defaults:**
    - the start stage is «قيد الإجراء» (in progress), not «مسودة» (draft), unless the
      template requires approval first, in which case it is «بانتظار الاعتماد»
      (awaiting approval);
    - currency is IQD;
    - the last-used type comes first.
  - **Result:** a toast «أُنشئ CASE/2026/09/010 مع ٦ خطوات و٣ مستمسكات — [فتح]»
    (created CASE/2026/09/010 with 6 steps and 3 required documents — open).
  - **Firm mode, litigation kind:** a fourth input «الخصم» (adverse party) appears.
    A **conflict banner** that cannot be dismissed shows colliding matters and needs
    a manager override with a reason (roadmap Phase 2, checked on
    `commercial_partner_id`).
- **Behind *advanced*:**
  - the «المزيد» (more) disclosure: body override (ministry → department cascade),
    team, urgency, reference numbers, note;
  - «فتح النموذج الكامل» (open the full form).
- **OWL components:**
  - `LegalQuickCreateDialog`;
  - `TemplatePicker` (autocomplete with recents);
  - `ConflictBanner`.
- **Odoo primitives:**
  - the `dialog` service + `Dialog` (`core/dialog/dialog.js`, sizes `sm…fs`, footer
    slot);
  - `Record` (`model/record.js`: `resModel`, `fieldNames`, `mode="edit"`, `values`,
    `hooks.onRootLoaded`, the same pattern as `views/view_components/multi_create_popover.js`
    and `calendar_common_popover.js`) with `Field` components, so the dialog gets
    real onchanges, domains and validation for free;
  - `Many2XAutocomplete` (`views/fields/relational_utils.js`: quick create, "Search
    more", create-and-edit);
  - `orm.call("legal.task", "create_from_template")`;
  - recents via `user.setUserSettings`;
  - `useCommand("ملف جديد", …, { hotkey: "alt+shift+n" })`.
- **Acceptance:**
  - keyboard only, ≤ 5 interactions from Ctrl+K to a saved matter;
  - no second screen;
  - the generated steps, deadlines and activities are visible on the cockpit
    immediately;
  - closing the dialog by accident keeps a draft.

### S3. Matter cockpit (the `legal.task` form, same view xmlid)

- **Purpose:** show where the matter is, what happens next, by when, who holds it and
  what it has cost, without scrolling.
- **Default layout:**

```
┌ CASE/2026/09/007 · دعوى مطالبة بمبلغ عقد توريد          [قيد الإجراء ▾]  [⋯] ┐
│ مجموعة دجلة التجارية · محكمة بداءة الكرخ · أ. زينب · عاجل                    │
│ ●──────●──────◍──────○   تحضير › تقديم › مرافعة › حكم      (phase rail)       │
├─────────────────────────────────────────────────────────────────────────────┤
│ الخطوة التالية:  جلسة المرافعة الثانية — الأحد ٢٨ أيلول (بعد ٤ أيام)          │
│ [سجّل نتيجة الجلسة]     تأجيل · تغيير الموعد · إسناد                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ الموعد القادم ٢٨ أيلول · المستمسكات ٤ من ٦ · المصروفات ٥٠٠٬٠٠٠ د.ع · الجلسات ٢ │  ← vitals
├ الخطوات │ الجلسات │ الوثائق │ المصروفات │ (الوقت والأتعاب) ──────────────────┤
│ …                                                                            │
└──────────────────────────────────────────── chatter: رسالة · ملاحظة · نشاط ───┘
```

  - **Header:** one stage control (`statusbar` on `state`, with
    `statusbar_duration` showing how long the matter has been in each stage). The
    **approval** appears as a banner only while pending or rejected: «بانتظار اعتماد
    المدير القانوني — منذ يومين» (awaiting the legal manager's approval — for 2 days),
    with [اعتماد] (approve) and [رفض] (reject) for approvers only.
  - **Overflow ⋯:** print follow-up sheet, reset to draft, cancel, duplicate, archive.
  - **Tabs follow `kind`:** «الجلسات» (hearings) only for litigation, and «الوقت
    والأتعاب» (time and fees) only in firm mode with the time feature on.
- **Behind *advanced*** (the «المزيد» toggle, plus any field that already has a
  value):
  - ministry (derived);
  - staff team (`employee_ids`, only with the HR feature);
  - accounting links: expense account, move, payment (only with the accounting
    feature);
  - reference numbers: court case number, letter number;
  - template-defined **properties**;
  - approver and date.
  - The full tracking history stays in the chatter.
- **OWL components:**
  - `MatterHeader` (`view_widgets`);
  - `NextStepCard`;
  - `LegalPhaseRail`, ported from `legal_procedure/…/phase_rail` (4–6 phases, never
    13 steps);
  - `StepChecklist`, ported from `legal_checklist` (GOV.UK task-list anatomy, the whole
    row is the target, inline tick);
  - `VitalsStrip`;
  - `DocumentsPanel` (drop, preview, and a tick on the matching required document);
  - `AdvancedToggle` (via a `js_class` form controller).
- **Odoo primitives:**
  - form `js_class`;
  - `registry.category("view_widgets")`;
  - `statusbar`, which already registers the palette commands Alt+X and Alt+Shift+X
    (`views/fields/statusbar/statusbar_field.js`);
  - `statusbar_duration` (`mail/static/src/views/fields/statusbar_duration/`);
  - `remaining_days`, `monetary`, `properties`, `many2one_avatar_user` (enables Alt+I
    and Alt+Shift+I "assign to me" from `mail/…/assign_user_command_hook.js`);
  - editable one2many with `handle`;
  - `<chatter/>`;
  - `useFileViewer` (pdf.js viewer, `core/file_viewer/`);
  - `useCustomDropzone` (`core/dropzone/dropzone_hook.js`);
  - the `file_upload` service with a progress bar (`core/file_upload/`);
  - `ConfirmationDialog`.
- **Acceptance:**
  - ≤ 2 visible header actions;
  - one status axis visible;
  - "what next / by when / who" readable in the first viewport;
  - recording a hearing outcome takes ≤ 3 interactions from the cockpit;
  - a document can be dropped anywhere on the form.

### S4. The register «المعاملات والقضايا» (matters): list, kanban, calendar, pivot, graph

- **Purpose:** find, triage and bulk-edit matters.
- **Default list** (≤ 6 columns):
  - «الملف» (file): number over title in one cell; the number never truncates;
  - client;
  - body (department);
  - «الموعد القادم» (next date) with `remaining_days`;
  - «المسؤول» (responsible) as an avatar;
  - stage badge.
  - The default filter is «مفتوحة» (open), plus «لي» (mine) for lawyers.
  - A **search panel** on the start side lists stage and ministry with counters.
  - Colour only on the overdue date cell. `list_activity` sits in the row.
- **Kanban:** grouped by **stage**. Drag to change stage (the Clio board). Cards show
  title, client, body, next date, avatar and `kanban_activity`.
- **Calendar:** hearings and due dates. `quick_create_view_id` points to the S2 form.
  `show_unusual_days` marks holidays.
- **Bulk actions** (list `<header>`, visible when records are selected): reassign,
  change stage, change due date, send for approval, print follow-up sheets, export.
- **Behind *advanced*:** optional columns (ministry, department, expenses, approval,
  team, created); group-bys, including by property (`properties_group_by_item`);
  pivot and graph; favourites; `multi_edit="1"`.
- **OWL:** none needed. Native views are the right tool (§1.3).
- **Odoo primitives:** list arch (`optional`, `multi_edit`, `<header>`, `sum`, field
  decorations); kanban (`default_group_by="state"`, `quick_create_view`, progressbar);
  calendar; pivot; graph (Chart.js); `<searchpanel>`.
- **IA fix:** a menu for everyone under العمل (work), not under a manager folder (A16).

### S5. Client / company dossier (`legal.company` form)

- **Purpose:** everything about one client or group company, as a hub. Every number
  is a door (ux-patterns §1.2).
- **Default:**
  - a header with name, kind chip and responsible lawyer;
  - **stat buttons:** open matters, hearings in the next 30 days, documents expiring,
    expenses this year; in firm mode also unbilled fees and «رصيد الأمانة» (retainer
    balance);
  - a primary action «ملف جديد لهذه الشركة» (new file for this company), which opens
    S2 pre-filled;
  - «ما يجري الآن» (what is happening now): the 5 most urgent open matters with next
    step and date;
  - «الجهات» (bodies): one chip per government body with its open-matter count;
    clicking opens the register filtered to that client and body.
- **Behind *advanced*:**
  - «بيانات التسجيل» (registration data): entity type, certificate number, tax number,
    activity, address, managing director; hidden when empty, revealed with المزيد;
  - contacts and team;
  - a documents register with expiry dates (licence renewals);
  - the company-file report.
- **OWL:** `BodyWindows` (replaces `department_cards_html`); `DossierStats` (optional).
- **Odoo primitives:** `formattedReadGroup(legal.task, [client, open], ["department_id"])`;
  the `oe_button_box` stat buttons; an embedded one2many list; `action.doAction` with
  a domain.

### S6. «الجهات الرسمية» (government bodies: ministries and departments)

- **Default:**
  - a flat, searchable list of departments: name, ministry, address/governorate, open
    matters;
  - a search panel by ministry;
  - an editable list for managers.
- **Body form:** address, working hours, phone, the **counters** (النوافذ, windows)
  and what each needs (the owner's `legal_counter_walk` concept, the runner's ordered
  stamp list), the linked templates, and open matters.
- **Behind *advanced*:** codes, responsible employee, archive.
- **Note:** `web_hierarchy` does not fit, because ministry and department are two
  models and the hierarchy view needs a `parent_id` on one model. The list plus search
  panel is enough.

### S7. «الاعتمادات» (approvals inbox, same `action_legal_task_to_approve`)

- **Default:**
  - pending items only, each row with [اعتماد ✓] (approve) and [رفض] (reject);
  - reject needs a reason in a dialog, which is logged to the chatter;
  - selecting a row shows a **read-only preview** of the matter beside the list;
  - bulk approve.
- **Behind *advanced*:** approved and rejected history filters; later, delegation.
- **OWL:** a `js_class` list with a preview pane.
- **Odoo primitives:** row `<button type="object">`; list `<header>` bulk button; the
  `View` component (`views/view.js`) embedding the form readonly; a Dialog for the
  reason.
- **Acceptance:** 1 click per approval; 10 approvals in ≤ 3 interactions; the menu is
  visible only to approvers; the auditor sees it with no buttons.

### S8. «المواعيد» (agenda and calendar: hearings and deadlines)

- **Default:** a day-grouped **agenda list** for the next 14 days (me / all), with
  sticky day headers. The month grid is the secondary view.
- **Behind *advanced*:** colour by lawyer or client; filters; the year view.
- **Odoo:** the calendar view (FullCalendar 6.1.11, lazy bundle
  `web.fullcalendar_lib`). Odoo exposes only the scales `day/week/month/year`
  (`calendar_arch_parser.js`: `SCALES`), so the agenda list is the ported
  `legal_office` agenda component, not a calendar scale.

### S9. «سجّل نتيجة الجلسة» (hearing-outcome dialog)

- **Entry points:** from S1 rows, the S3 next-step card, and the calendar event popover.
- **Purpose:** the most frequent act of a litigation lawyer, in one step.
- **Default:**
  - «النتيجة» (outcome) as chips: تأجيل (adjourned) · مرافعة (pleading) · حجز للحكم
    (reserved for judgment) · حكم (judgment) · شطب (struck out) · أخرى (other);
  - «الجلسة القادمة» (next hearing), required when the outcome is تأجيل;
  - «المطلوب قبلها» (what is needed before it), one line, which becomes an activity
    for the responsible person due N working days before;
  - «ملاحظة» (note).
  - Saving writes the hearing, the next hearing, the activity and a chatter line in
    **one transaction**.
- **Behind *advanced*:** court panel and room, attendees, a photo of the minutes. When
  the outcome is **حكم** (judgment), the appeal deadline (مدة الطعن) is proposed from
  the rules; a "recalculate" prompt follows if the judgment date changes (Clio Court
  Rules).
- **Odoo:** `Dialog` + `Record`; the `badge_selection` / `radio` field widgets; the
  date field; `orm.call`; the mail activity API.

### S10. Print and reports

- **Default:** «اطبع ما تراه» (print what you see). Reports bound to the model appear
  in the Print menu for the selection or the current search. The **follow-up sheet**
  (استمارة متابعة) is one page per matter with a QR code that opens the record. The
  company file prints from the dossier.
- **Behind *advanced*:** the existing general-report wizard (xmlid kept) for grouping
  and layout, pre-filled from `active_domain`.
- **Odoo:** `ir.actions.report` with `binding_model_id`; the Python `qrcode` library
  (in Odoo's requirements); `num2words` for amounts in words (تفقيط) on receipts.

### S11. «الإعدادات» (settings: mode and features)

- **Default:**
  - «نوع الجهة» (kind of organisation): ○ قسم قانوني (legal department)
    ○ مكتب محاماة (law office) ○ كلاهما (both);
  - feature switches: approvals, link expenses to accounting, staff team from HR,
    time and fees (firm mode), department requests (in-house), client portal (later);
  - working calendar and public holidays.
  - Each switch has one line saying what appears when it is turned on.
- **Odoo:** `res.config.settings` with `implied_group` (L0) and a company field for
  the mode (L2); `resource.calendar` for working days.
- **Onboarding:** the `onboarding` addon (a setup checklist: choose the mode, review
  the bodies, check templates, create the first matter) and `web_tour` for one guided
  first matter.

### S12. «أنواع المعاملات» (matter templates; managers only)

- **Default:**
  - name, `kind`, default body, default responsible person, expected duration;
  - **الخطوات** (steps): an editable list with handle, step name, "after N working
    days from" (start or trigger), responsible role, and linked required document;
  - **المستمسكات** (required documents).
- **Behind *advanced*:** «حقول إضافية» (extra fields: a `PropertiesDefinition` editor);
  approval rules (always, or when expenses exceed X); a follow-up activity plan.
- **Seed data:** the prototype's ten Iraqi body categories and their checklists: هيئة
  الاتصالات (communications commission), الماء والكهرباء (water and electricity),
  تسجيل الشركات (company registration), الضرائب (taxes), المرور (traffic), الضمان
  الاجتماعي (social security), المعارض (exhibitions), اتحاد الناقلين (transporters'
  union), كتّاب العدول (notaries), ضريبة المدير المفوض (managing director's tax). The
  product is useful on day one (P16).
- **Odoo:** form + one2many `handle` + `properties` definition. **Activity plans**
  (`mail.activity.plan` + `mail.activity.plan.template`: `delay_count`, `delay_unit`
  days/weeks/months, `delay_from` before/after the plan date, `responsible_type`
  "Ask at launch" or a default user) cover generic follow-ups. However, they count
  **calendar** days only, so legal steps need our own working-day scheduler on
  `resource.calendar`. Activity-type chaining (`chaining_type="trigger"`) gives
  Filevine-style dependent tasks for simple chains.

### S13. Time and fees (firm mode)

G3 plus the day sheet and the WIP board (roadmap §6.3–6.4). Not detailed here;
building it depends on roadmap Phases 3–4.

### S14. «طلبات الأقسام» (department requests, in-house mode; LawVu front door)

- **Default:**
  - requesters (HR, procurement, management) fill 3 fields: «ماذا تحتاج» (what do you
    need), «أي شركة» (which company), «متى» (by when), plus an attachment;
  - the legal manager's queue converts a request into a matter through S2, with the
    template suggested;
  - the requester sees the status and can ask «ما آخر المستجدات؟» (what is the
    latest?).
- **Odoo:** the internal-user form plus `portal` later; the queue is a filtered list.
  Scope depends on the coverage stream.

### S15. «التحليلات» (analytics; managers)

- **Purpose:** KPIs live here, not on My Day.
- **Content:** native pivot and graph; optionally a community `spreadsheet_dashboard`
  board; the owner's `LegalChart` (Chart.js 4.4.5 through
  `loadBundle("web.chartjs_lib")`) for bespoke panels. Every figure drills through.

### S16. «جولتي» (runner's route; mobile)

- **Purpose:** the runner at government counters.
- **Default** (at `env.isSmall`):
  - today's administrative steps grouped by body and address, with the counter list;
  - the required documents as a checklist;
  - **photograph the stamped paper** (file input with the `capture` attribute →
    upload);
  - **scan the QR** on a file cover to open it.
- **Odoo:** `core/barcode/barcode_dialog.js` + the shipped `zxing-library`; the
  owner's `legal_scan`; `file_upload`.

---

## 5. Component inventory

| Component | Screens | Built on (Odoo 19) | Port from (owner's code, LGPL-3) |
|---|---|---|---|
| `LegalMyDay` (client action, tag `legal_dashboard_tag`) | S1 | `Layout`, orm, action, `useNavigation`, `useHotkey` | `legal_office/static/src/office/legal_office.js` |
| `FocusQueue` / `QueueRow` | S1 | `useNavigation`, notification (Undo) | `legal_office/…/work_queue.js` |
| `AgendaRail` | S1, S8 | luxon, action | `legal_office/…/agenda.js` |
| `LegalCommandProvider` | G1 | `command_provider` / `command_setup` registries, `useCommand` | `legal_office/…/legal_search_utils.js` + `search_office()` |
| `LegalQuickCreateDialog` + `TemplatePicker` | S2, G2 | `Dialog`, `Record`, `Field`, `Many2XAutocomplete`, `user.setUserSettings` | new |
| `ConflictBanner` | S2 (firm) | orm | new (roadmap Phase 2 design) |
| `MatterHeader`, `NextStepCard`, `VitalsStrip` | S3 | `view_widgets`, `remaining_days`, `monetary` formatters | new |
| `LegalPhaseRail` | S3 | OWL | `legal_procedure/static/src/components/phase_rail/` |
| `StepChecklist` | S3, S16 | x2many, orm | `legal_procedure/…/checklist/` |
| `LegalClockBadge` | S1, S3 | OWL | `legal_procedure/…/clock_badge/` |
| `DocumentsPanel` | S3, S5 | `useCustomDropzone`, `file_upload`, `useFileViewer` (pdf.js) | new |
| `HearingOutcomeDialog` | S9 | `Dialog`, `Record`, `badge_selection` | new |
| `AdvancedToggle` (form `js_class`) | S3, S5 | `FormController` subclass, `user.setUserSettings`, `context` in modifiers | new |
| `BodyWindows` | S5 | `formattedReadGroup`, action | replaces `department_cards_html` |
| `ApprovalPreviewList` (list `js_class`) | S7 | `ListController`, `View` | new |
| `LegalTimer` (systray) | G3 | `systray` registry | new |
| `LegalScan` | S16 | `barcode_dialog`, zxing | `legal_procedure/…/scan/` |
| `LegalKpiTile`, `LegalChart` | S15 | Chart.js via `loadBundle` | `legal_procedure/…/kpi_tile`, `…/chart` |
| `LegalIcon` | all | OWL + local SVG subset | `legal_office/…/legal_icon.js` (Phosphor Duotone subset, MIT) |

**Port, do not depend.** SAG must be able to install `legal_department_management` on
its own. Copy the components into this module's namespace; the owner owns both codebases,
so this is allowed. Do not add a manifest dependency on `legal_office` or `legal_procedure`.

---

## 6. Odoo 19 primitives verified in this checkout

All paths are relative to `odoo-19.0/addons/` unless noted.

| Need | Primitive | Where (verified) | Notes |
|---|---|---|---|
| Command palette | `command` service, `useCommand`, registries `command_provider`, `command_categories`, `command_setup` | `web/static/src/core/commands/command_service.js` (Ctrl+K bound via `hotkeyService.add("control+k", …)`), `command_hook.js`, `default_providers.js` | Namespaces in use: `/` menus (`web/…/webclient/menus/menu_providers.js`), `@` Discuss (`mail/…/discuss_command_palette.js`). `#` is free in Community (used only in tests) |
| Hotkeys | `useHotkey(key, cb, {area, global, isAvailable, bypassEditableProtection, allowRepeat})` | `web/…/core/hotkeys/hotkey_hook.js`, `hotkey_service.js` | Holding **Alt** shows the `data-hotkey` hints overlay. **Physical keys are preferred on non-Latin layouts** (`getActiveHotkey`: "Prefer physical keys for non-latin keyboard layout"), so shortcuts work with the Arabic keyboard active |
| Built-in commands we get for free | Statusbar next/previous stage (Alt+X / Alt+Shift+X), assign (Alt+I, Alt+Shift+I, Alt+Shift+U), priority (Alt+R) | `web/…/fields/statusbar/statusbar_field.js`, `mail/…/fields/assign_user_command_hook.js`, `web/…/fields/priority/priority_field.js` | Apply only when the matching widgets are on the form |
| Dialogs | `Dialog` (size `sm/md/lg/xl/fs`, footer slot, `onExpand`), `dialog` service, `ConfirmationDialog`, `FormViewDialog`, `SelectCreateDialog` | `web/…/core/dialog/`, `core/confirmation_dialog/`, `views/view_dialogs/` | |
| Relational autocomplete | `Many2XAutocomplete`, `useOpenMany2XRecord`, `useSelectCreate` | `web/…/views/fields/relational_utils.js` (class at l.198) | Quick create and "Search more…" built in |
| Record-backed custom UI | `Record` (props `resModel`, `fieldNames`/`activeFields`, `resId`, `mode`, `values`, `hooks`) + `Field` | `web/…/model/record.js`, `views/fields/field.js`; usage examples `views/calendar/calendar_common/calendar_common_popover.js`, `views/view_components/multi_create_popover.js` | Real onchange, domains, validation and widgets inside our own dialogs |
| Data access | `useService("orm")`: `call`, `searchRead`, `webSearchRead`, `webRead`, `formattedReadGroup`, `formattedReadGroupingSets`, `searchCount`, `webSave`, `cache()` | `web/…/core/orm_service.js` | Use `formattedReadGroup` for counts, never client-side reduces (A5) |
| Popovers | `usePopover(Component, options)` | `web/…/core/popover/popover_hook.js` | Row "⋯" menus, the avatar card |
| Keyboard navigation in custom lists | `useNavigation(containerRef, options)` | `web/…/core/navigation/navigation.js` | |
| Drag and sort | `useSortable` | `web/…/core/utils/sortable_owl.js` | |
| Fuzzy matching | `fuzzyLookup`, `fuzzyLevenshteinLookup` | `web/…/core/utils/search.js` | Client side only; Arabic normalisation stays on the server |
| Notifications with Undo | `notification.add(msg, { buttons, sticky, autocloseDelay })` | `web/…/core/notifications/notification_service.js` | |
| Per-user preferences | `user.setUserSettings(key, value)` | `web/…/core/user.js` (→ `res.users.settings`) | For the "advanced" toggle state and recent templates |
| Calendar | calendar view, FullCalendar **6.1.11** (core, daygrid, timegrid, **list**, interaction, luxon3), lazy bundle `web.fullcalendar_lib`, `useFullCalendar` | `web/static/lib/fullcalendar/`, `web/__manifest__.py`, `web/…/views/calendar/hooks/full_calendar_hook.js` | Arch attributes include `quick_create`, `quick_create_view_id`, `multi_create_view`, `event_open_popup`, `color`, `avatar_field`, `show_unusual_days`, `aggregate`, `scales` (day/week/month/year only) |
| Charts | **Chart.js 4.4.5** (+ luxon adapter), lazy bundle `web.chartjs_lib` via `loadBundle` | `web/static/lib/Chart/Chart.js`, `web/__manifest__.py` | The owner's `LegalChart` wrapper already manages lifecycle and RTL |
| Files | `file_upload` service (progress bar), `FileInput`, `useCustomDropzone`, `useFileViewer` (pdf.js, images, video, text), `many2many_binary`, `pdf_viewer` field | `web/…/core/file_upload/`, `core/file_input/`, `core/dropzone/dropzone_hook.js`, `core/file_viewer/`, `web/static/lib/pdfjs` | In-place preview answers LawVu's top complaint |
| Rich text | `html` field (`html_editor`), **powerbox** slash commands, text-direction plugin, tables, signature | `html_editor/static/src/fields/html_field.js` (registered with `force: true`), `html_editor/static/src/main/powerbox/`, `…/text_direction_plugin.js` | For notes and pleading summaries |
| Activities | activity view, `list_activity`, `kanban_activity`, activity plans (`mail.activity.plan`/`…plan.template`), activity-type chaining | `mail/static/src/views/web/activity/`, `mail/…/fields/list_activity`, `mail/models/mail_activity_plan_template.py` (`delay_count`, `delay_unit`, `delay_from`, `responsible_type`), `mail/models/mail_activity_type.py` (`chaining_type`, `triggered_next_type_id`) | Plans count calendar days, not working days (see S12) |
| Stage time | `statusbar_duration` | `mail/static/src/views/fields/statusbar_duration/` | The SLA story on the form at no cost |
| Per-type fields | `fields.Properties` / `fields.PropertiesDefinition`, `properties` widget, group by property | `odoo/orm/fields_properties.py`, `web/…/views/fields/properties/`, `web/…/search/properties_group_by_item/` | L3 disclosure with no schema change |
| Date and relative date | `remaining_days`, `datetime` widgets, luxon | `web/…/views/fields/remaining_days/` | |
| Scan | Barcode/QR dialog + **zxing-library** | `web/…/core/barcode/`, `web/static/lib/zxing-library` | |
| Signature | `signature` widget + `signature_pad` | `web/…/views/fields/signature`, `web/static/lib/signature_pad` | Receipt of original documents |
| Onboarding | `onboarding` addon, `web_tour` | `addons/onboarding`, `addons/web_tour` | |
| Management boards | `spreadsheet_dashboard` (Community) | `addons/spreadsheet_dashboard` | Optional for S15 |
| Systray | `registry.category("systray")` | e.g. `mail/…/discuss/call/common/call_menu.js` | Timer (G3). **No `timer` module in Community** |

---

## 7. Third-party libraries: verdict

**Conclusion: no new runtime JS library is needed.** Every capability the screens
require already ships in Odoo 19 Community, under LGPL-3, MIT or OFL. Adding a
duplicate would cost bundle size, licence review and a second styling system, and
the owner's rule is zero new runtime dependencies (MY_OFFICE §4).

| Need | Shipped equivalent | Considered and **rejected** |
|---|---|---|
| Command palette | Odoo Ctrl+K palette | cmdk, kbar (React-only) |
| Calendar and agenda | FullCalendar 6.1.11 incl. list plugin | FullCalendar Premium resource/timeline (commercial licence), vis-timeline |
| Charts | Chart.js 4.4.5 | ECharts, ApexCharts |
| Dates, Hijri display for Eid | luxon + browser `Intl` (`islamic-umalqura` calendar) | moment-hijri, date-fns |
| Fuzzy search | server-side Arabic normalisation (ported) + `fuzzyLookup` | Fuse.js (would bypass record rules if run client-side over full data) |
| Drag, drop, sort | `useSortable`, dropzone | SortableJS, dropzone.js |
| PDF preview | pdf.js | — |
| QR / barcode | zxing-library | html5-qrcode |
| Rich text | html_editor with powerbox | TipTap, Quill |
| Data grid | native list view | AG Grid, TanStack Table (MY_OFFICE §4) |
| Guided onboarding | `web_tour`, `onboarding` | Shepherd.js, intro.js |
| Gantt | — (enterprise only) | frappe-gantt. Not needed: legal work is dated steps, not resource-levelled bars |

**Allowed, with a reason:**
- **Phosphor Icons, local SVG subset (MIT).** Already bundled by the owner in
  `legal_office` (`LegalIcon`). Reusing it gives one icon language and replaces the
  emoji (A1). It is static assets, not a runtime library.

**Candidates to raise with the owner, not to adopt now:**
- **`docxtpl` (Python, LGPL-2.1)** for Word output. Iraqi law offices draft pleadings
  and letters in Word and edit them; QWeb produces PDF only. The roadmap put document
  assembly **out of scope**, so this is open question Q6.
- **`tesseract.js` (Apache-2.0) or server-side Tesseract** for OCR of scanned official
  letters, to pre-fill a letter's number and date. The prototype had a scanner modal.
  Arabic OCR accuracy on stamped, photographed letters is uncertain and the payload is
  several MB. Evaluate against real SAG letters before committing.

---

## 8. Keyboard map (checked against Odoo 19's built-in shortcuts)

Built-ins found with `grep` for `data-hotkey` and `hotkey:` across `web` and `mail`:
- Alt + A, C, H, J, K, M, N, Q, S, T, U, V, X, Z, I, R, B, F;
- Alt + Shift + A, I, M, Q, U, X;
- Alt + Shift + T (used by `project_todo`, which SAG may have installed).

Browsers on Windows also reserve Alt + D, E and F.

| Key | Action | Status |
|---|---|---|
| Ctrl+K | Palette: search matters, clients and bodies, and run commands | Odoo built-in; we add a provider |
| `#` in the palette | File-number search | New namespace (free in Community) |
| Alt+Shift+N | ملف جديد (new file, S2) | **Free**: verified unused |
| Alt+Shift+H | سجّل نتيجة الجلسة (record hearing outcome, S9) on the current matter | **Free**: verified unused |
| Alt+X / Alt+Shift+X | Next / previous stage | Odoo built-in (statusbar) |
| Alt+I / Alt+Shift+I | Assign to… / assign to me | Odoo built-in (with `many2one_avatar_user`) |
| Alt+Shift+A | My activities | Odoo built-in (mail systray) |
| `/` | Focus search on مكتبي | New, area-restricted to S1 |
| ↑ ↓ Enter | Move and open in the focus queue | New (`useNavigation`, area-restricted) |
| Ctrl+Enter | Mark the focused row's next step done (with Undo) | New, area-restricted |
| Alt+Shift+W | Start/stop timer (firm) | **Free**: verified unused (avoid Alt+Shift+T) |

**Rules:**
- Never bind a single letter without a modifier outside an area-restricted list. An
  Arabic typist in a text field must never trigger an action.
- Every custom command is registered with `useCommand` so it also appears, with its
  key, in Ctrl+K (Superhuman rule 3).

---

## 9. Terminology by mode (L2)

| Concept | Field / model | قسم قانوني (in-house) | مكتب محاماة (law office) |
|---|---|---|---|
| The party served | `legal.company` | الشركة / الجهة التابعة (group entity) | الموكّل (client) |
| The unit of work | `legal.task` | المعاملة / القضية (procedure / case) | القضية / ملف الموكّل (case / client file) |
| Responsible person | `lawyer_id` | الموظف القانوني المسؤول (responsible legal officer) | المحامي المسؤول (responsible lawyer) |
| Money on the matter | `expenses_amount` | المصروفات والرسوم المدفوعة (expenses and fees paid) | المصروفات القابلة للاسترداد · الأتعاب (recoverable expenses · fees) |
| Approval | `approval_state` | اعتماد المدير القانوني (legal manager's approval) | اعتماد الشريك المسؤول (responsible partner's approval) |
| Front door | S14 | طلبات الأقسام (department requests) | استقبال الموكّلين (client intake) |
| Home | S1 | مكتبي (My Day) | مكتبي (My Day) |

**Implementation:** per-mode inherited views restricted by mode groups (`ir.ui.view`
inheritance applied only for users in the group), plus two sets of action names.
Never string surgery in Python (roadmap §5 Phase 1). In **both** mode, the neutral
label «الشركات والموكّلون» (companies and clients) is used, which is SAG's current label.

---

## 10. Verification plan (visual evidence for every screen)

The owner wants a team-style workflow with "visual verification of everything". Each
build round produces `docs/ldm/evidence/<round>/`:

1. **Screens** (Playwright): S1–S12 at 1440×900 and 390×844, in `ar_001` and
   `en_US`, as the roles lawyer, manager/approver, runner and auditor.
2. **Automatic checks on each capture:**
   - no Latin text in `ar_001` except identifiers;
   - no emoji;
   - the element with the largest computed font size is text, not a digit (S1);
   - visible header buttons ≤ 2 (S3);
   - default list columns ≤ 6 (S4);
   - no horizontal scroll at 390 px;
   - no console errors;
   - focus ring visible on Tab.
3. **Journeys with interaction counts** (clicks + key presses recorded by the script)
   against the targets in §2: new matter ≤ 5, hearing outcome ≤ 4, find by number ≤ 3,
   approve 1 / approve 10 ≤ 3, what is due today = 0.
4. **Upgrade check:** install the baseline on a copy of SAG-like data (10 ministries,
   23 departments, 2 companies, 11 matters), upgrade, re-run 1–3. No record may lose
   its state, approval, dates, amounts or attachments.
5. **Accessibility:** WCAG 2.1 AA contrast, 44 px targets on mobile, keyboard reach
   of every action, `prefers-reduced-motion`.

---

## 11. Open questions for the owner

| # | Question | Why it matters |
|---|---|---|
| Q1 | **Digits in the Arabic UI**: Arabic-Indic (٠١٢) or Latin (012)? | The showcase mixes both on one screen (A6). One rule, applied everywhere |
| Q2 | **One umbrella noun** for `legal.task`: «الملف» (the file), or keep «المعاملة / القضية»? | The kind (administrative/litigation) already distinguishes them; one noun makes the menus and palette read simply |
| Q3 | Does "both" mean **one company doing both kinds of work**, or **several companies with different modes**? | Mode is a company field; labels are per user group. Mixed multi-company needs neutral labels |
| Q4 | Timer and fees in the **first** professional release, or after the in-house core? | Roadmap orders billing after engagements |
| Q5 | In-house **department requests** (S14) now or later? | LawVu shows it is the in-house "front door"; it adds a requester role |
| Q6 | **Word output** (docxtpl) for pleadings and letters: revisit the roadmap's "document assembly out of scope"? | Iraqi offices draft in Word; PDF-only output forces retyping |

---

## Sources

**Clio**
- Matter Templates: https://help.clio.com/hc/en-us/articles/18353050138651-Matter-Templates
- Task Lists: https://help.clio.com/hc/en-us/articles/9206286672155-Task-Lists
- Automated Workflows: https://help.clio.com/hc/en-us/articles/35132279298843-Clio-Manage-Automated-Workflows
- Manage Tasks: https://help.clio.com/hc/en-us/articles/9204917906971-Manage-Tasks-in-Clio-Manage
- Navigate Clio Manage: https://help.clio.com/hc/en-us/articles/9290390462875-Navigate-Clio-Manage
- Time Entries: https://help.clio.com/hc/en-us/articles/9289741706779-Time-Entries
- Matter's Dashboard: https://help.clio.com/hc/en-us/articles/16681289917595-Matter-s-Dashboard
- Personal & Matter Dashboards: https://support.clio.com/hc/en-us/articles/204410037-Personal-Matter-Dashboards
- Matter Stages: https://help.clio.com/hc/en-us/articles/15083241879195-Matter-Stages
- Stages board (third party): https://streamlined.legal/clio-features/transform-your-legal-practice-with-stages-clios-new-kanban-board/
- Global Search: https://help.clio.com/hc/en-us/articles/9290347515291-Global-Search
- Court Rules: https://help.clio.com/hc/en-us/articles/9289840995867-Court-Rules
- Court Rules FAQ: https://support.clio.com/hc/en-us/articles/4409633822107-FAQ-Court-Rules-Enhancements
- Custom Fields: https://help.clio.com/hc/en-us/articles/9285493193115-Get-Started-With-Custom-Fields
- Custom Fields FAQ: https://support.clio.com/hc/en-us/articles/203139814-Custom-Fields-FAQ
- Preconfigured Accounts: https://help.clio.com/hc/en-us/articles/35393101722523-Preconfigured-Accounts
- Reviews: https://www.capterra.com/p/105428/Clio/reviews/ · https://www.g2.com/products/clio-clio-manage/reviews?qs=pros-and-cons

**MyCase**
- Workflow overview: https://supportcenter.mycase.com/en/articles/9370082-workflow-overview
- Creating and applying workflows: https://supportcenter.mycase.com/en/articles/9370081-creating-and-applying-workflows
- Lawyerist on MyCase Workflows: https://lawyerist.com/news/mycase-workflows/
- Tasks overview: https://supportcenter.mycase.com/en/articles/9370074-tasks-overview
- Case Stages: https://supportcenter.mycase.com/en/articles/9369886-case-stages
- Reviews: https://www.capterra.com/p/115613/MyCase/reviews/ · https://lawyerist.com/reviews/law-practice-management-software/mycase/

**PracticePanther**
- Dashboard: https://support.practicepanther.com/en/articles/629220-dashboard-tutorial
- Workflows: https://support.practicepanther.com/en/articles/480078-automating-task-event-workflows
- Tasks: https://support.practicepanther.com/en/articles/480005-tasks-tutorial
- Time Entries: https://support.practicepanther.com/en/articles/480031-time-entries
- Reviews: https://www.capterra.com/p/140231/PracticePanther-Legal-Software/reviews/?page=2

**Smokeball**
- AutoTime: https://www.smokeball.com/features/legal-time-tracking-software
- AutoTime Basics: https://support.smokeball.com/hc/en-us/articles/5860708227863-AutoTime-Basics
- Change a Matter Type: https://support.smokeball.com/hc/en-us/articles/13270415150231-Change-a-Matter-Type
- Matter Types Directory: https://support.smokeball.com/hc/en-us/articles/6011499596951-Matter-Types-Directory

**Filevine**
- What is a Project: https://support.filevine.com/hc/en-us/articles/360004182091-What-is-a-Project
- Vitals: https://support.filevine.com/hc/en-us/articles/360004183551-Vitals
- Flex Sections: https://support.filevine.com/hc/en-us/articles/360022614491-Flex-Sections
- Taskflow: https://support.filevine.com/hc/en-us/articles/360005080892-Taskflow
- Phases: https://support.filevine.com/hc/en-us/articles/360004140772-Phases
- Reviews: https://www.capterra.com/p/140815/Filevine/reviews/ · https://legalware.ai/blog/filevine-reviews/

**Litify**
- Legal CRM: https://www.litify.com/resources/legal-crm
- Reviews: https://www.g2.com/products/litify/reviews?qs=pros-and-cons · https://www.capterra.com/p/160393/Litify/reviews/

**LawVu**
- The legal workspace explained: https://help.lawvu.com/en/articles/6636506-the-lawvu-legal-workspace-explained
- Intake queues: https://help.lawvu.com/en/articles/3105719-intake-queues-for-in-house-legal-teams
- Business Portal for business users: https://help.lawvu.com/en/articles/5913119-the-lawvu-business-portal-for-business-users
- Intake: https://lawvu.com/workspace/intake/
- Reviews: https://www.g2.com/products/lawvu/reviews?qs=pros-and-cons · https://www.hyperstart.com/blog/lawvu-reviews/

**Thomson Reuters Legal Tracker**
- Features: https://legal.thomsonreuters.com/en/products/legal-tracker/features
- Reviews: https://www.g2.com/products/thomson-reuters-legal-tracker/reviews
- Matter management guide (third party): https://fast.io/resources/thomson-reuters-legal-tracker/

**Linear**
- Creating issues: https://linear.app/docs/creating-issues
- My issues: https://linear.app/docs/my-issues
- Conceptual model: https://linear.app/docs/conceptual-model
- Shortcut collection (third party): https://keycombiner.com/collections/linear/

**Superhuman**
- How to build a remarkable command palette: https://blog.superhuman.com/how-to-build-a-remarkable-command-palette/
- Shortcuts: https://help.superhuman.com/hc/en-us/articles/45191759067411-Speed-Up-With-Shortcuts
- Remind Me: https://help.superhuman.com/hc/en-us/articles/43822934607251-Remind-Me

**Notion**
- Property visibility (third party): https://super.so/blog/hide-notion-properties
- Intro to databases: https://www.notion.com/help/intro-to-databases

**Internal**
- `docs/research/ux-patterns.md`
- `docs/legal-product-roadmap.md`
- `docs/ui-audit/MY_OFFICE_REDESIGN.md`
- `docs/external-review/sag-legal-module.md`
- `docs/ldm/research/02-prototype-intent.md`
- `docs/ldm/evidence/00-baseline/*.png`
- `custom_addons/legal_department_management/**`
- `custom_addons/legal_procedure/static/src/components/**`
- `custom_addons/legal_office/static/src/office/**` (read only)
- `odoo-19.0/addons/{web,mail,html_editor}/**`
- `odoo-19.0/odoo/orm/fields_properties.py`
