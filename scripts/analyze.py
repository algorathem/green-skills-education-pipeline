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
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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
            "figure.dpi": 140,
        }
    )


def save(fig, name: str):
    path = OUT / name
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def chart_scatter(scored: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(11, 7))
    reviewed = scored[scored["has_reviews"]]
    norev = scored[~scored["has_reviews"]]
    sizes = (np.log10(reviewed["n_reviews"].fillna(1) + 1) * 80).clip(40, 400)
    colors = reviewed["credential_type"].map(
        {
            "industry_license": GREEN,
            "professional_standard": TEAL,
            "university": NAVY,
            "university_certificate": NAVY,
            "platform_cert": ORANGE,
        }
    ).fillna(GRAY)
    reviewed = reviewed.copy()
    norev = norev.copy()
    reviewed["plot_cost"] = reviewed["cost_usd_typical"].clip(lower=1)
    norev["plot_cost"] = norev["cost_usd_typical"].clip(lower=1)
    ax.scatter(
        reviewed["plot_cost"],
        reviewed["quality_index"],
        s=sizes,
        c=colors,
        alpha=0.85,
        edgecolors="white",
        linewidths=0.6,
        zorder=3,
    )
    ax.scatter(
        norev["plot_cost"],
        norev["quality_index"],
        s=90,
        facecolors="none",
        edgecolors=GRAY,
        linewidths=1.4,
        marker="D",
        label="No public star reviews",
        zorder=2,
    )
    label_ids = set(
        pd.concat(
            [
                scored.nlargest(8, "quality_index")["id"],
                scored.nsmallest(4, "cost_usd_typical")["id"],
                scored.nlargest(3, "cost_usd_typical")["id"],
            ]
        )
    )
    for _, r in scored.iterrows():
        if r["id"] not in label_ids:
            continue
        short = r["name"][:28] + ("…" if len(str(r["name"])) > 28 else "")
        ax.annotate(
            short,
            (max(float(r["cost_usd_typical"]), 1.0), r["quality_index"]),
            textcoords="offset points",
            xytext=(6, 4),
            fontsize=7.5,
            color=NAVY,
            alpha=0.95,
        )
    ax.set_xscale("log")
    ax.set_xlabel("Typical cost per person (USD, log scale)")
    ax.set_ylabel("Quality index (0–100)")
    ax.set_title("Cost per person vs quality of skill (reviews + credential + employer signal)")
    ax.set_ylim(30, 100)
    handles = [
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=GREEN, markersize=10, label="Industry license"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=NAVY, markersize=10, label="University"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=TEAL, markersize=10, label="Professional standard"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=ORANGE, markersize=10, label="Platform certificate"),
        plt.Line2D([0], [0], marker="D", color=GRAY, markerfacecolor="w", markersize=8, label="No public reviews"),
    ]
    ax.legend(handles=handles, loc="lower right", frameon=True)
    ax.text(
        0.01,
        -0.14,
        "Bubble size ∝ log(review count). Quality = 35% stars + 20% review confidence + 25% credential + 20% employer recognition.",
        transform=ax.transAxes,
        fontsize=8,
        color=GRAY,
    )
    return save(fig, "01_cost_vs_quality.png")


def chart_value(scored: pd.DataFrame):
    top = scored.sort_values("value_score", ascending=True).tail(12)
    fig, ax = plt.subplots(figsize=(10, 6.5))
    colors = [
        GREEN if v >= top["value_score"].median() else TEAL for v in top["value_score"]
    ]
    ax.barh(top["name"].str.slice(0, 42), top["value_score"], color=colors)
    ax.set_xlabel("Value score  =  quality / log10(cost + 10)")
    ax.set_title("Best quality for the money (top 12)")
    return save(fig, "02_value_for_money.png")


def chart_cost_ladder(scored: pd.DataFrame):
    order = scored.sort_values("cost_usd_typical")
    h = max(7.0, 0.28 * len(order) + 1.5)
    fig, ax = plt.subplots(figsize=(11, h))
    colors = order["credential_type"].map(
        {
            "industry_license": GREEN,
            "professional_standard": TEAL,
            "university": NAVY,
            "university_certificate": NAVY,
            "platform_cert": ORANGE,
        }
    ).fillna(GRAY)
    ax.barh(order["name"].str.slice(0, 40), order["cost_usd_typical"], color=colors)
    ax.set_xlabel("Typical cost per person (USD)")
    ax.set_title("Green-skills course cost ladder")
    ax.set_xscale("log")
    return save(fig, "03_cost_ladder.png")


def chart_gap():
    fig, ax = plt.subplots(figsize=(8.5, 5))
    years = ["2023–24\n(LinkedIn 2024 report)", "2024–25\n(LinkedIn 2025 report)"]
    demand = [11.6, 7.7]
    supply = [5.6, 4.3]
    x = np.arange(len(years))
    w = 0.35
    b1 = ax.bar(x - w / 2, demand, w, color=ORANGE, label="Green hiring / demand growth")
    b2 = ax.bar(x + w / 2, supply, w, color=GREEN, label="Green skills supply growth")
    ax.bar_label(b1, fmt="%.1f%%", padding=3)
    ax.bar_label(b2, fmt="%.1f%%", padding=3)
    ax.set_xticks(x, years)
    ax.set_ylabel("Year-over-year growth (%)")
    ax.set_title("Green hiring is still growing ~2× faster than green skills")
    ax.legend()
    ax.set_ylim(0, 15)
    return save(fig, "04_hiring_vs_skills_gap.png")


