"""
저위험 항행창은 47년간 이동했는가
AURORA 프로젝트

지금까지의 '9월 중순 최적창'은 2015~2024년 10년 평균이다. 그러나 해빙이 장기 감소했다면
최적창 자체가 이동했을 수 있고, 그렇다면 10년 평균으로 만든 창은 이미 낡았을 수 있다.

NSIDC 1979~2025년 관측만 사용한다. ERA5도 위험지수도 쓰지 않으므로
모델 가정에 의존하지 않는 순수 관측 기반 분석이다(근거등급 A 후보).

측정 대상:
  1) 개빙기 시작일 — 개빙수역 비율이 임계값을 처음 넘는 날
  2) 개빙기 종료일 — 마지막으로 넘는 날
  3) 개빙기 길이
  4) 연중 최소빙일 — 항행 최적 시점의 대리지표

주의: extent는 농도 15% 이상 격자면적 합이다. '얼음 없음'이 아니라 '15% 미만'이다.
"""
import os

import numpy as np
import pandas as pd
from scipy import stats

BASE = os.path.dirname(__file__)
OUT_DIR = os.path.join(BASE, "results")

SEA_KR = {"Kara": "카라해", "Laptev": "랍테프해",
          "East-Siberian": "동시베리아해", "Chukchi": "추크치해"}
THRESH = 0.5     # 개빙수역 비율 임계값
YEARS = (1979, 2025)


def doy_to_md(doy, year=2021):
    return (pd.Timestamp(f"{year}-01-01") + pd.Timedelta(days=int(doy) - 1)).strftime("%m-%d")


def trend(x, y):
    """OLS 기울기와 Theil-Sen(이상치 강건) 병기."""
    if len(x) < 10 or np.std(y) == 0:
        return dict(slope=np.nan, p=np.nan, sen=np.nan, lo=np.nan, hi=np.nan)
    sl, ic, r, p, se = stats.linregress(x, y)
    sen, icept, lo, hi = stats.theilslopes(y, x, 0.95)
    return dict(slope=sl, p=p, sen=sen, lo=lo, hi=hi)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    d = pd.read_csv(os.path.join(BASE, "nsidc_daily_extent.csv"), parse_dates=["date"])
    d["year"] = d["date"].dt.year
    d["doy"] = d["date"].dt.dayofyear
    d = d[(d["year"] >= YEARS[0]) & (d["year"] <= YEARS[1])]

    area = d.groupby("sea")["extent_km2"].max()
    d["open"] = 1 - d["extent_km2"] / d["sea"].map(area)

    print("=" * 86)
    print(f"저위험 항행창의 장기 이동 — NSIDC {YEARS[0]}~{YEARS[1]}, 관측 단독")
    print("=" * 86)

    recs = []
    for (sea, yr), g in d.groupby(["sea", "year"]):
        g = g.sort_values("doy")
        op = g[g["open"] > THRESH]
        rec = {"sea": sea, "year": yr,
               "min_ice_doy": int(g.loc[g["extent_km2"].idxmin(), "doy"]),
               "n_open_days": len(op)}
        if len(op) >= 5:
            rec["open_start"] = int(op["doy"].iloc[0])
            rec["open_end"] = int(op["doy"].iloc[-1])
            rec["open_span"] = rec["open_end"] - rec["open_start"] + 1
        else:
            rec["open_start"] = rec["open_end"] = rec["open_span"] = np.nan
        recs.append(rec)
    w = pd.DataFrame(recs)
    w.to_csv(os.path.join(OUT_DIR, "X2_window_by_year.csv"), index=False)

    metrics = [("open_start", "개빙기 시작일"), ("open_end", "개빙기 종료일"),
               ("open_span", "개빙기 길이(일)"), ("min_ice_doy", "연중 최소빙일")]

    out = []
    for col, label in metrics:
        print(f"\n\n[{label}]")
        print(f"  {'해역':<14}{'기울기(일/년)':>14}{'47년변화':>11}{'p':>10}"
              f"{'Theil-Sen':>12}{'초기5년':>10}{'최근5년':>10}")
        for sea, g in w.groupby("sea"):
            g = g.dropna(subset=[col]).sort_values("year")
            if len(g) < 15:
                continue
            t = trend(g["year"].values, g[col].values.astype(float))
            e0 = g[col].iloc[:5].mean()
            e1 = g[col].iloc[-5:].mean()
            sig = "***" if t["p"] < 0.001 else "**" if t["p"] < 0.01 else "*" if t["p"] < 0.05 else "n.s."
            chg = t["slope"] * (YEARS[1] - YEARS[0])
            if col in ("open_start", "open_end", "min_ice_doy"):
                e0s, e1s = doy_to_md(e0), doy_to_md(e1)
            else:
                e0s, e1s = f"{e0:.0f}", f"{e1:.0f}"
            print(f"  {SEA_KR[sea]:<14}{t['slope']:>14.3f}{chg:>11.1f}{t['p']:>10.2e}"
                  f"{t['sen']:>12.3f}{e0s:>10}{e1s:>10}  {sig}")
            out.append({"sea": sea, "metric": label, "slope_per_year": t["slope"],
                        "p_value": t["p"], "theil_sen": t["sen"],
                        "sen_ci_low": t["lo"], "sen_ci_high": t["hi"],
                        "early5": e0, "recent5": e1})

    res = pd.DataFrame(out)
    res.to_csv(os.path.join(OUT_DIR, "X2_window_trends.csv"), index=False)

    # ---- 핵심: 최소빙일이 실제로 늦춰졌는가 ----
    print("\n\n[핵심] 연중 최소빙일의 이동 — '9월 중순 최적'은 여전히 유효한가")
    mi = res[res["metric"] == "연중 최소빙일"]
    print(f"\n  {'해역':<14}{'초기5년(79~83)':>16}{'최근5년(21~25)':>16}{'이동':>9}{'유의성':>9}")
    for _, r in mi.iterrows():
        shift = r["recent5"] - r["early5"]
        sig = "유의" if r["p_value"] < 0.05 else "불확실"
        print(f"  {SEA_KR[r['sea']]:<14}{doy_to_md(r['early5']):>16}"
              f"{doy_to_md(r['recent5']):>16}{shift:>+8.1f}일{sig:>9}")

    sig_n = int((mi["p_value"] < 0.05).sum())
    print(f"\n  4개 해역 중 {sig_n}개에서 최소빙일 이동이 통계적으로 유의")

    # 최근 10년만으로 본 최소빙일 — 현재 운용 기준
    print("\n\n[현재 기준] 최근 10년(2016~2025) 최소빙일 분포")
    r10 = w[w["year"] >= 2016]
    print(f"  {'해역':<14}{'중앙값':>10}{'10~90퍼센타일':>18}{'표준편차(일)':>13}")
    for sea, g in r10.groupby("sea"):
        med = g["min_ice_doy"].median()
        q1, q9 = g["min_ice_doy"].quantile([.1, .9])
        print(f"  {SEA_KR[sea]:<14}{doy_to_md(med):>10}"
              f"{doy_to_md(q1)+'~'+doy_to_md(q9):>18}{g['min_ice_doy'].std():>13.1f}")

    print("\n  → 표준편차가 크면 '평균 최적일' 하나로 계획할 수 없다는 뜻이다.")
    print(f"\n저장: {OUT_DIR}/X2_window_by_year.csv, X2_window_trends.csv")


if __name__ == "__main__":
    main()
