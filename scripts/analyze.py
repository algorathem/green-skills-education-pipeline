"""Green skills education pipeline: score courses, plot cost vs quality.

Quality index (0-100):
  0.35 * rating_score          (stars / 5 * 100; missing rating => 70 neutral)
  0.20 * review_confidence     (log10(n+1)/4, capped at 1, * 100; 0 if no reviews)
  0.25 * credential_score      (industry license 100 ... none 20)
  0.20 * employer_signal       (0-100, analyst-coded from hiring recognition)

Value score = quality / log10(cost_usd + 10)   (penalizes price without crushing cheap courses)
Quality per $100 = quality / (cost/100)
"""
from __future__ import annotations

import math
import textwrap
from pathlib import Path

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "output"
REPORTS = ROOT / "reports"

CREDENTIAL = {
    "industry_license": 100,
    "professional_standard": 88,
    "university": 80,
    "university_certificate": 90,
    "platform_cert": 42,
    "none": 20,
}

GREEN = "#1B7A4E"
TEAL = "#2A9D8F"
NAVY = "#1D3557"
ORANGE = "#E07A3D"
GOLD = "#C9A227"
GRAY = "#6B7280"
RED = "#C0392B"

CRED_COLOR = {
    "industry_license": GREEN,
    "professional_standard": TEAL,
    "university": NAVY,
    "university_certificate": NAVY,
    "platform_cert": ORANGE,
}
CRED_LABEL = {
    "industry_license": "Industry license",
    "professional_standard": "Professional standard",
    "university": "University / CET",
    "university_certificate": "University certificate",
    "platform_cert": "Platform certificate",
}
CLUSTER_LABEL = {
    "solar_pv": "Solar PV",
    "solar_design": "Solar design",
    "renewables": "Renewables (general)",
    "heat_pump_hvac": "Heat pump / HVAC",
    "ev_mobility": "EV / mobility",
    "carbon_accounting": "Carbon accounting",
    "esg_reporting": "ESG / reporting",
    "energy_management": "Energy management",
    "energy_systems": "Energy systems / grid",
    "mixed_green": "Mixed green stack",
}


def load_courses() -> pd.DataFrame:
    df = pd.read_csv(DATA / "courses.csv", skipinitialspace=True)
    for col in [
        "cost_usd_typical",
        "cost_usd_list",
        "rating",
        "n_reviews",
        "employer_signal",
        "hours_low",
        "hours_high",
        "students",
        "pass_rate_pct",
        "target_wage_usd",
        "job_growth_pct",
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def quality_components(row: pd.Series) -> dict:
    rating = row["rating"]
    n = 0.0 if pd.isna(row["n_reviews"]) else float(row["n_reviews"])
    review_conf = min(1.0, math.log10(n + 1.0) / 4.0)  # ~10k reviews => 1.0
    if pd.isna(rating):
        # No public stars: use a neutral 70, and review_conf stays ~0 so
        # the 20% review-confidence term is the uncertainty penalty.
        rating_score = 70.0
    else:
        rating_score = float(rating) / 5.0 * 100.0
    cred = CREDENTIAL.get(str(row["credential_type"]), 50)
    emp = 50.0 if pd.isna(row["employer_signal"]) else float(row["employer_signal"])
    quality = (
        0.35 * rating_score
        + 0.20 * (review_conf * 100.0)
        + 0.25 * cred
        + 0.20 * emp
    )
    cost = float(row["cost_usd_typical"])
    value = quality / math.log10(cost + 10.0)
    q_per_100 = quality / (cost / 100.0) if cost > 0 else np.nan
    wage = row["target_wage_usd"]
    roi_proxy = (float(wage) / cost) if (cost > 0 and not pd.isna(wage)) else np.nan
    return {
        "rating_score": round(rating_score, 2),
        "review_confidence": round(review_conf, 3),
        "credential_score": cred,
        "quality_index": round(quality, 2),
        "value_score": round(value, 2),
        "quality_per_100usd": round(q_per_100, 2) if not pd.isna(q_per_100) else np.nan,
        "wage_to_cost_ratio": round(roi_proxy, 1) if not pd.isna(roi_proxy) else np.nan,
    }


def score(df: pd.DataFrame) -> pd.DataFrame:
    parts = df.apply(quality_components, axis=1, result_type="expand")
    out = pd.concat([df, parts], axis=1)
    out["has_reviews"] = out["n_reviews"].fillna(0) > 0
    return out.sort_values("quality_index", ascending=False)


def style():
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#D1D5DB",
            "axes.grid": True,
            "grid.color": "#EEF2F6",
            "grid.linewidth": 0.8,
            "font.size": 10,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
            "figure.dpi": 160,
            "legend.frameon": True,
            "legend.fontsize": 8.5,
        }
    )


def save(fig, name: str):
    path = OUT / name
    fig.savefig(path, bbox_inches="tight", dpi=160, facecolor="white")
    plt.close(fig)
    return path


def usd_label(v: float) -> str:
    if v <= 0:
        return "$0"
    if v < 1000:
        return f"${v:,.0f}"
    return f"${v:,.0f}"


def log_usd_axis(ax, which: str = "x"):
    fmt = FuncFormatter(lambda v, _p: usd_label(v) if v >= 1 else "$0")
    if which == "x":
        ax.xaxis.set_major_formatter(fmt)
    else:
        ax.yaxis.set_major_formatter(fmt)


def cred_handles(include_norev: bool = True):
    hs = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=GREEN, markersize=9, label="Industry license"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=NAVY, markersize=9, label="University / CET"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=TEAL, markersize=9, label="Professional standard"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=ORANGE, markersize=9, label="Platform certificate"),
    ]
    if include_norev:
        hs.append(
            Line2D([0], [0], marker="D", color=GRAY, markerfacecolor="w", markersize=8, label="No public star reviews")
        )
    return hs


def wrap_name(name: str, width: int = 40) -> str:
    return "\n".join(textwrap.wrap(str(name), width=width)[:2])


