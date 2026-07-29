"""
분석C — NSR 구간별 환경위험지수 + 극지구조공백지수(PRGI) + 가중치 민감도
AURORA 프로젝트

산출물:
  R_고유 = P(사고가능성) × S(사고결과)
  P: ERA5 환경위험 × 선박취약도(PC6/PC7)
  S: PRGI 기반 극지 손실증폭

⚠️ 이 지수는 POLARIS가 아니다.
   POLARIS RIO는 얼음 '유형별' 농도와 IMO 공식 RV표를 요구하는데,
   ERA5 siconc는 총 농도만 제공하고 얼음 유형 구분이 없다.
   따라서 아래 임계값은 문헌적 근거가 아니라 '물리적으로 설명 가능한 잠정값'이며,
   결론은 개별 점수의 절대값이 아니라 '가중치를 흔들어도 유지되는 순위'로만 제시한다.
   (§2 표현원칙: 정밀한 숫자 단정 금지, 범위+신뢰도로 제시)

임계값 근거(잠정):
  해빙농도  0.10 미만=개빙수역 / 0.80 초과=밀집빙, 비내빙선 사실상 통항불가
  풍속      5 m/s 미만=무시가능 / 20 m/s 초과=Beaufort 8 강풍
  파고      1 m 미만=평온 / 5 m 초과=황천, 조종성·구조가능성 급락
  기온      0°C 초과=착빙없음 / -20°C 미만=갑판착빙·장비고장 위험
  이슬점차  3K 초과=시정양호 / 0.5K 미만=안개 고확률 (가시거리 직접변수 대체)
            ※ 실측 분포(중앙값 1.6K, 최대 6.2K)에 맞춰 보정. 최초 5K 기준은 거의 전 구간이
              포화되어 판별력이 없었다.

선박취약도 적용방식:
  PC7은 PC6보다 내빙능력이 낮으므로 '같은 얼음에서 더 일찍 한계에 도달'한다.
  따라서 위험점수에 계수를 곱하는 대신 해빙 임계값 자체를 취약도만큼 낮춘다.
  (사후 곱셈 후 clip 방식은 고빙해역에서 상한에 걸려 PC6·PC7 차이가 되레 줄어드는
   역전 현상이 발생했다.)
"""
import os

import numpy as np
import pandas as pd

BASE = os.path.dirname(__file__)
OUT_DIR = os.path.join(BASE, "results")
RNG = np.random.default_rng(42)

# ERA5 다운로드에 사용한 구간 박스의 중심점
REGION_CENTER = {
    "kara": (73.5, 75.0),
    "laptev": (75.5, 120.0),
    "east_siberian": (72.5, 162.5),
    "chukchi": (70.0, -167.5),
}
REGION_KR = {"kara": "카라해", "laptev": "랍테프해",
             "east_siberian": "동시베리아해", "chukchi": "추크치해"}

# 러시아 북극권 주요 수색구조(SAR)·피난 거점. 좌표는 공개된 정착지 위치 기준 근사값.
SAR_BASES = {
    "Murmansk": (68.97, 33.08), "Arkhangelsk": (64.54, 40.54),
    "Naryan-Mar": (67.64, 53.01), "Sabetta": (71.26, 72.06),
    "Dikson": (73.51, 80.55), "Dudinka": (69.41, 86.18),
    "Khatanga": (71.98, 102.47), "Tiksi": (71.64, 128.87),
    "Pevek": (69.70, 170.31), "Anadyr": (64.73, 177.51),
    "Provideniya": (64.38, -173.30),
}

# 선박 취약도: 해빙 위험에 곱해지는 계수. PC7이 PC6보다 내빙능력이 낮다.
# 절대값 자체가 아니라 두 등급의 상대차이만 해석에 사용한다.
SHIP_VULN = {"PC6": 1.0, "PC7": 1.4}

