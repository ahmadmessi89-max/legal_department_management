# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

# A preset is only a set of switch values, never a code path. The switches are
# groups implied onto every internal user, so they are database-wide.
LDM_SWITCHES = (
    "group_ldm_government",
    "group_ldm_approvals",
    "group_ldm_correspondence",
    "group_ldm_requests",
    "group_ldm_corporate",
    "group_ldm_investigations",
    "group_ldm_billing",
    "group_ldm_time",
    "group_ldm_conflicts",
    "group_ldm_client_messages",
    "group_ldm_hr_team",
    "group_ldm_accounting_links",
)

LDM_PRESETS = {
    #              gov appr corr req corp inv bill time conf msg hr acc
    "department": (1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0),
    "public":     (0, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0),
    "office":     (1, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0),
    "solo":       (0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0),
    "hybrid":     (1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0),
}
LDM_PRESET_MODE = {"department": "department", "public": "department", "office": "office",
                   "solo": "office", "hybrid": "hybrid"}
LDM_PRESET_VISIBILITY = {"department": "assigned", "public": "all", "office": "assigned",
                         "solo": "all", "hybrid": "assigned"}
PRESET_SELECTION = [
    ("department", "Legal department of a company or group"),
    ("public", "Legal department of a ministry or state body"),
    ("office", "Law office"),
    ("solo", "Lawyer working alone"),
    ("hybrid", "Group legal department that also bills its companies"),
]


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ldm_preset = fields.Selection(PRESET_SELECTION, string="Kind of organisation",
                                  config_parameter="legal_department_management.preset")
    ldm_mode = fields.Selection(
        [("department", "In-house legal department"), ("office", "Law office"), ("hybrid", "Both")],
        string="Vocabulary", config_parameter="legal_department_management.mode",
        help="Department words («الشركات التابعة»), law-office words («الموكّلون») or neutral words.")
    ldm_visibility = fields.Selection(
        [("assigned", "Only the matters they work on"), ("all", "Every matter that is not confidential")],
        string="Lawyers and clerks see", config_parameter="legal_department_management.visibility")

    ldm_calendar_id = fields.Many2one(related="company_id.ldm_calendar_id", readonly=False)
    ldm_approval_sod = fields.Boolean(related="company_id.ldm_approval_sod", readonly=False)
    ldm_conflict_policy = fields.Selection(related="company_id.ldm_conflict_policy", readonly=False)
    ldm_fee_cap_check = fields.Boolean(related="company_id.ldm_fee_cap_check", readonly=False)
    ldm_reminder_days = fields.Integer(related="company_id.ldm_reminder_days", readonly=False)
    ldm_poa_warning_days = fields.Integer(related="company_id.ldm_poa_warning_days", readonly=False)
    ldm_engagement_required = fields.Boolean(related="company_id.ldm_engagement_required", readonly=False)
    ldm_retainer_min_local = fields.Monetary(related="company_id.ldm_retainer_min_local", readonly=False)
    ldm_retainer_min_foreign = fields.Monetary(related="company_id.ldm_retainer_min_foreign", readonly=False)

    group_ldm_government = fields.Boolean(
        "Government transactions", implied_group="legal_department_management.group_ldm_government",
        help="Transactions at ministries and departments: services, counter visits, the documents to carry.")
    group_ldm_approvals = fields.Boolean(
        "Approvals", implied_group="legal_department_management.group_ldm_approvals",
        help="Matters of the types that require it wait for an approver before work starts.")
    group_ldm_correspondence = fields.Boolean(
        "Correspondence register", implied_group="legal_department_management.group_ldm_correspondence",
        help="Numbered incoming and outgoing letters (صادر / وارد), the register book and reply deadlines.")
    group_ldm_requests = fields.Boolean(
        "Requests from other departments", implied_group="legal_department_management.group_ldm_requests",
        help="Every employee gets a small app to ask the legal team for help and follow the answer.")
    group_ldm_corporate = fields.Boolean(
        "Company records", implied_group="legal_department_management.group_ldm_corporate",
        help="Registration numbers, a document vault with expiry dates, letters of guarantee and "
        "recurring obligations for each company.")
    group_ldm_investigations = fields.Boolean(
        "Administrative investigations", implied_group="legal_department_management.group_ldm_investigations",
        help="Investigation committees, recommendations, decisions and compensation (تضمين).")
    group_ldm_billing = fields.Boolean(
        "Fees and invoicing", implied_group="legal_department_management.group_ldm_billing",
        help="Fee agreements, instalments and retainers, client money held, invoices and client statements.")
    group_ldm_time = fields.Boolean(
        "Time tracking", implied_group="legal_department_management.group_ldm_time",
        help="A timer on the top bar and time entries that can be invoiced.")
    group_ldm_conflicts = fields.Boolean(
        "Conflict of interest check", implied_group="legal_department_management.group_ldm_conflicts",
        help="Every new matter is checked against the office's clients and opposing parties "
        "(Advocacy Law Arts. 44 and 45).")
    group_ldm_client_messages = fields.Boolean(
        "Messages to clients", implied_group="legal_department_management.group_ldm_client_messages",
        help="Ready-written WhatsApp and email messages after a session, before an instalment, and more.")
    group_ldm_hr_team = fields.Boolean(
        "Staff team from HR", implied_group="legal_department_management.group_ldm_hr_team",
        help="Add employees who are not users to the team of a matter.")
    group_ldm_accounting_links = fields.Boolean(
        "Post expenses to accounting", implied_group="legal_department_management.group_ldm_accounting_links",
        help="Each confirmed expense can be posted as a journal entry or a payment.")

    @api.onchange("ldm_preset")
    def _onchange_ldm_preset(self):
        values = LDM_PRESETS.get(self.ldm_preset)
        if not values:
            return
        for name, value in zip(LDM_SWITCHES, values):
            self[name] = bool(value)
        self.ldm_mode = LDM_PRESET_MODE[self.ldm_preset]
        self.ldm_visibility = LDM_PRESET_VISIBILITY[self.ldm_preset]

    def set_values(self):
        super().set_values()
        self._ldm_apply_vocabulary(self.ldm_mode or "department")
        self._ldm_apply_visibility(self.ldm_visibility or "assigned")

    # ------------------------------------------------------------------
    # Applying presets outside the settings screen (install hook, upgrade)
    # ------------------------------------------------------------------
    @api.model
    def _ldm_apply_preset(self, preset):
        """Set every switch, the vocabulary and the visibility of ``preset``."""
        values = LDM_PRESETS[preset]
        employee = self.env.ref("base.group_user").sudo()
        for name, value in zip(LDM_SWITCHES, values):
            group = self.env.ref(f"legal_department_management.{name}").sudo()
            if value:
                employee._apply_group(group)
            else:
                employee._remove_group(group)
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("legal_department_management.preset", preset)
        params.set_param("legal_department_management.mode", LDM_PRESET_MODE[preset])
        params.set_param("legal_department_management.visibility", LDM_PRESET_VISIBILITY[preset])
        self._ldm_apply_vocabulary(LDM_PRESET_MODE[preset])
        self._ldm_apply_visibility(LDM_PRESET_VISIBILITY[preset])

    @api.model
    def _ldm_apply_vocabulary(self, mode):
        """Vocabulary groups follow the mode: department words, office words, or
        neither (the neutral words of the hybrid mode). Membership is computed from
        implied groups in Odoo 19, so removing the implication is enough."""
        employee = self.env.ref("base.group_user").sudo()
        department = self.env.ref("legal_department_management.group_ldm_terms_department").sudo()
        office = self.env.ref("legal_department_management.group_ldm_terms_office").sudo()
        for group, wanted in ((department, mode == "department"), (office, mode == "office")):
            if wanted:
                employee._apply_group(group)
            else:
                employee._remove_group(group)

    @api.model
    def _ldm_apply_visibility(self, visibility):
        employee = self.env.ref("base.group_user").sudo()
        see_all = self.env.ref("legal_department_management.group_ldm_see_all").sudo()
        if visibility == "all":
            employee._apply_group(see_all)
        else:
            employee._remove_group(see_all)

    def action_ldm_load_reference_data(self):
        """Implemented by the government stream (opt-in Iraqi reference library)."""
        raise UserError(_("The Iraqi reference library is not available in this version."))

    def action_ldm_open_templates(self):
        return self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_ldm_task_template")

    def action_ldm_open_bodies(self):
        return self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_legal_department")

    def action_ldm_open_holidays(self):
        return self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_ldm_holiday")
