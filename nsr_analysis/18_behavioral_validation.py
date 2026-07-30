"""
검증4 — 행동검증: 위험지수가 실제 선박 행동을 설명하는가
AURORA 프로젝트

PAME ASTD(선단 AIS)는 승인 대기 중이나, KPDC ARAON 원자료에 1초 간격 GPS가 포함돼
있어 실제 쇄빙선 1척의 항적으로 대체 검증이 가능하다.

핵심 검정: 합성 위험지수가 '해빙 단독'보다 선박 감속을 더 잘 설명하는가?
  설명하지 못하면 여러 변수를 결합할 이유가 없다. 이 프로젝트의 존재 근거를 직접 시험한다.

통제해야 할 교란:
  1) 아라온은 연구선이다. 관측정점 정박은 위험 반응이 아니라 과학 일정이다.
     → 항해속력(>2 m/s) 구간만 사용
  2) 선속은 최대속력에서 절단된다(약 7.3 m/s). 조건이 좋으면 그냥 순항한다.
     → 절단을 인지하고 해석. 감속 방향만 검정
  3) 항차·연도별 운항계획 차이
     → 연도 고정효과 포함

한계(반드시 명시):
  아라온은 PC 고등급 쇄빙연구선이지 PC7 화물선이 아니다. 얼음에 들어가는 것이 임무이므로
  화물선이라면 회피할 조건에서도 진입한다. 따라서 이 검증은 '위험지수가 환경 악화에
  대한 선박의 감속 반응을 포착하는가'까지만 말할 수 있고, 화물선의 회피행동으로
  일반화할 수 없다.
"""
import os

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

BASE = os.path.dirname(__file__)
OUT_DIR = os.path.join(BASE, "results")

TRANSIT_MIN = 2.0   # m/s. 이보다 느리면 정점작업·접안으로 간주


def ramp(x, lo, hi):
    if hi > lo:
        return np.clip((x - lo) / (hi - lo), 0, 1)
    return np.clip((lo - x) / (lo - hi), 0, 1)