BASE_WEIGHTS = {"ice": 0.35, "wind": 0.20, "wave": 0.25, "cold": 0.10, "fog": 0.10}


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def ramp(x, lo, hi):
    """lo 이하=0, hi 이상=1 인 선형 정규화 (hi<lo면 역방향)."""
    if hi > lo:
        return np.clip((x - lo) / (hi - lo), 0, 1)
    return np.clip((lo - x) / (lo - hi), 0, 1)


ICE_LIMITS_PC6 = (0.10, 0.80)  # 개빙수역 ~ 밀집빙


def compute_hazards(df, ship="PC6"):
    """선박등급별 환경위험 성분(0~1). 등급차는 해빙 임계값 축소로 반영."""
    lo, hi = np.array(ICE_LIMITS_PC6) / SHIP_VULN[ship]
    h = pd.DataFrame(index=df.index)
    h["ice"] = ramp(df["siconc_p90"], lo, hi)
    h["wind"] = ramp(df["wind_p90"], 5.0, 20.0)
    h["wave"] = ramp(df["swh_p90"].fillna(df["swh_p90"].median()), 1.0, 5.0)
    h["cold"] = ramp(df["t2m_min"], 0.0, -20.0)
    h["fog"] = ramp(df["dewpoint_spread_mean"], 3.0, 0.5)
    return h


def prgi_table():
    """구간별 극지구조공백지수. 최근접 SAR 거점까지 거리를 정규화."""
    rows = []
    for reg, (lat, lon) in REGION_CENTER.items():
        d = {b: haversine(lat, lon, blat, blon) for b, (blat, blon) in SAR_BASES.items()}
        nearest = min(d, key=d.get)
        rows.append({"region": reg, "nearest_sar": nearest, "sar_dist_km": d[nearest]})
    t = pd.DataFrame(rows)
    # 400km(헬기 왕복 실용한계권) ~ 1000km(장거리 구조 지연 심각) 구간을 0~1로
    t["PRGI"] = ramp(t["sar_dist_km"], 400, 1000)
    # 손실증폭 S: 구조공백이 클수록 같은 사고도 결과가 커진다. lambda=1.0 잠정.
    t["S_amplify"] = 1 + 1.0 * t["PRGI"]
    return t


