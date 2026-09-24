import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

import { relativeDay, shortDate } from "../core/ldm_format";
import { LdmIcon } from "../core/ldm_icon";

const OVERVIEW_FIELD = [{ name: "ldm_service_overview", type: "json" }];

const TONE_ICONS = {
    success: "circle-check",
    primary: "circle-dot",
    warning: "file-clock",
    info: "hourglass",
    danger: "circle-alert",
    muted: "circle",
};

/**
 * The company file read body by body (design-direction.md): each body a
 * section with its services, a status pill per service, the date that
 * matters (done on, next step, due by), the person responsible and Start or
 * Open at the row's end, with a thin completion bar per body. The data is
 * the record's `ldm_service_overview` (G's coverage view, read as the user),
 * so it reloads with the client.
 */
export class LdmServiceOverview extends Component {
    static template = "legal_department_management.ServiceOverview";
    static components = { LdmIcon };
    static props = { ...standardWidgetProps };

    static labels = {
        title: _t("Services this year"),
        start: _t("Start"),
        open: _t("Open"),
        empty: _t("No service is tracked for this client yet."),
        emptyHint: _t("Mark a matter type as tracked for every company to follow it here."),
        register: _t("All clients"),
        otherBody: _t("Other services"),
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
    }

    get label() {
        return LdmServiceOverview.labels;
    }

    get overview() {
        return (this.props.record && this.props.record.data.ldm_service_overview) || {};
    }

    get totals() {
        return this.overview.totals || { total: 0, done: 0, open: 0, due: 0, overdue: 0 };
    }

    get summary() {
        const t = this.totals;
        const parts = [_t("%(done)s of %(total)s done", { done: t.done, total: t.total })];
        if (t.open) {
            parts.push(_t("%s in progress", t.open));
        }
        if (t.due) {
            parts.push(_t("%s not done yet", t.due));
        }
        if (t.overdue) {
            parts.push(_t("%s overdue", t.overdue));
        }
        return parts.join(" · ");
    }

    get bodies() {
        return (this.overview.bodies || []).map((body) => ({
            ...body,
            key: body.id || "none",
            countLabel: _t("%(done)s of %(total)s done", { done: body.done, total: body.total }),
            services: body.services.map((service) => this.serviceRow(service)),
        }));
    }

    serviceRow(service) {
        let when = "";
        if (service.date) {
            const day = shortDate(service.date);
            if (service.date_kind === "done") {
                when = _t("Done on %s", day);
            } else if (service.date_kind === "next") {
                when = _t("Next: %s", `${day} · ${relativeDay(service.date).label}`);
            } else if (service.date_kind === "due") {
                when = _t("Due by %s", day);
            }
        }
        return {
            ...service,
            when,
            icon: TONE_ICONS[service.tone] || "circle",
        };
    }

    async start(service) {
        const action = await this.orm.call("legal.company.coverage", "action_ldm_start", [[service.coverage_id]]);
        await this.action.doAction(action, {
            onClose: () => this.props.record.load(),
        });
    }

    open(service) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "legal.task",
            res_id: service.task_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async openRegister() {
        const action = await this.orm.call("legal.company", "ldm_action_coverage_register", [[this.props.record.resId]]);
        this.action.doAction(action);
    }
}

registry.category("view_widgets").add("ldm_service_overview", {
    component: LdmServiceOverview,
    fieldDependencies: OVERVIEW_FIELD,
});