def numbered_key(ax_key, labels: list[str], title: str = "Numbered key"):
    ax_key.axis("off")
    ax_key.set_xlim(0, 1)
    ax_key.set_ylim(0, 1)
    ax_key.set_title(title, loc="left", fontsize=10, pad=6)
    n = len(labels)
    cols = 2 if n > 16 else 1
    per_col = int(math.ceil(n / cols))
    for i, lab in enumerate(labels):
        col = i // per_col
        row = i % per_col
        x = 0.0 + col * 0.52
        y = 0.98 - row * (0.92 / max(per_col - 1, 1))
        ax_key.text(x, y, f"{i + 1:>2}. {lab}", fontsize=6.4, va="center", ha="left")


def chart_scatter(scored: pd.DataFrame):
    plot = scored.sort_values(["cost_usd_typical", "name"]).reset_index(drop=True)
    plot["n"] = np.arange(1, len(plot) + 1)
    plot["plot_cost"] = plot["cost_usd_typical"].clip(lower=1)
    fig = plt.figure(figsize=(17.2, 10.0))
    gs = gridspec.GridSpec(1, 2, width_ratios=[1.25, 1.15], wspace=0.12)
    ax = fig.add_subplot(gs[0])
    ax_key = fig.add_subplot(gs[1])
    rev = plot[plot["has_reviews"]]
    norev = plot[~plot["has_reviews"]]
    sizes = (np.log10(rev["n_reviews"].fillna(1) + 1) * 70).clip(36, 280)
    ax.scatter(
        rev["plot_cost"],
        rev["quality_index"],
        s=sizes,
        c=rev["credential_type"].map(CRED_COLOR).fillna(GRAY),
        alpha=0.88,
        edgecolors="white",
        linewidths=0.5,
        zorder=3,
    )
    ax.scatter(
        norev["plot_cost"],
        norev["quality_index"],
        s=70,
        facecolors="white",
        edgecolors=norev["credential_type"].map(CRED_COLOR).fillna(GRAY),
        linewidths=1.6,
        marker="D",
        zorder=2,
    )
    logx = np.log10(plot["plot_cost"].to_numpy())
    qy = plot["quality_index"].to_numpy()
    ox = np.zeros(len(plot))
    oy = np.zeros(len(plot))
    for i in range(len(plot)):
        for j in range(i):
            if abs(logx[i] - logx[j]) < 0.14 and abs(qy[i] - qy[j]) < 2.4:
                ox[i] = 9 if (i % 2 == 0) else -9
                oy[i] = 8 + 5 * ((i + j) % 3)
                break
    for i, r in plot.iterrows():
        ax.annotate(
            str(int(r["n"])),
            (r["plot_cost"], r["quality_index"]),
            textcoords="offset points",
            xytext=(ox[i], oy[i]),
            ha="center",
            va="center",
            fontsize=6.2,
            color=NAVY,
            zorder=4,
            bbox=dict(boxstyle="circle,pad=0.16", fc="white", ec="#D1D5DB", lw=0.4, alpha=0.95),
        )
    ax.set_xscale("log")
    ax.set_xlim(0.7, 30000)
    ax.set_ylim(32, 98)
    log_usd_axis(ax, "x")
    ax.set_xlabel("Typical unsubsidised cost per person (US dollars, log scale)")
    ax.set_ylabel("Quality index (0–100 composite score)")
    ax.set_title("Cost per person vs quality")
    ax.legend(handles=cred_handles(), loc="lower right", title="Credential (colour)")
    ax.text(
        0.0,
        -0.14,
        "Each number is one course (key at right). Filled circles = public star reviews (size = review count). "
        "Diamonds = no public stars. Quality = 35% stars + 20% review confidence + 25% credential + 20% employer signal.",
        transform=ax.transAxes,
        fontsize=8,
        color=GRAY,
    )
    key_labels = [f"{str(r['name'])[:32]}  {usd_label(r['cost_usd_typical'])}" for _, r in plot.iterrows()]
    numbered_key(ax_key, key_labels, f"All {len(plot)} courses (by cost) · USD")
    return save(fig, "01_cost_vs_quality.png")


def chart_value(scored: pd.DataFrame):
    top = scored.sort_values("value_score", ascending=True).tail(12)
    fig, ax = plt.subplots(figsize=(11, 7), layout="constrained")
    colors = [GREEN if v >= top["value_score"].median() else TEAL for v in top["value_score"]]
    y = np.arange(len(top))
    ax.barh(y, top["value_score"], color=colors, height=0.72)
    ax.set_yticks(y)
    ax.set_yticklabels([wrap_name(n, 38) for n in top["name"]], fontsize=8.5)
    for yi, v, cost, q in zip(y, top["value_score"], top["cost_usd_typical"], top["quality_index"]):
        ax.text(v + 0.4, yi, f"{v:.1f}   (quality {q:.0f} · {usd_label(cost)})", va="center", fontsize=7.5, color=NAVY)
    ax.set_xlabel("Value score  =  quality index ÷ log10(cost USD + 10)   [unitless; higher is better]")
    ax.set_title(f"Best quality for the money (top 12 of {len(scored)})")
    ax.set_xlim(0, top["value_score"].max() * 1.38)
    ax.legend(
        handles=[
            Line2D([0], [0], color=GREEN, lw=8, label="At or above median of this top-12"),
            Line2D([0], [0], color=TEAL, lw=8, label="Below median of this top-12"),
        ],
        loc="lower right",
    )
    return save(fig, "02_value_for_money.png")


