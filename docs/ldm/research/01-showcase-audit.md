# 01 — Showcase audit: `legal_department_management` 19.0.6.3.0

**Subject:** `custom_addons/legal_department_management`, the showcase exactly as
received (commit `ccebae7`), author SAG Group, LGPL-3.
**Date:** 2026-09-24 · **Method:** every source file read line by line (32 files,
about 3,300 lines, excluding the PNG icon and the stray `.pyc` files), the eight baseline screenshots in
`docs/ldm/evidence/00-baseline/` viewed, the baseline install log
(`.odoo_logs_ldm/baseline_install.log`) searched, and every framework claim that a
finding depends on checked against the local Odoo 19 source (`odoo-19.0/`). §7
lists those checks. Claims that turned out wrong on checking are listed there too,
so nobody builds on them.

**Severity scale.** *Critical*: data loss or a security breach in SAG production
today. *High*: a security or correctness hole a normal user can hit, or a defect
that blocks a core job. *Medium*: wrong or misleading behaviour with a workaround.
*Low*: quality, hygiene or clarity. *Info*: noted, no action required on its own.

---

## 0. Verdict in one paragraph

The showcase is a **government-transactions tracker** (متابعة المعاملات: following a
client's paperwork through ministries and their directorates) with a thin
litigation veneer: one date field for the next hearing. Four real models
(`legal.ministry` → `legal.department` for government bodies, `legal.company` for
the client or group company, `legal.task` for the matter), three wizards, three
PDF reports, one daily reminder job, two groups and a hand-built OWL dashboard.
Its **ideas are sound and are what SAG's users rely on**: start a matter from
anywhere, a client dossier that shows every government body the client has
matters with, an approval queue for the legal manager, a printable follow-up
form, and lawyers who see only their own clients. Its **implementation cannot be
kept as is**:

- The approval can be self-granted or forged over RPC.
- A lawyer the user interface never shows (`lawyer_id`) keeps access to the
  matter.
- Every Settings administrator is silently a legal manager.
- In Odoo 19 the two groups cannot be assigned without developer mode.
- The reminder job duplicates overdue reminders every day.
- Money is an unlabelled `Float`.
- The accounting links are never filled.
- There is no translation layer. 578 lines of Arabic source text make English
  impossible for server messages.
- The screens are cluttered: up to seven header buttons in six colours, and 66
  lines carrying emoji.

The rebuild must keep the four model names, the xmlids and the selection values
(§4) and upgrade SAG's data in place. It must also replace most of the view and
controller layer (§5).

---

## 1. Full inventory

### 1.1 Manifest and file map

| Item | Value | Where |
|---|---|---|
| Name | `قسم الشؤون القانونية والمحاماة المتطور` ("Advanced legal affairs and advocacy department"), Arabic only | `__manifest__.py:3` |
| Version | `19.0.6.3.0` | `:4` |
| Depends | `base`, `mail`, `hr`, `account` | `:20` |
| Data order | security → access CSV → sequence → cron → 3 report files → 8 view files | `:21-37` |
| Not loaded | `report/legal_reports.xml` exists but is **not in the manifest** | — |
| Assets | `web.assets_backend`: dashboard `.scss`, `.js`, `.xml` | `:38-44` |
| Application | `True`; menu icon `static/description/icon.png` (512×512) plus `icon.svg` (scales of justice on a shield) | `:45` |
| Tests | **none** (no `tests/` folder) | — |
| Translations | **none** (no `i18n/` folder); install log line 970: *"no translation for language ar_001"* | — |
| Stray files | `__pycache__/*.pyc` committed alongside the sources; `.gitignore` excludes them but they were shipped | — |

### 1.2 Models and fields

Legend: **Req** required · **St** stored (computed fields only; plain fields are
stored) · **Tr** `tracking=True` · **Ro** readonly at model level.

#### `legal.task`: "إجراء / قضية / معاملة قانونية" (procedure, case or government transaction)

`_inherit = ['mail.thread', 'mail.activity.mixin']`, `_order = 'due_date asc, id desc'`
(`legal_task.py:6-10`). `_rec_name` is the default `name`, so the matter number is
**not** part of the display name.

| Field | Type | Req | St/compute | Tr | Other | Line |
|---|---|---|---|---|---|---|
| `task_number` | Char | | | | `copy=False`, `readonly`, default `_('مسودة')` ("draft"); replaced in `create()` by the `legal.task` sequence | 12 |
| `name` | Char | ✓ | | ✓ | | 13 |
| `legal_company_id` | M2o `legal.company` | ✓ | | ✓ | **`ondelete='cascade'`** | 14-20 |
| `company_name` | Char | | related `legal_company_id.name`, **store** | | used nowhere | 21 |
| `ministry_id` | M2o `legal.ministry` | | | ✓ | `ondelete='restrict'`; kept in line with the department only by onchange | 23-28 |
| `ministry_name` | Char | | related, **store** | | used nowhere | 29 |
| `department_id` | M2o `legal.department` | ✓ | | ✓ | `ondelete='restrict'` | 31-37 |
| `department_name` | Char | | related, **store** | | used nowhere | 38 |
| `state` | Selection | | | ✓ | `draft` مسودة (draft) · `in_progress` قيد الإجراء (in progress) · `pending_docs` بانتظار الوثائق وصحة الصدور (waiting for documents and verification of issuance) · `done` منجز (done) · `cancelled` ملغى (cancelled); default `draft`; not `required` | 50-56 |
| `approval_state` | Selection | | | ✓ | `draft` مسودة · `to_approve` "…⏳" · `approved` "…✓" · `rejected` "…✕" (**emoji in the labels**); default `draft` | 59-64 |
| `approver_id` | M2o `res.users` | | | ✓ | readonly **in the field definition only**, so it is writable over RPC | 66 |
| `approval_date` | Datetime | | | | readonly (same caveat) | 67 |
| `lawyer_id` | M2o `res.users` | | | ✓ | default = current user; **shown in no view** | 70-75 |
| `lawyer_ids` | M2m `res.users` via `legal_task_lawyers_rel(task_id, user_id)` | | | ✓ | default `[current user]` | 76-84 |
| `employee_ids` | M2m `hr.employee` via `legal_task_employees_rel(task_id, employee_id)` | | | ✓ | | 85-92 |
| `session_date` | Date | | | ✓ | **one** value: each new hearing overwrites the last one | 94 |
| `due_date` | Date | | | ✓ | label leaks developer text "(DUE_DATE)" | 95 |
| `action_details` | Text | | | | plain text, no formatting | 96 |
| `expenses_amount` | **Float** | | | ✓ | label "(د.ع)" (Iraqi dinar); no currency field | 99 |
| `account_move_id` | M2o `account.move` | | | | readonly, `copy=False`; **no code ever writes it** | 100 |
| `account_payment_id` | M2o `account.payment` | | | | readonly, `copy=False`; **never written** | 101 |
| `expense_account_id` | M2o `account.account` | | | | editable; **never read by any code** | 102 |
| `is_urgent` | Boolean | | | ✓ | label "عاجل ومستعجل ⚠️" ("urgent", with emoji) | 104 |
| `is_overdue` | Boolean | | compute `_compute_overdue`, **store=False**, no `search` | | depends on `due_date`, `state`; uses `date.today()` | 105, 127-134 |
| `attachment_ids` | M2m `ir.attachment` via `legal_task_ir_attachment_rel(task_id, attachment_id)` | | | | a second store beside the chatter's attachments | 107-113 |
| *(inherited)* | `message_*`, `activity_*`, `message_follower_ids`, `website_message_ids`… | | | | from `mail.thread` and `mail.activity.mixin` | 9 |

#### `legal.company`: "شركة / مؤسسة قانونية موكلة" (client company or organisation)

`_inherit = ['mail.thread', 'mail.activity.mixin']`, `_order = 'name asc'`
(`legal_company.py:5-9`). It is **not linked to `res.partner`**, so it cannot be
invoiced, emailed or given portal access.

| Field | Type | Req | St/compute | Tr | Other | Line |
|---|---|---|---|---|---|---|
| `name` | Char | ✓ | | ✓ | `index=True` | 11 |
| `code` | Char | | | ✓ | `copy=False`, not unique | 12 |
| `company_type` | Selection | | | ✓ | `llc` LLC · `joint_stock` شركة مساهمة خاصة (private joint-stock) · `sole` مشروع فردي (sole proprietorship) · `foreign_branch` فرع شركة أجنبية (branch of a foreign company) · `partnership` شركة تضامنية (general partnership); default `llc` | 13-19 |
| `owner_name` | Char | | | ✓ | "managing director / main owner" | 21 |
| `entity_type` | Char | | | ✓ | the **label** means "nature of business activity"; the name is misleading | 22 |
| `registration_number` | Char | | | ✓ | companies-registry number | 23 |
| `tax_number` | Char | | | ✓ | | 24 |
| `phone` | Char | | | ✓ | no `phone` widget | 25 |
| `email` | Char | | | ✓ | no validation | 26 |
| `address` | Text | | | ✓ | | 27 |
| `notes` | Text | | | | | 28 |
| `active` | Boolean | | | | default `True` | 29 |
| `lawyer_id` | M2o `res.users` | | | ✓ | default = current user; **shown in no view** | 32-37 |
| `lawyer_ids` | M2m `res.users` via `legal_company_lawyers_rel(company_id, user_id)` | | | ✓ | default `[current user]` | 38-46 |
| `employee_ids` | M2m `hr.employee` via `legal_company_employees_rel(company_id, employee_id)` | | | ✓ | | 47-54 |
| `attachment_ids` | M2m `ir.attachment` via `legal_company_ir_attachment_rel(company_id, attachment_id)` | | | | | 57-63 |
| `document_count` | Integer | | compute, not stored | | counts the M2m only; **shown nowhere** | 64, 75-78 |
| `task_ids` | O2m `legal.task` | | | | | 66 |
| `task_count` | Integer | | compute, **store** (sudo) | | | 67 |
| `department_count` | Integer | | compute, **store** | | | 68 |
| `ministry_count` | Integer | | compute, **store** | | **shown nowhere** | 69 |
| `total_expenses` | **Float** | | compute, **store** | | label "(د.ع / $)", mixing two currencies | 70 |
| `pending_tasks_count` | Integer | | compute, **store** | | counts `draft` as pending | 71, 89-91 |
| `department_cards_html` | Html | | compute, not stored, **no `@api.depends`** | | HTML built in Python with f-strings | 73, 93-263 |

#### `legal.ministry`: "الوزارة / الهيئة العامة" (ministry or public authority)

`_order = 'sequence, name asc'` (`legal_ministry.py:5-8`). No chatter.

| Field | Type | Req | Notes | Line |
|---|---|---|---|---|
| `name` | Char | ✓ | `index`; uniqueness enforced in Python (`=ilike`) | 10, 27-38 |
| `code` | Char | | | 11 |
| `website` | Char | | `url` widget in the form | 12 |
| `phone` | Char | | | 13 |
| `address` | Text | | | 14 |
| `notes` | Text | | | 15 |
| `sequence` | Integer | | default 10 | 16 |
| `active` | Boolean | | default True | 17 |
| `department_ids` | O2m `legal.department` | | | 19-23 |
| `department_count` | Integer | | compute, not stored | 24, 40-43 |
| `task_count` | Integer | | compute, not stored; one `search_count` per record (N+1); counts through departments, **not** through `task.ministry_id` | 25, 45-49 |

#### `legal.department`: "الجهة / الدائرة الرسمية" (government body or directorate; also used for courts)

`_order = 'sequence, name asc'` (`legal_department.py:5-8`). No chatter. Only two
levels exist: a court under "مجلس القضاء الأعلى" (Supreme Judicial Council)
cannot sit under its appeal presidency.

| Field | Type | Req | Notes | Line |
|---|---|---|---|---|
| `name` | Char | ✓ | `index`; unique per ministry, enforced in Python | 10, 27-48 |
| `ministry_id` | M2o `legal.ministry` | | `ondelete='restrict'`, `index` | 11-16 |
| `code` | Char | | | 17 |
| `contact_person` | Char | | free text, not a contact record | 18 |
| `phone` | Char | | | 19 |
| `address` | Text | | | 20 |
| `notes` | Text | | | 21 |
| `sequence` | Integer | | | 22 |
| `active` | Boolean | | | 23 |
| `task_count` | Integer | | compute via `_read_group` (efficient) | 25, 50-58 |

#### Wizards (transient)

| Model | Fields | Line |
|---|---|---|
| `legal.task.create.wizard` | `legal_company_id` (M2o, req), `ministry_id` (M2o), `department_id` (M2o, **not** required although the matter requires it) | `legal_task_wizard.py:8-23` |
| `legal.company.report.wizard` | `company_id` (req), `show_company_info` (Bool, default True), `filter_lawyer_id`, `filter_department_id`, `filter_state` (a **hand-copied** duplicate of `legal.task.state`), `filter_task_ids` (M2m via `legal_report_wizard_task_rel`) | `legal_company_report_wizard.py:8-32` |
| `legal.general.report.wizard` | `company_ids` (M2m via `legal_general_report_company_rel`), `filter_lawyer_id`, `filter_ministry_id`, `filter_department_id`, `filter_state` (duplicate selection), `date_from`, `date_to`, `group_by_company` (**never read**), `filter_task_ids` (M2m via `legal_gen_report_wizard_task_rel`). Five fields carry an invalid `placeholder=` parameter | `legal_general_report_wizard.py:9-41` |

### 1.3 Methods, buttons and what they do

| Method | Exposed as | What it does | Guard |
|---|---|---|---|
| `legal.task.create` | ORM | draws `ir.sequence` code `legal.task`; falls back to the constant `CASE/<YYYY>/<MM>/001` | none (`legal_task.py:115-125`) |
| `_onchange_ministry_id` / `_onchange_department_id` | form onchange | clears the department when the ministry mismatches; fills the ministry from the department | UI only (`:40-48`) |
| `_compute_overdue` | computed field | `due_date < date.today()` and state not done or cancelled | — (`:127-134`) |
| `_cron_check_upcoming_sessions` | cron `ir_cron_legal_task_checker` (daily) | for open matters with a session in `[today, today+3]` **or** a due date before today, schedules a *To-Do* activity per assigned lawyer unless one already exists with deadline ≥ today | — (`:136-166`) |
| `unlink` | ORM | `UserError` unless the user is a legal manager or system admin | Python, duplicates the ACL (`:168-172`) |
| `action_print_task_report` | header button "طباعة استمارة القضية" (print the matter form) | returns `action_report_legal_task` | none (`:174-176`) |
| `action_request_approval` | button, visible when `approval_state == 'draft'` | sets `to_approve` and posts a message | **no state check, no group check** (`:178-180`) |
| `action_approve` | button, `groups=manager`, visible when `to_approve` | sets `approved` and writes the approver and date | **group enforced only by the view** (`:182-188`) |
| `action_reject` | button, `groups=manager` | sets `rejected` and writes the approver and date | same (`:190-196`) |
| `action_set_draft_approval` | **no button anywhere** | resets approval to `draft` | dead in the UI; callable over RPC (`:198-199`) |
| `action_set_in_progress` | button when `state == 'draft'` | `state = in_progress` | none (`:201-202`) |
| `action_set_pending_docs` | button when state in draft or in_progress | `state = pending_docs` | none (`:204-205`) |
| `action_set_done` | button when not done or cancelled | `state = done`, even from `draft` and even when not approved | none (`:207-208`) |
| `action_set_draft` | button when not draft | `state = draft`, even from `done` | none (`:210-211`) |
| `action_set_cancelled` | button when not done or cancelled | `state = cancelled` | none (`:213-214`) |
| `legal.company.unlink` | ORM | manager or admin only | Python (`legal_company.py:265-269`) |
| `action_view_tasks` (company) | two smart buttons ("القضايا والمعاملات" (matters) **and** "الدوائر الرسمية" (government bodies), both open matters) | matters of the client in kanban, list, form and calendar, grouped by ministry and then department | — (`:271-284`) |
| `action_create_new_task` (company) | header button, plus a second button inside the first notebook page | opens the intake wizard with the client preset | — (`:286-297`) |
| `action_print_company_report` | header button | opens the dossier-report wizard | — (`:299-311`) |
| `action_view_departments` / `action_view_tasks` (ministry) | two smart buttons | departments list; matters where the department belongs to this ministry | — (`legal_ministry.py:51-71`) |
| `action_view_tasks` (department) | smart button | matters of the department | — (`legal_department.py:60-72`) |
| `legal.task.create.wizard.action_proceed` | footer "متابعة وإضافة بيانات القضية ➡️" (continue to the matter details) | opens a **new full matter form** with the three values as defaults | — (`legal_task_wizard.py:35-52`) |
| `legal.company.report.wizard.action_print_report` | footer "🖨️ طباعة التقرير المخصص (PDF)" (print the custom report) | filters matters in Python and renders `action_report_legal_company` with `with_context(report_data=…)` | — (`legal_company_report_wizard.py:34-57`) |
| `legal.general.report.wizard.action_print_general_report` | footer "🖨️ طباعة تقرير الرقابة العامة (PDF)" (print the general oversight report) | builds a domain, searches matters and renders `action_report_legal_general_overview` against a **dummy** client record | — (`legal_general_report_wizard.py:48-93`) |

### 1.4 Views

| xmlid | Model | Type | Notable content |
|---|---|---|---|
| `view_legal_task_kanban` | legal.task | kanban | `default_group_by="department_id"`, `quick_create="false"`, class `o_kanban_dashboard`; card with heavy inline `!important` styles, emoji "🏛️", urgent, approval or state badge, department, client, session date, number and lawyer avatars (`legal_task_views.xml:4-88`) |
| `view_legal_task_tree` | legal.task | list | row decorations (danger: urgent and not done; warning: pending_docs or to_approve; success: done; muted: cancelled); 11 visible columns plus `is_urgent` hidden as optional; `sum` on expenses (`:91-124`) |
| `view_legal_task_calendar` | legal.task | calendar | `date_start = date_stop = session_date`, colour by client, month mode, no quick create (`:127-145`) |
| `view_legal_task_form` | legal.task | form | 9 header buttons plus statusbar; two groups ("🏛️ …", "📅 …") with 13 fields; notebook "📝 details", "📁 attachments", "💳 accounting" (3 fields); `<chatter/>`; **`task_number` is absent** (`:148-214`) |
| `view_legal_task_search` | legal.task | search | fields name, number, client, ministry, department, lawyers; filters "my matters", "to approve ⏳", "approved ✓", "urgent ⚠️", in progress, pending documents, done, overdue; group by client, ministry, department, approval, state (`:217-248`) |
| `view_legal_company_kanban` | legal.company | kanban | type badge, "N جارية" (N ongoing), name, registration no., matter count, bodies count, lawyers (`legal_company_views.xml:4-63`) |
| `view_legal_company_tree` | legal.company | list | 10 columns, `sum` on total expenses (`:66-83`) |
| `view_legal_company_form` | legal.company | form | header "➕ …" and "🖨️ …"; 2 smart buttons; 2 groups ("🏛️", "⚖️") with 10 fields; notebook of 4 pages: HTML "government windows", matter table, attachments, notes; `<chatter/>` (`:86-167`) |
| `view_legal_company_search` | legal.company | search | "my clients", three type filters, group by type (`:170-189`) |
| `view_legal_ministry_list` | legal.ministry | list | `editable="bottom"`, handle, counts, `active` toggle (`legal_department_views.xml:5-19`) |
| `view_legal_ministry_form` | legal.ministry | form | 2 smart buttons; notebook with an **editable departments list** and notes (`:22-73`) |
| `view_legal_ministry_search` | legal.ministry | search | name, code, active and inactive filters (`:76-87`) |
| `view_legal_department_list` | legal.department | list | `editable="bottom"`, ministry column, counts (`:107-122`) |
| `view_legal_department_form` | legal.department | form | 1 smart button, 2 groups, notes page (`:125-161`) |
| `view_legal_department_search` | legal.department | search | group by ministry (`:164-180`) |
| `view_legal_task_create_wizard_form` | wizard | form | info alert and 3 fields (`legal_task_wizard_views.xml:3-37`) |
| `view_legal_company_report_wizard_form` | wizard | form | 2 groups, task picker (`legal_company_report_wizard_views.xml:3-33`) |
| `view_legal_general_report_wizard_form` | wizard | form | 4 groups, 9 inputs (`legal_general_report_wizard_views.xml:3-42`) |

### 1.5 Actions

| xmlid | Type | Target | Notes |
|---|---|---|---|
| `action_legal_task` | act_window legal.task | list, kanban, form, calendar | the "all matters" register; also used as the URL of the HTML cards |
| `action_legal_task_to_approve` | act_window legal.task | list, kanban, form | domain `approval_state = to_approve` |
| `action_legal_company` | act_window legal.company | kanban, list, form | |
| `action_legal_ministry` | act_window legal.ministry | list, form | **no menu points to it** |
| `action_legal_department` | act_window legal.department | list, form | `search_default_group_by_ministry` |
| `action_legal_task_create_wizard` | act_window wizard | new (dialog) | |
| `action_legal_general_report_wizard` | act_window wizard | new | name carries "🖨️" |
| `action_legal_dashboard` | **ir.actions.client**, tag `legal_dashboard_tag` | main | |
| `action_report_legal_company` | report, qweb-pdf, model legal.company | binding: Print menu | paperformat compact |
| `action_report_legal_task` | report, qweb-pdf, model legal.task | binding: Print menu | paperformat compact |
| `action_report_legal_general_overview` | report, qweb-pdf, model legal.company | no binding | paperformat compact general |

### 1.6 Menus: tree, groups, and who actually sees what

```
الشؤون القانونية  (menu_legal_root, seq 20, NO groups)                  (legal affairs)
├── 📊 لوحة المتابعة والرقابة الذكية  (dashboard, client action)           visible to EVERY internal user (see S8)
├── ➕ بدء معاملة / قضية جديدة       (intake wizard)                       legal users (ACL filters it)
├── الشركات والموكلين              (clients)                              legal users
├── الدوائر والجهات الرسمية         (departments)   groups=manager         managers
└── ⚖️ الصلاحيات والموافقات          (folder)        groups=manager         managers
    ├── معاملات بانتظار الاعتماد ⏳   (to approve)
    ├── الرقابة العامة على كافة القضايا 📑  (all matters)
    └── 🖨️ طباعة تقرير الرقابة العامة الشامل  (general report wizard)
```

Six top-level items in the menu bar (screenshots 01–08 show the bar full), five of
them carrying emoji. A **lawyer has no menu to a list of their own matters**: the
only register action sits under the manager-only folder. Ministries have no menu.

### 1.7 Reports and paperformats

| xmlid | What | Notes |
|---|---|---|
| `paperformat_legal_compact_report` | A4, portrait, margins 12/12/10/10, dpi 90, `default=True` | `legal_company_report_templates.xml:4-18` |
| `paperformat_legal_compact_general_report` | identical copy, `default=True` | `legal_general_report_templates.xml:4-18` |
| `report_legal_company_document` / `report_legal_company_template` | client dossier: header with the active filters, optional client card, 3 counters, matter table (8 columns), signature blocks "المحامي المكلف" (assigned lawyer) and "مصادقة المدير القانوني العام" (endorsement of the general legal manager) | `web.basic_layout` (no letterhead), `dir="rtl"`, `t-lang="doc.lawyer_id.lang or 'ar_001'"` |
| `report_legal_task_document` / `report_legal_task_template` | **استمارة متابعة** (per-matter follow-up form): header, basic block, 3 date and money tiles, notes box, two signatures (lawyer; legal manager, or "القسم القانوني" (the legal section) when there is no approver) | same layout, direction and language choices |
| `report_legal_general_overview_document` / `…_template` | general oversight report: filter header, 4 counters, matter table (9 columns), signatures ("إعداد وقسم المتابعة القانونية" (prepared by legal follow-up) + current user; "مصادقة المدير القانوني العام / مدير النظام" (endorsement of the general legal manager / system administrator)) | issuer hard-coded "الإدارة القانونية العامة" (the general legal administration); no `t-lang` |
| `report/legal_reports.xml` | **dead file** (not in the manifest) that redefines `action_report_legal_company` (different name) and `action_report_legal_task` without paperformats | delete |

### 1.8 Scheduled job and sequence

| xmlid | Record | Content |
|---|---|---|
| `ir_cron_legal_task_checker` (`noupdate="1"`) | `ir.cron` | name "الشؤون القانونية: تدقيق مواعيد الجلسات والاستحقاقات" (legal affairs: check session and due dates); model legal.task; `state=code`; code **`model._cron_check_upcoming_sessions()`**; every 1 day; active; no `user_id`, so it runs as the installing user (OdooBot); `ir_cron.py:110` |
| `seq_legal_task` (`noupdate="1"`) | `ir.sequence` | code `legal.task`, prefix `CASE/%(year)s/%(month)s/`, padding 3, **`number_next` 5**, no date-range reset, no company |

### 1.9 Security

**Groups** (`security/legal_security.xml`)

| xmlid | Name | Implies | Privilege / category |
|---|---|---|---|
| `group_legal_user` | محامي / موظف قانوني (lawyer / legal staff) | `base.group_user` | **none** |
| `group_legal_manager` | المدير القانوني / مدير النظام (legal manager / system administrator) | `group_legal_user` | **none** |
| *(modifies)* `base.group_system` | — | **adds `group_legal_manager`** | — |

**Access rows** (`security/ir.model.access.csv`, 11 rows)

| Model | `group_legal_user` R W C D | `group_legal_manager` R W C D |
|---|---|---|
| legal.ministry | 1 1 1 0 | 1 1 1 1 |
| legal.department | 1 1 1 0 | 1 1 1 1 |
| legal.company | 1 1 1 0 | 1 1 1 1 |
| legal.task | 1 1 1 0 | 1 1 1 1 |
| legal.task.create.wizard | 1 1 1 1 | (inherits) |
| legal.company.report.wizard | 1 1 1 1 | (inherits) |
| legal.general.report.wizard | 1 1 1 1 | (inherits) |

Nobody outside the two groups has any access. No read-only role exists.

**Record rules** (group-bound, so they combine with OR for a user in both groups)

| xmlid | Model | Group | Domain |
|---|---|---|---|
| `legal_company_rule_lawyer` | legal.company | user | `lawyer_ids ∋ user` **or** `lawyer_id = user` |
| `legal_company_rule_manager` | legal.company | manager | all |
| `legal_task_rule_lawyer` | legal.task | user | `lawyer_ids ∋ user` or `lawyer_id = user` or `legal_company_id.lawyer_ids ∋ user` |
| `legal_task_rule_manager` | legal.task | manager | all |

There are no rules on ministries or departments. There is no `company_id`
anywhere, so no multi-company isolation.

### 1.10 The OWL dashboard (`static/src/dashboard/`)

- **Component** `LegalDashboard` (`legal_dashboard.js:7-272`), registered as client
  action `legal_dashboard_tag` (`:274`). Services: `orm`, `action`.
- **Loading:** `onWillStart` → `searchRead('legal.company', [], 7 fields)` for **all**
  clients, then `searchRead('legal.task', [], 12 fields)` for **all** matters, with no
  limit (`:43-73`). Errors are swallowed to `console.error` (`:80-81`).
- **Metrics** are computed in JavaScript by `applyCompanyFilter` (`:103-158`):
  - "ongoing" = draft, in progress and pending documents;
  - awaiting approval, urgent-and-open, and done;
  - total expenses: computed but **never rendered**;
  - the top 5 departments by count;
  - upcoming sessions: all future sessions, first 5;
  - "recent" = the first 8 by `id desc`.
  - "Today" comes from `new Date().toISOString()`, so it is **UTC** (`:116`).
- **Drill-downs:** `openTasksView`, `openPendingApprovals`, `openUrgentTasks`,
  `openDoneTasks`, `openCompaniesView`, `openGeneralReport`, `createNewTask`,
  `createNewCompany`, `openTaskRecord`, `openCompanyRecord` (`:167-271`). Each one
  carries the current client filter into its domain or defaults, which is a good
  pattern.
- **Template** (`legal_dashboard.xml`): hard-coded `dir="rtl"` (`:4`).
  - A hero header with title, subtitle and two buttons (`:6-22`).
  - A "filtered by client" banner (`:25-39`).
  - Five KPI cards; the **client filter `<select>` sits inside the first card**
    (`:54-80`).
  - The recent-matters panel (`:162-231`), the upcoming-sessions panel
    (`:236-268`) and the distribution by department (`:271-302`).
  - 50 lines of Arabic text and 14 lines with emoji (🎯 ⏳ 🔥 ✓ 🏢 ⚙️ 📝).
- **SCSS** (`legal_dashboard.scss`, 314 lines): hard-coded hex colours, many
  `!important`, and physical `border-right` (`:22`) and `translateX` (`:206`). A
  **global** block (`:283-312`) targets `.o_kanban_view .o_kanban_record:has(...)`
  in every kanban in the database, to force white cards.

### 1.11 Screens as rendered (baseline, Arabic, 1440 px)

| Screen | What the screenshot shows | Clutter measures |
|---|---|---|
| 01 Dashboard | hero header, 5 KPI cards (client filter inside card 1), recent matters (5), upcoming sessions (2); **the header's accent bar renders on the left** (rtlcss flip, see R1); the "مسودة" (draft) badge is almost invisible (low contrast) | title repeated 3 times (menu, h2, subtitle); no overdue figure anywhere |
| 02 Clients kanban | 2 cards: type badge, "2 جارية" (2 ongoing), matters and bodies badges, lawyer avatar **overflowing the card edge** | sparse; fine |
| 03 Client form | 2 header buttons, 2 smart buttons (both open matters), 10 fields in 2 groups, 4 tabs; the "government windows" tab shows ministry cards with collapsible department lists and "▼ طي / فتح" ("fold / open") badges | an in-tab "add" button duplicates the header one; the windows tab and the table tab show the same matters twice |
| 04 Matters list | 11 columns; number, lawyer and client all truncated ("…ell Admin", ".../2026/09/009"); whole rows tinted red or green; "مسودة" appears in **two** columns (approval draft and work draft); amounts with no currency; Arabic-Indic digits in dates, Latin digits in numbers | too wide for 1440 px |
| 05 Matter form | **7 header buttons in two rows** (print, approve, reject, request documents, done, reset to draft, cancel) in six colours; the statusbar is squeezed to a single stage; `is_overdue` shows as a greyed checkbox; no matter number on the form | 13 fields, 3 tabs, one of which (accounting) is always empty |
| 06 Intake wizard | info alert and 3 fields; the "continue ➡️" arrow points the wrong way for right-to-left reading | step 1 of 2; step 2 repeats the same fields |
| 07 Departments | list grouped by ministry and **collapsed**, so the user sees 3 group lines and nothing else | — |
| 08 General report wizard | 9 inputs in 4 groups, including a "group by client" toggle that does nothing | — |

---

## 2. Defects

Each row gives an ID, where the defect is, its severity and the fix. IDs are
referenced from §4 and §5.

### 2.1 Security

| ID | Where | Sev | Defect | Fix |
|---|---|---|---|---|
| **S1** | `legal_task.py:178-199`; fields `:59-67` | **High** | **Approvals can be self-granted or forged.** `action_approve` and `action_reject` check no group, since the manager restriction is only `groups=` on the view button. Odoo 19's `call_button` runs any public method without checking it against the view (`web/controllers/dataset.py:35-41`). The approval fields are also plain writable fields: any assigned lawyer can `write({'approval_state': 'approved', 'approver_id': <manager id>})` and so **forge the manager's name** on the record and on the printed form. No state guard applies either (approving something never requested works), and nothing stops a manager approving their own request. | Server-side checks in each transition (a dedicated approver group, `AccessError` otherwise). Approval fields set only by the transition methods: block direct writes in `write()` for non-approvers, or keep them in a separate `legal.approval` log (who, when, decision, comment). Configurable separation of duties (requester ≠ approver). A transition table. |
| **S2** | `legal_task.py:70-75`, `legal_company.py:32-37`, rules `legal_security.xml:24,39` | **High** | **A hidden grant of access.** `lawyer_id` defaults to the creator, appears in **no view**, and the record rules grant read and write through it. Taking a lawyer off `lawyer_ids` does not revoke their access if they created the record, and nobody can see why they still have it. | Make it visible as *Responsible* (المسؤول) and editable by managers. Or remove it from the rules. Migration in §4.8 (M3). |
| **S3** | `legal_security.xml:15-18` | **High** | **Every Settings administrator is a legal manager**, and the link cannot be removed per user. IT staff can read and delete every legal file. A law office cannot accept this, because files are covered by professional secrecy. Removing the XML lines later does **not** undo the link: it must be unlinked explicitly. | Remove the implication with an explicit `(3, ref('group_legal_manager'))` or in a migration. Grant the manager role explicitly to the people who hold it (SAG to confirm who). |
| **S4** | `legal_security.xml:4-13` | **High** (admin usability) | **The groups have no `privilege_id`.** In Odoo 19 the user form shows groups without a privilege only in **debug mode**, under "Extra Rights" (`web/static/src/webclient/res_user_group_ids_field/res_user_group_ids_field.js:40-45, 100`). SAG admins cannot give a lawyer access without developer mode. | Define a `res.groups.privilege` under an `ir.module.category` with sequence and comments, as `legal_core/security/legal_core_security.xml` already does in this repository. |
| **S5** | `legal_task.py:14-20` | Medium | **Deleting a client deletes its matters at SQL level** (`ondelete='cascade'`). This bypasses `LegalTask.unlink`, and the matters' `mail.message`, `mail.activity` and `mail.followers` rows are left pointing at deleted records (activities then fail when clicked). One manager click wipes a client's whole history. | `ondelete='restrict'`; archive clients instead of deleting them; add `active` to matters. |
| **S6** | `ir.model.access.csv:2,4`; quick-create options `legal_task_views.xml:174-175`, `legal_task_wizard_views.xml:20-26` | Medium | Lawyers can create and edit ministries and departments: the ACL gives 1,1,1,0 and the pickers allow inline creation. Yet the directory's menu is manager-only. Master data gets duplicated and misspelt; the Python name check only catches exact duplicates. | Read-only for users; configuration for managers. Optionally a "request a new body" flow, or quick-create allowed only when a setting permits it. |
| **S7** | `legal_company.py:67-71`; kanban and list | Medium | **Stored totals leak matters hidden from the viewer.** Stored computes run as superuser, so a lawyer sees the client's total matter count, pending count and **total expenses**, including matters the record rule hides from them. | Non-stored `_read_group` computed under the viewer's rules, or hide these figures from non-managers. |
| **S8** | `legal_menus.xml:4-14`; `ir_ui_menu.py:95-128` | Medium | **The Legal app appears for every internal user.** The root menu has no groups, and Odoo 19 never filters `ir.actions.client` menus by access rights. POS and warehouse users on SAG's ERP see "الشؤون القانونية" (legal affairs); the dashboard then loads empty with swallowed access errors. | `groups=` on the root menu (the legal user group). |
| **S9** | `legal_security.xml:24,39` | Low | Incoherent rule scopes. The matter rule honours the client's `lawyer_ids` but not the client's `lawyer_id`, and the client rule does not grant "clients of my matters". A lawyer assigned to a matter cannot open its client. | One coherent rule set, e.g. clients where I am assigned **or** I have a matter. |
| **S10** | `legal_task.py:168-172`, `legal_company.py:265-269` | Low | The delete guards in `unlink` duplicate the ACL (users already have `perm_unlink = 0`), raise an untranslated `UserError`, and are bypassed by the SQL cascade (S5). | Rely on the ACL. Use `@api.ondelete(at_uninstall=False)` for business rules (e.g. "only draft matters can be deleted"). |
| **S11** | `ir.model.access.csv:10-12` | Info | Wizard access rows grant unlink. Harmless on transient models. | — |
| **S12** | `legal_company_views.xml:119-120` | Low | On the client form, `lawyer_ids` and `employee_ids` lack `no_create`: an admin typing a name can create a `res.users` or `hr.employee` by accident. | `options="{'no_create': True}"`. |
| **S13** | `legal_company.py:171-194` | Low | User text (matter names, client and body names) is pasted into HTML without escaping. The `Html` field sanitises on assignment (`odoo/orm/fields_textual.py:614-690`), so scripts and `on*` handlers are removed and this is **not** exploitable XSS. Markup injection (links, a broken layout) is still possible. | Replace with an OWL component (see O2). |
| **S14** | all models | Medium | **No `company_id` on any model.** In a multi-company database all legal data is shared across companies. | `company_id` with default `env.company`, plus global multi-company rules; the migration sets the main company. |
| **S15** | whole module | Medium | **No read-only role** (auditor or oversight) and no role finer than "lawyer". A manager's oversight requires full write power. | Roles: clerk, lawyer/officer, approver, manager and **read-only auditor**, as in `legal_core`, plus an office-mode partner role. |

### 2.2 Correctness

| ID | Where | Sev | Defect | Fix |
|---|---|---|---|---|
| **C1** | `legal_task.py:151-166` | **High** | **The reminder job duplicates overdue reminders every day.** The duplicate check only looks for an activity with `date_deadline >= today`. Overdue reminders are scheduled at `due_date` (or a past `session_date`), which is before today, so each run adds **one more activity per assigned lawyer per overdue matter**. Conversely, any unrelated future activity for that user on that matter (e.g. "call client") suppresses the reminder altogether. | Keep one reminder per (matter, date kind, user), identified by an activity type or key. Reschedule it rather than adding a new one. Schedule overdue reminders for today. The migration removes existing duplicates (M9). |
| **C2** | `legal_task.py:141-146` | Medium | **No advance warning for due dates**: they are flagged only after they pass. The prototype promised "3 days before the due or session date". A due date here often means a licence or registration expiry ("تاريخ الاستحقاق / انتهاء الصلاحية" (due / expiry date) in the prototype), where the warning has to come *before* the date. | Configurable lead times for each kind of date (session, due, expiry); a proper deadlines model. |
| **C3** | `legal_task.py:149, 158`; `ir_cron.py:110` | Medium | `is_court` treats **past** sessions as upcoming court sessions. Matters with no lawyer send the reminder to the cron user (OdooBot), so nobody sees it. | Separate the upcoming and overdue branches; fall back to the responsible person or the manager. |
| **C4** | `legal_task.py:129,139`; `legal_dashboard.js:116`; reports `legal_company_report_templates.xml:62`, `legal_task_report_templates.xml:32`, `legal_general_report_templates.xml:54` | Medium | **Timezone.** `date.today()` and `datetime.date.today()` give the **UTC** date (Odoo runs with the process timezone set to UTC), and the dashboard uses the UTC ISO date. Between 00:00 and 03:00 Baghdad time, "today" is yesterday: overdue flags, the 3-day window and printed issue dates are off by one. | `fields.Date.context_today(self)` with the user's or company's timezone; in the cron use the company timezone (Asia/Baghdad); in JS use luxon's local date. |
| **C5** | `legal_task.py:105,127-134`; search `legal_task_views.xml:238` | Medium | `is_overdue` is not stored and has no search method, so it cannot be filtered, grouped or sorted. The search filter re-implements the logic with its own domain (two versions of the truth). The dashboard shows **no** overdue figure. | A `search=` method (or a stored flag refreshed by the daily job); an overdue KPI first on the dashboard. |
| **C6** | `legal_task.py:198-214`; `legal_task_views.xml:155-166, 188-189` | Medium | **The approval axis dead-ends.** A rejection is terminal in the UI, because `action_set_draft_approval` has no button. Approval gates nothing (a matter can be *done* without ever being approved). Approver and date are written on rejection but displayed only when approved. The `action_set_*` methods check nothing: done → draft, draft → done and cancelled → pending are all allowed. | An explicit transition table: which transitions exist, who may take them, and whether approval is required per matter type. "Resubmit after rejection". Show who decided and when for both outcomes. |
| **C7** | wizard `legal_company_report_wizard.py:39-52`; template `legal_company_report_templates.xml:40-46` | Medium | **The dossier report prints every matter when the filters match none.** The wizard passes `task_ids: []`; the template treats the empty list as "no filter" and renders `doc.task_ids`, while the header still announces the filter (e.g. "الحالة: ملغى", status: cancelled). | Pass an explicit "filtered" flag, or better, `report_action(docs, data=…)` with a `report.<template>` AbstractModel computing the rows. |
| **C8** | `legal_general_report_wizard.py:64-71` | Low | The date range is evaluated as (due ≥ from **or** session ≥ from) **and** (due ≤ to **or** session ≤ to), so a matter due before the range with a session after it is included. | `(due in range) OR (session in range)`. |
| **C9** | `legal_general_report_wizard.py:32,85`; view `:15` | Low | The "group by client" toggle (on by default) is **never read** by the template. | Implement it or remove it. |
| **C10** | `legal_company_report_wizard.py:57`, `legal_general_report_wizard.py:93`; templates `:38`, `:35-38` | Low | **Report parameters travel in the context.** This works in Odoo 19 only because the web client merges `action.context` into the download context (`action_service.js:1367-1372` → `web/controllers/report.py:118-120`). Any server-side render (mail attachment, scheduled send) and the HTML preview path (`action_service.js:1327`, which uses the user context) lose the filters: the general report then prints **empty**. The filter header also compares against Arabic sentinel strings (`legal_general_report_templates.xml:48-50`), which breaks as soon as the strings are translated. | The idiomatic `data=` plus `_get_report_values`. |
| **C11** | `legal_task.py:23-48`; `legal_ministry.py:45-49`; `legal_company.py:84-87, 108` | Medium | **`ministry_id` is a denormalised copy of `department_id.ministry_id`**, kept aligned only by onchange. Imports, RPC and kanban drags (C12) can diverge it. The ministry's matter count goes through departments, while the client cards, the dashboard and the reports use `task.ministry_id`: two sources of truth. | A stored field computed from the department (read-only), with the ministry used only as a filter on the department picker. The migration repairs mismatches (M4). |
| **C12** | `legal_task_views.xml:8` | Medium | The matters kanban is **grouped by department and draggable**: dragging a card silently moves the matter to another government body, and the ministry stays stale because onchanges do not fire on drag. | Group by stage; `records_draggable="0"` for any many2one grouping. |
| **C13** | `legal_task.py:118-124`; `legal_department_data.xml:4-13` | Low | If the sequence is missing, every matter gets the constant `CASE/<Y>/<M>/001` (duplicates, and no unique constraint exists). The prefix contains the month but the counter never resets, so the prefix misleads ("CASE/2026/10/010"). The counter starts at 5 (seeded). | Raise if there is no sequence; a unique index on `(company_id, task_number)`; a yearly date range; a configurable format per mode. |
| **C14** | `legal_task.py:99`; `legal_company.py:70`; reports `…company…:106,142,157`, `…general…:82,120,135`, `…task…:81` | Medium | **Money is a `Float`** with a hard-coded "د.ع" (Iraqi dinar) suffix and one label saying "(د.ع / $)" (dinar or dollar). There is no currency, rounding or proper formatting. The reports mix `t-field` output ("500,000.00") with raw `t-esc sum(...)` output ("1200000.0") in the same table. | `Monetary` with `currency_id` (company currency, IQD at SAG), expense lines, and `t-options` monetary formatting. |
| **C15** | `legal_task.py:100-102`; `legal_task_views.xml:200-208` | Low | `account_move_id` and `account_payment_id` are read-only and **no code writes them**; `expense_account_id` is chosen but never used. The whole "💳 accounting link" tab is decoration. | Implement "record expense → vendor bill / payment" from expense lines, or hide until it exists. |
| **C16** | `legal_ministry.py:27-38`; `legal_department.py:27-48` | Low | Name uniqueness uses `=ilike` (so `%` and `_` act as wildcards), respects `active_test` (an archived duplicate goes undetected), and the stored name is not trimmed. | `models.UniqueIndex` on `lower(trim(name))` (per ministry for departments); trim on write. |
| **C17** | `legal_task_wizard.py:19-23` vs `legal_task.py:31-37` | Low | The wizard lets the user continue without a department, which the matter then requires. | A one-step quick-create (U4). |
| **C18** | `legal_task.py:107-113`, `legal_company.py:57-64,75-78` | Low | **Two attachment stores**: the many2many `attachment_ids` and the chatter's attachments. `document_count` counts only the first. | One documents list (chatter attachments plus typed documents). The migration links the many2many files to their record (M6). |
| **C19** | `legal_general_report_wizard.py:88-93` | Low | When no client exists, the general report is rendered with a `res.company` record as `legal.company` document ids. | A data-only report. |
| **C20** | `legal_task.py:94` | Medium | **One `session_date` per matter**: each new hearing overwrites the previous one, so the hearing history survives only as chatter tracking lines. This applies equally to follow-up visits to a government counter ("المراجعة القادمة", the next follow-up visit, in the prototype). | A sessions and visits model (date, body, purpose, outcome, next date); `session_date` becomes "next session", computed and stored. Migration M5. |
| **C21** | `…company…:186`, `…task…:116` | Low | The reports render in the language of the **hidden** `lawyer_id`, not the reader's. The general report has no `t-lang`. | The printing user's language (or a chosen one). |
| **C22** | `legal_company_views.xml:100-102` | Low | The "الدوائر الرسمية" (government bodies) smart button opens the **matters**, not the bodies. | Open the bodies, or remove the button. |
| **C23** | `legal_company.py:89-91`; `legal_dashboard.js:120` | Low | "Pending" and "ongoing" include `draft`. | Define the counters explicitly (open = not done or cancelled; draft counted separately). |

### 2.3 Performance

| ID | Where | Sev | Defect | Fix |
|---|---|---|---|---|
| **P1** | `legal_dashboard.js:43-73,103-158` | Medium | The dashboard downloads **every client and every matter** (plus the many2many lawyer ids) and aggregates them in the browser. That is fine at SAG's 11 matters and unusable for a firm with tens of thousands. | One RPC to a server method using `_read_group` for counters, plus short, limited lists. |
| **P2** | `legal_company.py:93-263` | Medium | `department_cards_html` builds a large inline-styled HTML string in Python on **every** read of the client form (no depends, no cache), iterating all the client's matters. | An OWL widget fed by `_read_group` and a limited list per body. |
| **P3** | `legal_ministry.py:45-49` | Low | One `search_count` per ministry (N+1) in the list and the form. | `_read_group`, as `legal.department` already does. |
| **P4** | `legal_company.py:80-91` | Low | The stored client statistics re-read all the client's matters on every matter write (state or expense change). | Non-stored `_read_group`, or targeted recompute. |
| **P5** | `legal_dashboard.scss:283-312` | Low | A global selector on **every** kanban in the ERP (`.o_kanban_view .o_kanban_record:has(...)`) with `!important`. `:has()` is evaluated on all kanban cards. | Scope everything under a module class; no `!important`. |
| **P6** | `legal_task.py:21,29,38` | Low | Three stored related name copies that nothing reads still cost writes whenever a client, ministry or department is renamed. | Drop them (M7). |

### 2.4 Odoo 19 idioms

| ID | Where | Sev | Defect | Fix |
|---|---|---|---|---|
| **O1** | `legal_general_report_wizard.py:15,18,19,20,40` | Low | `placeholder=` used as a Python field parameter: **10 warnings** in the baseline install log (`baseline_install.log:949-953, 990-994`). | Put placeholders in the view. |
| **O2** | `legal_company.py:173, 176-177` | Medium | An inline `onclick` using `window.odoo.__WOWL_DEBUG__` (a debug-only global) and `onmouseover` handlers. The Html sanitiser strips all of them, so the code is dead. Navigation still works only because Odoo 19's router intercepts `/odoo/...` links (`web/static/src/core/browser/router.js:309-336`), which **replaces the breadcrumb**: the path from the client back to the matter is lost. | An OWL field widget that calls `action.doAction` with proper breadcrumbs. |
| **O3** | `report/legal_reports.xml` | Low | A dead file (not in the manifest) that redefines two report xmlids with different names. | Delete it. |
| **O4** | `…company…:6`, `…general…:6` | Info | `default=True` on two paper formats. The flag is only a label in core (`report_paperformat.py:170`), but two "defaults" mislead. The two formats are also identical. | One paper format, no flag. |
| **O5** | `legal_task_views.xml:8,24-25`; `legal_company_views.xml:8,20` | Low | Kanban `class="o_kanban_dashboard"` (meant for dashboard kanbans), `oe_kanban_global_click` (unnecessary in `card` templates), and dozens of inline `style="… !important"` in the arch. | Plain card templates plus module SCSS using Odoo variables. |
| **O6** | several | Low | `super(LegalTask, self)`, `datetime.now()` for a Datetime field, `_("…%s") % x` instead of `_("…%s", x)`, `/** @odoo-module **/` headers (unnecessary since 17), Python-side uniqueness instead of `models.Constraint` / `UniqueIndex`. | Modern idioms. |
| **O7** | `legal_task.py:95` | Low | The label "تاريخ الاستحقاق (DUE_DATE)" shows developer text in filters, exports and group-by. | Clean the label. |
| **O8** | `__manifest__.py:20` | Medium | `hr` and `account` are **hard dependencies** only for `employee_ids` and three unused accounting fields, which forces the Employees and Invoicing apps on any database. SAG has both, so compatibility holds; a law office or small department would not want them. | Keep them for the first upgrade (dropping `hr` removes `employee_ids`). Then move to auto-install bridges (`…_hr`, `…_account`) once real accounting exists. |
| **O9** | module | Medium | **No tests.** | Unit tests (rules, transitions, cron, reports), tour tests, and an upgrade test from a copy of the baseline database. |
| **O10** | `static/src/dashboard/*` | Low | The client action loads its data in `onWillStart` with no `useService("orm")` batching, no `rpc` cancel, no refresh after returning from a record other than a remount. | A standard client action with a model and `useBus` refresh. |

### 2.5 Translation (i18n)

| ID | Where | Sev | Defect | Fix |
|---|---|---|---|---|
| **I1** | 27 files, **578 lines** of Arabic source; no `i18n/` | **High** | Every source string is Arabic. Odoo treats the source as `en_US` and returns it untranslated for English (`odoo/tools/translate.py:419-420`), so **English is impossible** for Python strings (`UserError`s, chatter posts, default names, report sentinels). Every label, menu, selection value and view shows Arabic to English users. There is no `ar.po` either, so the Arabic cannot be corrected without code changes. | English source everywhere plus a complete `i18n/ar.po` (`ar_001`), checked for coverage, and an upgrade step that makes SAG's Arabic UI survive the source switch (M10). |
| **I2** | `legal_dashboard.js:30,95,98,171-246`; `legal_dashboard.xml:4`; reports `dir="rtl"` | Medium | JS strings not wrapped in `_t`; `dir="rtl"` hard-coded in the dashboard and all three reports. | `_t`, direction from the user's language, `web.external_layout` handling direction. |
| **I3** | 66 lines | Medium | **Emoji as labels**: 5 menus, 3 selection labels, 1 field label, 7 buttons, 7 page and group titles, 3 filters, the kanban, the HTML cards, the dashboard and the reports. They do not translate, screen readers read them aloud, and they break the rhythm of Arabic lines. | Remove them all; use `fa`/`oi` icons with `title` where an icon adds meaning. |
| **I4** | `legal_general_report_templates.xml:55, 143-154`; `…company…:164-178`; `…task…:93-108` | Low | The issuer "الإدارة القانونية العامة" (the general legal administration) and the signature titles are hard-coded in department wording, which is wrong for a law office. | Mode-dependent labels plus company letterhead. |
| **I5** | screenshot 04 | Low | Mixed digit systems: Arabic-Indic digits in dates, Latin digits in numbers and amounts. | One consistent digit setting per language. |
| **I6** | `legal_ministry.py:38`; `legal_department.py:43-48`; `legal_task.py:171, 180-196`; `legal_company.py:268` | Low | `_("…") % x` formatting and bare `UserError("…")` strings: the first formats outside the translation call, the second is untranslatable. | `_("… %s", x)` / `self.env._()`. |

### 2.6 Accessibility

| ID | Where | Sev | Defect | Fix |
|---|---|---|---|---|
| **A1** | `legal_dashboard.xml:61,84,103,122,141,187,256` | Medium | Clickable `div`s (KPI cards, rows) with no `role="button"`, no `tabindex` and no key handler: the dashboard cannot be used from the keyboard. The icon-only client button has only a `title`. | `<button>` or `<a>` elements; visible focus; `aria-label`. |
| **A2** | `legal_dashboard.xml:68-77` | Low | The `<label>` is not tied to the `<select>`, so the select has no accessible name. | `for`/`id`, or a proper filter component. |
| **A3** | `legal_task_views.xml:95-99`; screenshot 01 | Low | Status shown by colour alone (entire rows tinted red or green); the washed-out draft badge; 0.7 rem badge text. | Badges with text; row decoration only for exceptions (overdue); WCAG AA contrast. |
| **A4** | `legal_company.py:201`; SCSS `:159-165` | Low | `outline: none` on the `<summary>` (and on the select's focus) removes or weakens the focus indicator. | Keep a visible focus style. |
| **A5** | `legal_dashboard.xml:296-298` | Low | Progress bars without an accessible name. | `aria-label` ("department X: N matters, P%"). |
| **A6** | `legal_task_views.xml:190`; screenshot 05 | Low | `is_overdue` shown as a disabled checkbox labelled "متأخر" (overdue). | A status badge in the title area. |

### 2.7 Right-to-left layout

| ID | Where | Sev | Defect | Fix |
|---|---|---|---|---|
| **R1** | `legal_dashboard.scss:22`; inline styles `legal_task_views.xml:25`, `legal_company_views.xml:20`, `legal_company.py:215`, `legal_dashboard.xml:257` | Medium | Odoo 19 flips module CSS through rtlcss for right-to-left users (`odoo/addons/base/models/assetsbundle.py:573-592`). The SCSS `border-right` on the hero header therefore renders **on the left in Arabic** (screenshot 01), while the inline `border-right` on kanban cards, HTML cards and session rows is not flipped and renders on the right. In English all of them sit on the wrong side. | No inline styles. Logical properties (`border-inline-start`), which rtlcss leaves alone and browsers resolve by direction. |
| **R2** | `legal_dashboard.xml:4`; three report templates | Medium | Hard-coded `dir="rtl"`: the English layout is broken. | Direction from the language. |
| **R3** | `legal_company.py:178`; `…company…:135`; `legal_dashboard.scss:206`; `legal_task_wizard_views.xml:30` | Low | `text-align: right`, `margin-left`, a `translateX(-3px)` hover, and the "➡️" arrow on "continue", which points **backwards** for Arabic readers. | Logical alignment; direction-aware chevron icons (`oi-chevron-left/right` swap). |

### 2.8 Clutter and usability

| ID | Where | Sev | Defect | Fix |
|---|---|---|---|---|
| **U1** | `legal_task_views.xml:153-166`; screenshot 05 | **High** | **The matter header**: 9 buttons defined, **up to 7 visible at once in two rows**, in six colours (outline-primary, success, danger, warning, success, secondary, outline-danger). The statusbar is squeezed to one visible stage. | One primary next step; everything else in a "⋯" menu or a clickable statusbar limited to allowed transitions; approval shown as a banner ("Awaiting approval by…" with Approve and Reject for the approver only). |
| **U2** | `legal_menus.xml:37-59` | **High** | **Lawyers have no "my matters" list**: the register is only reachable through the manager-only folder, the dashboard, or a client's smart button. | A top-level "Matters" entry defaulting to *My matters*; approvals as a queue for approvers only. |
| **U3** | `legal_task_views.xml:148-213`; `_rec_name` | Medium | The **matter number is not shown on its own form** and is not part of its display name, so pickers (such as the report wizard's matter picker) are ambiguous. | Show it in the title area; `display_name` = "CASE/… · title". |
| **U4** | `legal_task_wizard.py:35-52`; screenshot 06 | Medium | **Two-step intake**: a dialog asks for client, ministry and department, then opens the full form, which asks for them again. That takes more clicks than creating the matter directly. | A single OWL quick-create (client, matter type, body, title, responsible) with smart defaults and "more fields"; the full form stays one click away. |
| **U5** | `legal_company_views.xml:91-162`; screenshot 03 | Medium | **Client form**: 2 header buttons, 2 smart buttons (both open matters), a duplicate in-tab "add" button, 4 tabs; the windows tab and the matter-table tab show the same matters twice. | One "matters by body" OWL panel (the valued idea, see §3) plus a stat button; advanced registry data behind "more". |
| **U6** | `legal_task_views.xml:91-124`; screenshot 04 | Medium | **Matters list**: 11 default columns, truncated values, entire rows tinted, and two "مسودة" (draft) badges from two different state fields. | About 6 default columns (number, title, client, body, next date, stage); the rest optional; one status badge; overdue as the only row decoration. |
| **U7** | `legal_dashboard.xml`; screenshot 01 | Medium | **Dashboard**: no overdue KPI and no "today / this week" view; the client filter is hidden inside KPI card 1; expenses are computed but not shown; "recent = last 8 created" rather than "what needs me"; the title is repeated. | An attention-first home: overdue, due this week, sessions this week, awaiting my approval, and my open matters, with a client filter in the control panel. |
| **U8** | `legal_menus.xml`; `legal_department_views.xml:90-103` | Low | Configuration (government bodies) sits in the main menu bar; ministries have no menu; six long, emoji-decorated top items fill the bar. | Top level: Home, Matters, Clients, Calendar, Reporting, Configuration (bodies, types, settings). |
| **U9** | `legal_department_views.xml:188`; screenshot 07 | Low | The departments list opens grouped **and collapsed**, showing 3 lines. | A flat list with a ministry column, or expanded groups. |
| **U10** | `legal_task_views.xml:200-208` | Low | An "accounting" tab with three fields that are always empty. | Hide it until implemented (C15). |
| **U11** | screenshot 08 | Low | The general report wizard has 9 inputs in 4 groups, one of them dead (C9). | Reuse the list view's search (filters, then Print), or a short dialog. |
| **U12** | all views | Low | Long labels: "تحديد قضايا ومعاملات معينة بالاسم (اختياري)" ("select specific matters by name (optional)"), "المصروفات والمبالغ المدفوعة (د.ع)" ("expenses and amounts paid (IQD)"), and so on. | Short labels with the explanation in `help`. |
| **U13** | screenshot 02 | Low | The lawyer avatar overflows the client card edge. | Standard kanban footer. |
| **U14** | SCSS and inline styles | Low | Hard-coded white and hex colours with `!important` everywhere: Odoo 19's dark mode shows white cards on a dark UI. | Odoo SCSS variables and CSS custom properties. |

---

## 3. What is good and must be kept

These are the ideas and behaviours SAG's users rely on today. The rebuild must
keep **the behaviour**, not the code.

1. **Starting a matter is a first-class action.** It is a top-level menu item
   ("بدء معاملة / قضية جديدة", start a new transaction or case), a button on the
   dashboard and a button on the client form, and the client is preset when
   started from a client. Keep all three entry points and make them one
   quick-create step.
2. **Choosing the government body in two steps.** Picking a ministry narrows the
   departments; picking a department fills its ministry. This is the natural way
   an Iraqi user thinks: "the Ministry of Finance, the General Commission for
   Taxes, the large-taxpayers branch". Keep it, with typing-ahead search across
   both levels.
3. **A client dossier that shows every government "window" the client has
   matters with**: per ministry, then per department, with pending and done
   counts, lawyers, and one click into each matter (the "نوافذ الوزارات والدوائر"
   tab, "ministry and department windows"). Users value this map; only the HTML
   mechanism is wrong. Keep it as an OWL component on the client form.
4. **The client's legal record data** for Iraqi companies: registration number,
   tax number, managing director or owner, business activity, and legal form.
   The legal-form values match the forms of Iraq's Companies Law No. 21 of 1997,
   which allows private companies as LLC, joint stock, general partnership,
   individual enterprise or simple company, with mixed (public/private)
   companies limited to LLC or joint stock
   ([Al Tamimi & Co.](https://www.tamimi.com/law-update-articles/companies-and-their-administration-in-iraq/);
   [law text, as amended 2004](https://baghdad.eregulations.org/media/company%20law%2021%20as%20amended%20in%202004.pdf)).
   Keep the five values and add the missing forms ("simple company", mixed, and
   an individual person for law-office clients).
5. **An approval step for the legal manager, separate from the work state**,
   with its own queue ("معاملات بانتظار الاعتماد", transactions awaiting approval)
   and a dashboard counter. Keep the concept: a manager signs off before a file
   leaves. Make it enforceable and configurable (S1, C6).
6. **"بانتظار الوثائق وصحة الصدور"** ("waiting for documents and verification of
   issuance") as its own stage. "صحة صدور" is the Iraqi practice of confirming
   with the issuing office that an official document is genuine. It is a real,
   frequent waiting state in government work. Keep it as a stage (and later as
   a tracked request in its own right).
7. **Matter numbers `CASE/YYYY/MM/NNN`** on screen and on every print. Existing
   numbers must never change; the format may become configurable for new
   matters.
8. **Lawyers see only their clients and matters; the manager sees everything.**
   Keep the principle and fix its leaks (S2, S7, S9).
9. **Assigning several lawyers, and a staff team, to both the client and the
   matter.** Keep it (as responsible plus team).
10. **The urgent flag, the "overdue" and "my matters" filters, and the calendar
    of sessions.** Keep them all; make overdue a real field (C5).
11. **Daily reminders as Odoo activities for the assigned lawyers ahead of
    sessions.** Users see them in their activity menu. Keep the mechanism; fix
    its logic (C1-C4) and make lead times configurable.
12. **The three prints**: the client dossier with a filter dialog (by lawyer,
    body, state, chosen matters, with or without the client card); the
    **per-matter follow-up form** (استمارة متابعة) with signature and stamp
    blocks, which a runner carries to the government office; and the general
    oversight report across all clients. Keep all three, rebuilt on a letterhead
    layout with correct filters and money.
13. **Expenses recorded per matter and totalled per client**, with the
    *intention* of posting them to Accounting (move, payment and expense account
    on the matter). Keep the intention and implement it properly.
14. **Chatter, activities and field tracking** on matters and clients; the
    history of who changed what matters in legal work. Keep them.
15. **Delete restricted to managers.** Keep it, via access rights plus
    archiving (S5, S10).
16. **Dashboard drill-downs that carry the current client filter** into the
    opened list and into "new matter" and "print report". It is a good
    interaction pattern; keep it in the new home screen.
17. **Directory editing**: a ministry's departments are editable in place on the
    ministry form, with handles to reorder and archive toggles, and duplicate
    names are refused. It is fast data entry; keep it for managers.
18. **One app, few menus.** Nine menu items against the suite's seventy-four
    (`docs/external-review/sag-legal-module.md` §2). The small surface is a
    virtue to preserve while scope grows, through progressive disclosure rather
    than more menus.

Two observations for the configuration switch:

- **The showcase already straddles both modes, with mixed vocabulary.** The
  client model says "شركة موكلة" (a client company, office vocabulary), while the
  matter's field says "الشركة التابعة" (the affiliated/subsidiary company,
  in-house vocabulary). SAG uses it in-house for group companies. The fix is
  mode-driven terminology on one model, not two models.
- **The core of the showcase is government-transaction follow-up**, not only
  litigation. Most sample titles are licence renewals and tax clearance
  ("تجديد إجازة الاستيراد وتصديق براءة الذمة السنوية", renewal of the import licence
  and certification of the annual tax clearance, `legal_task_views.xml:169`). Any
  rebuild that turns "matter" into "lawsuit" would break SAG's actual use.

---

## 4. Upgrade-compatibility surface

SAG runs 19.0.6.3.0 in production with data (about 10 ministries, 23 departments,
2 clients, 11 matters). The professional version must install as an **upgrade
of the same technical name** (`-u legal_department_management`), with
`migrations/<new version>/pre-`, `post-` and `end-migrate.py` scripts.
Treatments:

- **Keep**: same identifier, same meaning; code may change.
- **Keep + change**: same identifier, new behaviour or type; the migration
  adapts the data.
- **Rename + migrate**: a new identifier with the data moved. Avoid it for
  anything a user or another record may reference.
- **Drop + migrate**: the identifier is removed and its data moved, archived or
  deleted on purpose.

### 4.1 Models and tables

| Model | Table | Treatment | Why |
|---|---|---|---|
| `legal.task` | `legal_task` | **Keep** (label becomes "Matter" / "معاملة" (transaction), or "قضية" (case) in office mode, by configuration) | `mail.message.model`, `mail.activity.res_model`, `mail.followers.res_model`, `ir.attachment.res_model`, `ir.filters.model_id`, URLs and the sequence all reference it |
| `legal.company` | `legal_company` | **Keep + change**: add `partner_id` → `res.partner` | same references; the partner link unlocks invoicing, email and portal |
| `legal.ministry` | `legal_ministry` | **Keep**; add a body type (ministry, independent commission, judicial council, governorate) | 10 records in production; referenced by matters |
| `legal.department` | `legal_department` | **Keep**; add an optional `parent_id` (depth for courts), body type and contacts | 23 records; referenced with `ondelete=restrict` |
| `legal.task.create.wizard` | transient | **Keep the name** if it stays a wizard; free to replace (no persistent data). Its action xmlid must stay an `ir.actions.act_window`, otherwise it needs a new xmlid plus removal of the old one (M12) | action URL `…action_legal_task_create_wizard` may be bookmarked |
| `legal.company.report.wizard` | transient | Keep or replace freely | no data |
| `legal.general.report.wizard` | transient | Keep or replace freely | no data |

### 4.2 Fields: technical treatment and product verdict

This table is also the field-level answer to §5.

**`legal.task`**

| Field | Compat treatment | Product verdict |
|---|---|---|
| `task_number` | Keep; never renumber existing rows; add a unique index per company (after probe Q6) | **Keep**: show on the form and in `display_name` |
| `name` | Keep | Keep |
| `legal_company_id` | Keep + change: `ondelete` cascade → **restrict** (Odoo updates the foreign key on upgrade) | Keep; label by mode ("Client" / "Group company") |
| `company_name`, `ministry_name`, `department_name` | **Drop + migrate**: remove the fields; migration M7 drops the columns after probe Q10 confirms no saved filter or export uses them | Drop (P6) |
| `ministry_id` | Keep + change: stored, computed from `department_id.ministry_id`, read-only; M4 repairs mismatches first | Keep as a filter; not an input |
| `department_id` | Keep; relax `required` to "required for government-transaction matter types" (relaxing is safe) | Keep: "Government body / court" |
| `state` | Keep **all five values** | Keep as the coarse state behind configurable stages (a stage model mapped to these five), with a transition table (C6) |
| `approval_state` | Keep all four values; remove emoji from the labels | Keep, enforced (S1) |
| `approver_id`, `approval_date` | Keep; written only by transitions | Keep; shown for both approval and rejection |
| `lawyer_id` | Keep + change: M3 adds each `lawyer_id` to `lawyer_ids` (so nobody's visibility changes), then the field becomes the visible "Responsible" | Keep, visible (S2) |
| `lawyer_ids` | Keep; keep table `legal_task_lawyers_rel(task_id,user_id)` | Keep: "Assigned lawyers" |
| `employee_ids` | Keep; keep the `hr` dependency for now (O8) | Keep under "more" (advanced) |
| `session_date` | Keep + change: stored "next session", computed from a new sessions model; M5 creates one session row per non-empty value | Keep as a display; data lives in sessions (C20) |
| `due_date` | Keep; clean the label (O7) | Keep; later fed by a deadlines model |
| `action_details` | Keep as Text, **or** convert to Html with M8 (`plaintext2html`, otherwise line breaks are lost) | Keep ("Notes") |
| `expenses_amount` | Keep + change: `Float` → `Monetary` plus a new `currency_id` (M2). The column type changes from double precision to numeric; Odoo converts it in place, which the upgrade test must confirm. Later a computed sum of expense lines, with M2 creating one line per non-zero amount | Keep |
| `account_move_id`, `account_payment_id`, `expense_account_id` | Keep the columns (probe Q5; expected empty) | Hide until accounting integration exists (C15) |
| `is_urgent` | Keep | Keep (shown as a flag or priority star, no emoji) |
| `is_overdue` | Keep (non-stored, add `search`) | Keep, made searchable (C5) |
| `attachment_ids` | Keep the table `legal_task_ir_attachment_rel`; M6 sets `res_model`/`res_id` on linked files so the chatter shows them | Merge into one documents view (C18) |
| *(new)* `company_id`, `currency_id`, `active`, `stage_id`, `matter_type_id`… | Add with defaults set by the migration | per the specification |

**`legal.company`**

| Field | Compat treatment | Product verdict |
|---|---|---|
| `name`, `code`, `active`, `notes` | Keep | Keep |
| `company_type` | Keep all five values; add new ones only | Keep and extend (§3.4) |
| `owner_name`, `entity_type`, `registration_number`, `tax_number` | Keep (the name `entity_type` stays; the label becomes "Business activity") | Keep under "Registry details" |
| `phone`, `email`, `address` | Keep + change: M1 creates a `res.partner` per client (name, phone, email, street, `vat` ← `tax_number`, `company_registry` ← `registration_number`), then these become related to the partner | Keep (through the partner) |
| `lawyer_id`, `lawyer_ids` | As on `legal.task` (M3); keep `legal_company_lawyers_rel` | Keep, visible |
| `employee_ids` | Keep; keep `legal_company_employees_rel` | Keep (advanced) |
| `attachment_ids` | Keep; keep `legal_company_ir_attachment_rel`; M6 | Merge into documents |
| `task_ids` | Keep | Keep |
| `task_count`, `pending_tasks_count`, `department_count` | Keep the names; change to non-stored `_read_group` under the viewer's rules (S7). The old columns remain, unused | Keep |
| `ministry_count`, `document_count` | Drop (never displayed); no data to move | Drop, or fold into the dossier panel |
| `total_expenses` | Keep + change → `Monetary` | Keep, managers only |
| `department_cards_html` | **Drop** (non-stored, no data) | Replace with an OWL widget (§3.3) |
| *(new)* `partner_id`, `company_id` | Add; M1 fills them | — |

**`legal.ministry` / `legal.department`**: keep every field. The name and
`ministry_id` pair gains a real unique index (C16) after probe Q11 checks for
case-variant duplicates. `contact_person` stays as free text next to a new
contacts one2many.

**Wizards**: no persistent data. Fields may change freely; the `filter_state`
duplicates should reference `legal.task`'s selection.

### 4.3 Selection values (stored in data, never rename)

| Field | Values |
|---|---|
| `legal.task.state` | `draft`, `in_progress`, `pending_docs`, `done`, `cancelled` |
| `legal.task.approval_state` | `draft`, `to_approve`, `approved`, `rejected` |
| `legal.company.company_type` | `llc`, `joint_stock`, `sole`, `foreign_branch`, `partnership` |
| wizard `filter_state` (both) | same five as `state` (transient) |

Only labels may change, and only through translations and the English source.
The prototype lineage used `cancel` rather than `cancelled`, so probe Q1 must
confirm that no legacy value survives in SAG's rows.

### 4.4 Many2many relation tables (keep the names)

`legal_task_lawyers_rel(task_id, user_id)` · `legal_task_employees_rel(task_id, employee_id)` ·
`legal_task_ir_attachment_rel(task_id, attachment_id)` · `legal_company_lawyers_rel(company_id, user_id)` ·
`legal_company_employees_rel(company_id, employee_id)` · `legal_company_ir_attachment_rel(company_id, attachment_id)`.
Transient: `legal_report_wizard_task_rel`, `legal_general_report_company_rel`,
`legal_gen_report_wizard_task_rel` (free to drop).
Lineage risk: the prototype declared `legal_task_ir_attachments_rel` (with an
**s**). If SAG ever ran the prototype, older attachments may sit in that table,
invisible today. Probe Q7.

### 4.5 XML ids

| Kind | xmlids | Treatment |
|---|---|---|
| Groups | `group_legal_user`, `group_legal_manager` | **Keep**: SAG's users are members. Rename the labels (English source: "Lawyer" / "Legal Manager"), add `privilege_id` (S4). New roles (clerk, approver, auditor, partner) are **new** xmlids implied so that existing members keep exactly their current rights. |
| Group link | `base.group_system` → `group_legal_manager` | **Remove explicitly** (S3), via XML `(3, …)` or M11, after SAG says who should hold the manager role |
| Record rules | `legal_company_rule_lawyer`, `legal_company_rule_manager`, `legal_task_rule_lawyer`, `legal_task_rule_manager` | **Keep the xmlids; change the domains** (the file is not `noupdate`, so an update applies them). Add global multi-company rules as new xmlids. |
| Access rows | `access_legal_ministry_user`, `access_legal_ministry_manager`, `access_legal_department_user`, `access_legal_department_manager`, `access_legal_company_user`, `access_legal_company_manager`, `access_legal_task_user`, `access_legal_task_manager`, `access_legal_task_wizard_user`, `access_legal_company_report_wizard_user`, `access_legal_general_report_wizard_user` | Keep the ids; values change (e.g. users read-only on the directory, S6). The wizard rows follow whatever wizards remain; rows for removed models go with them. |
| Model and field xmlids | `model_legal_task`, `model_legal_company`, `model_legal_ministry`, `model_legal_department`, `model_legal_task_create_wizard`, `model_legal_company_report_wizard`, `model_legal_general_report_wizard`; `field_legal_*__*`; `selection__legal_task__state__*` etc. | Generated automatically; kept as long as the model or field exists. `mail.tracking.value` survives field removal in Odoo 19 (see §7). |
| Sequence | `seq_legal_task` (`noupdate`), **code `legal.task`** | Keep the xmlid and code; existing counter continues. Format changes for new matters go through a migration, because `noupdate` blocks XML changes. |
| Cron | `ir_cron_legal_task_checker` (`noupdate`), code **`model._cron_check_upcoming_sessions()`**, plus its `_inherits` parent server action | **Keep the method name** `_cron_check_upcoming_sessions` as a stable entry point that delegates to the new logic, because the `noupdate` record will keep calling it. Change the interval or name only through a migration. |
| Paper formats | `paperformat_legal_compact_report`, `paperformat_legal_compact_general_report` | Keep the xmlids (reports reference them); merge settings; drop `default` |
| Report actions | `action_report_legal_company`, `action_report_legal_task`, `action_report_legal_general_overview` | **Keep the xmlids** (Print-menu bindings, `action_print_task_report`) |
| Report names | `legal_department_management.report_legal_company_template`, `…report_legal_task_template`, `…report_legal_general_overview_template` | **Keep** (the `report_name` string is the download URL key) |
| Report templates | `report_legal_company_document`, `report_legal_company_template`, `report_legal_task_document`, `report_legal_task_template`, `report_legal_general_overview_document`, `report_legal_general_overview_template` | Keep the ids; rewrite the content |
| Views | `view_legal_task_kanban`, `view_legal_task_tree`, `view_legal_task_calendar`, `view_legal_task_form`, `view_legal_task_search`, `view_legal_company_kanban`, `view_legal_company_tree`, `view_legal_company_form`, `view_legal_company_search`, `view_legal_ministry_list`, `view_legal_ministry_form`, `view_legal_ministry_search`, `view_legal_department_list`, `view_legal_department_form`, `view_legal_department_search`, `view_legal_task_create_wizard_form`, `view_legal_company_report_wizard_form`, `view_legal_general_report_wizard_form` | **Keep the primary view xmlids** (any SAG-side inheriting view hangs on them, probe Q8); rewrite the arches. A retired view is deleted by the ORM when its xmlid disappears, **which breaks any inheriting view**, so check Q8 first. |
| Window actions | `action_legal_task`, `action_legal_task_to_approve`, `action_legal_company`, `action_legal_ministry`, `action_legal_department`, `action_legal_task_create_wizard`, `action_legal_general_report_wizard` | Keep (URLs `/odoo/action-legal_department_management.<xmlid>` are bookmarkable; `ir.filters.action_id` may point at them) |
| Client action | `action_legal_dashboard`, tag **`legal_dashboard_tag`** | Keep the xmlid **and** the JS registry tag (the stored action carries the tag); the component behind it is replaced |
| Menus | `menu_legal_root`, `menu_legal_dashboard_main`, `menu_legal_create_task_action`, `menu_legal_company`, `menu_legal_department`, `menu_legal_approvals_root`, `menu_legal_tasks_to_approve`, `menu_legal_all_tasks_management`, `menu_legal_general_report` | Keep the xmlids that survive, re-parented and relabelled. Menus that disappear are deleted with their xmlid; add new ones under new xmlids. |

### 4.6 References to the module held elsewhere in SAG's database

| Holder | What it references | Risk if we rename or drop |
|---|---|---|
| `mail.message`, `mail.followers`, `mail.activity`, `mail.tracking.value` | model names; `field_id` | Model rename would orphan history. **Keep the models.** Field removal is safe for tracking values in Odoo 19. |
| `ir.attachment` | `res_model`, `res_id`, plus the many2many rows | Keep the models and relation tables |
| `ir.filters` (saved favourites) | `model_id`, domains naming fields (e.g. `lawyer_ids`, `approval_state`, `company_name`), `action_id` | A renamed or dropped field breaks the filter at load. Probe Q10 before dropping anything. |
| `ir.exports` / `ir.exports.line` | field names | same |
| `ir.default` (user "set default") | `field_id` | Dropped fields remove them (acceptable) |
| `ir.ui.view` not owned by the module | inherits from our views | Q8. A broken inheritance **aborts the upgrade**. |
| `ir.model.fields` with `state = 'manual'` (`x_` fields added in debug mode) | our models | Q9. Kept by Odoo, but views must not collide |
| `ir.actions.server` / `base.automation` | `model_name`, and code calling our methods | Q12. Keep the public method names used there |
| `res.users` group membership | `group_legal_user`, `group_legal_manager` | keep the xmlids (§4.5) |
| Users' bookmarks and links | `/odoo/action-legal_department_management.action_…` | keep the action xmlids |
| `ir.cron` (`noupdate`) | method `_cron_check_upcoming_sessions` | keep the method |
| `ir.sequence` (`noupdate`) | code `legal.task` | keep the code |

### 4.7 Read-only probes to run on SAG before writing migrations

These are metadata and counts only, in line with the posture of
`docs/external-review/sag-legal-module.md`: no record content, and run only with
SAG's consent.

| # | Query (sketch) | Decides |
|---|---|---|
| Q1 | `SELECT state, approval_state, count(*) FROM legal_task GROUP BY 1,2` | whether legacy selection values exist |
| Q2 | `SELECT company_type, count(*) FROM legal_company GROUP BY 1` | the same for clients |
| Q3 | count of matters whose `ministry_id` differs from their department's ministry | M4 size |
| Q4 | count of matters and clients where `lawyer_id` is not in `lawyer_ids` | M3 effect: how many hidden grants exist today |
| Q5 | counts of non-null `account_move_id`, `account_payment_id`, `expense_account_id` | whether the accounting fields are truly dead |
| Q6 | `SELECT task_number, count(*) … HAVING count(*) > 1` | whether a unique index can be added |
| Q7 | `information_schema.columns` / `tables` for `legal_%`: look for prototype leftovers (`department_category`, `lawyer_name`, `legal_task_ir_attachments_rel`) | lineage clean-up |
| Q8 | `ir_ui_view` with `model LIKE 'legal.%'` and no `ir_model_data` row from this module | inheritance breakage |
| Q9 | `ir_model_fields WHERE model LIKE 'legal.%' AND state = 'manual'` | custom fields |
| Q10 | `ir_filters` / `ir_exports(_line)` on `legal.%`: which field names they use | whether dropping `company_name` etc. is safe |
| Q11 | case- and space-insensitive duplicate names among ministries and departments | unique index |
| Q12 | `ir_act_server` / `base_automation` with `model_name LIKE 'legal.%'` | method names to keep |
| Q13 | users per group; admins who reach the manager role **only** through `base.group_system` | M11 policy |
| Q14 | `mail_activity` duplicates per (`res_id`, `user_id`, `summary`) on `legal.task` | M9 size |
| Q15 | many2many attachments whose `res_model`/`res_id` do not match the owning record | M6 |
| Q16 | active languages (`res_lang`), company currency, company timezone | M10, M2, C4 |
| Q17 | `ir_cron` state for the checker (active, interval, `nextcall`, `user_id`); `ir_sequence` `number_next` | cron and sequence handling |

### 4.8 Migration steps (to be written against the probes)

| Step | Phase | Action |
|---|---|---|
| M1 | post | Create a `res.partner` (company type) per `legal.company` and fill `partner_id`; copy phone, email, address, tax and registry numbers |
| M2 | post | Set `currency_id` = company currency on matters; verify the float → numeric conversion of `expenses_amount`; optionally create expense lines |
| M3 | post | Add `lawyer_id` into `lawyer_ids` on matters and clients (keeps who-sees-what identical), then expose `lawyer_id` as Responsible |
| M4 | pre | Set `ministry_id` from the department where they differ (count from Q3, logged) |
| M5 | post | Create one session row per non-empty `session_date` (type "session / visit", no outcome) |
| M6 | post | Set `res_model`/`res_id` on many2many attachments that lack them, so the chatter and documents view show them |
| M7 | end | `ALTER TABLE … DROP COLUMN company_name, ministry_name, department_name` (Odoo leaves orphan columns) once Q10 is clean |
| M8 | post (if chosen) | Convert `action_details` to HTML with `plaintext2html` |
| M9 | post | Remove duplicate cron activities (keep the newest per matter, user and kind) |
| M10 | end | Load `ar.po` with overwrite for this module, so every term moved to English source keeps its Arabic for `ar_001` users. The upgrade test must show every screen still Arabic for an Arabic user. |
| M11 | post | Unlink `group_legal_manager` from `base.group_system`'s implied groups; grant the manager role explicitly per SAG's answer (Q13) |
| M12 | post | Remove duplicate or dead records whose xmlids disappear (e.g. the second paper format), and replace the intake action if it becomes a client action (new xmlid; delete the old one) |
| M13 | post | Set `company_id` = main company on all records |
| M14 | post | If stages are introduced, map each of the five `state` values to a default stage |

Every step needs an upgrade test: restore `ldm_baseline`, run `-u`, and assert
counts, access per role, and screenshots in Arabic and English.

---

## 5. Keep / change / drop verdict for every element

Field-level verdicts are in §4.2. This table covers every other element.

### 5.1 Models, wizards, data, security

| Element | Verdict | Becomes |
|---|---|---|
| `legal.task` | **Keep, change** | The matter: typed (government transaction, litigation, consultation, contract…), stages, sessions, deadlines, expenses, documents; mode-dependent vocabulary |
| `legal.company` | **Keep, change** | The client (office mode) or group company (department mode), backed by `res.partner` |
| `legal.ministry` | **Keep, change** | Top level of the government-body directory, with a body type |
| `legal.department` | **Keep, change** | The government body, directorate or court, with an optional parent, contacts, hours and location |
| `legal.task.create.wizard` | **Change** | A one-step quick-create (OWL dialog), U4 |
| `legal.company.report.wizard` | **Change** | A short print dialog (or print from the filtered list); data-based report (C7, C10) |
| `legal.general.report.wizard` | **Change** | The same; remove the dead toggle (C9) |
| `_cron_check_upcoming_sessions` | **Keep the name, change the logic** | A deadline and session reminder engine with lead times and no duplicates (C1-C4) |
| `seq_legal_task` | **Keep** | Same sequence; optional yearly reset and format for new matters through a migration |
| `group_legal_user` | **Keep, change** | "Lawyer / Legal officer", with a privilege and category |
| `group_legal_manager` | **Keep, change** | "Legal manager"; **no longer implied by `base.group_system`** |
| new roles | **Add** | Clerk, Approver, read-only Auditor, and an office-mode Partner |
| 4 record rules | **Keep ids, change domains** | Coherent visibility (S2, S9) plus multi-company |
| 11 access rows | **Keep ids, change values** | Directory read-only for users (S6) |
| `legal_security.xml` `base.group_system` block | **Drop** (with M11) | — |
| paper formats (2) | **Keep ids, merge** | One compact format; no `default` flag |
| `report/legal_reports.xml` | **Drop** | — |
| `__pycache__` in the tree | **Drop** | — |
| dependencies `hr`, `account` | **Keep now, change later** | Auto-install bridge modules once accounting is real (O8) |

### 5.2 Views and screens

| Element | Verdict | Becomes |
|---|---|---|
| Matter kanban | **Change** | Grouped by stage, not draggable across bodies; a compact card (number, title, client, body, next date, responsible avatar, overdue badge); no inline styles or emoji |
| Matter list | **Change** | About 6 default columns, the rest optional; one status badge; overdue as the only row decoration; monetary sums for managers |
| Matter calendar | **Keep, change** | Sessions and deadlines from their own models; colour by type |
| Matter form | **Change heavily** | Title area with number, client, body, stage and overdue/urgent badges; one primary action plus a "⋯" menu; approval banner; "essentials" first, with details (team, registry, accounting) behind progressive disclosure; a sessions and deadlines timeline; one documents area; chatter |
| Matter search | **Keep, change** | Default *My matters*; overdue as a real field; no emoji; filters by type and stage |
| Client kanban | **Keep, change** | Standard card with counts computed under the viewer's rules |
| Client list | **Keep, change** | Fewer columns; totals for managers |
| Client form | **Change** | One "matters by government body" OWL panel (the valued windows idea, U5); registry details behind "more"; partner link; chatter |
| Client search | **Keep** | plus type filters from the extended legal forms |
| Ministry list and form | **Keep** | Editable departments in place (§3.17); body type |
| Department list and form | **Keep, change** | Flat list by default (U9); contacts, hours and location |
| Intake wizard view | **Replace** | OWL quick-create dialog |
| Report wizard views (2) | **Replace** | Short dialogs, or printing from the list |
| `action_legal_task_to_approve` | **Keep, change** | "Awaiting my approval" for approvers, fed by the enforced approval axis |
| `action_legal_ministry` | **Keep** | Give it a menu under Configuration |

### 5.3 Menus

| Menu | Verdict | Becomes |
|---|---|---|
| Root "الشؤون القانونية" (legal affairs) | **Keep, change** | Restricted to legal groups (S8); label per mode |
| "📊 لوحة المتابعة…" (the dashboard) | **Keep, change** | "Home", with no emoji |
| "➕ بدء معاملة…" (start a new matter) | **Keep, change** | Stays top-level; opens the quick-create |
| "الشركات والموكلين" (companies and clients) | **Keep** | "Clients" / "Group companies" by mode |
| "الدوائر والجهات الرسمية" (government bodies) | **Change** | Moves under "Configuration" |
| "⚖️ الصلاحيات والموافقات" folder (permissions and approvals) | **Change** | Split: "Matters" (everyone, own by default); "Approvals" (approvers only) |
| "معاملات بانتظار الاعتماد ⏳" (awaiting approval) | **Keep, change** | Under Approvals; no emoji |
| "الرقابة العامة على كافة القضايا 📑" (oversight of all matters) | **Change** | Becomes the Matters register (all matters for managers and auditors) |
| "🖨️ طباعة تقرير الرقابة…" (print the oversight report) | **Change** | Under "Reporting", next to pivot and graph analyses |
| *(new)* Calendar, Reporting (pivot/graph), Configuration (bodies, matter types, stages, settings with the department/office switch) | **Add** | — |

### 5.4 Reports

| Report | Verdict | Becomes |
|---|---|---|
| Client dossier (`action_report_legal_company`) | **Keep, change** | `web.external_layout` letterhead; data-based filters (C7, C10); monetary formatting; the reader's language; mode-dependent signature titles |
| Per-matter follow-up form (`action_report_legal_task`) | **Keep, change** | The same fixes, plus sessions or visits and outstanding documents, a QR code back to the record, and space for the counter officer's remarks |
| General oversight report (`action_report_legal_general_overview`) | **Keep, change** | Data-based; grouping by client really implemented; complemented (not replaced) by pivot and graph views |

### 5.5 OWL dashboard and styling

| Element | Verdict | Becomes |
|---|---|---|
| Client action tag `legal_dashboard_tag` | **Keep** | The same tag, new component |
| `LegalDashboard` data loading | **Drop** | A server method with `_read_group` plus limited lists (P1) |
| KPI cards | **Change** | Overdue, due this week, sessions this week, awaiting my approval, my open matters; each one a keyboard-accessible drill-down (A1) |
| Client filter inside a KPI card | **Change** | A filter in the control panel, carried into every drill-down (§3.16) |
| Recent-matters panel | **Change** | "Needs my attention" ordered by the next date |
| Upcoming sessions panel | **Keep, change** | Sessions and visits for the next 7 days with body and time |
| Distribution by department | **Drop from home** | Moves to Reporting (graph) |
| Hero header with title and 2 buttons | **Change** | Standard control panel; "New matter" as the primary button |
| `legal_dashboard.scss` | **Drop** | Module SCSS using Odoo variables, logical properties and dark-mode support (R1, U14, P5) |
| Global kanban override block | **Drop** | — |
| `department_cards_html` | **Drop** | An OWL "matters by body" widget |
| Icons `icon.png` / `icon.svg` | **Keep** | (a brand decision for the owner) |

---

## 6. What the showcase does not attempt (for the specification)

Listed so the specification does not mistake the showcase's scope for the target.
Details belong to research documents 03 (department needs) and 04 (office needs).

- **Litigation**: court, case number at the court, level of court, parties and
  opponents, judge, hearing log with outcomes, judgments, appeal deadlines.
- **Government work**: a catalogue of transaction types per body with required
  documents and fees; the prototype's ten-body catalogue is a ready seed
  (see 02). Verification requests (صحة صدور) as tracked items; licence and
  registration expiries.
- **Documents**: typed documents with expiry, incoming and outgoing official
  letters (الكتب الرسمية), and powers of attorney (الوكالات) with scope and
  expiry.
- **Office mode**: engagements, conflict check, fee agreements, time and
  expenses, invoicing, trust money, and a client portal.
- **Department mode**: requests from internal business units, legal opinions,
  contract review, SLA and working calendars.
- **Oversight**: an audit trail, a read-only auditor, pivot and graph analyses,
  and a confidentiality level per matter.

---

## 7. Verification log: what was checked in Odoo 19, and what was corrected

| Claim | Evidence | Result |
|---|---|---|
| Buttons' `groups=` do not protect methods | `addons/web/controllers/dataset.py:35-41`: `call_button` calls any method with no view check | **Confirmed**; S1 |
| Groups without a privilege are hidden on the user form | `addons/web/static/src/webclient/res_user_group_ids_field/res_user_group_ids_field.js:40-45, 100`: the "extra" category is rendered only in debug mode | **Confirmed**; S4 |
| Client-action menus are visible to all | `odoo/addons/base/models/ir_ui_menu.py:95-128`: `MODEL_BY_TYPE` has no `ir.actions.client` | **Confirmed**; S8 |
| `placeholder=` on fields warns | `odoo/orm/fields.py:531-538`; `.odoo_logs_ldm/baseline_install.log:949-953, 990-994` | **Confirmed**; O1 |
| The Html field sanitises values assigned in compute | `odoo/orm/fields_textual.py:614-690` (`convert_to_cache` → `html_sanitize`) | **Confirmed**; so S13 is *not* exploitable XSS, and the `onclick`/`onmouseover` handlers are dead code (O2) |
| The router intercepts `/odoo/...` links | `addons/web/static/src/core/browser/router.js:309-336` | **Confirmed**; explains why the HTML cards still navigate (O2) |
| SCSS is flipped by rtlcss for right-to-left users | `odoo/addons/base/models/assetsbundle.py:573-592`; screenshot 01 (header accent on the left) | **Confirmed**; R1 |
| `_()` cannot translate into English | `odoo/tools/translate.py:419-420` | **Confirmed**; I1 |
| Cron user default | `odoo/addons/base/models/ir_cron.py:110` (`default=self.env.user`) | **Confirmed**; C3 |
| `report.paperformat.default` matters | `odoo/addons/base/models/report_paperformat.py:170`; not used by the company default (`res_company.py:72`) | Label only; O4 is Info |
| **Report filters are lost because the context is not sent** | `addons/web/static/src/webclient/actions/action_service.js:1367-1372` merges `action.context` into the download context; `web/controllers/report.py:28-37, 118-120` applies it | **Refuted** for the web download path. Downgraded to C10 (fragile; lost on server-side and HTML-preview paths) |
| **Removing a tracked field deletes its chatter history** | `addons/mail/models/mail_tracking_value.py:15-18` (`ondelete='set null'`, `field_info`); `addons/mail/models/ir_model_fields.py:35-58` fills `field_info` on unlink | **Refuted**: Odoo 19 keeps the history. Dropping fields is safe for the chatter. |
| **Stored related name copies "drift"** (external review, idea 13) | the ORM recomputes stored related fields on source change | **Corrected**: they do not drift through the ORM. The real problems are that nothing reads them and they cost writes (P6). |
| `fa` icons without a title produce view warnings | `odoo/addons/base/models/ir_ui_view.py:2320-2341`; no such line in the install log | Not triggered; not claimed |
| Internal users can read `account.account` | `addons/account/security/ir.model.access.csv:70` | Yes, so the `expense_account_id` picker works for lawyers; move and payment need accounting rights (only matters once they are filled) |

**Sources**

- Local Odoo 19 source: `C:/Users/Lenovo/Documents/odoo19/odoo-19.0/` (paths above).
- Baseline evidence: `docs/ldm/evidence/00-baseline/*.png`, `metrics.json` (0 console errors on all eight screens).
- `.odoo_logs_ldm/baseline_install.log`.
- Earlier metadata review: `docs/external-review/sag-legal-module.md`.
- Prototype lineage (older module copy): scratchpad `src/old/legal_department_management/models/legal_task.py` (the ten-body `department_category`, `cancel` state value, `legal_task_ir_attachments_rel`).
- Iraqi company forms: [Al Tamimi & Co., "Companies and their administration in Iraq"](https://www.tamimi.com/law-update-articles/companies-and-their-administration-in-iraq/); [Company Law No. 21 of 1997, as amended 2004](https://baghdad.eregulations.org/media/company%20law%2021%20as%20amended%20in%202004.pdf).
