import { Component, onWillStart, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { formatCurrency } from "@web/core/currency";
import { formatInteger } from "@web/views/fields/formatters";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

import { LdmIcon } from "../core/ldm_icon";
import { longDate } from "../core/ldm_format";
import { LdmChart } from "./ldm_chart";

const { DateTime } = luxon;

/** The questions the board answers, in reading order. */
const PANELS = [
    { key: "by_body", icon: "landmark", title: _t("Where are the open matters?"),
      hint: _t("Open matters by body or court."), empty: _t("No open matter.") },
    { key: "by_kind", icon: "clipboard-list", title: _t("What kind of work is open?"),
      hint: _t("Open matters by kind."), empty: _t("No open matter.") },
    { key: "workload", icon: "users", title: _t("Who carries the work?"),
      hint: _t("Open matters by responsible lawyer and status."), empty: _t("No open matter."), wide: true },
    { key: "time_to_close", icon: "hourglass", title: _t("How long does each type take to close?"),
      hint: _t("Median working days from opening to closing, matters closed in the period."),
      empty: _t("No matter was closed in the period.") },
    { key: "deadlines", icon: "calendar-check", title: _t("Are deadlines met?"),
      hint: _t("Our statutory and reply deadlines, met or missed, by month."),
      empty: _t("No deadline was met or missed in the period.") },
    { key: "past_target", icon: "building-2", title: _t("Which bodies keep our files too long?"),
      hint: _t("Open government transactions at the body past its usual answer time."),
      empty: _t("No transaction is at a body past its target.") },
    { key: "exposure", icon: "scale", title: _t("What is at stake in court?"),
      hint: _t("Claim values of open lawsuits by the side we act for, in the company currency."),
      empty: _t("No open lawsuit has a claim value.") },
    { key: "expenses", icon: "receipt", title: _t("What do we spend, and for whom?"),
      hint: _t("Confirmed expenses by month and client, in the company currency."),
      empty: _t("No expense in the period."), wide: true },
];

/**
 * The managers' analytics board (design-direction.md, "Charts"): real
 * questions answered from the records the reader may see, one server call
 * (`legal.task.ldm_analytics`), each figure and each bar opening exactly the
 * records it counts. Read-only for everyone, auditors included.
 */
export class LdmAnalytics extends Component {
    static template = "legal_department_management.Analytics";
    static components = { LdmIcon, LdmChart };
    static props = { ...standardActionServiceProps };

    static labels = {
        title: _t("How the work is going"),
        period: _t("Period"),
        loading: _t("Counting…"),
        error: _t("The figures could not be loaded."),
        retry: _t("Try again"),
        openList: _t("Open the list"),
        forUs: _t("Brought by us"),
        againstUs: _t("Brought against us"),
        total: _t("Total"),
        days: _t("%s working days"),
        matters: _t("%s matters"),
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.root = useRef("root");
        this.state = useState({ period: "year", loading: true, error: false, data: null, colors: null });
        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            this.palette = readPalette();
            await this.load();
        });
    }

    get label() {
        return LdmAnalytics.labels;
    }

    get panels() {
        const charts = (this.state.data && this.state.data.charts) || {};
        return PANELS.map((panel) => {
            const spec = charts[panel.key];
            return { ...panel, spec, empty: !spec || isEmpty(spec) ? panel.empty : "", answer: this.answer(panel.key, spec) };
        });
    }

    get periodLabel() {
        const data = this.state.data;
        if (!data) {
            return "";
        }
        return `${longDate(data.date_from)} – ${longDate(data.date_to)}`;
    }

    async load(period = this.state.period) {
        this.state.loading = true;
        this.state.error = false;
        try {
            this.state.data = await this.orm.call("legal.task", "ldm_analytics", [], { period });
            this.state.period = period;
        } catch {
            // The board says so and offers to try again; nothing is half drawn.
            this.state.error = true;
        } finally {
            this.state.loading = false;
        }
    }

    setPeriod(period) {
        if (period !== this.state.period || this.state.error) {
            this.load(period);
        }
    }

    formatter(unit) {
        const currency = this.state.data && this.state.data.currency;
        return (value, short = false) => {
            if (unit === "money" && currency) {
                if (short && Math.abs(value) >= 1000) {
                    return compact(value);
                }
                return formatCurrency(value || 0, currency.id, { digits: [69, currency.digits] });
            }
            if (unit === "days") {
                return short ? formatInteger(value) : _t("%s working days", formatInteger(Math.round(value)));
            }
            return formatInteger(value || 0);
        };
    }

    monthLabels(spec) {
        if (!spec || !spec.months) {
            return undefined;
        }
        return spec.labels.map((iso) => DateTime.fromISO(iso).toFormat("MMM yy"));
    }

    /** The one sentence that answers the question, from the same numbers. */
    answer(key, spec) {
        if (!spec || isEmpty(spec)) {
            return "";
        }
        const money = this.formatter("money");
        if (spec.kind === "bars" && key === "exposure") {
            return `${this.label.forUs}: ${money(spec.total_for)} · ${this.label.againstUs}: ${money(spec.total_against)}`;
        }
        if (spec.kind === "bars") {
            const top = spec.items[0];
            if (key === "time_to_close") {
                const slowest = [...spec.items].sort((a, b) => b.value - a.value)[0];
                return _t("Slowest: %(type)s, %(days)s working days (%(count)s closed)", {
                    type: slowest.label, days: Math.round(slowest.value), count: slowest.count,
                });
            }
            return _t("Most: %(label)s (%(value)s)", { label: top.label, value: formatInteger(top.value) });
        }
        if (key === "deadlines") {
            const met = sum(spec.series[0].values);
            const missed = sum(spec.series[1].values);
            return _t("%(met)s met, %(missed)s missed", { met, missed });
        }
        if (key === "expenses") {
            return `${this.label.total}: ${money(spec.total)}`;
        }
        if (key === "workload") {
            return _t("%(people)s people carry %(count)s open matters", {
                people: spec.labels.length, count: spec.series.reduce((t, s) => t + sum(s.values), 0),
            });
        }
        return "";
    }

    pick(panel, datasetIndex, index) {
        const spec = panel.spec;
        const target = spec.kind === "bars" ? spec.items[index].action : spec.series[datasetIndex].actions[index];
        this.open(target);
    }

    open(target) {
        if (!target) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: target.name,
            res_model: target.model,
            domain: target.domain,
            views: [[false, "list"], [false, "form"]],
            target: "current",
            context: { create: false },
        });
    }
}

