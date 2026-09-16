"""Standalone synthesis PDF for people who will not open GitHub."""
from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
REPORTS = ROOT / "reports"
PDF_PATH = REPORTS / "Green-Skills-Education-Briefing.pdf"

NAVY = colors.HexColor("#1D3557")
GREEN = colors.HexColor("#1B7A4E")
TEAL = colors.HexColor("#2A9D8F")
ORANGE = colors.HexColor("#E07A3D")
PALE = colors.HexColor("#F4F7F5")
LINE = colors.HexColor("#D1D5DB")
MUTED = colors.HexColor("#4B5563")
WHITE = colors.white

PAGE = landscape(A4)
W, H = PAGE
MARGIN = 14 * mm


def styles():
    base = getSampleStyleSheet()
    s = {
        "cover_kicker": ParagraphStyle(
            "cover_kicker", parent=base["Normal"], fontName="Helvetica",
            fontSize=10, textColor=GREEN, spaceAfter=6,
        ),
        "cover_title": ParagraphStyle(
            "cover_title", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=26, leading=30, textColor=NAVY, alignment=TA_LEFT, spaceAfter=8,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub", parent=base["Normal"], fontName="Helvetica",
            fontSize=12, leading=16, textColor=MUTED, spaceAfter=10,
        ),
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=16, leading=20, textColor=NAVY, spaceBefore=4, spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=12.5, leading=16, textColor=GREEN, spaceBefore=8, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontName="Helvetica",
            fontSize=9.5, leading=13, textColor=NAVY, alignment=TA_JUSTIFY, spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "bullet", parent=base["Normal"], fontName="Helvetica",
            fontSize=9.5, leading=13, textColor=NAVY, leftIndent=8, spaceAfter=3,
        ),
        "caption": ParagraphStyle(
            "caption", parent=base["Normal"], fontName="Helvetica-Oblique",
            fontSize=8, leading=11, textColor=MUTED, spaceBefore=3, spaceAfter=8,
        ),
        "th": ParagraphStyle(
            "th", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=8, leading=10, textColor=WHITE,
        ),
        "td": ParagraphStyle(
            "td", parent=base["Normal"], fontName="Helvetica",
            fontSize=7.8, leading=10, textColor=NAVY,
        ),
        "td_r": ParagraphStyle(
            "td_r", parent=base["Normal"], fontName="Helvetica",
            fontSize=7.8, leading=10, textColor=NAVY, alignment=TA_CENTER,
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["Normal"], fontName="Helvetica",
            fontSize=7.5, textColor=MUTED,
        ),
        "callout": ParagraphStyle(
            "callout", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=10, leading=14, textColor=NAVY,
        ),
    }
    return s


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN, 10 * mm, W - MARGIN, 10 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 6 * mm, "Green skills education briefing  |  16 September 2026  |  Standalone file — GitHub not required")
    canvas.drawRightString(W - MARGIN, 6 * mm, f"Page {doc.page}")
    canvas.restoreState()


def fit_image(path: Path, max_w: float, max_h: float) -> Image:
    im = PILImage.open(path)
    w, h = im.size
    scale = min(max_w / w, max_h / h)
    return Image(str(path), width=w * scale, height=h * scale, kind="proportional")


def table(headers, rows, col_widths):
    s = styles()
    data = [[Paragraph(escape(str(h)), s["th"]) for h in headers]]
    for row in rows:
        cells = []
        for i, v in enumerate(row):
            st = s["td_r"] if i > 0 else s["td"]
            cells.append(Paragraph(escape(str(v)), st))
        data.append(cells)
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("BACKGROUND", (0, 1), (-1, -1), PALE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.25, LINE),
            ]
        )
    )
    return t


def bullets(items):
    s = styles()
    return ListFlowable(
        [ListItem(Paragraph(escape(x), s["bullet"]), leftIndent=12, bulletColor=GREEN) for x in items],
        bulletType="bullet",
        start="•",
        leftIndent=12,
        bulletFontName="Helvetica",
        bulletFontSize=9,
        spaceBefore=2,
        spaceAfter=6,
    )


def chart_block(title, path, caption, max_h=118 * mm):
    s = styles()
    usable_w = W - 2 * MARGIN
    bits = []
    if title:
        bits.append(Paragraph(title, s["h2"]))
    bits.append(fit_image(path, usable_w, max_h))
    bits.append(Paragraph(caption, s["caption"]))
    return KeepTogether(bits)


