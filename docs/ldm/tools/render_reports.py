# Render the module's reports to HTML files as a given user, in that user's
# language, the way the web client prints them, so they can be looked at on
# a machine without wkhtmltopdf. Run in `odoo-bin shell`:
#
#   LDM_USER=manager LDM_OUT=docs/ldm/evidence/<round>/reports \
#   LDM_REPORTS="legal_department_management.report_legal_task_template:17;..." \
#   odoo-bin shell -c odoo19_ldm.conf -d ldm_pro --no-http < docs/ldm/tools/render_reports.py
#
# Each file gets a <base> pointing at the running server, so its stylesheets
# and fonts load when the file is opened; docs/ldm/tools/capture_reports.py
# --files then screenshots them.
import os

user = env["res.users"].search([("login", "=", os.environ.get("LDM_USER", "manager"))], limit=1)
out = os.environ.get("LDM_OUT", "docs/ldm/evidence/reports")
base = env["ir.config_parameter"].sudo().get_param("web.base.url") or "http://127.0.0.1:8110"
base = os.environ.get("LDM_BASE", base).rstrip("/") + "/"
os.makedirs(out, exist_ok=True)
Report = env["ir.actions.report"].with_user(user).with_context(lang=user.lang)
for spec in os.environ["LDM_REPORTS"].split(";"):
    name, ids = spec.strip().split(":")
    html = Report._render_qweb_html(name, [int(i) for i in ids.split(",")])[0].decode()
    html = html.replace("<head>", f'<head><base href="{base}">', 1)
    path = os.path.join(out, f"{name.split('.')[-1]}_{ids.replace(',', '-')}_{user.lang[:2]}.html")
    open(path, "w", encoding="utf-8").write(html)
    print("rendered", path)