/**
 * The chart colours, read from the design tokens (ldm_tokens.scss) on a probe
 * element, so the charts use the same values as the page, dark mode included.
 */
function readPalette() {
    const probe = document.createElement("div");
    probe.className = "o_ldm";
    probe.hidden = true;
    document.body.append(probe);
    const css = getComputedStyle(probe);
    const get = (name, fallback) => (css.getPropertyValue(name) || "").trim() || fallback;
    const colors = {
        ink: get("--ldm-ink", "#090B11"),
        inkSoft: get("--ldm-ink-soft", "#475569"),
        inkFaint: get("--ldm-ink-faint", "#64748B"),
        rule: get("--ldm-rule", "#E2E8F0"),
        grid: get("--ldm-chart-grid", "#EEF2F7"),
        signal: get("--ldm-signal", "#2563EB"),
        success: get("--ldm-success", "#15803D"),
        danger: get("--ldm-danger", "#DC2626"),
        warning: get("--ldm-warning", "#B45309"),
        info: get("--ldm-signal", "#2563EB"),
        muted: get("--ldm-chart-6", "#CBD5E1"),
        mono: get("--ldm-font-mono", "monospace"),
    };
    // Series and kinds take a ramp of the one accent, darkest first (the
    // ANU identity has one hue; the ramp keeps series apart without a rainbow).
    const ramp = [1, 2, 3, 4, 5, 6].map((n) => get(`--ldm-chart-${n}`, colors.signal));
    ramp.forEach((color, index) => (colors[`ink${index}`] = color));
    ["litigation", "government", "execution", "contract", "opinion", "corporate", "investigation", "other"].forEach(
        (kind, index) => (colors[`kind_${kind}`] = ramp[Math.min(index, ramp.length - 1)])
    );
    probe.remove();
    return colors;
}

function sum(values) {
    return values.reduce((total, value) => total + value, 0);
}

function isEmpty(spec) {
    if (spec.kind === "bars") {
        return !spec.items.length;
    }
    return !spec.labels.length || spec.series.every((serie) => serie.values.every((value) => !value));
}

/** 1.2M, 350K: axis ticks only; bars and tooltips show the full amount. */
function compact(value) {
    try {
        return new Intl.NumberFormat(luxon.Settings.defaultLocale || undefined, {
            notation: "compact",
            maximumFractionDigits: 1,
        }).format(value);
    } catch {
        return String(Math.round(value));
    }
}

registry.category("actions").add("ldm_analytics", LdmAnalytics);
