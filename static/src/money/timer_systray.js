import { Component, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { formatFloatTime } from "@web/views/fields/formatters";
import { parseFloatTime } from "@web/views/fields/parsers";

/**
 * The dialog shown when the timer stops: two answers (what was done, billable)
 * and the measured time, which can be corrected as 1.5 or 1:30.
 */
export class LdmTimerStopDialog extends Component {
    static template = "legal_department_management.LdmTimerStopDialog";
    static components = { Dialog };
    static props = {
        taskName: String,
        hours: Number,
        confirm: Function,
        discard: Function,
        close: Function,
    };

    setup() {
        this.state = useState({
            description: "",
            billable: true,
            duration: formatFloatTime(Math.max(this.props.hours, 0.01)),
            error: "",
            saving: false,
        });
    }

    async save() {
        let hours = NaN;
        try {
            hours = parseFloatTime((this.state.duration || "").trim());
        } catch {
            hours = NaN;
        }
        if (!this.state.description.trim()) {
            this.state.error = _t("Say what was done.");
            return;
        }
        if (!(hours > 0) || hours > 24) {
            this.state.error = _t("Enter the time as 1.5 or 1:30.");
            return;
        }
        this.state.saving = true;
        try {
            await this.props.confirm({
                description: this.state.description.trim(),
                billable: this.state.billable,
                duration: hours,
            });
            this.props.close();
        } finally {
            this.state.saving = false;
        }
    }

    async discard() {
        await this.props.discard();
        this.props.close();
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey && ev.target.tagName !== "TEXTAREA") {
            ev.preventDefault();
            this.save();
        }
    }
}

/**
 * Top-bar timer for time tracking (switch "Time tracking"). Starts on the
 * matter that is open, or on one of the user's recent matters; stopping asks
 * for what was done and records a time entry. The running state lives on the
 * server, so a reload or another device shows the same timer.
 */
export class LdmTimerSystray extends Component {
    static template = "legal_department_management.LdmTimerSystray";
    static components = { Dropdown, DropdownItem };
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.dropdown = useDropdownState();
        this.state = useState({
            enabled: false,
            running: false,
            taskId: false,
            taskName: "",
            elapsed: 0,
            recent: [],
        });
        onWillStart(async () => {
            this.state.enabled = await user.hasGroup("legal_department_management.group_ldm_time");
            if (this.state.enabled) {
                await this.refresh();
            }
        });
        this.ticker = setInterval(() => {
            if (this.state.running) {
                this.state.elapsed += 1;
            }
        }, 1000);
        onWillUnmount(() => clearInterval(this.ticker));
    }

    async refresh() {
        const timer = await this.orm.call("legal.time.entry", "ldm_timer_state", []);
        this.state.running = Boolean(timer.running);
        this.state.taskId = timer.task_id || false;
        this.state.taskName = timer.task_name || "";
        this.state.elapsed = timer.elapsed || 0;
    }

    get toggleTitle() {
        return this.state.running ? this.state.taskName : _t("Timer");
    }

    get elapsedLabel() {
        const total = Math.max(0, Math.floor(this.state.elapsed));
        const hours = Math.floor(total / 3600);
        const minutes = Math.floor((total % 3600) / 60);
        const seconds = total % 60;
        const pad = (n) => String(n).padStart(2, "0");
        return `${hours}:${pad(minutes)}:${pad(seconds)}`;
    }

    /** The matter open in the main view, if the user is looking at one. */
    get openMatterId() {
        const controller = this.action.currentController;
        if (!controller) {
            return false;
        }
        const model = controller.props?.resModel || controller.action?.res_model;
        const viewType = controller.view?.type || controller.props?.type;
        const resId = controller.currentState?.resId || controller.props?.resId;
        return model === "legal.task" && viewType === "form" && Number.isInteger(resId) ? resId : false;
    }

    async onBeforeOpen() {
        if (!this.state.running) {
            this.state.recent = await this.orm.call("legal.time.entry", "ldm_timer_recent_matters", []);
        }
    }

    async start(taskId) {
        this.dropdown.close();
        const timer = await this.orm.call("legal.time.entry", "ldm_timer_start", [taskId]);
        this.state.running = Boolean(timer.running);
        this.state.taskId = timer.task_id || false;
        this.state.taskName = timer.task_name || "";
        this.state.elapsed = timer.elapsed || 0;
    }

    startHere() {
        return this.start(this.openMatterId);
    }

    stop() {
        this.dropdown.close();
        this.dialog.add(LdmTimerStopDialog, {
            taskName: this.state.taskName,
            hours: this.state.elapsed / 3600,
            confirm: async ({ description, billable, duration }) => {
                const entry = await this.orm.call("legal.time.entry", "ldm_timer_stop", [description], {
                    billable,
                    duration,
                });
                this.notification.add(
                    _t("%(hours)s recorded on %(matter)s.", {
                        hours: formatFloatTime(entry.duration),
                        matter: entry.task_name,
                    }),
                    { type: "success" }
                );
                await this.refresh();
            },
            discard: async () => {
                await this.orm.call("legal.time.entry", "ldm_timer_discard", []);
                await this.refresh();
            },
        });
    }

    openRunningMatter() {
        this.dropdown.close();
        if (this.state.taskId) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "legal.task",
                res_id: this.state.taskId,
                views: [[false, "form"]],
            });
        }
    }
}

registry.category("systray").add("ldm_timer", { Component: LdmTimerSystray }, { sequence: 45 });