def chart_cost_ladder(scored: pd.DataFrame):
    groups = list(scored.groupby("skill_cluster"))
    groups.sort(key=lambda kv: kv[1]["cost_usd_typical"].median())
    heights = [max(1.35, 0.42 * len(g) + 0.55) for _, g in groups]
    fig, axes = plt.subplots(
        len(groups),
        1,
        figsize=(12.2, sum(heights) + 1.4),
        sharex=True,
        gridspec_kw={"height_ratios": heights},
    )
    if len(groups) == 1:
        axes = [axes]
    for ax, (cl, g) in zip(axes, groups):
        g = g.sort_values("cost_usd_typical")
        y = np.arange(len(g))
        colors = g["credential_type"].map(CRED_COLOR).fillna(GRAY)
        ax.barh(y, g["cost_usd_typical"].clip(lower=0.8), color=colors, height=0.68)
        ax.set_yticks(y)
        ax.set_yticklabels([wrap_name(n, 36) for n in g["name"]], fontsize=7.6)
        ax.set_xscale("log")
        ax.set_xlim(0.7, 28000)
        ax.set_ylabel(CLUSTER_LABEL.get(cl, cl), fontsize=8.5, fontweight="bold", rotation=0, ha="right", va="center", labelpad=8)
        ax.tick_params(axis="x", labelbottom=False)
        ax.grid(axis="y", visible=False)
        for yi, cost in zip(y, g["cost_usd_typical"]):
            ax.text(max(float(cost), 1.0) * 1.12, yi, usd_label(cost), va="center", fontsize=7, color=NAVY)
    axes[-1].tick_params(axis="x", labelbottom=True)
    log_usd_axis(axes[-1], "x")
    axes[-1].set_xlabel("Typical unsubsidised cost per person (US dollars, log scale)")
    axes[0].set_title("Course cost ladder by skill cluster — every course, dollar amount on the bar")
    fig.legend(handles=cred_handles(include_norev=False), loc="upper center", ncol=4, bbox_to_anchor=(0.55, 1.0))
    fig.subplots_adjust(top=0.96, hspace=0.35)
    return save(fig, "03_cost_ladder.png")


def chart_gap():
    fig, ax = plt.subplots(figsize=(9, 5.4), layout="constrained")
    years = ["2023–24\nLinkedIn 2024 report", "2024–25\nLinkedIn 2025 report"]
    demand = [11.6, 7.7]
    supply = [5.6, 4.3]
    x = np.arange(len(years))
    w = 0.34
    b1 = ax.bar(x - w / 2, demand, w, color=ORANGE, label="Green hiring growth (demand)")
    b2 = ax.bar(x + w / 2, supply, w, color=GREEN, label="Share of workers with green skills (supply)")
    ax.bar_label(b1, fmt="%.1f%%", padding=3, fontsize=9)
    ax.bar_label(b2, fmt="%.1f%%", padding=3, fontsize=9)
    ax.set_xticks(x, years)
    ax.set_ylabel("Year-over-year change (percent)")
    ax.set_title("Green hiring still grows about 2× faster than green skills")
    ax.legend(title="Metric (same unit: % per year)")
    ax.set_ylim(0, 16)
    return save(fig, "04_hiring_vs_skills_gap.png")


def chart_future():
    fig, axes = plt.subplots(1, 3, figsize=(13.8, 5.2), layout="constrained")
    panels = [
        (
            axes[0],
            "US job outlook\n(BLS employment change, 2025–35)",
            ["Solar PV\ninstallers", "Wind turbine\ntechnicians", "HVAC\nmechanics"],
            [37, 30, 11],
            GREEN,
            "Percent change in employment",
        ),
        (
            axes[1],
            "Employer expectations by 2030\n(WEF Future of Jobs 2025)",
            ["Climate\nmitigation\ntransforms firm", "Climate\nadaptation\ntransforms firm", "Key skills\nwill change"],
            [47, 41, 39],
            ORANGE,
            "Percent of surveyed employers",
        ),
        (
            axes[2],
            "How green hires show up\n(LinkedIn 2025)",
            ["Green hires in\nnon-green job titles"],
            [53],
            TEAL,
            "Percent of green hires",
        ),
    ]
    for ax, title, labs, vals, color, ylab in panels:
        bars = ax.bar(labs, vals, color=color, width=0.55)
        ax.bar_label(bars, fmt="%.0f%%", padding=3, fontsize=9)
        ax.set_title(title, fontsize=10)
        ax.set_ylabel(ylab)
        ax.set_ylim(0, max(vals) * 1.25)
    fig.suptitle("Future-course demand signals — each panel has its own unit", fontsize=13, fontweight="bold")
    return save(fig, "05_future_demand_signals.png")


def chart_macro_cost():
    # Convert to USD so one axis; original currency stays in the label.
    rows = [
        ("UK employer spend per trainee (ESS 2024)", 2710, 2710 * 1.30, "GBP", NAVY, "Training spend"),
        ("UK construction spend per trainee", 5350, 5350 * 1.30, "GBP", NAVY, "Training spend"),
        ("Croatia green/digital voucher (max)", 3000, 3000 * 1.10, "EUR", TEAL, "Training voucher"),
        ("Australia apprentice incentive (max)", 10000, 10000 * 0.67, "AUD", TEAL, "Training voucher"),
        ("US solar PV installer median wage", 53140, 53140, "USD", GREEN, "Occupation wage"),
        ("US wind turbine tech median wage", 64120, 64120, "USD", GREEN, "Occupation wage"),
        ("US HVAC mechanic median wage", 61010, 61010, "USD", GREEN, "Occupation wage"),
    ]
    fig, ax = plt.subplots(figsize=(11, 6.2), layout="constrained")
    y = np.arange(len(rows))
    ax.barh(y, [r[2] for r in rows], color=[r[4] for r in rows], height=0.7)
    ax.set_yticks(y)
    ax.set_yticklabels([r[0] for r in rows], fontsize=9)
    for yi, orig, usd, cur in [(i, r[1], r[2], r[3]) for i, r in enumerate(rows)]:
        tag = usd_label(usd) if cur == "USD" else f"{usd_label(usd)}   ({cur} {orig:,.0f})"
        ax.text(usd * 1.02, yi, tag, va="center", fontsize=8, color=NAVY)
    ax.set_xlabel("US dollars (FX: GBP 1.30, EUR 1.10, AUD 0.67)")
    ax.set_title("Cost per person: public training spend vs occupation wages")
    ax.legend(
        handles=[
            Line2D([0], [0], color=NAVY, lw=8, label="Employer training spend"),
            Line2D([0], [0], color=TEAL, lw=8, label="Public voucher / incentive (cap)"),
            Line2D([0], [0], color=GREEN, lw=8, label="Occupation median wage (BLS)"),
        ],
        loc="lower right",
    )
    ax.set_xlim(0, 78000)
    return save(fig, "06_cost_per_person_macro.png")


