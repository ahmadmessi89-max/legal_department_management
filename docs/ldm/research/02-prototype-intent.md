# Prototype intent — what the AI Studio mock and the old module copy were trying to build

**Scope of this document.** Recovers product intent for `legal_department_management`
(SAG Group, technical name unchanged since v19.0.1.0.0, now v19.0.6.3.0, committed at
`ccebae7`) from two upstream artefacts, cross-checked against the module as it exists
today. It does **not** decide the professional rebuild plan — it is the evidence that
plan is built from. Nothing in the repository was changed to produce this document.

**Sources read.**

| Artefact | Path | What it is |
|---|---|---|
| React prototype | `…/scratchpad/src/old/src/**` (App.tsx, 20 components, types.ts, initialData.ts, translations.ts, LanguageContext.tsx) | Google AI Studio app, id `52c3deb2-…`, "Legal Department Management" — Express + `server.ts` backend, React 19 + Vite + Tailwind frontend |
| Old module copy | `…/scratchpad/src/old/legal_department_management/**` | The **first**, literal Odoo port of the prototype: v19.0.1.0.0, OPL-1, author "Enterprise Legal Solutions" — one Selection field standing in for the whole department tree |
| Current module | `custom_addons/legal_department_management/**` | v19.0.6.3.0, LGPL-3, author SAG Group — the production module, committed unchanged at `ccebae7` |
| `docs/mock-adoption-plan.md` | repo | An earlier (2026-09-05) feature-by-feature review of the **same prototype**, judged against the larger `legal_office`/`legal_case` suite. Different target architecture from this task, but its per-feature verdicts on UI patterns (charts, badges, QR, OCR, inline state) transfer directly and are cited throughout |
| `docs/external-review/sag-legal-module.md` | repo | Read-only metadata review of SAG's **live production instance** (`odoo.sag2.group`) — confirms the current module's field list, menu shape and the production data volumes (10 ministries, 23 departments, 2 companies, 11 tasks) that any rebuild must upgrade over |
| `docs/mock-review/*.png` | repo | 13 screenshots of the prototype, referenced by number below |
| `docs/ldm/evidence/00-baseline/*.png` | repo | 8 screenshots of the **current** module, used to answer "does the showcase implement this today" |

**Lineage, in one line.** React/Gemini mock → naive 1:1 Odoo port (old module,
`department_category` as a 10-value Selection) → SAG's production module (real
`legal.ministry`/`legal.department` records, approval workflow, accounting links,
three report wizards) → this task, which must turn the production module into
professional software **without breaking its model names or the 11 live matters**.

---

## 1. Data model the prototype assumed (`types.ts`, `initialData.ts`)

This is the contract every component below was built against. Column "Current
module" gives the closest existing field on `legal.task` / `legal.company` today.