def course_appendix(scored: pd.DataFrame):
    fund = {}
    fp = ROOT / "data" / "sg_course_funding.csv"
    if fp.exists():
        for _, r in pd.read_csv(fp).iterrows():
            fund[str(r["id"])] = r
    rows = []
    show = scored.sort_values(["skill_cluster", "cost_usd_typical"])
    s = styles()
    data = [[
        Paragraph("Course (click for lookup)", s["th"]),
        Paragraph("Provider", s["th"]),
        Paragraph("Cost USD list", s["th"]),
        Paragraph("SG nett SC 40+", s["th"]),
        Paragraph("Quality", s["th"]),
    ]]
    for _, r in show.iterrows():
        url = str(r.get("source_url") or "")
        name = escape(str(r["name"])[:52])
        if url.startswith("http"):
            name_p = Paragraph(f'<link href="{escape(url)}">{name}</link>', s["td"])
        else:
            name_p = Paragraph(name, s["td"])
        sg = fund.get(str(r["id"]))
        nett = "—"
        if sg is not None and not pd.isna(sg.get("sgd_net_sc_40")):
            try:
                nett = f"S${float(sg['sgd_net_sc_40']):,.0f}"
            except (TypeError, ValueError):
                nett = "—"
        data.append([
            name_p,
            Paragraph(escape(str(r["provider"])[:28]), s["td"]),
            Paragraph(f"${r['cost_usd_typical']:,.0f}", s["td_r"]),
            Paragraph(nett, s["td_r"]),
            Paragraph(f"{r['quality_index']:.0f}", s["td_r"]),
        ])
    t = Table(data, colWidths=[88 * mm, 48 * mm, 28 * mm, 28 * mm, 22 * mm], repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("GRID", (0, 0), (-1, -1), 0.25, LINE),
                ("TEXTCOLOR", (0, 1), (0, -1), TEAL),
            ]
        )
    )
    return t


