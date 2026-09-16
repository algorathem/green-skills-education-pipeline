# Green skills education pipeline

End-to-end method to **find costs**, **future courses**, **green-skills education stats**, and **cost-per-person vs quality from reviews**.

This repo already has a first scored dataset and graphs. Use this file to collect more, refresh, or scale.

## Pipeline (8 stages)

```
1. Taxonomy     →  what counts as a green skill
2. Inventory    →  which courses/programmes exist
3. Cost         →  list price, typical paid price, subsidies
4. Quality      →  ratings, reviews, pass rates, completion
5. Labour       →  wages, openings, hiring premium
6. Normalize    →  one row per offering, USD, dated
7. Score        →  quality index + value + wage/cost
8. Visualize    →  graphs + report  (scripts/analyze.py)
```

Refresh cadence: **quarterly** for course prices/reviews; **annually** for OECD/WEF/BLS/LinkedIn flagship reports.

---

## Stage 1 — Taxonomy (what to search)

Do not invent a private skill list. Start from public classifications, then map courses onto them.

| Source | What it gives | URL |
| --- | --- | --- |
| ESCO / EU green skills | Official skill taxonomy | https://esco.ec.europa.eu |
| LinkedIn Green Skills taxonomy | Labour-market “green skill” tags used in hiring reports | LinkedIn Economic Graph reports |
| O*NET / BLS green jobs | US occupations (solar PV installer, wind tech, environmental engineer) | https://www.bls.gov/ooh/ · https://www.onetonline.org |
| WEF Future of Jobs skill clusters | Forward-looking employer demand | https://www.weforum.org/publications/the-future-of-jobs-report-2025/ |
| ILO / OECD green-driven vs GHG-intensive occupations | Policy-grade occupation split | OECD Employment Outlook; ILO skills reports |

**Practical clusters for course tagging** (used in `data/courses.csv`):

- `solar_pv` / `solar_design`
- `wind`
- `heat_pump_hvac`
- `ev_mobility`
- `energy_management`
- `energy_systems` / `storage_grid`
- `carbon_accounting`
- `esg_reporting`
- `sustainable_procurement`
- `environmental_stewardship`
- `mixed_green`

---

## Stage 2 — Course inventory (where to find programmes)

Search these catalogs in this order. Record provider, URL, hours, level, language, country.

| Layer | Catalogs | How to pull |
| --- | --- | --- |
| MOOC / university | Coursera, edX, FutureLearn, Class Central | Site search + Class Central topic pages (`climate change`, `solar`, `sustainability`). Coursera has a public course catalog API. |
| Marketplace | Udemy, Skillshare | Search “solar”, “PV syst”, “heat pump”, “GHG”, “ESG”. **Always store sale price and list price.** |
| Industry license | HeatSpring, SEI, Everblue, NABCEP provider list, GWO training providers, AEE | These are the courses employers actually shortlist for trades. |
| Standard-setters | GHG Protocol Learning Store, GHG Management Institute, GRI Academy, ISSB/IFRS Foundation | Best quality signal for carbon/ESG white-collar work. |
| Professional / university exec ed | MIT PE, Harvard Extension, Columbia, Imperial, TU Delft | High cost, high brand. |
| Public / voucher-eligible | OECD questionnaire programmes; national VET; NYSERDA directory (US); UK IfATE / Skills Bootcamps; EU ESCO-aligned VET | Needed for **cost per person** at system level, not just sticker price. |
| Singapore CET directory | MySkillsFuture open dataset (`d_b5802b76f409764c16dde4bf2feb19cd`) via `scripts/ingest_myskillsfuture.py` | Writes `data/myskillsfuture_green_dump.csv` (lookup inventory). **Do not** dump every TGS into `data/courses.csv` — that wrecks the quality scatter. |
| Employer academies | Octopus heat-pump academy, Trane TAP, utility line-schools | Often free to the learner (wage-paid). Cost is employer’s. |

**Future courses** = demand signal with thin catalog. Build a watchlist from:

1. WEF fastest-growing skills/roles (environmental stewardship, renewable engineers, EV specialists).
2. LinkedIn fastest-growing green skills (energy management 2025; sustainable procurement 2024).
3. Shortage anecdotes with numbers (UK heat pumps 100k; US HVAC 110k unfilled).
4. Regulation coming into force (CSRD/ESRS, ISSB, state climate disclosure).

If a skill is in (1)–(4) and you find **fewer than 5 high-quality paid courses**, it is a “future course” gap, not a saturated market.

---

## Stage 3 — Cost per person

Capture **four** numbers, not one:

| Field | Meaning |
| --- | --- |
| `cost_usd_list` | Sticker / rack rate |
| `cost_usd_typical` | What a private learner actually pays (Udemy sale, Coursera 4-month specialization, etc.) |
| `subsidy_usd` | Voucher, WIOA, employer, tax credit |
| `net_cost_usd` | typical − subsidy |

**System-level cost per person** (different unit — do not mix with course sticker prices in the same scatter without a label):

| Source | Metric | Latest figure used here |
| --- | --- | --- |
| UK Employer Skills Survey 2024 | Spend per trainee / per employee | £2,710 / £1,700 |
| OECD country programmes | Vouchers, apprentice grants | Croatia €3,000; Australia AUD 10k + 5k |
| US BLS | Not tuition — occupation wage (outcome) | Solar $53,140; wind $64,120 |

