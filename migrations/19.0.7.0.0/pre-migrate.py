# -*- coding: utf-8 -*-
"""19.0.6.3.0 -> 19.0.7.0.0, before the new schema and data are loaded.

Plain SQL only: the ORM still has the old definitions here.
"""
import logging

_logger = logging.getLogger(__name__)
MODULE = "legal_department_management"


def _xmlid_res_id(cr, module, name):
    cr.execute("SELECT res_id FROM ir_model_data WHERE module = %s AND name = %s", (module, name))
    row = cr.fetchone()
    return row and row[0]


def _column_exists(cr, table, column):
    cr.execute("""SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = %s""",
               (table, column))
    return bool(cr.fetchone())


def _probe(cr):
    """M0: read-only counts, logged so the upgrade report shows what was found."""
    probes = {
        "matters by state and approval": "SELECT state, approval_state, count(*) FROM legal_task GROUP BY 1, 2",
        "clients by legal form": "SELECT company_type, count(*) FROM legal_company GROUP BY 1",
        "matters whose ministry differs from their department's":
            """SELECT count(*) FROM legal_task t JOIN legal_department d ON d.id = t.department_id
               WHERE d.ministry_id IS NOT NULL AND t.ministry_id IS DISTINCT FROM d.ministry_id""",
        "duplicated matter numbers":
            "SELECT count(*) FROM (SELECT task_number FROM legal_task WHERE task_number IS NOT NULL "
            "GROUP BY 1 HAVING count(*) > 1) x",
        "matters with a session date": "SELECT count(*) FROM legal_task WHERE session_date IS NOT NULL",
        "matters with expenses": "SELECT count(*) FROM legal_task WHERE COALESCE(expenses_amount, 0) <> 0",
    }
    for label, query in probes.items():
        try:
            cr.execute("SAVEPOINT ldm_probe")
            cr.execute(query)
            _logger.info("legal_department_management upgrade probe - %s: %s", label, cr.fetchall())
            cr.execute("RELEASE SAVEPOINT ldm_probe")
        except Exception as exc:  # a probe never blocks the upgrade
            cr.execute("ROLLBACK TO SAVEPOINT ldm_probe")
            _logger.warning("legal_department_management upgrade probe - %s failed: %s", label, exc)


def _grant_manager_to_admins(cr):
    """M11: 19.0.6.3.0 made every Settings administrator a legal manager through
    an implied group. 19.0.7.0.0 removes that implication (a Settings admin is IT,
    not the legal manager), so first give the role explicitly to every user who
    held it only that way: nobody loses access on upgrade day."""
    manager = _xmlid_res_id(cr, MODULE, "group_legal_manager")
    system = _xmlid_res_id(cr, "base", "group_system")
    if not manager or not system:
        return
    cr.execute("""
        WITH RECURSIVE closure(gid, hid) AS (
            SELECT gid, hid FROM res_groups_implied_rel
            UNION
            SELECT c.gid, r.hid FROM closure c JOIN res_groups_implied_rel r ON r.gid = c.hid
        ),
        admins AS (
            SELECT DISTINCT u.uid FROM res_groups_users_rel u
             WHERE u.gid = %(system)s
                OR u.gid IN (SELECT gid FROM closure WHERE hid = %(system)s)
        )
        INSERT INTO res_groups_users_rel (gid, uid)
        SELECT %(manager)s, a.uid FROM admins a
         WHERE NOT EXISTS (SELECT 1 FROM res_groups_users_rel x WHERE x.gid = %(manager)s AND x.uid = a.uid)
        RETURNING uid
    """, {"system": system, "manager": manager})
    granted = [row[0] for row in cr.fetchall()]
    _logger.info("legal_department_management upgrade: legal manager granted explicitly to users %s", granted)


def _repair_ministries(cr):
    """M4: the matter's ministry follows its department."""
    cr.execute("""
        UPDATE legal_task t SET ministry_id = d.ministry_id
          FROM legal_department d
         WHERE t.department_id = d.id AND d.ministry_id IS NOT NULL
           AND t.ministry_id IS DISTINCT FROM d.ministry_id
    """)
    _logger.info("legal_department_management upgrade: %s matter ministries repaired", cr.rowcount)


def _deduplicate_numbers(cr):
    """The showcase fell back to CASE/YYYY/MM/001 when its sequence was missing,
    so numbers can repeat. The new unique index needs them unique."""
    cr.execute("""
        UPDATE legal_task t SET task_number = t.task_number || '-' || t.id
          FROM (SELECT id, row_number() OVER (PARTITION BY task_number ORDER BY id) AS rn
                  FROM legal_task WHERE task_number IS NOT NULL) x
         WHERE x.id = t.id AND x.rn > 1
    """)
    if cr.rowcount:
        _logger.info("legal_department_management upgrade: %s duplicated matter numbers renumbered", cr.rowcount)


def _keep_legacy_values(cr):
    """session_date and expenses_amount become computed; legal.company phone and
    email move to the contact. Keep their values for the post-migration."""
    copies = [
        ("legal_task", "session_date", "ldm_legacy_session_date", "date"),
        ("legal_task", "expenses_amount", "ldm_legacy_expenses", "double precision"),
        ("legal_company", "phone", "ldm_legacy_phone", "varchar"),
        ("legal_company", "email", "ldm_legacy_email", "varchar"),
        ("legal_company", "address", "ldm_legacy_address", "text"),
    ]
    for table, source, target, sql_type in copies:
        if not _column_exists(cr, table, source) or _column_exists(cr, table, target):
            continue
        cr.execute(f'ALTER TABLE "{table}" ADD COLUMN "{target}" {sql_type}')
        cr.execute(f'UPDATE "{table}" SET "{target}" = "{source}"')


def migrate(cr, version):
    if not version:
        return
    _probe(cr)
    _grant_manager_to_admins(cr)
    _repair_ministries(cr)
    _deduplicate_numbers(cr)
    _keep_legacy_values(cr)