def score(hazards, weights):
    w = pd.Series(weights)
    w = w / w.sum()
    return (hazards * w).sum(axis=1)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    df = pd.read_csv(os.path.join(BASE, "era5_daily_features.csv"), parse_dates=["date"])
    df["month"] = df["date"].dt.month

    hz = {s: compute_hazards(df, s) for s in SHIP_VULN}
    prgi = prgi_table().set_index("region")

    print("=" * 88)
    print("분석C — NSR 구간별 환경위험지수 (ERA5 2015~2024 항행시즌 7~10월, n=4,920일)")
    print("=" * 88)

    print("\n[극지구조공백지수 PRGI — 최근접 SAR 거점까지 거리]")
    print(f"{'구간':<14}{'최근접거점':<14}{'거리(km)':>10}{'PRGI':>8}{'손실증폭S':>10}")
    for reg, r in prgi.iterrows():
        print(f"{REGION_KR[reg]:<14}{r.nearest_sar:<14}{r.sar_dist_km:>10.0f}"
              f"{r.PRGI:>8.2f}{r.S_amplify:>10.2f}")

    # 구간×월 위험 프로파일
    for ship in ["PC6", "PC7"]:
        df[f"P_{ship}"] = score(hz[ship], BASE_WEIGHTS)
        df[f"R_{ship}"] = df[f"P_{ship}"] * df["region"].map(prgi["S_amplify"])

    print("\n\n[구간 × 월 고유위험 R = P × S  (PC7 기준)]")
    piv = df.pivot_table(index="region", columns="month", values="R_PC7", aggfunc="mean")
    piv.index = [REGION_KR[i] for i in piv.index]
    piv.columns = [f"{m}월" for m in piv.columns]
    piv["연중평균"] = piv.mean(axis=1)
    print(piv.round(3).sort_values("연중평균", ascending=False).to_string())

    print("\n\n[위험 구성요소 분해 — 구간별 평균 위험도 기여 (PC7 기준, 정규화 0~1)]")
    hz2 = hz["PC7"].copy()
    hz2["region"] = df["region"].values
    comp = hz2.groupby("region").mean()
    comp.index = [REGION_KR[i] for i in comp.index]
    comp.columns = ["해빙", "풍속", "파고", "저온", "안개"]
    print(comp.round(3).to_string())

    print("\n\n[선박등급 비교 — PC6 vs PC7 고유위험]")
    cmp_rows = []
    for reg, g in df.groupby("region"):
        p6, p7 = g["R_PC6"].mean(), g["R_PC7"].mean()
        cmp_rows.append({"구간": REGION_KR[reg], "PC6": p6, "PC7": p7,
                         "PC7할증율(%)": (p7 / p6 - 1) * 100})
    cdf = pd.DataFrame(cmp_rows).sort_values("PC7할증율(%)", ascending=False)
    print(cdf.round(3).to_string(index=False))

    # 등급차는 구간 평균으로 보면 과소평가된다. 해빙농도 구간별로 나눠 봐야
    # '어떤 조건에서 등급 선택이 실익이 있는가'가 드러난다.
    print("\n\n[해빙농도 구간별 PC6 → PC7 위험격차]")
    df["gap"] = df["R_PC7"] - df["R_PC6"]
    bins = [0, .1, .3, .5, .7, .9, 1.01]
    labels = ["0-10%", "10-30%", "30-50%", "50-70%", "70-90%", "90-100%"]
    df["ice_bin"] = pd.cut(df["siconc_p90"], bins, labels=labels)
    gb = df.groupby("ice_bin", observed=True).agg(
        일수=("gap", "size"), PC6=("R_PC6", "mean"), PC7=("R_PC7", "mean"))
    gb["격차율(%)"] = (gb["PC7"] / gb["PC6"] - 1) * 100
    print(gb.round(3).to_string())
    print("  → 등급 선택의 실익은 중간 빙조건에서 최대. 개빙수역은 등급 무관,")
    print("     밀집빙은 두 등급 모두 한계 초과라 지수가 포화되어 차이가 사라진다.")

    # ---- 가중치 민감도: 순위가 가중치 선택에 얼마나 좌우되는가 ----
    print("\n\n[가중치 민감도 분석 — Dirichlet 1,000회 교란]")
    base_rank = (df.groupby(["region", "month"])["R_PC7"].mean()
                 .rank(ascending=False))
    taus, top1 = [], []
    for _ in range(1000):
        w = RNG.dirichlet(np.array(list(BASE_WEIGHTS.values())) * 10)
        wd = dict(zip(BASE_WEIGHTS.keys(), w))
        s = score(hz["PC7"], wd) * df["region"].map(prgi["S_amplify"])
        r = s.groupby([df["region"], df["month"]]).mean().rank(ascending=False)
        taus.append(base_rank.corr(r, method="spearman"))
        top1.append(r.idxmin())

    taus = np.array(taus)
    top_counts = pd.Series(top1).value_counts(normalize=True)
    print(f"  기준가중치 대비 순위 Spearman 상관: 평균 {taus.mean():.3f}, "
          f"5퍼센타일 {np.percentile(taus, 5):.3f}, 최소 {taus.min():.3f}")
    print(f"  최고위험 구간×월 1위 유지율:")
    for (reg, m), frac in top_counts.head(3).items():
        print(f"    {REGION_KR[reg]} {m}월 — {frac:.1%}")

    df.to_csv(os.path.join(OUT_DIR, "C_daily_risk.csv"), index=False)
    piv.to_csv(os.path.join(OUT_DIR, "C_region_month_risk.csv"))
    prgi.to_csv(os.path.join(OUT_DIR, "C_prgi.csv"))
    print(f"\n저장: {OUT_DIR}/C_daily_risk.csv, C_region_month_risk.csv, C_prgi.csv")


if __name__ == "__main__":
    main()