def build(df):
    """ARAON 지점의 ERA5 값으로 위험 성분 구성. 파고는 지점추출 대상이 아니라 제외."""
    h = pd.DataFrame(index=df.index)
    h["ice"] = ramp(df["siconc"], 0.10, 0.80)
    h["wind"] = ramp(df["wind_ms"], 5.0, 20.0)
    h["cold"] = ramp(df["t2m_C"], 0.0, -20.0)
    h["fog"] = ramp(df["t2m_C"] - df["d2m_C"], 3.0, 0.5)
    # 파고 성분이 빠지므로 나머지 가중치를 재정규화
    w = pd.Series({"ice": 0.35, "wind": 0.20, "cold": 0.10, "fog": 0.10})
    w = w / w.sum()
    h["composite"] = (h * w).sum(axis=1)
    return h


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    d = pd.read_csv(os.path.join(OUT_DIR, "V3_araon_era5_matched.csv"), parse_dates=["datetime"])
    d = d.dropna(subset=["sog_ms", "siconc", "wind_ms", "t2m_C", "d2m_C"])

    print("=" * 82)
    print("검증4 — 행동검증: 위험지수가 선박 감속을 설명하는가")
    print("=" * 82)
    print(f"\nARAON 6개 항차 매칭 {len(d):,}시간")

    hz = build(d)
    d = pd.concat([d.reset_index(drop=True), hz.reset_index(drop=True)], axis=1)

    st = d[d["sog_ms"] < 0.5]
    tr = d[d["sog_ms"] > TRANSIT_MIN].copy()
    print(f"  정박(<0.5 m/s) {len(st):,}시간 — 연구정점 작업, 위험반응 아님. 제외")
    print(f"  항해(>{TRANSIT_MIN} m/s) {len(tr):,}시간 — 분석 대상")
    print(f"  연도별 {tr.groupby('cruise_year').size().to_dict()}")

    # ---- 1. 단변량 관계 ----
    print("\n\n[1] 항해 중 선속과 환경위험 성분의 관계")
    print(f"  {'성분':<12}{'Spearman':>11}{'p':>12}")
    for c in ["ice", "wind", "cold", "fog", "composite"]:
        rho, p = stats.spearmanr(tr[c], tr["sog_ms"])
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."
        print(f"  {c:<12}{rho:>11.3f}{p:>12.2e}  {sig}")

    # ---- 2. 핵심 검정: 합성지수가 해빙 단독보다 나은가 ----
    print("\n\n[2] 핵심 검정 — 합성지수는 해빙 단독보다 설명력이 있는가")
    print("  연도 고정효과를 포함한 선형모형. 종속변수는 항해 중 선속(m/s).\n")

    yd = pd.get_dummies(tr["cruise_year"].astype(int), prefix="y", drop_first=True).astype(float)

    models = {
        "M0 연도만": [],
        "M1 해빙만": ["ice"],
        "M2 해빙+풍속": ["ice", "wind"],
        "M3 합성지수": ["composite"],
        "M4 성분 전부": ["ice", "wind", "cold", "fog"],
    }
    res_rows = []
    fitted = {}
    for name, cols in models.items():
        X = pd.concat([tr[cols].reset_index(drop=True), yd.reset_index(drop=True)], axis=1) if cols \
            else yd.reset_index(drop=True)
        X = sm.add_constant(X, has_constant="add")
        m = sm.OLS(tr["sog_ms"].values, X.values).fit()
        fitted[name] = (m, X.columns.tolist())
        res_rows.append({"모형": name, "R²": m.rsquared, "adj R²": m.rsquared_adj,
                         "AIC": m.aic, "n": int(m.nobs)})
    rt = pd.DataFrame(res_rows)
    rt["ΔR²(vs M0)"] = rt["R²"] - rt.loc[rt["모형"] == "M0 연도만", "R²"].iloc[0]
    print(rt.to_string(index=False, float_format=lambda x: f"{x:9.4f}"))

    m1 = fitted["M1 해빙만"][0]
    m3 = fitted["M3 합성지수"][0]
    m4 = fitted["M4 성분 전부"][0]
    print(f"\n  해빙만 대비 합성지수: ΔR² = {m3.rsquared - m1.rsquared:+.4f}")
    print(f"  해빙만 대비 성분전부: ΔR² = {m4.rsquared - m1.rsquared:+.4f}")

    # 성분 전부 모형에서 각 계수의 유의성
    print("\n  [M4 성분 전부] 계수 — 음수면 해당 위험이 클수록 감속")
    names = fitted["M4 성분 전부"][1]
    for i, nm in enumerate(names):
        if nm in ["ice", "wind", "cold", "fog"]:
            b, p = m4.params[i], m4.pvalues[i]
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."
            print(f"    {nm:<10} β={b:+7.3f}  p={p:.2e}  {sig}")

    # ---- 3. 비정상 감속 이진분석 ----
    print("\n\n[3] 비정상 감속 — 자기 항차 평소속력 대비")
    print("  선속은 최대속력에서 절단되므로 절대속도보다 상대편차가 낫다.\n")
    tr["ref"] = tr.groupby("cruise_year")["sog_ms"].transform(lambda s: s.quantile(0.75))
    tr["slow"] = (tr["sog_ms"] < 0.8 * tr["ref"]).astype(int)
    print(f"  비정상 감속(평소 75퍼센타일의 80% 미만) 발생률: {tr['slow'].mean():.1%}")

    print(f"\n  {'위험분위':<12}{'n':>7}{'감속발생률':>11}{'평균선속':>10}")
    tr["q"] = pd.qcut(tr["composite"], 4, labels=["Q1(저)", "Q2", "Q3", "Q4(고)"])
    for q, g in tr.groupby("q", observed=True):
        print(f"  {str(q):<12}{len(g):>7}{g['slow'].mean():>11.1%}{g['sog_ms'].mean():>10.2f}")

    q1 = tr[tr["q"] == "Q1(저)"]["slow"]
    q4 = tr[tr["q"] == "Q4(고)"]["slow"]
    chi2, pchi = stats.fisher_exact([[q4.sum(), len(q4) - q4.sum()],
                                     [q1.sum(), len(q1) - q1.sum()]])
    print(f"\n  Q4 vs Q1 오즈비 {chi2:.2f}, Fisher p={pchi:.3e}")

    # ---- 4. 저장 ----
    rt.to_csv(os.path.join(OUT_DIR, "V4_model_comparison.csv"), index=False)
    tr[["datetime", "cruise_year", "era5_region", "sog_ms", "slow",
        "ice", "wind", "cold", "fog", "composite"]].to_csv(
        os.path.join(OUT_DIR, "V4_transit_hours.csv"), index=False)

    # ---- 4. 교란 진단 ----
    print("\n\n[4] 교란 진단 — 왜 이 결과를 신뢰할 수 없는가")

    d["stn"] = (d["sog_ms"] < 0.5).astype(int)
    d["ib"] = pd.cut(d["siconc"], [-.01, .05, .3, .6, 1.01],
                     labels=["개빙", "산개빙", "중빙", "밀집빙"])
    stn = d.groupby("ib", observed=True)["stn"].mean()
    print("\n  (a) 얼음이 짙을수록 정박한다 — 감속이 아니라 '정지'가 반응이다")
    for k, v in stn.items():
        print(f"      {k:<6} 정박비율 {v:.1%}")
    print("      항해구간만 분석하면 정작 보려던 행동을 걸러내게 된다.")
    print("      그러나 연구선의 얼음 정박은 관측임무 자체이므로 위험반응과 분리 불가.")

    r_lat = np.corrcoef(tr["latitude"], tr["t2m_C"])[0, 1]
    print(f"\n  (b) 저온 계수는 위도 대리변수다 — 위도·기온 상관 r={r_lat:+.3f}")
    print("      '추우면 감속'이 아니라 '북쪽일수록 감속'이며 이는 임무 구조다.")

    print("\n  (c) 연도별 해빙-선속 부호가 일관되지 않는다")
    for y, g in tr.groupby("cruise_year"):
        if len(g) > 80:
            rho, p = stats.spearmanr(g["siconc"], g["sog_ms"])
            print(f"      {int(y)}: rho={rho:+.3f} (p={p:.3f}, n={len(g)})")

    # ---- 5. 판정 ----
    print("\n\n[5] 판정 — 검증 실패")
    gain_composite = m3.rsquared - m1.rsquared
    rho_c, p_c = stats.spearmanr(tr["composite"], tr["sog_ms"])
    print(f"  합성지수 vs 선속: Spearman {rho_c:+.3f} (p={p_c:.3f})")
    print(f"  합성지수의 해빙 대비 추가 설명력: ΔR² = {gain_composite:+.4f}")
    print(f"  고위험 분위(Q4) 감속 오즈비 {chi2:.2f} — 1 미만은 가설과 반대 방향")
    print("\n  결론: 아라온 항적으로는 위험지수를 검증할 수 없다.")
    print("  실패 원인은 표본 부족이 아니라 구조적 교란이다.")
    print("    · 연구선의 속도는 과학 일정이 결정한다")
    print("    · 쇄빙선은 화물선이 회피할 조건에 의도적으로 진입한다")
    print("    · 얼음 속 정박이 임무이자 잠재적 위험반응이라 둘을 분리할 수 없다")
    print("\n  → PAME ASTD 화물선 선단 AIS는 '있으면 좋은 것'이 아니라")
    print("     행동검증에 반드시 필요한 자료임이 확인되었다.")
    print(f"\n저장: {OUT_DIR}/V4_model_comparison.csv, V4_transit_hours.csv")


if __name__ == "__main__":
    main()
