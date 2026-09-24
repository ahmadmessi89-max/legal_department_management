# -*- coding: utf-8 -*-
"""Settings the money stream adds: whole-dinar display of IQD, and the
"fee agreement required" warning that the law-office preset switches on."""
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

# research 04 §8.2, row 4: an engagement is expected before matter work in a
# law office; the other kinds of organisation do not bill their matters.
ENGAGEMENT_REQUIRED = {"office": True}


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ldm_iqd_decimals = fields.Integer(string="IQD decimals", compute="_compute_ldm_iqd")
    ldm_iqd_can_round = fields.Boolean(string="IQD can switch to whole dinars", compute="_compute_ldm_iqd")

    def _compute_ldm_iqd(self):
        iqd = self.env.ref("base.IQD", raise_if_not_found=False)
        can_round = bool(iqd) and iqd.rounding != 1.0 and not self._ldm_iqd_used()
        for settings in self:
            settings.ldm_iqd_decimals = iqd.decimal_places if iqd else 0
            settings.ldm_iqd_can_round = can_round

    @api.model
    def _ldm_iqd_used(self):
        iqd = self.env.ref("base.IQD", raise_if_not_found=False)
        if not iqd:
            return False
        return bool(self.env["account.move.line"].sudo().search_count(
            [("parent_state", "=", "posted"), "|", ("currency_id", "=", iqd.id), ("company_currency_id", "=", iqd.id)],
            limit=1))

    def action_ldm_iqd_whole_dinars(self):
        """Show Iraqi dinars without fils: set the currency's rounding to 1.
        Offered only while no posted accounting entry uses IQD, because changing
        the rounding of a currency with posted entries would misstate them."""
        if not self.env.is_admin():
            raise AccessError(_("Only an administrator can change how a currency is rounded."))
        iqd = self.env.ref("base.IQD", raise_if_not_found=False)
        if not iqd:
            raise UserError(_("The Iraqi dinar is not available in this database."))
        if self._ldm_iqd_used():
            raise UserError(_("Posted accounting entries already use the Iraqi dinar, so its rounding can no "
                              "longer change."))
        iqd.sudo().write({"rounding": 1.0})
        return {"type": "ir.actions.client", "tag": "reload"}

    @api.onchange("ldm_preset")
    def _onchange_ldm_preset_engagement(self):
        if self.ldm_preset:
            self.ldm_engagement_required = ENGAGEMENT_REQUIRED.get(self.ldm_preset, False)

    @api.model
    def _ldm_apply_preset(self, preset):
        result = super()._ldm_apply_preset(preset)
        self.env["res.company"].sudo().search([]).write(
            {"ldm_engagement_required": ENGAGEMENT_REQUIRED.get(preset, False)})
        return result
