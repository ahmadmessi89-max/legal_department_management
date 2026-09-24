# -*- coding: utf-8 -*-
"""The conflict-of-interest check (Advocacy Law Arts. 44-45).

Before the office acts against someone, it must know whether that person is,
or was, its client, stood on its client's side, or is a company it advises on a
retainer; and before it acts for a new client, whether that client was the
other side in one of its matters.

The search runs with sudo, because a conflict must be found across teams whose
record rules hide each other's matters. What comes back to someone who may not
open the matter is redacted to "a matter handled by another team" and the name
of its responsible lawyer. Every check is recorded; a legal manager decides on a
check that found a possible conflict, with a reason, and the decision can then
never change. A matter whose check is waiting for that decision cannot start.

Matching is by name after Arabic normalisation (alef forms, taa marbuta,
yaa / alef maksura, diacritics, tatweel, the article, "عبد ال" spacing,
Arabic-Indic digits) and through the partner hierarchy: a name that matches a
company also finds its branches, contacts and subsidiaries, and the other way
round (research 06 F1, test 5).
"""
import re
import threading
from datetime import timedelta

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from .ldm_engine import engine_guard, in_engine
from .ldm_text import normalize

MANAGER = "legal_department_management.group_legal_manager"
CONFLICTS = "group_ldm_conflicts"
_ABD = re.compile(r"\bعبد\s+ال")

# create_from_template tries to start the matter straight away; while a
# conflict check waits for a manager the matter must stay New instead of the
# whole creation failing. Process-local, so no RPC call can set it.
_template_create = threading.local()


def in_template_create():
    return getattr(_template_create, "depth", 0) > 0


def conflict_key(text):
    """Comparison key: normalised, "عبد ال…" joined, the article dropped."""
    value = normalize(text)
    value = _ABD.sub("عبدال", value)
    words = [w[2:] if w.startswith("ال") and len(w) > 3 else w for w in value.split(" ") if w]
    return " ".join(words)


def keys_match(ka, kb):
    """Same key, or one name's words all contained in the other's (at least two words)."""
    if not ka or not kb:
        return False
    if ka == kb:
        return True
    ta, tb = set(ka.split(" ")), set(kb.split(" "))
    return (len(ta) >= 2 and ta <= tb) or (len(tb) >= 2 and tb <= ta)


def names_match(a, b):
    return keys_match(conflict_key(a), conflict_key(b))


