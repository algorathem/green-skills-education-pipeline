"""Pull the MySkillsFuture open directory and keep green/sustainability rows.

Does not dump every match into the scored catalogue (that would wreck the
quality scatter). Writes data/myskillsfuture_green_dump.csv for lookup.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "myskillsfuture_directory.xlsx"
DUMP = ROOT / "data" / "myskillsfuture_green_dump.csv"
DATASET_ID = "d_b5802b76f409764c16dde4bf2feb19cd"
SGD_USD = 0.78

TITLE_PAT = re.compile(
    r"sustainab|carbon|ghg|\besg\b|solar|photovoltaic|renewable|heat.?pump|"
    r"climate change|climate report|climate risk|net.?zero|decarbon|issb|"
    r"green.?mark|\bscem\b|energy audit|energy efficien|energy manager|"
    r"circular econom|green finance|sustainable finance|nature-based|"
    r"biodiversity|greenhouse|electric vehicle|\bev\b specialist|"
    r"green technolog|green workplace|green building|green skill|"
    r"low.?carbon|energy storage|smart grid|waste management|recycl|"
    r"green hydrogen|hydrogen econom",
    re.I,
)
ABOUT_STRONG = re.compile(
    r"SFGW|SR BOK|Sustainability Reporting Body|Singapore Certified Energy Manager|"
    r"Green Mark Accredited|SkillsFuture Green Workplace",
    re.I,
)
EXCLUDE = re.compile(
    r"social media|hr analytics|customer experience|passenger service|"
    r"child protection|self-leadership|international relations|applied hr|"
    r"lean six sigma|green belt|ethical and sustainable data",
    re.I,
)


def clean_text(s) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    t = str(s).replace("_x000D_", " ")
    t = t.replace("\u00e2\u20ac\u201c", "-")
    t = t.replace("\u00e2\u20ac\u201d", "-")
    t = t.replace("\u00e2\u20ac\u2122", "'")
    t = t.replace("\u00e2\u20ac\u0153", "'")
    t = t.replace("\u00c2\u00a0", " ")
    t = t.replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()


def download_xlsx() -> Path:
    RAW.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{DATASET_ID}/poll-download"
    j = requests.get(url, timeout=60).json()
    if j.get("code") != 0:
        raise RuntimeError(j.get("errorMsg") or j)
    r = requests.get(j["data"]["url"], timeout=180)
    r.raise_for_status()
    RAW.write_bytes(r.content)
    return RAW


def cluster(title: str) -> str:
    t = title.lower()
    if re.search(r"solar|photovoltaic", t):
        return "solar_pv"
    if re.search(r"heat.?pump|acmv|air conditioning", t):
        return "heat_pump_hvac"
    if re.search(r"carbon|ghg|greenhouse|decarbon", t):
        return "carbon_accounting"
    if re.search(r"esg|issb|report|disclosure|governance", t):
        return "esg_reporting"
    if re.search(r"energy audit|energy manager|scem|energy efficien", t):
        return "energy_management"
    if re.search(r"storage|smart grid|renewable|hydrogen|wind", t):
        return "energy_systems"
    if re.search(r"electric vehicle|\bev\b", t):
        return "ev_mobility"
    return "esg_reporting"


def lookup_url(tgs: str) -> str:
    return f"https://skillsfuture.gobusiness.gov.sg/course-directory/courses/{tgs}"


def existing_tgs() -> set[str]:
    found: set[str] = set()
    courses = ROOT / "data" / "courses.csv"
    if courses.exists():
        txt = courses.read_text(encoding="utf-8", errors="ignore")
        found.update(re.findall(r"TGS-\d+", txt))
    fund = ROOT / "data" / "sg_course_funding.csv"
    if fund.exists():
        f = pd.read_csv(fund)
        if "tgs_code" in f.columns:
            found.update(f["tgs_code"].dropna().astype(str).str.extract(r"(TGS-\d+)", expand=False).dropna())
    return found


def ingest(refresh: bool = False) -> pd.DataFrame:
    if refresh or not RAW.exists():
        download_xlsx()
    df = pd.read_excel(RAW)
    title = df["coursetitle"].map(clean_text)
    about = df["about_this_course"].map(clean_text)
    mask = title.str.contains(TITLE_PAT) | about.str.contains(ABOUT_STRONG)
    mask = mask & ~title.str.contains(EXCLUDE)
    g = df.loc[mask].copy()
    g["coursetitle"] = title.loc[mask]
    g["about_this_course"] = about.loc[mask]
    g["trainingprovideralias"] = g["trainingprovideralias"].map(clean_text)
    g["coursereferencenumber"] = g["coursereferencenumber"].astype(str)
    g = g.drop_duplicates(subset=["coursereferencenumber"])
    known = existing_tgs()
    g["already_in_scored_catalogue"] = g["coursereferencenumber"].isin(known)
    g["skill_cluster"] = g["coursetitle"].map(cluster)
    g["lookup_url"] = g["coursereferencenumber"].map(lookup_url)
    g["usd_list"] = pd.to_numeric(g["full_course_fee"], errors="coerce") * SGD_USD
    g["usd_after_ssg"] = pd.to_numeric(g["course_fee_after_subsidies"], errors="coerce") * SGD_USD
    keep = [
        "coursereferencenumber",
        "coursetitle",
        "trainingprovideralias",
        "skill_cluster",
        "full_course_fee",
        "course_fee_after_subsidies",
        "usd_list",
        "usd_after_ssg",
        "courseratings_stars",
        "courseratings_noofrespondents",
        "attendancecount",
        "number_of_hours",
        "lookup_url",
        "already_in_scored_catalogue",
    ]
    out = g[keep].sort_values(["skill_cluster", "full_course_fee", "coursetitle"])
    out.to_csv(DUMP, index=False)
    print(
        "dump rows",
        len(out),
        "already scored",
        int(out["already_in_scored_catalogue"].sum()),
        "new",
        int((~out["already_in_scored_catalogue"]).sum()),
        "->",
        DUMP,
    )
    return out


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Filter the MySkillsFuture open directory into a green-skills dump.")
    p.add_argument("--refresh", action="store_true", help="Re-download the XLSX from data.gov.sg instead of using the cached file.")
    args = p.parse_args()
    ingest(refresh=args.refresh)
