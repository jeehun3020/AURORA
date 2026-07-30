"""
예측모델 — 구간별 위험지수 단기예측 + 출항 의사결정 후향검증
AURORA 프로젝트

발견 4는 "출항을 늦출지"가 위험을 크게 바꾼다는 것이었다. 그러나 실제 운항자는
미래 위험을 모른 채 결정해야 한다. 따라서 물어야 할 진짜 질문은 이것이다.

  예측 가능한 만큼만 알고 결정해도, 실제로 위험이 줄어드는가?

구성:
  1) 예측: t 시점 정보로 t+h 시점 위험지수 예측 (h=3, 7일)
  2) 베이스라인: 지속성(오늘 값 유지), 기후값(학습기간 일자별 평균)
     — 베이스라인을 못 이기는 모델은 쓸모가 없다
  3) 후향검증: 예측을 실제 출항 의사결정에 적용했을 때 실현위험이 낮아지는가

분할: 학습 2015~2021, 검증 2022~2024 (시간순 분할, 미래 정보 누설 없음)
기후값은 학습기간만으로 산출한다.

주의: 목표변수인 위험지수 자체가 잠정 가중치의 산물이다. 따라서 아래 결과는
     "위험지수를 예측할 수 있는가"이지 "위험을 예측할 수 있는가"가 아니다.
     다만 지수의 주성분인 해빙·기온은 §검증에서 외부 관측과 일치함을 확인했다.
"""
import os

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

BASE = os.path.dirname(__file__)
OUT_DIR = os.path.join(BASE, "results")

HORIZONS = [3, 7]
TRAIN_YEARS = range(2015, 2022)
TEST_YEARS = range(2022, 2025)
REGION_KR = {"kara": "카라해", "laptev": "랍테프해",
             "east_siberian": "동시베리아해", "chukchi": "추크치해"}


