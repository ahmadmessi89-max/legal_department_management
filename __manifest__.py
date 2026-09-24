# -*- coding: utf-8 -*-
{
    "name": "Legal Department and Law Office",
    "version": "19.0.7.0.0",
    "category": "Services/Legal",
    "summary": "Matters, government transactions, lawsuits and deadlines, powers of attorney, fees and client money "
               "for in-house legal departments and law offices",
    "description": """
Legal department and law office management
==========================================

One application for an in-house legal department (قسم الشؤون القانونية) and for
a law office (مكتب المحاماة), chosen in Settings:

* My Day: what is overdue, today and this week, with the reason and one action.
* One-step matter creation from matter types that create the steps, the
  documents to collect and the target date.
* Government transactions at ministries and departments, with counter visits.
* Lawsuits: court stages, sessions, judgments and Iraqi statutory periods
  counted in calendar days with holidays rolled forward.
* Powers of attorney, correspondence register, requests from other departments,
  company records, contracts and legal opinions.
* Law office: fee agreements, instalments and retainers, client money held,
  invoicing, client statements and conflict checks.

Upgrades SAG Group's 19.0.6.3.0 in place.
    """,
    "author": "SAG Group",
    "license": "LGPL-3",
    "depends": ["base", "mail", "hr", "account", "resource"],
    "excludes": ["legal_core"],
    "data": [
        # Security
        "security/legal_security.xml",
        "security/ir.model.access.csv",
        "security/ir.model.access-gov.csv",
        "security/ir.model.access-lit.csv",
        "security/ir.model.access-ws.csv",
        "security/ir.model.access-money.csv",
        "security/ir.model.access-reg.csv",
        "security/ldm_rules.xml",
        # Data
        "data/legal_department_data.xml",
        "data/legal_cron.xml",
        "data/ldm_calendar_data.xml",
        "data/ldm_activity_data.xml",
        "data/ldm_template_data.xml",
        "data/ldm_template_translations.xml",
        "data/ldm_avatars.xml",
        "data/gov_data.xml",
        "data/lit_data.xml",
        "data/ws_data.xml",
        "data/money_data.xml",
        "data/reg_data.xml",
        # Reports
        "report/legal_company_report_templates.xml",
        "report/legal_task_report_templates.xml",
        "report/legal_general_report_templates.xml",
        "report/lit_reports.xml",
        "report/money_reports.xml",
        "report/reg_reports.xml",
        # Foundation views and actions
        "views/ldm_actions.xml",
        "views/legal_department_views.xml",
        "views/legal_task_wizard_views.xml",
        "views/legal_company_report_wizard_views.xml",
        "views/legal_general_report_wizard_views.xml",
        "views/ldm_decision_wizard_views.xml",
        "views/legal_task_views.xml",
        "views/legal_company_views.xml",
        "views/legal_dashboard_views.xml",
        "views/res_config_settings_views.xml",
        "views/legal_menus.xml",
        # Streams (after the menus, so they can add under existing folders)
        "views/gov_views.xml",
        "views/lit_views.xml",
        "views/ws_views.xml",
        "views/money_views.xml",
        "views/reg_views.xml",
        # Design pass
        "views/ds_views.xml",
    ],
    "demo": [],
    "assets": {
        "web.assets_backend": [
            "legal_department_management/static/src/**/*",
        ],
        "web.report_assets_common": [
            "legal_department_management/static/report/*.scss",
        ],
        "web.assets_unit_tests": [
            "legal_department_management/static/tests/**/*",
        ],
    },
    "post_init_hook": "post_init_hook",
    "application": True,
    "installable": True,
}
