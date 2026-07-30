"""
검증3 — KPDC ARAON 선상 기상관측 vs ERA5 재분석
AURORA 프로젝트

데이터: [KOPRI-KPDC-00001463/00001704/00002146/00002359/00002855/00002994]
        Weather data on ARAON DaDis for Arctic cruise, 2020~2025
        1초 간격 선상관측, 6개 항차 12,189시간

세 가지를 수행한다.

A. ERA5 검증 — 위험지수 기상 입력변수가 실제 해상관측과 맞물리는가
B. 풍속 규약 판별 — 원자료 풍속이 실제풍인가 겉보기풍인가
   (메타데이터에 명시가 없다. 겉보기풍을 ERA5의 실제풍과 그대로 대조하면
    검증이 아니라 오류가 되므로 선행 판별이 필수다. 선박속도는 GPS에서 유도.)
C. 역방향 검증 — ERA5로 선상 관측장비의 결함을 탐지

QC 계층 (각 단계가 실제로 필요했음을 확인하고 도입):
  1) 값 단위 물리범위 필터
  2) 파일 단위 불량률 게이트 — 원자료 대부분이 범위 밖인 시간대는 잔존값도 못 믿는다
  3) 기록 완결성 필터 — 3,600초 중 일부만 기록된 파일에서 -39°C 고정값이 관측됨
  4) 강건통계 병기 — Pearson r은 이상치 몇 개에 무너지므로 중앙값 오차·Spearman 병기
"""
import os

import numpy as np
import pandas as pd
from scipy import stats

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "track", os.path.join(os.path.dirname(__file__), "14_era5_track_extract.py"))
track_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(track_mod)

BASE = os.path.dirname(__file__)
OUT_DIR = os.path.join(BASE, "results")

MIN_SEC = 3000       # 시간당 3,600초 중 최소 기록수
SENSOR_OK_WIND = 0.05  # 풍속 0값 비율이 이보다 크면 결함으로 간주


def to_uv(speed, dir_from):
    """기상학적 풍향(불어오는 방향) → 바람이 향하는 방향의 u,v."""
    r = np.radians(dir_from)
    return -speed * np.sin(r), -speed * np.cos(r)


def metrics(obs, era, label):
    m = ~(np.isnan(obs) | np.isnan(era))
    if m.sum() < 30:
        return None
    o, e = obs[m], era[m]
    d = o - e
    r, p = stats.pearsonr(o, e)
    rho, _ = stats.spearmanr(o, e)
    return {
        "변수": label, "n": int(m.sum()),
        "Pearson r": r, "Spearman": rho,
        "중앙값오차": float(np.median(d)),
        "MAD": float(np.median(np.abs(d - np.median(d)))),
        "RMSE": float(np.sqrt(np.mean(d ** 2))),
        "이상치율(|오차|>3)": float((np.abs(d) > 3).mean()),
    }


