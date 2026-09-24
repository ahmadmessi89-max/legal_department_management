import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { _t } from "@web/core/l10n/translation";

import { dayHeading, formatHour, shortDate, todayDay } from "../core/ldm_format";

/**
 * Agenda (SPEC 5.7, 14.4): court sessions, counter visits and deadlines for
 * the next fourteen days, one heading per day, read top to bottom in the
 * order they will be met. The month grid is one click away ("Month"), and the
 * hearing roll prints the same range.
 */
export class LdmAgenda extends Component {
    static template = "legal_department_management.Agenda";
    static components = { Layout };
    static props = { ...standardActionServiceProps };

    static labels = {
        title: _t("Agenda"),
        subtitle: _t("The next fourteen days"),
        me: _t("Mine"),
        all: _t("Everyone"),
        month: _t("Month"),
        roll: _t("Print roll"),
        loading: _t("Opening the agenda…"),
        error: _t("The agenda could not be loaded. Try again in a moment."),
        retry: _t("Try again"),
        empty: _t("Nothing is booked in the next fourteen days."),
        emptyHint: _t("Court sessions, counter visits and deadlines appear here as soon as they are dated."),
        unstaffed: _t("Nobody attending"),
    };

    static kinds = {
        hearing: { icon: "fa-gavel", label: _t("Court session") },
        visit: { icon: "fa-building-o", label: _t("Visit") },
        deadline: { icon: "fa-hourglass-half", label: _t("Deadline") },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ data: null, error: false, scope: "me" });
        if (this.env.config && this.env.config.setDisplayName) {
            this.env.config.setDisplayName(this.props.action.name || this.label.title);
        }
        onWillStart(() => this.load());
    }

    get label() {
        return LdmAgenda.labels;
    }

    async load(scope = this.state.scope) {
        try {
            this.state.data = await this.orm.call("legal.task", "ldm_get_agenda", [scope, 14]);
            this.state.scope = this.state.data.scope;
            this.state.error = false;
        } catch {
            this.state.error = true;
        }
    }

    get range() {
        const data = this.state.data;
        return data ? `${shortDate(data.start)} – ${shortDate(data.end)}` : "";
    }

    heading(day) {
        return dayHeading(day.date, todayDay());
    }

    kind(item) {
        return LdmAgenda.kinds[item.kind] || { icon: "fa-circle-o", label: "" };
    }

    hour(value) {
        return formatHour(value);
    }

    setScope(scope) {
        if (scope !== this.state.scope) {
            this.load(scope);
        }
    }

    open(item) {
        if (!item.open) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: item.open.res_model,
            res_id: item.open.res_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async openMonth() {
        const action = await this.orm.call("legal.task", "ldm_agenda_calendar_action", []);
        this.action.doAction(action);
    }

    async printRoll() {
        const data = this.state.data;
        const action = await this.orm.call("legal.task", "ldm_agenda_print_roll", [data.start, data.end, data.scope]);
        this.action.doAction(action);
    }
}

registry.category("actions").add("ldm_agenda", LdmAgenda);
