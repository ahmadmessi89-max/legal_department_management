# Run in `odoo-bin shell`. Writes, as JSON to the path in env var LDM_SNAPSHOT,
# what every user can see (matters and clients, through the record rules),
# record counts, and each user's legal groups. Works on the old and new module.
import json
import os

out = {"users": {}, "counts": {}}
for model in ("legal.task", "legal.company", "legal.ministry", "legal.department"):
    out["counts"][model] = env[model].sudo().with_context(active_test=False).search_count([])
legal_groups = env["res.groups"].search([("id", "in", env["ir.model.data"].search(
    [("module", "=", "legal_department_management"), ("model", "=", "res.groups")]).mapped("res_id"))])
for user in env["res.users"].search([("share", "=", False), ("login", "!=", "__system__")]):
    entry = {"login": user.login, "groups": sorted(g.name for g in legal_groups if g in user.all_group_ids)}
    for model in ("legal.task", "legal.company"):
        try:
            entry[model] = sorted(env[model].with_user(user).search([]).ids)
        except Exception as exc:  # no access at all
            entry[model] = "no access: %s" % type(exc).__name__
    out["users"][user.login] = entry
with open(os.environ["LDM_SNAPSHOT"], "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print("snapshot written", os.environ["LDM_SNAPSHOT"])
