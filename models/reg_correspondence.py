# -*- coding: utf-8 -*-
"""The correspondence register (الصادر والوارد) and letter templates.

A letter enters the book when it is registered: it takes the next number of its
direction for its year (a number typed before registration is kept, and the
book continues after it), and from then on its number, date and direction are
what the other side has in its own book, so they are locked in ``write`` and a
mistake is voided with a reason, never deleted."""
import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.fields import Domain
from odoo.tools import is_html_empty
from odoo.tools.misc import format_date

from .ldm_engine import engine_guard, in_engine
from .reg_common import adopt_attachments, attach_report, close_activities, sync_deadline, value_of
from .reg_render import placeholder_values, render_line, render_text

LOCKED_ONCE_REGISTERED = ("number", "direction", "date")
LETTER_GUARDED = ("state", "void_reason")
SEQUENCE_CODES = {"incoming": "legal.correspondence.incoming", "outgoing": "legal.correspondence.outgoing"}


class LegalLetterTemplate(models.Model):
    _inherit = "legal.letter.template"

    usage_note = fields.Char(string="When to use it", translate=True)

    def ldm_render(self, values, lang=None):
        """``(subject, body_html)`` of this template filled from ``values``."""
        self.ensure_one()
        template = self.with_context(lang=lang) if lang else self
        return (render_line(self.env, template.subject or "", values),
                render_text(self.env, template.body or "", values))

    def _ldm_set_translations(self, translations):
        """Data helper for the seed templates: ``{field: {lang: text}}``.

        A translation is written only for an installed language and only where
        the field has none yet (it still shows the English source), so running
        it on every upgrade never overwrites a text somebody rewrote."""
        installed = {code for code, _name in self.env["res.lang"].get_installed()}
        for template in self.exists():
            for field_name, by_lang in translations.items():
                source = template.with_context(lang="en_US")[field_name]
                values = {}
                for lang, text in by_lang.items():
                    if lang not in installed:
                        continue
                    current = template.with_context(lang=lang)[field_name]
                    if not current or current == source:
                        values[lang] = text
                if values:
                    template.update_field_translations(field_name, values)
        return True

    @api.model
    def _ldm_seed_translations(self, xmlid, translations):
        """Called from the module data on every install and upgrade; a seed
        template the manager deleted is simply skipped."""
        template = self.env.ref(xmlid, raise_if_not_found=False)
        if template and template._name == self._name:
            template._ldm_set_translations(translations)
        return True


