from __future__ import annotations

from html import escape
from pathlib import Path

WIDTH = 1200
HEIGHT = 680
INK = "#e7edf5"
MUTED = "#98a7b8"
GRID = "#26384a"
PANEL = "#0c1724"
ACCENT = "#24d39a"
SECONDARY = "#61a8ff"
NEGATIVE = "#ff6b7a"


def _svg_frame(title: str, subtitle: str, body: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">
  <title id="title">{escape(title)}</title>
  <desc id="desc">{escape(subtitle)}</desc>
  <rect width="{WIDTH}" height="{HEIGHT}" fill="#07111d"/>
  <rect x="24" y="24" width="1152" height="632" rx="24" fill="{PANEL}" stroke="#203247"/>
  <text x="64" y="80" fill="{INK}" font-family="Inter,Segoe UI,sans-serif" font-size="30" font-weight="700">{escape(title)}</text>
  <text x="64" y="112" fill="{MUTED}" font-family="Inter,Segoe UI,sans-serif" font-size="16">{escape(subtitle)}</text>
  {body}
  <text x="64" y="626" fill="{MUTED}" font-family="Inter,Segoe UI,sans-serif" font-size="14">Synthetic paired evaluation — not measured merchant uplift</text>
</svg>
'''


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def render_policy_recovery_rate(report: dict, output: Path) -> None:
    labels = {
        "random": "Random",
        "rules": "Fixed rules",
        "linucb": "LinUCB",
        "incremental_value": "RecoverIQ incremental value",
    }
    rows = [
        (labels[name], values["mean_recovery_rate"] * 100)
        for name, values in report["policy_aggregates"].items()
    ]
    plot_x = 330
    plot_width = 760
    maximum = max(value for _, value in rows) * 1.12
    body = []
    for tick in range(0, 6):
        value = maximum * tick / 5
        x = plot_x + plot_width * tick / 5
        body.append(
            f'<line x1="{x:.1f}" y1="154" x2="{x:.1f}" y2="550" stroke="{GRID}"/>'
        )
        body.append(
            f'<text x="{x:.1f}" y="575" text-anchor="middle" fill="{MUTED}" font-family="Inter,Segoe UI,sans-serif" font-size="13">{value:.0f}%</text>'
        )
    for index, (label, value) in enumerate(rows):
        y = 188 + index * 88
        width = plot_width * value / maximum
        color = ACCENT if "RecoverIQ" in label else SECONDARY
        body.extend(
            [
                f'<text x="64" y="{y + 25}" fill="{INK}" font-family="Inter,Segoe UI,sans-serif" font-size="17">{escape(label)}</text>',
                f'<rect x="{plot_x}" y="{y}" width="{width:.1f}" height="38" rx="9" fill="{color}"/>',
                f'<text x="{plot_x + width + 12:.1f}" y="{y + 25}" fill="{INK}" font-family="Inter,Segoe UI,sans-serif" font-size="16" font-weight="700">{value:.2f}%</text>',
            ]
        )
    _write(
        output,
        _svg_frame(
            "Mean recovery rate by policy",
            f'{report["frozen_config"]["seed_count"]} paired seeds × {report["frozen_config"]["events_per_seed"]:,} cases',
            "\n  ".join(body),
        ),
    )


def render_seed_gain(report: dict, output: Path) -> None:
    rows = report["seed_comparisons"]["incremental_value"]
    values = [row["relative_recovered_revenue_gain_pct"] for row in rows]
    lower = min(0.0, min(values))
    upper = max(0.0, max(values))
    padding = max(1.0, (upper - lower) * 0.12)
    lower -= padding
    upper += padding
    plot_left, plot_top, plot_width, plot_height = 72, 160, 1056, 384

    def y_position(value: float) -> float:
        return plot_top + (upper - value) / (upper - lower) * plot_height

    zero_y = y_position(0)
    bar_gap = plot_width / len(rows)
    bar_width = max(8, bar_gap * 0.68)
    body = [
        f'<line x1="{plot_left}" y1="{zero_y:.1f}" x2="{plot_left + plot_width}" y2="{zero_y:.1f}" stroke="{INK}" stroke-width="2"/>',
    ]
    for tick in range(5):
        value = lower + (upper - lower) * tick / 4
        y = y_position(value)
        body.extend(
            [
                f'<line x1="{plot_left}" y1="{y:.1f}" x2="{plot_left + plot_width}" y2="{y:.1f}" stroke="{GRID}"/>',
                f'<text x="{plot_left - 12}" y="{y + 5:.1f}" text-anchor="end" fill="{MUTED}" font-family="Inter,Segoe UI,sans-serif" font-size="13">{value:.1f}%</text>',
            ]
        )
    for index, row in enumerate(rows):
        value = row["relative_recovered_revenue_gain_pct"]
        x = plot_left + index * bar_gap + (bar_gap - bar_width) / 2
        y = y_position(value)
        rect_y = min(y, zero_y)
        height = max(1, abs(zero_y - y))
        color = ACCENT if value >= 0 else NEGATIVE
        body.append(
            f'<rect x="{x:.1f}" y="{rect_y:.1f}" width="{bar_width:.1f}" height="{height:.1f}" rx="3" fill="{color}"><title>Seed {row["seed"]}: {value:.2f}%</title></rect>'
        )
        if index % 2 == 0:
            body.append(
                f'<text x="{x + bar_width / 2:.1f}" y="570" text-anchor="middle" fill="{MUTED}" font-family="Inter,Segoe UI,sans-serif" font-size="11">{row["seed"]}</text>'
            )
    body.append(
        f'<text x="{plot_left + plot_width / 2}" y="596" text-anchor="middle" fill="{MUTED}" font-family="Inter,Segoe UI,sans-serif" font-size="14">Paired seed</text>'
    )
    _write(
        output,
        _svg_frame(
            "RecoverIQ gain versus fixed rules by seed",
            "Relative simulated recovered-revenue difference; every seed is shown",
            "\n  ".join(body),
        ),
    )


def render_oracle_regret(report: dict, output: Path) -> None:
    labels = {
        "random": "Random",
        "rules": "Fixed rules",
        "linucb": "LinUCB",
        "incremental_value": "RecoverIQ incremental value",
    }
    rows = [
        (labels[name], values["mean_oracle_regret_rupees"])
        for name, values in report["policy_aggregates"].items()
    ]
    maximum = max(value for _, value in rows) * 1.12
    plot_x, plot_width = 330, 760
    body = []
    for tick in range(0, 6):
        value = maximum * tick / 5
        x = plot_x + plot_width * tick / 5
        body.extend(
            [
                f'<line x1="{x:.1f}" y1="154" x2="{x:.1f}" y2="550" stroke="{GRID}"/>',
                f'<text x="{x:.1f}" y="575" text-anchor="middle" fill="{MUTED}" font-family="Inter,Segoe UI,sans-serif" font-size="13">₹{value / 1_000_000:.1f}M</text>',
            ]
        )
    for index, (label, value) in enumerate(rows):
        y = 188 + index * 88
        width = plot_width * value / maximum
        color = ACCENT if "RecoverIQ" in label else SECONDARY
        body.extend(
            [
                f'<text x="64" y="{y + 25}" fill="{INK}" font-family="Inter,Segoe UI,sans-serif" font-size="17">{escape(label)}</text>',
                f'<rect x="{plot_x}" y="{y}" width="{width:.1f}" height="38" rx="9" fill="{color}"/>',
                f'<text x="{plot_x + width + 12:.1f}" y="{y + 25}" fill="{INK}" font-family="Inter,Segoe UI,sans-serif" font-size="15" font-weight="700">₹{value:,.0f}</text>',
            ]
        )
    _write(
        output,
        _svg_frame(
            "Mean oracle regret by policy",
            "Lower is better; oracle is restricted to autonomously permitted actions",
            "\n  ".join(body),
        ),
    )


def render_final_charts(report: dict, output_dir: Path) -> list[Path]:
    paths = [
        output_dir / "policy_recovery_rate.svg",
        output_dir / "incremental_value_seed_gain.svg",
        output_dir / "oracle_regret.svg",
    ]
    render_policy_recovery_rate(report, paths[0])
    render_seed_gain(report, paths[1])
    render_oracle_regret(report, paths[2])
    return paths
