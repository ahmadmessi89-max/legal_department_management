import { Component, onWillStart, useExternalListener, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { _t } from "@web/core/l10n/translation";

import { dayHeading, formatAmount, formatHour, longDate, relativeDay, todayDay } from "../core/ldm_format";
import { runRecordAction, toggleStep } from "../core/ldm_step_actions";
import { LdmIcon } from "../core/ldm_icon";

/**
 * مكتبي / My Day - the first screen of the application (SPEC 5.1, 14.4).
 *
 * It answers one question: what needs me now, and what is the next thing to
 * do on each. The work is grouped into focus bands (overdue, today, this
 * week, later, no date); every row says why it is there and offers at most one
 * action; the next seven days sit beside it. A band with nothing in it is not
 * drawn, and a day with nothing to do says so in two lines.
 *
 * The screen is a renderer. `legal.task.get_my_day` decides, as the reader,
 * what is shown and which actions exist, so an auditor who opens it gets the
 * same page with no action on it.
 */
export class LdmMyDay extends Component {
    static template = "legal_department_management.MyDay";
    static components = { Layout, DateTimeInput, LdmIcon };
    static props = { ...standardActionServiceProps };

    static labels = {
        loading: _t("Opening your day…"),
        errorTitle: _t("My Day could not be loaded."),
        errorHint: _t("The server could not be reached or reported an error. Try again in a moment."),
        retry: _t("Try again"),
        refreshFailed: _t("Could not refresh; the screen shows what it had."),
        newMatter: _t("New matter"),
        statsTitle: _t("At a glance"),
        search: _t("Search by number, client or body…"),
        readOnly: _t("Read only"),
        unfold: _t("Show"),
        fold: _t("Hide"),
        agendaOpen: _t("Open the agenda"),
        routeTitle: _t("Today's visits, by body"),
        routeHint: _t("What to carry to each counter."),
        managerTitle: _t("Needs a manager"),
        approved: _t("Approved."),
        activityDone: _t("Marked as done."),
        dateSaved: _t("Notification date saved: the challenge periods are counted from it."),
        noDateYet: _t("Choose the date first."),
        notifiedOn: _t("Notified on"),
        undated: _t("No date"),
        have: _t("We have it"),
        missing: _t("Missing"),
        open: _t("Open"),
        noBody: _t("Hours not recorded"),
    };

    /** Lucide icon and tone of the tinted square that opens each row. */
    static kinds = {
        step: { icon: "square-check-big", tone: "brand" },
        visit: { icon: "building-2", tone: "info" },
        hearing: { icon: "gavel", tone: "violet" },
        deadline: { icon: "hourglass", tone: "danger" },
        target: { icon: "flag", tone: "warning" },
        approval: { icon: "badge-check", tone: "violet" },
        activity: { icon: "clock", tone: "neutral" },
        notification: { icon: "mail", tone: "warning" },
        idle: { icon: "circle", tone: "neutral" },
        waiting: { icon: "hourglass", tone: "neutral" },
        conflict: { icon: "shield-alert", tone: "danger" },
    };

    static kindLabels = {
        step: _t("Step"),
        visit: _t("Visit"),
        hearing: _t("Court session"),
        deadline: _t("Deadline"),
        target: _t("Target date"),
        approval: _t("Approval"),
        activity: _t("Activity"),
        notification: _t("Judgment"),
        idle: _t("Matter"),
        waiting: _t("Approval"),
        conflict: _t("Conflict check"),
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.command = useService("command");
        this.state = useState({
            data: null,
            error: null,
            busy: false,
            scope: "me",
            unfolded: {},
            dates: {},
            pending: {},
        });
        this.queueRef = useRef("queue");
        if (this.env.config && this.env.config.setDisplayName) {
            this.env.config.setDisplayName(this.props.action.name || _t("My Day"));
        }
        useExternalListener(window, "keydown", (ev) => this.onGlobalKeydown(ev));
        onWillStart(() => this.load());
    }

    get label() {
        return LdmMyDay.labels;
    }

    get data() {
        return this.state.data;
    }

    async load(scope = this.state.scope) {
        this.state.busy = true;
        try {
            const data = await this.orm.call("legal.task", "get_my_day", [scope]);
            this.state.data = data;
            this.state.scope = data.scope;
            this.state.error = null;
        } catch (error) {
            if (this.state.data) {
                this.notification.add(this.label.refreshFailed, { type: "warning" });
            } else {
                this.state.error = true;
            }
        } finally {
            this.state.busy = false;
        }
    }

    reload() {
        return this.load();
    }

    // ------------------------------------------------------------ derived
    get today() {
        return todayDay();
    }

    get dateLine() {
        return this.data ? longDate(this.data.header.today) : "";
    }

    get visibleBands() {
        return (this.data?.bands || []).filter((band) => band.count);
    }

    isFolded(band) {
        const override = this.state.unfolded[band.key];
        return override === undefined ? band.folded : !override;
    }

    toggleBand(band) {
        this.state.unfolded[band.key] = this.isFolded(band);
    }

    rowDate(row) {
        if (!row.date) {
            return { label: "", tone: "" };
        }
        if (row.kind === "approval") {
            return { label: row.since ? relativeDay(row.since, this.today).label : "", tone: "" };
        }
        const rel = relativeDay(row.date, this.today);
        const hour = formatHour(row.time);
        // The tone lives on the flag pills; the date itself stays quiet.
        return { label: hour ? `${rel.label} · ${hour}` : rel.label, tone: "" };
    }

    kindIcon(kind) {
        return (LdmMyDay.kinds[kind] || LdmMyDay.kinds.idle).icon;
    }

    kindTone(kind) {
        return (LdmMyDay.kinds[kind] || LdmMyDay.kinds.idle).tone;
    }

    kindLabel(kind) {
        return LdmMyDay.kindLabels[kind] || "";
    }

    /** The kind word leads the reason only where the reason does not say it. */
    showKind(row) {
        return ["step", "deadline", "activity", "target"].includes(row.kind);
    }

    agendaDay(day) {
        return dayHeading(day.date, this.today);
    }

    hour(value) {
        return formatHour(value);
    }

    amount(entry) {
        return formatAmount(entry.amount, entry.currency_id);
    }

    moreLabel(band) {
        return _t("Showing the first %s. The register has the rest.", band.rows.length);
    }

    // ------------------------------------------------------------ actions
    openRow(row) {
        if (!row || !row.open) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: row.open.res_model,
            res_id: row.open.res_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openMatter(taskId) {
        this.openRow({ open: { res_model: "legal.task", res_id: taskId } });
    }

    async runAction(row, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        const action = row.action;
        if (!action || this.state.pending[row.key]) {
            return;
        }
        this.state.pending[row.key] = true;
        const services = { orm: this.orm, action: this.action, notification: this.notification };
        const reload = () => this.reload();
        try {
            switch (action.type) {
                case "tick":
                    await toggleStep(services, action.id, reload);
                    break;
                case "visit":
                    await runRecordAction(services, "legal.task.step", "action_ldm_log_visit", action.id, reload);
                    break;
                case "outcome":
                    await runRecordAction(services, "legal.hearing", "action_ldm_record_outcome", action.id, reload);
                    break;
                case "approve":
                    await this.orm.call("legal.task", "action_approve", [[action.id]]);
                    this.notification.add(this.label.approved, { type: "success" });
                    await reload();
                    break;
                case "activity":
                    await this.orm.call("legal.task", "ldm_my_day_activity_done", [action.id]);
                    this.notification.add(this.label.activityDone, { type: "success" });
                    await reload();
                    break;
                case "notified":
                    await this.saveNotified(row);
                    break;
            }
        } finally {
            this.state.pending[row.key] = false;
        }
    }

    onDateChange(row, value) {
        this.state.dates[row.key] = value ? value.toISODate() : null;
    }

    async saveNotified(row) {
        const value = this.state.dates[row.key];
        if (!value) {
            this.notification.add(this.label.noDateYet, { type: "warning" });
            return;
        }
        await this.orm.call("legal.task", "ldm_my_day_notified", [row.action.id, value]);
        this.notification.add(this.label.dateSaved, { type: "success" });
        await this.reload();
    }

    newMatter() {
        this.action.doAction("legal_department_management.action_legal_task_create_wizard", {
            onClose: () => this.reload(),
        });
    }

    openSearch() {
        this.command.openMainPalette({ searchValue: "" });
    }

    openApprovals() {
        this.action.doAction("legal_department_management.action_legal_task_to_approve");
    }

    openAgenda() {
        this.action.doAction("legal_department_management.action_ldm_agenda_board");
    }

    openAdvances() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Cash advances"),
            res_model: "legal.advance",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", "paid"]],
            context: { create: false },
        });
    }

    openCount(count) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: count.label,
            res_model: count.model,
            views: [[false, "list"], [false, "form"]],
            domain: count.domain,
        });
    }

    setScope(key) {
        if (key !== this.state.scope) {
            this.load(key);
        }
    }

    async logVisit(visit, ev) {
        ev.stopPropagation();
        const services = { orm: this.orm, action: this.action, notification: this.notification };
        await runRecordAction(services, "legal.task.step", "action_ldm_log_visit", visit.step_id, () => this.reload());
    }

    // ------------------------------------------------------------ keyboard
    /** ↑/↓ move between rows, Enter opens, Home/End jump. */
    onQueueKeydown(ev) {
        const rows = [...(this.queueRef.el?.querySelectorAll(".o_ldm_row") || [])];
        if (!rows.length) {
            return;
        }
        const index = rows.indexOf(document.activeElement);
        const focus = (i) => {
            ev.preventDefault();
            rows[Math.max(0, Math.min(rows.length - 1, i))].focus();
        };
        switch (ev.key) {
            case "ArrowDown":
                return focus(index + 1);
            case "ArrowUp":
                return focus(index < 0 ? 0 : index - 1);
            case "Home":
                return focus(0);
            case "End":
                return focus(rows.length - 1);
        }
    }

    onRowKeydown(row, ev) {
        if (ev.target !== ev.currentTarget) {
            return;
        }
        if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            this.openRow(row);
        }
    }

    /** "/" opens the search from anywhere on the screen, unless typing. */
    onGlobalKeydown(ev) {
        if (ev.key !== "/" || ev.ctrlKey || ev.metaKey || ev.altKey) {
            return;
        }
        const target = ev.target;
        const editable = target && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName));
        if (editable || !this.data) {
            return;
        }
        ev.preventDefault();
        this.openSearch();
    }
}

registry.category("actions").add("legal_dashboard_tag", LdmMyDay);
