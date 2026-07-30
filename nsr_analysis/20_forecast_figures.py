"""
예측모델·의사결정 후향검증 그림
AURORA 프로젝트
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = os.path.dirname(__file__)
RES = os.path.join(BASE, "results")
FIG = os.path.join(BASE, "figures")

plt.rcParams["font.family"] = "AppleGothic"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 130

REGION_KR = {"kara": "카라해", "laptev": "랍테프해",
             "east_siberian": "동시베리아해", "chukchi": "추크치해"}


def main():
    os.makedirs(FIG, exist_ok=True)
    sk = pd.read_csv(os.path.join(RES, "M1_forecast_skill.csv"))
    pr = pd.read_csv(os.path.join(RES, "M2_predictions.csv"), parse_dates=["date"])

    fig, ax = plt.subplots(2, 2, figsize=(13.5, 9.6))

    # (1) 베이스라인 대비 예측 성능
    a = ax[0, 0]
    hs = sorted(sk["horizon"].unique())
    meth = ["지속성(오늘값)", "기후값", "모델"]
    col = {"지속성(오늘값)": "#8899A6", "기후값": "#F18F01", "모델": "#2E86AB"}
    x = np.arange(len(hs)); w = .26
    for i, m in enumerate(meth):
        v = [sk[(sk.horizon == h) & (sk.method == m)]["MAE"].iloc[0] for h in hs]
        b = a.bar(x + (i - 1) * w, v, w, label=m, color=col[m])
        for xi, vi in zip(x + (i - 1) * w, v):
            a.text(xi, vi + .002, f"{vi:.3f}", ha="center", fontsize=8)
    a.set_xticks(x); a.set_xticklabels([f"{h}일 후" for h in hs])
    a.set_ylabel("MAE (위험지수 단위)")
    a.set_title("예측 성능 — 두 베이스라인을 모두 이긴다\n"
                "지속성 대비 skill 0.26(3일)·0.35(7일)", fontsize=11, pad=9)
    a.legend(fontsize=9); a.grid(alpha=.25, axis="y")

    # (2) 예측 대 실제
    a = ax[0, 1]
    g = pr[pr.horizon == 3]
    for reg, gg in g.groupby("region"):
        a.scatter(gg["y"], gg["y_model"], s=5, alpha=.35, label=REGION_KR[reg])
    lim = [.15, .95]
    a.plot(lim, lim, "k--", lw=1.1)
    a.set_xlim(lim); a.set_ylim(lim)
    a.set_xlabel("실제 위험지수 (3일 후)"); a.set_ylabel("모델 예측")
    a.set_title("3일 후 예측 정확도 (검증기간 2022~2024)\n"
                "학습에 쓰이지 않은 연도", fontsize=11, pad=9)
    a.legend(fontsize=8, markerscale=2); a.grid(alpha=.25)

    # (3) 의사결정 후향검증 — 완전예지 대비 달성률
    a = ax[1, 0]
    rules = ["항상 연기", "기후값 규칙", "모델 규칙", "완전예지(상한)"]
    rc = {"항상 연기": "#C1440E", "기후값 규칙": "#F18F01",
          "모델 규칙": "#2E86AB", "완전예지(상한)": "#3B7A57"}
    vals = {h: {} for h in hs}
    for h in hs:
        t = pr[pr.horizon == h].dropna(subset=["y", "y_persist", "y_model", "clim_target", "clim_now"])
        now, later = t["y_persist"].values, t["y"].values
        base = now.mean()
        oracle = base - np.minimum(now, later).mean()
        r = {"항상 연기": later.mean(),
             "기후값 규칙": np.where(t["clim_target"].values < t["clim_now"].values, later, now).mean(),
             "모델 규칙": np.where(t["y_model"].values < now, later, now).mean(),
             "완전예지(상한)": np.minimum(now, later).mean()}
        vals[h] = {k: (base - v) / oracle * 100 for k, v in r.items()}
    x = np.arange(len(hs)); w = .2
    for i, k in enumerate(rules):
        v = [vals[h][k] for h in hs]
        a.bar(x + (i - 1.5) * w, v, w, label=k, color=rc[k])
        for xi, vi in zip(x + (i - 1.5) * w, v):
            a.text(xi, vi + 1.5, f"{vi:.0f}%", ha="center", fontsize=8)
    a.axhline(0, color="k", lw=1)
    a.set_xticks(x); a.set_xticklabels([f"{h}일 연기 판단" for h in hs])
    a.set_ylabel("완전예지 대비 달성률 (%)")
    a.set_title("출항 의사결정 후향검증\n모델이 이론적 최대이득의 55~66%를 실현",
                fontsize=11, pad=9)
    a.legend(fontsize=8.5, loc="upper left"); a.grid(alpha=.25, axis="y")

    # (4) 사례 시계열
    a = ax[1, 1]
    s = pr[(pr.horizon == 3) & (pr.region == "chukchi") & (pr.year == 2023)].sort_values("date")
    a.plot(s["date"], s["y"], "-", lw=2, color="#333", label="실제 (3일 후)")
    a.plot(s["date"], s["y_model"], "-", lw=1.6, color="#2E86AB", label="모델 예측")
    a.plot(s["date"], s["y_persist"], "--", lw=1.2, color="#8899A6", label="지속성 베이스라인")
    a.set_ylabel("위험지수"); a.set_title("사례 — 추크치해 2023 항행시즌\n모델이 계절 전환을 따라간다",
                                       fontsize=11, pad=9)
    a.legend(fontsize=8.5); a.grid(alpha=.25)
    plt.setp(a.get_xticklabels(), rotation=25, ha="right")

    plt.tight_layout()
    plt.savefig(os.path.join(FIG, "M_forecast_backtest.png"))
    plt.close()
    print("M_forecast_backtest.png")


if __name__ == "__main__":
    main()