def chart_oecd_supply():
    fig, ax = plt.subplots(figsize=(9.5, 5.2), layout="constrained")
    labels = [
        "Green-driven occupations\n(share of OECD workforce)",
        "GHG-intensive occupations\n(share of OECD workforce)",
        "Adult courses with green content\n(4-country low: AU, DE, SG, US)",
        "Adult courses with green content\n(4-country high)",
    ]
    vals = [20, 6, 2.1, 14.1]
    colors = [GREEN, RED, GOLD, TEAL]
    y = np.arange(len(labels))
    ax.barh(y, vals, color=colors, height=0.65)
    ax.set_yticks(y, labels)
    for yi, v in zip(y, vals):
        ax.text(v + 0.35, yi, f"{v:g}%", va="center", fontsize=9, color=NAVY)
    ax.set_xlabel("Percent of workforce or of course catalogue")
    ax.set_title("OECD: green jobs vs green training supply")
    ax.set_xlim(0, 28)
    ax.legend(
        handles=[
            Line2D([0], [0], color=GREEN, lw=8, label="Jobs that should grow in net-zero (workforce %)"),
            Line2D([0], [0], color=RED, lw=8, label="Jobs in high-emission industries (workforce %)"),
            Line2D([0], [0], color=GOLD, lw=8, label="Green share of adult courses — low"),
            Line2D([0], [0], color=TEAL, lw=8, label="Green share of adult courses — high"),
        ],
        loc="lower right",
        fontsize=8,
    )
    return save(fig, "07_oecd_jobs_vs_training.png")


def chart_roi(scored: pd.DataFrame):
    sub = scored.dropna(subset=["target_wage_usd"]).copy()
    sub = sub[sub["cost_usd_typical"] >= 30].sort_values(["target_occupation", "cost_usd_typical"])
    occs = list(sub["target_occupation"].astype(str).unique())
    occ_pos = {o: i for i, o in enumerate(occs)}
    fig = plt.figure(figsize=(16.8, 9.4))
    gs = gridspec.GridSpec(1, 2, width_ratios=[1.25, 1.15], wspace=0.12)
    ax = fig.add_subplot(gs[0])
    ax_key = fig.add_subplot(gs[1])
    rng = np.random.default_rng(0)
    sub = sub.reset_index(drop=True)
    sub["n"] = np.arange(1, len(sub) + 1)
    # Spread courses that share an occupation so they do not sit on one line.
    jitter = []
    for occ, g in sub.groupby("target_occupation", sort=False):
        n = len(g)
        jitter.extend(np.linspace(-0.28, 0.28, n) if n > 1 else [0.0])
    sub["y"] = [occ_pos[o] + j for o, j in zip(sub["target_occupation"], jitter)]
    sc = ax.scatter(
        sub["cost_usd_typical"],
        sub["y"],
        s=sub["quality_index"] * 2.4,
        c=sub["job_growth_pct"],
        cmap="YlGn",
        vmin=8,
        vmax=40,
        edgecolors=NAVY,
        linewidths=0.4,
        alpha=0.92,
        zorder=3,
    )
    for _, r in sub.iterrows():
        ax.annotate(
            str(int(r["n"])),
            (r["cost_usd_typical"], r["y"]),
            ha="center",
            va="center",
            fontsize=6,
            zorder=4,
            bbox=dict(boxstyle="circle,pad=0.15", fc="white", ec="#D1D5DB", lw=0.35, alpha=0.9),
        )
    ax.set_xscale("log")
    log_usd_axis(ax, "x")
    ax.set_yticks(range(len(occs)), [textwrap.fill(o, 28) for o in occs], fontsize=8)
    ax.set_xlabel("Training cost per person (US dollars, log scale)")
    ax.set_ylabel("Target occupation (US median wage used as the row)")
    ax.set_title("Training cost vs occupation — points jittered within each job")
    cbar = fig.colorbar(sc, ax=ax, shrink=0.72, pad=0.02)
    cbar.set_label("Projected occupation job growth (%)")
    ax.legend(
        handles=[
            Line2D([0], [0], marker="o", color="w", markerfacecolor=GREEN, markersize=5, label="Smaller = lower quality index"),
            Line2D([0], [0], marker="o", color="w", markerfacecolor=GREEN, markersize=12, label="Larger = higher quality index"),
        ],
        loc="lower right",
        title="Bubble size",
    )
    key_labels = [f"{str(r['name'])[:32]}  {usd_label(r['cost_usd_typical'])}" for _, r in sub.iterrows()]
    numbered_key(ax_key, key_labels, "Courses on this chart · USD")
    return save(fig, "08_cost_vs_wage.png")


def chart_htg_outcomes():
    labels = [
        "Satisfied with\nthe course",
        "Confident they\ncan install",
        "Installed ≥1\nheat pump",
        "Salary went up\nafter training",
        "Got MCS cert\nif not already",
    ]
    values = [94, 80, 33, 13, 12]
    colors = [GREEN, TEAL, ORANGE, GOLD, RED]
    fig, ax = plt.subplots(figsize=(10.5, 5.8), layout="constrained")
    bars = ax.bar(np.arange(len(labels)), values, color=colors, width=0.62)
    ax.set_xticks(np.arange(len(labels)), labels)
    ax.bar_label(bars, fmt="%.0f%%", padding=3, fontsize=9)
    ax.set_ylabel("Share of surveyed graduates (percent)")
    ax.set_title("Heat-pump training: course reviews vs work outcomes")
    ax.set_ylim(0, 112)
    ax.legend(
        handles=[
            Line2D([0], [0], color=GREEN, lw=8, label="Satisfaction with training"),
            Line2D([0], [0], color=TEAL, lw=8, label="Self-rated ability"),
            Line2D([0], [0], color=ORANGE, lw=8, label="Did the job (installed)"),
            Line2D([0], [0], color=GOLD, lw=8, label="Pay rose"),
            Line2D([0], [0], color=RED, lw=8, label="New MCS (if not already certified)"),
        ],
        loc="upper right",
        fontsize=8,
    )
    ax.text(
        0.0,
        -0.18,
        "England Heat Training Grant 2025 survey (DESNZ, Jun 2026). Sample n ≈ 139. 9,100 vouchers redeemed. Grant up to £500.",
        transform=ax.transAxes,
        fontsize=8,
        color=GRAY,
    )
    return save(fig, "09_htg_satisfaction_vs_jobs.png")