| Prototype type/field | Type | Meaning | Current module equivalent |
|---|---|---|---|
| `LegalCompany.id/name/code/notes` | number/string | client company | `legal.company.id/name/code/notes` — present |
| `LegalCompany.partners` | string | free-text shareholder list | **missing** — no structured partners/shareholders |
| `LegalCompany.task_count/pending_tasks_count/total_expenses` | number | dossier badges | `legal.company` computes all three, **stored** — better than the prototype (client-side reduce over the full task list) |
| `DepartmentCategory` (10 literal codes) | enum | telecom/utilities/registrar/tax/traffic/social_security/trade_exhibitions/transporters/notary/personal_tax | **superseded**: `legal.ministry` (10 rows in production) + `legal.department` (23 rows) — real records with `code`, `phone`, `address`, `sequence`, `active`, not a hardcoded enum. Confirmed better by both prior reviews (mock-adoption-plan #4/reject-the-enum; sag-review idea 4/reject) |
| `OfficialSubService` (deptCode, subCode أ/ب/ت…, title) — 28 rows | static list | the statutory sub-procedure catalogue, table in §5 below | **missing as data** — nothing in the current module encodes "these are the N filings that exist for this department"; `legal.department` has no child "procedure type" or "service" model. This is the single largest content gap, see §6 |
| `LegalTask.id/name/legal_company_id/lawyer_id/state/due_date/session_date/expenses_amount/action_details` | mixed | the case record | present, plus the current module already **exceeds** this: `approval_state`, `approver_id`, `lawyer_ids` (m2m, prototype only had one), `employee_ids`, `account_move_id/account_payment_id/expense_account_id`, `is_urgent`, `is_overdue` (computed), `task_number` (sequence) |
| `LegalTask.action_steps: LawyerActionStep[]` | embedded array | numbered field-visit steps (title, details, lawyer, date, status, attachment) | **missing** — no child model; `action_details` is one free-text field |
| `LegalTask.chatter_messages / activities` | embedded | messaging + to-dos | **superseded, better**: real `mail.thread` + `mail.activity.mixin` (native chatter, native activities) instead of hand-rolled arrays |
| `LegalTask.attachments: LegalTaskAttachment[]` (name, size, date, type, category, scannedBy, previewDataUrl) | embedded | scanned-document gallery with a category taxonomy | **partial**: `attachment_ids` (m2m to `ir.attachment`) exists, but there is no `category` taxonomy and no `scannedBy`/OCR metadata — plain Odoo attachments, no scanner workflow |
| `LegalTask.audit_history: LegalTaskAuditEntry[]` (user, timestamp, old/new data) | embedded | a hand-written audit trail duplicating chatter | **superseded, better**: `tracking=True` on every field already writes this into the native chatter/`mail.message` log — the prototype's parallel audit array is redundant by construction |
| `LegalUser.job_title/role` | string/enum | `'محامي' \| 'مدير الشؤون القانونية'` mapped to `'user' \| 'manager'` **by matching a substring of a free-text job title** | **flagged as a defect, not a gap**: current module uses two real `res.groups` (`group_legal_manager`, implicit base user) — correctly avoids the prototype's privilege-escalation pattern. Do not reintroduce string-matched roles |
| `OperationLog` (actionType, targetType, targetName, details) | embedded | the global audit-log screen's rows | **superseded**: native chatter tracking again; a global log is one `mail.message` search, not a parallel model |

---

## 2. Feature inventory

Each entry: what it does → data it needs → whether the **current** module (v19.0.6.3.0,
screenshots in `docs/ldm/evidence/00-baseline/`) implements it → verdict for the
professional rebuild. Verdict vocabulary is exactly the four the brief asked for:
**build natively** (Odoo ORM + standard views/actions, no custom JS), **build with
custom OWL** (a bespoke frontend component earns its keep), **use standard Odoo
feature** (the capability already exists in Odoo core/`web`/`mail`/`account` — wire
it, do not rebuild it), **drop** (no product value, or actively worse than the Odoo
convention it would replace).

### 2.1 Dashboard (`DashboardView.tsx`, screenshot `01-dashboard.png`)

Four KPI tiles (completed/pending/expenses/companies) + **five charts**: lawyer
productivity (stacked bar), avg. resolution days per department (bar, seeded from a
**hardcoded dict** `{'شركات': 14, 'عدول': 3, …}` then averaged with a literal fallback
`days = 7`), expenses-by-company (bar), department distribution (pie), and a
6-month revenue/expense trend (**area chart with five of six months hardcoded**,
only the current month computed). Plus an "upcoming sessions" card grid.

- **Current module:** has its own OWL dashboard (`static/src/dashboard/legal_dashboard.js/.xml/.scss`, registered as `legal_dashboard_tag`) with real KPI tiles (see baseline `01_dashboard.png`: منجزة/عاجلة/بانتظار الاعتماد/جارية counts + a company filter) — **already implemented**, and already avoids the prototype's fabricated charts.
- **Verdict: build with custom OWL for the KPI tiles (already done, keep and extend), drop the two fabricated charts entirely, standard Odoo feature for anything chart-shaped.** `mock-adoption-plan.md` §5 independently reached the same reject on the resolution-time and revenue-trend charts ("fabricated ... seeded from a hardcoded dict"/"five of its six months are hardcoded constants") — do not let a rebuild re-import them looking for "parity with the mock." Any real analytics (tasks per ministry, expenses over time) belongs on a `pivot`/`graph` view over `legal.task`, which is free once the model is reportable, not on more OWL chart code.

### 2.2 Company dossier — list + 10×28 compliance matrix (`CompanyDossierView.tsx`, screenshots `02`, `03`)

Two-level screen: a card grid of companies (completion %, three state chips, total
expenses), then per-company an **accordion of all 10 departments**, each expanded to
its sub-services from the static 28-row catalogue (§5), each row showing a matched
task or a "لم يبدأ" (not started) state with a **"بدء الإجراء" button that creates
the missing filing**. Completion % = `completed_count / 28`.

- **Current module:** `department_cards_html` on `legal.company` (see `legal_company.py`, `_compute_department_cards_html`) renders a similar grouped-by-ministry/department view, but as a **server-rendered HTML blob field** with `onclick` JavaScript hacks to call `doAction` — not a real view, not searchable, not groupable, and (per the external review, §5.6) "re-renders server-side on every read." It also only shows departments/tasks that **already have a task** — it does not show the "not started" rows the prototype's matrix makes its whole point of.
- **Verdict: build natively, as a read-only SQL-backed model, not custom OWL.** This is the single idea in the whole prototype both prior reviews call the most valuable ("the mock's dossier shows the procedures that do not exist yet — in a compliance product the missing filing is the whole point," `mock-adoption-plan.md` §3 P1-A). The HTML-blob mechanism is explicitly wrong (same document, "Do not implement it the mock's way"; external review §5.6 flags it as a regression to avoid). The correct shape needs two new pieces this module does not have today:
  1. A **service/procedure-type model** — `legal.department` needs child rows (name = the sub-service, e.g. "دفع الرسوم وتقديم الطلبات") so the catalogue in §5 becomes configuration, not a hardcoded list, and so the module remains **configurable between an in-house department and a law office** (a law office's "sub-services" are different per §6.2).
  2. A **coverage view** (`_auto=False` SQL model, `entity × procedure_type` CROSS JOIN LEFT JOIN task, exactly the pattern `legal.entity.coverage` already proves works in this codebase — see `mock-adoption-plan.md` §3 for the query shape) so "not started" rows exist without writing 28 draft tasks per company. Group by department gives the accordion for free via `default_group_by` on a native `<list>`/`<kanban>`, which is also how the current `legal_task_views.xml` kanban already groups (`default_group_by="department_id"`).
  This is native Odoo work (views + one SQL model), not an OWL component — the "accordion of grouped rows with per-group counts" is exactly what a grouped list/kanban already renders.

### 2.3 Task list with advanced filters (`TaskListView.tsx`, screenshots `04`, `05`)

Instant search (name/company/lawyer/details), quick selects (company/state/due-date
preset), an **"advanced search" drawer** (company, state with pill toggles, due-date
presets including exact-date/range/no-date, department, an **"impact" classifier**:
urgent-48h ∪ fee ≥ 500 000 IQD ∪ "sovereign" department ∪ blocked-on-docs), removable
filter chips, a live "N of M matching" counter, checkbox multi-select + bulk state
change, sort-by-nearest-due-date toggle, a red "N due within 48h" banner, up to
**four coloured badges per row**, and a footer Σ of the fees column.

- **Current module:** `legal_task_views.xml` has `list, kanban, form, calendar` view modes (confirmed by grep) but no advanced-search drawer, no impact classifier, no bulk-action button, no footer sum — this is a plain Odoo list today (see baseline `04_tasks_list.png`).
- **Verdict, item by item — mostly "use standard Odoo feature," not custom code:**
  - Instant search, quick company/state selects, removable chips, live match count → **standard Odoo feature**. Odoo's search view + facets already render exactly this (`mock-adoption-plan.md` #14/#15, "Odoo's search facets already do exactly this" — reject rebuilding it).
  - Due-date presets (today/tomorrow/this-week/this-month/exact/range/**no-date**) → **build natively**: a handful of `<filter domain="...">` entries on the search view. "بدون تاريخ" (`due_date = False`) is the one genuinely missing today and worth adding first.
  - Impact classification (urgent-48h, high-fee, sovereign body, blocked-on-docs) → **build natively**: 3–4 `<filter>` elements plus one boolean (`is_sovereign` on `legal.department`, configuration not code) and the 500 000 threshold as an `ir.config_parameter`, not a literal in the view.
  - Bulk state change from a checkbox selection → **build natively, but only as a server action that calls the same transition methods** (`action_set_in_progress`, etc.) already on `legal.task` — never a raw `write({'state': …})`, which is how the prototype's version bypasses any future guard on those transitions.
  - Footer Σ of fees → **standard Odoo feature**: `sum="…"` on the `expenses_amount` column, one XML attribute.
  - Row decorations (colour bar by state/urgency) → **standard Odoo feature**: `decoration-danger`/`decoration-warning` on `<list>`.
  - Up to four badges per row → **drop**. Screenshot `05-task-list-advanced-search-open.png` is the mock's own evidence of the failure mode: badge noise competing with the subject line. One decoration colour communicates state; a second `is_urgent` badge is the ceiling.

### 2.4 Task Kanban (`TaskKanbanView.tsx`, screenshot `06`)

Four columns (draft/in_progress/pending_docs/done), each card showing department
chip + inline "quick edit" pencil that turns the **entire card into an edit form**
in place (name, department, lawyer, expenses, due date), plus a `<select>` on every
card to change stage directly.

- **Current module:** `legal_task_views.xml` already ships a kanban (`default_group_by="department_id"`, confirmed by grep) — grouped by department, not by state as the prototype does, and column view mode already exists as `list,kanban,form,calendar`.
- **Verdict: use standard Odoo feature for the board itself** (a kanban grouped by `state` with `group_by` is one view change), **drop the inline full-card edit and the direct `<select>` stage-changer**. Both bypass whatever transition guards the state machine carries — this is the same objection as §2.3's inline bulk edit, and it is `mock-adoption-plan.md` #11's explicit reject ("bypasses the transition engine ... the row opens the file; the file has the statusbar"). A kanban card's job is to open the form and to support the board's own native drag-and-drop between columns (which itself should call the transition method, not a raw write) — nothing more.

### 2.5 Task Calendar (`TaskCalendarView.tsx`) — **dead code in the prototype**

A hand-rolled month grid (not a real calendar component) plotting tasks on
`session_date`/`due_date`. `mock-adoption-plan.md` §1.3 already flagged this exact
component as imported by `App.tsx` and never rendered — the view-mode switcher in
that build offers no calendar button, so this screen is unreachable in the mock
itself.

- **Current module:** already ships a real `<calendar>` view on `legal.task` (confirmed by grep, `view_mode` includes `calendar`) — an actual native Odoo calendar, not a hand-rolled grid.
- **Verdict: use standard Odoo feature (already done).** Nothing to port; the prototype's own version was never even wired up.

### 2.6 Task form (`TaskFormView.tsx`, screenshot `08`) — the largest single component (~1150 lines)

- **Statusbar with explicit transition buttons** (بدء الإجراءات / انتظار الوثائق / إنجاز / إلغاء) plus a second always-visible pill row. → **Current module: yes, native** (`legal_task_views.xml` statusbar, confirmed by baseline `05_task_form.png` showing five action buttons: طلب وثائق/صحة صدور, رفض الطلب, اعتماد وموافقة, إنجاز المعاملة بنجاح, إلغاء المعاملة, إعادة للمسودة). **Verdict: use standard Odoo feature (already done).**
- **AI due-date suggestion**: a `Record<DepartmentCategory, {days, reason}>` of **ten hardcoded integers** (e.g. `registrar: 21 days`) dressed as "توصية الذكاء الاصطناعي بالموعد النهائي", with a one-click "اعتماد" to apply it. → **Current module: no.** **Verdict: build natively, and do not call it AI.** `mock-adoption-plan.md` #24 is blunt and correct: "the mock's version is ten hardcoded integers dressed as AI." The legitimate version of this idea is an SLA rule per department (`target days`, counted in the department's actual working calendar via `resource.calendar` — Sunday–Thursday, holidays as leave — the way the sibling `legal_procedure` suite's `legal.sla.rule` already does it). That is configuration data plus one compute method, not a JS dictionary and not an LLM call.
- **Standard checklist applied when department changes** (`applyCategoryTemplate`): inserts a text block of `[ ] N. item` lines into the free-text `action_details` field, from a small hardcoded template set (also editable in §2.13). → **Current module: no** (no checklist template concept exists on `legal.task` today). **Verdict: build natively — as a real child model, not a text block.** A `legal.task.document.requirement` (or equivalent) child of `legal.department`/service, rendered as tickable lines in a form tab (a `<list>` with a `state` checkbox), gives the same "impossible to miss" effect the mock's checklist has, but the lines are real records: they can block a state transition, they can be grouped, and a report can show "3 of 5 required documents received" without parsing text.
- **Lawyer action steps** (`LawyerActionStepsList.tsx`): numbered steps (title, details, lawyer, date, status, optional attachment), a "apply standard template" button seeding 4 generic steps, inline status-cycle button. → **Current module: no** dedicated child model (only the free-text `action_details`). **Verdict: build natively, as a `legal.task.step` One2many** — a small, genuinely useful idea (narrative of what happened at the counter, in order) that the mock implements reasonably; `mock-adoption-plan.md` #27 agrees ("Adapt ... present the existing action log as an ordered timeline; do not add a model" — but that verdict assumes the *big* suite's action-log model already exists. This standalone module has no action-log model at all, so here the child model is the right call, not an adaptation of something already present).
- **Document scanner** (`DocumentScannerModal.tsx`): upload or camera capture, a document-category `<select>` (صحة صدور / لائحة دعوى / براءة ذمة / …), scan filters (magic-color/B&W/original) + rotate, and client-side **OCR via `tesseract.js`** (`ara+eng`), with a canvas-drawn *simulated* scan as a fallback when no camera is available. → **Current module: no** — attachments are plain `ir.attachment` uploads with no category, no OCR. **Verdict: use standard Odoo feature for capture, drop the OCR, keep the category taxonomy as native data.** Odoo 19 web core already ships a camera capture/scan dialog (the same barcode/camera stack cited for §2.8); a generic "upload with a required category field" is a one-line addition to the attachment relation (a `legal.document.type` selection or model), not a bespoke modal. Client-side Tesseract OCR on Arabic government stamps is real effort for weak accuracy (`mock-adoption-plan.md` #31: "a browser OCR bundle for Arabic is heavy and weak on Iraqi stamps" — reject for now, revisit server-side only if a customer asks) — do not port `tesseract.js`. Scan filters/rotation (#32) are what a phone's own camera app already does better; drop.
- **QR label + QR scanner** (`QRCodeScannerModal.tsx`, the printable-label modal inside `TaskFormView.tsx`): generates a QR (`qrcode` npm package) encoding `OdooTask:<id>`, a printable sticker with task/company/lawyer/department, and a **separate scanner** (camera via `jsQR`, image upload, or manual code entry) that parses several ad-hoc payload shapes (`TASK-12`, `OdooTask:12`, a bare `12`, a URL containing `/task/12`, or JSON `{taskId}`) and opens the matching record. → **Current module: no.** **Verdict: use standard Odoo feature — zero new dependencies.** This is the prototype's second genuinely good idea (bridging a paper-first Iraqi office to the record), and Odoo 19's own `web` module already ships everything needed: `scanBarcode(env, facingMode)` and `isBarcodeScannerSupported()` from `@web/core/barcode/*` (ZXing-backed, QR included — verified present under `odoo-19.0/addons/web/static/src/core/barcode/` by `mock-adoption-plan.md` §3 P1-B), plus the `/report/barcode/QR/<token>` report controller already used elsewhere in this codebase for letter QR codes. **Do not** add `jsqr`, `qrcode`, or any client-side QR library — wire the native scanner to a `search` on `legal.task`/`legal.company` (or their identifying reference) and print the label from a QWeb template reusing that same controller. Keep camera + manual entry from the mock's three-tab pattern; drop the upload-an-image tab, which the native scanner does not need.
- **Chatter + audit trail**: a hand-rolled `chatter_messages` feed plus a **separate, parallel** `audit_history` array logging every field change with old/new values. → **Current module: already correct** — `mail.thread` + `tracking=True` on essentially every field of `legal.task`/`legal.company` gives real chatter and a real tracked-field log for free, which is strictly what the prototype's two parallel arrays were trying to fake. **Verdict: use standard Odoo feature (already done); this is not a gap.**
- **"Send directive email to lawyer"**: builds a `mailto:` link plus logs a fake send to `/api/notifications/send-directive-email`. → **Current module: no explicit button**, but `mail.activity` assignment (native) already notifies an assignee. **Verdict: use standard Odoo feature** — an activity or a `mail.template` triggered on assignment change covers this; no bespoke mailto-composer.

### 2.7 Company list / CRUD (`CompanyListView.tsx`, screenshot `07`)

Card grid with search, admin-only edit/delete buttons, a drawer showing the full
record plus its task list, and its own "ماسح القرارات" scanner button.

- **Current module: yes**, `legal.company` already has kanban + list + form (confirmed by external review §2) with the security rule that only managers can delete (`unlink()` override in `legal_company.py`, matching the prototype's admin-only delete). **Verdict: use standard Odoo feature (already done).** The scanner-in-a-drawer pattern adds nothing beyond §2.6's attachment tab.

### 2.8 Contacts management (`ContactsManagementView.tsx`)

Lists `res.users`-like objects, lets an admin **set the `role` (`user`/`manager`) by
picking a free-text `job_title` string** (`'محامي'` vs `'مدير الشؤون القانونية'`),
with the UI stating outright: *"سيتم ضبط حقل الصلاحية `role` آلياً … فور حفظ العنوان
الوظيفي"* (the permission field will be set automatically from the job-title text).

- **Current module: correctly does not have this** — `res.groups` (`group_legal_manager`) already govern access.
- **Verdict: drop, explicitly.** This is not a missing feature; it is a security anti-pattern the current module already avoids and must keep avoiding. `mock-adoption-plan.md` #38 names it precisely: "Assigns groups by substring-matching `'مدير' in function` — a privilege-escalation vector. Groups stay explicit." Any future "who can approve" UI must read/write real `res.groups`/`res.users` membership, never infer it from a text field a clerk can edit.

### 2.9 Audit log screen (`AuditLogView.tsx`, screenshot `09`)

A global, filterable timeline (action type × target type × free-text search) over a
hand-maintained `OperationLog` array.

- **Current module: not needed as a separate model** — chatter tracking (§2.6) already writes every change to `mail.message`.
- **Verdict: use standard Odoo feature.** A "Registers → Action Trail" style menu is a saved search over `mail.message`/`mail.tracking.value` filtered to this module's models, not a parallel log table. Building a second audit mechanism next to native tracking is pure duplication and drift risk (two logs that can disagree).

### 2.10 Email notifications log (`EmailNotificationsView.tsx`)

A read-only inbox-style view of "emails the system sent" (on task completion or
urgent-task creation), backed by a fake `/api/notifications/emails` log, purely for
show — no real SMTP integration in the mock.

- **Current module: not present**, and does not need to be as a separate screen.
- **Verdict: use standard Odoo feature.** Odoo's own mail tracking (`mail.mail` records, the chatter's "sent" indicator, `mail.activity` for reminders) already answers "was this notification sent and to whom" — a dedicated log screen duplicates the mail app.

### 2.11 QWeb printed reports (`QWebReportView.tsx`, screenshot `10`)

Two report types (company file, lawyer performance) rendered as an HTML page with a
generated QR code, then opened in a popup window with print-specific CSS
(`@media print`) for a clean black-and-white printout.

- **Current module: already has three QWeb reports** (`legal_task_report_templates.xml`, `legal_company_report_templates.xml`, `legal_general_report_templates.xml`) plus two report wizards (`legal_company_report_wizard`, `legal_general_report_wizard`) confirmed by the external review (§2: "Reports: three QWeb — a full company file, a general oversight report … a per-matter follow-up form") and by baseline `08_general_report_wizard.png`.
- **Verdict: use standard Odoo feature (already done, and already better)** — real QWeb templates rendered through Odoo's own PDF pipeline beat a `window.open` + injected `<style>` popup-print hack every time (correct paper size, correct fonts, no popup-blocker dependency). The one addition worth taking from the mock is the **QR code on the printed report** — covered by §2.6's QR work, reusing the same `/report/barcode/QR/<token>` helper, not a new dependency.

### 2.12 QWeb template editor (`QWebTemplateEditor.tsx`)

A form (header/sub-header/reference-prefix/logo upload/primary colour/signature
titles/footer notice/watermark text/border toggle) with a live WYSIWYG preview pane,
letting a non-technical admin restyle the printed report without touching code.

- **Current module: not present** — the report header/footer/signatures are presumably hardcoded in the QWeb XML today (not verified further; out of scope to open those templates for this document).
- **Verdict: build natively, as configuration fields, not a bespoke live-preview editor.** The legitimate need (an admin sets the department's letterhead once) is `res.company`-level fields (`report_header`, logo — Odoo already has these) plus a handful of module-specific ones (signature titles, footer notice) surfaced on a normal settings form. A hand-built "live QWeb preview" canvas is solving a problem Odoo's own report-editor/Studio-adjacent tooling already addresses at a different layer; do not build a second one.

### 2.13 Task templates / checklist settings (`TaskTemplatesSettingsView.tsx`, screenshot `11`)

Per-department checklist templates (description, estimated days, an editable list
of checklist line items) that feed §2.6's "apply standard checklist" button.

- **Current module: not present.**
- **Verdict: build natively — this is the configuration side of §2.6's document-requirement model**, not a separate feature. Whatever child model §2.2/§2.6 use for "required documents per service" needs an admin screen to define its rows; that screen *is* this one, just backed by a real model instead of a JSON blob synced through `/api/task-templates`.

### 2.14 XLSX export (`XlsxExportView.tsx`, screenshot `12`)

Two buttons producing `.xlsx` files client-side via the `xlsx` (SheetJS) package —
one exporting the full task list, one exporting per-company expense summaries.

- **Current module: not a dedicated screen**, but every Odoo list view already has a native "Export" action producing XLSX with column selection.
- **Verdict: use standard Odoo feature.** A bespoke export screen re-implements what the list view's export button already does, with less flexibility (fixed columns, no saved-export templates). Drop the screen; if a specific export shape recurs often, register it as a **saved export** on the relevant list view instead.

### 2.15 AI legal assistant (`AILegalAssistantModal.tsx`)

A chat-style modal calling a Gemini API (`@google/genai`) with a curated,
category-tabbed library of Arabic prompt suggestions (تسجيل الشركات / كتاب العدل /
الضرائب / المعارض / المحاكم), each prompt drafting a specific kind of legal letter.

- **Current module: not present.**
- **Verdict: drop, for the module.** Out of scope per the platform's standing rule that this module's professional rebuild should not depend on external paid APIs without owner approval, and `mock-adoption-plan.md` #43/#36 independently reject it ("external API, no offline story, and the steps are already configured data"). The one thing worth keeping from this screen is **not code**: the prompt-suggestion library is a well-organised content brief of the letter types an Iraqi legal department actually drafts (POA, tax objection, board minutes, notarial notice, import-licence renewal request…) — useful as a reference when writing `legal.department`/service-level document-requirement seed data (§2.13), nothing more.

### 2.16 Odoo module explorer (`OdooModuleExplorer.tsx`, screenshot `13`)

A syntax-highlighted source browser over the mock's *own* generated module files,
with "download as .zip" / "download as .html" buttons — a meta-feature of the AI
Studio tool itself, not a legal-department feature.

- **Current module: not present, and should never be.**
- **Verdict: drop.** No product meaning whatsoever; this is AI Studio scaffolding for handing the generated code to a developer, not a screen an Iraqi legal department or law office would ever open.

### 2.17 Navbar & chrome (`Navbar.tsx`)

Apps-launcher grid clone, a centred "+ إجراء جديد" button, an AI-assistant button,
a direct "download module .zip" link, a QR-scanner button, a browser push-notification
toggle, and a "trigger cron now" button with a spinning-refresh icon.

- **Current module:** normal Odoo webclient chrome (real apps launcher already exists).
- **Verdict:** apps-launcher clone → **drop** (`mock-adoption-plan.md` #3, "the real launcher exists"). "+ New" button → **use standard Odoo feature** (every list/kanban already has one; §1-B's guided intake wizard, confirmed independently important by the *production* SAG review as idea 1 — "Start a new matter as a top-level menu item" — deserves a **top-level menu entry**, which the current module already partly has via `legal.task.create.wizard`, confirmed by the external review's menu tree, "بدء معاملة / قضية جديدة"). Browser push notifications → **drop**, duplicates Odoo's own bus/activity notification system (`mock-adoption-plan.md` #45). "Trigger cron now" → **use standard Odoo feature**, Settings → Technical → Scheduled Actions already has "Run Manually" (#44). Download-module-.zip → **drop**, meta-feature (§2.16).

### 2.18 Language / RTL switching (`LanguageContext.tsx`, `translations.ts`)

A React context toggling `lang: 'ar' | 'en'`, flipping `document.dir`/`document.lang`,
backed by a single flat `TranslationDictionary` (~260 lines, one string per UI label,
no pluralisation, no ICU message format) covering nav labels, states, categories,
and a handful of settings-screen strings.

- **Current module:** Odoo's own i18n (`.po` files, `_()` / `_t()`) plus the `ar_001` locale already does this at the platform level, for every string in every view, with real pluralisation and RTL as a first-class layout mode (`dir="rtl"` is automatic, not hand-toggled per component).
- **Verdict: use standard Odoo feature.** A parallel hand-rolled translation dictionary is strictly worse than what Odoo already provides, and the owner's standing requirement (full Arabic coverage, verified by coverage not a partial file — see the project's own translation-coverage rule) is specifically about `.po` completeness, which this pattern cannot deliver. No React-style i18n context belongs anywhere in the rebuild.

---

## 3. What "build with custom OWL" actually means for this module

Reading all eighteen sections above together, the honest count of features that
justify a **bespoke OWL component** (as opposed to configuration on native Odoo
views) is small and specific:

1. **The KPI dashboard tiles** (§2.1) — already exists, keep and extend with real
   (non-fabricated) aggregates once the coverage view (§2.2) exists to aggregate over.
2. **The entity/service coverage matrix's presentation**, *if* a plain grouped
   `<list>`/`<kanban>` over the new coverage view (§2.2) turns out not to render the
   "N / M منجزة" accordion header cleanly enough — worth trying the native grouped
   list first, since it is free, before writing a component for it.

Everything else the prototype implements as a 300–1000-line custom React component —
the task list's advanced-filter drawer, the kanban, the calendar, chatter, the audit
log, contacts, email log, XLSX export, the QWeb editor, i18n — has a native Odoo
answer that is both less code and more correct (native search facets keep working
with saved filters, favourites, and the pager; native chatter keeps working with
`mail.activity` reminders and the mobile app; a native list export keeps working with
every column the user has added). The instruction to "take full advantage of custom
OWL where it makes work easier" is best honoured by concentrating that effort on the
one or two screens above where Odoo's stock widgets genuinely fall short, not by
matching the mock's screen count with equivalent bespoke screens.

---

## 4. Configurable-for-both-audiences requirement — what changes between "department" and "office" mode

The prototype and both old-module copies model exactly one context: an **in-house**
legal department serving a fixed group of subsidiary companies against a fixed list
of **government bodies**. Nothing in the artefacts read for this document models a
**law office** (مكتب محاماة) serving external, unrelated clients, billing them, and
tracking conflicts of interest between them — that vocabulary and those screens
belong to the sibling `legal_*` suite (`legal_core`, `legal_contract`, the
Phase-2 engagement/conflict work in `docs/phase-2-engagements-and-conflicts.md`), not
to anything in this prototype. Recorded here because the brief asks the professional
module to be configurable between the two:

- `LegalCompany` in the prototype (and `legal.company` today) already reads fine as
  either "our subsidiary" (department mode) or "our client" (office mode) — the
  field set does not need to fork.
- The **service catalogue** (§5) is entirely department-mode: it is government
  filings a subsidiary owes to the state. A law office's equivalent "service
  catalogue" is its own list of engagement/matter types (litigation, contract
  review, opinion, notarisation instruction…) — structurally the same
  `department → sub-service` shape (§2.2's coverage-matrix model generalises to it
  directly: swap `legal.department` rows for practice-area rows), but the **seed
  data** must differ per mode. This argues for the service/procedure-type model
  from §2.2 being **user-configurable data**, never a hardcoded enum or a hardcoded
  seed list — the one architectural decision this document can state with
  confidence, since it is what makes "configurable between the two" possible at all
  without a second module.
- Billing: the prototype's `expenses_amount` is a single float per task (money the
  department spent on government fees, reimbursed internally). A law office needs
  actual **billing to a client** — timesheets, fee notes, invoices. That is
  `account`-integration work the current module's `account_move_id`/
  `account_payment_id` fields already point toward (confirmed present, §1 above,
  independently confirmed as the right direction by `sag-legal-module.md` idea 3),
  but the prototype offers no further evidence on it — this needs its own research
  pass against the `legal_*` suite's contract/billing models, out of scope here.

---

## 5. Service / transaction catalogue (reusable seed-data table)

The prototype's `DEPARTMENT_METAS` (10 rows) × `OFFICIAL_SUB_SERVICES` (28 rows,
`initialData.ts`/`types.ts`) is Iraqi-government-specific content, independent of any
UI decision above. It is real domain knowledge worth carrying into the rebuild as
**seed data for the department/service model from §2.2**, not as a Selection field.
أ/ب/ت… are Arabic ordinal letters (a/b/c/d/e…), the prototype's own numbering scheme
for sub-services within a department.

| # | Ministry / body (اسم الوزارة أو الهيئة) | Sub-service code | Sub-service (الخدمة الفرعية) |
|---|---|---|---|
| 1 | الهيئة العامة للاتصالات — Communications & Media Commission (domain/.iq registration, P.O. Box, telecom licensing) | أ | حجز نطاق أو تجديد (domain reservation/renewal) |
| 1 | " | ب | صندوق البريد / تجديد (P.O. Box / renewal) |
| 2 | الماء والكهرباء — Public Utilities (subscription transfer, service clearance, meter settlement) | أ | تسوية العدادات والاشتراكات وبراءة الذمة للماء والكهرباء |
| 3 | دائرة تسجيل الشركات — Companies Registrar (articles of association, annual accounts, legal verification) | أ | تصديق أوليات الشركات من دائرة مسجل الشركات |
| 3 | " | ب | تقديم الحسابات الختامية إلى دائرة مسجل الشركات |
| 3 | " | ت | دفع الرسوم وتقديم الطلبات |
| 3 | " | ث | صحة صدور الأوليات |
| 4 | الهيئة العامة للضرائب — General Commission for Taxes (annual tax assessment, clearance, payroll deduction) | أ | التحاسب الضريبي للشركات |
| 4 | " | ب | تقديم الحسابات الضريبية |
| 4 | " | ت | براءة ذمة للشركات |
| 4 | " | ث | صحة صدور كتب براءة الذمة |
| 4 | " | ج | التحاسب على رواتب مدير الفرع للشركات الأجنبية |
| 4 | " | د | تجديد هويات الشركات |
| 5 | دائرة المرور العامة — General Traffic Directorate (fleet registration, entry badges, POA verification) | أ | تجديد السنويات للشركات (باسم المدير المفوض) |
| 5 | " | ب | إصدار باجات جديدة للشركات (باسم المدير المفوض) |
| 5 | " | ت | صحة صدور وكالات وأوراق الشركة |
| 6 | دائرة الضمان الاجتماعي — Social Security & Labor Dept (contributions, inspection, hiring/resignation) | أ | تسديد اشتراكات الضمان للشركات المشمولة |
| 6 | " | ب | التقارير التفتيشية للشركات |
| 6 | " | ت | براءة ذمة الشركات |
| 6 | " | ث | استقالة وتعيين الموظفين |
| 7 | الشركة العامة للمعارض والخدمات التجارية — Iraqi Fairs & Commercial Services (import licensing, Chamber of Commerce) | أ | تجديد هويات الشركات من غرفة التجارة |
| 7 | " | ب | إجازات الاستيراد للشركات من مسجل الشركات |
| 8 | اتحاد الناقلين — Iraqi Transporters Union (transport company licences) | أ | تجديد هويات شركات النقل |
| 9 | دائرة كتاب العدول — Notary Public (POA notarisation, formal notices, agent revocation) | أ | وكالات للسواق والمحامين والموظفين |
| 9 | " | ب | تصديق الوكالات |
| 9 | " | ت | صحة صدور الوكالات |
| 9 | " | ث | إنذار وعزل الوكالات |
| 10 | التحاسب الضريبي الشخصي للمدير المفوض — Managing Director Personal Tax Audit | أ | التحاسب الضريبي الشخصي وبراءة الذمة للمدير المفوض |

Notes for whoever seeds this data:

- Counts: **10 ministries, 28 sub-services** (the task brief's "24-service matrix"
  undercounts by 4 — the actual `OFFICIAL_SUB_SERVICES` array in `types.ts` has 28
  entries; screenshot `03-company-dossier-24-service-matrix.png`'s filename is the
  mock author's own label, not a verified count).
- Every department also needs the fields SAG's production `legal.department`
  already carries (`contact_person`, `phone`, `address`) — the prototype has none of
  these per-service, only per-department tooltips (`tooltipAr`/`tooltipEn`), which
  are reasonable `help=` text on the department/service record, not a feature.
  Iraq is `Asia/Baghdad`; nothing in this catalogue is currency- or timezone-bearing
  itself, but any SLA/working-days computation built on top of it (§2.6) must use
  the department's real business hours, not a flat integer.
- This table is **department-mode** seed data. A law-office deployment of the same
  module needs an equivalent table of matter/engagement types — not recovered from
  this prototype (see §4) — before the "configurable between the two" requirement
  can be fully seeded.

---

## 6. Summary verdict table

| Verdict | Count | Representative items |
|---|---|---|
| **Use standard Odoo feature** | 16 | search facets/chips/counter, footer sums, row decorations, statusbar, chatter, activities, tracking-as-audit-log, kanban board, calendar view, list export, mail notifications, cron "run now", apps launcher, i18n/RTL, QWeb printing pipeline, native camera/barcode scanner |
| **Build natively** (ORM + views/wizards, no bespoke JS) | 9 | coverage SQL view + department/service child model, due-date filter set incl. "no date", impact-classification filters, bulk-transition server action, SLA-days-per-department config (replacing the "AI" due-date dict), document-requirement child model + its settings screen, lawyer-action-step child model, letterhead/signature config fields, QR label report reusing the existing barcode controller |
| **Build with custom OWL** | 1–2 | the KPI dashboard tiles (already exists — extend, don't rewrite); possibly the coverage matrix's grouped-accordion presentation, only if the native grouped list proves insufficient |
| **Drop** | 10 | fabricated charts, inline state `<select>` on rows/cards, job-title-substring role assignment, global parallel audit-log model, email-notification log screen, QWeb live-preview editor (replace with plain config fields), client-side OCR/scan-filters/rotate, AI legal-assistant chat, module source explorer, browser push notifications, apps-launcher clone, standalone XLSX-export screen |

The pattern across all eighteen features is consistent: **the prototype is a
faithful, over-engineered simulation of capabilities Odoo already ships natively**
(search, chatter, activities, tracking, export, print, i18n, barcode scanning), plus
**two genuinely new product ideas** the current module does not yet have (the
service-coverage matrix showing what was never filed, and the paper-file QR bridge),
plus **a handful of anti-patterns to actively avoid** (fabricated analytics,
role-by-substring, bypassing the state machine, a parallel audit log). A professional
rebuild's job is almost entirely subtraction and reuse, concentrated new effort on
the coverage model and the QR bridge, and — per the ease-of-use brief — arranging all
of the "use standard Odoo feature" items behind the simplest possible surface
(progressive disclosure: the direct action visible, the advanced filter/config one
click away), which is a screen-hierarchy and interaction-design question for the next
document in this research series, not this one.
