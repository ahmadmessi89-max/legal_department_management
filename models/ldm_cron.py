# -*- coding: utf-8 -*-
"""The module's scheduled jobs run in the legal team's language.

A cron runs without a language, so every text a job writes and keeps (the
name of a deadline, the title of a matter opened for a recurring obligation,
the next period of a chain, a renewed retainer instalment, a reminder) would
be stored in English and shown as English on an Arabic screen. The jobs of
this module therefore run in the language most of the active legal staff use,
the company's own language breaking a tie.
"""
from collections import Counter

from odoo import api, models

MODULE = "legal_department_management"


def ldm_team_lang(env):
    """The language the legal team reads, for texts written by nobody in particular."""
    installed = {code for code, _name in env["res.lang"].get_installed()}
    company_lang = env.company.partner_id.lang
    staff = env.ref(f"{MODULE}.group_ldm_clerk", raise_if_not_found=False)
    counts = Counter()
    if staff:
        for user in staff.sudo().all_user_ids:
            if user.active and user.lang in installed:
                counts[user.lang] += 1
    if counts:
        best = max(counts.values())
        leaders = [lang for lang, count in counts.items() if count == best]
        if company_lang in leaders:
            return company_lang
        return sorted(leaders)[0]
    if company_lang in installed:
        return company_lang
    return env.lang or "en_US"


class IrCron(models.Model):
    _inherit = "ir.cron"

    def _callback(self, cron_name, server_action_id):
        if self.ldm_is_legal_job() and not self.env.context.get("lang"):
            self = self.with_context(lang=ldm_team_lang(self.env))
        return super()._callback(cron_name, server_action_id)

    def ldm_is_legal_job(self):
        self.ensure_one()
        return self.sudo().ir_actions_server_id.model_id.model.startswith(("legal.", "ldm."))

    @api.model
    def ldm_team_lang(self):
        return ldm_team_lang(self.env)