Convert FX on the date you collect. Keep original currency in `notes`.

**Coursera math:** individual course ~$49; specialization $39–$79/mo; Plus $59/mo or **$399/yr**. Do not assign $399 to a single course unless the learner is buying Plus.

---

## Stage 4 — Quality from reviews (and better than reviews)

Pull in this priority:

1. **Platform stars + count** — Coursera, Udemy, HeatSpring, Class Central.
2. **Outcome metrics** — exam pass rate (HeatSpring NABCEP 88%), completion rate if published, job-placement if audited.
3. **Credential rank** — license > standard-setter > university credit > university certificate > platform certificate > none.
4. **Qualitative review themes** — sample 20–50 reviews: “outdated”, “got me the job”, “exam prep worked”, “too theoretical”. Tag `job_outcome`, `exam_prep`, `outdated`, `production`.
5. **Forum mining** — Reddit r/solar, r/heatpumps, r/sustainability, NABCEP groups. This is the `startup-competitors` review-mining method applied to courses.

**Do not** treat a 5.0 with 8 reviews as better than a 4.7 with 1,000.

Scoring formula (implemented in `scripts/analyze.py`):

```
quality_index =
    0.35 * (stars/5*100)                    # 70 if no public stars (neutral, not 0)
  + 0.20 * (log10(n_reviews+1)/4 * 100)     # ~10k reviews = full confidence; 0 if none
  + 0.25 * credential_score
  + 0.20 * employer_signal                  # 0–100
```

Value score = `quality / log10(cost + 10)` so a $15 course cannot dominate a $895 license solely on price.

---

## Stage 5 — Labour-market outcomes

| Source | Use for |
| --- | --- |
| BLS OOH + OEWS | US wages, growth, openings (solar, wind, HVAC, environmental engineers) |
| O*NET skills importance | Which skills the occupation actually requires |
| LinkedIn Green Skills Report | Hiring premium, skill vs hire growth, industry mix |
| Lightcast / Indeed / Adzuna scrapes | Job-posting counts for a skill string |
| WEF Future of Jobs | 5-year employer expectations |
| IREC National Solar Jobs Census | Solar workforce, not just BLS installer SOC |
| ILO / OECD | Cross-country, policy, VET alignment |

Join to courses on `target_occupation` / `skill_cluster`. ROI proxy in the script is `median_wage / training_cost` — a screening ratio, **not** causal earnings gain.

---

## Stage 6 — Normalize

One CSV row per offering. Required columns are those in `data/courses.csv`. Rules:

- Date every row (`as_of`).
- Tag `cost_confidence` = high / medium / low.
- Empty reviews → leave rating blank (script will not invent 4.x stars).
- Keep source URL.
- Separate `macro_indicators.csv` and `future_skills.csv` from course rows.

---

## Stage 7–8 — Score and graph

```bash
python scripts/analyze.py
```

Writes:

- `output/courses_scored.csv`
- `output/01_cost_vs_quality.png` … `13_myskillsfuture_green_dump.png`
- `reports/cost-quality-report.md`
- `reports/Green-Skills-Education-Briefing.pdf` (via `scripts/build_pdf.py`)

---

## APIs and bulk collection (when you scale)

| Need | Tool |
| --- | --- |
| Coursera catalog | `https://api.coursera.org/api/courses.v1` (public, limited fields) |
| US wages | BLS OEWS / OOH APIs |
| Occupations | O*NET Web Services (free key) |
| EU skills | ESCO API |
| Course discovery index | Class Central (no official public API; HTML + existing reports) |
| Reviews | Platform pages; Class Central aggregates; Trustpilot for bootcamps |
| Job ads | Lightcast (paid), Adzuna API, or Google Jobs |
| Singapore course directory | data.gov.sg poll-download for dataset `d_b5802b76f409764c16dde4bf2feb19cd` (XLSX, ~25k TGS rows) |

There is **no** good public API for Udemy review text at scale. Budget time for manual/sample pulls, or licensed data.

---

## Agent skills (Grok / skills.sh)

Searched 2026-09-15. **No dedicated “green skills labour-market” skill** with real install volume. Closest:

| Skill | Installs | Fit |
| --- | --- | --- |
| `travisjneuman/.claude@career-path-planner` | 313 | Career paths, not course costing |
| `educates/educates-course-design-skill@educates-course-design` | 171 | Designing courses, not pricing them |
| `meleantonio/awesome-econ-ai-stuff@research-ideation` | 197 | Research framing |

This folder **is** the working pipeline. If you run this analysis often, wrap it as a local skill (`npx skills init green-skills-education`) pointing at `PIPELINE.md` + `scripts/analyze.py`.

---

## Decision rules (so the graphs change actions)

1. **Literacy / explore** → audit Coursera/edX or a $15–25 Udemy bestseller with 4.5+ and >1,000 reviews.
2. **Get hired as a solar installer / designer** → budget **$800–1,800** for NABCEP-aligned training; do not stop at MOOCs.
3. **Carbon accounting job** → GHG Protocol ($30–$600) or GHGMI ($435 / $2,250 diploma) before Harvard ($7,160) unless brand is the product.
4. **Workforce programme / voucher** → design around £2.7k–€3k per person: one license bootcamp or one professional diploma, not a scatter of random MOOCs.
5. **Build a future catalog** → heat pumps, energy management, CSRD/GHG, storage/grid, green-skills-for-non-green-jobs. That is where demand outruns supply.
