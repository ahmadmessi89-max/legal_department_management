import { Component, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

import { formatAmount, formatHour, relativeDay, shortDate } from "../core/ldm_format";
import { runRecordAction, toggleStep } from "../core/ldm_step_actions";

const COCKPIT_FIELD = [{ name: "ldm_cockpit", type: "json" }];

function cockpitOf(record) {
    return (record && record.data && record.data.ldm_cockpit) || {};
}

/** Open a notebook page of the form this widget sits in. */
function openTab(rootEl, tab) {
    if (!tab || !rootEl) {
        return;
    }
    const form = rootEl.closest(".o_form_view") || document;
    const link = form.querySelector(`.o_notebook .nav-link[name='${tab}']`);
    if (link) {
        link.click();
        link.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
}

async function saveFirst(record) {
    if (await record.isDirty()) {
        return record.save();
    }
    return true;
}

// ================================================================= vitals
/**
 * The matter's vital facts on one line (SPEC 5.3): the next date and its
 * days left, documents N of M, sessions, expenses, time in this status. Each
 * one is a door to the tab that holds its detail.
 */
export class LdmMatterVitals extends Component {
    static template = "legal_department_management.MatterVitals";
    static props = { ...standardWidgetProps };

    setup() {
        this.root = useRef("root");
    }

    get vitals() {
        return (cockpitOf(this.props.record).vitals || []).map((vital) => this.decorate(vital));
    }

    decorate(vital) {
        const out = { ...vital, display: vital.value || "", tone: vital.tone || "" };
        if (vital.key === "next") {
            if (vital.date) {
                const rel = relativeDay(vital.date);
                out.display = rel.days !== null && Math.abs(rel.days) <= 6 ? `${shortDate(vital.date)} · ${rel.label}` : shortDate(vital.date);
                out.tone = rel.tone;
            } else {
                out.display = _t("Nothing dated");
                out.tone = "";
            }
        } else if (vital.key === "expenses") {
            out.display = formatAmount(vital.amount, vital.currency_id);
        } else if (vital.key === "age") {
            out.display = vital.days ? _t("%s days", vital.days) : _t("Since today");
        }
        return out;
    }

    open(vital) {
        openTab(this.root.el, vital.tab);
    }
}

// =============================================================== next step
/**
 * What happens next on this matter, and its one action (SPEC 14.4): tick the
 * step, log the visit, record the session's outcome. While the matter waits
 * for approval the approval banner takes the card's place; approvers decide
 * from it.
 */
export class LdmNextStep extends Component {
    static template = "legal_department_management.NextStep";
    static props = { ...standardWidgetProps };

    static labels = {
        next: _t("Next"),
        done: _t("Mark done"),
        visit: _t("Log visit"),
        outcome: _t("Record outcome"),
        openDeadline: _t("Open the deadline"),
        approve: _t("Approve"),
        reject: _t("Reject"),
        resubmit: _t("Send for approval again"),
        waiting: _t("Waiting for approval"),
        waitingHint: _t("An approver decides before work starts."),
        rejected: _t("Approval refused"),
        closed: _t("This matter is closed."),
        approved: _t("Approved. Work can start."),
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({ busy: false });
    }

    get label() {
        return LdmNextStep.labels;
    }

    get cockpit() {
        return cockpitOf(this.props.record);
    }

    get approval() {
        return this.cockpit.approval || false;
    }

    get next() {
        return this.cockpit.next || false;
    }

    get canAct() {
        return !this.props.readonly && !this.cockpit.read_only && Boolean(this.props.record.resId);
    }

    get when() {
        const next = this.next;
        if (!next || !next.date) {
            return null;
        }
        const rel = relativeDay(next.date);
        const hour = formatHour(next.time);
        return {
            date: shortDate(next.date),
            label: rel.label,
            tone: rel.tone,
            hour,
        };
    }

    get icon() {
        return {
            hearing: "fa-gavel",
            step: "fa-check-square-o",
            visit: "fa-building-o",
            deadline: "fa-hourglass-half",
            target: "fa-flag-o",
            start: "fa-play-circle-o",
            none: "fa-circle-o",
            closed: "fa-check-circle",
        }[this.next.kind] || "fa-circle-o";
    }

    get approvalMeta() {
        const approval = this.approval;
        const parts = [];
        if (approval.state === "to_approve" && approval.requested_by) {
            parts.push(_t("Sent by %s", approval.requested_by));
        }
        if (approval.state === "rejected" && approval.decided_by) {
            parts.push(_t("Decided by %s", approval.decided_by));
        }
        if (approval.since) {
            parts.push(relativeDay(approval.since).label);
        }
        return parts.join(" · ");
    }

    get nextMeta() {
        const next = this.next;
        const parts = [];
        if (next.body) {
            parts.push(next.body);
        }
        if (next.who) {
            parts.push(_t("Assigned to %s", next.who));
        }
        if (next.legal_date && next.legal_date !== next.date) {
            parts.push(_t("Legal last day: %s", shortDate(next.legal_date)));
        }
        return parts.join(" · ");
    }

    async reload() {
        await this.props.record.load();
    }

    async run(fn) {
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            if (await saveFirst(this.props.record)) {
                await fn();
            }
        } finally {
            this.state.busy = false;
        }
    }

    services() {
        return { orm: this.orm, action: this.action, notification: this.notification };
    }

    markDone() {
        return this.run(() => toggleStep(this.services(), this.next.id, () => this.reload()));
    }

    logVisit() {
        return this.run(() =>
            runRecordAction(this.services(), "legal.task.step", "action_ldm_log_visit", this.next.id, () => this.reload())
        );
    }

    recordOutcome() {
        return this.run(() =>
            runRecordAction(this.services(), "legal.hearing", "action_ldm_record_outcome", this.next.id, () => this.reload())
        );
    }

    openDeadline() {
        return this.action.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "legal.deadline",
                res_id: this.next.id,
                views: [[false, "form"]],
                target: "new",
            },
            { onClose: () => this.reload() }
        );
    }

    approve() {
        return this.run(async () => {
            await this.orm.call("legal.task", "action_approve", [[this.props.record.resId]]);
            this.notification.add(this.label.approved, { type: "success" });
            await this.reload();
        });
    }

    reject() {
        return this.run(() =>
            runRecordAction(this.services(), "legal.task", "action_reject", this.props.record.resId, () => this.reload())
        );
    }

    resubmit() {
        return this.run(async () => {
            await this.orm.call("legal.task", "action_request_approval", [[this.props.record.resId]]);
            await this.reload();
        });
    }
}

