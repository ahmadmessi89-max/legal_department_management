import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

import { relativeDay, shortDate } from "../core/ldm_format";

const DOSSIER_FIELD = [{ name: "ldm_dossier", type: "json" }];

function dossierOf(record) {
    return (record && record.data && record.data.ldm_dossier) || {};
}

/**
 * «What is happening now» on the client dossier (SPEC 5.5): the five most
 * urgent open matters of this client, each with its next date and reason.
 */
export class LdmClientNow extends Component {
    static template = "legal_department_management.ClientNow";
    static props = { ...standardWidgetProps };

    static labels = {
        empty: _t("No open matter for this client."),
        emptyHint: _t("Open one with “New matter for this client”."),
        all: _t("All open matters"),
        nothing: _t("Nothing dated"),
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
    }

    get label() {
        return LdmClientNow.labels;
    }

    get dossier() {
        return dossierOf(this.props.record);
    }

    get rows() {
        return (this.dossier.now || []).map((row) => {
            const rel = row.next_date ? relativeDay(row.next_date) : null;
            return {
                ...row,
                when: rel ? `${shortDate(row.next_date)} · ${rel.label}` : this.label.nothing,
                tone: rel ? rel.tone : "",
            };
        });
    }

    open(row) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "legal.task",
            res_id: row.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async openAll() {
        const action = await this.orm.call("legal.company", "ldm_open_matters", [[this.props.record.resId]]);
        this.action.doAction(action);
    }
}

/**
 * One window per government body or court the client has matters with,
 * counted as the reader (SPEC 5.5, replaces SAG's HTML cards). A window
 * opens the register filtered to this client and that body.
 */
export class LdmBodyWindows extends Component {
    static template = "legal_department_management.BodyWindows";
    static props = { ...standardWidgetProps };

    static labels = {
        empty: _t("No matter with a body or court yet."),
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
    }

    get label() {
        return LdmBodyWindows.labels;
    }

    get dossier() {
        return dossierOf(this.props.record);
    }

    get bodies() {
        return (this.dossier.bodies || []).map((body) => {
            const rel = body.next_date ? relativeDay(body.next_date) : null;
            return {
                ...body,
                nextLabel: rel ? _t("Next: %s", `${shortDate(body.next_date)} · ${rel.label}`) : "",
                openLabel: body.open ? _t("%s open", body.open) : "",
                doneLabel: body.done ? _t("%s done", body.done) : "",
                tone: rel ? rel.tone : "",
            };
        });
    }

    async open(body) {
        const action = await this.orm.call("legal.company", "ldm_open_matters", [[this.props.record.resId], body.id]);
        this.action.doAction(action);
    }
}

const widgets = registry.category("view_widgets");
widgets.add("ldm_client_now", { component: LdmClientNow, fieldDependencies: DOSSIER_FIELD });
widgets.add("ldm_body_windows", { component: LdmBodyWindows, fieldDependencies: DOSSIER_FIELD });
