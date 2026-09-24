# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Domain

from .base_litigation import COURT_STAGES
from .ldm_engine import engine_guard, in_engine
from .legal_task_template import LAW_BRANCHES, MATTER_KINDS

OPEN_STATES = ("draft", "in_progress", "pending_docs")
CLOSED_STATES = ("done", "cancelled")
APPROVAL_FIELDS = ("approval_state", "approver_id", "approval_date", "approval_requested_by_id", "approval_note")
TEAM_FIELDS = ("lawyer_id", "lawyer_ids", "confidential")
PRIVILEGED = "legal_department_management.group_ldm_clerk,legal_department_management.group_ldm_auditor"

# (from, to): who may make the move. "any" = anyone with write access on the
# matter; "manager" = legal managers only. Enforced in write(), so a kanban drop
# and an RPC write obey the same table as the buttons. Done and Cancelled are
# reachable only through their dialogs, which run inside engine_guard().
TRANSITIONS = {
    ("draft", "in_progress"): "any",
    ("draft", "pending_docs"): "any",
    ("in_progress", "pending_docs"): "any",
    ("pending_docs", "in_progress"): "any",
    ("in_progress", "done"): "engine",
    ("pending_docs", "done"): "engine",
    ("draft", "cancelled"): "engine",
    ("in_progress", "cancelled"): "engine",
    ("pending_docs", "cancelled"): "engine",
    ("done", "in_progress"): "manager",
    ("cancelled", "in_progress"): "manager",
    ("in_progress", "draft"): "manager",
    ("pending_docs", "draft"): "manager",
    ("done", "draft"): "manager",
    ("cancelled", "draft"): "manager",
}


