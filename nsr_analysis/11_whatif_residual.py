"""
분석D — 안전조치 what-if: 출항연기·쇄빙지원의 잔여위험 감소효과
AURORA 프로젝트

핵심 질문: "3일 연기하면 위험이 얼마나 줄어드는가?"에 실측으로 답한다.

방법:
- 2015~2024년 실제 ERA5 일별 위험지수를 사용 (가상 시나리오 아님)
- 출항일 D에 대해 D+k일의 위험과 비교 → 연기 효과의 '분포'를 산출
- 평균만 보고하면 오도된다. 연기가 오히려 위험을 키우는 확률도 함께 제시한다.

잔여위험 = 고유위험 × (1 - η_m)
  η_쇄빙지원: 쇄빙선 에스코트의 해빙위험 완화효과. 실측 검증 불가한 가정값이므로
             단일값이 아니라 범위로 제시하고 결론은 부호와 순서로만 말한다.
"""
import os

import numpy as np
import pandas as pd

BASE = os.path.dirname(__file__)
OUT_DIR = os.path.join(BASE, "results")

REGION_KR = {"kara": "카라해", "laptev": "랍테프해",
             "east_siberian": "동시베리아해", "chukchi": "추크치해"}

DELAYS = [1, 3, 5, 7, 14]
ETA_ESCORT = [0.2, 0.35, 0.5]  # 쇄빙지원 완화효과 가정범위


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    df = pd.read_csv(os.path.join(OUT_DIR, "C_daily_risk.csv"), parse_dates=["date"])
    df = df.sort_values(["region", "date"]).reset_index(drop=True)
    df["year"] = df["date"].dt.year

    print("=" * 92)
    print("분석D — 안전조치 what-if (ERA5 2015~2024 실측 기반)")
    print("=" * 92)

    # ---- 1. 출항연기 효과 ----
    print("\n[출항연기 k일의 위험 변화 — PC7 기준]")
    print("  연기가 항상 이득은 아니다. '위험이 오히려 증가할 확률'을 함께 본다.\n")
    print(f"{'구간':<14}{'연기':>5}{'평균변화%':>11}{'중앙값%':>10}"
          f"{'악화확률':>10}{'10%개선초과':>12}{'10%악화초과':>12}")

    rows = []
    for region, g in df.groupby("region"):
        g = g.sort_values("date").reset_index(drop=True)
        for k in DELAYS:
            # 같은 항행시즌(같은 연도) 안에서만 비교. 연도 경계를 넘으면 무의미.
            cur = g["R_PC7"].values
            fut = g["R_PC7"].shift(-k).values
            same_year = (g["year"].values == g["year"].shift(-k).values)
            m = same_year & ~np.isnan(fut)
            chg = (fut[m] - cur[m]) / cur[m] * 100

            rows.append({
                "region": region, "delay_days": k, "n": int(m.sum()),
                "mean_pct": chg.mean(), "median_pct": np.median(chg),
                "p_worse": (chg > 0).mean(),
                "p_better10": (chg < -10).mean(), "p_worse10": (chg > 10).mean(),
            })
            print(f"{REGION_KR[region]:<14}{k:>4}일{chg.mean():>11.1f}{np.median(chg):>10.1f}"
                  f"{(chg > 0).mean():>10.1%}{(chg < -10).mean():>12.1%}{(chg > 10).mean():>12.1%}")

    delay_df = pd.DataFrame(rows)
    delay_df.to_csv(os.path.join(OUT_DIR, "D_delay_effect.csv"), index=False)

    # ---- 2. 계절 위치에 따른 연기 효과 역전 ----
    print("\n\n[출항 시점별 3일 연기 효과 — 월별 분해]")
    print("  같은 '3일 연기'라도 시즌 초반과 후반의 의미가 정반대일 수 있다.\n")
    seg = []
    for region, g in df.groupby("region"):
        g = g.sort_values("date").reset_index(drop=True)
        cur, fut = g["R_PC7"].values, g["R_PC7"].shift(-3).values
        m = (g["year"].values == g["year"].shift(-3).values) & ~np.isnan(fut)
        tmp = pd.DataFrame({
            "region": region, "month": g["date"].dt.month.values[m],
            "chg": (fut[m] - cur[m]) / cur[m] * 100,
        })
        seg.append(tmp)
    seg = pd.concat(seg)
    piv = seg.pivot_table(index="region", columns="month", values="chg", aggfunc="mean")
    piv.index = [REGION_KR[i] for i in piv.index]
    piv.columns = [f"{m}월" for m in piv.columns]
    print(piv.round(1).to_string())
    print("\n  음수 = 연기가 위험 감소, 양수 = 연기가 위험 증가")

    # ---- 3. 쇄빙지원 잔여위험 ----
    print("\n\n[쇄빙지원 적용 시 잔여위험 — 완화효과 η 가정범위별]")
    print("  η는 실측 검증이 불가능한 가정값. 절대 감소폭이 아니라 '구간 간 순서'만 해석한다.\n")
    print(f"{'구간':<14}{'조치없음':>10}" + "".join(f"{'η='+str(e):>12}" for e in ETA_ESCORT))
    esc_rows = []
    for region, g in df.groupby("region"):
        base = g["R_PC7"].mean()
        line = f"{REGION_KR[region]:<14}{base:>10.3f}"
        rec = {"region": region, "base": base}
        for e in ETA_ESCORT:
            # 쇄빙지원은 해빙위험만 완화한다. 파고·풍속·안개는 그대로 남는다.
            ice_share = g["siconc_p90"].pipe(lambda s: np.clip((s - 0.071) / 0.5, 0, 1))
            ice_contrib = ice_share * 0.35 / sum([0.35, 0.20, 0.25, 0.10, 0.10])
            resid = (g["P_PC7"] - ice_contrib * e) * g["R_PC7"] / g["P_PC7"]
            line += f"{resid.mean():>12.3f}"
            rec[f"eta_{e}"] = resid.mean()
        esc_rows.append(rec)
        print(line)

    pd.DataFrame(esc_rows).to_csv(os.path.join(OUT_DIR, "D_escort_residual.csv"), index=False)

    # ---- 4. 최적 출항시점 ----
    print("\n\n[구간별 최저위험 출항시점 — 10년 평균 일별 위험의 최솟값]")
    df["doy"] = df["date"].dt.strftime("%m-%d")
    for region, g in df.groupby("region"):
        prof = g.groupby("doy")["R_PC7"].mean()
        best, worst = prof.idxmin(), prof.idxmax()
        print(f"  {REGION_KR[region]:<14} 최저 {best} (R={prof.min():.3f}) / "
              f"최고 {worst} (R={prof.max():.3f}) / 격차 {(prof.max()/prof.min()-1)*100:.0f}%")

    print(f"\n저장: {OUT_DIR}/D_delay_effect.csv, D_escort_residual.csv")


if __name__ == "__main__":
    main()
