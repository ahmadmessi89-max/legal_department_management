# -*- coding: utf-8 -*-
"""Hand over work (SPEC 14.4): a lawyer or clerk leaves, or goes on leave.

A legal manager picks who hands over to whom and what moves: the matters they
are responsible for and the teams they sit on, their open steps, planned court
sessions, open deadlines, activities and the requests assigned to them. With an
end date the hand-over is a cover: the colleague joins the teams and takes the
dated work up to that day, and nobody loses a matter. Every matter that changes
gets one hand-over note in its history. Powers of attorney that name the person
leaving are listed, because a new one has to be issued; the dialog cannot do
that for them.
"""
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from ..models.ldm_engine import engine_guard
from ..models.ws_common import G_MANAGER, LEGAL_ACTIVITY_MODELS, OPEN_STATES


class LegalHandoverWizard(models.TransientModel):
    _name = "legal.handover.wizard"
    _description = "Hand over work"

    from_user_id = fields.Many2one("res.users", string="From", required=True,
                                   domain="[('share', '=', False)]")
    to_user_id = fields.Many2one("res.users", string="To", required=True,
                                 domain="[('share', '=', False), ('id', '!=', from_user_id)]")
    date_end = fields.Date(string="Until",
                           help="Leave empty to hand the work over for good. With a date the colleague covers "
                                "until then: they join the teams and take the work dated up to that day.")
    scope_matters = fields.Boolean(string="Matters and clients they are responsible for, and their teams",
                                   default=True)
    scope_steps = fields.Boolean(string="Open steps", default=True)
    scope_hearings = fields.Boolean(string="Planned court sessions", default=True)
    scope_deadlines = fields.Boolean(string="Open deadlines", default=True)
    scope_activities = fields.Boolean(string="Activities", default=True)
    scope_requests = fields.Boolean(string="Requests assigned to them", default=True)
    note = fields.Text(string="Hand-over note",
                       help="Written once into the history of every matter that changes hands.")
    summary = fields.Text(string="What moves", compute="_compute_preview")
    poa_ids = fields.Many2many("legal.poa", string="New power of attorney needed", compute="_compute_preview")

    @api.depends("from_user_id", "to_user_id", "date_end", "scope_matters", "scope_steps", "scope_hearings",
                 "scope_deadlines", "scope_activities", "scope_requests")
    def _compute_preview(self):
        for wizard in self:
            if not wizard.from_user_id:
                wizard.summary = False
                wizard.poa_ids = False
                continue
            moves = wizard._ldm_moves()
            lines = []
            labels = [
                ("matters", _("%s matters")), ("clients", _("%s clients")), ("steps", _("%s open steps")),
                ("hearings", _("%s court sessions")), ("deadlines", _("%s deadlines")),
                ("activities", _("%s activities")), ("requests", _("%s requests")),
            ]
            for key, label in labels:
                if moves.get(key):
                    lines.append(label % len(moves[key]))
            wizard.summary = "\n".join(lines) if lines else _("Nothing to hand over with these choices.")
            wizard.poa_ids = self.env["legal.poa"].search(
                [("agent_user_ids", "in", wizard.from_user_id.ids), ("state", "=", "active")])

    def _ldm_moves(self):
        """What would move, as recordsets, for the choices in the dialog."""
        self.ensure_one()
        user = self.from_user_id
        end = self.date_end
        today = fields.Date.context_today(self)
        moves = {}
        if self.scope_matters:
            moves["matters"] = self.env["legal.task"].search(
                [("state", "in", OPEN_STATES), "|", ("lawyer_id", "=", user.id), ("lawyer_ids", "in", user.ids)])
            if not end:
                moves["clients"] = self.env["legal.company"].search(
                    ["|", ("lawyer_id", "=", user.id), ("lawyer_ids", "in", user.ids)])
        if self.scope_steps:
            domain = [("state", "=", "todo"), ("user_id", "=", user.id), ("task_id.state", "in", OPEN_STATES)]
            if end:
                domain += [("date_due", "<=", end)]
            moves["steps"] = self.env["legal.task.step"].search(domain)
        if self.scope_hearings:
            domain = [("state", "=", "planned"), ("attending_user_id", "=", user.id), ("date", ">=", today)]
            if end:
                domain += [("date", "<=", end)]
            moves["hearings"] = self.env["legal.hearing"].search(domain)
        if self.scope_deadlines:
            domain = [("state", "in", ("open", "awaiting_service")), ("user_id", "=", user.id)]
            if end:
                domain += ["|", ("date_safe", "=", False), ("date_safe", "<=", end)]
            moves["deadlines"] = self.env["legal.deadline"].search(domain)
        if self.scope_activities:
            domain = [("user_id", "=", user.id), ("res_model", "in", LEGAL_ACTIVITY_MODELS)]
            if end:
                domain += [("date_deadline", "<=", end)]
            moves["activities"] = self.env["mail.activity"].search(domain)
        if self.scope_requests:
            moves["requests"] = self.env["legal.request"].search(
                [("assigned_user_id", "=", user.id), ("state", "in", ("new", "in_review", "returned"))])
        return moves

    def action_confirm(self):
        self.ensure_one()
        if not self.env.user.has_group(G_MANAGER):
            raise AccessError(_("Only a legal manager can hand work over."))
        if self.from_user_id == self.to_user_id:
            raise UserError(_("Choose two different people."))
        source, target, end = self.from_user_id, self.to_user_id, self.date_end
        moves = self._ldm_moves()
        touched = {}

        def mark(tasks, what):
            for task in tasks:
                touched.setdefault(task.id, []).append(what)

        matters = moves.get("matters", self.env["legal.task"])
        if matters:
            if end:
                matters.write({"lawyer_ids": [(4, target.id)]})
                mark(matters, _("joins the team"))
            else:
                responsible = matters.filtered(lambda t: t.lawyer_id == source)
                if responsible:
                    responsible.write({"lawyer_id": target.id})
                    mark(responsible, _("becomes responsible"))
                matters.write({"lawyer_ids": [(4, target.id), (3, source.id)]})
                mark(matters - responsible, _("replaces them on the team"))
        clients = moves.get("clients", self.env["legal.company"])
        if clients:
            responsible = clients.filtered(lambda c: c.lawyer_id == source)
            responsible.write({"lawyer_id": target.id})
            clients.write({"lawyer_ids": [(4, target.id), (3, source.id)]})
        if moves.get("steps"):
            moves["steps"].write({"user_id": target.id})
            mark(moves["steps"].task_id, _("%s open steps", len(moves["steps"])))
        if moves.get("hearings"):
            moves["hearings"].write({"attending_user_id": target.id})
            mark(moves["hearings"].task_id, _("court sessions"))
        if moves.get("deadlines"):
            moves["deadlines"].write({"user_id": target.id})
            mark(moves["deadlines"].task_id, _("deadlines"))
        if moves.get("activities"):
            moves["activities"].write({"user_id": target.id})
            legal = moves["activities"].filtered(lambda a: a.res_model == "legal.task")
            mark(self.env["legal.task"].browse(legal.mapped("res_id")).exists(), _("activities"))
        if moves.get("requests"):
            # The assignee of a request is guarded by its workflow; a manager's
            # hand-over is that workflow.
            with engine_guard():
                moves["requests"].write({"assigned_user_id": target.id})
        for task in self.env["legal.task"].browse(list(touched)):
            if end:
                head = _("Covered by %(taker)s for %(giver)s until %(date)s:", taker=target.name,
                         giver=source.name, date=fields.Date.to_string(end))
            else:
                head = _("Handed over from %(giver)s to %(taker)s:", taker=target.name, giver=source.name)
            body = head + " " + ", ".join(dict.fromkeys(touched[task.id])) + "."
            if self.note:
                body += "\n" + self.note
            task.message_post(body=body)
        message = _("%(count)s matters changed hands.", count=len(touched))
        if self.poa_ids:
            message += " " + _("%(count)s powers of attorney name %(name)s: issue new ones.",
                               count=len(self.poa_ids), name=source.name)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"type": "success", "message": message, "sticky": bool(self.poa_ids),
                       "next": {"type": "ir.actions.act_window_close"}},
        }
