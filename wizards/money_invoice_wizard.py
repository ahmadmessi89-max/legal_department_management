# -*- coding: utf-8 -*-
"""Create invoices from To invoice: one customer invoice per client and
currency, each source (instalment, time, expense) linked to its invoice line."""
from markupsafe import Markup

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError

from ..models.ldm_engine import engine_guard
from ..models.money_whatsapp import money_text

BAR_SHARE = 0.05


class LegalInvoiceWizard(models.TransientModel):
    _name = "legal.invoice.wizard"
    _description = "Create invoices from what is due"

    billable_ids = fields.Many2many("legal.billable", "ldm_invoice_wizard_billable_rel", "wizard_id", "billable_id",
                                    string="To invoice")
    journal_id = fields.Many2one("account.journal", string="Journal", domain=[("type", "=", "sale")],
                                 default=lambda self: self._default_journal())
    invoice_date = fields.Date(string="Invoice date", default=fields.Date.context_today)
    invoice_count = fields.Integer(string="Invoices", compute="_compute_summary")
    summary = fields.Html(string="Invoices to create", compute="_compute_summary", sanitize=False)

    @api.model
    def _default_journal(self):
        return self.env["account.journal"].search(
            [("type", "=", "sale"), *self.env["account.journal"]._check_company_domain(self.env.company)], limit=1)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        context = self.env.context
        if "billable_ids" in fields_list and not values.get("billable_ids") \
                and context.get("active_model") == "legal.billable" and context.get("active_ids"):
            values["billable_ids"] = [Command.set(context["active_ids"])]
        return values

    @api.depends("billable_ids")
    def _compute_summary(self):
        for wizard in self:
            groups = wizard._ldm_groups()
            wizard.invoice_count = len(groups)
            rows = [Markup("<li><b>%s</b>: %s <span class='text-muted'>(%s)</span></li>")
                    % (client.name, money_text(self.env, [(currency, sum(items.mapped("amount")))]) or "0",
                       _("%s lines", len(items)))
                    for (client, currency), items in groups.items()]
            wizard.summary = Markup("<ul class='mb-0'>%s</ul>") % Markup("").join(rows) if rows else False

    def _ldm_groups(self):
        groups = {}
        for item in self.billable_ids:
            groups.setdefault((item.legal_company_id, item.currency_id), self.env["legal.billable"])
            groups[(item.legal_company_id, item.currency_id)] |= item
        return groups

    @api.model
    def _ldm_check_rights(self):
        if not self.env.user.has_group("account.group_account_invoice"):
            raise AccessError(_("Creating invoices needs invoicing rights (the Billing role)."))

    @api.model
    def ldm_open(self, billables=None, tasks=None, clients=None, engagement=None):
        """Open the dialog on what is waiting to be invoiced for these records."""
        self._ldm_check_rights()
        if billables is None:
            domain = []
            if tasks:
                domain = [("task_id", "in", tasks.ids)]
            elif clients:
                domain = [("legal_company_id", "in", clients.ids)]
            elif engagement:
                domain = ["|", ("engagement_id", "=", engagement.id), ("task_id", "in", engagement.task_ids.ids)]
            billables = self.env["legal.billable"].search(domain)
        if not billables:
            raise UserError(_("Nothing is waiting to be invoiced here. Instalments fall due with their events, time "
                              "needs approving, and expenses must be recharged to the client."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Create invoices"),
            "res_model": self._name,
            "view_mode": "form",
            "target": "new",
            "context": {"default_billable_ids": [Command.set(billables.ids)]},
        }

    # ------------------------------------------------------------------
    # Creating the invoices
    # ------------------------------------------------------------------
    def _ldm_line_values(self, item):
        if item.kind == "fee":
            line = item.fee_line_id
            name = f"{line.engagement_id.name} — {line.name}"
            return {"name": name, "quantity": 1.0, "price_unit": line.amount}
        if item.kind == "time":
            entry = item.time_entry_id
            name = f"{fields.Date.to_string(entry.date)} · {entry.user_id.name}: {entry.description}"
            return {"name": name, "quantity": entry.duration, "price_unit": entry.rate}
        expense = item.expense_id
        name = f"{expense.category_id.name}: {expense.name}" if expense.category_id else expense.name
        if expense.receipt_number:
            name += " " + _("(receipt %s)", expense.receipt_number)
        return {"name": name, "quantity": 1.0, "price_unit": expense.amount}

    def action_create(self):
        self.ensure_one()
        self._ldm_check_rights()
        items = self.env["legal.billable"].search([("id", "in", self.billable_ids.ids)])
        if not items:
            raise UserError(_("Everything selected has already been invoiced."))
        moves = self.env["account.move"]
        for (client, currency), rows in self._ldm_groups().items():
            rows = rows & items
            if rows:
                moves |= self._ldm_create_invoice(client, currency, rows)
        action = self.env["ir.actions.act_window"]._for_xml_id("account.action_move_out_invoice_type")
        if len(moves) == 1:
            action.update({"views": [[False, "form"]], "res_id": moves.id})
        else:
            action.update({"domain": [("id", "in", moves.ids)]})
        return action

    def _ldm_create_invoice(self, client, currency, rows):
        client._ldm_ensure_partner()
        company = rows.company_id[:1] or self.env.company
        tasks = rows.task_id
        commands, sources = [], []
        # Each matter's lines under its own heading, then what belongs to no matter.
        for task in [*tasks.sorted("id"), self.env["legal.task"]]:
            task_rows = rows.filtered(lambda r, t=task: r.task_id == t)
            if not task_rows:
                continue
            if len(tasks) > 1 and task:
                commands.append(Command.create({"display_type": "line_section", "name": task.display_name}))
                sources.append(None)
            for row in task_rows.sorted(lambda r: (r.kind != "fee", r.date or fields.Date.today(), r.id)):
                values = self._ldm_line_values(row)
                values["tax_ids"] = [Command.clear()]
                commands.append(Command.create(values))
                sources.append(row)
        withheld = rows.filtered(lambda r: r.kind == "fee" and r.engagement_id.bar_withholding
                                 and r.engagement_id.fee_type == "retainer")
        if withheld:
            commands.append(Command.create({
                "name": _("Bar share withheld by the client (5%%, Iraqi Bar order 3021)"),
                "quantity": 1.0, "price_unit": -currency.round(sum(withheld.mapped("amount")) * BAR_SHARE),
                "tax_ids": [Command.clear()],
            }))
            sources.append(None)
        fee_rows = rows.filtered(lambda r: r.kind == "fee")
        lawyer = (fee_rows.engagement_id[:1].lawyer_id or rows.engagement_id[:1].lawyer_id
                  or tasks[:1].lawyer_id or self.env.user)
        journal = self.journal_id if self.journal_id.company_id == company else \
            self.env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", company.id)], limit=1)
        move = self.env["account.move"].with_company(company).create({
            "move_type": "out_invoice",
            "partner_id": client.partner_id.id,
            "currency_id": currency.id,
            "journal_id": journal.id,
            "invoice_date": self.invoice_date,
            "invoice_user_id": lawyer.id,
            "invoice_origin": ", ".join(t.task_number for t in tasks if t.task_number)[:250] or False,
            # Instalments of the agreement as a whole concern all its matters.
            "ldm_task_ids": [Command.set((tasks | rows.filtered(lambda r: not r.task_id).engagement_id.task_ids).ids)],
            "invoice_line_ids": commands,
        })
        created = move.invoice_line_ids.sorted("id")
        with engine_guard():
            for line, source in zip(created, sources):
                if source is None:
                    continue
                if source.kind == "fee":
                    source.fee_line_id.sudo().write({"invoice_line_id": line.id, "state": "invoiced"})
                elif source.kind == "time":
                    source.time_entry_id.sudo().write({"invoice_line_id": line.id, "state": "invoiced"})
                else:
                    source.expense_id.sudo().write({"invoice_line_id": line.id})
        for task in tasks:
            task.sudo().message_post(body=_("Invoice %(invoice)s prepared: %(amount)s.", invoice=move.name or _("draft"),
                                            amount=money_text(self.env, [(currency, move.amount_total)]) or "0"))
        return move
