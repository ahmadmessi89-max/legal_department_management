# -*- coding: utf-8 -*-
"""Coverage: for every client and every service tracked for all companies,
whether it was done this year (SPEC 14.6, research 06 D3).

The mock's flagship idea: the filing nobody started is the whole point of a
compliance product. A read-only SQL view crosses clients with the matter types
that have ``track_coverage`` and looks up each pair's latest matter, so the
"not done this year" rows exist without creating a draft matter for each.
No translatable column is projected (the type's name is read through the
many2one), so the view has no jsonb column (see the suite's SKILL.md).
"""
from odoo import _, api, fields, models, tools

COVERAGE_STATES = [
    ("done", "Done this year"),
    ("open", "In progress"),
    ("due", "Not done this year"),
]


class LegalCompanyCoverage(models.Model):
    _name = "legal.company.coverage"
    _description = "Services done this year, per client"
    _auto = False
    _order = "legal_company_id, sequence, template_id"
    _rec_name = "template_id"

    legal_company_id = fields.Many2one("legal.company", string="Client", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    template_id = fields.Many2one("legal.task.template", string="Service", readonly=True)
    department_id = fields.Many2one("legal.department", string="Body", readonly=True)
    sequence = fields.Integer(readonly=True)
    last_task_id = fields.Many2one("legal.task", string="Latest matter", readonly=True)
    last_state = fields.Selection(
        [("draft", "New"), ("in_progress", "In progress"), ("pending_docs", "Waiting"),
         ("done", "Done"), ("cancelled", "Cancelled")], string="Latest matter status", readonly=True)
    last_done_date = fields.Date(string="Last done on", readonly=True)
    coverage_state = fields.Selection(COVERAGE_STATES, string="This year", readonly=True)
    is_due = fields.Boolean(string="Due this year", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH local_today AS (
                    SELECT (now() AT TIME ZONE 'Asia/Baghdad')::date AS today
                )
                SELECT
                    c.id * 100000 + t.id AS id,
                    c.id AS legal_company_id,
                    c.company_id AS company_id,
                    t.id AS template_id,
                    t.department_id AS department_id,
                    t.sequence AS sequence,
                    latest.id AS last_task_id,
                    latest.state AS last_state,
                    done.last_done AS last_done_date,
                    CASE
                        WHEN done.last_done IS NOT NULL
                             AND date_part('year', done.last_done) = date_part('year', lt.today) THEN 'done'
                        WHEN opened.open_count > 0 THEN 'open'
                        ELSE 'due'
                    END AS coverage_state,
                    NOT (
                        (done.last_done IS NOT NULL
                         AND date_part('year', done.last_done) = date_part('year', lt.today))
                        OR opened.open_count > 0
                    ) AS is_due
                FROM legal_company c
                CROSS JOIN local_today lt
                JOIN legal_task_template t
                  ON t.track_coverage IS TRUE AND t.active IS TRUE
                 AND (t.company_id IS NULL OR c.company_id IS NULL OR t.company_id = c.company_id)
                LEFT JOIN LATERAL (
                    SELECT m.id, m.state
                      FROM legal_task m
                     WHERE m.legal_company_id = c.id AND m.template_id = t.id AND m.active IS TRUE
                       AND m.state != 'cancelled'
                  ORDER BY COALESCE(m.date_closed, m.date_opened) DESC NULLS LAST, m.id DESC
                     LIMIT 1
                ) latest ON TRUE
                LEFT JOIN LATERAL (
                    SELECT MAX(m.date_closed) AS last_done
                      FROM legal_task m
                     WHERE m.legal_company_id = c.id AND m.template_id = t.id AND m.active IS TRUE
                       AND m.state = 'done'
                ) done ON TRUE
                LEFT JOIN LATERAL (
                    SELECT COUNT(*) AS open_count
                      FROM legal_task m
                     WHERE m.legal_company_id = c.id AND m.template_id = t.id AND m.active IS TRUE
                       AND m.state IN ('draft', 'in_progress', 'pending_docs')
                ) opened ON TRUE
                WHERE c.active IS TRUE AND COALESCE(c.client_kind, 'company') = 'company'
            )
        """)

    def action_ldm_start(self):
        """Open the quick-create dialog for this client and service."""
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "legal_department_management.action_legal_task_create_wizard")
        action["context"] = {
            "default_legal_company_id": self.legal_company_id.id,
            "default_template_id": self.template_id.id,
            "default_department_id": self.department_id.id or False,
        }
        action["name"] = _("New matter: %s", self.template_id.name)
        return action

    def action_open_last_task(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "res_model": "legal.task", "res_id": self.last_task_id.id,
                "view_mode": "form", "target": "current"}