def chart_future():
    labels = [
        "Solar PV installers\n(BLS 2025–35)",
        "Wind turbine techs\n(BLS 2025–35)",
        "HVAC techs\n(BLS 2025–35)",
        "Climate mitigation\n(WEF employer %)",
        "Climate adaptation\n(WEF employer %)",
        "Skills changing\nby 2030 (WEF)",
        "Green hires in\nnon-green titles",
    ]
    values = [37, 30, 11, 47, 41, 39, 53]
    colors = [GREEN, TEAL, TEAL, ORANGE, GOLD, NAVY, GREEN]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = ax.bar(labels, values, color=colors)
    ax.bar_label(bars, fmt="%.0f%%", padding=3)
    ax.set_ylabel("Percent")
    ax.set_title("Future-course demand signals (jobs, skills, regulation)")
    ax.set_ylim(0, 65)
    return save(fig, "05_future_demand_signals.png")


def chart_macro_cost():
    fig, ax = plt.subplots(figsize=(9, 5.2))
    labels = [
        "UK spend / trainee\n(ESS 2024, GBP)",
        "UK construction\nspend / trainee",
        "Croatia green/digital\nvoucher (EUR)",
        "Australia apprentice\nincentive (AUD)",
        "US solar installer\nmedian wage (USD)",
        "US wind tech\nmedian wage (USD)",
    ]
    values = [2710, 5350, 3000, 10000, 53140, 64120]
    colors = [NAVY, NAVY, TEAL, TEAL, GREEN, GREEN]
    bars = ax.barh(labels, values, color=colors)
    ax.bar_label(bars, fmt="{:,.0f}", padding=4)
    ax.set_xlabel("Amount (local currency as labeled)")
    ax.set_title("Cost per person: public training spend vs occupation wages")
    return save(fig, "06_cost_per_person_macro.png")


def chart_oecd_supply():
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.barh(
        ["Green-driven occupations\n(share of OECD workforce)", "GHG-intensive occupations", "Green content in adult courses\n(4-country range, low)", "Green content in adult courses\n(4-country range, high)"],
        [20, 6, 2.1, 14.1],
        color=[GREEN, RED, GOLD, TEAL],
    )
    ax.set_xlabel("Percent")
    ax.set_title("OECD: green jobs vs green training supply")
    ax.set_xlim(0, 28)
    for i, v in enumerate([20, 6, 2.1, 14.1]):
        ax.text(v + 0.4, i, f"{v}%", va="center", fontsize=9)
    return save(fig, "07_oecd_jobs_vs_training.png")


def chart_roi(scored: pd.DataFrame):
    sub = scored.dropna(subset=["wage_to_cost_ratio", "target_wage_usd"]).copy()
    sub = sub[sub["cost_usd_typical"] >= 30]  # skip tiny Udemy sales that explode the ratio
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(
        sub["cost_usd_typical"],
        sub["target_wage_usd"],
        s=sub["quality_index"] * 3,
        c=sub["job_growth_pct"],
        cmap="YlGn",
        edgecolors=NAVY,
        linewidths=0.5,
        alpha=0.9,
    )
    for _, r in sub.iterrows():
        ax.annotate(
            str(r["name"])[:28],
            (r["cost_usd_typical"], r["target_wage_usd"]),
            fontsize=7,
            textcoords="offset points",
            xytext=(5, 3),
        )
    ax.set_xscale("log")
    ax.set_xlabel("Training cost per person (USD, log)")
    ax.set_ylabel("Target occupation median wage (USD)")
    ax.set_title("Training cost vs target wage (bubble = quality; color = job growth %)")
    cbar = fig.colorbar(ax.collections[0], ax=ax, shrink=0.8)
    cbar.set_label("Projected job growth %")
    return save(fig, "08_cost_vs_wage.png")


def chart_htg_outcomes():
    """Stars/satisfaction are not job outcomes. UK Heat Training Grant survey."""
    labels = [
        "Satisfied with\nthe course",
        "Confident they\ncan install",
        "Installed ≥1\nheat pump",
        "Salary went up\nafter training",
        "Got MCS cert\nif not already",
    ]
    values = [94, 80, 33, 13, 12]
    colors = [GREEN, TEAL, ORANGE, GOLD, RED]
    fig, ax = plt.subplots(figsize=(10, 5.4))
    bars = ax.bar(labels, values, color=colors)
    ax.bar_label(bars, fmt="%.0f%%", padding=3)
    ax.set_ylabel("Share of surveyed HTG graduates (%)")
    ax.set_title("Heat-pump training: reviews look great; work outcomes do not")
    ax.set_ylim(0, 110)
    ax.text(
        0.01,
        -0.18,
        "England Heat Training Grant 2025 survey (DESNZ, published Jun 2026). n≈139. 9,100 vouchers redeemed. Grant up to £500.",
        transform=ax.transAxes,
        fontsize=8,
        color=GRAY,
    )
    return save(fig, "09_htg_satisfaction_vs_jobs.png")


