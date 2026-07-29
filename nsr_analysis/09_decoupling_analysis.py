"""
분석B — 해빙 감소와 NSR 통항량의 탈동조화 검증
AURORA 프로젝트

핵심 질문: "해빙이 줄어서 배가 늘었다"는 단순 인과가 데이터로 지지되는가?

방법:
- NSR 완주 transit 항차수(CHNL) vs 9월 해빙면적(NSIDC) vs 국제유가(EIA Brent)
- Spearman 순위상관 사용 (표본이 작고 선형성 가정이 어려움)
- 해빙은 단조 감소, 통항량은 비단조 → 상관계수만으로 인과를 말할 수 없음을 보임

⚠️ 심각한 한계 (보고서에 반드시 명시):
- 통항 실적은 9개 연도만 확보 (2014, 2017, 2019~2022 누락)
- n=9로는 어떤 상관계수도 통계적 검정력이 매우 낮다
- 따라서 이 분석의 결론은 "해빙이 원인이 아니다"가 아니라
  "해빙 단독으로는 통항량 변동을 설명할 수 없다"에 그쳐야 한다
"""
import os

import numpy as np
import pandas as pd
from scipy import stats

BASE = os.path.dirname(__file__)
OUT_DIR = os.path.join(BASE, "results")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    transit = pd.read_csv(os.path.join(BASE, "nsr_transit_data.csv")).dropna(subset=["transits"])
    transit = transit[["year", "transits"]].astype({"year": int, "transits": float})

    ice = pd.read_csv(os.path.join(BASE, "nsidc_daily_extent.csv"), parse_dates=["date"])
    ice["year"] = ice["date"].dt.year
    # 9월 해빙면적: 해역별로 9월 일평균을 낸 뒤 4개 해역을 합산 (연중 최소빙 시점)
    sep_by_sea = (ice[ice["date"].dt.month == 9]
                  .groupby(["year", "sea"])["extent_km2"].mean())
    sep = sep_by_sea.groupby("year").sum()
    sep.name = "sep_ice_km2"

    oil = pd.read_csv(os.path.join(BASE, "eia_data", "eia_brent.csv"), parse_dates=["date"])
    oil["year"] = oil["date"].dt.year
    oil_y = oil.groupby("year")["price_usd_bbl"].mean()
    oil_y.name = "brent_usd"

    df = transit.merge(sep, on="year").merge(oil_y, on="year").sort_values("year")

    print("=" * 78)
    print("분석B — 해빙 감소와 NSR 통항량의 관계")
    print("=" * 78)
    print(f"\n표본: {len(df)}개 연도 (누락 2014, 2017, 2019~2022)\n")
    print(df.to_string(index=False, float_format=lambda x: f"{x:,.1f}"))

    print("\n\n[Spearman 순위상관]")
    pairs = [
        ("통항량 ~ 9월해빙", "transits", "sep_ice_km2"),
        ("통항량 ~ 유가", "transits", "brent_usd"),
        ("9월해빙 ~ 연도", "sep_ice_km2", "year"),
        ("통항량 ~ 연도", "transits", "year"),
    ]
    rows = []
    for label, a, b in pairs:
        rho, p = stats.spearmanr(df[a], df[b])
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."
        print(f"  {label:<20} rho={rho:>6.3f}  p={p:>7.4f}  {sig}")
        rows.append({"pair": label, "spearman_rho": rho, "p_value": p})

    # 비단조성의 직접 증거: 해빙은 계속 줄었는데 통항량은 올랐다 내렸다 반복
    print("\n\n[비단조성 직접 증거]")
    d = df.sort_values("year").reset_index(drop=True)
    d["통항_전년대비"] = d["transits"].diff()
    d["해빙_전년대비"] = d["sep_ice_km2"].diff()
    print(d[["year", "transits", "통항_전년대비", "sep_ice_km2", "해빙_전년대비", "brent_usd"]]
          .to_string(index=False, float_format=lambda x: f"{x:,.1f}"))

    n_down = int((d["통항_전년대비"] < 0).sum())
    print(f"\n  해빙이 장기 감소 추세인 기간 중 통항량이 오히려 감소한 구간: {n_down}회")

    # 2013 정점 → 2015 붕괴 구간이 핵심 반증사례
    if {2013, 2015}.issubset(set(df["year"])):
        t13 = df.loc[df.year == 2013, "transits"].iloc[0]
        t15 = df.loc[df.year == 2015, "transits"].iloc[0]
        i13 = df.loc[df.year == 2013, "sep_ice_km2"].iloc[0]
        i15 = df.loc[df.year == 2015, "sep_ice_km2"].iloc[0]
        o13 = df.loc[df.year == 2013, "brent_usd"].iloc[0]
        o15 = df.loc[df.year == 2015, "brent_usd"].iloc[0]
        print(f"\n  ★ 핵심 반증사례 2013→2015")
        print(f"     통항량 {t13:.0f} → {t15:.0f}항차 ({(t15/t13-1)*100:+.0f}%)")
        print(f"     9월해빙 {i13:,.0f} → {i15:,.0f} km² ({(i15/i13-1)*100:+.0f}%)")
        print(f"     Brent유가 ${o13:.0f} → ${o15:.0f} ({(o15/o13-1)*100:+.0f}%)")
        print(f"     → 해빙 조건은 거의 그대로인데 통항량은 4분의 1로 붕괴.")
        print(f"       같은 기간 유가는 반토막. 해빙만으로 설명 불가.")

    pd.DataFrame(rows).to_csv(os.path.join(OUT_DIR, "B_decoupling.csv"), index=False)
    df.to_csv(os.path.join(OUT_DIR, "B_merged_series.csv"), index=False)
    print(f"\n저장: {OUT_DIR}/B_decoupling.csv")

    print("\n" + "=" * 78)
    print("해석 한계: n=9. 어떤 상관계수도 검정력이 낮다.")
    print("주장 가능: '해빙 단독으로 통항량 변동을 설명할 수 없다'")
    print("주장 불가: '유가가 통항량의 원인이다'")
    print("=" * 78)


if __name__ == "__main__":
    main()