def build():
    s = styles()
    scored = pd.read_csv(OUT / "courses_scored.csv")
    story = []

    # Cover
    story.append(Paragraph("STANDALONE BRIEFING  ·  71 COURSES  ·  US, UK, SINGAPORE", s["cover_kicker"]))
    story.append(Paragraph("Green skills education", s["cover_title"]))
    story.append(
        Paragraph(
            "What courses cost, how quality shows up in reviews and credentials, "
            "which skills are rising, and why a 4.7-star course still may not produce an installer.",
            s["cover_sub"],
        )
    )
    story.append(
        Paragraph(
            "This PDF is the full synthesis. You do not need GitHub, Python, or a spreadsheet. "
            "Snapshot dated 16 September 2026. Costs are typical unsubsidised list prices in US dollars "
            "unless a subsidy is named. FX: GBP 1.30, SGD 0.78, EUR 1.10, AUD 0.67.",
            s["body"],
        )
    )

    takeaways = [
        [
            "1. Hiring is ahead of training",
            "Green hiring grew 7.7% vs 4.3% for green skills (LinkedIn 2025). About 20% of OECD workers are in green-driven jobs; only 2–14% of adult courses have green content.",
        ],
        [
            "2. Stars are not jobs",
            "England Heat Training Grant: 94% liked the course, 33% installed a heat pump, 12% newly got MCS. The bottleneck is a first install and a business accreditation, not another video.",
        ],
        [
            "3. Pay for the credential that employers use",
            "Solar jobs: NABCEP-class bootcamp (~$895) beats a $20 overview. Carbon jobs: GHG Protocol $30–$600 or GHGMI $435 beat Harvard $7,160 on value. Singapore: SkillsFuture can cut NTU list prices by 50–90%.",
        ],
    ]
    cells = []
    for t, b in takeaways:
        cells.append(
            [
                Paragraph(f"<b>{escape(t)}</b><br/><font size='8.5'>{escape(b)}</font>", s["body"]),
            ]
        )
    box = Table(cells, colWidths=[W - 2 * MARGIN])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE),
                ("BOX", (0, 0), (-1, -1), 0.8, GREEN),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -2), 0.3, LINE),
            ]
        )
    )
    story.append(Spacer(1, 6))
    story.append(box)
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "Contents: headlines · cost vs quality · cost bands · future skills · labour-market spend · "
            "heat-pump conversion · NTU Singapore · method and limits · full course list.",
            s["caption"],
        )
    )

    # Headlines
    story.append(PageBreak())
    story.append(Paragraph("1. Headlines", s["h1"]))
    story.append(
        table(
            ["Signal", "Figure", "Source"],
            [
                ["Green hiring vs green skills growth", "7.7% vs 4.3% (still ~2x)", "LinkedIn Green Skills 2025"],
                ["Hiring premium for green talent", "+46.6% vs overall workforce", "LinkedIn 2025"],
                ["Green hires in non-green job titles", "53%", "LinkedIn 2025"],
                ["OECD workers in green-driven occupations", "20%", "OECD Employment Outlook 2024"],
                ["Adult courses with green content", "2.1–14.1% (AU, DE, SG, US)", "OECD 2024"],
                ["Employer skills changing by 2030", "39%", "WEF Future of Jobs 2025"],
                ["Climate mitigation transforms the firm", "47% of employers", "WEF 2025"],
                ["US solar PV installer median wage", "$53,140; jobs +37% 2025–35", "BLS OOH"],
                ["US wind turbine technician median wage", "$64,120; jobs +30% 2025–35", "BLS OOH"],
                ["US HVAC mechanic median wage", "$61,010; jobs +11% 2025–35", "BLS OOH"],
                ["UK employer spend per trainee", "GBP 2,710 (series low)", "DfE ESS 2024"],
                ["Singapore SRA professionals", "2,000 (2023) to 4,000 (2030)", "Green Skills Committee 2025"],
            ],
            [70 * mm, 95 * mm, 55 * mm],
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            "Training supply is thin relative to job demand. Cheap MOOCs cover literacy. "
            "License and standard-setter courses are where employer-recognized quality concentrates.",
            s["body"],
        )
    )
    story.append(
        chart_block(
            "Green hiring vs green skills",
            OUT / "04_hiring_vs_skills_gap.png",
            "Figure 1. LinkedIn Economic Graph. Unit: percent year-over-year.",
            58 * mm,
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("2. Cost per person vs quality", s["h1"]))
    story.append(
        Paragraph(
            "Quality index (0–100) = 35% star rating + 20% review-count confidence + 25% credential type "
            "+ 20% employer recognition. A 5.0 with 8 reviews cannot beat a 4.7 with 1,000 reviews plus a license. "
            "Each number on the chart is one course; names and dollar amounts are in the key on the right. "
            "Diamonds have no public star ratings — quality is inferred from the credential.",
            s["body"],
        )
    )
    story.append(fit_image(OUT / "01_cost_vs_quality.png", W - 2 * MARGIN, 145 * mm))
    story.append(
        Paragraph(
            "Figure 2. Horizontal axis: unsubsidised cost per person, US dollars, log scale. "
            "Vertical axis: quality index. Colour: credential type.",
            s["caption"],
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("Highest quality in this catalogue", s["h2"]))
    top_q = scored.sort_values("quality_index", ascending=False).head(6)
    story.append(
        table(
            ["Course", "Provider", "Cost USD", "Stars", "Reviews", "Quality"],
            [
                [
                    str(r["name"])[:42],
                    str(r["provider"])[:24],
                    f"${r['cost_usd_typical']:,.0f}",
                    "—" if pd.isna(r["rating"]) else f"{r['rating']:.2f}",
                    "—" if pd.isna(r["n_reviews"]) else f"{int(r['n_reviews']):,}",
                    f"{r['quality_index']:.1f}",
                ]
                for _, r in top_q.iterrows()
            ],
            [68 * mm, 42 * mm, 24 * mm, 20 * mm, 22 * mm, 22 * mm],
        )
    )
    story.append(Paragraph("Best value (quality divided by log cost)", s["h2"]))
    top_v = scored.sort_values("value_score", ascending=False).head(6)
    story.append(
        table(
            ["Course", "Cost USD", "Quality", "Value score"],
            [
                [str(r["name"])[:50], f"${r['cost_usd_typical']:,.0f}", f"{r['quality_index']:.1f}", f"{r['value_score']:.1f}"]
                for _, r in top_v.iterrows()
            ],
            [90 * mm, 30 * mm, 30 * mm, 30 * mm],
        )
    )
    story.append(Spacer(1, 4))
    story.append(fit_image(OUT / "02_value_for_money.png", W - 2 * MARGIN, 88 * mm))
    story.append(Paragraph("Figure 3. Top 12 value scores. Free literacy courses rank high because cost is zero.", s["caption"]))

    # Cost ladder — tall, so its own page at full height
    story.append(PageBreak())
    story.append(
        KeepTogether(
            [
                Paragraph("3. Full cost ladder by skill cluster", s["h1"]),
                Paragraph(
                    "Every course is here. Dollar labels are unsubsidised typical prices. Colour is credential type. "
                    "UK and Singapore subsidies can cut the net price; those nets are discussed later, not on this chart.",
                    s["body"],
                ),
                fit_image(OUT / "03_cost_ladder.png", W - 2 * MARGIN, 124 * mm),
                Paragraph(
                    "Figure 4. Log scale so a $20 course and a $15,000 certificate can share one axis.",
                    s["caption"],
                ),
            ]
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("4. What the price bands buy", s["h1"]))
    story.append(
        table(
            ["Band", "Typical USD / person", "What you get", "Review / quality pattern"],
            [
                ["Free / audit", "0", "Literacy, weak or no credential", "High stars, low employer weight"],
                ["Marketplace sale", "13–25", "Tool tutorials (PVsyst, solar, EV intro)", "Many reviews; wide quality spread"],
                ["University MOOC certificate", "49–80", "Single Coursera / edX certificate", "4.6–4.8 stars, 100–2,600 reviews"],
                ["Specialization / Plus year", "199–399", "Multi-course university stack", "Strong ratings; mid-tier credential"],
                ["Official standard e-learning", "30–600", "GHG Protocol Scope 2 ($30) to Scope 3 ($600)", "Few public stars; high employer signal"],
                ["Industry license bootcamp", "800–1,800", "NABCEP PVA/PVIP, AEE CEM, UK L3 ASHP", "4.7 stars + pass rates where published"],
                ["NTU Singapore classroom (list)", "1,700–15,500", "PACE / NBS CET, IES and ACRA pathways", "No course-level stars; SkillsFuture 50–90% off"],
                ["University microcertificate", "7,000+", "Harvard Extension GHG", "Highest brand, weakest value in this set"],
            ],
            [42 * mm, 38 * mm, 68 * mm, 70 * mm],
        )
    )
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "Implication. For a solar installer job, the jump that matters is MOOC to NABCEP (~$895), not Udemy to another Udemy. "
            "For carbon accounting, GHG Protocol $30–$600 or GHGMI $435 beat Harvard $7,160 on value unless the Harvard name is the product. "
            "A public voucher of about GBP 2,710 or EUR 3,000 covers one license bootcamp or a professional diploma — not a Harvard microcertificate, and not a scatter of $15 courses.",
            s["body"],
        )
    )
    story.append(fit_image(OUT / "10_cluster_cost_quality.png", W - 2 * MARGIN, 108 * mm))
    story.append(Paragraph("Figure 5. Skill clusters. Bubble size = number of courses in this catalogue.", s["caption"]))

    story.append(PageBreak())
    story.append(Paragraph("5. Future courses worth stocking", s["h1"]))
    story.append(
        Paragraph(
            "Each panel below uses a different unit on purpose. Do not compare the 37% BLS job-growth bar with the 47% WEF employer bar as if they were the same thing.",
            s["body"],
        )
    )
    story.append(fit_image(OUT / "05_future_demand_signals.png", W - 2 * MARGIN, 88 * mm))
    story.append(Paragraph("Figure 6. BLS = US employment change. WEF = share of employers. LinkedIn = share of green hires.", s["caption"]))
    story.append(Paragraph("Priority inventory (demand times training gap)", s["h2"]))
    story.append(
        bullets(
            [
                "Heat-pump / HVAC electrification — UK ~100,000 engineers needed; US ~110,000 HVAC vacancies, heading toward ~225,000.",
                "Energy management — LinkedIn 2025 fastest-growing green skill (AI and data-centre load).",
                "Environmental stewardship — first time in the WEF top-10 growing skills.",
                "Solar PV install and design — BLS +37%; solar-design skills spiking on profiles.",
                "Wind turbine service — BLS +30%, median $64,120.",
                "GHG / CSRD / ESRS / ISSB reporting — regulation-pulled; cheap intros and $15k professional stacks coexist.",
                "EV / charging — WEF top-15 growing role.",
                "Grid flexibility and storage; sustainable procurement; green skills inside non-green jobs (53% of green hires).",
            ]
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("6. Public spend vs wages", s["h1"]))
    story.append(fit_image(OUT / "06_cost_per_person_macro.png", W - 2 * MARGIN, 100 * mm))
    story.append(Paragraph("Figure 7. All bars in US dollars so they can be compared. Original currency in brackets.", s["caption"]))
    story.append(fit_image(OUT / "07_oecd_jobs_vs_training.png", W - 2 * MARGIN, 88 * mm))
    story.append(Paragraph("Figure 8. 20% of OECD workers are in green-driven occupations; 2–14% of catalogue courses are green.", s["caption"]))

    story.append(PageBreak())
    story.append(Paragraph("Training cost against the job it points at", s["h2"]))
    story.append(
        Paragraph(
            "Each row is an occupation. Points on a row are courses aimed at that job, spread sideways so they do not sit on top of each other. "
            "Numbers match the key on the right. Bubble size is quality; colour is projected job growth.",
            s["body"],
        )
    )
    story.append(fit_image(OUT / "08_cost_vs_wage.png", W - 2 * MARGIN, 138 * mm))
    story.append(Paragraph("Figure 9. Wages are US BLS occupation medians, not course placement rates.", s["caption"]))

    story.append(PageBreak())
    story.append(Paragraph("7. Heat pumps: reviews are not jobs", s["h1"]))
    story.append(
        Paragraph(
            "This is the highest-value finding in the pack. England’s Heat Training Grant (up to GBP 500, 9,100 vouchers) "
            "is the rare dataset that measures both course satisfaction and whether people then install.",
            s["body"],
        )
    )
    story.append(fit_image(OUT / "09_htg_satisfaction_vs_jobs.png", W - 2 * MARGIN, 68 * mm))
    story.append(Paragraph("Figure 10. DESNZ HTG 2025 survey, n about 139.", s["caption"]))
    story.append(fit_image(OUT / "11_conversion_funnel.png", W - 2 * MARGIN, 68 * mm))
    story.append(Paragraph("Figure 11. Per 100 graduates. Last bar is among those not already MCS-certified.", s["caption"]))

    story.append(PageBreak())
    story.append(Paragraph("What actually converts a trainee into an installer", s["h2"]))
    story.append(
        Paragraph(
            "MCS is a business accreditation, not a personal exam. The Boiler Upgrade Scheme’s GBP 7,500 grant only pays if the job is MCS-certified. "
            "The Heat Training Grant’s GBP 500 pays for the course and stops there. HPA counted 7,800 UK course completions in 2023 and 7,000+ in 2024; about half still have no installation.",
            s["body"],
        )
    )
    story.append(
        table(
            ["Path", "GBP", "USD at 1.30", "What it does"],
            [
                ["L3 ASHP classroom (inc VAT)", "702", "913", "The course HTG can discount"],
                ["After Heat Training Grant", "202", "263", "Net course in England"],
                ["Own MCS year-1 fees (ex training)", "1,090", "1,417", "Certification body + code + MCS"],
                ["Course + own MCS year 1", "~1,792", "~2,330", "What conversion actually costs"],
                ["HPIN umbrella first job", "500", "650", "They hold MCS; you install"],
                ["Nesta Start at Home first install", "0 kit", "0", "Funded kit in the engineer’s own house"],
            ],
            [58 * mm, 28 * mm, 32 * mm, 82 * mm],
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        bullets(
            [
                "Supervised first install — Nesta Start at Home: 2,000 registered, 250 live, 83 completed. Daikin adds GBP 750 off the first customer job.",
                "MCS umbrella for early jobs — HPIN (EDF): join GBP 0; GBP 250 design + GBP 250 audit per job. Same pattern at Alto, Baxi, manufacturer networks.",
                "Own MCS only if volume is coming — fee breakeven vs umbrella is about 3 certified jobs. After that own MCS is cheaper on cash. The real cost is QMS time, insurance, a first house, 2–4 months.",
            ]
        )
    )
    story.append(fit_image(OUT / "12_mcs_vs_umbrella_cost.png", W - 2 * MARGIN, 95 * mm))
    story.append(Paragraph("Figure 12. Vertical axis: British pounds. Horizontal axis: certified jobs in year 1.", s["caption"]))

    story.append(PageBreak())
    story.append(Paragraph("8. Singapore SkillsFuture — subsidies and courses", s["h1"]))
    story.append(
        Paragraph(
            "We did not add every SkillsFuture course. SSG has counted 640+ sustainability CET programmes and 13,000+ enrolments. "
            "This pack is a working sample: NTU, plus the official SkillsFuture Green Workplace (SFGW-SR) list, NUS, SMU, SIT, SEAS (solar/SCEM), NTUC, Temasek Polytechnic, Singapore Polytechnic, and Vertical Institute. "
            "Click any course name in the appendix to open the lookup page. Confirm live fees on MySkillsFuture before you pay.",
            s["body"],
        )
    )
    story.append(Paragraph("How the money actually stacks (typical SSG CET)", s["h2"]))
    story.append(
        table(
            ["Who", "Scheme", "What it usually does"],
            [
                ["SC 21–39 and PR 21+", "Baseline SSG funding", "50% or 70% of the fee (course tier). GST often on the full fee."],
                ["SC aged 40+", "Mid-Career Enhanced Subsidy (MCES)", "70% or 90% of the fee. You pay only the nett."],
                ["SME-sponsored SC/PR", "ETSS", "70% or 90%. Employer claims."],
                ["SCTP + unemployed / ComCare / WIS / PwD", "Additional Funding Support", "Up to 95% of SCTP fees."],
                ["SC aged 25+", "SkillsFuture Credit (base)", "About S$500 to offset the nett AFTER SSG."],
                ["SC aged 40+", "SkillsFuture Credit (Mid-Career)", "Extra S$4,000 on selected long-form / SCTP / IHL stackables."],
                ["SC aged 40+ on long programmes", "Mid-Career Training Allowance", "Income support (not a fee discount). Part-time S$300/mo."],
                ["Foreigner", "No SSG fee funding", "Pay list. Credit is for citizens."],
            ],
            [48 * mm, 58 * mm, 112 * mm],
        )
    )
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            'Hub pages: <link href="https://www.myskillsfuture.gov.sg/content/portal/en/career-resources/career-resources/education-career-personal-development/SFGW.html">SkillsFuture Green Workplace</link> · '
            '<link href="https://www.greenplan.gov.sg/courses/">Singapore Green Plan courses</link> · '
            '<link href="https://courses.myskillsfuture.gov.sg">MySkillsFuture course search</link>. '
            "Attendance is usually 75% plus a pass, or the subsidy can be clawed back.",
            s["body"],
        )
    )
    story.append(Paragraph("NTU list vs funded Singaporean (USD at SGD 0.78)", s["h2"]))
    story.append(
        table(
            ["NTU offering", "List (inc GST)", "SC 21–39 / PR", "SC 40+ (MCES)"],
            [
                ["CM2 Carbon Accounting Fundamentals", "S$3,270 (~$2,551)", "S$1,770 (~$1,381)", "S$1,170 (~$913)"],
                ["SCTP GHG module", "S$3,815 (~$2,976)", "S$1,145 (~$893)", "S$445 (~$347)"],
                ["SCTP Sustainability Reporting + AI (135h)", "S$19,838 (~$15,474)", "S$5,951 (~$4,642)", "S$2,311 (~$1,803)"],
                ["Sustainable Finance certificate", "S$5,341 (~$4,166)", "S$2,891 (~$2,255)", "S$1,911 (~$1,491)"],
                ["Carbon Markets exec (per module)", "S$3,270 (~$2,551)", "S$1,770", "S$1,170"],
                ["Renewable Energy Systems in Smart Grids", "~S$5,616 (~$4,380)", "~S$1,685 (70%)", "SME ~S$654"],
                ["CEng (SG) Sustainability 4 cores", "S$11,990 (~$9,352)", "—", "electives still TBC"],
            ],
            [68 * mm, 48 * mm, 48 * mm, 48 * mm],
        )
    )
    story.append(Spacer(1, 8))
    story.append(
        table(
            ["Singapore demand signal", "Figure", "Source"],
            [
                ["Sustainability reporting professionals", "2,000 (2023) → 4,000 (2030)", "Green Skills Committee 2025"],
                ["Solar / storage / smart grid / power-import workforce", "+70% to ~720 by 2026", "Green Skills Committee 2025"],
                ["Green-jobs demand growth 2024", "+27% (fastest in Asia)", "LinkedIn"],
                ["Carbon Markets Academy at NTU", "300 professionals by 2027", "EDB / NTU"],
                ["Green workforce budget", "S$235 million", "SBR 2026"],
            ],
            [80 * mm, 70 * mm, 58 * mm],
        )
    )
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "GHGMI 201 is $435 with an exam. NTU CM2 is $2,551 list / about $913 after 70% funding. "
            "You are paying for classroom time, the IES Chartered Engineer (SG) pathway, and Singapore statute — not the same product as a $435 e-learn. "
            "After MCES, NTU carbon accounting sits near GHG Protocol Scope 3 ($600) and well below Harvard ($7,160). "
            "The SCTP reporting certificate at $15k list is the ISSB / ACRA compliance stack, not a solar-installer bootcamp.",
            s["body"],
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("9. How quality was scored, and the limits", s["h1"]))
    story.append(
        Paragraph(
            "quality_index = 0.35 x (stars / 5 x 100)  +  0.20 x (log10(reviews+1) / 4 x 100)  +  0.25 x credential  +  0.20 x employer signal. "
            "Missing stars are scored as a neutral 70, and review confidence is then zero, so unreviewed professional courses are not fake-4.8’d and not crushed to zero.",
            s["body"],
        )
    )
    story.append(Paragraph("What reviews can and cannot do", s["h2"]))
    story.append(
        bullets(
            [
                "They measure learner satisfaction (clarity, production, instructor).",
                "They do not measure job placement. HeatSpring’s 88% NABCEP pass rate and the HTG 33% install rate are better outcome metrics.",
                "A marketplace 4.4 with 11,000 reviews is a popularity signal, not an employer signal.",
            ]
        )
    )
    story.append(Paragraph("Limits of this snapshot", s["h2"]))
    story.append(
        bullets(
            [
                "Udemy list prices are fictional for most buyers; sale price is used as typical.",
                "Coursera specializations assume about 4 months at $49/month unless the row is Coursera Plus ($399/year).",
                "GHG Protocol, GHGMI, AEE, SEI, NATE programmes, and NTU courses often publish no course-level stars.",
                "One EV row is low-confidence (estimated reviews).",
                "Wages are US occupation medians, not graduate placement. HVAC wage is the heat-pump proxy (no separate BLS heat-pump installer code).",
                "LinkedIn green skills are self-reported profile skills.",
                "HTG survey n is about 139 — directional, not a census.",
                "This is not legal, careers, or investment advice. Confirm live prices and funding rules before buying a course.",
            ]
        )
    )

    story.append(PageBreak())
    story.append(Paragraph("10. Full course list (click the name to open the source)", s["h1"]))
    story.append(
        Paragraph(
            "Sorted by cluster then cost. Quality is the 0–100 index. "
            "SG nett SC 40+ is the SkillsFuture MCES-style payable in Singapore dollars where we have it; otherwise a dash. "
            "Blue course names are links. US/UK rows have no Singapore nett.",
            s["body"],
        )
    )
    story.append(course_appendix(scored))
    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "Primary sources include OECD Training Supply for the Green and AI Transitions (2024), OECD Employment Outlook 2024, "
            "WEF Future of Jobs 2025, LinkedIn Green Skills Reports 2024–2025, BLS Occupational Outlook Handbook (May 2025 wages), "
            "UK DfE Employer Skills Survey 2024, DESNZ Heat Training Grant 2025 mid-scheme review, Nesta Start at Home, "
            "MCS / NICEIC fee tables, Singapore Green Skills Committee Report 2025, and live NTU PACE / NBS fee pages. "
            "Course ratings from Coursera, Udemy, HeatSpring, and MySkillsFuture as dated in the underlying tables.",
            s["caption"],
        )
    )
    story.append(
        Paragraph(
            "If someone later needs the spreadsheets or to refresh the numbers, the same briefing lives with the data files. "
            "This PDF is meant to be forwarded on its own.",
            s["body"],
        )
    )

    REPORTS.mkdir(exist_ok=True)
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=PAGE,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=12 * mm,
        bottomMargin=14 * mm,
        title="Green skills education briefing",
        author="Green skills education pipeline",
        subject="Cost, quality, future courses, and heat-pump conversion — standalone synthesis",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print("wrote", PDF_PATH)


if __name__ == "__main__":
    build()
