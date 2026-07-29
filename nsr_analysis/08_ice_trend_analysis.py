"""
분석A — NSR 4개 해역 항행가능일수 장기추세 (NSIDC 1979~2025)
AURORA 프로젝트

핵심 질문: NSR 각 구간의 항행 가능 기간이 실제로 얼마나 늘었는가?

방법:
- NSIDC 지역별 일별 해빙면적(extent, km²) 사용
- 각 해역의 '전체 면적'은 기록상 최대 extent로 근사 (겨울철 완전 결빙 시 포화값)
- 개빙수역 비율 = 1 - extent/해역면적
- 항행가능일 = 개빙수역 비율이 임계값을 넘는 날 (0.5 / 0.8 두 기준 병행)
- 연도별 항행가능일수에 선형회귀 → 기울기(일/년)와 p값

주의(§2 표현원칙):
- extent는 농도 15% 이상 격자의 면적 합. '얼음이 없다'가 아니라 '15% 미만'을 뜻함.
- 항행가능일수는 물리적 접근가능성 지표일 뿐, 실제 운항허가/경제성과 다르다.
"""
import os

import numpy as np
import pandas as pd
from scipy import stats

BASE = os.path.dirname(__file__)
SRC = os.path.join(BASE, "nsidc_daily_extent.csv")
OUT_DIR = os.path.join(BASE, "results")

THRESHOLDS = [0.5, 0.8]  # 개빙수역 비율 임계값
FULL_YEARS = (1979, 2025)  # 1978은 10월부터라 제외, 2026은 미완결


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    df = pd.read_csv(SRC, parse_dates=["date"])
    df["year"] = df["date"].dt.year
    df = df[(df["year"] >= FULL_YEARS[0]) & (df["year"] <= FULL_YEARS[1])]

    # 해역 면적 근사 = 기록상 최대 extent (겨울 포화값)
    sea_area = df.groupby("sea")["extent_km2"].max()
    df["open_frac"] = 1 - df["extent_km2"] / df["sea"].map(sea_area)

    rows = []
    for sea, g in df.groupby("sea"):
        # 연간 최소 extent (9월 최소빙 시점)
        annual_min = g.groupby("year")["extent_km2"].min()
        sl, ic, r, p, se = stats.linregress(annual_min.index, annual_min.values)
        rows.append({
            "sea": sea, "metric": "연간최소해빙면적(km2)",
            "slope_per_year": sl, "p_value": p, "r2": r ** 2,
            "start_val": annual_min.iloc[:5].mean(), "end_val": annual_min.iloc[-5:].mean(),
        })

        for th in THRESHOLDS:
            nav = g.assign(nav=g["open_frac"] > th).groupby("year")["nav"].sum()
            sl, ic, r, p, se = stats.linregress(nav.index, nav.values)
            rows.append({
                "sea": sea, "metric": f"항행가능일수(개빙>{th:.0%})",
                "slope_per_year": sl, "p_value": p, "r2": r ** 2,
                "start_val": nav.iloc[:5].mean(), "end_val": nav.iloc[-5:].mean(),
            })

    res = pd.DataFrame(rows)
    res["47년_변화량"] = res["slope_per_year"] * (FULL_YEARS[1] - FULL_YEARS[0])
    res.to_csv(os.path.join(OUT_DIR, "A_ice_trend.csv"), index=False)

    pd.set_option("display.width", 200)
    print("=" * 100)
    print(f"분석A — NSR 해역별 해빙 추세 ({FULL_YEARS[0]}~{FULL_YEARS[1]}, NSIDC G02135 v4.0)")
    print("=" * 100)
    print(f"\n해역 면적 근사값(최대 extent, km²):\n{sea_area.round(0).to_string()}\n")

    for metric in res["metric"].unique():
        sub = res[res["metric"] == metric].copy()
        print(f"\n[{metric}]")
        print(f"{'해역':<16}{'기울기/년':>12}{'47년변화':>12}{'초기5년평균':>14}{'최근5년평균':>14}{'p값':>10}{'R²':>8}")
        for _, r in sub.iterrows():
            sig = "***" if r.p_value < 0.001 else "**" if r.p_value < 0.01 else "*" if r.p_value < 0.05 else "n.s."
            print(f"{r.sea:<16}{r.slope_per_year:>12.2f}{r['47년_변화량']:>12.1f}"
                  f"{r.start_val:>14.1f}{r.end_val:>14.1f}{r.p_value:>10.2e}{r.r2:>8.2f}  {sig}")

    # 항행시즌(7~10월) 내 개빙 비율 — ERA5 분석과 접점
    print("\n\n[항행시즌 7~10월 평균 개빙수역 비율 — 10년 단위]")
    nav_season = df[df["date"].dt.month.isin([7, 8, 9, 10])].copy()
    nav_season["decade"] = (nav_season["year"] // 10) * 10
    piv = nav_season.pivot_table(index="decade", columns="sea", values="open_frac", aggfunc="mean")
    print((piv * 100).round(1).to_string())

    print(f"\n저장: {OUT_DIR}/A_ice_trend.csv")


if __name__ == "__main__":
    main()
