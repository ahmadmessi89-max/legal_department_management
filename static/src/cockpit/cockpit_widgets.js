import { Component, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

import {
    formatAmount, formatHour, markStampLanding, relativeDay, shortDate, takeStampLanding,
} from "../core/ldm_format";
import { runRecordAction, toggleStep } from "../core/ldm_step_actions";
import { LdmIcon } from "../core/ldm_icon";

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

function selectionLabel(record, field) {
    const value = record.data[field];
    const pair = ((record.fields[field] && record.fields[field].selection) || []).find(([key]) => key === value);
    return pair ? pair[1] : "";
}

// ============================================================ title band
/**
 * The line under the matter's title inside the ink band (design direction):
 * who it is for and where, its status and court stage as pills, what is wrong
 * with it now (from real data), and the violet stamp once it is approved.
 */
export class LdmTitleMeta extends Component {
    static template = "legal_department_management.TitleMeta";
    static components = { LdmIcon };
    static props = { ...standardWidgetProps };

    static stateIcons = {
        draft: "circle-dot",
        in_progress: "refresh-cw",
        pending_docs: "hourglass",
        done: "circle-check",
        cancelled: "circle-x",
    };

    setup() {
        this.landing = takeStampLanding(this.props.record.resId);
    }

    get data() {
        return this.props.record.data;
    }

    get where() {
        const parts = [this.data.legal_company_id, this.data.department_id].filter(Boolean);
        return parts.map((value) => value.display_name).join(" · ");
    }

    get responsible() {
        return this.data.lawyer_id ? this.data.lawyer_id.display_name : "";
    }

    get statePill() {
        return {
            label: selectionLabel(this.props.record, "state"),
            icon: LdmTitleMeta.stateIcons[this.data.state] || "circle",
        };
    }

    get stagePill() {
        if (!["litigation", "execution"].includes(this.data.kind) || !this.data.court_stage) {
            return "";
        }
        return selectionLabel(this.props.record, "court_stage");
    }

    get flags() {
        return cockpitOf(this.props.record).flags || [];
    }

    get approved() {
        return this.data.approval_state === "approved";
    }

    get approvedLabel() {
        return _t("Approved");
    }

    get responsibleLabel() {
        return _t("Responsible");
    }
}

// ================================================================= vitals
/**
 * The matter's vital facts on one line (SPEC 5.3): the next date and its
 * days left, documents N of M, sessions, expenses, time in this status. Each
 * one is a door to the tab that holds its detail.
 */
export class LdmMatterVitals extends Component {
    static template = "legal_department_management.MatterVitals";
    static components = { LdmIcon };
    static props = { ...standardWidgetProps };

    static icons = {
        next: "calendar-clock",
        sessions: "gavel",
        documents: "file-check",
        steps: "list-checks",
        expenses: "wallet",
        age: "clock",
    };

    setup() {
        this.root = useRef("root");
    }

    get vitals() {
        return (cockpitOf(this.props.record).vitals || []).map((vital) => this.decorate(vital));
    }

    decorate(vital) {
        const out = {
            ...vital,
            display: vital.value || "",
            tone: vital.tone || "",
            icon: LdmMatterVitals.icons[vital.key] || "circle",
        };
        if (vital.key === "next") {
            if (vital.date) {
                const rel = relativeDay(vital.date);
                out.display = rel.days !== null && Math.abs(rel.days) <= 6
                    ? `${shortDate(vital.date)} · ${rel.label}` : shortDate(vital.date);
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
 * for approval the approval notice takes the card's place; approvers decide
 * from it. Below it, when the matter type and the body imply another target
 * date, the suggestion with "Use this date".
 */
export class LdmNextStep extends Component {
    static template = "legal_department_management.NextStep";
    static components = { LdmIcon };
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
        suggested: _t("Suggested target date"),
        useIt: _t("Use this date"),
        current: _t("Now: %s"),
        noCurrent: _t("No target date yet"),
        suggestionUsed: _t("Target date updated."),
    };

    static icons = {
        hearing: "gavel",
        step: "list-checks",
        visit: "building-2",
        deadline: "hourglass",
        target: "flag",
        start: "circle-dot",
        none: "circle",
        closed: "circle-check",
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

    get suggestion() {
        return this.cockpit.suggestion || false;
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
        return { date: shortDate(next.date), label: rel.label, tone: rel.tone, hour: formatHour(next.time) };
    }

    get icon() {
        return LdmNextStep.icons[this.next.kind] || "circle";
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

    get suggestionDate() {
        const suggestion = this.suggestion;
        return suggestion ? shortDate(suggestion.date) : "";
    }

    get suggestionCurrent() {
        const suggestion = this.suggestion;
        return suggestion.current ? _t("Now: %s", shortDate(suggestion.current)) : this.label.noCurrent;
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
            markStampLanding(this.props.record.resId);
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

    useSuggestion() {
        return this.run(async () => {
            await this.orm.call("legal.task", "action_ldm_use_suggested_target", [[this.props.record.resId]]);
            this.notification.add(this.label.suggestionUsed, { type: "success" });
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
    static components = { LdmIcon };
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
    static components = { LdmIcon };
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
widgets.add("ldm_title_meta", { component: LdmTitleMeta, fieldDependencies: COCKPIT_FIELD });
widgets.add("ldm_matter_vitals", { component: LdmMatterVitals, fieldDependencies: COCKPIT_FIELD });
widgets.add("ldm_next_step", { component: LdmNextStep, fieldDependencies: COCKPIT_FIELD });
widgets.add("ldm_phase_rail", { component: LdmPhaseRail, fieldDependencies: COCKPIT_FIELD });
widgets.add("ldm_advanced_toggle", { component: LdmAdvancedToggle });