class LegalConflictCheck(models.Model):
    _inherit = "legal.conflict.check"

    decision = fields.Selection(selection_add=[("superseded", "Replaced by a newer check")],
                                ondelete={"superseded": "set default"})
    legal_company_id = fields.Many2one("legal.company", string="For client", ondelete="set null", index=True)
    policy = fields.Selection([("warn", "Warn, a manager may override"), ("block", "Block")], string="Policy",
                              readonly=True)
    decided_on = fields.Datetime(string="Decided on", readonly=True)
    seen_count = fields.Integer(string="Seen before", help="Earlier appearances that are not a conflict, "
                                "such as the same opponent in another of our matters.")
    hit_html = fields.Html(string="What was found", compute="_compute_hit_html", sanitize=False)
    task_state = fields.Selection(related="task_id.state", string="Matter status")
    ldm_is_manager = fields.Boolean(compute="_compute_ldm_is_manager")

    @api.depends("query", "date")
    def _compute_display_name(self):
        for check in self:
            check.display_name = _("Check of %(date)s: %(names)s",
                                   date=fields.Date.to_string(fields.Datetime.context_timestamp(check, check.date))
                                   if check.date else "", names=check.query or "")

    @api.depends_context("uid")
    def _compute_ldm_is_manager(self):
        is_manager = self.env.user.has_group(MANAGER)
        for check in self:
            check.ldm_is_manager = is_manager

    @api.depends_context("uid", "lang")
    @api.depends("hits")
    def _compute_hit_html(self):
        for check in self:
            hits = check._ldm_present(check.hits or [])
            if not hits:
                check.hit_html = Markup("<p class='text-muted mb-0'>%s</p>") % _("Nothing found.")
                continue
            rows = []
            for hit in hits:
                css = "text-danger" if hit["conflict"] else "text-muted"
                rows.append(Markup("<li><span class='%s fw-bold'>%s</span> — %s <span class='text-muted'>(%s)</span></li>")
                            % (css, hit["role"], hit["label"], hit["name"]))
            check.hit_html = Markup("<ul class='mb-0'>%s</ul>") % Markup("").join(rows)

    # ------------------------------------------------------------------
    # Guards: a check is evidence, it never changes once decided
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        if not (in_engine() or self.env.su):
            raise AccessError(_("Conflict checks are recorded by running the check, not typed in."))
        return super().create(vals_list)

    def write(self, vals):
        if not (in_engine() or self.env.su):
            if set(vals) - {"task_id"}:
                raise AccessError(_("A conflict check cannot be edited; a legal manager records the decision."))
            if any(check.task_id and check.task_id.id != vals.get("task_id") for check in self):
                raise AccessError(_("This conflict check already belongs to a matter."))
        if {"decision", "reason", "hits", "query"} & set(vals) and any(c.decision != "pending" for c in self):
            if not self.env.su:
                raise UserError(_("A conflict check that has been decided can never change."))
        return super().write(vals)

    def unlink(self):
        if not self.env.su:
            raise UserError(_("Conflict checks are kept as evidence and cannot be deleted."))
        return super().unlink()

    # ------------------------------------------------------------------
    # The search
    # ------------------------------------------------------------------
    @api.model
    def _ldm_run(self, names, task=None, client=None):
        """Search, record a check and return it. ``names`` are the people or
        companies the matter is against; ``client`` is who the office acts for."""
        task = task or self.env["legal.task"]
        client = client or task.legal_company_id or self.env["legal.company"]
        if isinstance(names, str):
            names = [names]
        names = [n.strip() for n in (names or []) if n and n.strip()]
        entries = [(n, "opposing") for n in dict.fromkeys(names)]
        if client:
            entries.append((client.name, "client"))
        hits = self._ldm_search(entries, task, client) if entries else []
        conflicts = [h for h in hits if h["conflict"]]
        query = ", ".join(n for n, _side in entries)
        adopted = task and self._ldm_adoptable(names, client)
        if adopted:
            with engine_guard():
                adopted.sudo().write({"task_id": task.id})
            adopted._ldm_after_link()
            return adopted
        company = task.company_id or client.company_id or self.env.company
        with engine_guard():
            check = self.sudo().create({
                "task_id": task.id or False,
                "legal_company_id": client.id or False,
                "company_id": company.id,
                "query": query or "-",
                "hits": hits,
                "hit_count": len(conflicts),
                "seen_count": len(hits) - len(conflicts),
                "decision": "pending" if conflicts else "clear",
                "policy": company.ldm_conflict_policy,
                "user_id": self.env.uid,
            })
        if task:
            check._ldm_after_link()
        return check

    def _ldm_adoptable(self, names, client):
        """A check the same user ran moments ago in the quick-create dialog for
        the same names, not yet linked to a matter: the matter adopts it (and any
        decision a manager already took on it) instead of checking twice."""
        recent = self.search([("task_id", "=", False), ("user_id", "=", self.env.uid),
                              ("date", ">=", fields.Datetime.now() - timedelta(minutes=30))],
                             order="id desc", limit=10)
        wanted = {conflict_key(n) for n in names}
        for check in recent:
            if client and check.legal_company_id and check.legal_company_id != client:
                continue
            checked = {conflict_key(n) for n in (check.query or "").split(", ")}
            if wanted and wanted <= checked:
                return check
        return self.browse()

    @api.model
    def _ldm_supersede(self, old, new):
        """Pending checks whose names the new check covers are replaced by it:
        the manager decides once, on the complete picture. A pending check with
        a name the new one no longer has stays pending."""
        new_keys = {conflict_key(n) for n in (new.sudo().query or "").split(", ")}
        replaced = old.sudo().filtered(lambda c: c.decision == "pending" and c != new and
                                       {conflict_key(n) for n in (c.query or "").split(", ")} <= new_keys)
        if replaced:
            with engine_guard():
                replaced.write({"decision": "superseded", "reason": _("Replaced by a newer check.")})
        return replaced

    def _ldm_after_link(self):
        """A possible conflict on a matter: tell the legal managers once."""
        for check in self.filtered(lambda c: c.task_id and c.decision == "pending"):
            task = check.task_id.sudo()
            task.message_post(body=_("Possible conflict of interest found (%s). A legal manager must decide "
                                     "before work starts.", check.hit_count))
            check._ldm_notify_managers()

    def _ldm_notify_managers(self):
        activity_type = self.env.ref("legal_department_management.ldm_activity_conflict", raise_if_not_found=False)
        for check in self.filtered("task_id"):
            task = check.task_id.sudo()
            managers = task._ldm_managers(task.company_id)
            summary = _("Decide on a possible conflict — %s", task.task_number or task.name)
            for manager in managers[:5]:
                if task.activity_ids.filtered(lambda a, m=manager: a.user_id == m and a.summary == summary):
                    continue
                task.activity_schedule(activity_type_id=activity_type.id if activity_type else False,
                                       summary=summary, user_id=manager.id,
                                       date_deadline=fields.Date.context_today(self))

    @api.model
    def _ldm_group(self, partners):
        """Every partner in the same group as ``partners``: their top company and
        all its branches, contacts and subsidiaries."""
        Partner = self.env["res.partner"].sudo().with_context(active_test=False)
        roots = set()
        for partner in partners.sudo():
            top, seen = partner, set()
            while top.parent_id and top.parent_id.id not in seen:
                seen.add(top.id)
                top = top.parent_id
            roots.add(top.id)
        return Partner.search([("id", "child_of", list(roots))]) if roots else Partner

    @api.model
    def _ldm_partners_named(self, name):
        """Partners whose name matches ``name``, tolerant of Arabic letter forms."""
        key = conflict_key(name)
        if not key:
            return self.env["res.partner"]
        longest = max(key.split(" "), key=len)
        self.env.cr.execute("""
            SELECT id, name FROM res_partner
             WHERE translate(lower(name), 'أإآٱةىؤئـ', 'ااااهيوي') ILIKE %s
             LIMIT 500
        """, (f"%{longest}%",))
        ids = [pid for pid, pname in self.env.cr.fetchall() if names_match(pname or "", name)]
        return self.env["res.partner"].sudo().with_context(active_test=False).browse(ids)

    @api.model
    def _ldm_search(self, entries, task, client):
        """Every place the names appear, as a list of plain dicts (stored on the check)."""
        company = task.company_id or client.company_id or self.env.company
        in_company = ["|", ("company_id", "=", False), ("company_id", "=", company.id)]
        Task = self.env["legal.task"].sudo().with_context(active_test=False)
        Client = self.env["legal.company"].sudo().with_context(active_test=False)
        Party = self.env["legal.task.party"].sudo().with_context(active_test=False)
        retainer_clients = self.env["legal.engagement"].sudo().search(
            [("state", "=", "active"), ("fee_type", "=", "retainer"), ("company_id", "=", company.id)]
        ).legal_company_id
        not_this = [("task_id", "!=", task.id)] if task else []
        clients = [(c, conflict_key(c.name), c.partner_id.id) for c in Client.search(in_company)]
        parties = [(p, conflict_key(p.partner_id.name), p.partner_id.id)
                   for p in Party.search(in_company + not_this)]
        counterparties = [(m, conflict_key(m.counterparty_id.name), m.counterparty_id.id)
                          for m in Task.search(in_company + [("counterparty_id", "!=", False)]
                                               + ([("id", "!=", task.id)] if task else []))]
        hits = []
        seen = set()

        def add(model, rec_id, role, name, conflict):
            if (model, rec_id, role) not in seen:
                seen.add((model, rec_id, role))
                hits.append({"model": model, "id": rec_id, "role": role, "name": name, "conflict": conflict})

        for name, side in entries:
            key = conflict_key(name)
            group = set(self._ldm_group(self._ldm_partners_named(name)).ids)

            def matches(record_key, partner_id, key=key, group=group):
                return keys_match(key, record_key) or bool(partner_id and partner_id in group)

            if side == "opposing":
                for other, other_key, partner_id in clients:
                    if other == client or not matches(other_key, partner_id):
                        continue
                    if other in retainer_clients:
                        add("legal.company", other.id, "retainer_client", name, True)
                    else:
                        add("legal.company", other.id, "client" if other.active else "former_client", name, True)
            for party, party_key, partner_id in parties:
                if not matches(party_key, partner_id):
                    continue
                matter = party.task_id
                if side == "opposing":
                    if party.is_client_side:
                        add("legal.task", matter.id, "our_side", name, True)
                    elif party.role not in ("witness", "expert"):
                        add("legal.task", matter.id, "opponent", name, False)
                elif not party.is_client_side and party.role not in ("witness", "expert")                         and matter.legal_company_id != client:
                    add("legal.task", matter.id, "opponent", name, True)
            for matter, matter_key, partner_id in counterparties:
                if not matches(matter_key, partner_id):
                    continue
                if side == "opposing":
                    add("legal.task", matter.id, "counterparty", name, False)
                elif matter.legal_company_id != client:
                    add("legal.task", matter.id, "counterparty", name, True)
        return hits

    # ------------------------------------------------------------------
    # Presenting hits to the person looking
    # ------------------------------------------------------------------
    def _ldm_role_labels(self):
        return {
            "client": _("Is our client"),
            "former_client": _("Was our client"),
            "retainer_client": _("Is a company we advise on a retainer"),
            "our_side": _("Was on our client's side"),
            "opponent": _("Was the other side"),
            "counterparty": _("Was the other party to a contract"),
        }

    def _ldm_present(self, hits):
        """Hits as the current user may see them: records they cannot open are
        redacted to "handled by another team" with the responsible's name."""
        by_model = {}
        for hit in hits:
            by_model.setdefault(hit["model"], set()).add(hit["id"])
        readable = {}
        for model, ids in by_model.items():
            readable[model] = set(self.env[model].with_context(active_test=False).search([("id", "in", list(ids))]).ids)
        roles = self._ldm_role_labels()
        result = []
        for hit in hits:
            record = self.env[hit["model"]].sudo().with_context(active_test=False).browse(hit["id"]).exists()
            if not record:
                continue
            responsible = record.lawyer_id.name or _("no one")
            if hit["id"] in readable.get(hit["model"], ()):
                if hit["model"] == "legal.task":
                    label = _("%(matter)s for %(client)s, responsible %(lawyer)s", matter=record.display_name,
                              client=record.legal_company_id.name, lawyer=responsible)
                else:
                    label = _("%(client)s, responsible %(lawyer)s", client=record.name, lawyer=responsible)
                redacted = False
            else:
                label = (_("A matter handled by another team, responsible %s", responsible)
                         if hit["model"] == "legal.task"
                         else _("A client of another team, responsible %s", responsible))
                redacted = True
            result.append({
                "model": hit["model"], "id": False if redacted else hit["id"], "role": roles.get(hit["role"], hit["role"]),
                "role_code": hit["role"], "name": hit["name"], "label": label, "conflict": hit["conflict"],
                "redacted": redacted, "responsible": responsible,
            })
        return result

    # ------------------------------------------------------------------
    # The decision
    # ------------------------------------------------------------------
    def ldm_decide(self, decision, reason):
        """A legal manager decides: ``clear`` (not the same person or no real
        conflict), ``override`` (accept despite the match; not allowed when the
        policy blocks) or ``declined``. The reason is required and the decision
        is final."""
        if not self.env.user.has_group(MANAGER):
            raise AccessError(_("Only a legal manager can decide on a possible conflict of interest."))
        if decision not in ("clear", "override", "declined"):
            raise UserError(_("Choose a decision."))
        if not (reason or "").strip():
            raise UserError(_("Give the reason for the decision; it is kept with the check."))
        labels = dict(self._fields["decision"]._description_selection(self.env))
        for check in self:
            if check.decision != "pending":
                raise UserError(_("This conflict check has already been decided."))
            if decision == "override" and (check.policy or check.company_id.ldm_conflict_policy) == "block":
                raise UserError(_("The office's policy blocks matters with a conflict. Decline it, or record "
                                  "that it is not a conflict if the match is someone else."))
            with engine_guard():
                check.write({"decision": decision, "reason": reason.strip(), "decided_by_id": self.env.uid,
                             "decided_on": fields.Datetime.now()})
            if check.task_id:
                task = check.task_id.sudo()
                task.message_post(body=_("Conflict check decided by %(user)s: %(decision)s. %(reason)s",
                                         user=self.env.user.name, decision=labels[decision], reason=reason.strip()))
                task.activity_ids.filtered(
                    lambda a: a.activity_type_id == self.env.ref(
                        "legal_department_management.ldm_activity_conflict", raise_if_not_found=False)
                ).action_feedback(feedback=labels[decision])
        return True

    def action_ldm_decide(self):
        self.ensure_one()
        if not self.env.user.has_group(MANAGER):
            raise AccessError(_("Only a legal manager can decide on a possible conflict of interest."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Decide on the conflict check"),
            "res_model": "legal.conflict.decision.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_check_id": self.id},
        }

    def action_ldm_send_to_partner(self):
        """Anyone on the matter can ask the legal managers to decide."""
        self._ldm_notify_managers()
        return {"type": "ir.actions.client", "tag": "display_notification",
                "params": {"type": "info", "message": _("The legal managers have been asked to decide.")}}