def build_features(df, horizon, clim):
    """t 시점까지의 정보만으로 특징 구성. 미래 정보는 절대 넣지 않는다."""
    out = []
    for (reg, yr), g in df.groupby(["region", "year"]):
        g = g.sort_values("date").reset_index(drop=True)
        f = pd.DataFrame({"region": reg, "year": yr, "date": g["date"]})

        for c in ["R_PC7", "siconc_p90", "t2m_mean", "wind_p90", "swh_p90",
                  "dewpoint_spread_mean"]:
            f[c] = g[c]
        # 과거 지연값과 변화율 — 추세 정보
        for lag in [1, 3, 7]:
            f[f"R_lag{lag}"] = g["R_PC7"].shift(lag)
            f[f"ice_lag{lag}"] = g["siconc_p90"].shift(lag)
        f["R_trend3"] = g["R_PC7"] - g["R_PC7"].shift(3)
        f["ice_trend3"] = g["siconc_p90"] - g["siconc_p90"].shift(3)
        f["R_roll7"] = g["R_PC7"].rolling(7, min_periods=3).mean()

        doy = g["date"].dt.dayofyear
        f["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
        f["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
        f["doy"] = doy

        # 목표시점의 기후값 — 학습기간만으로 산출했으므로 누설 아님
        tgt_doy = (g["date"] + pd.Timedelta(days=horizon)).dt.dayofyear
        f["clim_target"] = [clim.get((reg, d), np.nan) for d in tgt_doy]
        f["clim_now"] = [clim.get((reg, d), np.nan) for d in doy]

        # 목표: h일 후 위험. 같은 시즌 안에서만 유효
        f["y"] = g["R_PC7"].shift(-horizon)
        f["y_persist"] = g["R_PC7"]          # 베이스라인1: 오늘 값 유지
        f["y_clim"] = f["clim_target"]        # 베이스라인2: 기후값
        out.append(f)
    return pd.concat(out, ignore_index=True).dropna(subset=["y"])


def skill(pred, truth, ref):
    """기준모형 대비 기술점수. 1이면 완벽, 0이면 기준과 동등, 음수면 기준보다 나쁨."""
    mse_p = np.mean((pred - truth) ** 2)
    mse_r = np.mean((ref - truth) ** 2)
    return 1 - mse_p / mse_r


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    df = pd.read_csv(os.path.join(OUT_DIR, "C_daily_risk.csv"), parse_dates=["date"])
    df["year"] = df["date"].dt.year
    df["doy"] = df["date"].dt.dayofyear

    print("=" * 84)
    print("예측모델 — 구간별 위험지수 단기예측 및 출항 의사결정 후향검증")
    print("=" * 84)
    print(f"\n학습 {TRAIN_YEARS.start}~{TRAIN_YEARS.stop-1} / 검증 {TEST_YEARS.start}~{TEST_YEARS.stop-1} (시간순 분할)")

    # 기후값은 학습기간만으로 (검증기간 정보 누설 방지)
    tr_mask = df["year"].isin(TRAIN_YEARS)
    clim = df[tr_mask].groupby(["region", "doy"])["R_PC7"].mean().to_dict()

    all_metrics, all_preds = [], []
    for h in HORIZONS:
        data = build_features(df, h, clim)
        feats = [c for c in data.columns
                 if c not in ["region", "year", "date", "y", "y_persist", "y_clim"]]
        tr = data[data["year"].isin(TRAIN_YEARS)]
        te = data[data["year"].isin(TEST_YEARS)].copy()

        model = HistGradientBoostingRegressor(
            max_iter=400, learning_rate=0.05, max_depth=6,
            min_samples_leaf=20, l2_regularization=1.0, random_state=42)
        model.fit(tr[feats], tr["y"])
        te["y_model"] = model.predict(te[feats])

        print(f"\n\n[예측 성능 — {h}일 후]  학습 {len(tr):,} / 검증 {len(te):,}")
        print(f"  {'방법':<16}{'MAE':>9}{'RMSE':>9}{'지속성대비 skill':>18}{'기후값대비 skill':>18}")
        for name, col in [("지속성(오늘값)", "y_persist"), ("기후값", "y_clim"),
                          ("모델", "y_model")]:
            p = te[col].values
            y = te["y"].values
            m = ~np.isnan(p)
            mae = mean_absolute_error(y[m], p[m])
            rmse = float(np.sqrt(np.mean((p[m] - y[m]) ** 2)))
            s_p = skill(p[m], y[m], te["y_persist"].values[m])
            s_c = skill(p[m], y[m], te["y_clim"].values[m])
            print(f"  {name:<16}{mae:>9.4f}{rmse:>9.4f}{s_p:>18.3f}{s_c:>18.3f}")
            all_metrics.append({"horizon": h, "method": name, "MAE": mae, "RMSE": rmse,
                                "skill_vs_persist": s_p, "skill_vs_clim": s_c})

        # 구간별 성능
        print(f"\n  구간별 모델 MAE ({h}일):")
        for reg, g in te.groupby("region"):
            mp = mean_absolute_error(g["y"], g["y_model"])
            mper = mean_absolute_error(g["y"], g["y_persist"])
            print(f"    {REGION_KR[reg]:<14} 모델 {mp:.4f} / 지속성 {mper:.4f}"
                  f"  개선 {100*(1-mp/mper):+.1f}%")

        te["horizon"] = h
        all_preds.append(te)

    pd.DataFrame(all_metrics).to_csv(os.path.join(OUT_DIR, "M1_forecast_skill.csv"), index=False)
    preds = pd.concat(all_preds, ignore_index=True)
    preds.to_csv(os.path.join(OUT_DIR, "M2_predictions.csv"), index=False)

    # ---------- 의사결정 후향검증 ----------
    print("\n\n" + "=" * 84)
    print("출항 의사결정 후향검증 — 예측을 쓰면 실제로 위험이 줄어드는가")
    print("=" * 84)
    print("\n상황: 출항 예정일 t. '지금 출항' 또는 'h일 연기' 중 택일.")
    print("      실현위험은 실제 출항일의 위험지수. 낮을수록 좋다.\n")

    for h in HORIZONS:
        te = preds[preds["horizon"] == h].copy()
        te = te.dropna(subset=["y", "y_persist", "y_clim", "y_model"])
        now, later = te["y_persist"].values, te["y"].values

        rules = {
            "항상 지금 출항": now,
            "항상 연기": later,
            "기후값 규칙": np.where(te["clim_target"].values < te["clim_now"].values, later, now),
            "모델 규칙": np.where(te["y_model"].values < now, later, now),
            "완전예지(상한)": np.minimum(now, later),
        }
        base = rules["항상 지금 출항"].mean()
        print(f"[{h}일 연기 의사결정]  n={len(te):,}")
        print(f"  {'규칙':<18}{'평균 실현위험':>14}{'개선율':>10}{'상한대비 달성률':>16}")
        oracle_gain = base - rules["완전예지(상한)"].mean()
        for name, r in rules.items():
            v = r.mean()
            imp = (base - v) / base * 100
            cap = (base - v) / oracle_gain * 100 if oracle_gain > 0 else np.nan
            print(f"  {name:<18}{v:>14.4f}{imp:>9.1f}%{cap:>15.1f}%")
        print()

    print("해석 지침: '모델 규칙'이 '기후값 규칙'을 못 이기면, 예측모델을 쓸 이유가 없다.")
    print("           달력만 보고 결정하는 것과 같기 때문이다.")
    print(f"\n저장: {OUT_DIR}/M1_forecast_skill.csv, M2_predictions.csv")


if __name__ == "__main__":
    main()