def chart_cluster(scored: pd.DataFrame):
    g = (
        scored.groupby("skill_cluster", as_index=False)
        .agg(n=("id", "count"), median_cost=("cost_usd_typical", "median"), mean_quality=("quality_index", "mean"))
        .sort_values("median_cost")
        .reset_index(drop=True)
    )
    g["label"] = g["skill_cluster"].map(CLUSTER_LABEL).fillna(g["skill_cluster"])
    fig, ax = plt.subplots(figsize=(12.2, 6.6), layout="constrained")
    ax.scatter(
        g["median_cost"].clip(lower=1),
        g["mean_quality"],
        s=g["n"] * 55,
        c=TEAL,
        alpha=0.8,
        edgecolors=NAVY,
        zorder=3,
    )
    # Manual offsets for the crowded high-cost cluster on the right.
    extra = {
        "carbon_accounting": (-22, 18),
        "energy_systems": (16, -24),
        "esg_reporting": (16, 16),
        "energy_management": (10, 12),
        "heat_pump_hvac": (-12, 14),
        "solar_pv": (10, 10),
        "solar_design": (-12, 10),
        "ev_mobility": (10, -14),
        "renewables": (8, 12),
        "mixed_green": (10, 10),
    }
    for _, r in g.iterrows():
        dx, dy = extra.get(r["skill_cluster"], (10, 8))
        ax.annotate(
            f"{r['label']}\n{int(r['n'])} courses · {usd_label(r['median_cost'])}",
            (max(float(r["median_cost"]), 1.0), r["mean_quality"]),
            textcoords="offset points",
            xytext=(dx, dy),
            fontsize=8,
            ha="left" if dx >= 0 else "right",
            color=NAVY,
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#E5E7EB", alpha=0.95),
        )
    ax.set_xscale("log")
    log_usd_axis(ax, "x")
    ax.set_xlabel("Median typical cost per person (US dollars, log scale)")
    ax.set_ylabel("Mean quality index (0–100)")
    ax.set_title("Skill clusters: median cost vs mean quality")
    ax.set_ylim(52, 92)
    ax.legend(
        handles=[
            Line2D([0], [0], marker="o", color="w", markerfacecolor=TEAL, markersize=6, label="1 course"),
            Line2D([0], [0], marker="o", color="w", markerfacecolor=TEAL, markersize=14, label="~10 courses"),
        ],
        loc="lower right",
        title="Bubble size = number of courses",
    )
    return save(fig, "10_cluster_cost_quality.png")


def chart_conversion_funnel():
    labels = [
        "Finished\nHTG course",
        "Liked the\ncourse",
        "Feel able\nto install",
        "Installed\n≥1 unit",
        "Got MCS\nif not already",
    ]
    values = [100, 94, 80, 33, 12]
    colors = [NAVY, GREEN, TEAL, ORANGE, RED]
    fig, ax = plt.subplots(figsize=(10.8, 5.8), layout="constrained")
    x = np.arange(len(labels))
    bars = ax.bar(x, values, color=colors, width=0.62)
    ax.set_xticks(x, labels)
    ax.bar_label(bars, labels=[f"{v}\nper 100" for v in values], padding=3, fontsize=8.5)
    ax.set_ylabel("Graduates (index: 100 = everyone in the survey)")
    ax.set_title("Conversion leak: training ≠ first install ≠ MCS")
    ax.set_ylim(0, 125)
    ax.annotate(
        "−67 never install\nin this sample",
        xy=(3, 33),
        xytext=(3.45, 62),
        fontsize=8,
        color=ORANGE,
        arrowprops=dict(arrowstyle="->", color=ORANGE),
    )
    ax.legend(
        handles=[
            Line2D([0], [0], color=NAVY, lw=8, label="Entered training"),
            Line2D([0], [0], color=GREEN, lw=8, label="Satisfied"),
            Line2D([0], [0], color=TEAL, lw=8, label="Confident"),
            Line2D([0], [0], color=ORANGE, lw=8, label="Installed"),
            Line2D([0], [0], color=RED, lw=8, label="Newly MCS-certified"),
        ],
        loc="upper right",
        fontsize=8,
    )
    ax.text(
        0.0,
        -0.17,
        "England HTG 2025 (DESNZ), n ≈ 139. Last bar is among those not already MCS (12%). HPA: ~half of 2023–24 UK trainees still have no install.",
        transform=ax.transAxes,
        fontsize=8,
        color=GRAY,
    )
    return save(fig, "11_conversion_funnel.png")


