"""
발견 6·7 그림 — 항행창 이동 / 지수 분기
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

SEA_KR = {"Kara": "카라해", "Laptev": "랍테프해",
          "East-Siberian": "동시베리아해", "Chukchi": "추크치해"}
COL = {"카라해": "#2E86AB", "랍테프해": "#A23B72",
       "동시베리아해": "#F18F01", "추크치해": "#3B7A57"}


def md(doy, year=2021):
    return (pd.Timestamp(f"{year}-01-01") + pd.Timedelta(days=int(doy) - 1)).strftime("%m/%d")


def main():
    os.makedirs(FIG, exist_ok=True)
    w = pd.read_csv(os.path.join(RES, "X2_window_by_year.csv"))

    fig, ax = plt.subplots(1, 3, figsize=(16.5, 5.1))

    # (1) 개빙기 시작·종료의 47년 이동
    a = ax[0]
    for sea, g in w.groupby("sea"):
        g = g.dropna(subset=["open_start", "open_end"]).sort_values("year")
        if len(g) < 15:
            continue
        kr = SEA_KR[sea]
        for col, ls in [("open_start", "-"), ("open_end", "-")]:
            sl, ic, r, p, se = stats.linregress(g["year"], g[col])
            a.plot(g["year"], sl * g["year"] + ic, ls, lw=2.2, color=COL[kr],
                   alpha=.95 if col == "open_end" else .45)
        a.fill_between(g["year"],
                       np.polyval(np.polyfit(g["year"], g["open_start"], 1), g["year"]),
                       np.polyval(np.polyfit(g["year"], g["open_end"], 1), g["year"]),
                       color=COL[kr], alpha=.10)
    a.set_ylabel("연중 일자"); a.set_xlabel("연도")
    yt = [182, 213, 244, 274, 305]
    a.set_yticks(yt); a.set_yticklabels([md(d) for d in yt])
    a.set_title("개빙기 시작·종료의 47년 이동\n확장은 거의 전부 종료일 지연에서 온다",
                fontsize=11, pad=9)
    a.grid(alpha=.25)
    hs = [plt.Line2D([], [], color=COL[SEA_KR[s]], lw=2.2) for s in SEA_KR]
    a.legend(hs, list(SEA_KR.values()), fontsize=8, loc="upper left")

    # (2) 최소빙일은 이동하지 않았다
    a = ax[1]
    tr = pd.read_csv(os.path.join(RES, "X2_window_trends.csv"))
    mi = tr[tr["metric"] == "연중 최소빙일"]
    order = ["Kara", "Chukchi", "East-Siberian", "Laptev"]
    x = np.arange(len(order))
    # 유의성 표시를 축 안에 두려면 데이터 범위를 먼저 확정해야 한다
    sub = w[w["year"].isin(list(range(1979, 1984)) + list(range(2021, 2026)))]
    lo, hi = sub["min_ice_doy"].min(), sub["min_ice_doy"].max()
    pad = (hi - lo) * 0.16
    a.set_ylim(lo - pad * 0.4, hi + pad)
    label_y = hi + pad * 0.45

    for i, sea in enumerate(order):
        g = w[w["sea"] == sea]
        kr = SEA_KR[sea]
        early = g[g["year"] <= 1983]["min_ice_doy"]
        late = g[g["year"] >= 2021]["min_ice_doy"]
        a.scatter([i - .16] * len(early), early, s=26, color=COL[kr], alpha=.5, marker="o")
        a.scatter([i + .16] * len(late), late, s=26, color=COL[kr], alpha=.95, marker="s")
        a.plot([i - .16, i + .16], [early.mean(), late.mean()], "-", color=COL[kr], lw=2)
        r = mi[mi["sea"] == sea].iloc[0]
        lbl = f"*  {r['recent5']-r['early5']:+.0f}일" if r["p_value"] < 0.05 else "n.s."
        a.text(i, label_y, lbl, ha="center", fontsize=9,
               color="#8B0000" if r["p_value"] < 0.05 else "#555")
    a.set_xticks(x); a.set_xticklabels([SEA_KR[s] for s in order], fontsize=9.5)
    yt2 = [d for d in [244, 252, 260, 268, 276, 284] if lo - pad * 0.4 <= d <= hi + pad]
    a.set_yticks(yt2); a.set_yticklabels([md(d) for d in yt2])
    a.set_ylabel("연중 최소빙일")
    a.set_title("최소빙일은 이동하지 않았다\n○ 1979~83  ■ 2021~25 · 4개 중 3개 n.s.",
                fontsize=11, pad=9)
    a.grid(alpha=.25, axis="y")

    # (3) 최적일의 연간 변동 — 달력만으로 부족한 이유
    a = ax[2]
    r10 = w[w["year"] >= 2016]
    data, labels, cols = [], [], []
    for sea in order:
        g = r10[r10["sea"] == sea]["min_ice_doy"].dropna()
        data.append(g.values); labels.append(SEA_KR[sea]); cols.append(COL[SEA_KR[sea]])
    bp = a.boxplot(data, labels=labels, patch_artist=True, widths=.55)
    for patch, c in zip(bp["boxes"], cols):
        patch.set_facecolor(c); patch.set_alpha(.55)
    for med in bp["medians"]:
        med.set_color("k"); med.set_linewidth(1.6)
    a.set_yticks(yt2); a.set_yticklabels([md(d) for d in yt2])
    a.set_ylabel("최소빙일")
    a.set_title("최근 10년 최적일의 연간 변동\n카라해 표준편차 16.0일 → 달력만으론 부족",
                fontsize=11, pad=9)
    a.grid(alpha=.25, axis="y")
    plt.setp(a.get_xticklabels(), fontsize=9.5)

    plt.tight_layout()
    plt.savefig(os.path.join(FIG, "X_window_shift.png"))
    plt.close()
    print("X_window_shift.png")


if __name__ == "__main__":
    main()