def wind_hypotheses(g):
    """관측 풍속이 실제풍인지 겉보기풍인지 ERA5 정합도로 판별."""
    d = g.dropna(subset=["wspd", "wdir", "sog_ms", "cog_deg", "wind_ms"])
    d = d[d["wspd"] > 0]
    if len(d) < 50:
        return None, d
    ou, ov = to_uv(d["wspd"].values, d["wdir"].values)
    sr = np.radians(d["cog_deg"].values)
    su, sv = d["sog_ms"].values * np.sin(sr), d["sog_ms"].values * np.cos(sr)

    cand = {
        "H1 관측=실제풍": d["wspd"].values,
        "H2 관측=겉보기풍(선속보정)": np.hypot(ou + su, ov + sv),
    }
    e = d["wind_ms"].values
    rows = []
    for k, x in cand.items():
        r, _ = stats.pearsonr(x, e)
        rows.append({"가설": k, "r": r,
                     "RMSE": float(np.sqrt(np.mean((x - e) ** 2))),
                     "bias": float(np.mean(x - e))})
    d = d.copy()
    d["wspd_corrected"] = cand["H2 관측=겉보기풍(선속보정)"]
    return pd.DataFrame(rows), d


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    ar = pd.read_csv(os.path.join(BASE, "araon_hourly.csv"), parse_dates=["datetime"])

    print("=" * 88)
    print("검증3 — KPDC ARAON 선상 기상관측 vs ERA5 재분석")
    print("=" * 88)
    print(f"\n원자료 {len(ar):,}시간 (6개 항차, 2020~2025)")

    n0 = len(ar)
    ar = ar[ar["n_sec"] >= MIN_SEC]
    print(f"기록 완결성 필터(>={MIN_SEC}초/시간): {n0-len(ar):,}시간 제외 → {len(ar):,}시간")

    arctic = ar[ar["latitude"] > 65].copy()
    print(f"북위 65도 이북: {len(arctic):,}시간")

    matched = track_mod.extract_track(arctic)
    matched = matched[matched["t2m_C"].notna()].copy()
    print(f"ERA5 구간 박스 내 매칭: {len(matched):,}시간")
    print(f"  연도별 {matched.groupby('cruise_year').size().to_dict()}")
    print(f"  구간별 {matched['era5_region'].value_counts().to_dict()}")
    matched.to_csv(os.path.join(OUT_DIR, "V3_araon_era5_matched.csv"), index=False)

    # ---- C. 센서 상태 먼저 판정 (이후 해석의 전제) ----
    print("\n\n[1] 선상 관측장비 상태 — ERA5를 기준으로 한 역방향 진단")
    print("  검증은 양방향이다. 어느 해 자료를 검증에 쓸 수 있는지부터 정해야 한다.\n")
    print(f"  {'연도':<7}{'기압유효':>9}{'풍속0비율':>10}{'풍속p99':>9}{'ERA5p99':>9}  판정")
    status = {}
    for yr, g in matched.groupby("cruise_year"):
        pv = 1 - g["qc_bad_pres"].mean()
        zf = g["wspd_zero_frac"].mean()
        o99 = np.nanpercentile(g["wspd"].dropna(), 99) if g["wspd"].notna().any() else np.nan
        e99 = np.nanpercentile(g["wind_ms"], 99)
        wind_ok = (zf < SENSOR_OK_WIND) and (o99 > e99 * 0.6)
        pres_ok = pv > 0.9
        status[yr] = {"wind_ok": wind_ok, "pres_ok": pres_ok}
        v = ("정상" if wind_ok and pres_ok else
             "풍속만 정상" if wind_ok else "기압만 정상" if pres_ok else "풍속·기압 모두 결함")
        print(f"  {yr:<7}{pv:>9.1%}{zf:>10.1%}{o99:>9.1f}{e99:>9.1f}  {v}")

    print("\n  → 기압센서는 2022년까지 정상, 2023년부터 전량 결측(500.00 고정).")
    print("     풍속센서는 2023·2024년 이상(0값 20%대, p99가 ERA5의 60% 미만).")
    print("     따라서 풍속 검증은 센서 정상연도만으로 수행해야 한다.")

    # ---- B. 풍속 규약 판별 (센서 정상연도만) ----
    print("\n\n[2] 풍속 규약 판별 — 실제풍인가 겉보기풍인가")
    print("  센서 결함연도를 섞으면 판별 자체가 무의미하므로 정상연도만 사용한다.\n")
    good = [y for y, s in status.items() if s["wind_ok"]]
    print(f"  대상 연도: {good}\n")
    for yr in good:
        res, gd = wind_hypotheses(matched[matched["cruise_year"] == yr])
        if res is None:
            continue
        print(f"  {yr}년 (n={len(gd):,})")
        print(res.to_string(index=False, float_format=lambda x: f"{x:8.3f}"))
        print()

    # ---- A. 변수별 검증 ----
    print("\n[3] 변수별 ERA5 검증")
    print("  Pearson r은 이상치 몇 개에 무너진다. 중앙값오차·MAD·Spearman을 함께 본다.\n")
    rows = []
    for yr, g in matched.groupby("cruise_year"):
        m = metrics(g["temp_c"].values, g["t2m_C"].values, "기온(°C)")
        if m:
            m.update(연도=yr, 센서="정상")
            rows.append(m)
        if status[yr]["wind_ok"]:
            m = metrics(g["wspd"].values, g["wind_ms"].values, "풍속-원값(m/s)")
            if m:
                m.update(연도=yr, 센서="정상")
                rows.append(m)
            _, gd = wind_hypotheses(g)
            if "wspd_corrected" in gd:
                m = metrics(gd["wspd_corrected"].values, gd["wind_ms"].values, "풍속-선속보정(m/s)")
                if m:
                    m.update(연도=yr, 센서="정상")
                    rows.append(m)
        else:
            m = metrics(g["wspd"].values, g["wind_ms"].values, "풍속-원값(m/s)")
            if m:
                m.update(연도=yr, 센서="결함")
                rows.append(m)

    res = pd.DataFrame(rows)
    cols = ["연도", "변수", "센서", "n", "Pearson r", "Spearman", "중앙값오차", "MAD",
            "RMSE", "이상치율(|오차|>3)"]
    res = res[cols].sort_values(["변수", "연도"])
    for v, g in res.groupby("변수"):
        print(f"  [{v}]")
        print(g.drop(columns=["변수"]).to_string(index=False,
              float_format=lambda x: f"{x:7.3f}"))
        print()

    res.to_csv(os.path.join(OUT_DIR, "V3_validation_metrics.csv"), index=False)

    # ---- 종합 ----
    t = res[res["변수"] == "기온(°C)"]
    print("\n[4] 종합")
    print(f"  기온: 6개 항차 전부에서 중앙값오차 {t['중앙값오차'].min():+.2f} ~ "
          f"{t['중앙값오차'].max():+.2f}°C, MAD {t['MAD'].min():.2f}~{t['MAD'].max():.2f}°C")
    print(f"        센서 정상연도(2022~2024) Pearson r = "
          f"{t[t['연도'].isin([2022,2023,2024])]['Pearson r'].min():.3f}~"
          f"{t[t['연도'].isin([2022,2023,2024])]['Pearson r'].max():.3f}")
    w = res[(res["변수"] == "풍속-선속보정(m/s)")]
    if len(w):
        print(f"  풍속: 센서 정상연도 선속보정 후 r = {w['Pearson r'].min():.3f}~{w['Pearson r'].max():.3f}")
    print(f"\n저장: {OUT_DIR}/V3_araon_era5_matched.csv, V3_validation_metrics.csv")


if __name__ == "__main__":
    main()