class LegalCorrespondence(models.Model):
    _inherit = "legal.correspondence"
    _rec_names_search = ["number", "name", "sender_ref"]

    assigned_user_id = fields.Many2one("res.users", string="Referred to", tracking=True, index=True,
                                       help="The person who must act on the letter.")
    reply_days = fields.Integer(string="Answer within (working days)",
                                help="Working days from the date the letter was received (incoming) or sent "
                                "(outgoing) to the date an answer is due.")
    reply_due_date = fields.Date(tracking=True)
    reply_done = fields.Boolean(string="Answered", tracking=True, copy=False,
                                help="Set when a reply to this letter is registered, or by hand when it was "
                                "answered some other way.")
    reply_state = fields.Selection(
        [("none", "No answer expected"), ("waiting", "Awaiting answer"), ("overdue", "Answer overdue"),
         ("answered", "Answered")],
        string="Answer", compute="_compute_reply_state", search="_search_reply_state")
    reply_ids = fields.One2many("legal.correspondence", "reply_to_id", string="Replies")
    instruction_days = fields.Integer(string="Instruction due in (working days)")
    instruction_due = fields.Date(tracking=True)
    party_display = fields.Char(string="From / to", compute="_compute_party_display")
    guarantee_id = fields.Many2one("legal.guarantee", string="Letter of guarantee", ondelete="set null", index=True)
    poa_id = fields.Many2one("legal.poa", string="Power of attorney", ondelete="set null", index=True)
    ldm_numbering = fields.Boolean(compute="_compute_ldm_numbering",
                                   help="The correspondence register is switched on: letters get numbers.")

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("number", "name")
    def _compute_display_name(self):
        for letter in self:
            letter.display_name = f"{letter.number} · {letter.name}" if letter.number else (letter.name or "")

    @api.depends("department_id", "partner_id")
    def _compute_party_display(self):
        for letter in self:
            letter.party_display = letter.department_id.name or letter.partner_id.name or False

    @api.depends_context("uid")
    def _compute_ldm_numbering(self):
        on = self.env["legal.task"]._ldm_feature("group_ldm_correspondence")
        for letter in self:
            letter.ldm_numbering = on

    def _ldm_calendar(self):
        self.ensure_one()
        if self.direction == "outgoing" and self.department_id:
            return self.department_id._ldm_calendar()
        return self.company_id._ldm_calendar()

    def _ldm_due_dates(self, vals=None):
        """Due dates from the working-day counts: ``{field: date}`` for the
        counts that are set. ``vals`` overrides the record's values (onchange,
        create and write all go through here)."""
        self.ensure_one()
        vals = vals or {}
        get = lambda name: vals[name] if name in vals else self[name]  # noqa: E731
        start = fields.Date.to_date(get("received_date") or get("date")) or fields.Date.context_today(self)
        company = self.env["res.company"].browse(vals["company_id"]) if vals.get("company_id") else             (self.company_id or self.env.company)
        result = {}
        if (get("reply_days") or 0) > 0:
            direction = get("direction")
            body = self.env["legal.department"].browse(vals["department_id"]) if vals.get("department_id") else                 self.department_id
            calendar = body._ldm_calendar() if direction == "outgoing" and body else company._ldm_calendar()
            result["reply_due_date"] = company.ldm_add_working_days(start, get("reply_days"), calendar)
        if (get("instruction_days") or 0) > 0:
            result["instruction_due"] = company.ldm_add_working_days(start, get("instruction_days"))
        return result

    @api.onchange("reply_days", "instruction_days", "received_date", "date", "department_id", "direction")
    def _onchange_due_days(self):
        for field, value in self._ldm_due_dates().items():
            self[field] = value

    @api.depends("state", "reply_due_date", "reply_done")
    def _compute_reply_state(self):
        today = fields.Date.context_today(self)
        for letter in self:
            if not letter.reply_due_date or letter.state == "void":
                letter.reply_state = "none"
            elif letter.reply_done:
                letter.reply_state = "answered"
            elif letter.reply_due_date < today:
                letter.reply_state = "overdue"
            else:
                letter.reply_state = "waiting"

    def _search_reply_state(self, operator, value):
        if operator not in ("=", "!=", "in", "not in"):
            return NotImplemented
        today = fields.Date.context_today(self)
        expected = Domain("reply_due_date", "!=", False) & Domain("state", "!=", "void")
        domains = {
            "none": ~expected,
            "answered": expected & Domain("reply_done", "=", True),
            "overdue": expected & Domain("reply_done", "=", False) & Domain("reply_due_date", "<", today),
            "waiting": expected & Domain("reply_done", "=", False) & Domain("reply_due_date", ">=", today),
        }
        values = [value] if isinstance(value, str) else list(value)
        domain = Domain.OR([domains[v] for v in values if v in domains] or [Domain.FALSE])
        return domain if operator in ("=", "in") else ~domain

    # ------------------------------------------------------------------
    # Onchange: a template fills the letter
    # ------------------------------------------------------------------
    @api.onchange("template_id")
    def _onchange_template_id(self):
        if self.template_id and self.state == "draft":
            values = placeholder_values(self.env, letter=self, lang=self.lang)
            subject, body = self.template_id.ldm_render(values, lang=self.lang)
            if subject:
                self.name = subject
            self.body_html = body

    @api.onchange("task_id")
    def _onchange_task_id(self):
        if self.task_id:
            self.legal_company_id = self.task_id.legal_company_id
            if not self.department_id:
                self.department_id = self.task_id.department_id

    # ------------------------------------------------------------------
    # CRUD: the register only moves forward
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        if not (in_engine() or self.env.su):
            for vals in vals_list:
                for field in LETTER_GUARDED:
                    vals.pop(field, None)
        for vals in vals_list:
            if vals.get("task_id") and not vals.get("legal_company_id"):
                vals["legal_company_id"] = self.env["legal.task"].browse(vals["task_id"]).legal_company_id.id
            for field, value in self.new(vals)._ldm_due_dates(vals).items():
                vals.setdefault(field, value)
        letters = super().create(vals_list)
        adopt_attachments(letters)
        return letters

    def _ldm_changes(self, name, new_value):
        """Is the write really changing the field? A form that is saved again
        sends unchanged values back; only a real change is refused."""
        self.ensure_one()
        field = self._fields[name]
        if field.type == "date":
            return fields.Date.to_date(new_value) != self[name]
        return (new_value or False) != (value_of(self, name) or False)

    def write(self, vals):
        if not (in_engine() or self.env.su):
            if set(vals) & set(LETTER_GUARDED):
                raise AccessError(_("A letter enters the register through “Register” and leaves it through "
                                    "“Void”: its status cannot be edited."))
            locked = set(vals) & set(LOCKED_ONCE_REGISTERED)
            if locked:
                for letter in self.filtered(lambda l: l.state != "draft"):
                    changed = [name for name in locked if letter._ldm_changes(name, vals[name])]
                    if changed:
                        raise AccessError(_(
                            "%(letter)s is in the register, so its %(fields)s cannot change: the other side "
                            "has it in their book. Void it with a reason and register a new letter.",
                            letter=letter.display_name,
                            fields=", ".join(letter._fields[n]._description_string(self.env) for n in changed)))
        if {"reply_days", "instruction_days", "received_date", "date"} & set(vals):
            for letter in self:
                due = {k: v for k, v in letter._ldm_due_dates(vals).items() if k not in vals}
                if due:
                    super(LegalCorrespondence, letter).write(due)
        result = super().write(vals)
        if "attachment_ids" in vals:
            adopt_attachments(self)
        if {"reply_due_date", "reply_done", "instruction_due", "assigned_user_id", "task_id", "reply_days",
                "instruction_days", "received_date", "date"} & set(vals):
            self.filtered(lambda l: l.state == "registered")._ldm_sync_deadlines()
        return result

    def unlink(self):
        booked = self.filtered(lambda l: l.state != "draft")
        if booked and not self.env.su:
            raise UserError(_("%s has a register number and cannot be deleted. Void it with a reason: the number "
                              "stays in the book, struck through.", ", ".join(booked.mapped("display_name"))))
        return super().unlink()

    # ------------------------------------------------------------------
    # Registration and numbering
    # ------------------------------------------------------------------
    def _ldm_sequence(self):
        self.ensure_one()
        return self.env["ir.sequence"].sudo().search(
            [("code", "=", SEQUENCE_CODES[self.direction]), ("company_id", "in", [self.company_id.id, False])],
            order="company_id", limit=1)

    def _ldm_next_number(self):
        self.ensure_one()
        sequence = self._ldm_sequence()
        if not sequence:
            raise UserError(_("There is no numbering sequence for %s letters.",
                              dict(self._fields["direction"]._description_selection(self.env))[self.direction]))
        return sequence._next(sequence_date=self.date)

    def _ldm_continue_after(self, number):
        """A number typed by hand in the book's own format ("2026/1247") moves
        the book on, so the next letter gets 1248: a department that starts using
        the register in October is already at 1,247."""
        self.ensure_one()
        sequence = self._ldm_sequence()
        match = re.match(r"^(.*?)(\d+)\s*$", number or "")
        if not sequence or not match:
            return
        current = sequence._get_current_sequence(sequence_date=self.date)
        prefix = sequence.with_context(ir_sequence_date=self.date,
                                       ir_sequence_date_range=getattr(current, "date_from", False) or False
                                       )._get_prefix_suffix()[0]
        if match.group(1) != prefix:
            return
        typed = int(match.group(2))
        if typed >= current.number_next_actual:
            current.sudo().number_next_actual = typed + 1

    def _ldm_check_unique(self, number):
        self.ensure_one()
        year_start, year_end = self.date.replace(month=1, day=1), self.date.replace(month=12, day=31)
        clash = self.sudo().search([
            ("id", "!=", self.id), ("company_id", "=", self.company_id.id), ("direction", "=", self.direction),
            ("number", "=", number), ("state", "!=", "draft"), ("date", ">=", year_start), ("date", "<=", year_end)],
            limit=1)
        if clash:
            raise UserError(_("Number %(number)s is already in the %(direction)s register for %(year)s.",
                              number=number, year=self.date.year,
                              direction=dict(self._fields["direction"]._description_selection(self.env))[self.direction]))

    def action_register(self):
        """Put the letter in the book: its number, then its clocks."""
        if not self.env["legal.task"]._ldm_feature("group_ldm_correspondence"):
            raise UserError(_("The correspondence register is switched off in Settings, so letters are not numbered."))
        self.check_access("write")
        today = fields.Date.context_today(self)
        for letter in self:
            if letter.state != "draft":
                raise UserError(_("%s is already in the register.", letter.display_name))
            if not (letter.name or "").strip():
                raise UserError(_("Give the letter a subject before registering it."))
            typed = (letter.number or "").strip()
            number = typed or letter._ldm_next_number()
            letter._ldm_check_unique(number)
            if typed:
                letter._ldm_continue_after(typed)
            values = {"number": number, "state": "registered"}
            if letter.direction == "incoming" and not letter.received_date:
                values["received_date"] = today
            with engine_guard():
                letter.write(values)
            letter.message_post(body=_("Registered as %(number)s on %(date)s.", number=number, date=letter.date))
            letter._ldm_sync_deadlines()
            if letter.reply_to_id and not letter.reply_to_id.reply_done:
                letter.reply_to_id.sudo()._ldm_mark_answered(letter)
        return True

    def _ldm_mark_answered(self, reply=None):
        for letter in self:
            letter.write({"reply_done": True})
            letter.message_post(body=_("Answered by %s.", reply.display_name) if reply else _("Marked as answered."))
            close_activities(letter, "ldm_activity_letter_reply")
        return True

    def action_ldm_mark_answered(self):
        self.check_access("write")
        return self.filtered(lambda l: not l.reply_done)._ldm_mark_answered()

    def action_ldm_void(self):
        self.ensure_one()
        if self.state == "void":
            raise UserError(_("%s is already void.", self.display_name))
        return {
            "type": "ir.actions.act_window",
            "name": _("Void letter"),
            "res_model": "legal.correspondence.void.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_correspondence_id": self.id},
        }

    def _ldm_void(self, reason):
        if not (reason or "").strip():
            raise UserError(_("Say why the letter is voided."))
        self.check_access("write")
        for letter in self:
            if letter.state == "void":
                raise UserError(_("%s is already void.", letter.display_name))
            with engine_guard():
                letter.write({"state": "void", "void_reason": reason})
            letter.message_post(body=_("Voided by %(user)s: %(reason)s", user=self.env.user.name, reason=reason))
            letter._ldm_sync_deadlines()
            close_activities(letter, "ldm_activity_letter_reply")
        return True

    # ------------------------------------------------------------------
    # Clocks
    # ------------------------------------------------------------------
    def _ldm_owner(self):
        self.ensure_one()
        user = self.assigned_user_id or self.task_id.lawyer_id or self.create_uid
        return user if user.active and not user.share else self.env["res.users"]

    def _ldm_sync_deadlines(self):
        """The answer and the instruction of a registered letter are deadlines
        (counted in working days); answering or voiding closes them."""
        for letter in self:
            live = letter.state == "registered"
            common = {
                "task_id": letter.task_id.id or False,
                "legal_company_id": letter.legal_company_id.id or False,
                "company_id": letter.company_id.id,
                "user_id": letter._ldm_owner().id or False,
                "date_start": letter.received_date or letter.date,
            }
            if live and letter.reply_due_date and not letter.reply_done:
                name = (_("Answer letter %s", letter.display_name) if letter.direction == "incoming"
                        else _("Follow up the answer to letter %s", letter.display_name))
                sync_deadline(letter, "reply", dict(common, name=name, date_safe=letter.reply_due_date,
                                                    date_deadline=letter.reply_due_date))
            else:
                sync_deadline(letter, "reply", None, close_state="done" if letter.reply_done else "cancelled")
            if live and letter.instruction_due:
                sync_deadline(letter, "custom", dict(
                    common, name=_("Act on the instruction on letter %s", letter.display_name),
                    date_safe=letter.instruction_due, date_deadline=letter.instruction_due,
                    note=(letter.referral_note or "")[:250] or False))
            else:
                sync_deadline(letter, "custom", None, close_state="cancelled")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_ldm_open_matter(self):
        self.ensure_one()
        if self.task_id:
            raise UserError(_("%(letter)s already belongs to %(matter)s.", letter=self.display_name,
                              matter=self.task_id.display_name))
        return {
            "type": "ir.actions.act_window",
            "name": _("Open a matter from this letter"),
            "res_model": "legal.reg.matter.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_correspondence_id": self.id},
        }

    def action_ldm_reply(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Reply"),
            "res_model": "legal.correspondence",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_direction": "outgoing" if self.direction == "incoming" else "incoming",
                "default_reply_to_id": self.id,
                "default_name": self.name,
                "default_department_id": self.department_id.id,
                "default_partner_id": self.partner_id.id,
                "default_task_id": self.task_id.id,
                "default_legal_company_id": self.legal_company_id.id,
            },
        }

    def action_ldm_print_letter(self):
        self.ensure_one()
        if self.direction != "outgoing":
            raise UserError(_("Only outgoing letters are printed from here; an incoming letter is filed as received."))
        if is_html_empty(self.body_html):
            raise UserError(_("Write the letter, or choose a template, before printing it."))
        return self.env.ref("legal_department_management.action_report_ldm_letter").report_action(self)

    def action_ldm_attach_pdf(self):
        """File the letter as printed: a PDF on the letter and, when it belongs
        to a matter, among the matter's files."""
        self.ensure_one()
        if self.direction != "outgoing" or is_html_empty(self.body_html):
            raise UserError(_("Only a written outgoing letter can be filed as a PDF."))
        name = self.number or self.name
        owner = self.task_id or self
        attachment = attach_report(self.env, "legal_department_management.action_report_ldm_letter", self,
                                   _("Letter %s", name), owner=owner)
        self.attachment_ids = [(4, attachment.id)]
        if self.task_id:
            self.task_id.attachment_ids = [(4, attachment.id)]
        self.message_post(body=_("Filed copy attached: %s", attachment.name), attachment_ids=[])
        return attachment

    @api.model
    def _ldm_create_document(self, values):
        """Create an outgoing draft letter from a filled template and file its
        PDF on the matter (on the letter itself when there is no matter)."""
        values = dict(values, direction="outgoing")
        if values.get("guarantee_id") and not values.get("task_id"):
            values["task_id"] = self.env["legal.guarantee"].browse(values["guarantee_id"]).task_id.id or False
        letter = self.create(values)
        owner = letter.task_id or letter
        attachment = attach_report(self.env, "legal_department_management.action_report_ldm_letter", letter,
                                   letter.name, owner=owner)
        letter.attachment_ids = [(4, attachment.id)]
        if letter.task_id:
            letter.task_id.attachment_ids = [(4, attachment.id)]
            letter.task_id.message_post(body=_("Document prepared: %s", letter.name), attachment_ids=attachment.ids)
        return letter

    def action_ldm_register_book(self):
        """The list's "Print the register book" button (with or without a selection)."""
        return {
            "type": "ir.actions.act_window",
            "name": _("Print the register book"),
            "res_model": "legal.register.book.wizard",
            "view_mode": "form",
            "target": "new",
        }

    def _ldm_direction_label(self):
        self.ensure_one()
        return dict(self._fields["direction"]._description_selection(self.env)).get(self.direction, "")

    def _ldm_lang_direction(self):
        self.ensure_one()
        lang = self.env["res.lang"]._get_data(code=self.lang or self.env.lang)
        return lang.direction or "ltr"

    def _ldm_fdate(self, value):
        """A date as the letter's language writes it."""
        self.ensure_one()
        return format_date(self.env, value, lang_code=self.lang or self.env.lang) if value else ""


class LegalTask(models.Model):
    _inherit = "legal.task"

    letter_count = fields.Integer(string="Number of letters", compute="_compute_letter_count")

    def _compute_letter_count(self):
        counts = {t.id: n for t, n in self.env["legal.correspondence"]._read_group(
            [("task_id", "in", self.ids)], ["task_id"], ["__count"])}
        for task in self:
            task.letter_count = counts.get(task.id, 0)

    def action_ldm_view_letters(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_ldm_correspondence")
        action.update({
            "name": _("Letters of %s", self.task_number or self.name),
            "domain": [("task_id", "=", self.id)],
            "context": {"default_task_id": self.id, "default_legal_company_id": self.legal_company_id.id,
                        "default_department_id": self.department_id.id},
        })
        return action

    def action_ldm_new_document(self):
        """New document from a template, in every mode (the correspondence
        switch only decides whether letters are numbered)."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("New document from a template"),
            "res_model": "legal.document.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_task_id": self.id},
        }