def chart_cluster(scored: pd.DataFrame):
    g = (
        scored.groupby("skill_cluster", as_index=False)
        .agg(
            n=("id", "count"),
            median_cost=("cost_usd_typical", "median"),
            mean_quality=("quality_index", "mean"),
        )
        .sort_values("mean_quality", ascending=True)
    )
    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    ax.scatter(
        g["median_cost"].clip(lower=1),
        g["mean_quality"],
        s=g["n"] * 40,
        c=GREEN,
        alpha=0.85,
        edgecolors=NAVY,
    )
    for _, r in g.iterrows():
        ax.annotate(
            f"{r['skill_cluster']} (n={int(r['n'])})",
            (max(float(r["median_cost"]), 1.0), r["mean_quality"]),
            textcoords="offset points",
            xytext=(7, 3),
            fontsize=8,
        )
    ax.set_xscale("log")
    ax.set_xlabel("Median typical cost per person (USD, log)")
    ax.set_ylabel("Mean quality index")
    ax.set_title("Skill clusters: cost vs quality (bubble = number of courses)")
    ax.set_ylim(50, 95)
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
    fig, ax = plt.subplots(figsize=(10, 5.6))
    bars = ax.bar(labels, values, color=colors)
    ax.bar_label(bars, fmt="%.0f", padding=3)
    ax.set_ylabel("Per 100 HTG graduates")
    ax.set_title("Conversion leak: training ≠ first install ≠ MCS")
    ax.set_ylim(0, 120)
    ax.annotate(
        "−61 never install",
        xy=(3, 33),
        xytext=(3.35, 55),
        fontsize=8,
        color=ORANGE,
        arrowprops=dict(arrowstyle="->", color=ORANGE),
    )
    ax.text(
        0.01,
        -0.18,
        "England HTG 2025 (DESNZ). MCS bar is among those not already certified (12%). Industry-wide HPA: ~half of 2023–24 trainees still have no install.",
        transform=ax.transAxes,
        fontsize=8,
        color=GRAY,
    )
    return save(fig, "11_conversion_funnel.png")


def chart_mcs_pathways():
    """Fee comparison: own MCS vs umbrella vs course-only. GBP then shown as USD."""
    jobs = np.array([1, 3, 5, 10, 20])
    own = 1090 + 30 * jobs  # official MCS year-1 bundle + per-cert
    umbrella = 500 * jobs  # HPIN 250 design + 250 audit
    course = np.full_like(jobs, 702, dtype=float)
    fig, ax = plt.subplots(figsize=(9.5, 5.6))
    ax.plot(jobs, own, marker="o", color=NAVY, label="Own MCS year-1 fees + £30/cert")
    ax.plot(jobs, umbrella, marker="s", color=TEAL, label="HPIN umbrella (£250 design + £250 audit / job)")
    ax.plot(jobs, course, marker="^", color=ORANGE, linestyle="--", label="L3 course only (£702 inc VAT)")
    ax.axvline(2.3, color=GRAY, linestyle=":", linewidth=1)
    ax.text(2.4, 2800, "fee breakeven\n~3 jobs", fontsize=8, color=GRAY)
    ax.set_xlabel("Certified heat-pump jobs in year 1")
    ax.set_ylabel("GBP fees (training or scheme)")
    ax.set_title("Own MCS vs umbrella: course cost is not the conversion cost")
    ax.legend(loc="upper left")
    ax.set_xlim(0.5, 21)
    ax.set_ylim(0, 4500)
    ax.text(
        0.01,
        -0.16,
        "Own MCS £1,090 year-1 (Dwellow/MCS) excludes training and time. Umbrella is per-job forever. HTG £500 does not pay MCS fees.",
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

{md_table(best_quality, ["name", "provider", "cost_usd_typical", "rating", "n_reviews", "quality_index", "credential_type"])}

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

**What reviews can and cannot do**

- They measure learner satisfaction (clarity, production, instructor).
- They do **not** measure job placement. HeatSpring’s **88% NABCEP pass rate** and the HTG **33% install rate** are better outcome metrics than stars.
- Marketplace 4.4 with 11k reviews is a real popularity signal, not an employer signal.

## Data limits

- Udemy list prices are fictional for most buyers; **sale price** is used as typical.
- Coursera specialization cost assumes ~4 months at $49/mo, not Coursera Plus ($399/yr) unless the row is Plus.
- Several professional courses (GHG Protocol, GHGMI, AEE, SEI) publish **no star ratings** — quality is credential-weighted.
- One EV row is low-confidence (estimated reviews).
- UK course USD uses **GBP 1.30**; Heat Training Grant net cost is in notes not in `cost_usd_typical` (typical = unsubsidised).
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
