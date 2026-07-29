"""
분석 A~D 핵심 그림 생성
AURORA 프로젝트 — 보고서·발표자료용 figure
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

REGION_KR = {"kara": "카라해", "laptev": "랍테프해",
             "east_siberian": "동시베리아해", "chukchi": "추크치해"}
SEA_KR = {"Kara": "카라해", "Laptev": "랍테프해",
          "East-Siberian": "동시베리아해", "Chukchi": "추크치해"}
COL = {"카라해": "#2E86AB", "랍테프해": "#A23B72",
       "동시베리아해": "#F18F01", "추크치해": "#3B7A57"}


def fig_a_navigable():
    """A — 해역별 항행가능일수 47년 추세. NSR은 최악 구간이 결정한다."""
    ice = pd.read_csv(os.path.join(BASE, "nsidc_daily_extent.csv"), parse_dates=["date"])
    ice["year"] = ice["date"].dt.year
    ice = ice[(ice.year >= 1979) & (ice.year <= 2025)]
    area = ice.groupby("sea")["extent_km2"].max()
    ice["open"] = 1 - ice["extent_km2"] / ice["sea"].map(area)

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    ax = axes[0]
    for sea, g in ice.groupby("sea"):
        nav = g.assign(n=g["open"] > 0.5).groupby("year")["n"].sum()
        kr = SEA_KR[sea]
        ax.plot(nav.index, nav.values, "o-", ms=2.5, lw=1, alpha=.55, color=COL[kr])
        sl, ic, r, p, se = stats.linregress(nav.index, nav.values)
        ax.plot(nav.index, sl * nav.index + ic, lw=2.4, color=COL[kr],
                label=f"{kr}  +{sl:.2f}일/년")
    ax.set_title("NSR 해역별 항행가능일수 추세 (개빙수역 50% 초과)", fontsize=11.5, pad=9)
    ax.set_xlabel("연도"); ax.set_ylabel("연간 항행가능일수")
    ax.legend(fontsize=8.5, loc="upper left"); ax.grid(alpha=.25)

    ax = axes[1]
    recent = {}
    for sea, g in ice[ice.year >= 2021].groupby("sea"):
        nav = g.assign(n=g["open"] > 0.5).groupby("year")["n"].sum().mean()
        nav80 = g.assign(n=g["open"] > 0.8).groupby("year")["n"].sum().mean()
        recent[SEA_KR[sea]] = (nav, nav80)
    order = sorted(recent, key=lambda k: -recent[k][0])
    x = np.arange(len(order))
    ax.bar(x - .19, [recent[k][0] for k in order], .38,
           label="개빙>50%", color=[COL[k] for k in order])
    ax.bar(x + .19, [recent[k][1] for k in order], .38,
           label="개빙>80%", color=[COL[k] for k in order], alpha=.45, hatch="//")
    ax.set_xticks(x); ax.set_xticklabels(order, fontsize=9.5)
    ax.set_ylabel("연간 항행가능일수"); ax.legend(fontsize=9)
    ax.set_title("최근 5년(2021~2025) 평균 — 동시베리아해가 병목", fontsize=11.5, pad=9)
    ax.grid(alpha=.25, axis="y")
    for i, k in enumerate(order):
        ax.text(i - .19, recent[k][0] + 2, f"{recent[k][0]:.0f}", ha="center", fontsize=8.5)
        ax.text(i + .19, recent[k][1] + 2, f"{recent[k][1]:.0f}", ha="center", fontsize=8.5)

    plt.tight_layout(); plt.savefig(os.path.join(FIG, "A_navigable_days.png")); plt.close()


def fig_b_decoupling():
    """B — 해빙은 단조 감소, 통항량은 비단조. 2013→2015 붕괴가 핵심 반증."""
    d = pd.read_csv(os.path.join(RES, "B_merged_series.csv"))
    fig, ax1 = plt.subplots(figsize=(9.5, 5))
    ax1.bar(d.year, d.transits, color="#2E86AB", alpha=.8, width=.62, label="NSR 완주 통항(항차)")
    ax1.set_ylabel("완주 transit 항차수", color="#2E86AB")
    ax1.tick_params(axis="y", labelcolor="#2E86AB")
    ax1.set_xlabel("연도")

    ax2 = ax1.twinx()
    ax2.plot(d.year, d.sep_ice_km2 / 1e6, "s--", color="#3B7A57", lw=1.8, ms=6,
             label="9월 해빙면적(4개해역 합)")
    ax2.plot(d.year, d.brent_usd / 100, "^-", color="#C1440E", lw=1.8, ms=6,
             label="Brent 유가(÷100 $/bbl)")
    ax2.set_ylabel("9월 해빙 (백만 km²)  /  유가 (÷100 $)")

    ax1.axvspan(2013.5, 2015.5, color="red", alpha=.08)
    ax1.annotate("2013→2015\n통항 -75%\n유가 -52%", xy=(2014.5, 85), ha="center",
                 fontsize=9, color="#8B0000",
                 bbox=dict(boxstyle="round,pad=0.4", fc="mistyrose", ec="#8B0000", lw=.9))

    h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, fontsize=8.5, loc="upper left")
    ax1.set_title("해빙 감소만으로는 NSR 통항량 변동을 설명할 수 없다\n"
                  "(통항 실적 9개 연도만 확보 — 2014·2017·2019~2022 누락)",
                  fontsize=11.5, pad=10)
    ax1.grid(alpha=.22, axis="y")
    plt.tight_layout(); plt.savefig(os.path.join(FIG, "B_decoupling.png")); plt.close()


def fig_c_risk():
    """C — 구간×월 위험 히트맵 + 등급 선택 실익이 최대인 빙조건."""
    d = pd.read_csv(os.path.join(RES, "C_daily_risk.csv"), parse_dates=["date"])
    d["month"] = d["date"].dt.month

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
    ax = axes[0]
    piv = d.pivot_table(index="region", columns="month", values="R_PC7", aggfunc="mean")
    piv = piv.loc[piv.mean(axis=1).sort_values(ascending=False).index]
    im = ax.imshow(piv.values, cmap="RdYlGn_r", aspect="auto", vmin=.2, vmax=.75)
    ax.set_xticks(range(4)); ax.set_xticklabels(["7월", "8월", "9월", "10월"])
    ax.set_yticks(range(len(piv))); ax.set_yticklabels([REGION_KR[i] for i in piv.index], fontsize=10)
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            ax.text(j, i, f"{piv.values[i, j]:.2f}", ha="center", va="center",
                    fontsize=10, fontweight="bold")
    ax.set_title("구간×월 고유위험 R = P × S  (PC7)", fontsize=11.5, pad=9)
    plt.colorbar(im, ax=ax, shrink=.85, label="고유위험")

    ax = axes[1]
    bins = [0, .1, .3, .5, .7, .9, 1.01]
    labels = ["0-10", "10-30", "30-50", "50-70", "70-90", "90-100"]
    d["ib"] = pd.cut(d.siconc_p90, bins, labels=labels)
    g = d.groupby("ib", observed=True).agg(PC6=("R_PC6", "mean"), PC7=("R_PC7", "mean"))
    gap = (g.PC7 / g.PC6 - 1) * 100
    ax.bar(range(len(gap)), gap.values, color="#A23B72", alpha=.85)
    ax.set_xticks(range(len(gap))); ax.set_xticklabels(labels, fontsize=9)
    ax.set_xlabel("해빙농도 (%)"); ax.set_ylabel("PC6 → PC7 위험 증가율 (%)")
    ax.set_title("선박등급 선택의 실익은 중간 빙조건에서 최대", fontsize=11.5, pad=9)
    for i, v in enumerate(gap.values):
        ax.text(i, v + .5, f"{v:.1f}%", ha="center", fontsize=9)
    ax.grid(alpha=.25, axis="y")
    ax.annotate("개빙수역\n등급 무의미", xy=(0, 2), xytext=(0.15, 14), fontsize=8,
                ha="center", arrowprops=dict(arrowstyle="->", lw=.9, color="gray"))
    ax.annotate("밀집빙\n양 등급 모두 한계초과", xy=(5, 1), xytext=(4.3, 14), fontsize=8,
                ha="center", arrowprops=dict(arrowstyle="->", lw=.9, color="gray"))

    plt.tight_layout(); plt.savefig(os.path.join(FIG, "C_risk_index.png")); plt.close()


def fig_d_whatif():
    """D — 출항연기는 평균과 중앙값의 부호가 다르다. 꼬리위험이 평균을 지배."""
    d = pd.read_csv(os.path.join(RES, "C_daily_risk.csv"), parse_dates=["date"])
    d["year"] = d["date"].dt.year
    d["month"] = d["date"].dt.month

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.7))

    ax = axes[0]
    for region, g in d.groupby("region"):
        g = g.sort_values("date").reset_index(drop=True)
        cur, fut = g.R_PC7.values, g.R_PC7.shift(-3).values
        m = (g.year.values == g.year.shift(-3).values) & ~np.isnan(fut)
        chg = (fut[m] - cur[m]) / cur[m] * 100
        kr = REGION_KR[region]
        ax.hist(np.clip(chg, -60, 60), bins=45, histtype="step", lw=1.9,
                color=COL[kr], label=f"{kr}  중앙값 {np.median(chg):+.1f}% / 평균 {chg.mean():+.1f}%")
    ax.axvline(0, color="k", lw=.9, ls="--")
    ax.set_xlabel("3일 연기 시 위험 변화 (%)"); ax.set_ylabel("일수")
    ax.set_title("출항 3일 연기 효과의 분포\n대부분 소폭 개선, 드물게 큰 악화 → 평균이 오도한다",
                 fontsize=11, pad=9)
    ax.legend(fontsize=7.8); ax.grid(alpha=.25)

    ax = axes[1]
    seg = []
    for region, g in d.groupby("region"):
        g = g.sort_values("date").reset_index(drop=True)
        cur, fut = g.R_PC7.values, g.R_PC7.shift(-3).values
        m = (g.year.values == g.year.shift(-3).values) & ~np.isnan(fut)
        seg.append(pd.DataFrame({"region": region, "month": g.month.values[m],
                                 "chg": (fut[m] - cur[m]) / cur[m] * 100}))
    seg = pd.concat(seg)
    piv = seg.pivot_table(index="region", columns="month", values="chg", aggfunc="mean")
    x = np.arange(4); w = .2
    for i, (region, row) in enumerate(piv.iterrows()):
        kr = REGION_KR[region]
        ax.bar(x + (i - 1.5) * w, row.values, w, label=kr, color=COL[kr])
    ax.axhline(0, color="k", lw=1)
    ax.set_xticks(x); ax.set_xticklabels(["7월", "8월", "9월", "10월"])
    ax.set_ylabel("3일 연기 시 평균 위험 변화 (%)")
    ax.set_title("같은 '3일 연기'도 시즌 초·후반에 정반대\n7월엔 이득, 10월엔 최대 +26%",
                 fontsize=11, pad=9)
    ax.legend(fontsize=8.5); ax.grid(alpha=.25, axis="y")

    plt.tight_layout(); plt.savefig(os.path.join(FIG, "D_whatif_delay.png")); plt.close()


def main():
    os.makedirs(FIG, exist_ok=True)
    fig_a_navigable(); print("A_navigable_days.png")
    fig_b_decoupling(); print("B_decoupling.png")
    fig_c_risk(); print("C_risk_index.png")
    fig_d_whatif(); print("D_whatif_delay.png")
    print(f"\n저장 위치: {FIG}")


if __name__ == "__main__":
    main()
