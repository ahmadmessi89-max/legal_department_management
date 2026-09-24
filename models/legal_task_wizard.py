# -*- coding: utf-8 -*-
"""New matter (ملف جديد, SPEC 5.2 and 14.4), redesigned in place.

SAG's wizard asked for a client, a ministry and a department and then opened a
blank form that saved nothing. This one is a single dialog: the matter type,
the client, the key date and a suggested title are enough to open a matter
whose steps, documents to collect and target date the type fills in. The body
appears when the type has none; a lawsuit adds our role, the opponent and the
court; everything else waits under More. The model name and the action xmlid
are SAG's, so bookmarks and buttons keep working.
"""
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from .legal_task_template import MATTER_KINDS

KEY_DATE_KINDS = ("litigation", "execution")
RECENT_LIMIT = 6


class LegalTaskCreateWizard(models.TransientModel):
    _name = "legal.task.create.wizard"
    _description = "New matter"

    template_id = fields.Many2one(
        "legal.task.template", string="Matter type",
        domain="[('company_id', 'in', (False, company_id))]",
        help="The type fills in the steps, the documents to collect and the target date.")
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    kind = fields.Selection(MATTER_KINDS, string="Kind", compute="_compute_kind")
    legal_company_id = fields.Many2one("legal.company", string="Client", required=True)
    key_date = fields.Date(string="Key date")
    name = fields.Char(string="Title")
    name_suggested = fields.Char()
    show_body = fields.Boolean(compute="_compute_kind")
    show_more = fields.Boolean(string="More options")
    ministry_id = fields.Many2one("legal.ministry", string="Ministry or authority")
    department_id = fields.Many2one("legal.department", string="Body or court")
    our_role = fields.Selection(lambda self: self.env["legal.task"]._fields["our_role"].selection,
                                string="We act as")
    opponent_name = fields.Char(string="Opponent")
    lawyer_id = fields.Many2one("res.users", string="Responsible",
                                help="Leave empty: the type's or the client's responsible, else you.")
    lawyer_ids = fields.Many2many("res.users", "ldm_create_wizard_team_rel", "wizard_id", "user_id",
                                  string="Team")
    is_urgent = fields.Boolean(string="Urgent")
    note = fields.Text(string="Note")
    request_id = fields.Many2one("legal.request", string="From request")
    recent_template_ids = fields.Many2many("legal.task.template", string="Recent types",
                                           compute="_compute_recent_template_ids")
    # Law office with fees switched on: the fee agreement the matter falls under.
    fee_agreement = fields.Selection(
        [("none", "Decide later"), ("existing", "Under an existing agreement"), ("new", "Start a draft agreement")],
        string="Fee agreement", default="none")
    engagement_id = fields.Many2one(
        "legal.engagement", string="Agreement",
        domain="[('legal_company_id', '=', legal_company_id), ('state', '=', 'active')]")
    # Conflict of interest check (law office).
    conflict_state = fields.Selection([("none", "Not checked"), ("clear", "Clear"), ("hits", "Possible conflict"),
                                       ("blocked", "Blocked")], default="none")
    conflict_summary = fields.Text(string="Possible conflicts", readonly=True)
    conflict_check_id = fields.Integer()

    # ------------------------------------------------------------------
    # Computes and onchanges
    # ------------------------------------------------------------------
    @api.depends("template_id", "template_id.department_id")
    def _compute_kind(self):
        for wizard in self:
            wizard.kind = wizard.template_id.kind or "other"
            wizard.show_body = bool(wizard.kind in ("government", "litigation")
                                    and not wizard.template_id.department_id)

    @api.depends_context("uid")
    def _compute_recent_template_ids(self):
        recent = self._ldm_recent_templates()
        for wizard in self:
            wizard.recent_template_ids = recent

    @api.model
    def _ldm_recent_templates(self):
        """The user's recent matter types, the last used first."""
        settings = self.env["res.users.settings"]._find_or_create_for_user(self.env.user)
        Template = self.env["legal.task.template"]
        templates = Template.browse(settings.sudo().ldm_recent_template_ids.ids).exists().filtered(
            lambda t: t.active and t.company_id in (self.env["res.company"], self.env.company))
        if not templates:
            return Template
        last_used = {template.id: when for template, when in self.env["legal.task"]._read_group(
            [("create_uid", "=", self.env.uid), ("template_id", "in", templates.ids)],
            ["template_id"], ["create_date:max"])}
        return templates.sorted(lambda t: last_used.get(t.id) or fields.Datetime.from_string("2000-01-01"),
                                reverse=True)[:RECENT_LIMIT]

    def _ldm_suggested_name(self):
        self.ensure_one()
        parts = [self.template_id.name or "", self.legal_company_id.name or ""]
        return " — ".join(p for p in parts if p)

    @api.onchange("template_id", "legal_company_id")
    def _onchange_suggest(self):
        suggestion = self._ldm_suggested_name()
        if not self.name or self.name == self.name_suggested:
            self.name = suggestion
        self.name_suggested = suggestion
        if self.template_id.department_id:
            self.department_id = self.template_id.department_id
        if self.engagement_id and self.engagement_id.legal_company_id != self.legal_company_id:
            self.engagement_id = False

    @api.onchange("ministry_id")
    def _onchange_ministry_id(self):
        if self.ministry_id and self.department_id and self.department_id.ministry_id != self.ministry_id:
            self.department_id = False

    @api.onchange("department_id")
    def _onchange_department_id(self):
        if self.department_id.ministry_id and not self.ministry_id:
            self.ministry_id = self.department_id.ministry_id

    # ------------------------------------------------------------------
    # Creating
    # ------------------------------------------------------------------
    def action_create_open(self):
        """Create the matter and open its cockpit."""
        self.ensure_one()
        blocked = self._ldm_conflict_gate()
        if blocked:
            return blocked
        task = self._ldm_create_matter()
        return self._ldm_result(task, {
            "type": "ir.actions.act_window",
            "res_model": "legal.task",
            "res_id": task.id,
            "views": [[False, "form"]],
            "target": "current",
        })

    def action_create_another(self):
        """Create the matter and start the next one for the same client."""
        self.ensure_one()
        blocked = self._ldm_conflict_gate()
        if blocked:
            return blocked
        task = self._ldm_create_matter()
        return self._ldm_result(task, {
            "type": "ir.actions.act_window",
            "name": _("New matter"),
            "res_model": self._name,
            "views": [[False, "form"]],
            "target": "new",
            "context": {"default_legal_company_id": self.legal_company_id.id},
        })

    def action_create_despite_conflict(self):
        """Policy "warn": the matter is opened but stays New until a partner
        decides on the possible conflict."""
        self.ensure_one()
        if self.conflict_state != "hits":
            return self.action_create_open()
        task = self.with_context(ldm_hold_draft=True)._ldm_create_matter()
        task.ldm_conflict_check(self._ldm_conflict_names(), task_id=task.id)
        task.message_post(body=_("Opened despite a possible conflict of interest; waiting for a partner's decision."))
        return self._ldm_result(task, {
            "type": "ir.actions.act_window",
            "res_model": "legal.task",
            "res_id": task.id,
            "views": [[False, "form"]],
            "target": "current",
        })

    def action_proceed(self):
        """SAG's button name, kept for anything that still calls it."""
        return self.action_create_open()

    def _ldm_conflict_names(self):
        self.ensure_one()
        return [name for name in (self.legal_company_id.name, (self.opponent_name or "").strip()) if name]

    def _ldm_conflict_gate(self):
        """With the conflict check switched on, check the names before creating.
        Returns the dialog again when there is something to show, else False."""
        self.ensure_one()
        Task = self.env["legal.task"]
        if self.conflict_state in ("clear", "hits") or not Task._ldm_feature("group_ldm_conflicts"):
            return False
        result = Task.ldm_conflict_check(self._ldm_conflict_names()) or {}
        hits = result.get("hits") or []
        if not hits:
            self.conflict_state = "clear"
            return False
        lines = []
        for hit in hits:
            if isinstance(hit, dict):
                label = hit.get("label") or hit.get("name") or ""
                role = hit.get("role") or hit.get("reason") or ""
                lines.append(f"• {label} — {role}" if role else f"• {label}")
            else:
                lines.append(f"• {hit}")
        self.write({
            "conflict_state": "blocked" if result.get("policy") == "block" else "hits",
            "conflict_summary": "\n".join(lines),
            "conflict_check_id": result.get("check_id") or 0,
        })
        return {
            "type": "ir.actions.act_window",
            "name": _("New matter"),
            "res_model": self._name,
            "res_id": self.id,
            "views": [[False, "form"]],
            "target": "new",
        }

    def _ldm_create_matter(self):
        self.ensure_one()
        if not self.legal_company_id:
            raise UserError(_("Choose the client first."))
        if self.conflict_state == "blocked":
            raise UserError(_("A possible conflict of interest blocks this matter. Ask a partner."))
        vals = {
            "template_id": self.template_id.id or False,
            "legal_company_id": self.legal_company_id.id,
            "name": (self.name or "").strip() or self._ldm_suggested_name()
            or _("Matter for %s", self.legal_company_id.name),
            "key_date": self.key_date or False,
            "is_urgent": self.is_urgent,
        }
        if not self.template_id:
            vals["kind"] = "other"
        if self.department_id:
            vals["department_id"] = self.department_id.id
        if self.lawyer_id:
            vals["lawyer_id"] = self.lawyer_id.id
        if self.lawyer_ids:
            vals["lawyer_ids"] = [(6, 0, self.lawyer_ids.ids)]
        if self.kind in KEY_DATE_KINDS:
            if self.our_role:
                vals["our_role"] = self.our_role
            if (self.opponent_name or "").strip():
                vals["opponent_name"] = self.opponent_name.strip()
        if self.note:
            vals["action_details"] = self.note
        if self.request_id:
            vals["request_id"] = self.request_id.id
        vals.update(self.env.context.get("ldm_quick_create_vals") or {})
        task = self.env["legal.task"].browse(self.env["legal.task"].create_from_template(vals))
        self._ldm_link_engagement(task)
        self._ldm_remember_template()
        self._ldm_after_create(task)
        return task

    def _ldm_link_engagement(self, task):
        if self.fee_agreement == "existing" and self.engagement_id:
            task.engagement_id = self.engagement_id
        elif self.fee_agreement == "new":
            Engagement = self.env["legal.engagement"]
            if not Engagement.has_access("create"):
                raise AccessError(_("Only a lawyer can start a fee agreement."))
            engagement = Engagement.create({
                "name": _("Fee agreement — %s", self.legal_company_id.name),
                "legal_company_id": self.legal_company_id.id,
                "lawyer_id": task.lawyer_id.id,
                "fee_type": self.template_id.default_fee_type or "lump_sum",
                "currency_id": task.currency_id.id,
            })
            task.engagement_id = engagement

    def _ldm_remember_template(self):
        if not self.template_id:
            return
        settings = self.env["res.users.settings"]._find_or_create_for_user(self.env.user).sudo()
        recent = settings.ldm_recent_template_ids.ids
        ids = [self.template_id.id] + [tid for tid in self._ldm_recent_templates().ids if tid != self.template_id.id]
        ids += [tid for tid in recent if tid not in ids]
        settings.ldm_recent_template_ids = [(6, 0, ids[:RECENT_LIMIT])]

    def _ldm_after_create(self, task):
        """Hook for the streams that open matters from their own records
        (a request, a letter, a coverage row): link the new matter back."""
        return True

    def _ldm_result(self, task, next_action):
        steps = len(task.step_ids)
        docs = len(task.document_ids)
        message = _("%(number)s created with %(steps)s steps and %(docs)s documents to collect.",
                    number=task.task_number, steps=steps, docs=docs)
        if task.approval_state == "to_approve":
            message += " " + _("It waits for approval before work starts.")
        elif task.state == "draft":
            message += " " + _("It stays New until its body is chosen or a partner clears it.")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"type": "success", "message": message, "next": next_action},
        }
