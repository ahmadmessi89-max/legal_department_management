# 06 — What the owner's legal suite can donate to `legal_department_management`

**Date:** 2026-09-24 · **Mode:** read-only research. No code in the repository was changed; this file is the only output.
**Question:** which parts of the owner's own `legal_*` suite (everything in `custom_addons/legal_*` except
`legal_department_management`) should be ported into the professional `legal_department_management` (LDM), how, how
much to simplify them, and in what order. LDM must stay **one self-contained module** that depends on no `legal_*`
module and upgrades in place over SAG Group's production data.

**Sources read:** `docs/PROGRESS.md`, `docs/legal-product-roadmap.md`, `docs/phase-2-engagements-and-conflicts.md`,
`docs/research/ux-patterns.md`, `docs/mock-adoption-plan.md`, `docs/external-review/sag-legal-module.md`,
`docs/ui-audit/AUDIT.md` §0 and §3.4, `docs/ui-audit/MY_OFFICE_REDESIGN.md` §1–3, `docs/ui-audit-3/audit3.py`,
`.claude/skills/legal-suite-conventions/SKILL.md`, every donor manifest, the models, wizards, security, data and
`static/src` listed below, the LDM source (`ccebae7`), and the baseline screenshots `docs/ldm/evidence/00-baseline/`.
Sizes are line counts measured on disk on 2026-09-24. Test counts are `def test_` counts. The claim that the suite is
green (0 failed, 0 errors of 249) comes from PROGRESS session 5 and **was not re-run for this document**.

---

## 0. The answer on one screen

The suite is large (≈27.8k lines of Python, 24k of XML, 3k of JS, 4.5k of SCSS, 249 Python tests plus 25 hoot tests,
complete Arabic catalogues) and much of it is well built. It was built as a **configurable engine for consultants**,
though, and the owner now wants **the easiest possible product**. So the rule for LDM is:
**port the foundations and the proven behaviours, and re-implement the heavy engines as small, direct versions.**

**Port nearly as-is (renamed into LDM):**
1. The **five-role security ladder** with a read-only auditor, the Odoo 19 `res.groups.privilege` wiring, and the
   **Settings switch** (`implied_group`) that becomes LDM's in-house/law-office mode.
2. The **working-calendar deadline arithmetic** (`legal.gov.body._plan_days` on a real `resource.calendar`, Sunday to
   Thursday plus Iraqi holidays) and the **expiry mixin** (`start_by_date`, the notice ladder, a gate that reads the
   clock live).