class LegalTask(models.Model):
    """The matter (ملف): a government transaction, a lawsuit, a contract, an
    opinion... The model name, table and fields of SAG's 19.0.6.3.0 are kept so
    their data upgrades in place."""

    _name = "legal.task"
    _description = "Matter"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "is_urgent desc, next_date asc, id desc"
    _rec_names_search = ["task_number", "name", "court_case_number", "reference"]

    # --- Identity ---------------------------------------------------------
    task_number = fields.Char(string="Number", copy=False, readonly=True, index=True)
    name = fields.Char(string="Title", required=True, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", string="Company", required=True, index=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one("res.currency", string="Currency", required=True,
                                  default=lambda self: self.env.company.currency_id)
    legal_company_id = fields.Many2one("legal.company", string="Client", required=True, ondelete="restrict",
                                       index=True, tracking=True)
    partner_id = fields.Many2one(related="legal_company_id.partner_id", string="Client contact")
    template_id = fields.Many2one("legal.task.template", string="Matter type", ondelete="restrict", index=True,
                                  tracking=True)
    kind = fields.Selection(MATTER_KINDS, string="Kind", compute="_compute_kind", store=True, readonly=False,
                            precompute=True, required=True, index=True)
    law_branch = fields.Selection(LAW_BRANCHES, string="Branch of law", compute="_compute_kind", store=True,
                                  readonly=False, precompute=True)
    properties = fields.Properties(string="Extra fields", definition="template_id.properties_definition", copy=True)
    reference = fields.Char(string="Body's transaction number", tracking=True,
                            help="The number the government body gave the file, or the client's own reference.")
    confidential = fields.Boolean(string="Confidential", tracking=True,
                                  help="Only the responsible, the team and legal managers can see a confidential matter.")
    is_urgent = fields.Boolean(string="Urgent", tracking=True)

    # --- Government body --------------------------------------------------
    department_id = fields.Many2one("legal.department", string="Body or court", ondelete="restrict", index=True,
                                    tracking=True)
    ministry_id = fields.Many2one("legal.ministry", string="Ministry / authority", ondelete="restrict", index=True,
                                  compute="_compute_ministry_id", store=True, readonly=False, precompute=True)
    waiting_on = fields.Selection(
        [("us", "Us"), ("body", "The body"), ("client", "The client"), ("verification", "Confirmation of issuance")],
        string="Waiting on", tracking=True)
    date_submitted = fields.Date(string="Submitted to the body on", tracking=True)
    days_at_body = fields.Integer(string="Working days at the body", compute="_compute_days_at_body")
    # SAG's denormalised copies: kept declared and hidden; no longer written.
    company_name = fields.Char(string="Client name (legacy)", readonly=True)
    ministry_name = fields.Char(string="Ministry name (legacy)", readonly=True)
    department_name = fields.Char(string="Body name (legacy)", readonly=True)

    # --- Status -----------------------------------------------------------
    state = fields.Selection(
        [
            ("draft", "New"),
            ("in_progress", "In progress"),
            ("pending_docs", "Waiting"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        string="Status", default="draft", required=True, tracking=True, index=True, copy=False,
        group_expand=True,
        help="Waiting: for documents, for the body's answer, or for confirmation that a document is genuine.")
    date_state_changed = fields.Datetime(string="In this status since", readonly=True, copy=False,
                                         default=fields.Datetime.now)
    approval_state = fields.Selection(
        [
            ("draft", "Not requested"),
            ("to_approve", "Awaiting approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Approval", default="draft", required=True, tracking=True, index=True, copy=False, readonly=True)
    approver_id = fields.Many2one("res.users", string="Decided by", readonly=True, tracking=True, copy=False)
    approval_date = fields.Datetime(string="Decided on", readonly=True, copy=False)
    approval_requested_by_id = fields.Many2one("res.users", string="Approval requested by", readonly=True, copy=False)
    approval_note = fields.Text(string="Approval note", readonly=True, copy=False)
    date_opened = fields.Date(string="Opened on", default=fields.Date.context_today, copy=False)
    date_closed = fields.Date(string="Closed on", readonly=True, copy=False)
    outcome = fields.Selection(
        [
            ("won", "Won"),
            ("lost", "Lost"),
            ("partial", "Partly won"),
            ("settled", "Settled"),
            ("withdrawn", "Withdrawn"),
            ("completed", "Completed"),
            ("rejected", "Refused by the body"),
            ("client_revoked", "Client ended our mandate"),
            ("lawyer_withdrew", "We withdrew"),
            ("other", "Other"),
        ],
        string="Outcome", tracking=True, copy=False, readonly=True)
    close_note = fields.Text(string="Closing note", copy=False, readonly=True, groups=PRIVILEGED)

    # --- People -----------------------------------------------------------
    lawyer_id = fields.Many2one("res.users", string="Responsible", index=True, tracking=True,
                                default=lambda self: self.env.user)
    lawyer_ids = fields.Many2many("res.users", "legal_task_lawyers_rel", "task_id", "user_id", string="Team",
                                  default=lambda self: [self.env.user.id], tracking=True)
    employee_ids = fields.Many2many("hr.employee", "legal_task_employees_rel", "task_id", "employee_id",
                                    string="Staff team", tracking=True)
    requester_id = fields.Many2one("res.users", string="Requested by", index=True)
    request_id = fields.Many2one("legal.request", string="From request", ondelete="set null", copy=False)

    # --- Dates ------------------------------------------------------------
    session_date = fields.Date(string="Next session or visit", compute="_compute_session_date", store=True,
                               help="Date of the next planned court session or counter visit.")
    due_date = fields.Date(string="Target date", tracking=True)
    is_overdue = fields.Boolean(string="Overdue", compute="_compute_is_overdue", search="_search_is_overdue")
    next_date = fields.Date(string="Next date", compute="_compute_next_date", store=True, index=True)
    next_action = fields.Char(string="Next", compute="_compute_next_action")

    # --- Notes and files ----------------------------------------------------
    action_details = fields.Text(string="Notes", groups=PRIVILEGED)
    attachment_ids = fields.Many2many("ir.attachment", "legal_task_ir_attachment_rel", "task_id", "attachment_id",
                                      string="Files")

    # --- Work records -------------------------------------------------------
    step_ids = fields.One2many("legal.task.step", "task_id", string="Steps", copy=False)
    document_ids = fields.One2many("legal.task.document", "task_id", string="Documents to collect", copy=False)
    hearing_ids = fields.One2many("legal.hearing", "task_id", string="Court sessions", copy=False)
    court_stage_ids = fields.One2many("legal.court.stage", "task_id", string="Court stages", copy=False)
    deadline_ids = fields.One2many("legal.deadline", "task_id", string="Deadlines", copy=False)
    expense_ids = fields.One2many("legal.task.expense", "task_id", string="Expense lines", copy=False)
    party_ids = fields.One2many("legal.task.party", "task_id", string="Parties", copy=True)
    judgment_ids = fields.One2many("legal.judgment", "task_id", string="Judgments", copy=False)
    correspondence_ids = fields.One2many("legal.correspondence", "task_id", string="Letters", copy=False)
    time_entry_ids = fields.One2many("legal.time.entry", "task_id", string="Time", copy=False)
    guarantee_ids = fields.One2many("legal.guarantee", "task_id", string="Letters of guarantee", copy=False)
    poa_id = fields.Many2one("legal.poa", string="Power of attorney", ondelete="set null", index=True)
    progress = fields.Integer(string="Progress", compute="_compute_progress", store=True, aggregator="avg")
    missing_document_count = fields.Integer(string="Missing documents", compute="_compute_missing_documents",
                                            store=True)

    # --- Litigation -------------------------------------------------------
    court_case_number = fields.Char(string="Court case number", tracking=True,
                                    help="The case number at the current court stage. Earlier numbers stay on the court stages.")
    court_stage = fields.Selection(COURT_STAGES, string="Stage", tracking=True)
    our_role = fields.Selection(
        [("plaintiff", "Plaintiff"), ("defendant", "Defendant"), ("complainant", "Complainant"),
         ("accused", "Accused"), ("intervener", "Intervener"), ("other", "Other")],
        string="We act as")
    opponent_name = fields.Char(string="Opponent", compute="_compute_opponent_name", store=True)
    matter_value = fields.Monetary(string="Value of the claim", currency_field="currency_id")

    # --- Contract, opinion, investigation ------------------------------------
    counterparty_id = fields.Many2one("res.partner", string="Counterparty", ondelete="restrict")
    contract_start = fields.Date(string="Contract start")
    contract_end = fields.Date(string="Contract end")
    renewal_notice_days = fields.Integer(string="Renewal notice (days)", default=30)
    question = fields.Text(string="Question", groups=PRIVILEGED)
    requesting_unit = fields.Char(string="Asked by (unit)")
    opinion_html = fields.Html(string="Opinion", groups=PRIVILEGED)
    opinion_number = fields.Char(string="Opinion number", readonly=True, copy=False)
    opinion_date = fields.Date(string="Issued on", readonly=True, copy=False)
    supersedes_id = fields.Many2one("legal.task", string="Revises opinion", ondelete="set null", copy=False)
    superseded_by_id = fields.Many2one("legal.task", string="Revised by", ondelete="set null", copy=False, readonly=True)
    order_number = fields.Char(string="Order number")
    order_date = fields.Date(string="Order date")
    issuing_authority = fields.Char(string="Ordered by")
    committee_member_ids = fields.Many2many("res.users", "legal_task_committee_rel", "task_id", "user_id",
                                            string="Committee members")
    employees_concerned = fields.Text(string="Employees concerned", groups=PRIVILEGED)
    recommendation = fields.Text(string="Recommendation", groups=PRIVILEGED)
    decision_number = fields.Char(string="Decision number")
    decision_date = fields.Date(string="Decision date")
    compensation_amount = fields.Monetary(string="Compensation ordered", currency_field="currency_id",
                                          help="The amount the employee is ordered to pay back (تضمين).")

    # --- Money --------------------------------------------------------------
    expenses_amount = fields.Monetary(string="Expenses", compute="_compute_expenses_amount", store=True,
                                      currency_field="company_currency_id")
    company_currency_id = fields.Many2one(related="company_id.currency_id", string="Company currency")
    account_move_id = fields.Many2one("account.move", string="Journal entry (legacy)", readonly=True, copy=False,
                                      groups="account.group_account_invoice,account.group_account_readonly")
    account_payment_id = fields.Many2one("account.payment", string="Payment (legacy)", readonly=True, copy=False,
                                         groups="account.group_account_invoice,account.group_account_readonly")
    expense_account_id = fields.Many2one("account.account", string="Expense account (legacy)", copy=False,
                                         groups="account.group_account_invoice,account.group_account_readonly")
    engagement_id = fields.Many2one("legal.engagement", string="Fee agreement", ondelete="set null", index=True)
    billing_state = fields.Selection([("none", "Nothing to invoice"), ("to_invoice", "To invoice"),
                                      ("invoiced", "Invoiced")], string="Billing", compute="_compute_billing_state",
                                     compute_sudo=True)
    invoice_ids = fields.Many2many("account.move", string="Invoices", compute="_compute_billing_state",
                                   compute_sudo=True,
                                   groups="account.group_account_invoice,account.group_account_readonly")

    # --- Per-user switches for the form's buttons (the view cannot AND a
    # feature switch with a role, so the model says what this user may do) ---
    ldm_can_request_approval = fields.Boolean(compute="_compute_ldm_rights")
    ldm_can_decide = fields.Boolean(compute="_compute_ldm_rights")
    ldm_is_manager = fields.Boolean(compute="_compute_ldm_rights")

    _task_number_company_uniq = models.UniqueIndex("(company_id, task_number) WHERE task_number IS NOT NULL")

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("template_id")
    def _compute_kind(self):
        for task in self:
            if task.template_id:
                task.kind = task.template_id.kind
                task.law_branch = task.template_id.law_branch or task.law_branch
            elif not task.kind:
                task.kind = "other"

    @api.depends("department_id")
    def _compute_ministry_id(self):
        for task in self:
            if task.department_id:
                task.ministry_id = task.department_id.ministry_id

    @api.depends("hearing_ids.date", "hearing_ids.state", "step_ids.date_due", "step_ids.state", "step_ids.is_visit")
    def _compute_session_date(self):
        for task in self:
            dates = task.hearing_ids.filtered(lambda h: h.state == "planned" and h.date).mapped("date")
            dates += task.step_ids.filtered(lambda s: s.is_visit and s.state == "todo" and s.date_due).mapped("date_due")
            task.session_date = min(dates) if dates else False

    @api.depends("due_date", "state")
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for task in self:
            task.is_overdue = bool(task.due_date and task.due_date < today and task.state not in CLOSED_STATES)

    def _search_is_overdue(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            return NotImplemented
        today = fields.Date.context_today(self)
        domain = Domain("due_date", "<", today) & Domain("state", "not in", CLOSED_STATES)
        return domain if (operator == "=") == value else ~domain

    @api.depends("date_submitted", "waiting_on", "department_id")
    def _compute_days_at_body(self):
        today = fields.Date.context_today(self)
        for task in self:
            if not task.date_submitted or task.waiting_on not in ("body", "verification"):
                task.days_at_body = 0
                continue
            calendar = task.department_id._ldm_calendar() if task.department_id else task.company_id._ldm_calendar()
            if not calendar:
                task.days_at_body = (today - task.date_submitted).days
                continue
            span = task.company_id._ldm_working_days(calendar, task.date_submitted, today) if today > task.date_submitted else set()
            task.days_at_body = len([d for d in span if d > task.date_submitted])

    @api.depends("step_ids.state")
    def _compute_progress(self):
        for task in self:
            steps = task.step_ids.filtered(lambda s: s.state != "skipped")
            task.progress = round(100 * len(steps.filtered(lambda s: s.state == "done")) / len(steps)) if steps else 0

    @api.depends("document_ids.state", "document_ids.mandatory")
    def _compute_missing_documents(self):
        for task in self:
            task.missing_document_count = len(task.document_ids.filtered(
                lambda d: d.mandatory and d.state in ("missing", "expired")))

    @api.depends("expense_ids.amount_company")
    def _compute_expenses_amount(self):
        for task in self:
            task.expenses_amount = sum(task.expense_ids.mapped("amount_company"))

    @api.depends("party_ids.partner_id", "party_ids.is_client_side", "party_ids.role")
    def _compute_opponent_name(self):
        for task in self:
            others = task.party_ids.filtered(lambda p: not p.is_client_side and p.role not in ("witness", "expert"))
            task.opponent_name = "، ".join(others.mapped("partner_id.name")) or False

    def _compute_billing_state(self):
        # The money stream replaces this with the real computation.
        for task in self:
            task.billing_state = "none"
            task.invoice_ids = False

    def _ldm_open_items(self):
        """(date, order, label) for every open dated item of the matter."""
        self.ensure_one()
        items = []
        for hearing in self.hearing_ids.filtered(lambda h: h.state == "planned" and h.date):
            items.append((hearing.date, 0, _("Court session") if hearing.kind == "hearing" else _("Meeting")))
        for deadline in self.deadline_ids.filtered(lambda d: d.state == "open" and d.date_safe):
            items.append((deadline.date_safe, 1, _("Deadline: %s", deadline.name)))
        for step in self.step_ids.filtered(lambda s: s.state == "todo" and s.date_due):
            label = _("Visit: %s", step.name) if step.is_visit else step.name
            items.append((step.date_due, 2, label))
        if self.due_date:
            items.append((self.due_date, 3, _("Target date")))
        return items

    @api.depends("hearing_ids.date", "hearing_ids.state", "deadline_ids.date_safe", "deadline_ids.state",
                 "step_ids.date_due", "step_ids.state", "due_date", "state")
    def _compute_next_date(self):
        for task in self:
            items = task._ldm_open_items() if task.state not in CLOSED_STATES else []
            task.next_date = min(i[0] for i in items) if items else False

    @api.depends_context("lang")
    @api.depends("next_date", "step_ids.name", "step_ids.state", "deadline_ids.name")
    def _compute_next_action(self):
        for task in self:
            if task.state in CLOSED_STATES:
                task.next_action = False
                continue
            items = task._ldm_open_items()
            if items:
                task.next_action = min(items, key=lambda i: (i[0], i[1]))[2]
            else:
                open_step = task.step_ids.filtered(lambda s: s.state == "todo")[:1]
                task.next_action = open_step.name or False

    @api.depends("task_number", "name")
    def _compute_display_name(self):
        for task in self:
            task.display_name = f"{task.task_number} · {task.name}" if task.task_number else (task.name or "")

    @api.depends_context("uid")
    @api.depends("state", "approval_state", "template_id.requires_approval", "approval_requested_by_id")
    def _compute_ldm_rights(self):
        user = self.env.user
        approvals_on = self._ldm_feature("group_ldm_approvals")
        is_lawyer = user.has_group("legal_department_management.group_legal_user")
        is_approver = user.has_group("legal_department_management.group_ldm_approver")
        is_manager = user.has_group("legal_department_management.group_legal_manager")
        for task in self:
            task.ldm_is_manager = is_manager
            task.ldm_can_request_approval = bool(
                approvals_on and is_lawyer and task.state == "draft"
                and (task.template_id.requires_approval or task.approval_state == "rejected")
                and task.approval_state in ("draft", "rejected"))
            task.ldm_can_decide = bool(
                approvals_on and is_approver and task.approval_state == "to_approve"
                and not (task.company_id.ldm_approval_sod and task.approval_requested_by_id == user))

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange("legal_company_id")
    def _onchange_legal_company_id(self):
        if self.legal_company_id.lawyer_id and not self._origin.id:
            self.lawyer_id = self.legal_company_id.lawyer_id

    @api.onchange("template_id")
    def _onchange_template_id(self):
        if self.template_id.confidential_default and not self._origin.id:
            self.confidential = True

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        trusted = in_engine() or self.env.su
        wanted_states = []
        for vals in vals_list:
            if not vals.get("task_number") or vals.get("task_number") in ("New", "/", "مسودة"):
                company = self.env["res.company"].browse(vals["company_id"]) if vals.get("company_id") else self.env.company
                vals["task_number"] = self.env["ir.sequence"].with_company(company).next_by_code("legal.task") or "/"
            if not trusted:
                for field in APPROVAL_FIELDS + ("outcome", "date_closed", "opinion_number", "opinion_date"):
                    vals.pop(field, None)
                wanted_states.append(vals.pop("state", "draft"))
            else:
                wanted_states.append(None)
        tasks = super().create(vals_list)
        tasks._ldm_adopt_attachments()
        for task, wanted in zip(tasks, wanted_states):
            if task.lawyer_id and task.lawyer_id not in task.lawyer_ids:
                task.lawyer_ids = [(4, task.lawyer_id.id)]
            if wanted and wanted != "draft":
                task.write({"state": wanted})  # validated like any other move
        return tasks

    def write(self, vals):
        trusted = in_engine() or self.env.su
        if not trusted:
            if set(vals) & set(APPROVAL_FIELDS):
                raise AccessError(_("The approval of a matter can only change through Approve, Reject or Send for approval."))
            if set(vals) & {"outcome", "date_closed", "opinion_number", "opinion_date"}:
                raise AccessError(_("This is set when the matter is closed or the opinion issued."))
            if set(vals) & set(TEAM_FIELDS) and not self._ldm_is_manager():
                for task in self:
                    if task.lawyer_id != self.env.user:
                        raise UserError(_("Only the lawyer responsible for %s or a legal manager can change its team "
                                          "or make it confidential.", task.display_name))
            if {"legal_company_id", "template_id", "department_id"} & set(vals) and not self._ldm_is_manager():
                for task in self.filtered(lambda t: t.approval_state == "approved"):
                    locked = {"legal_company_id", "template_id"}
                    if task.kind == "government":
                        locked.add("department_id")
                    if locked & set(vals):
                        raise UserError(_("%s is approved: only a legal manager can change its client, type or body.",
                                          task.display_name))
        if "state" in vals:
            for task in self:
                if task.state != vals["state"]:
                    task._ldm_check_transition(vals["state"], trusted)
            vals = dict(vals, date_state_changed=fields.Datetime.now())
            if vals["state"] in CLOSED_STATES:
                vals.setdefault("date_closed", fields.Date.context_today(self))
            else:
                vals.setdefault("date_closed", False)
        result = super().write(vals)
        if "attachment_ids" in vals:
            self._ldm_adopt_attachments()
        if "lawyer_id" in vals:
            for task in self.filtered(lambda t: t.lawyer_id and t.lawyer_id not in t.lawyer_ids):
                task.lawyer_ids = [(4, task.lawyer_id.id)]
        return result

    def _ldm_adopt_attachments(self):
        """Files uploaded on a record before its first save are stored without a
        record id, and Odoo lets only the uploader open those. Attach the current
        user's own uploads to the record so its team can read them."""
        uid = self.env.uid
        for record in self:
            orphans = record.sudo().attachment_ids.filtered(
                lambda a: not a.res_id and a.res_model in (False, record._name) and a.create_uid.id == uid)
            if orphans:
                orphans.write({"res_model": record._name, "res_id": record.id})

    def unlink(self):
        self.check_access("unlink")
        if not self.env.user.has_group("legal_department_management.group_legal_manager") and not self.env.su:
            raise UserError(_("Only a legal manager can delete a matter. Cancel or archive it instead."))
        return super().unlink()

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def _ldm_is_manager(self):
        return self.env.user.has_group("legal_department_management.group_legal_manager")

    @api.model
    def _ldm_feature(self, xmlid):
        """True when a feature switch is on: the switch implies its group onto
        every internal user, so we ask the employee group, not the current user
        (the cron runs as OdooBot)."""
        group = self.env.ref(f"legal_department_management.{xmlid}", raise_if_not_found=False)
        return bool(group) and group in self.env.ref("base.group_user").sudo().all_implied_ids

    def _ldm_needs_approval(self):
        self.ensure_one()
        return (self._ldm_feature("group_ldm_approvals") and self.template_id.requires_approval
                and self.approval_state != "approved")

    def _ldm_check_transition(self, new_state, trusted=False):
        self.ensure_one()
        old_state = self.state
        who = TRANSITIONS.get((old_state, new_state))
        labels = dict(self._fields["state"]._description_selection(self.env))
        if not who:
            raise UserError(_("%(matter)s cannot go from “%(old)s” to “%(new)s”.",
                              matter=self.display_name, old=labels[old_state], new=labels[new_state]))
        if who == "engine" and not trusted:
            if new_state == "done":
                raise UserError(_("Use “Close matter” to close %s: it asks for the outcome.", self.display_name))
            raise UserError(_("Use “Cancel matter” to cancel %s: it asks for the reason.", self.display_name))
        if who == "manager" and not (trusted or self._ldm_is_manager()):
            raise UserError(_("Only a legal manager can move %(matter)s back to “%(new)s”.",
                              matter=self.display_name, new=labels[new_state]))
        if old_state == "draft" and new_state in ("in_progress", "pending_docs") and self._ldm_needs_approval():
            raise UserError(_("%s needs approval before work starts. Send it for approval first.", self.display_name))
        if new_state == "in_progress" and self.kind == "government" and not self.department_id:
            raise UserError(_("Choose the government body for %s before starting it.", self.display_name))
        if new_state == "draft" and self.approval_state == "approved":
            raise UserError(_("%s is approved; reset its approval before sending it back to New.", self.display_name))

    def _ldm_set_state(self, new_state):
        for task in self:
            if task.state != new_state:
                task.write({"state": new_state})
        return True

    def action_set_in_progress(self):
        return self._ldm_set_state("in_progress")

    def action_set_pending_docs(self):
        return self._ldm_set_state("pending_docs")

    def action_set_draft(self):
        return self._ldm_set_state("draft")

    def action_set_done(self):
        """Closing asks for the outcome: open the closing dialog."""
        return self._ldm_open_decision("close")

    def action_set_cancelled(self):
        if not self.env.user.has_group("legal_department_management.group_legal_user"):
            raise AccessError(_("Only a lawyer can cancel a matter."))
        return self._ldm_open_decision("cancel")

    def _ldm_open_decision(self, mode):
        titles = {"close": _("Close matter"), "cancel": _("Cancel matter"), "reject": _("Reject")}
        return {
            "type": "ir.actions.act_window",
            "name": titles[mode],
            "res_model": "legal.task.decision.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_task_ids": self.ids, "default_mode": mode},
        }

    def _ldm_close(self, outcome, note):
        self.check_access("write")
        outcome = outcome or "completed"
        for task in self:
            with engine_guard():
                task.write({"state": "done", "outcome": outcome, "close_note": note or False})
            label = dict(task._fields["outcome"]._description_selection(task.env)).get(outcome)
            task.message_post(body=_("Matter closed: %(outcome)s. %(note)s", outcome=label, note=note or ""))

    def _ldm_cancel(self, note):
        if not (note or "").strip():
            raise UserError(_("Say why the matter is cancelled."))
        if not self.env.user.has_group("legal_department_management.group_legal_user"):
            raise AccessError(_("Only a lawyer can cancel a matter."))
        self.check_access("write")
        for task in self:
            with engine_guard():
                task.write({"state": "cancelled", "close_note": note})
            task.message_post(body=_("Matter cancelled: %s", note))

    # ------------------------------------------------------------------
    # Approval (method names kept from 19.0.6.3.0)
    # ------------------------------------------------------------------
    def _ldm_check_approver(self):
        if not self.env.user.has_group("legal_department_management.group_ldm_approver"):
            raise AccessError(_("Only an approver can decide on a matter."))
        for task in self:
            if task.approval_state != "to_approve":
                raise UserError(_("%s is not waiting for approval.", task.display_name))
            if (task.company_id.ldm_approval_sod and task.approval_requested_by_id == self.env.user
                    and not self.env.su):
                raise UserError(_("You sent %s for approval, so someone else must decide on it.", task.display_name))

    def action_request_approval(self):
        for task in self:
            if task.approval_state not in ("draft", "rejected"):
                raise UserError(_("%s is already approved or waiting for approval.", task.display_name))
            if not (task.lawyer_id == self.env.user or self.env.user in task.lawyer_ids or task._ldm_is_manager()):
                raise AccessError(_("Only the people working on %s can send it for approval.", task.display_name))
        with engine_guard():
            self.write({"approval_state": "to_approve", "approval_requested_by_id": self.env.user.id,
                        "approver_id": False, "approval_date": False, "approval_note": False})
        for task in self:
            task.message_post(body=_("Sent for approval."))
            task._ldm_notify_approvers()
        return True

    def _ldm_notify_approvers(self):
        self.ensure_one()
        group = self.env.ref("legal_department_management.group_ldm_approver")
        approvers = group.all_user_ids.filtered(
            lambda u: u.active and not u.share and u != self.env.user and self.company_id in u.company_ids)
        activity_type = self.env.ref("legal_department_management.ldm_activity_approval", raise_if_not_found=False)
        for approver in approvers[:5]:
            self.activity_schedule(
                activity_type_id=activity_type.id if activity_type else False,
                summary=_("Approve %s", self.task_number or self.name),
                user_id=approver.id,
                date_deadline=fields.Date.context_today(self))

    def action_approve(self):
        self._ldm_check_approver()
        with engine_guard():
            self.write({"approval_state": "approved", "approver_id": self.env.user.id,
                        "approval_date": fields.Datetime.now(), "approval_note": False})
        for task in self:
            task.message_post(body=_("Approved by %s.", self.env.user.name))
            task._ldm_close_reminders("ldm_activity_approval")
            if task.state == "draft":
                task.write({"state": "in_progress"})
        return True

    def action_reject(self):
        """Rejecting needs a reason: open the decision dialog."""
        self._ldm_check_approver()
        return self._ldm_open_decision("reject")

    def _ldm_reject(self, note):
        self._ldm_check_approver()
        if not (note or "").strip():
            raise UserError(_("Say why the matter is rejected."))
        with engine_guard():
            self.write({"approval_state": "rejected", "approver_id": self.env.user.id,
                        "approval_date": fields.Datetime.now(), "approval_note": note})
        for task in self:
            task.message_post(body=_("Rejected by %(user)s: %(note)s", user=self.env.user.name, note=note))
            task._ldm_close_reminders("ldm_activity_approval")
        return True

    def action_set_draft_approval(self):
        if not self._ldm_is_manager():
            raise AccessError(_("Only a legal manager can reset an approval."))
        with engine_guard():
            self.write({"approval_state": "draft", "approver_id": False, "approval_date": False,
                        "approval_note": False, "approval_requested_by_id": False})
        for task in self:
            task.message_post(body=_("Approval reset by %s.", self.env.user.name))
        return True

    def _ldm_close_reminders(self, type_xmlid, summary=None):
        """Mark done the reminder activities of one kind (and optional summary)."""
        activity_type = self.env.ref(f"legal_department_management.{type_xmlid}", raise_if_not_found=False)
        if not activity_type:
            return
        for task in self:
            activities = task.activity_ids.filtered(
                lambda a: a.activity_type_id == activity_type and (summary is None or a.summary == summary))
            if activities:
                activities.sudo().action_feedback(feedback=_("Done"))

    # ------------------------------------------------------------------
    # Matter types
    # ------------------------------------------------------------------
    @api.model
    def create_from_template(self, vals):
        """Open a matter the way the quick-create dialog does: the type fills in
        the body, the responsible, the target date, the steps (working days) and
        the documents to collect. ``vals`` holds the answers plus optional
        ``key_date`` (first session for lawsuits, target date otherwise) and
        ``opponent_name`` / ``opponent_partner_id``. Returns the new matter's id."""
        vals = dict(vals)
        key_date = vals.pop("key_date", False)
        opponent_name = (vals.pop("opponent_name", "") or "").strip()
        opponent_partner_id = vals.pop("opponent_partner_id", False)
        template = self.env["legal.task.template"].browse(vals["template_id"]) if vals.get("template_id") else False
        client = self.env["legal.company"].sudo().browse(vals["legal_company_id"]) if vals.get("legal_company_id") else False
        if template:
            if template.department_id and not vals.get("department_id"):
                vals["department_id"] = template.department_id.id
            if not vals.get("lawyer_id"):
                vals["lawyer_id"] = (template.lawyer_id or (client and client.lawyer_id) or self.env.user).id
            if not vals.get("name"):
                vals["name"] = template.name + (f" — {client.name}" if client else "")
            if template.confidential_default:
                vals.setdefault("confidential", True)
        elif not vals.get("lawyer_id"):
            vals["lawyer_id"] = ((client and client.lawyer_id) or self.env.user).id
        # The person opening the matter must be able to open it afterwards.
        team = {self.env.user.id, vals["lawyer_id"]}
        vals["lawyer_ids"] = [(6, 0, list(team | set(self._ldm_ids_from_commands(vals.get("lawyer_ids")))))]
        if isinstance(key_date, str):
            key_date = fields.Date.to_date(key_date)
        kind = vals.get("kind") or (template and template.kind) or "other"
        if key_date and kind not in ("litigation", "execution"):
            vals.setdefault("due_date", key_date)
        vals.pop("state", None)
        task = self.create(vals)
        today = task.date_opened or fields.Date.context_today(task)
        company = task.company_id
        calendar = task.department_id._ldm_calendar() if task.department_id else company._ldm_calendar()
        if template:
            if not task.due_date and template.duration_days:
                task.due_date = company.ldm_add_working_days(today, template.duration_days, calendar)
            reference = today
            steps = []
            for line in template.step_ids:
                base = today if line.offset_from == "start" else reference
                due = company.ldm_add_working_days(base, line.offset_days, calendar) if line.offset_days else base
                reference = due
                user = {"responsible": task.lawyer_id, "creator": self.env.user}.get(line.responsible,
                                                                                      self.env["res.users"])
                steps.append({
                    "task_id": task.id, "sequence": line.sequence, "name": line.name, "date_due": due,
                    "user_id": user.id or False, "is_visit": line.is_visit,
                    "department_id": task.department_id.id if line.is_visit else False,
                    "document_type_id": line.document_type_id.id,
                })
            self.env["legal.task.step"].create(steps)
            docs = []
            vault = client.document_ids.filtered(lambda d: d.state != "expired") if client else self.env["legal.company.document"]
            for line in template.document_ids:
                held = vault.filtered(lambda d, t=line.document_type_id: d.document_type_id == t)[:1]
                docs.append({
                    "task_id": task.id, "sequence": line.sequence, "document_type_id": line.document_type_id.id,
                    "name": line.document_type_id.name, "mandatory": line.mandatory,
                    "state": "received" if held else "missing",
                    "company_document_id": held.id or False,
                    "attachment_id": (held.attachment_id.sudo().copy(
                        {"res_model": "legal.task", "res_id": task.id}).id if held.attachment_id else False),
                    "expiry_date": held.date_expiry or False,
                    "received_date": today if held else False,
                    "note": line.note or False,
                })
            self.env["legal.task.document"].create(docs)
        if opponent_partner_id or opponent_name:
            partner = self.env["res.partner"].browse(opponent_partner_id) if opponent_partner_id else \
                self.env["res.partner"].search([("name", "=ilike", opponent_name)], limit=1)
            if not partner:
                partner = self.env["res.partner"].sudo().create({"name": opponent_name})
            role = "defendant" if task.our_role in (False, "plaintiff", "complainant") else "plaintiff"
            self.env["legal.task.party"].create({"task_id": task.id, "partner_id": partner.id, "role": role})
        if key_date and kind in ("litigation", "execution"):
            self.env["legal.hearing"].create({
                "task_id": task.id, "kind": "hearing", "date": key_date,
                "department_id": task.department_id.id or False, "attending_user_id": task.lawyer_id.id,
            })
        # Start the work unless the type needs an approver first.
        if task._ldm_needs_approval():
            task.action_request_approval()
        elif task.state == "draft" and not (kind == "government" and not task.department_id):
            task.write({"state": "in_progress"})
        return task.id

    @api.model
    def _ldm_ids_from_commands(self, commands):
        ids = set()
        for command in commands or []:
            if isinstance(command, int):
                ids.add(command)
            elif command[0] == 6:
                ids |= set(command[2])
            elif command[0] == 4:
                ids.add(command[1])
        return ids

    # ------------------------------------------------------------------
    # Reminders (entry point name kept: SAG's noupdate cron calls it)
    # ------------------------------------------------------------------
    @api.model
    def _cron_check_upcoming_sessions(self):
        return self._ldm_run_reminders()

    @api.model
    def _ldm_run_reminders(self):
        """Keep exactly one open reminder per (matter, person, kind, subject) for
        every session, visit, deadline, step and target date that is due soon or
        late. Running it twice changes nothing. Dates are local to the legal
        calendar's timezone."""
        for company in self.env["res.company"].search([]):
            calendar = company._ldm_calendar()
            tz = (calendar and calendar.tz) or "Asia/Baghdad"
            today = fields.Date.context_today(self.with_context(tz=tz))
            horizon = company.ldm_add_working_days(today, company.ldm_reminder_days or 3)
            items = self.with_company(company)._ldm_reminder_items(company, today, horizon)
            for task, user, date, summary, type_xmlid in items:
                if not task.active or task.state in CLOSED_STATES:
                    continue
                user = user if user and user.active and not user.share else task.lawyer_id
                if not user or not user.active:
                    user = self._ldm_managers(company)[:1]
                if not user:
                    continue
                activity_type = self.env.ref(f"legal_department_management.{type_xmlid}", raise_if_not_found=False)
                existing = task.activity_ids.filtered(
                    lambda a: a.user_id == user and a.summary == summary and a.activity_type_id == activity_type)
                if existing:
                    if existing[0].date_deadline != date:
                        existing[0].sudo().date_deadline = date
                    continue
                task.sudo().activity_schedule(
                    activity_type_id=activity_type.id if activity_type else False,
                    summary=summary, user_id=user.id, date_deadline=date)
        return True

    @api.model
    def _ldm_managers(self, company):
        group = self.env.ref("legal_department_management.group_legal_manager")
        return group.all_user_ids.filtered(lambda u: u.active and not u.share and company in u.company_ids)

    @api.model
    def _ldm_reminder_items(self, company, today, horizon):
        """Return (matter, user, date, summary, activity type xmlid) tuples to
        remind about. Streams add their own sources by extending this method.
        Summaries are written in the responsible person's language."""
        items = []
        for hearing in self.env["legal.hearing"].search([("company_id", "=", company.id), ("state", "=", "planned"),
                                                         ("date", ">=", today), ("date", "<=", horizon)]):
            user = hearing.attending_user_id or hearing.task_id.lawyer_id
            summary = _("Court session on %(date)s — %(number)s", date=hearing.date,
                        number=hearing.task_id.task_number)
            items.append((hearing.task_id, user, hearing.date, summary, "ldm_activity_session"))
        for deadline in self.env["legal.deadline"].search([("company_id", "=", company.id), ("state", "=", "open"),
                                                           ("task_id", "!=", False), ("date_safe", "!=", False),
                                                           ("date_safe", "<=", horizon)]):
            summary = _("Deadline: %(name)s — %(number)s", name=deadline.name, number=deadline.task_id.task_number)
            items.append((deadline.task_id, deadline.user_id or deadline.task_id.lawyer_id, deadline.date_safe,
                          summary, "ldm_activity_deadline"))
        for step in self.env["legal.task.step"].search([("company_id", "=", company.id), ("state", "=", "todo"),
                                                        ("date_due", "!=", False), ("date_due", "<=", horizon)]):
            summary = _("Step: %(name)s — %(number)s", name=step.name, number=step.task_id.task_number)
            items.append((step.task_id, step.user_id or step.task_id.lawyer_id, step.date_due, summary,
                          "ldm_activity_step"))
        for task in self.search([("company_id", "=", company.id), ("state", "in", OPEN_STATES),
                                 ("due_date", "!=", False), ("due_date", "<=", horizon)]):
            items.append((task, task.lawyer_id, task.due_date, _("Target date — %s", task.task_number),
                          "ldm_activity_target"))
        return items

    # ------------------------------------------------------------------
    # Cross-stream interfaces (SPEC 11): working minimal versions that the
    # owning stream replaces, so every stream can call them from day one.
    # ------------------------------------------------------------------
    def action_ldm_record_outcome(self):
        """Record the outcome of this matter's next planned session."""
        self.ensure_one()
        hearing = self.hearing_ids.filtered(lambda h: h.state == "planned").sorted("date")[:1]
        if not hearing:
            raise UserError(_("%s has no planned court session.", self.display_name))
        return hearing.action_ldm_record_outcome()

    @api.model
    def ldm_conflict_check(self, names, task_id=False):
        """Check names against the office's clients and opposing parties.
        Returns {"hits": [...], "policy": "warn"|"block", "check_id": id or False}.
        The money stream implements the search; the foundation finds nothing."""
        return {"hits": [], "policy": self.env.company.ldm_conflict_policy, "check_id": False}

    # ------------------------------------------------------------------
    # Printing (name kept)
    # ------------------------------------------------------------------
    def action_print_task_report(self):
        return self.env.ref("legal_department_management.action_report_legal_task").report_action(self)

    @api.constrains("contract_start", "contract_end")
    def _check_contract_dates(self):
        for task in self:
            if task.contract_start and task.contract_end and task.contract_end < task.contract_start:
                raise ValidationError(_("The contract cannot end before it starts."))
