"""
합성지수는 해빙단독과 실제로 다른 결정을 내리는가
AURORA 프로젝트

배경: 심층감사 결과 현재 지수는 해빙이 평균수준의 51.0%, 일별변동의 81.7%를 차지한다.
      화물선 AIS 확보가 무산되어 합성의 '추가가치'를 행동자료로 검증할 수 없다.

그러나 검증할 수 없다는 것과 차이가 없다는 것은 다르다. 행동검증 없이도
'두 지수가 실제로 다른 결정을 내리는가'는 데이터로 답할 수 있다. 답에 따라
프로젝트의 정직한 포지셔닝이 달라진다.

  · 결정이 거의 같다  → 합성은 장식이다. 해빙지수로 단순화하고 그렇게 말해야 한다.
  · 결정이 자주 다르다 → 합성에 내용이 있다. 다만 어느 쪽이 옳은지는 미검증이라고 말해야 한다.

주의: 이 분석은 '합성이 더 낫다'를 보일 수 없다. 정답 라벨이 없기 때문이다.
      오직 '다른가'만 답한다.
"""
import os

import numpy as np
import pandas as pd
from scipy import stats

BASE = os.path.dirname(__file__)
OUT_DIR = os.path.join(BASE, "results")

REGION_KR = {"kara": "카라해", "laptev": "랍테프해",
             "east_siberian": "동시베리아해", "chukchi": "추크치해"}
WEIGHTS = {"ice": 0.35, "wind": 0.20, "wave": 0.25, "cold": 0.10, "fog": 0.10}
ICE_LIMITS_PC6 = (0.10, 0.80)
SHIP_VULN = {"PC6": 1.0, "PC7": 1.4}


def ramp(x, lo, hi):
    if hi > lo:
        return np.clip((x - lo) / (hi - lo), 0, 1)
    return np.clip((lo - x) / (lo - hi), 0, 1)


