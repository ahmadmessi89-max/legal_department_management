# -*- coding: utf-8 -*-
"""19.0.6.3.0 -> 19.0.7.0.0, after the new schema and data are loaded.

Order matters: courts are classified first, because the kind of every matter
and the fate of every old session date depend on whether its body is a court.
"""
import logging

from odoo import SUPERUSER_ID, api, fields

from odoo.addons.legal_department_management.models.ldm_text import normalize

_logger = logging.getLogger(__name__)

JUDICIAL_COUNCIL = normalize("مجلس القضاء الأعلى")
COURT_PREFIX = normalize("محكمة")
DEGREE_TOKENS = [  # most specific first
    (normalize("أحوال شخصية"), "personal_status"),
    (normalize("استئناف"), "appeal"),
    (normalize("تمييز"), "cassation"),
    (normalize("بداءة"), "first_instance"),
    (normalize("جنايات"), "felony"),
    (normalize("جنح"), "misdemeanour"),
    (normalize("تحقيق"), "investigation"),
    (normalize("عمل"), "labour"),
    (normalize("قضاء إداري"), "administrative"),
    (normalize("قضاء الموظفين"), "employee"),
    (normalize("تنفيذ"), "execution"),
]


def _has_column(cr, table, column):
    cr.execute("SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = %s", (table, column))
    return bool(cr.fetchone())


def _classify_courts(env):
    """Before M5 and M13: which of SAG's bodies are courts."""
    Department = env["legal.department"].with_context(active_test=False)
    matched, unmatched = [], []
    for ministry in env["legal.ministry"].with_context(active_test=False).search([]):
        if normalize(ministry.name) == JUDICIAL_COUNCIL:
            ministry.body_kind = "judicial"
    for department in Department.search([]):
        name = normalize(department.name)
        is_court = name.startswith(COURT_PREFIX) or normalize(department.ministry_id.name or "") == JUDICIAL_COUNCIL
        if not is_court:
            continue
        degree = next((value for token, value in DEGREE_TOKENS if token in name), "other")
        department.write({"body_kind": "execution" if degree == "execution" else "court", "court_degree": degree})
        (matched if degree != "other" else unmatched).append(department.name)
    _logger.info("legal_department_management upgrade: courts classified %s; courts without a degree %s",
                 matched, unmatched)


def _create_partners(env, cr):
    """M1: a contact behind every client, carrying its phone, email and address."""
    legacy = {}
    if _has_column(cr, "legal_company", "ldm_legacy_phone"):
        cr.execute("SELECT id, ldm_legacy_phone, ldm_legacy_email, ldm_legacy_address FROM legal_company")
        legacy = {row[0]: row[1:] for row in cr.fetchall()}
    Partner = env["res.partner"]
    for client in env["legal.company"].with_context(active_test=False).search([("partner_id", "=", False)]):
        phone, email, address = legacy.get(client.id, (False, False, False))
        values = client._ldm_partner_values()
        values.update({"phone": phone or False, "email": email or False,
                       "street": (address or "").strip().split("\n")[0] or False})
        client.partner_id = Partner.create(values)
        if address and not client.address:
            client.address = address


def _matter_basics(env, cr):
    """M13: company, kind and opening date on every matter."""
    company = env.ref("base.main_company")
    cr.execute("UPDATE legal_task SET company_id = %s WHERE company_id IS NULL", (company.id,))
    cr.execute("UPDATE legal_company SET company_id = %s WHERE company_id IS NULL", (company.id,))
    cr.execute("UPDATE legal_task SET date_opened = create_date::date WHERE date_opened IS NULL")
    for task in env["legal.task"].with_context(active_test=False).search([("template_id", "=", False)]):
        if task.department_id.body_kind in ("court", "execution"):
            kind = "execution" if task.department_id.body_kind == "execution" else "litigation"
        elif task.department_id:
            kind = "government"
        else:
            kind = "other"
        if task.kind != kind:
            task.kind = kind


def _responsible_in_team(cr):
    """M3: whoever SAG's hidden lawyer_id gave access to keeps it, now visibly."""
    cr.execute("""
        INSERT INTO legal_task_lawyers_rel (task_id, user_id)
        SELECT t.id, t.lawyer_id FROM legal_task t
         WHERE t.lawyer_id IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM legal_task_lawyers_rel r WHERE r.task_id = t.id AND r.user_id = t.lawyer_id)
    """)
    cr.execute("""
        INSERT INTO legal_company_lawyers_rel (company_id, user_id)
        SELECT c.id, c.lawyer_id FROM legal_company c
         WHERE c.lawyer_id IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM legal_company_lawyers_rel r WHERE r.company_id = c.id AND r.user_id = c.lawyer_id)
    """)


