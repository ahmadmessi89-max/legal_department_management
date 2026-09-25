import { Component, onMounted, onPatched, onWillUnmount, useRef } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";

/**
 * One Chart.js chart in the workspace's language (design-direction.md):
 * flat fills in the token colours, no gradients, the values written on the
 * bars instead of a legend where one series is shown, the reading direction
 * respected, and every bar opening the records it counts (`onPick`).
 *
 * `spec` is a chart of the board's payload: `{kind: "bars", items: [...]}`
 * or `{kind: "stacked", labels: [...], series: [...]}`; `format` turns a
 * value into its text; `colors` maps a tone to a colour read from the tokens.
 */
export class LdmChart extends Component {
    static template = "legal_department_management.LdmChart";
    static props = {
        spec: Object,
        format: Function,
        colors: Object,
        onPick: Function,
        labels: { type: Array, optional: true },
        ariaLabel: { type: String, optional: true },
    };

    setup() {
        this.canvasRef = useRef("canvas");
        this.chart = null;
        onMounted(() => this.draw());
        onPatched(() => this.draw());
        onWillUnmount(() => this.chart && this.chart.destroy());
    }

    get isRtl() {
        return localization.direction === "rtl";
    }

    /** A height class by the number of rows: no inline style, no stretched bars. */
    get sizeClass() {
        const spec = this.props.spec;
        const rows = spec.kind === "bars" ? spec.items.length : spec.horizontal ? spec.labels.length : 0;
        if (!rows) {
            return "o_ldm_chart_m";
        }
        return rows <= 3 ? "o_ldm_chart_s" : rows <= 7 ? "o_ldm_chart_m" : "o_ldm_chart_l";
    }

    config() {
        const { spec, colors, format } = this.props;
        const style = getComputedStyle(this.canvasRef.el);
        const font = style.getPropertyValue("--ldm-font-text") || style.fontFamily;
        const ink = colors.ink;
        const bar = colors.signal || ink;
        const mono = colors.mono || font;
        const horizontal = spec.kind === "bars" || spec.horizontal;
        let labels;
        let datasets;
        if (spec.kind === "bars") {
            labels = spec.items.map((item) => item.label);
            datasets = [
                {
                    data: spec.items.map((item) => item.value),
                    backgroundColor: spec.items.map((item) =>
                        spec.tone === "kind" ? colors[`kind_${item.kind}`] || bar : colors[spec.tone] || bar
                    ),
                    borderRadius: 0,
                    borderSkipped: false,
                    maxBarThickness: 20,
                },
            ];
        } else {
            labels = this.props.labels || spec.labels;
            datasets = spec.series.map((serie) => ({
                label: serie.label,
                data: serie.values,
                // "ink" (work in hand) takes the ramp's darkest blue: one hue on the charts.
                backgroundColor: serie.tone === "ink" ? colors.ink0 || bar : colors[serie.tone] || bar,
                borderRadius: 0,
                borderSkipped: spec.kind === "stacked" ? "start" : false,
                maxBarThickness: 24,
            }));
        }
        const valueAxis = {
            beginAtZero: true,
            grace: horizontal ? "18%" : "8%",
            stacked: spec.kind === "stacked",
            grid: { color: colors.grid || colors.rule, drawTicks: false },
            border: { display: false, dash: [3, 4] },
            ticks: {
                color: colors.inkFaint,
                font: { family: mono, size: 11 },
                padding: 6,
                callback: (value) => format(value, true),
                maxTicksLimit: 5,
                precision: spec.unit === "count" ? 0 : undefined,
            },
            reverse: horizontal && this.isRtl,
        };
        const categoryAxis = {
            stacked: spec.kind === "stacked",
            grid: { display: false },
            border: { color: colors.rule },
            ticks: {
                color: colors.ink,
                font: { family: font, size: 13 },
                autoSkip: false,
                callback(value) {
                    const label = this.getLabelForValue(value) || "";
                    return label.length > 28 ? `${label.slice(0, 27)}…` : label;
                },
            },
            reverse: !horizontal && this.isRtl,
            position: horizontal && this.isRtl ? "right" : undefined,
        };
        const singleSeries = spec.kind === "bars";
        return {
            type: "bar",
            data: { labels, datasets },
            options: {
                indexAxis: horizontal ? "y" : "x",
                maintainAspectRatio: false,
                animation: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? false : { duration: 250 },
                layout: { padding: { left: 8, right: 8, top: 4 } },
                scales: horizontal ? { x: valueAxis, y: categoryAxis } : { x: categoryAxis, y: valueAxis },
                plugins: {
                    legend: {
                        display: !singleSeries,
                        position: "top",
                        align: "start",
                        rtl: this.isRtl,
                        labels: {
                            color: colors.inkSoft,
                            font: { family: font, size: 13 },
                            boxWidth: 12,
                            boxHeight: 12,
                            useBorderRadius: true,
                            borderRadius: 0,
                        },
                    },
                    tooltip: {
                        rtl: this.isRtl,
                        backgroundColor: ink,
                        titleColor: "#fff",
                        bodyColor: "rgba(255, 255, 255, 0.82)",
                        titleFont: { family: font, weight: "600", size: 13 },
                        bodyFont: { family: mono, size: 12 },
                        padding: 10,
                        cornerRadius: 0,
                        caretSize: 5,
                        displayColors: !singleSeries,
                        boxPadding: 4,
                        callbacks: {
                            label: (ctx) => {
                                const text = format(ctx.parsed[horizontal ? "x" : "y"]);
                                return singleSeries ? text : `${ctx.dataset.label}: ${text}`;
                            },
                        },
                    },
                },
                onHover: (event, elements) => {
                    event.native.target.style.cursor = elements.length ? "pointer" : "default";
                },
                onClick: (event, elements) => {
                    if (elements.length) {
                        const { datasetIndex, index } = elements[0];
                        this.props.onPick(datasetIndex, index);
                    }
                },
            },
            plugins: singleSeries ? [directLabels(format, colors.ink, mono, this.isRtl)] : [],
        };
    }

    draw() {
        if (!this.canvasRef.el || !window.Chart) {
            return;
        }
        if (this.chart) {
            this.chart.destroy();
        }
        this.chart = new window.Chart(this.canvasRef.el, this.config());
    }
}

/**
 * Write each bar's value at its end, so a one-series chart needs no legend
 * and no reading off an axis.
 */
function directLabels(format, color, font, rtl) {
    return {
        id: "ldmDirectLabels",
        afterDatasetsDraw(chart) {
            const { ctx } = chart;
            const meta = chart.getDatasetMeta(0);
            const data = chart.data.datasets[0].data;
            ctx.save();
            ctx.fillStyle = color;
            ctx.font = `500 12px ${font}`;
            ctx.textBaseline = "middle";
            meta.data.forEach((bar, index) => {
                // Counts in full; days and money short (the answer line gives the full amount).
                const text = format(data[index], true);
                const { x, y } = bar.tooltipPosition();
                if (chart.options.indexAxis === "y") {
                    ctx.textAlign = rtl ? "right" : "left";
                    ctx.fillText(text, rtl ? x - 6 : x + 6, y);
                } else {
                    ctx.textAlign = "center";
                    ctx.fillText(text, x, y - 10);
                }
            });
            ctx.restore();
        },
    };
}