def chart_mcs_pathways():
    jobs = np.array([1, 3, 5, 10, 20])
    own = 1090 + 30 * jobs
    umbrella = 500 * jobs
    course = np.full(jobs.shape, 702, dtype=float)
    fig, ax = plt.subplots(figsize=(10.5, 6.0), layout="constrained")
    ax.plot(jobs, own, marker="o", color=NAVY, lw=2, label="Own MCS: £1,090 year-1 fees + £30 per certificate")
    ax.plot(jobs, umbrella, marker="s", color=TEAL, lw=2, label="HPIN umbrella: £250 design + £250 audit per job")
    ax.plot(jobs, course, marker="^", color=ORANGE, ls="--", lw=2, label="L3 classroom course only: £702 including VAT")
    ax.axvline(2.3, color=GRAY, ls=":", lw=1)
    ax.text(2.45, 3200, "Fee breakeven\n≈ 3 jobs", fontsize=8, color=GRAY)
    for x, y in zip(jobs, own):
        ax.annotate(f"£{y:,.0f}", (x, y), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=7, color=NAVY)
    ax.set_xlabel("Certified heat-pump jobs completed in year 1 (count)")
    ax.set_ylabel("Fees paid (British pounds, GBP)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"£{v:,.0f}"))
    ax.set_title("Own MCS vs umbrella — course fee is not the conversion cost")
    ax.legend(loc="upper left", fontsize=8.5)
    ax.set_xlim(0.4, 21)
    ax.set_ylim(0, 5200)
    ax.text(
        0.0,
        -0.14,
        "Own MCS £1,090 (Dwellow/MCS) excludes training time and insurance. Umbrella is charged every job. HTG £500 does not pay MCS fees. USD ≈ GBP × 1.30.",
        transform=ax.transAxes,
        fontsize=8,
        color=GRAY,
    )
    return save(fig, "12_mcs_vs_umbrella_cost.png")


def write_report(scored: pd.DataFrame, charts: list[Path]):
    best_value = scored.sort_values("value_score", ascending=False).head(5)
    best_quality = scored.sort_values("quality_index", ascending=False).head(5)
    cheapest_good = scored[(scored["quality_index"] >= 70) & (scored["has_reviews"])].sort_values(
        "cost_usd_typical"
    ).head(5)

    def md_table(df, cols):
        show = df[cols].copy()
        lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
        for _, r in show.iterrows():
            cells = []
            for c in cols:
                v = r[c]
                if isinstance(v, float) and not pd.isna(v):
                    cells.append(f"{v:,.2f}" if abs(v) < 1000 else f"{v:,.0f}")
                elif pd.isna(v):
                    cells.append("—")
                else:
                    cells.append(str(v)[:48])
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines)

    rel = lambda p: f"../output/{p.name}"
    body = f"""# Green skills education: cost, quality, and future demand

*Generated from `data/courses.csv`, `data/macro_indicators.csv`, `data/future_skills.csv`.*
*Pipeline: `scripts/analyze.py`. Currency USD unless noted. Date of this run: 2026-09-15.*

## What this answers

1. What do green-skills **courses actually cost per person**?
2. How does **cost compare with quality** pulled from reviews, credentials, and employer recognition?
3. Which **future courses / skills** are worth building inventory for?
4. How does **system-level training spend** (OECD, UK ESS, LinkedIn, WEF, BLS) sit against course prices?

## Headline numbers

| Signal | Figure | Source |
| --- | --- | --- |
| Green hiring vs green skills growth | **7.7% vs 4.3%** (still ~2×) | LinkedIn Green Skills Report 2025 |
| Hiring premium for green talent | **+46.6%** vs overall workforce | LinkedIn 2025 |
| Green hires now in non-green titles | **53%** | LinkedIn 2025 |
| OECD workers in green-driven occupations | **20%** | OECD Employment Outlook 2024 |
| Share of adult courses with green content | **2.1–14.1%** (AU, DE, SG, US) | OECD 2024 |
| Employer skills change by 2030 | **39%** | WEF Future of Jobs 2025 |
| Climate mitigation as business transformer | **47% of employers** | WEF 2025 |
| US solar PV installer median wage | **$53,140**; jobs **+37%** 2025–35 | BLS OOH |
| US wind turbine tech median wage | **$64,120**; jobs **+30%** 2025–35 | BLS OOH |
| UK employer spend per trainee | **£2,710** (lowest in the series) | DfE ESS 2024 |
| Croatia green/digital voucher | **up to €3,000 / person** | OECD |

Training supply is thin relative to job demand. Cheap MOOCs cover literacy; **license and standard-setter courses** are where employer-recognized quality concentrates.

## Cost vs quality

![Cost vs quality scatter]({rel(charts[0])})

How to read it:

- **Right and high** = expensive and strong (Harvard GHG, MIT PE, NABCEP PVIP).
- **Left and high** = bargains with real review volume (SUNY/UB Coursera solar, CU Boulder renewables).
- **Left and mid** = cheap marketplace courses: high review counts, weaker credentials.
- **Open diamonds** = no public star ratings; quality is inferred from the credential (GHG Protocol, GHGMI, AEE, SEI).

### Highest quality index

{md_table(best_quality, ["name", "provider", "cost_usd_typical", "rating", "n_reviews", "quality_index", "source_url"])}

### Best value (quality adjusted for log cost)

{md_table(best_value, ["name", "cost_usd_typical", "quality_index", "value_score", "quality_per_100usd"])}

### Cheapest reviewed courses that still clear quality ≥ 70

{md_table(cheapest_good, ["name", "cost_usd_typical", "rating", "n_reviews", "quality_index"])}

![Value for money]({rel(charts[1])})

![Cost ladder]({rel(charts[2])})

## Cost bands (rule of thumb)

| Band | Typical $ / person | What you get | Quality pattern from reviews |
| --- | ---: | --- | --- |
| Free / audit | 0 | Literacy, no (or weak) credential | High ratings, low employer weight |
| Marketplace sale | 13–25 | Tool tutorials (PVsyst, solar overview, EV intro) | Lots of reviews; wide quality spread |
| University MOOC certificate | 49–80 | Single course certificate | 4.6–4.8 stars, 100–2,600 reviews |
| Specialization / Plus year | 199–399 | Multi-course university stack | Strong ratings; credential mid-tier |
| Official standard e-learning | 30–600 | GHG Protocol Scope 2 ($30) to Scope 3 ($600) | Few public stars; high employer signal |
| Industry license bootcamp | 800–1,800 | NABCEP PVA/PVIP, AEE CEM | 4.7 stars + pass-rate data (HeatSpring 88%) |
| Professional diploma | 2,250–3,200 | GHGMI diploma, MIT PE | Thin public reviews; high brand |
| University microcertificate | 7,000+ | Harvard Extension GHG | Highest brand, highest price |

**Implication:** moving from a $20 Udemy overview to an ~$895 NABCEP PVA bootcamp is the largest quality jump per dollar for **hands-on solar jobs**. For **white-collar carbon accounting**, GHG Protocol $30–$600 and GHGMI $435 beat Harvard $7,160 on value unless the buyer specifically needs the Harvard brand.

## Future courses to stock

![Future demand]({rel(charts[4])})

Priority inventory (demand × training gap):

1. **Heat-pump / HVAC electrification** — UK needs ~100k heat-pump engineers; US HVAC vacancy ~110k heading toward ~225k.
2. **Energy management** — LinkedIn 2025 fastest-growing green skill (AI/data-center load).
3. **Environmental stewardship** — first time in WEF top-10 growing skills.
4. **Solar PV install + design** — BLS +37% jobs; solar design skills spiking on profiles.
5. **Wind turbine service** — BLS +30%, median $64,120.
6. **GHG / CSRD / ESRS reporting** — regulation-pulled white-collar skill; cheap intro (€100) and expensive professional paths coexist.
7. **EV / charging / powertrain** — WEF top-15 growing role.
8. **Grid flexibility + storage** — rising in LinkedIn 2025 skill relevance.
9. **Sustainable procurement** — fastest green skill in 2024 (+15% adoption).
10. **Green skills inside non-green jobs** — 53% of green hires. Courses for finance, ops, and procurement beat “green job” bootcamps alone.

## System-level spend vs course prices

![Macro cost]({rel(charts[5])})

![OECD supply]({rel(charts[6])})

![Hiring gap]({rel(charts[3])})

A public voucher of **€3,000** (Croatia) or UK average **£2,710 / trainee** covers:

- several university specializations, **or**
- one NABCEP-class bootcamp plus exam, **or**
- a GHGMI diploma, **or**
- **not** a Harvard microcertificate.

OECD: **20%** of workers are in green-driven occupations but only **2–14%** of catalogued adult courses carry green content. That is the core supply gap the course market is not filling.

![Cost vs wage]({rel(charts[7])})

## Quality method (so you can rerun it)

```
quality_index =
    0.35 * (stars / 5 * 100)          # 70 if no public stars (neutral)
  + 0.20 * (log10(reviews+1) / 4 * 100)  # 0 if no reviews
  + 0.25 * credential_score           # license 100, standard 88, university 80, platform 42
  + 0.20 * employer_signal            # 0-100 coded from hiring recognition
```

Stars without reviews are discounted. A 5.0 with 8 reviews cannot beat a 4.7 with 1,000 reviews plus a license.

## Heat pumps: the outcome gap (this refresh)

This run added **14 heat-pump / HVAC courses** (UK MCS pathway, US NATE/BPI/NYSERDA, HeatSpring, manufacturer academies). That was the thin catalog relative to demand (UK ~100k heat-pump engineers; US HVAC median **$61,010**, jobs **+11%** 2025–35, ~110k unfilled).

![HTG outcomes]({rel(charts[8])})

England’s Heat Training Grant is the rare case where **course reviews and job outcomes are both measured**:

| After HTG-subsidised training | Share |
| --- | ---: |
| Satisfied or very satisfied with the course | **94%** |
| Confident they can install | **80%** |
| Installed at least one heat pump | **33%** (was 27% in 2024) |
| Salary increased | **13%** (72% unchanged) |
| Obtained MCS if they were not already certified | **12%** |

Grant is **£500 / person**. Unsubsidised UK L3 ASHP classroom is about **£702 ($913)**; net after grant ~**$263**. NYSERDA-sponsored mini-split training is **$95** for NY residents vs **$1,795** out of state — subsidy, not pedagogy, is doing most of the cost work.

**Implication:** stocking more 4.7-star heat-pump MOOCs will not close the installer gap. The bottleneck after a short course is MCS / NATE / a first paid install, not another video.

![Cluster comparison]({rel(charts[9])})

## Conversion: first install and MCS (this follow-up)

MCS is a **business** accreditation, not a personal exam. BUS’s **£7,500** grant only pays if the job is MCS-certified. HTG’s **£500** pays for the course and stops there.

![Conversion funnel]({rel(charts[10])})

Per 100 England HTG graduates (DESNZ 2025):

| Stage | Per 100 |
| --- | ---: |
| Finished the course | 100 |
| Liked it | 94 |
| Feel able to install | 80 |
| Installed at least one unit | **33** |
| Already MCS when they trained | 16 |
| Got MCS afterwards if they were not | **12** |

Industry-wide the same leak shows up: HPA counted **7,800** course completions in 2023 and **7,000+** in 2024; **about half still have no installation**. LCL Awards / Nesta name the blockers: confidence, MCS paperwork, no first customer, admin (heat-loss, quoting, DNO), large brands taking the work.

**What actually converts** (evidence, not more catalogues):

1. **A supervised first install** — Nesta Start at Home: funded kit in the engineer’s own house. Scale-up: **2,000 registered, 250 live, 83 completed**. Around half of pilot home-installers then explored their own MCS. Daikin adds **£750 off** the first *customer* job.
2. **MCS umbrella for jobs 1–N** — HPIN (EDF): join **£0**; **£250 design + £250 audit** per job; they hold MCS and file BUS. Alto, Baxi, manufacturer networks do the same. This is how people install *before* they can sell MCS themselves.
3. **Own MCS only if volume is coming** — NICEIC 2026/27 one-technology year: application **£114** + cert **£846** + MCS licence **£66** (all inc VAT), plus consumer code ~**£385** year 1. MCS’s own bundle is **£1,090** year 1 + **£30 per certificate**, then **£890**/year.

![MCS vs umbrella cost]({rel(charts[11])})

Fee breakeven vs HPIN-style umbrella is about **3 certified jobs**. After that own MCS is cheaper on cash fees. The real cost of own MCS is still **QMS time, insurance, a first site the customer will accept, and 2–4 months**. That is why 94% like the course and 12% become newly MCS.

**Money the voucher does not cover**

| Stack | GBP | USD @ 1.30 |
| --- | ---: | ---: |
| L3 ASHP classroom (inc VAT) | 702 | 913 |
| HTG (England) | −500 | −650 |
| Net course after HTG | 202 | 263 |
| Own MCS year-1 fees (ex training) | 1,090 | 1,417 |
| Course + own MCS year 1 | ~1,792 | ~2,330 |
| Umbrella first job (HPIN) | 500 | 650 |
| Start at Home first install | 0 kit | 0 |

HTG is sized for the **course**. Conversion is sized like **£1,000–£1,800 plus a house to practise on**.

Workforce gap this leak sits in: Payaca / HPA-type estimates **<3,000** MCS heat-pump businesses and **2,000–4,500** full-time installers against **~31,000–41,000** needed this decade (HPA 30,590 by 2028; Nesta/CCC ~38,000 more by 2030). Octopus still cites **~100,000** heat-pump engineers for the UK build-out.

## NTU Singapore (this refresh)

Added **13 NTU PACE / Nanyang Business School** offerings. These are classroom CET with SkillsFuture funding, not MOOCs. **No public course-level star ratings** (NTU as a MySkillsFuture *provider* is 4.2 from 16,427 reviews — institution-level). Quality in the scatter is therefore credential-weighted.

Singapore demand this is aimed at (Green Skills Committee 2025):

| Signal | Figure |
| --- | --- |
| Sustainability reporting professionals | **2,000 (2023) → 4,000 (2030)** |
| Solar / storage / smart grid / power-import workforce | **~420 (2022) → 720 (2026)** (+70%) |
| Green-jobs demand growth 2024 | **+27%** (fastest in Asia, LinkedIn) |
| Carbon Markets Academy at NTU | **300** professionals by 2027 |
| Green workforce budget | **S$235m** |

**List vs what a funded Singaporean actually pays** (USD @ SGD 0.78; typical in the CSV is the **unsubsidised list**, same rule as UK HTG):

| NTU offering | List (inc GST) | SC 21–39 / PR | SC ≥40 (MCES) |
| --- | ---: | ---: | ---: |
| CM2 Carbon Accounting Fundamentals | S$3,270 (~$2,551) | S$1,770 (~$1,381) | S$1,170 (~$913) |
| SCTP GHG module | S$3,815 (~$2,976) | S$1,145 (~$893) | S$445 (~$347) |
| SCTP Sustainability Reporting + AI (full) | S$19,838 (~$15,474) | S$5,951 (~$4,642) | S$2,311 (~$1,803) |
| Sustainable Finance certificate | S$5,341 (~$4,166) | S$2,891 (~$2,255) | S$1,911 (~$1,491) |
| Carbon Markets exec (per module) | S$3,270 (~$2,551) | S$1,770 | S$1,170 |
| Renewable Energy Systems in Smart Grids | ~S$5,616 (~$4,380) | ~S$1,685 (70%) | SME ETSS ~S$654 |

Compare: **GHGMI 201 is $435** with an exam; **NTU CM2 is $2,551 list / ~$913 after 70%**. You are paying for IES Chartered Engineer (SG) pathway, classroom, and Singapore statute — not the same product as a $435 e-learning. After MCES, NTU carbon accounting lands near **GHG Protocol Scope 3 ($600)** and below **Harvard ($7,160)**.

The SCTP reporting certificate at **$15k list** is the ISSB/ACRA compliance stack. That is the local analogue of “regulation-pulled white-collar green skill,” not a solar-installer bootcamp.

This catalogue is **not** all 640+ sustainability CET courses SSG has counted. It is a working sample: NTU plus SkillsFuture Green Workplace (SFGW-SR) programmes, NUS, SMU, SIT, SEAS solar/SCEM, NTUC, Temasek Poly, Vertical Institute. Lookup URLs are in `source_url` on every row. Singapore subsidy bands and nett fees are in `data/sg_subsidy_rules.csv` and `data/sg_course_funding.csv`.

**What reviews can and cannot do**

- They measure learner satisfaction (clarity, production, instructor).
- They do **not** measure job placement. HeatSpring’s **88% NABCEP pass rate** and the HTG **33% install rate** are better outcome metrics than stars.
- Marketplace 4.4 with 11k reviews is a real popularity signal, not an employer signal.

## Data limits

- Udemy list prices are fictional for most buyers; **sale price** is used as typical.
- Coursera specialization cost assumes ~4 months at $49/mo, not Coursera Plus ($399/yr) unless the row is Plus.
- Several professional courses (GHG Protocol, GHGMI, AEE, SEI) publish **no star ratings** — quality is credential-weighted.
- One EV row is low-confidence (estimated reviews).
- UK course USD uses **GBP 1.30**; NTU Singapore uses **SGD 0.78**. SkillsFuture / HTG net cost is in notes; `cost_usd_typical` is unsubsidised list.
- Wages are US BLS occupation medians, not course-specific placement. HVAC wage is used as the heat-pump proxy (no separate BLS heat-pump installer SOC).
- LinkedIn “green skills” are self-reported profile skills, not assessed competence.
- HTG survey n is small (~139); treat percentages as directional.

## How to refresh

```
python scripts/analyze.py
```

Add rows to `data/courses.csv` (keep column names). Re-run. New PNGs land in `output/`, scored table in `output/courses_scored.csv`, this report in `reports/cost-quality-report.md`.

Full collector map: `PIPELINE.md`.
"""
    path = REPORTS / "cost-quality-report.md"
    path.write_text(body, encoding="utf-8")
    return path


def main():
    OUT.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    style()
    scored = score(load_courses())
    scored.to_csv(OUT / "courses_scored.csv", index=False)
    charts = [
        chart_scatter(scored),
        chart_value(scored),
        chart_cost_ladder(scored),
        chart_gap(),
        chart_future(),
        chart_macro_cost(),
        chart_oecd_supply(),
        chart_roi(scored),
        chart_htg_outcomes(),
        chart_cluster(scored),
        chart_conversion_funnel(),
        chart_mcs_pathways(),
    ]
    report = write_report(scored, charts)
    print("scored rows:", len(scored))
    print("report:", report)
    for c in charts:
        print("chart:", c)


if __name__ == "__main__":
    main()