def _sessions(env, cr):
    """M5: SAG's one session date becomes a court session (at a court) or a
    counter visit step (anywhere else)."""
    if not _has_column(cr, "legal_task", "ldm_legacy_session_date"):
        return
    cr.execute("SELECT id, ldm_legacy_session_date FROM legal_task WHERE ldm_legacy_session_date IS NOT NULL")
    today = fields.Date.context_today(env["legal.task"])
    for task_id, day in cr.fetchall():
        task = env["legal.task"].browse(task_id)
        future = day >= today
        if task.kind in ("litigation", "execution"):
            env["legal.hearing"].create({
                "task_id": task.id, "kind": "hearing", "date": day, "department_id": task.department_id.id or False,
                "attending_user_id": task.lawyer_id.id or False, "state": "planned" if future else "held",
            })
        else:
            env["legal.task.step"].create({
                "task_id": task.id, "name": "Visit to the body", "is_visit": True, "date_due": day,
                "department_id": task.department_id.id or False, "user_id": task.lawyer_id.id or False,
                "state": "todo" if future else "done", "done_date": False if future else day,
            })


def _expenses(env, cr):
    """M2: SAG's single expenses figure becomes one expense line."""
    if not _has_column(cr, "legal_task", "ldm_legacy_expenses"):
        return
    cr.execute("SELECT id, ldm_legacy_expenses FROM legal_task WHERE COALESCE(ldm_legacy_expenses, 0) <> 0")
    for task_id, amount in cr.fetchall():
        task = env["legal.task"].browse(task_id)
        env["legal.task.expense"].create({
            "task_id": task.id, "name": "Expenses recorded before the upgrade", "amount": amount,
            "currency_id": task.company_id.currency_id.id, "date": task.date_opened or fields.Date.today(),
            "recoverable": False,
        })


def _attachments(cr):
    """M6: files linked through SAG's attachment tabs appear in the chatter too."""
    for model, table, column in (("legal.task", "legal_task_ir_attachment_rel", "task_id"),
                                 ("legal.company", "legal_company_ir_attachment_rel", "company_id")):
        cr.execute(f"""
            UPDATE ir_attachment a SET res_model = %s, res_id = r.{column}
              FROM {table} r
             WHERE a.id = r.attachment_id AND (a.res_model IS NULL OR a.res_id IS NULL OR a.res_id = 0)
        """, (model,))


def _duplicate_activities(cr):
    """M9: SAG's cron added a new overdue reminder every day. Keep the newest."""
    cr.execute("""
        DELETE FROM mail_activity a USING mail_activity b
         WHERE a.res_model = 'legal.task' AND b.res_model = 'legal.task'
           AND a.res_id = b.res_id AND a.user_id = b.user_id
           AND COALESCE(a.summary, '') = COALESCE(b.summary, '') AND a.id < b.id
    """)
    _logger.info("legal_department_management upgrade: %s duplicate reminders removed", cr.rowcount)


def _bilingual_names(env):
    """M10: SAG's cron and sequence are noupdate records named in Arabic.
    Give them an English source and keep the Arabic for Arabic users."""
    names = {
        "legal_department_management.ir_cron_legal_task_checker": (
            "Legal: reminders for sessions, deadlines and steps",
            "الشؤون القانونية: التذكير بالجلسات والمواعيد والخطوات"),
    }
    for xmlid, (english, arabic) in names.items():
        record = env.ref(xmlid, raise_if_not_found=False)
        if not record:
            continue
        target = record.ir_actions_server_id if record._name == "ir.cron" else record
        target.with_context(lang="en_US").name = english
        if env["res.lang"]._lang_get("ar_001"):
            target.with_context(lang="ar_001").name = arabic
    sequence = env.ref("legal_department_management.seq_legal_task", raise_if_not_found=False)
    if sequence:
        sequence.name = "Legal matters"


def _recompute(env):
    tasks = env["legal.task"].with_context(active_test=False).search([])
    for fname in ("session_date", "next_date", "expenses_amount", "progress", "missing_document_count"):
        env.add_to_compute(env["legal.task"]._fields[fname], tasks)
    env.flush_all()


def _preset(env):
    """M14: SAG's data fits both an in-house department and an office serving
    client companies, so it upgrades into the hybrid preset. Unconditional:
    this script runs only on the 19.0.6.3.0 -> 19.0.7.0.0 path."""
    env["res.config.settings"]._ldm_apply_preset("hybrid")
    calendar = env.ref("legal_department_management.ldm_calendar_iraq", raise_if_not_found=False)
    if calendar:
        env["res.company"].search([("ldm_calendar_id", "=", False)]).write({"ldm_calendar_id": calendar.id})


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {"active_test": False, "tracking_disable": True,
                                             "mail_notrack": True, "mail_create_nolog": True})
    _classify_courts(env)
    _create_partners(env, cr)
    _matter_basics(env, cr)
    _responsible_in_team(cr)
    _sessions(env, cr)
    _expenses(env, cr)
    _attachments(cr)
    _duplicate_activities(cr)
    _bilingual_names(env)
    env.invalidate_all()
    _recompute(env)
    _preset(env)
    _logger.info("legal_department_management upgraded to 19.0.7.0.0")