// ============================================================== phase rail
/**
 * A lawsuit's court stages as a rail (first instance, appeal, cassation,
 * execution): done, current, still to come, with the case number of each
 * stage reached. No percentage: a lawsuit is not a progress bar.
 */
export class LdmPhaseRail extends Component {
    static template = "legal_department_management.PhaseRail";
    static props = { ...standardWidgetProps };

    static labels = {
        title: _t("Court stages"),
        done: _t("Done"),
        current: _t("Current stage"),
        todo: _t("Not reached"),
    };

    setup() {
        this.root = useRef("root");
    }

    get label() {
        return LdmPhaseRail.labels;
    }

    get phases() {
        return cockpitOf(this.props.record).phases || [];
    }

    statusLabel(phase) {
        return this.label[phase.status] || "";
    }

    open() {
        openTab(this.root.el, "case");
    }
}

// ========================================================= advanced toggle
/**
 * «More» (SPEC 14.4): the secondary fields sit in one group at the bottom of
 * the form, folded until asked for. The choice is remembered per user.
 */
export class LdmAdvancedToggle extends Component {
    static template = "legal_department_management.AdvancedToggle";
    static props = { ...standardWidgetProps };

    setup() {
        this.local = useState({ open: false });
    }

    get isOpen() {
        return this.env.ldmForm ? this.env.ldmForm.state.advanced : this.local.open;
    }

    get label() {
        return this.isOpen ? _t("Fewer details") : _t("More details");
    }

    toggle() {
        if (this.env.ldmForm) {
            this.env.ldmForm.toggleAdvanced();
        } else {
            this.local.open = !this.local.open;
        }
    }
}

const widgets = registry.category("view_widgets");
widgets.add("ldm_matter_vitals", { component: LdmMatterVitals, fieldDependencies: COCKPIT_FIELD });
widgets.add("ldm_next_step", { component: LdmNextStep, fieldDependencies: COCKPIT_FIELD });
widgets.add("ldm_phase_rail", { component: LdmPhaseRail, fieldDependencies: COCKPIT_FIELD });
widgets.add("ldm_advanced_toggle", { component: LdmAdvancedToggle });
