# -*- coding: utf-8 -*-
from odoo import api, fields, models

MATTER_KINDS = [
    ("government", "Government transaction"),
    ("litigation", "Lawsuit"),
    ("execution", "Execution"),
    ("contract", "Contract"),
    ("opinion", "Legal opinion"),
    ("corporate", "Company affairs"),
    ("investigation", "Investigation"),
    ("other", "Other"),
]


LAW_BRANCHES = [
    ("civil", "Civil"),
    ("commercial", "Commercial"),
    ("personal_status", "Personal status"),
    ("labour", "Labour"),
    ("criminal", "Criminal"),
    ("administrative", "Administrative"),
    ("other", "Other"),
]


class LegalTaskTemplate(models.Model):
    """A matter type. Choosing one when a matter is opened fills in the body,
    the responsible person, the target date, the steps with their working-day
    offsets and the documents to collect."""

    _name = "legal.task.template"
    _description = "Matter type"
    _order = "sequence, name"

    name = fields.Char(string="Name", required=True, translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one("res.company", string="Company", index=True,
                                 help="Leave empty to share the type with every company.")
    kind = fields.Selection(MATTER_KINDS, string="Kind", required=True, default="other")
    law_branch = fields.Selection(LAW_BRANCHES, string="Branch of law",
                                  help="Decides which appeal periods apply and whether the fee cap applies.")
    target_days = fields.Integer(aggregator=None, string="Days allowed at the body",
                                 help="Working days the body is expected to take once the file is submitted.")
    confidential_default = fields.Boolean(string="Confidential by default")
    track_coverage = fields.Boolean(string="Track for every company",
                                    help="Show, for each company, whether this service was done this year.")
    description = fields.Text(string="Description", translate=True)
    department_id = fields.Many2one("legal.department", string="Default body", ondelete="set null")
    lawyer_id = fields.Many2one("res.users", string="Default responsible", ondelete="set null")
    duration_days = fields.Integer(aggregator=None, string="Expected duration (working days)", default=0)
    requires_approval = fields.Boolean(string="Needs approval before work starts")
    color = fields.Integer(aggregator=None, string="Colour")
    properties_definition = fields.PropertiesDefinition(string="Extra fields")
    step_ids = fields.One2many("legal.task.template.step", "template_id", string="Steps", copy=True)
    document_ids = fields.One2many("legal.task.template.document", "template_id", string="Documents to collect", copy=True)
    fee_amount = fields.Monetary(string="Typical government fee", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", string="Currency",
                                 default=lambda self: self.env.company.currency_id)
    default_fee_type = fields.Selection(
        [
            ("lump_sum", "Lump sum"),
            ("installments", "Instalments"),
            ("success", "Success fee"),
            ("retainer", "Retainer"),
            ("per_transaction", "Per transaction"),
            ("per_hearing", "Per hearing"),
            ("consultation", "Consultation"),
            ("hourly", "Hourly"),
        ],
        string="Usual fee arrangement",
    )
    task_ids = fields.One2many("legal.task", "template_id", string="Matters")
    usage_count = fields.Integer(string="Matters opened", compute="_compute_usage_count")

    def _compute_usage_count(self):
        groups = self.env["legal.task"]._read_group([("template_id", "in", self.ids)], ["template_id"], ["__count"])
        counts = {template.id: count for template, count in groups}
        for template in self:
            template.usage_count = counts.get(template.id, 0)

    def action_view_tasks(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_legal_task")
        action.update({"domain": [("template_id", "=", self.id)], "context": {"default_template_id": self.id}})
        return action


# Arabic for the steps of the matter types shipped in data/ldm_template_data.xml.
# Those steps are written inline in the data file, so they have no xmlid and the
# catalogue export never offers them for translation.
SHIPPED_STEPS_AR = {
    "Collect the documents": "جمع المستمسكات",
    "Submit the file at the counter": "تقديم المعاملة إلى الجهة",
    "Follow up and collect the result": "متابعة المعاملة واستلام النتيجة",
    "Draft the petition": "تحرير عريضة الدعوى",
    "Pay the court fee and register the case": "دفع رسم الدعوى وتسجيلها",
    "Follow the service of the summons": "متابعة تبليغ الخصم بعريضة الدعوى",
    "File the complaint with the investigating judge": "تقديم الشكوى إلى قاضي التحقيق",
    "Submit the grievance to the authority": "تقديم التظلّم إلى الجهة الإدارية",
    "Open the file at the execution directorate": "فتح الإضبارة التنفيذية في مديرية التنفيذ",
    "Follow the service of the execution notice": "متابعة تبليغ المدين بالإخطار التنفيذي",
    "Review and send comments": "تدقيق العقد وإرسال الملاحظات",
    "Agree the final text": "الاتفاق على الصيغة النهائية",
    "Research and draft the opinion": "البحث وكتابة الرأي",
    "Issue the opinion": "إصدار الرأي",
    "Prepare the power of attorney text": "إعداد نص الوكالة",
    "Sign it at the notary": "توقيع الوكالة لدى كاتب العدل",
}


class LegalTaskTemplateStep(models.Model):
    _name = "legal.task.template.step"
    _description = "Matter type step"
    _order = "sequence, id"

    @api.model
    def _ldm_translate_shipped_steps(self):
        """Give the shipped matter types' steps their Arabic. Runs on every install
        and upgrade; a step someone has already translated or renamed is left alone."""
        if not self.env["res.lang"]._lang_get("ar_001"):
            return
        steps = self.sudo().with_context(lang="en_US").search([("name", "in", list(SHIPPED_STEPS_AR))])
        for step in steps:
            arabic = step.with_context(lang="ar_001").name
            if not arabic or arabic == step.name:
                step.update_field_translations("name", {"ar_001": SHIPPED_STEPS_AR[step.name]})

    template_id = fields.Many2one("legal.task.template", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Step", required=True, translate=True)
    offset_days = fields.Integer(aggregator=None, string="Working days", default=0,
                                 help="Working days after the reference date at which the step is due.")
    offset_from = fields.Selection(
        [("start", "From the opening date"), ("previous", "From the previous step")],
        string="Counted from", default="previous", required=True)
    responsible = fields.Selection(
        [("responsible", "The matter's responsible"), ("creator", "Whoever opens the matter"), ("nobody", "Nobody yet")],
        string="Assigned to", default="responsible", required=True)
    is_visit = fields.Boolean(string="Visit to the body", help="The step is done at a government counter.")
    document_type_id = fields.Many2one("legal.document.type", string="Produces document", ondelete="set null")


class LegalTaskTemplateDocument(models.Model):
    _name = "legal.task.template.document"
    _description = "Document to collect for a matter type"
    _order = "sequence, id"

    template_id = fields.Many2one("legal.task.template", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    document_type_id = fields.Many2one("legal.document.type", string="Document", required=True, ondelete="restrict")
    mandatory = fields.Boolean(string="Mandatory", default=True)
    note = fields.Char(string="Note", translate=True)