3. The **editable register numbering** (`legal.sequence.mixin`, a port of `account`'s `sequence.mixin`) and the
   **صادر/وارد register** rules: void, never delete; lock once registered; the reply clock; the official letter.
4. **Powers of attorney** (`legal.poa`): who may act, at which bodies, until when, and revocation as a state.
5. **Iraqi court remedies as data** (`legal.appeal.rule`), **corrected** against the Civil Procedure Code text (§3.B4:
   three periods are missing and one help text is legally wrong), plus the 18 governorates and the court ladder.
6. The **union deadline board** (`legal.deadline`, a read-only SQL view over every clock) and the **approval queue**
   (the same idiom).
7. The **intake wizard that previews** what a filing needs before anything is created.
8. The **OWL architecture and components** that proved themselves: server-composed payloads, the phase rail, the
   document checklist, the clock badge, the QR scan screen, and the My Office work queue, agenda and search. Take these
   from **HEAD**, not from the other stream's uncommitted working tree.
9. The **design tokens** (`legal_ds.scss`, `legal_native.scss`, the Tajawal font file), the **test fixtures and
   auditor tests**, and the **Playwright harness lessons**.

**Re-implement smaller:** the procedure engine (10.7k lines: procedure types, phases, steps, transitions, capture fields,
versioning) becomes **configurable stages plus a checklist template per matter type**. Lawsuits, hearings and
judgments become a **court tab on `legal.task`**. Contracts (11 states), requests (11 states) and opinions (7 states)
each shrink to **four or five states**. The two duplicated recurring-obligation generators become **one**.

**Do not copy:** the full procedure engine in v1; `legal_dashboard.py`'s soft-dependency probing; the three older OWL
desks (mail room, body desk, legacy desk) with their KPI tiles; the 92-item menu tree; the content packs as upgrade
data (they would crash SAG's upgrade on its own unique-name constraint, §3.B5); the demo module's writes to
company currency and to admin; a separate `legal.court` model (SAG already records courts as departments under
مجلس القضاء الأعلى); a second "entity" model beside `legal.company`.

---

## 1. Constraints that shape every port

| # | Constraint | Consequence for porting |
|---|---|---|
| C1 | **LDM must not depend on any `legal_*` module.** | Every `from odoo.addons.legal_core...` import is relocated into LDM (for example `legal_engine.py`). Every `legal_core.group_*` / `legal_procedure.*` xmlid is rewritten to `legal_department_management.*`. |
| C2 | **Model-name collision.** The suite already defines `legal.poa`, `legal.correspondence`, `legal.hearing`, `legal.deadline` and others. Two installed modules that declare the same `_name` without `_inherit` get their classes merged, and the result breaks unpredictably. | Declare co-installation unsupported: add `'excludes': ['legal_core']` to the LDM manifest. Odoo 19 enforces it in `ir.module.module.button_install` (`odoo/addons/base/models/ir_module.py:441`). Then new LDM models may keep the suite's `legal.*` names, which keeps port diffs small. Use distinct **browser registry keys** anyway (`ldm_phase_rail`, not `legal_phase_rail`) and a distinct CSS scope class (`o_ldm_view`). Both are cheap insurance. |
| C3 | **The SAG compatibility surface.** SAG runs 19.0.6.3.0 in production (≈10 ministries, 23 departments, 2 client companies, 11 matters). | Keep `legal.task`, `legal.company`, `legal.ministry`, `legal.department`, their stored fields, the xmlids `group_legal_user` / `group_legal_manager`, the actions, the `legal_dashboard_tag` client-action tag, the `legal.task` sequence and the three report xmlids. Changing a field's meaning needs a migration script in `migrations/19.0.7.0.0/`. |
| C4 | **SAG's data will collide with seed data.** `legal.ministry._check_unique_name` and `legal.department._check_unique_department` raise `ValidationError` on a case-insensitive duplicate name. | Iraqi reference data (bodies, courts) **cannot** ship as ordinary module data: the upgrade would fail the first time a shipped "وزارة التجارة" meets SAG's own. Ship it as an **opt-in import** ("load the Iraqi reference library") that merges by code and then by normalised name. |
| C5 | **Arabic-first, English must also work.** SAG's source strings are hard-coded Arabic, including emoji. | Adopt the suite's convention: English source strings plus `i18n/ar.po` generated with `odoo-bin i18n export`. Converting SAG's Arabic literals to English source is a translation migration: after upgrade, `ar_001` users must still see the same Arabic, so ship the `ar.po` in the same release and verify on screen. |
| C6 | **Production safety.** SAG runs Accounting, HR, Sales, POS and more. | Never write `res.company.currency_id`, never change `base.IQD` rounding, never add users to groups, and never load demo data outside the manifest's `demo` key. See §4 N6. |
| C7 | **Licence.** LDM is LGPL-3, authored by SAG Group and deployed at a third party. | The owner's suite is LGPL-3 and his own, so porting it is clean. Do **not** bring in AGPL code (for example OCA `agreement`). The owner's "licence is no obstacle" rule covers ANU's internal modules; LDM is distributed to SAG, so that rule does not apply here. |
| C8 | **Available dependencies.** LDM depends on `base, mail, hr, account`. `hr` brings `resource_mail → resource`; `account` brings `analytic` and `portal` (`odoo-19.0/addons/account/__manifest__.py:17`). | Working calendars, analytic lines, invoices and the portal are available **with no new dependency**. Declare `resource` explicitly anyway. Never add `project` or `hr_timesheet` (roadmap §4). |

---

## 2. Donor inventory

Priority key: **P0** = foundation that must land before feature work · **P1** = first professional release (the daily
work of both audiences) · **P2** = second wave, or kept behind "advanced" disclosure · **P3** = office-mode money and
portal, or niche · **NO** = do not port.
Port modes: **Copy** = code nearly verbatim, renamed · **Adapt** = same behaviour, reshaped onto LDM models ·
**Re-implement** = keep the idea, write a much smaller version · **Data** = records only · **Pattern** = a convention
or technique, not code.

| # | Donor | Main path(s) | Size | Maturity | Mode | LDM target | Pri |
|---|---|---|---|---|---|---|---|
| A1 | Five roles + auditor + privilege | `legal_core/security/legal_core_security.xml`, `*/security/ir.model.access.csv` | 89 + ACL rows | Live-verified; 0 auditor mutation affordances on 33 screens (session 4 audit) | Adapt | groups on the SAG xmlids + 3 new ones | **P0** |
| A2 | Mode switch (`group_legal_firm`) | `legal_core/models/res_config_settings.py`, `legal_core_security.xml:41` | 36 | Verified both ways (menus 13 ↔ 12) | Copy | in-house / office setting | **P0** |
| A3 | Engine guard (write-guard marker) | `legal_core/models/legal_engine.py` | 38 | Verified: a spoofed context is still blocked | Copy | `models/legal_engine.py` | **P0** |
| A4 | Working-calendar arithmetic | `legal_core/models/legal_gov_body.py:222-234` (`_plan_days`) | 8 lines + calendar field | Used by every clock; tested via procedure tests | Adapt | `legal.department._plan_days` | **P0** |
| A5 | Iraqi working calendar + holidays | `legal_iq_*/data/*_calendar.xml` (×5) | 1 calendar + 11 leaves each | Data; Eid dates are **estimates** for 2026 only | Data (opt-in) | one shared calendar | **P0** |
| A6 | Expiry mixin | `legal_core/models/legal_expiry_mixin.py` | 158 | Used by POA, documents; tested indirectly | Copy | `legal.expiry.mixin` | **P1** |
| A7 | Editable register numbering | `legal_correspondence/models/legal_sequence_mixin.py` | 403 | 4 dedicated tests (typed number continues the chain, year reset…) | Copy | numbering for صادر/وارد | **P1** |
| B1 | Government-body features | `legal_core/models/legal_gov_body.py` | 234 | Mature, well documented | Adapt | fields on `legal.ministry` / `legal.department` | **P1** |
| B2 | Jurisdictions + 18 governorates | `legal_core/models/legal_jurisdiction.py`, `legal_litigation/data/legal_court_data.xml` | 55 + 18 records | Data | Re-implement (a governorate field) | `legal.department.governorate` | **P2** |
| B3 | Court ladder + court list | `legal_litigation/models/legal_court.py`, court data | 137 + 16 courts | Tested (a court cannot be its own appeal court) | Re-implement | court fields on `legal.department` | **P1** |
| B4 | Appeal-window rules | `legal_litigation/models/legal_appeal_rule.py`, `data/legal_appeal_rule_data.xml` | 148 + 5 rules | 3 tests; every rule shipped `stale`; **incomplete** | Copy + correct | `legal.appeal.rule` | **P1** |
| B5 | Iraqi content packs | `legal_iq_registrar/tax/chamber/social_security/residency` | 38 bodies, 67 doc types, 23 procedures, 17 obligations, 24 fee rules, 123 steps | 35 verified / 8 stale / 1 not researched; a pack-purity test | Data (opt-in import only) | reference library | **P2** |
| B6 | Legal forms + identifier kinds | `legal_core/models/legal_entity.py` (forms, identifiers), `legal_document_kind_data.xml` | 290 | Mature | Adapt | `legal.company` identifiers tab | **P2** |
| C1 | Procedure engine (`legal.case`) | `legal_procedure/models/*` | 10.7k py | 96 tests; the audit's "exceptionally well-engineered" spine | **Re-implement small** | stages + checklist template on `legal.task` | **P1** (small) / **NO** (full) |
| C2 | Intake wizard with preview | `legal_procedure/wizard/legal_case_intake.py` | 141 + 63 xml | 8 tests; browser-verified clerk/auditor | Adapt | upgrade `legal.task.create.wizard` in place | **P1** |
| C3 | Document checklist | `legal_procedure/models/legal_doc_requirement.py`, `legal_case_document.py` | 209 + 405 | Tested; the blocking reason was fixed for Arabic | Re-implement | `legal.task.document` lines | **P1** |
| C4 | Lawsuits, hearings, judgments | `legal_litigation/models/legal_lawsuit.py`, `legal_hearing.py`, `legal_judgment.py`, `legal_lawsuit_party.py` | 682 + 224 + 388 + 60 | 20 tests | Adapt, collapsed | court tab on `legal.task`, `legal.task.hearing`, `legal.task.judgment` | **P1** |
| C5 | صادر/وارد register + official letter | `legal_correspondence/*` | 2.8k py, 1.6k xml, 216 scss | 19 tests incl. rendering the letter, Hijri, numerals | Adapt, trimmed | `legal.correspondence` | **P1** |
| C6 | Powers of attorney | `legal_procedure/models/legal_poa.py`, `wizard/legal_poa_revoke.py` | 264 + 61 | Used by the litigation filing gate (3 tests) | Copy | `legal.poa` | **P1** |
| C7 | Contracts + obligations | `legal_contract/*` | 1.8k py | 18 tests | Re-implement small | `legal.contract` (5 states) | **P2** |
| C8 | Legal opinions (freeze + supersede) | `legal_opinion/models/legal_opinion.py` | 718 | 17 tests | Adapt, 4 states | `legal.opinion` | **P2** |
| C9 | Internal requests intake | `legal_request/*` | 1.3k py | 20 tests | Re-implement small | `legal.request` (5 states) | **P2** (in-house) |
| C10 | Company document register | `legal_core/models/legal_document.py`, `legal_document_type.py` | 308 + 216 | Confidentiality rule live-verified | Adapt | `legal.company.document` | **P1** |
| C11 | Recurring statutory obligations | `legal_procedure/models/legal_obligation.py` (+ duplicate in `legal_contract/models/legal_contract_obligation.py`) | 532 (+440) | 6 tests; idempotent generator | Re-implement once | `legal.obligation` | **P2** |
| C12 | Fees (quoted vs paid) | `legal_procedure/models/legal_fee.py`, `legal_fee_rule.py` | 106 + 140 | Tested | Adapt + SAG's accounting links | `legal.task.fee` | **P1** |
| C13 | Immutable action log | `legal_procedure/models/legal_action_log.py` | 137 | Write/unlink raise even under sudo | Pattern | chatter tracking is enough in v1 | **P2** |
| C14 | SLA rule + escalation | `legal_procedure/models/legal_sla_rule.py` | 234 | Idempotent by unique index; tested | Re-implement small | target days per stage + one escalation cron | **P2** |
| D1 | Union deadline board | `legal_deadline/models/legal_deadline.py` | 395 | 9 tests; 94–103 live rows | Adapt | `legal.deadline` over LDM's clocks | **P1** |
| D2 | Approval queue | `legal_deadline/models/legal_approval_queue.py` | 169 | 9 tests; the jsonb/translate gotcha found here | Adapt when there is more than one approvable model | `legal.approval.queue` | **P2** |
| D3 | Coverage (what nobody filed) | `legal_procedure/models/legal_entity_coverage.py` | 303 | 9 tests | Defer (needs procedure templates) | — | **P3** |
| D4 | QR file label + scan to open | `legal_procedure/report/legal_case_label.xml`, `static/src/components/scan/` | 71 + 237 | Browser-verified; zero new dependencies | Copy | label on `legal.task` + scan action | **P2** |
| D5 | Printed reports + helpers | `legal_reports/report/*`, `report_models.py` | 462 py + ≈940 xml | 13 tests | Adapt | upgrade SAG's 3 reports; add the register book | **P1** helpers / **P2** extra reports |
| D6 | Analytics + chart wrapper | `legal_office/models/legal_analytics.py`, `legal_procedure/static/src/components/chart/` | 532 + 173 | Tested at HEAD; a validated palette | Adapt | management screen | **P2** |
| E1 | My Office workspace (reference only) | `legal_office/models/legal_office.py`, `static/src/office/*` | HEAD: 1,664 py / 150+180+43 js | 13 tests at HEAD; working tree in flux (+3,576 lines, 23 tests, unverified) | Pattern + Adapt from HEAD | redesign `legal_dashboard_tag` **in place** | **P1** |
| E2 | Field widgets: phase rail, checklist, clock badge | `legal_procedure/static/src/components/{phase_rail,checklist,clock_badge}` | ≈150 + 159 + 110 js each | Rail has hoot tests; all browser-verified | Copy (rename registry keys) | widgets on the matter form | **P1** |
| E3 | Older desks: mail room, body desk, legacy desk, KPI tile, worklist, counter walk | `legal_procedure/static/src/components/*` | ≈1.1k js | Superseded by My Office | **NO** (counter walk P3) | — | NO |
| E4 | Design tokens + native-view skin + font | `legal_office/static/src/scss/legal_ds.scss`, `legal_native.scss`, `legal_procedure/static/src/components/_common/legal_fonts.scss`, `scripts/legal_stamp_view_class.py` | 188 + 145 + 77 + 91 | Verified at 1366 and 1920, RTL | Copy | `static/src/scss/` | **P0** |
| F1 | Engagement + conflicts check (design only) | `docs/phase-2-engagements-and-conflicts.md` | 254-line spec, 10 named tests | **Not built** | Implement from the spec, simplified | office mode | **P2** (conflicts) / **P3** (engagement) |
| F2 | Time, WIP, billing, portal (design only) | roadmap §4–§6 | spec | **Not built** | Implement on `analytic` + `account` | office mode | **P3** |
| G1 | Test fixtures and patterns | `legal_procedure/tests/common.py`, auditor tests, `test_wizards.py`, hoot tests | 153 + … | Green | Pattern + Copy | `tests/` | **P0** |
| G2 | Playwright harnesses | `docs/ui-audit-3/audit3.py`, `menu_map.py`, `scripts/legal_ui_capture.py`, `docs/ldm/tools/capture.py` | 298 + 43 + 184 + ≈70 | Rewritten after an invalid run; lessons recorded | Adapt | `docs/ldm/tools/` | **P0** |
| G3 | Translation workflow + catalogues | `*/i18n/ar.po`, SKILL.md §Translations | 10 catalogues, 0 empty | Verified on screen | Pattern + Data (Arabic terms) | `i18n/ar.po` | **P0** |

---

## 3. Donor cards

Each card gives: what it does · size and maturity · how to port it into one module · how to simplify it · priority.

### A. Foundations

#### A1 — The five-role ladder with a read-only auditor · P0

- **Path:** `custom_addons/legal_core/security/legal_core_security.xml` (groups, the `ir.module.category` and the
  Odoo 19 `res.groups.privilege`), `legal_core/security/legal_core_rules.xml` (company rules, confidentiality), ACL
  rows in each module's `ir.model.access.csv`.
- **What it does:** clerk → officer → approver → manager, chained by `implied_ids`, plus an **auditor** that implies
  only `base.group_user`. Officer also implies `base.group_partner_manager`, because stock internal users cannot create
  contacts and the UAT dead-ended on an empty opposing-party dropdown. Per-body visibility is data (`officer_ids` on
  the body, read by a record rule), never one group per ministry. Separation of duties sits in the server methods
  (for example `legal_litigation`: a clerk cannot close a lawsuit, an approver can).
- **Maturity:** the strongest verified asset in the suite. The session-4 audit found zero auditor mutation affordances
  on 33 auditor screens, and 18/18 live mutation probes were denied (AUDIT §0). SAG's module has **two** groups, both
  able to write, and **no auditor** (external review §5.1).
- **Port:** keep SAG's xmlids so existing users keep working:

  | LDM xmlid | Role | Note |
  |---|---|---|
  | `group_legal_clerk` (new) | كاتب / موظف تسجيل | registers letters, prepares files |
  | `group_legal_user` (**kept**) | محامٍ / مسؤول متابعة (officer) | SAG's current lawyers land here, so they keep every right they have today |
  | `group_legal_approver` (new) | المعتمِد | approves, signs |
  | `group_legal_manager` (**kept**) | المدير القانوني | configures, sees everything |
  | `group_legal_auditor` (new) | مدقق (قراءة فقط) | implies only `base.group_user` |

  Re-create the privilege record the Odoo 19 way (`res.groups.privilege` with `category_id`); `res.groups.category_id`
  no longer exists in 19. Port the ACL shape: auditor rows are `1,0,0,0` everywhere.
- **SAG-specific trap:** `security/legal_security.xml` makes `base.group_system` imply `group_legal_manager`.
  Deleting that XML **does not remove** the implication, because `(4, …)` only ever adds. Remove it explicitly with
  `(3, ref('group_legal_manager'))` or in a migration, then decide how admin gets access: the suite later added admin
  to the manager group with a `<function>` (`legal_iq_demo/data/demo_admin.xml`), but do **not** do that on SAG's
  production database (C6). Also keep SAG's lawyer rule ("companies and matters I am assigned to"): it is the
  confidentiality rule an office needs. Add read-all rules for manager and auditor.
- **Simplify:** hide roles the install does not need. A two-person office is served by `officer` + `manager`; the
  clerk, approver and auditor groups exist but need not be assigned.

#### A2 — The mode switch: in-house department or law office · P0

- **Path:** `legal_core/models/res_config_settings.py` (36 lines), `legal_core_security.xml:41-44`,
  `legal_core/views/res_config_settings_views.xml`.
- **What it does:** a Settings boolean with `implied_group="…group_legal_firm"`, the same idiom as
  `group_project_stages`. It gates **menus and screens only, never data**; roles stay the only fence.
- **Maturity:** shipped and verified both ways. The roadmap §3 table says exactly what differs between the audiences:
  who the work is for, which way money flows, time, the portal, conflicts, and the engagement.
- **Port:** copy verbatim as `group_legal_office_mode`, and add a `res.company.legal_mode` selection only if per-company
  behaviour is needed (roadmap §5 Phase 1). The same switch should also drive **defaults**: a new `legal.company`
  defaults to `relationship='client'` in office mode and `'own'` in in-house mode.
- **Simplify:** one switch, set once during onboarding. Do not scatter mode checks through Python: use groups on menus
  and view fields, and defaults.

#### A3 — The engine guard · P0

- **Path:** `legal_core/models/legal_engine.py` (38 lines).
- **What it does:** a thread-local, depth-counted marker (`engine_guard()` / `in_engine()`) that lets engine methods
  write protected fields (stage, register number, frozen text) while every RPC write is refused. It replaced a
  context-flag guard that any client could forge (`PROGRESS` P0, commit `b2c71f9`, "clerk with spoofed context still
  blocked").
- **Port:** copy verbatim. Use it wherever LDM needs a field only the workflow may move: `state`/`approval_state` once
  approval becomes a real separation of duties, the register number once registered, and the frozen opinion text.
- **Priority:** P0. SAG's `legal.task` exposes `action_approve` to every `group_legal_user` today, and the new
  approver role is meaningless without this guard.

#### A4 + A5 — Working-day deadlines on an Iraqi calendar · P0

- **Path:** `legal_core/models/legal_gov_body.py:156-162,222-234` (`resource_calendar_id`, `_plan_days`);
  calendars in `legal_iq_registrar/data/registrar_calendar.xml` and its four siblings.
- **What it does:** `_plan_days(days, from_dt)` plans N working days through the body's calendar, falling back to the
  company calendar and then to plain calendar days. The calendar is Sunday–Thursday, 08:30–14:15, `Asia/Baghdad`,
  with 11 holiday leaves (New Year, Army Day, Eid al-Fitr, Nowruz, Labour Day, Eid al-Adha…).
- **Maturity:** used by every SLA, reply and dashboard clock in the suite, and tested through them. The **holiday data
  is year-bound**: the Islamic dates are astronomical estimates for 2026 and the file comments say so. The same
  eleven leaves are copied into five calendars so that each pack stays independent.
- **Port:** add `resource_calendar_id` to `legal.department` with a fallback to `legal.ministry` and then to the
  company, and copy `_plan_days`. Ship **one** calendar, "الدوام الرسمي العراقي", as `noupdate` data (it has no name
  constraint, so it cannot collide with SAG's data), and let a department override it only when its hours differ.
- **Simplify:** one national calendar, not five. Add a manager-facing **"holidays for next year" reminder** (an
  activity in December), because the Eid dates are announced by moon sighting and must be corrected every year.
- **Why it matters:** SAG's module has "no SLA engine and no working calendars" (external review §5.3). Its cron
  counts calendar days, so every weekend produces false alarms.

#### A6 — Expiry mixin · P1

- **Path:** `legal_core/models/legal_expiry_mixin.py` (158 lines).
- **What it does:** `expiry_date`, `notice_days`, `renewal_lead_days`, a stored `start_by_date` (expiry minus the
  renewal lead time), a stored `expiry_state` (no expiry / valid / due soon / expiring / expired), a searchable
  non-stored `days_to_expiry`, and `_is_expired(on_date)`, which **reads the clock live** so a gate never trusts a
  column that is a day stale. It also has `_is_valid_on(date)` for "must be valid on the tender closing date".
  The daily cron `cron_refresh_expiry_states` refreshes the stored state.
- **Port:** copy as-is. Inherit it on `legal.poa`, `legal.company.document` and `legal.contract`.
- **Simplify:** hide `renewal_lead_days` behind advanced disclosure, defaulting it from the document type.

#### A7 — Editable register numbering · P1

- **Path:** `legal_correspondence/models/legal_sequence_mixin.py` (403 lines).
- **What it does:** a deliberate port of `account`'s `sequence.mixin`. A clerk may **type** the number (a department
  that migrates in October is already at 1,247), and the next number is deduced from the last one. The format
  (`1247`, `2026/1247`, `ق/2026/1247`) and the yearly reset are inferred from the book rather than configured.
  Concurrency is handled by savepoint retries on a unique index.
- **Maturity:** 4 dedicated tests (register prefix and year; reset with the calendar year; a typed number continues
  the chain; a number must agree with its date) plus RPC-lock tests.
- **Port:** copy. LDM already depends on `account`, so it *could* inherit `sequence.mixin` directly. The owner's
  version is simpler (the year-range formats and the cache are removed), is documented, and has tests for this exact
  use, so prefer it.
- **Priority:** P1, together with the صادر/وارد register (C5).

### B. Reference data

#### B1 — Government-body features onto SAG's two-level tree · P1

- **Path:** `legal_core/models/legal_gov_body.py` (234 lines: `legal.gov.body`, `legal.gov.body.type`,
  `legal.gov.body.contact`).
- **What it adds that SAG lacks:** `short_name` (what a clerk actually calls the body); `letterhead_recipient` +
  `salutation` (printed verbatim on a letter); `open_hours`; `channel` (paper, online or both) + `portal_url`; named
  **contacts** (a person, their section, phone, mobile, "answers before eleven"); `officer_ids` (who follows up with
  this body, read by a record rule); the working calendar (A4); `legal_basis`, `last_verified_on` and
  `verification_status`; and a hierarchy with `_parent_store`.
- **Port:** **keep SAG's `legal.ministry` → `legal.department` models.** The external review rejected their tree, but
  it is now the compatibility surface, and for users two levels are easier than an arbitrary tree. Add the fields
  above to `legal.department` (contacts as `legal.department.contact`), inherit ministry-level defaults (calendar,
  salutation), and keep SAG's duplicate-name constraints.
- **Simplify:** the default form shows name, ministry, phone, hours and contacts. Addressee block, salutation,
  channel, portal, officers and provenance go in an "advanced" tab. Replace `legal.gov.body.type` (13 type records)
  with a short `kind` selection (ministry directorate · court · notary · bank · other) that exists mainly to switch on
  the court fields (B3).

#### B3 — Courts: fold them into `legal.department` · P1

- **Path:** `legal_litigation/models/legal_court.py` (137 lines; `degree`, `governorate_id`, `parent_court_id`,
  `gov_body_id`), `legal_litigation/data/legal_court_data.xml` (18 governorates, 3 court-type bodies, 16 courts: the
  Federal Court of Cassation, five federal appeal courts plus Erbil, six first-instance courts, the Employees' Court,
  the Administrative Court and a Labour Court).
- **Key observation from the baseline:** SAG already records courts **as departments under مجلس القضاء الأعلى**. The
  baseline task form (`05_task_form.png`) shows الوزارة = مجلس القضاء الأعلى and الدائرة = محكمة بداءة الكرخ. A
  separate `legal.court` would split one concept in two for SAG's users.
- **Port:** add `court_degree` (Selection: first instance, appeal, cassation, labour, misdemeanour/felony,
  administrative, personal status), `appeal_court_id` (the court above) and `governorate` to `legal.department`,
  visible only when `kind == 'court'`. Keep the test "a court cannot be its own appeal court". Offer the court list
  through the opt-in reference import (C4), never as upgrade data.

#### B4 — Appeal windows as data, corrected against the statute · P1

- **Path:** `legal_litigation/models/legal_appeal_rule.py` (148 lines),
  `legal_litigation/data/legal_appeal_rule_data.xml` (5 rules, all shipped `verification_status = stale`),
  `legal_litigation/models/legal_judgment.py:235-300` (rule match, deadline, days left, window state).
- **What it does:** a rule is matched on remedy × ruling type (judgment or decision) × court degree × jurisdiction,
  and the most specific rule wins. A judgment's `appeal_deadline` is `tabligh_date + days`. The window state lives on
  the deadline board. The periods are data a lawyer can read and correct, with `legal_basis` and a verification flag.
- **Maturity:** 3 tests (the deadline is notification plus the rule; a lapsed window is overdue; lodging a challenge
  stops the clock).
- **Checked against the Civil Procedure Code, Law 83 of 1969** (English translation hosted by the University of
  Zurich, see §7):

  | Remedy | Statute | Shipped? |
  |---|---|---|
  | Objection to an in-absentia judgment (اعتراض على الحكم الغيابي), 10 days | Art. 177(1) | yes, 10 |
  | Appeal (استئناف), 15 days | Art. 187(1) | yes, 15 |
  | Cassation (تمييز) of judgments of appeal and first-instance courts, 30 days | Art. 204 | yes, 30 |
  | Cassation of **magisterial and religious court** judgments, **10 days** | Art. 204 | **missing** |
  | Cassation of the decisions listed in Art. 216 (summary matters, precautionary attachment…), 7 days | Art. 216(1) | yes, 7 |
  | Rectification of a cassation decision (تصحيح القرار التمييزي), **7 days**, never after 6 months, once only | Art. 219–221 | **missing** |
  | Retrial (إعادة المحاكمة), **15 days** from discovering the fraud, forgery or document | Art. 196–198 | **missing** |
  | Counting starts the **day after** notification | Art. 172 | consistent (`tabligh + days`) |
  | Periods are mandatory; a late challenge is dismissed by the court on its own initiative | Art. 171 | consistent (`non_extendable`) |
  | **A period ending on an official holiday extends to the next business day** | **Art. 25(2)** | **not modelled, and the help text contradicts it** |

  The `non_extendable` help text says a period "does not stretch because the office was shut". Art. 25(2) says the
  last day moves to the next business day when it falls on an official holiday. The shipped arithmetic is therefore
  **conservative**: it shows an earlier date, which is safe. The wording is legally wrong, though, and the
  department's real last day is lost. **Port:** show two dates, "الموعد الآمن" (the shipped calendar-day arithmetic)
  and "آخر يوم قانوناً" (rolled forward over the court's calendar holidays per Art. 25(2)). Add the three missing
  rules, fill `legal_basis` with the article numbers, and keep every rule `stale` until the owner's counsel confirms
  it. Secondary English-language guides disagree with the statute (two say appeal is **30** days, citing "Art. 186"),
  which shows why the verification flag must stay visible. The labour-court rule (30 days) has no primary citation in
  the suite; check it against Labour Law 37 of 2015 before relying on it.

#### B5 — Iraqi content packs · P2, opt-in only

- **Path:** `legal_iq_registrar`, `legal_iq_tax`, `legal_iq_chamber`, `legal_iq_social_security`, `legal_iq_residency`.
  Together they ship 38 bodies with sections, 67 document types, 23 procedure types (123 steps, 73 phases,
  30 transitions), 17 recurring obligations, 24 IQD fee rules, 5 calendars and 50 document requirements.
  Provenance flags: 35 `verified`, 8 `stale`, 1 `not_researched`. `test_pack_purity.py` fails the build if a pack
  ever adds a model, a field or Python.
- **Value:** the AUDIT calls the packs "the strongest existing asset". They record which documents the Registrar
  demands, the tax-clearance walk, the monthly social-security day, and residency and work-permit renewals, each with
  a `legal_basis`.
- **Why not ordinary module data:** (1) SAG's unique-name constraints (C4) would abort the upgrade on the first
  duplicate; (2) most of the payload is **procedure-engine configuration** (steps, phases, transitions) that LDM will
  not have in v1; (3) packs are `noupdate`, and the holiday dates inside them expire.
- **Port:** a manager-only wizard, "مكتبة المراجع العراقية", that imports bodies (merged into ministries and
  departments by code, then by normalised Arabic name), document types, recurring obligations and, once C1-small
  exists, a **checklist template** per common filing (for example تأسيس شركة محدودة → the list of required documents).
  The source files can be the pack XML, converted to a JSON library under `data/reference/`. Keep `legal_basis`,
  `last_verified_on` and `verification_status` on every imported row.

#### B6 — Legal forms and identifiers · P2

- **Path:** `legal_core/models/legal_entity.py` (`legal.entity.form` with the Art. 28 minimum capital,
  `legal.entity.identifier` = "our number at that body", unique per entity × body × kind, plus an `identifier_index`
  for search), and `legal_core/data/legal_document_kind_data.xml` (6 forms, 6 identifier kinds: registration, tax
  file, social security, Chamber, Ministry of Planning, KRI UEN).
- **Port:** SAG's `legal.company` already has `company_type` (5 values), `registration_number` and `tax_number`.
  Keep those fields. Add an **identifiers tab** (advanced) and a stored search index so that the matter search finds a
  company by any number a clerk is holding. Do not add `legal.entity.form` as a model: the 5-value selection already
  covers the forms, so add `foreign_branch` details only if SAG needs them.

### C. Work records

#### C1 — The procedure engine → configurable stages plus a checklist template · P1 small / NO full

- **Path:** `legal_procedure/models/legal_case.py` (2,005), `legal_procedure_type.py` (663), `legal_procedure_step.py`
  (314), `legal_procedure_transition.py` (202), `legal_procedure_phase.py` (91), `legal_procedure_field.py` (136),
  `legal_case_check.py` (114), `legal_case_subject.py` (113), `legal_constants.py` (133) plus views and wizards.
  96 tests.
- **What it does:** states are rows (`step_id` → `legal.procedure.step`, `group_expand`), linear advances need no
  transition rows, a return increments a *round* and pauses the SLA, and procedure types are **versioned**
  (`effective_from` / `superseded_by_id`, with a snapshot on each file). `mail.tracking.duration.mixin` +
  `statusbar_duration` measure the time spent at each step, and our days are split from their days
  (`_compute_desk_days`, from the log).
- **Verdict:** excellent engineering, but it is a **consultant's configuration product**. The roadmap §2.3 names it as
  a source of clutter: nine configuration menus for one procedure. SAG's users think in terms of a matter with a
  state, and the owner wants "very direct". Do **not** port it whole in v1.
- **Port the small version:**
  1. `legal.task.stage` (name, sequence, `fold`, `is_closed`, `needs_approval`, `target_days`, `matter_type` scope)
     with `group_expand`, and `stage_id` tracked through `mail.tracking.duration.mixin` + `_track_duration_field`,
     so `statusbar_duration` shows how long a matter sat in each stage. The one mixin-ordering rule to copy: list
     `mail.activity.mixin` and `mail.tracking.duration.mixin` and **do not** name `mail.thread` first (`legal_case.py`
     comment on `_inherit`).
  2. **Keep SAG's `state`** (draft / in progress / pending documents / done / cancelled) as the coarse, compatible
     lifecycle. `stage_id` is the optional finer step for a matter type that has stages configured. This is
     progressive disclosure: an office that never configures stages never sees them.
  3. A **checklist template** per matter type or filing (C3) instead of procedure types + requirements + fields.
  4. From the engine, keep the **write guard** on `stage_id` (A3), the **return-with-reason** idea (one wizard), and
     `_compute_desk_days` (ours / theirs) once the log exists.
- **Leave for later (P3, behind "advanced procedures"):** transitions with group gates, capture fields, versioning,
  rounds, subjects and step checks.

#### C2 — The intake wizard that previews before creating · P1

- **Path:** `legal_procedure/wizard/legal_case_intake.py` (141), `legal_case_intake_views.xml` (63), 8 tests in
  `tests/test_case_intake.py` (plus 7 wizard tests in `test_wizards.py`).
- **What it does:** asks for whom → at which counter → which filing, narrowing at each step, then shows the required
  documents, the expected fees and the service target **before** anything is created. The file is then created
  through ordinary `create`, so every access rule applies. The idea itself came from SAG (review idea 1).
- **Port:** upgrade SAG's `legal.task.create.wizard` **in place** (same xmlid and menu). Keep its company → ministry →
  department order and add the matter type (معاملة حكومية / دعوى / عقد / استشارة), the preview (checklist template,
  fees, target date in working days via A4), and, in office mode, the conflicts check (F1).
- **Gotcha to copy:** the test must call `default_get([...])` and `new({})`, not only `create`. A wizard default
  `_baghdad_year()` with no arguments killed a dialog for three roles while every test stayed green (SKILL.md).

#### C3 — The document checklist on the matter · P1

- **Path:** `legal_procedure/models/legal_doc_requirement.py` (209: `applicability_domain`, `producer_procedure_type_id`),
  `legal_procedure/models/legal_case_document.py` (405: a closed set of seven statuses, freshness versus expiry,
  "pick from the company register", "start the producing procedure").
- **Port:** `legal.task.document` lines (name, document type, status from a **closed** set of 5–7 values, a link to a
  `legal.company.document` register row, expiry, note, attachment) seeded from the checklist template at intake. Keep
  the **"pick from the company register"** action: a valid document is filed once and reused, not uploaded per matter.
  Keep `blocking_reason` as a **non-stored, `depends_context=('lang',)`** compute; a stored one froze in English on an
  Arabic screen (PROGRESS P2 bug).
- **Simplify:** no `applicability_domain` in v1. Show the rows in the checklist widget (E2), which is already written
  to GOV.UK task-list anatomy.

#### C4 — Court cases: lawsuit, parties, hearings, judgments → a court tab on the matter · P1

- **Path:** `legal_litigation/models/legal_lawsuit.py` (682), `legal_lawsuit_party.py` (60), `legal_hearing.py` (224),
  `legal_judgment.py` (388), `wizard/legal_lawsuit_reason.py`; 20 tests.
- **What it does:** parties with roles, `our_capacity`, court case number and year, claim amount, lawyer, external
  counsel, risk; **filing is blocked without a valid litigation POA** (the POA is auto-found when not named); closing
  is a separated duty with a reason; hearings carry purpose, attendance, minutes, result and next step, and setting
  the next date rolls one sitting forward exactly once; judgments carry the notification date (التبليغ), remedy, rule,
  deadline and window state.
- **Port onto SAG's model:** `legal.task` with `matter_type = 'lawsuit'` gets a **court tab** (court = a court-kind
  `legal.department` (B3), court case number/year, our capacity, claim amount, opposing parties as `legal.task.party`,
  POA). Hearings become `legal.task.hearing`. **SAG's `session_date` becomes the stored computed "next hearing"**, and
  a migration turns each existing `session_date` into one hearing row, so SAG's 11 matters keep their dates.
  Judgments become `legal.task.judgment`, with the appeal window from B4.
- **Simplify:** lawsuit states 8 → none of its own (the matter's `state`/`stage_id` is enough; "judgment", "appeal"
  and "enforcement" can be stages of the lawsuit matter type). Hearing purpose and attendance selections stay, but
  with **English source labels and ar.po**, not the suite's bilingual labels "Pleading (مرافعة)". Treat the POA gate
  as a **warning with a one-click fix** by default and a hard block only when the office turns it on. This follows
  the owner's ease-of-use rule and the conventions' lesson that a view-level `required=` froze three of six files.

#### C5 — The صادر/وارد register and the official letter · P1

- **Path:** `legal_correspondence/models/legal_correspondence.py` (1,127), `legal_register.py` (224), `legal_letter_template.py`
  (188), `legal_correspondence_kind.py` (128), `legal_sequence_mixin.py` (A7), `wizard/legal_correspondence_register_wizard.py`,
  `legal_correspondence_void_wizard.py`, `legal_contact_note_wizard.py`, `report/report_official_letter.xml` (210) +
  paperformat (47), `static/src/scss/legal_letter.scss` (216), `res.company` letterhead fields
  (`legal_core/models/res_company.py`), and the signatory (`legal_core/models/legal_signatory.py`). 19 tests.
- **What it does:** the letter exists **before** a file does. `our_number` and `their_number` are separate fields.
  Once registered, number, date, book and direction are locked in `write()` (not only `readonly`), and a registered
  entry is **voided with a reason, never deleted**. The reply clock is `reply_due_on` in the body's working days, and
  `reply_state` is searchable. The numbered subject table (جدول الموضوع) records rows such as eleven engineers in one
  letter. A contact note consumes no number. `write_group_id` on the book: only the register keeper allocates. The
  official letter has the Iraqi letterhead stack, العدد/التاريخ, a QR verification token, Arabic-Indic numerals and
  Hijri as company settings, pre-printed versus plain paper formats, and a frozen snapshot PDF.
- **Port:** a new `legal.correspondence` with `task_id` (optional), `company_id` (the client or own company),
  `department_id` (the body) and two shipped books (صادر and وارد). Keep register-then-lock, void-not-delete, typed
  numbering, the reply clock, the letter report and letter templates (the placeholder vocabulary is fixed and
  **deliberately not QWeb or safe_eval**; keep that security decision).
- **Simplify:** drop `legal.correspondence.kind` (12 kinds) for a short `letter_type` selection. Drop referral fields,
  `outbound_method`/`carried_by`, `round` and the answer thread in v1, keeping only `reply_to_id`. Turn **contact
  notes into a quick "سجل مراجعة" action on the matter** (who we spoke to, what they said, promised date) rather than
  a register row. Signatories with specimen signature and seal images are P2; if ported, **port their company rule
  too**, which closed a real cross-company leak (`legal_core_rules.xml:38-50`).
- **Gotchas carried:** `sanitize=False` on `body_html` is deliberate and depends on the letter being composed from
  templates. Review that decision again before letting clerks paste HTML. A QR verification token must be
  unguessable (`uuid`).

#### C6 — Powers of attorney · P1

- **Path:** `legal_procedure/models/legal_poa.py` (264), `wizard/legal_poa_revoke.py` (61), `views/legal_poa_views.xml`
  (215).
- **What it does:** a POA is checkable in three dimensions: **who** (agent partner or user, advocate flag, Bar
  Association branch and registration number), **where** (`body_ids`; empty means a general deed) and **when**
  (the expiry mixin). Its scope is general, specific or litigation, and `scope_note` keeps the deed's exact words.
  Revocation is a terminal state with a date and reason, never an archive. It links to the scan in the company
  register.
- **Port:** copy as `legal.poa` with `entity_id` → `company_id` (`legal.company`) and `body_ids` →
  `legal.department`. It is P1 for **both** audiences: the in-house department needs the وكالة of the مراجع
  (company representative); the office needs the وكالة بالمرافعة to be accepted in court.
- **Simplify:** states 4 → 3 (active / revoked / expired, computed from dates). Put the Bar fields under
  advanced disclosure; they appear only when "advocate" is ticked.

#### C7 — Contracts · P2

- **Path:** `legal_contract/models/legal_contract.py` (626; `legal.contract.party` with roles, 11-state lifecycle,
  internal approval, `counterparty_id`, value/current value, auto-renew, notice period, governing law, risk, signature
  status, signed document), `legal_contract_obligation.py` (440, recurring obligations + instances),
  `legal_contract_modification.py` (102), `wizard/legal_contract_sign.py` (94); 18 tests.
- **Port:** an in-house department reviews contracts every week; an office drafts and reviews them for clients. Port a
  **5-state** `legal.contract`: received/in review → internal approval → signed/in force → expired/terminated →
  closed. Keep parties with roles, value, dates, notice, auto-renew, the signed-document link, the expiry mixin (A6),
  and **approval through the approver role** (A1).
- **Simplify:** merge contract obligations into the single obligation model (C11). Modifications become chatter plus
  an attachment in v1. **Note for the conflicts check:** the counterparty field is `counterparty_id`;
  `legal.contract.partner_id` does not exist (Phase 2 doc §1). Keep that name, or the conflicts search silently
  matches nothing.

#### C8 — Legal opinions (رأي قانوني) · P2

- **Path:** `legal_opinion/models/legal_opinion.py` (718); 17 tests.
- **What it does:** on issue, the `_FROZEN_FIELDS` (subject, question, background, legal basis, analysis, conclusion)
  are frozen into a snapshot and an outgoing register number is booked in the same step. A change is made by drafting
  a **revision that supersedes** the opinion, never by reopening it. The result is a searchable precedent library.
- **Port:** P2 for in-house (فتاوى / آراء قانونية requested by other departments) and useful for offices (advice to
  clients). States 7 → 4: draft → review → issued → superseded. Keep the freeze and supersession exactly. Book the
  register number only when the صادر register (C5) is enabled.

#### C9 — Internal requests to the legal department · P2 (in-house mode)

- **Path:** `legal_request/models/legal_request.py` (794), `legal_request_category.py` (68, 10 categories), 3 wizards;
  20 tests.
- **What it does:** the front door for the rest of the company. A request exists before any file does; triage and
  assignment are an officer's job and approval an approver's; `action_convert` turns it into a letter, a document,
  or later a matter; `target_response_date`, age and overdue flags.
- **Port:** in in-house mode, any employee submits a request (`group_legal_requester`, implied by `base.group_user`,
  own-records rule), and the legal team converts it into a `legal.task`, a contract review or an opinion.
- **Simplify:** 11 states → 5 (submitted → assigned → in progress → answered → closed/cancelled). Waiting-on is a
  flag, not two states. Keep the tests' shape: auditor read-only, clerk cannot triage, officer cannot approve, a
  numbered request cannot be deleted.

#### C10 — The company's permanent document register · P1

- **Path:** `legal_core/models/legal_document.py` (308) + `legal_document_type.py` (216; validity model, freshness,
  notice, renewal lead, certified/notarised/legalised/translated flags, grades, `is_per_subject`,
  `company_register`), `legal_core_rules.xml:62-86` (confidential documents: manager, auditor and the issuing body's
  officers only).
- **Why P1:** SAG's `legal.company.attachment_ids` is a bare many2many of files. A company's registration
  certificate, tax clearance (براءة ذمة), Chamber ID and POAs **expire**, and expiry is the most common thing a legal
  department is chased for. The deadline board (D1) and the checklist (C3) both read this register.
- **Port:** `legal.company.document` (type, number, issuing department, issue date, expiry via A6, state,
  supersedes/superseded, scans, confidential) plus a small `legal.document.type`. Keep the confidentiality rule and
  keep `entity_id` as `ondelete='restrict'`: the register is permanent (PROGRESS P0 fix).
- **Simplify:** drop licence grades, `is_per_subject` and the four certification flags from the default form.

#### C11 — Recurring statutory obligations · P2

- **Path:** `legal_procedure/models/legal_obligation.py` (532: four shapes: a fixed annual date, an offset from the
  financial year end, monthly, an offset before an expiry; a 12-month generation horizon; an idempotent
  `_cron_generate`; `_cron_mark_late`), duplicated in `legal_contract/models/legal_contract_obligation.py` (440).
- **Port once:** one `legal.obligation` (a schedule on a company or a contract) plus `legal.obligation.period`
  (instance), with one generator and one late-marking cron. It feeds the deadline board. The Iraqi schedules
  (corporate tax return on 31 May federally and 30 June in the Region; monthly social-security contribution;
  annual Chamber ID renewal…) arrive through the reference import (B5).

#### C12 — Fees: quoted versus paid, linked to accounting · P1

- **Path:** `legal_procedure/models/legal_fee.py` (106; quoted `amount`, `amount_paid`, stored `variance`, `state`
  due/paid/waived, receipt number in the search index, paid by/on), `legal_fee_rule.py` (140).
- **Port:** SAG's `legal.task` has one `expenses_amount` Float plus `account_move_id`, `account_payment_id` and
  `expense_account_id`, which are real links to Odoo Accounting and were confirmed as the right direction by both
  reviews. Add `legal.task.fee` lines (name, quoted, paid, receipt number, state, paid on/by, receipt scan, **optional
  move/payment link per line**) and make `expenses_amount` a stored compute of the paid lines. The migration creates
  one fee line from each existing non-zero `expenses_amount`. Use **Monetary** in the company currency, IQD at SAG
  (C6), instead of SAG's Float labelled "(د.ع)".
- **Simplify:** no fee-rule table in v1; expected fees come from the checklist template in the intake preview.

#### C13 + C14 — Action log and SLA escalation · P2

- **Paths:** `legal_procedure/models/legal_action_log.py` (137: append-only; `write`/`unlink` raise even under sudo;
  no ACL grants create; denormalised snapshots); `legal_procedure/models/legal_sla_rule.py` (234: a rule per
  procedure, step and company; `legal.sla.escalation` made idempotent by a unique index on case × step × round ×
  level).
- **Port:** v1 uses `tracking=True` + `statusbar_duration`, which is enough for "who moved what, when" at SAG's
  volume. Add the immutable log when approvals and returns carry legal weight (P2). The escalation becomes one daily
  cron that raises an activity for the manager when a stage exceeds `target_days` **in working days**, deduplicated
  by a unique index as in the suite. It replaces SAG's calendar-day cron (`_cron_check_upcoming_sessions`).

### D. Cross-cutting surfaces

#### D1 — One board for every date (المواعيد) · P1

- **Path:** `legal_deadline/models/legal_deadline.py` (395), views (129); 9 tests (the view materialises; a discharged
  period leaves the board; open-origin points at the source; auditor read-only; company scoping).
- **What it does:** a `_auto = False` SQL view that UNIONs 11 clocks. Each arm has a literal source index for a stable
  id and projects `company_id` so the ordinary rule fences it; `_depends` flushes before reads; it gets native
  list/calendar/graph views and an "open the source" button. It replaced nine filter-menus (mock-adoption §4.1).
- **Port:** the same idiom over LDM's clocks: matter due date, next hearing, appeal window (B4), POA expiry,
  company-document expiry, contract expiry/notice, correspondence reply due, obligation periods and request target.
  Add each arm as its model lands.
- **Gotchas to carry (SKILL.md):** a translatable source column is `jsonb`, so the view field must be
  `translate=True`, and all union arms must agree on the column type. The kanban-card crash
  (`this.child.mount is not a function`) came from exactly this. Every field a kanban reads must be declared.

#### D2 — Approval queue · P2

- **Path:** `legal_deadline/models/legal_approval_queue.py` (169); 9 tests.
- **Port:** SAG already has `approval_state` on `legal.task` and a menu "معاملات بانتظار الاعتماد". Keep that action
  for v1. When contracts, opinions and requests also carry approvals, port the union view. The queue **never
  mutates**: its button opens the record so the record's own guards apply.

#### D3 — Coverage: the filings nobody started · P3

- **Path:** `legal_procedure/models/legal_entity_coverage.py` (303, a cross join of entity × effective procedure types
  with a LATERAL join to the file); 9 tests.
- **Port:** only after checklist templates (C1-small) exist per body. Rewrite the cross join over
  `legal.company × legal.task.template`. It answers "which statutory filings has this client never started" and is
  the mock's flagship idea, but it depends on configuration that v1 will not have.

#### D4 — QR file label and scan-to-open · P2

- **Path:** `legal_procedure/report/legal_case_label.xml` (71) + `static/src/report/legal_case_label.scss` (84);
  `legal_procedure/static/src/components/scan/legal_scan.{js,xml,scss}` (149 + 40 + 48).
- **What it does:** prints a folder-cover label with the QR and the number under it, and opens a file by scanning the
  code or typing the number. It uses **zero new dependencies**: web core ships a ZXing scanner
  (`@web/core/barcode/barcode_dialog`, verified at `odoo-19.0/addons/web/static/src/core/barcode/`), and
  `/report/barcode/QR/…` generates the code. The lookup is an ordinary search as the current user, so a scan can never
  reveal a hidden record. The screen does not auto-start the camera, because on a desktop that would put a modal over
  the one input that always works.
- **Port:** copy with `legal.task` as the target. Low effort and high value for paper-first Iraqi offices.

#### D5 — Printed outputs · P1 helpers, P2 extra reports

- **Path:** `legal_reports/report/report_models.py` (462: Baghdad timezone, Arabic-Indic numerals per company, Hijri
  on demand, **closed Arabic label maps** so the printed page is Arabic whatever the session language),
  `report_case_followup.xml` (197: the استمارة متابعة a runner carries, with six ruled rows whose columns are the
  fields of a contact note), `report_case_cover.xml`, `report_lawsuit_status.xml`, `report_contract_summary.xml`,
  `report_register_book.xml` + wizard, `report/legal_reports_paperformat.xml`, `static/src/scss/legal_reports_print.scss`
  (199); 13 tests.
- **Port:** SAG ships three reports (company file, general oversight, per-matter form). **Upgrade them in place**,
  keeping their xmlids, with the helpers (Baghdad dates, numerals, Hijri), the ruled follow-up rows, and the print
  stylesheet with Tajawal. Add the register book (P2, needs C5) and a lawsuit status report (P2).
- **Gotcha:** wkhtmltopdf finds fonts through the server's fontconfig, not the browser, so Arabic PDFs need the font
  installed on the server (`legal_fonts.scss` comment). Verify PDFs on SAG's host, not only locally.

#### D6 — Management analytics · P2

- **Path:** `legal_office/models/legal_analytics.py` (532; 14 panels, each stating its management question, each
  figure drilling through, "nothing invented"), `legal_office/static/src/analytics/*` (212 js + 152 xml + 212 scss),
  `legal_procedure/static/src/components/chart/legal_chart.js` (157: loads Chart.js lazily from `web.chartjs_lib`,
  destroys the canvas safely, takes theme colours from Odoo, **fixes RTL legends and tooltips**).
- **Port:** P2, a manager-only screen. Copy the chart wrapper and a validated palette (MY_OFFICE_REDESIGN §7: two
  series maximum; amber fails 3:1 on white). The baseline showcase dashboard's KPI wall must not come back (§4 N8).

### E. OWL and design

#### E1 — My Office (مكتبي) as the model for LDM's workspace · P1 (patterns; read-only reference)

- **Path:** `legal_office/models/legal_office.py`, `static/src/office/{legal_office,work_queue,agenda,secondary}.{js,xml}`,
  `legal_office.scss`. **At HEAD:** model 1,664 lines, JS 150/180/43, SCSS 792, 13 tests. **In the working tree
  (another stream, uncommitted, unverified):** model 2,526, `legal_office.js` 370, new `legal_icon.js` (inline
  Phosphor Duotone paths, MIT licence in `static/lib/phosphor/LICENSE`) and `legal_search_utils.js` (Arabic
  normalisation: alef forms, taa marbuta, alef maqsura, tashkeel, Arabic-Indic and Persian digits, and article
  stripping), 23 tests. **Do not edit it and do not copy from the working tree until that stream commits and verifies.**
- **What is worth taking:** (1) **one server round trip composes the whole screen through the ORM as the reader**,
  with no sudo, so record rules and the auditor's read-only access apply automatically; (2) a **work queue across
  registers** where every row carries a server-written **reason** ("why is this on my desk"), with due buckets
  overdue/today/soon/later/undated; (3) **roles differ in structure, not in numbers** (clerk: intake; officer: my
  matters; approver: waiting on me; manager: team; auditor: oversight, no buttons); (4) an agenda of the next few
  dates from the union board; (5) a universal search box with Ctrl+K and `/`, scopes, and relevance plus fuzzy
  matching on normalised Arabic; (6) loading, empty, permission and error states, and "could not refresh, showing
  what we had"; (7) a `Layout` control panel with a compact `+ جديد`; (8) `setDisplayName`, so a URL-opened client
  action does not breadcrumb as غير مسمى.
- **Port:** **redesign LDM's `legal_dashboard_tag` in place** (same client-action xmlid and tag; SAG's menu and
  bookmarks keep working), following `redesign-in-place-not-alongside`. The payload model is a fresh
  `legal.workspace` AbstractModel over LDM's own records. The `_safe_*`/`_has_model` probing layer from
  `legal_dashboard.py` is not needed, because in a single module every model exists.
- **Simplify:** SAG's scale is 11 matters and 2 clients, so the queue plus agenda plus search is the whole screen.
  No attention rail with five counters and no secondary tabs until the data needs them.

#### E2 — Field widgets: phase rail, checklist, clock badge · P1

- **Paths:** `legal_procedure/static/src/components/phase_rail/` (151 js + 145 xml + 205 scss, with
  `static/tests/legal_phase_rail.test.js` 181), `checklist/` (159 + 128 + 189), `clock_badge/` (110 + 50 + 111),
  shared `_common/legal_common.scss` (426).
- **Why these three:** they are pure renderers of a server-composed JSON payload, which keeps the business rules in
  Python where tests reach them, and they are written to an explicit accessibility contract (USWDS step indicator:
  real `<button>` segments, `aria-current="step"`, visually hidden status words, a table fallback in `<details>`;
  GOV.UK task list: the whole row is the link, sentence case, one hint line per row). The clock badge says **whose
  delay it is** ("لدى الجهة منذ ٦ أيام عمل — تجاوز الهدف بيومين" versus "بانتظارنا") before it uses colour.
- **Port:** copy, rename the registry keys (`ldm_phase_rail`, `ldm_checklist`, `ldm_clock_badge`) and templates, and
  write the payload computes on `legal.task`. Draw 3–6 phases, never one segment per step. Keep
  `markup()` only for server-sanitised HTML (the rail's `clerk_instruction_html` comment explains why).
- **Tests to copy:** the hoot pattern in `legal_phase_rail.test.js` (`defineModels`, `mountView`, payload fed
  directly) and `legal_mail_room.test.js` for client actions.

#### E3 — What not to take from `static/src` · NO

`desk/` (legacy مكتبي, superseded by E1), `mail_room/` (three-column diwan screen, superseded by the queue and the
board), `body_desk/` (per-body panels, reference material that competed with work), `kpi_tile/` and `worklist/`
(the "hero numeral" and a single-register list that MY_OFFICE_REDESIGN §1 names as faults 1 and 2).
`counter_walk/` (the runner's ordered stamp checklist for the 22-counter براءة ذمة walk) is clever but niche: P3, and
only if a customer runs clearance walks.

#### E4 — Design tokens, native-view skin, font · P0

- **Paths:** `legal_office/static/src/scss/legal_ds.scss` (188: spacing on a 4px base, a type ramp with an Arabic
  step-up (13 → 14px body, 1.65 leading), a three-level surface ladder, one hairline colour, row heights 54/52/32,
  **five semantic tones** (critical, warning, waiting, calm, neutral), one focus ring, mixins `ds-numeral`,
  `ds-truncate`, `ds-panel`, `ds-section-label` (never uppercase in RTL)); `legal_native.scss` (145: quieter
  list/kanban/form under a scope class copied onto the view root by `computeViewClassName`);
  `legal_procedure/static/src/components/_common/legal_fonts.scss` (77: Tajawal from Odoo's own
  `web/static/fonts/google/Tajawal/` files, **not** `fonts.scss`, which would fetch Noto from `fonts.odoocdn.com`
  and stall on an air-gapped network); `scripts/legal_stamp_view_class.py` (idempotent, `--check`).
- **Port:** copy into `legal_department_management/static/src/scss/` and list the files in the manifest in order (the
  tokens before their users; do not glob). Rename the scope class to `o_ldm_view`, stamp it with the script adapted
  to LDM's views, and keep **logical properties only**.
- **Notes:** the tokens are fixed hex, not mixed from `$o-*`. That is acceptable on Community, which has no user
  dark-mode toggle (the `*.dark.scss` bundles exist in `web` but the switch is an Enterprise feature). A
  known layering flaw in the suite (the tokens live in the top module, so lower modules cannot use them, PROGRESS
  session 5) **does not exist** in a single module.

### F. Office-mode designs that were never built

#### F1 — Conflicts check (and engagements) · P2 conflicts, P3 engagement

- **Path:** `docs/phase-2-engagements-and-conflicts.md` (254 lines, written against the live models, with 10 named
  acceptance tests and 4 open decisions). **Nothing is implemented** (no `legal.engagement` or `legal.conflict.check`
  exists in the tree).
- **Port the conflicts check first:** at intake in office mode, search the proposed adverse party's
  **`commercial_partner_id`** across `legal.task.party`, `legal.contract` parties/counterparty and `legal.company`
  (via `partner_id`). **Warn, then require a manager override with a reason.** Store a `legal.conflict.check` row that
  nobody but a system administrator can unlink. The unresolved operator decision carries over unchanged: SAG's lawyer
  rule hides other lawyers' matters, so the search must use `sudo()` and return **redacted** hits ("٣ قضايا لدى فريق
  آخر", with the responsible lawyer's name only). That needs the owner's explicit yes. Add the design's test 5: a
  subsidiary is found through its parent, and the test fails if someone "simplifies" the search back to `partner_id`.
- **Engagement (التكليف):** P3. SAG's `legal.company.lawyer_id`/`lawyer_ids` already cover "responsible advocate per
  client" for a small office. Build `legal.engagement` only with billing.

#### F2 — Time, WIP, billing, retainer, portal · P3

- **Path:** `docs/legal-product-roadmap.md` §4–§6. The decision is to build on **`analytic` + `account` only**:
  `account.analytic.line` for time (standalone, no project dependency), `account.move` from unbilled lines, a
  retainer (أمانة) as a liability, drawn down explicitly. **Never `project` or `hr_timesheet`**, which would duplicate
  the stage engine. The time-entry design constraints (roadmap §6.3: systray timer, keyboard day sheet under five
  seconds per line, `1.5` or `1:30`) are the most important UX specification for the office audience.
- **Port:** all from the specification. LDM already depends on `account`, so no new dependency is needed.

### G. Quality machinery

#### G1 — Test patterns · P0

- `legal_procedure/tests/common.py`: an honest linear fixture (jurisdiction, body type, two bodies, an entity,
  document kinds and types, a three-step procedure with one return transition) and `_make_case` /
  `_register_document` helpers. Rebuild it over LDM models as `tests/common.py`.
- **Auditor tests in every module:** read succeeds; create, write and unlink raise `AccessError` (for example
  `legal_contract/tests/test_legal_contract.py:85`, `legal_deadline/tests/test_deadline.py:169-181`).
- **Separation-of-duties tests:** clerk cannot close, approver can, clerk cannot close through the wizard either
  (`legal_litigation/tests/test_litigation.py:43-75`).
- **SQL-view tests:** materialises, flushes, company scoping, and a test that fails without the LATERAL
  (`legal_procedure/tests/test_entity_coverage.py`).
- **Wizard tests through `default_get` + `new({})`** (SKILL.md).
- **The pack-purity idea** (`legal_iq_registrar/tests/test_pack_purity.py`), recast as a test that the reference
  import adds rows only and is idempotent.
- **Hoot tests** for widgets (`legal_procedure/static/tests/*.test.js`, `web.assets_unit_tests`).
- User creation in 19: `new_test_user(env, login, groups="…")` or `group_ids` (not `groups_id`).
- **An upgrade test that belongs to LDM alone:** load a fixture shaped like SAG's data (Arabic ministry/department
  names, 2 companies, 11 tasks with `session_date`, `expenses_amount`, `approval_state`), run the migration, and assert
  nothing was lost.

#### G2 — Playwright harness lessons · P0

- `docs/ui-audit-3/audit3.py` (298 lines) and `menu_map.py` (43). The lessons are the valuable part:
  1. **Navigate by action xmlid, never by menu xmlid.** Odoo silently lands on the default screen, and 31
     byte-identical "evidence" shots were produced that way. Assert that the landing screen is not the fallback.
  2. **Wait on a real view container** (`.o_list_view, .o_kanban_view, .o_form_view, …, .o_view_nocontent`, plus
     LDM's own OWL root class), never on `networkidle`; the bus never idles. Use `/web/login?db=…` on a
     multi-database server.
  3. Detect **`.o_error_dialog`** as well as `pageerror`: kanban field errors surface only as dialogs. Do not match
     bare `.modal`, which flags every wizard.
  4. Count **named** column headers only, and record `groups` next to `rows`, because a grouped list has zero data
     rows.
  5. For the auditor, count **mutation affordances** (create, save, quick-create, chatter send, activity, cog
     menu) and fail loudly on any.
  6. Read menu visibility from the **DOM**: `ir.ui.menu.search` over RPC returns every menu to every role.
  7. Run at most **two roles concurrently**. Five Chromium contexts exhausted Windows commit memory and crashed
     PostgreSQL twice.
- `docs/ldm/tools/capture.py` already carries lessons 2 and 3 (and `locale='ar-IQ'`). Extend it with roles ×
  screens, the auditor mutation check, 1366 and 1920 viewports, and the fallback assertion.

#### G3 — Translation workflow · P0

- Export with `odoo-bin i18n export … -l ar_001`, fill every `msgstr`, and assert that no previously translated term
  comes back empty. Never hand-write view-term entries: `model_terms` are stored per view.
- **JS strings reach the browser only with an `odoo-javascript` occurrence**, and Python strings only with
  `odoo-python`. Both failures show a single English sentence on an Arabic screen.
- The catalogues are a **terminology donor**: `legal_core`, `legal_procedure`, `legal_litigation`,
  `legal_correspondence` and `legal_request` hold reviewed Iraqi legal Arabic for most concepts LDM will need
  (الوكالة، التبليغ، الطعن تمييزاً، براءة الذمة، صادر/وارد، ملغى …). Reuse those msgstr values for the same English
  msgids.

---

## 4. What must NOT be copied

| # | Do not copy | Why (evidence) |
|---|---|---|
| N1 | **The full procedure engine** (types, phases, steps, transitions, capture fields, versioning, rounds, subjects, step checks, fee rules), ≈10.7k lines | A consultant-configured product. Its configuration spread over nine menus that the roadmap §2.3 names as clutter. The owner wants "very direct", and SAG's users think in matter + state. Take the small version (C1). |
| N2 | **The 92-item menu tree and its habits**: folders wrapping a single child, the same word three times (العقود ×3, الدعاوى ×3), saved filters dressed as menus, configuration as nine menus | Roadmap §2; even after two compaction passes the suite sits at 74. LDM starts at SAG's ~9 items. Keep **one door per register, scope through search filters**, configuration as tabs on its parent, and the naming rules in roadmap §2.4. |
| N3 | **Long lifecycles**: contracts 11 states, requests 11, lawsuits 8, opinions 7 | Each is a statusbar the user must parse. Target 4–5 states, with "waiting on X" as a flag. |
| N4 | **Bilingual selection labels** such as `"Pleading (مرافعة)"`, `"Appeal (استئناف)"` | They put English in the Arabic UI's source. Use English source with `ar.po`. |
| N5 | **Content packs as upgrade data**, and the five per-pack copies of one calendar | They would crash on SAG's unique-name constraints (C4), carry engine configuration LDM lacks, and hold dates that expire. Use an opt-in import (B5) and one calendar. |
| N6 | **`legal_iq_demo`'s `<function>` writes**: `res.company.currency_id = IQD`, `base.IQD.rounding = 1.0`, admin added to Legal Manager; demo users with a shared password (`Legal#2026`); demo shipped as `data` | Destructive on a production ERP with accounting (C6). LDM demo goes under the manifest `demo` key only, never touches base records, and never creates users with known passwords. |
| N7 | **`legal_dashboard.py`'s probing layer** (`_has_model`, `_field`, `_safe_search`…, 1,990 lines) | It exists because the suite's modules are optional to each other. In one module every model exists; probing only hides bugs. |
| N8 | **KPI walls, hero numerals, chart walls, gradients, emoji labels** (the showcase dashboard's 5 counters, SAG's ⚖️📑⏳🖨️➕📊 menu labels, "⏳/✓/✕" inside selection labels) | MY_OFFICE_REDESIGN §1 (faults 1, 5, 9) and §3; SKILL.md design rules; the external review idea 12. |
| N9 | **The older OWL desks**: `legal_desk`, `legal_mail_room`, `legal_body_desk`, `LegalKpiTile`, `LegalWorklist` | Superseded by My Office. Three landing screens is the clutter the owner regretted. |
| N10 | **A separate `legal.court` model** and **a second entity model** beside `legal.company` | SAG already records courts as departments under مجلس القضاء الأعلى. The roadmap's own rule is "no second client model" (Phase 2 doc §9). |
| N11 | **The duplicated obligation generators** (`legal_procedure` and `legal_contract` each have `_clamp_day`, `_planned_*`, `_generate`, `_cron_generate`, `_cron_mark_late`) | Port one generator (C11). |
| N12 | **Stored computed text that depends on language** (for example `blocking_reason` `store=True`) | It froze English into the Arabic queue (PROGRESS P2). Keep such text non-stored with `depends_context=('lang',)`. |
| N13 | **The appeal-rule help text "does not stretch because the office was shut"** | Contradicted by CCP Art. 25(2) (§3.B4). |
| N14 | **View-level `required=` on workflow-conditional fields** (the suite's `poa_id required="poa_usage == 'required'"`) | It froze 3 of 6 files, including the button that would have explained what was missing (SKILL.md). Enforce at the transition instead. |
| N15 | **Anything from the other stream's uncommitted `legal_office` working tree**, until it lands | 3,576 uncommitted lines, not yet verified. Take the HEAD versions (E1). |
| N16 | **AGPL/OPL code** (OCA `agreement`/`contract`, `eh_board` OPL-1) and **the AI Studio mock's bundled module** (OPL-1) | Licence (C7) and quality (mock-adoption §1.4). |
| N17 | **The coverage cross join and the counter walk in v1** | Both depend on procedure configuration that v1 will not have (D3, E3). |
| N18 | **SAG's own anti-patterns**, which the professional version must also drop: stored denormalised `company_name`/`ministry_name`/`department_name`; the `department_cards_html` HTML-blob dossier; Float money labelled "(د.ع / $)"; `datetime.now()` for approval stamps; calendar-day crons; only two groups; unguarded `action_approve` | External review §5. Keep the columns until a migration removes them, but stop showing them. |

---

## 5. Conventions and gotchas from the suite that apply to the new work

From `.claude/skills/legal-suite-conventions/SKILL.md`, filtered to what LDM will actually hit:

1. **Build and verify every batch:** validate the XML, upgrade into a **fresh log**, read the whole log with **zero new
   warnings**, restart, verify **in the browser in Arabic per affected role** with Playwright (watch
   `.o_error_dialog` and `pageerror`), run the full suite, then commit. LDM's database is `ldm_pro` on
   `http://127.0.0.1:8095` per `docs/ldm/tools/capture.py`; `legal_dept` on 8090 belongs to the suite.
2. **Translations reach the webclient only with an `odoo-javascript` occurrence**, and server strings only with
   `odoo-python`. Code translations are read from the `.po` on disk per process, so a restart deploys them.
3. **Translatable columns in `_auto = False` views are `jsonb`**: declare `translate=True`, and all union arms must
   agree on the type.
4. **A field default is called with the recordset** (`def f(model)`). Test wizards through `default_get` and
   `new({})`.
5. **An Integer year prints as "2,026"**; use `options="{'enable_formatting': False}"`.
6. **A view-level `required=` freezes the whole record.** Where the engine refuses a transition, the view must not
   also demand the value.
7. **Every field a kanban reads via `record.X` must be declared** in that kanban, or the view shows an error dialog.
8. **OWL expressions are JavaScript** (`&&`, not `and`).
9. **`<i class="fa …">` needs `title=` and `role="img"`**, or the upgrade logs an accessibility warning.
10. **`target="inline"` is invalid** for `act_window` in 19.
11. **Odoo 19 renames:** `res.users.groups_id` → `group_ids`, `ir.ui.menu.groups_id` → `group_ids`;
    `res.groups.category_id` → `privilege_id` + `res.groups.privilege`.
12. **Search views:** group-by filters go in a bare `<group>`, without `expand=` or `string=`.
13. **`load_menus` needs a hashed URL.** Verify menus through the DOM.
14. **The bus never idles.** Wait on selectors. Use `/web/login?db=`.
15. **Shell cwd resets**, so use absolute paths; `git add` needs the repository root.
16. **Native Odoo first.** OWL only where it clearly wins, with `setup()` + hooks + registries, loading/empty/error
    states and keyboard access. **No React, Vue or jQuery, and no core patches.**
17. **RTL through logical CSS only.** Verify at 1366×768 and 1920×1080.
18. **Don't build a big Excel.** Money and audit trails get columns and totals, queues get kanban, schedules get a
    calendar, analysis gets graph/pivot, and secondary columns get `optional="hide"`.
19. **Fixed colour semantics:** danger = overdue or rejected; warning = due soon or missing; success = done or
    accepted; info = waiting on an external party.
20. **No emoji, no gradients, no KPI walls, no invented numbers.** Every panel states its question. Empty states name
    the next action. Errors say what happened and what to do.
21. **Iraqi legal Arabic terminology**, not machine translation.
22. **The auditor gets no mutation affordance anywhere:** hide buttons **and** fence with ACLs and rules.
23. **Firm/office mode gates menus only, never data.**
24. **Commits:** small, author **Silete1**, messages explain *why*, **no Claude/Anthropic attribution**, and check
    with `git show -s --format=fuller HEAD`. **Never stage `custom_addons/legal_office`** while the parallel stream
    holds uncommitted work there; build staged blobs from HEAD when a file is shared.
25. **The live system wins over the plan.** Correct plans in writing. Two menu removals were walked back because the
    action behind them was not read.

**New gotchas this research adds for LDM specifically:**

26. **`'excludes': ['legal_core']`** in the manifest; distinct registry keys and CSS scope (C2).
27. **Never ship reference data that SAG's unique-name constraints can hit** (C4).
28. **`(4, …)` never removes an implied group.** Removing SAG's `base.group_system → group_legal_manager` needs
    `(3, …)` or a migration (A1).
29. **Arabic-literal → English-source conversion** must ship its `ar.po` in the same upgrade, or SAG's users see
    English the morning after (C5).
30. **Migration scripts for changed meaning:** `session_date` → hearing rows, `expenses_amount` → fee lines, emoji
    selection labels → clean labels (values unchanged). Test the migration on a SAG-shaped fixture before touching
    production.
31. **Appeal windows:** add CCP Art. 204 (10 days, magisterial and religious courts), Art. 221 (rectification 7 days,
    6-month cap, once only), Art. 198 (retrial 15 days), and the Art. 25(2) holiday roll-forward (§3.B4).
32. **Iraqi holidays are yearly data**, with Eid dates announced by sighting. Schedule a yearly review.
33. **Arabic PDFs depend on server fonts** (wkhtmltopdf and fontconfig). Verify on SAG's host.

---

## 6. Recommended port order

| Wave | Items | Why this order |
|---|---|---|
| **0: foundation** | A1 roles (+ migration of SAG's groups), A2 mode switch, A3 engine guard, A4/A5 calendar, E4 tokens and font, G1 fixtures + a SAG-shaped upgrade test, G2 harness, G3 English source + `ar.po` | Everything later depends on these, and they change no user-visible workflow, so SAG's upgrade risk is lowest here. |
| **1: the daily work** | E1 workspace (redesign `legal_dashboard_tag` in place), C2 intake with preview, C1-small stages + `statusbar_duration`, C3 checklist + E2 widgets, C10 company documents + A6 expiry, C12 fees with accounting links, C6 POA, C4 court tab + hearings + judgments + B3/B4 corrected, C5 صادر/وارد + A7 + official letter, D1 deadline board, D5 report helpers (SAG's 3 reports upgraded) | Covers what both an in-house department and an office do every day. Each item is verifiable on screen in Arabic. |
| **2: breadth, behind advanced disclosure** | C7 contracts, C8 opinions, C9 requests (in-house), C11 obligations, C13/C14 log + escalation, D2 approval queue, D4 QR, D6 analytics, B5 reference import, B6 identifiers, F1 conflicts check (after the owner's sudo decision) | Valuable but not daily for everyone. Each is gated by mode or role so it adds nothing to the default screens. |
| **3: office money and niche** | F2 time, WIP, billing, retainer, portal; F1 engagement; D3 coverage; counter walk; full procedure templates | Largest and riskiest (money, portal leaks). Build them only when an office customer is using waves 1–2. |

---

## 7. Sources

**Repository (read-only):** every path cited above, under `C:\Users\Lenovo\Documents\odoo19\`.

**External, for the statutory periods in §3.B4 and §5:**
- Iraqi Civil Actions (Procedure) Law No. 83 of 1969, English translation, University of Zurich: Arts. 25(2), 171,
  172, 177, 187, 196–198, 204, 216, 219–221, 224.
  https://www.ius.uzh.ch/dam/jcr:00000000-0c03-6a0c-ffff-ffffd59df529/civil-action-law.pdf
- The same law in Arabic, Companies Registrar mirror (not opened; listed for the Arabic text):
  https://tasjeel.mot.gov.iq/newtasjeel/قوانين%20المساهمة/قانون%20المرافعات%20المدنية%20رقم%2083%20لسنة%201969%20المعدل.pdf
- Full text, eastlaws (listed): https://www.eastlaws.com/legislation-full-text/ar/iraq/law/10-08-1969/no-83?type=1&id=152749
- Secondary guides that **contradict the statute** on the appeal period (they state 30 days, "Art. 186"), cited only
  to show why the verification flag must stay visible:
  https://www.mondaq.com/guides/results/28/1103/all/iraq-litigation-dispute-resolution ·
  https://muayadandassociates.com/iraq-litigation-guide-qa/

**Odoo 19 checkout facts verified for this document:** `odoo-19.0/addons/account/__manifest__.py:17` (account →
analytic, portal); `odoo-19.0/addons/hr/__manifest__.py:13-19` (hr → resource_mail); `odoo-19.0/odoo/addons/base/models/ir_module.py:441,821,847`
(manifest `excludes` enforced at install); `odoo-19.0/addons/web/static/src/core/barcode/` (ZXing scanner);
`odoo-19.0/addons/mail/static/src/views/fields/statusbar_duration/`; `odoo-19.0/addons/web/static/lib/` (Chart.js,
zxing-library, luxon, fullcalendar and others already bundled, so a port needs no new front-end library).
