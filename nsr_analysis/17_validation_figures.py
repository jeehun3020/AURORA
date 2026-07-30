"""
검증3 그림 — ARAON 선상관측 vs ERA5
AURORA 프로젝트
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

BASE = os.path.dirname(__file__)
RES = os.path.join(BASE, "results")
FIG = os.path.join(BASE, "figures")

plt.rcParams["font.family"] = "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 130

YCOL = {2020: "#2E86AB", 2021: "#3B7A57", 2022: "#F18F01",
        2023: "#A23B72", 2024: "#8B5E3C"}


def main():
    os.makedirs(FIG, exist_ok=True)
    d = pd.read_csv(os.path.join(RES, "V3_araon_era5_matched.csv"), parse_dates=["datetime"])
    m = pd.read_csv(os.path.join(RES, "V3_validation_metrics.csv"))
    hourly = pd.read_csv(os.path.join(BASE, "araon_hourly.csv"), parse_dates=["datetime"])

    fig, ax = plt.subplots(2, 2, figsize=(13.5, 10))

    # (1) 기온 산점도
    a = ax[0, 0]
    t = d.dropna(subset=["temp_c", "t2m_C"])
    for yr, g in t.groupby("cruise_year"):
        a.scatter(g["t2m_C"], g["temp_c"], s=7, alpha=.45,
                  color=YCOL.get(yr, "gray"), label=f"{yr} (n={len(g)})")
    lim = [-8, 14]
    a.plot(lim, lim, "k--", lw=1.1, zorder=5)
    a.set_xlim(lim); a.set_ylim(lim)
    a.set_xlabel("ERA5 2m 기온 (°C)"); a.set_ylabel("ARAON 선상관측 기온 (°C)")
    tm = m[m["변수"] == "기온(°C)"]
    a.set_title(f"기온 — 6개 항차 전부 중앙값오차 ±0.53°C 이내\n"
                f"MAD {tm['MAD'].min():.2f}~{tm['MAD'].max():.2f}°C", fontsize=11, pad=9)
    a.legend(fontsize=7.5, loc="upper left"); a.grid(alpha=.25)

    # (2) 연도별 지표 — 기온은 안정, 풍속은 센서 상태에 좌우
    a = ax[0, 1]
    yrs = sorted(d["cruise_year"].unique())
    tr = [tm[tm["연도"] == y]["Pearson r"].iloc[0] if (tm["연도"] == y).any() else np.nan for y in yrs]
    wm = m[m["변수"] == "풍속-원값(m/s)"]
    wr = [wm[wm["연도"] == y]["Pearson r"].iloc[0] if (wm["연도"] == y).any() else np.nan for y in yrs]
    ok = [wm[wm["연도"] == y]["센서"].iloc[0] if (wm["연도"] == y).any() else "?" for y in yrs]
    x = np.arange(len(yrs))
    a.bar(x - .2, tr, .4, label="기온", color="#2E86AB")
    a.bar(x + .2, wr, .4, label="풍속",
          color=["#3B7A57" if s == "정상" else "#C1440E" for s in ok])
    for i, s in enumerate(ok):
        if s == "결함":
            a.text(i + .2, max(wr[i], 0) + .04, "센서\n결함", ha="center",
                   fontsize=7.5, color="#C1440E")
    a.set_xticks(x); a.set_xticklabels(yrs)
    a.set_ylabel("ERA5와의 Pearson r"); a.set_ylim(-.1, 1.05)
    a.axhline(0, color="k", lw=.8)
    a.set_title("변수별·연도별 정합도\n기온은 안정, 풍속은 센서 상태에 좌우", fontsize=11, pad=9)
    a.legend(fontsize=9); a.grid(alpha=.25, axis="y")

    # (3) 센서 결함 타임라인 — ERA5가 관측장비 이상을 드러낸다
    a = ax[1, 0]
    s = hourly.groupby("cruise_year").agg(
        기압유효=("qc_bad_pres", lambda v: 1 - v.mean()),
        풍속0비율=("wspd_zero_frac", "mean")).reset_index()
    xs = np.arange(len(s))
    a.bar(xs - .2, s["기압유효"] * 100, .4, label="기압 유효율", color="#2E86AB")
    a.bar(xs + .2, s["풍속0비율"] * 100, .4, label="풍속 0값 비율", color="#C1440E")
    a.set_xticks(xs); a.set_xticklabels(s["cruise_year"].astype(int))
    a.set_ylabel("%")
    a.axvspan(2.5, 5.5, color="red", alpha=.07)
    a.text(4, 78, "기압센서 결함구간\n(2023~2025)", ha="center", fontsize=9, color="#8B0000",
           bbox=dict(boxstyle="round,pad=0.35", fc="mistyrose", ec="#8B0000", lw=.8))
    a.set_title("역방향 검증 — ERA5로 탐지한 선상 관측장비 이상\n"
                "기압센서 2023년부터 전량 500.00 고정", fontsize=11, pad=9)
    a.legend(fontsize=9); a.grid(alpha=.25, axis="y")

    # (4) 풍속 — 센서 정상 최량연도(2022) 원값 vs 선속보정
    a = ax[1, 1]
    g = d[d["cruise_year"] == 2022].dropna(subset=["wspd", "wind_ms", "sog_ms", "cog_deg", "wdir"])
    g = g[g["wspd"] > 0]
    r_ = np.radians(g["wdir"].values)
    ou, ov = -g["wspd"].values * np.sin(r_), -g["wspd"].values * np.cos(r_)
    sr = np.radians(g["cog_deg"].values)
    su, sv = g["sog_ms"].values * np.sin(sr), g["sog_ms"].values * np.cos(sr)
    corr = np.hypot(ou + su, ov + sv)
    r1 = stats.pearsonr(g["wspd"].values, g["wind_ms"].values)[0]
    r2 = stats.pearsonr(corr, g["wind_ms"].values)[0]
    a.scatter(g["wind_ms"], g["wspd"], s=8, alpha=.4, color="#C1440E", label=f"원값  r={r1:.3f}")
    a.scatter(g["wind_ms"], corr, s=8, alpha=.4, color="#3B7A57", label=f"선속보정  r={r2:.3f}")
    lim = [0, 25]
    a.plot(lim, lim, "k--", lw=1.1)
    a.set_xlim(lim); a.set_ylim(lim)
    a.set_xlabel("ERA5 10m 풍속 (m/s)"); a.set_ylabel("ARAON 관측 풍속 (m/s)")
    a.set_title("풍속 — 2022년 항차(센서 정상 최량)\nGPS 유도 선속으로 보정 시 정합도 개선",
                fontsize=11, pad=9)
    a.legend(fontsize=9); a.grid(alpha=.25)

    plt.tight_layout()
    plt.savefig(os.path.join(FIG, "V3_araon_validation.png"))
    plt.close()
    print("V3_araon_validation.png")


if __name__ == "__main__":
    main()
