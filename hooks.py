# -*- coding: utf-8 -*-


def post_init_hook(env):
    """A fresh install starts as an in-house legal department (the module's
    name), with the Iraqi working calendar for deadlines. An upgrade from
    19.0.6.3.0 does not run this hook; its migration applies the hybrid preset."""
    params = env["ir.config_parameter"].sudo()
    if not params.get_param("legal_department_management.preset"):
        env["res.config.settings"]._ldm_apply_preset("department")
    calendar = env.ref("legal_department_management.ldm_calendar_iraq", raise_if_not_found=False)
    if calendar:
        env["res.company"].sudo().search([("ldm_calendar_id", "=", False)]).write({"ldm_calendar_id": calendar.id})
