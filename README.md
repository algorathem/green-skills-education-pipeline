# Green skills education pipeline

Find **course costs**, **future / green-skills programmes**, **labour-market stats**, and **cost-per-person vs quality from reviews**.

**If you do not use GitHub:** open the standalone briefing PDF and email it as a file.

| Start here | File |
| --- | --- |
| **PDF for non-technical readers** | [reports/Green-Skills-Education-Briefing.pdf](reports/Green-Skills-Education-Briefing.pdf) |
| How the whole pipeline works | [PIPELINE.md](PIPELINE.md) |
| First-run analysis + graphs | [reports/cost-quality-report.md](reports/cost-quality-report.md) |
| Raw course costs & ratings | [data/courses.csv](data/courses.csv) |
| Macro stats (OECD, WEF, BLS, LinkedIn) | [data/macro_indicators.csv](data/macro_indicators.csv) |
| Future skills watchlist | [data/future_skills.csv](data/future_skills.csv) |
| Heat Training Grant outcomes | [data/outcomes_htg.csv](data/outcomes_htg.csv) |
| First-install / MCS conversion funnel | [data/conversion_funnel.csv](data/conversion_funnel.csv) |
| MCS vs umbrella cost stack | [data/mcs_cost_stack.csv](data/mcs_cost_stack.csv) |
| Scored table | [output/courses_scored.csv](output/courses_scored.csv) |
| Singapore subsidy rules | [data/sg_subsidy_rules.csv](data/sg_subsidy_rules.csv) |
| Singapore course nett fees + TGS codes | [data/sg_course_funding.csv](data/sg_course_funding.csv) |
| SkillsFuture green dump (lookup inventory, not scored) | [data/myskillsfuture_green_dump.csv](data/myskillsfuture_green_dump.csv) |
| Heat-pump outcome chart | [output/09_htg_satisfaction_vs_jobs.png](output/09_htg_satisfaction_vs_jobs.png) |
| Conversion funnel | [output/11_conversion_funnel.png](output/11_conversion_funnel.png) |
| SkillsFuture dump chart | [output/13_myskillsfuture_green_dump.png](output/13_myskillsfuture_green_dump.png) |

The scored catalogue is **91** curated courses. The dump is **975** green-titled TGS codes from the public MySkillsFuture directory. It is inventory with lookup URLs, not a quality ranking — those rows are not plotted on the cost-vs-quality scatter.

```bash
python scripts/ingest_myskillsfuture.py
python scripts/analyze.py
python scripts/build_pdf.py
```