def hazards(df, ship="PC7"):
    lo, hi = np.array(ICE_LIMITS_PC6) / SHIP_VULN[ship]
    h = pd.DataFrame(index=df.index)
    h["ice"] = ramp(df["siconc_p90"], lo, hi)
    h["wind"] = ramp(df["wind_p90"], 5.0, 20.0)
    h["wave"] = ramp(df["swh_p90"].fillna(df["swh_p90"].median()), 1.0, 5.0)
    h["cold"] = ramp(df["t2m_min"], 0.0, -20.0)
    h["fog"] = ramp(df["dewpoint_spread_mean"], 3.0, 0.5)
    return h


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    df = pd.read_csv(os.path.join(OUT_DIR, "C_daily_risk.csv"), parse_dates=["date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month

    h = hazards(df)
    w = pd.Series(WEIGHTS) / sum(WEIGHTS.values())
    S = df["region"].map({"kara": 1.0, "laptev": 1.184575,
                          "east_siberian": 1.031621, "chukchi": 1.453956})

    df["R_composite"] = (h * w).sum(axis=1) * S
    df["R_ice_only"] = h["ice"] * S          # 해빙만, 동일한 손실증폭 적용
    df["R_ice_noS"] = h["ice"]               # 해빙만, 증폭 없음

    print("=" * 84)
    print("합성지수 vs 해빙단독 — 두 지수는 다른 결정을 내리는가")
    print("=" * 84)
    print(f"\n표본: ERA5 2015~2024 항행시즌, {len(df):,}일 (4구간)")

    # ---- 1. 값 자체의 유사도 ----
    print("\n\n[1] 두 지수는 얼마나 닮았는가")
    r_all, _ = stats.pearsonr(df["R_composite"], df["R_ice_only"])
    rho_all, _ = stats.spearmanr(df["R_composite"], df["R_ice_only"])
    print(f"  전체   Pearson r={r_all:.3f}  Spearman={rho_all:.3f}")
    for reg, g in df.groupby("region"):
        r, _ = stats.pearsonr(g["R_composite"], g["R_ice_only"])
        rho, _ = stats.spearmanr(g["R_composite"], g["R_ice_only"])
        print(f"  {REGION_KR[reg]:<12} r={r:.3f}  Spearman={rho:.3f}")

    # ---- 2. 구간×월 순위가 바뀌는가 ----
    print("\n\n[2] 구간×월 위험순위가 바뀌는가")
    pc = df.groupby(["region", "month"])["R_composite"].mean().rank(ascending=False)
    pi = df.groupby(["region", "month"])["R_ice_only"].mean().rank(ascending=False)
    tau, p_tau = stats.spearmanr(pc, pi)
    print(f"  16개 구간×월 순위 Spearman = {tau:.3f} (p={p_tau:.2e})")
    cmp = pd.DataFrame({"합성순위": pc, "해빙순위": pi})
    cmp["순위변동"] = (cmp["합성순위"] - cmp["해빙순위"]).astype(int)
    moved = cmp[cmp["순위변동"] != 0]
    print(f"  순위가 바뀐 칸: {len(moved)}/16")
    if len(moved):
        print(f"\n  {'구간':<14}{'월':>4}{'합성':>7}{'해빙':>7}{'변동':>7}")
        for (reg, m), r in moved.sort_values("순위변동", key=abs, ascending=False).head(6).iterrows():
            print(f"  {REGION_KR[reg]:<14}{m:>4}{int(r['합성순위']):>7}"
                  f"{int(r['해빙순위']):>7}{int(r['순위변동']):>+7}")

    # ---- 3. 핵심: 실제 출항 결정이 갈리는가 ----
    print("\n\n[3] 핵심 — 출항 결정이 갈리는 빈도")
    print("  '지금 출항 vs 3일 연기'를 두 지수로 각각 판단하고 일치율을 본다.")
    print("  (완전예지 조건. 예측오차 없이도 두 지수가 다른 답을 내는지 보는 것)\n")

    rows = []
    for hzn in [3, 7]:
        recs = []
        for (reg, yr), g in df.groupby(["region", "year"]):
            g = g.sort_values("date").reset_index(drop=True)
            for col in ["R_composite", "R_ice_only"]:
                g[f"{col}_fut"] = g[col].shift(-hzn)
            g = g.dropna(subset=["R_composite_fut", "R_ice_only_fut"])
            recs.append(pd.DataFrame({
                "region": reg, "year": yr, "month": g["date"].dt.month,
                "dec_comp": (g["R_composite_fut"] < g["R_composite"]).astype(int),
                "dec_ice": (g["R_ice_only_fut"] < g["R_ice_only"]).astype(int),
                "real_comp_now": g["R_composite"], "real_comp_fut": g["R_composite_fut"],
            }))
        t = pd.concat(recs, ignore_index=True)
        agree = (t["dec_comp"] == t["dec_ice"]).mean()
        n_diff = int((t["dec_comp"] != t["dec_ice"]).sum())
        print(f"  {hzn}일 연기 판단: 일치율 {agree:.1%}  (총 {len(t):,}건 중 {n_diff:,}건 불일치)")

        # 불일치 건이 계절적으로 어디에 몰리는가
        d = t[t["dec_comp"] != t["dec_ice"]]
        by_m = d.groupby("month").size() / t.groupby("month").size()
        print(f"    월별 불일치율: " + " / ".join(f"{m}월 {v:.1%}" for m, v in by_m.items()))
        rows.append({"horizon": hzn, "agreement": agree, "n_total": len(t), "n_disagree": n_diff})

    # ---- 4. 불일치가 결과에 영향을 주는가 ----
    print("\n\n[4] 결정이 갈릴 때 실제 위험 차이는 얼마인가")
    print("  합성지수 기준으로 평가. 해빙단독을 따랐다면 어떻게 됐을지 비교.\n")
    for hzn in [3, 7]:
        recs = []
        for (reg, yr), g in df.groupby(["region", "year"]):
            g = g.sort_values("date").reset_index(drop=True)
            cf = g["R_composite"].shift(-hzn)
            i_now, i_fut = g["R_ice_only"], g["R_ice_only"].shift(-hzn)
            m = cf.notna()
            recs.append(pd.DataFrame({
                "comp_rule": np.where(cf[m] < g["R_composite"][m], cf[m], g["R_composite"][m]),
                "ice_rule": np.where(i_fut[m] < i_now[m], cf[m], g["R_composite"][m]),
                "always_now": g["R_composite"][m],
            }))
        t = pd.concat(recs, ignore_index=True)
        base = t["always_now"].mean()
        print(f"  [{hzn}일] 합성규칙 {t['comp_rule'].mean():.4f} "
              f"({(base-t['comp_rule'].mean())/base*100:+.2f}%) / "
              f"해빙규칙 {t['ice_rule'].mean():.4f} "
              f"({(base-t['ice_rule'].mean())/base*100:+.2f}%)")
        gap = (t["ice_rule"].mean() - t["comp_rule"].mean()) / base * 100
        print(f"         두 규칙의 실현위험 격차: {gap:+.2f}%p (합성지수 기준 평가이므로 합성이 유리한 게 당연)")

    pd.DataFrame(rows).to_csv(os.path.join(OUT_DIR, "X1_index_divergence.csv"), index=False)

    print("\n\n[5] 판정")
    print(f"  두 지수의 값 상관: Spearman {rho_all:.3f}")
    print(f"  구간×월 순위 변동: {len(moved)}/16 칸")
    print("\n  정직한 서술:")
    if rho_all > 0.95 and len(moved) <= 2:
        print("    합성지수는 해빙단독과 사실상 같다. 해빙지수로 단순화하고 그렇게 발표해야 한다.")
    else:
        print("    두 지수는 상당 부분 함께 움직이지만 순위와 개별 결정에서 갈린다.")
        print("    합성에 내용은 있다. 다만 '어느 쪽이 옳은가'는 화물선 AIS 없이 판정 불가다.")
    print(f"\n저장: {OUT_DIR}/X1_index_divergence.csv")


if __name__ == "__main__":
    main()
