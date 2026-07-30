"""
AURORA 심층 감사·추가 분석.

기존 산출물을 덮어쓰지 않고 results/deep_analysis/에 별도 저장한다.
핵심 목적:
1) 데이터 품질과 문서상 표본수의 일관성 감사
2) 위험수준·변동을 만드는 성분 분해
3) 출항연기 효과의 분모효과, 꼬리위험, 연도 군집 불확실성 검증
4) 최적 출항일이 아니라 반복 가능한 저위험 '창(window)' 탐색
5) 단기예측이 실제 의사결정에 주는 가치와 연도·구간 안정성 평가
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import HistGradientBoostingRegressor


BASE = Path(__file__).resolve().parent
RESULTS = BASE / "results"
OUT = RESULTS / "deep_analysis"
RNG = np.random.default_rng(20260730)

REGION_KR = {
    "kara": "카라해",
    "laptev": "랍테프해",
    "east_siberian": "동시베리아해",
    "chukchi": "추크치해",
    "ALL": "전체",
}
WEIGHTS = {"ice": 0.35, "wind": 0.20, "wave": 0.25, "cold": 0.10, "fog": 0.10}
S_AMPLIFY = {
    "kara": 1.0,
    "laptev": 1.1845746526301282,
    "east_siberian": 1.0316211724957642,
    "chukchi": 1.453955519273668,
}


def ramp(values: pd.Series, lo: float, hi: float) -> pd.Series:
    """lo에서 0, hi에서 1이 되는 절단 선형 변환."""
    if hi > lo:
        return ((values - lo) / (hi - lo)).clip(0, 1)
    return ((lo - values) / (lo - hi)).clip(0, 1)


def pc7_hazards(df: pd.DataFrame) -> pd.DataFrame:
    """기존 10_risk_index.py와 동일한 PC7 위험 성분을 재현."""
    hazards = pd.DataFrame(index=df.index)
    hazards["ice"] = ramp(df["siconc_p90"], 0.10 / 1.4, 0.80 / 1.4)
    hazards["wind"] = ramp(df["wind_p90"], 5.0, 20.0)
    hazards["wave"] = ramp(
        df["swh_p90"].fillna(df["swh_p90"].median()), 1.0, 5.0
    )
    hazards["cold"] = ramp(df["t2m_min"], 0.0, -20.0)
    hazards["fog"] = ramp(df["dewpoint_spread_mean"], 3.0, 0.5)
    return hazards


def quality_record(
    name: str,
    frame: pd.DataFrame,
    date_col: str | None,
    keys: list[str] | None,
    critical: list[str],
    issue: str = "",
) -> dict:
    missing_critical = int(frame[critical].isna().sum().sum())
    critical_cells = max(len(frame) * len(critical), 1)
    duplicate_keys = int(frame.duplicated(keys).sum()) if keys else 0
    if date_col:
        dates = pd.to_datetime(frame[date_col], errors="coerce")
        date_min = dates.min().strftime("%Y-%m-%d") if dates.notna().any() else ""
        date_max = dates.max().strftime("%Y-%m-%d") if dates.notna().any() else ""
    else:
        date_min = date_max = ""
    return {
        "dataset": name,
        "rows": len(frame),
        "columns": len(frame.columns),
        "date_min": date_min,
        "date_max": date_max,
        "duplicate_keys": duplicate_keys,
        "critical_missing_cells": missing_critical,
        "critical_missing_pct": missing_critical / critical_cells,
        "issue": issue,
    }


def data_quality(
    era5: pd.DataFrame,
    risk: pd.DataFrame,
    nsidc: pd.DataFrame,
    araon: pd.DataFrame,
    matched: pd.DataFrame,
    transit: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    records = [
        quality_record(
            "ERA5 일별 피처",
            era5,
            "date",
            ["region", "date"],
            [
                "siconc_p90",
                "t2m_mean",
                "t2m_min",
                "wind_p90",
                "swh_p90",
                "dewpoint_spread_mean",
            ],
        ),
        quality_record(
            "일별 위험지수",
            risk,
            "date",
            ["region", "date"],
            ["R_PC6", "R_PC7", "P_PC6", "P_PC7"],
        ),
        quality_record(
            "NSIDC 일별 해빙",
            nsidc,
            "date",
            ["sea", "date"],
            ["extent_km2"],
        ),
        quality_record(
            "ARAON 시간별 QC",
            araon,
            "datetime",
            ["cruise_year", "datetime"],
            ["latitude", "longitude", "temp_c", "wspd", "pres_hpa"],
            "센서 결함 연도는 결측 자체가 분석 결과이므로 별도 표에서 진단",
        ),
        quality_record(
            "ARAON-ERA5 매칭",
            matched,
            "datetime",
            ["cruise_year", "datetime"],
            ["t2m_C", "wind_ms", "siconc", "temp_c", "wspd"],
            "ERA5가 2024년까지만 있어 2025 항차는 외부검증 표본에 포함되지 않음",
        ),
        quality_record(
            "NSR 통항",
            transit,
            None,
            ["year"],
            ["transits"],
            "2014·2017·2019~2022 통항 실적 결측",
        ),
    ]

    expected = pd.MultiIndex.from_product(
        [
            sorted(risk["region"].unique()),
            sorted(risk["date"].dt.year.unique()),
        ],
        names=["region", "year"],
    )
    counts = (
        risk.assign(year=risk["date"].dt.year)
        .groupby(["region", "year"])
        .size()
        .reindex(expected, fill_value=0)
        .rename("rows")
        .reset_index()
    )
    counts["expected_rows"] = 123
    counts["complete"] = counts["rows"].eq(counts["expected_rows"])

    araon_year = (
        araon.groupby("cruise_year")
        .agg(
            hourly_rows=("datetime", "size"),
            start=("datetime", "min"),
            end=("datetime", "max"),
            arctic_hours=("latitude", lambda x: int((x >= 65).sum())),
            temp_valid_pct=("temp_c", lambda x: x.notna().mean()),
            wind_valid_pct=("wspd", lambda x: x.notna().mean()),
            pressure_valid_pct=("pres_hpa", lambda x: x.notna().mean()),
            wind_zero_pct=("wspd", lambda x: x.fillna(-1).eq(0).mean()),
        )
        .reset_index()
    )
    araon_year["start"] = araon_year["start"].dt.strftime("%Y-%m-%d")
    araon_year["end"] = araon_year["end"].dt.strftime("%Y-%m-%d")

    matched_counts = (
        matched.groupby(["cruise_year", "era5_region"])
        .agg(
            matched_rows=("datetime", "size"),
            temp_pairs=("temp_c", lambda x: int(x.notna().sum())),
            wind_pairs=("wspd", lambda x: int(x.notna().sum())),
            moving_hours=("sog_ms", lambda x: int((x > 2).sum())),
        )
        .reset_index()
    )
    return pd.DataFrame(records), counts, araon_year.merge(
        matched_counts.groupby("cruise_year").sum(numeric_only=True).reset_index(),
        on="cruise_year",
        how="left",
    )


def raw_file_inventory() -> pd.DataFrame:
    rows = []
    for year in range(2020, 2026):
        candidates = sorted(BASE.parent.glob(f"ARAON_DADIS_WEATHER_ARCTIC_{year}*"))
        folders = [path for path in candidates if path.is_dir()]
        dat_files = []
        for folder in folders:
            dat_files.extend(folder.rglob("*.dat"))
        rows.append(
            {
                "cruise_year": year,
                "source_folders": len(folders),
                "raw_dat_files": len(dat_files),
                "raw_size_gb": sum(path.stat().st_size for path in dat_files) / 1e9,
            }
        )
    return pd.DataFrame(rows)


def risk_driver_analysis(risk: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    hazards = pc7_hazards(risk)
    contributions = hazards.mul(pd.Series(WEIGHTS))
    p_rebuilt = contributions.sum(axis=1)
    max_error = float((p_rebuilt - risk["P_PC7"]).abs().max())
    if max_error > 1e-10:
        raise ValueError(f"PC7 위험 재현 오차가 너무 큼: {max_error}")

    rows = []
    for region in ["ALL", *sorted(risk["region"].unique())]:
        mask = pd.Series(True, index=risk.index) if region == "ALL" else risk["region"].eq(region)
        p = risk.loc[mask, "P_PC7"]
        for component in WEIGHTS:
            c = contributions.loc[mask, component]
            variance_share = (
                WEIGHTS[component]
                * np.cov(hazards.loc[mask, component], p, ddof=1)[0, 1]
                / p.var(ddof=1)
            )
            rows.append(
                {
                    "region": region,
                    "region_kr": REGION_KR[region],
                    "component": component,
                    "mean_component_score": hazards.loc[mask, component].mean(),
                    "mean_weighted_contribution": c.mean(),
                    "mean_share_pct": c.mean() / p.mean(),
                    "variance_share_pct": variance_share,
                    "spearman_to_P": stats.spearmanr(hazards.loc[mask, component], p).statistic,
                }
            )

    region_rows = []
    for region, group in risk.groupby("region"):
        p_mean = group["P_PC7"].mean()
        r_mean = group["R_PC7"].mean()
        region_rows.append(
            {
                "region": region,
                "region_kr": REGION_KR[region],
                "environmental_P_mean": p_mean,
                "loss_multiplier_S": S_AMPLIFY[region],
                "final_R_mean": r_mean,
                "amplification_pct": r_mean / p_mean - 1,
                "risk_rank": 0,
            }
        )
    region_table = pd.DataFrame(region_rows)
    region_table["risk_rank"] = (
        region_table["final_R_mean"].rank(method="min", ascending=False).astype(int)
    )
    return pd.DataFrame(rows), region_table.sort_values("risk_rank")


def delay_pairs(risk: pd.DataFrame, delay: int = 3) -> pd.DataFrame:
    pieces = []
    for region, group in risk.groupby("region"):
        group = group.sort_values("date").reset_index(drop=True)
        future = group["R_PC7"].shift(-delay)
        future_date = group["date"].shift(-delay)
        valid = future.notna() & group["date"].dt.year.eq(future_date.dt.year)
        current = group.loc[valid, "R_PC7"]
        later = future.loc[valid]
        pieces.append(
            pd.DataFrame(
                {
                    "region": region,
                    "year": group.loc[valid, "date"].dt.year.to_numpy(),
                    "month": group.loc[valid, "date"].dt.month.to_numpy(),
                    "date": group.loc[valid, "date"].to_numpy(),
                    "current": current.to_numpy(),
                    "future": later.to_numpy(),
                    "relative_pct": ((later.to_numpy() / current.to_numpy()) - 1) * 100,
                    "log_pct": np.log(later.to_numpy() / current.to_numpy()) * 100,
                    "absolute_change": later.to_numpy() - current.to_numpy(),
                }
            )
        )
    return pd.concat(pieces, ignore_index=True)


def cluster_bootstrap_ci(
    frame: pd.DataFrame,
    value: str,
    cluster_cols: list[str],
    iterations: int = 5000,
) -> tuple[float, float]:
    cluster_values = frame.groupby(cluster_cols)[value].mean().dropna().to_numpy()
    if len(cluster_values) < 2:
        return np.nan, np.nan
    draws = RNG.choice(cluster_values, size=(iterations, len(cluster_values)), replace=True)
    means = draws.mean(axis=1)
    return tuple(np.percentile(means, [2.5, 97.5]))


def delay_robustness(risk: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    pairs = delay_pairs(risk, 3)
    rows = []
    for region in ["ALL", *sorted(pairs["region"].unique())]:
        region_frame = pairs if region == "ALL" else pairs[pairs["region"].eq(region)]
        for month in ["ALL", 7, 8, 9, 10]:
            frame = (
                region_frame
                if month == "ALL"
                else region_frame[region_frame["month"].eq(month)]
            )
            q05, q95 = frame["relative_pct"].quantile([0.05, 0.95])
            wins = frame["relative_pct"].clip(q05, q95)
            # 전체 집계도 연도를 최상위 군집으로 둔다. 같은 해의 네 해역은
            # 공통 대기·해빙장을 공유하므로 독립 군집으로 세지 않는다.
            cluster_cols = ["year"]
            ci_low, ci_high = cluster_bootstrap_ci(frame, "relative_pct", cluster_cols)
            cluster_means = frame.groupby(cluster_cols)["relative_pct"].mean()
            rows.append(
                {
                    "region": region,
                    "region_kr": REGION_KR[region],
                    "month": month,
                    "n_pairs": len(frame),
                    "mean_relative_pct": frame["relative_pct"].mean(),
                    "median_relative_pct": frame["relative_pct"].median(),
                    "winsor_mean_pct": wins.mean(),
                    "mean_log_pct": frame["log_pct"].mean(),
                    "mean_absolute_change": frame["absolute_change"].mean(),
                    "p_worse": frame["relative_pct"].gt(0).mean(),
                    "q10_pct": frame["relative_pct"].quantile(0.10),
                    "q90_pct": frame["relative_pct"].quantile(0.90),
                    "cluster_mean_ci_low": ci_low,
                    "cluster_mean_ci_high": ci_high,
                    "positive_cluster_share": cluster_means.gt(0).mean(),
                    "denominator_sensitive": np.sign(frame["relative_pct"].mean())
                    != np.sign(frame["log_pct"].mean()),
                    "robust_direction": (
                        "증가"
                        if ci_low > 0
                        else "감소"
                        if ci_high < 0
                        else "불확실"
                    ),
                }
            )

    by_year = (
        pairs.groupby(["region", "year", "month"])
        .agg(
            mean_relative_pct=("relative_pct", "mean"),
            median_relative_pct=("relative_pct", "median"),
            p_worse=("relative_pct", lambda x: x.gt(0).mean()),
            n_pairs=("relative_pct", "size"),
        )
        .reset_index()
    )
    return pd.DataFrame(rows), by_year


def wave_imputation_sensitivity(risk: pd.DataFrame) -> pd.DataFrame:
    """결빙기에 결측인 파고 40일의 대체값이 시즌 후반 결론을 바꾸는지 점검."""
    scenarios = {"기준(전체 중앙값)": risk["R_PC7"].copy()}
    base_hazards = pc7_hazards(risk)
    for label, wave_source in {
        "결측=0m": risk["swh_p90"].fillna(0),
        "결측=구간×월 중앙값": risk["swh_p90"].fillna(
            risk.groupby(["region", risk["date"].dt.month])["swh_p90"].transform(
                "median"
            )
        ),
    }.items():
        hazards = base_hazards.copy()
        hazards["wave"] = ramp(wave_source, 1.0, 5.0)
        p_alt = hazards.mul(pd.Series(WEIGHTS)).sum(axis=1)
        scenarios[label] = p_alt * risk["region"].map(S_AMPLIFY)

    rows = []
    for scenario, values in scenarios.items():
        altered = risk.copy()
        altered["R_PC7"] = values
        pairs = delay_pairs(altered, 3)
        for region in ["ALL", *sorted(pairs["region"].unique())]:
            region_frame = pairs if region == "ALL" else pairs[pairs["region"].eq(region)]
            for month in [9, 10]:
                frame = region_frame[region_frame["month"].eq(month)]
                q05, q95 = frame["relative_pct"].quantile([0.05, 0.95])
                ci_low, ci_high = cluster_bootstrap_ci(
                    frame, "relative_pct", ["year"]
                )
                year_means = frame.groupby("year")["relative_pct"].mean()
                rows.append(
                    {
                        "scenario": scenario,
                        "region": region,
                        "region_kr": REGION_KR[region],
                        "month": month,
                        "missing_wave_days": int(risk["swh_p90"].isna().sum()),
                        "mean_relative_pct": frame["relative_pct"].mean(),
                        "median_relative_pct": frame["relative_pct"].median(),
                        "winsor_mean_pct": frame["relative_pct"].clip(q05, q95).mean(),
                        "cluster_ci_low": ci_low,
                        "cluster_ci_high": ci_high,
                        "positive_year_share": year_means.gt(0).mean(),
                        "direction": (
                            "증가"
                            if ci_low > 0
                            else "감소"
                            if ci_high < 0
                            else "불확실"
                        ),
                    }
                )
    return pd.DataFrame(rows)


def longest_window(profile: pd.DataFrame) -> tuple[str, str, int]:
    candidates = profile["candidate"].to_numpy()
    best_start = best_end = -1
    start = -1
    for idx, value in enumerate(np.r_[candidates, False]):
        if value and start < 0:
            start = idx
        elif not value and start >= 0:
            if idx - start > best_end - best_start + 1:
                best_start, best_end = start, idx - 1
            start = -1
    if best_start < 0:
        return "", "", 0
    return (
        profile.iloc[best_start]["mmdd"],
        profile.iloc[best_end]["mmdd"],
        best_end - best_start + 1,
    )


def season_windows(risk: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = risk.copy()
    frame["year"] = frame["date"].dt.year
    frame["mmdd"] = frame["date"].dt.strftime("%m-%d")
    frame["year_median"] = frame.groupby(["region", "year"])["R_PC7"].transform("median")
    frame["below_year_median"] = frame["R_PC7"].lt(frame["year_median"])

    profiles = []
    summaries = []
    for region, group in frame.groupby("region"):
        profile = (
            group.groupby("mmdd")
            .agg(
                risk_mean=("R_PC7", "mean"),
                risk_median=("R_PC7", "median"),
                risk_q25=("R_PC7", lambda x: x.quantile(0.25)),
                risk_q75=("R_PC7", lambda x: x.quantile(0.75)),
                p_below_year_median=("below_year_median", "mean"),
                years=("year", "nunique"),
            )
            .reset_index()
            .sort_values("mmdd")
        )
        threshold = profile["risk_mean"].quantile(0.25)
        profile["candidate"] = profile["risk_mean"].le(threshold) & profile[
            "p_below_year_median"
        ].ge(0.8)
        start, end, days = longest_window(profile)
        if days == 0:
            profile["candidate"] = profile["risk_mean"].le(threshold)
            start, end, days = longest_window(profile)
            criterion = "평균위험 하위 25%(연도 일관성 80% 조건 미충족)"
        else:
            criterion = "평균위험 하위 25% + 10년 중 8년 이상 연도 중앙값 미만"
        best_mean = profile.loc[profile["risk_mean"].idxmin()]
        best_median = profile.loc[profile["risk_median"].idxmin()]
        summaries.append(
            {
                "region": region,
                "region_kr": REGION_KR[region],
                "preferred_start": start,
                "preferred_end": end,
                "window_days": days,
                "criterion": criterion,
                "best_day_by_mean": best_mean["mmdd"],
                "best_mean_risk": best_mean["risk_mean"],
                "best_day_by_median": best_median["mmdd"],
                "best_median_risk": best_median["risk_median"],
                "best_day_year_consistency": best_mean["p_below_year_median"],
            }
        )
        profile.insert(0, "region", region)
        profile.insert(1, "region_kr", REGION_KR[region])
        profiles.append(profile)
    return pd.DataFrame(summaries), pd.concat(profiles, ignore_index=True)


def corridor_window(season_profile: pd.DataFrame) -> pd.DataFrame:
    """네 구간이 동시에 저위험 후보인 가장 긴 공통 창."""
    pivot = season_profile.pivot(index="mmdd", columns="region", values="candidate")
    common = pivot.all(axis=1).rename("candidate").reset_index().sort_values("mmdd")
    start, end, days = longest_window(common)
    corridor_risk = (
        season_profile.groupby("mmdd")["risk_mean"].mean().sort_values()
    )
    return pd.DataFrame(
        [
            {
                "scope": "NSR 4구간 공통",
                "preferred_start": start,
                "preferred_end": end,
                "window_days": days,
                "best_day_by_mean": corridor_risk.index[0],
                "best_corridor_mean_risk": corridor_risk.iloc[0],
                "criterion": "각 구간별 저위험 후보일의 교집합",
            }
        ]
    )


def annual_risk_trends(risk: pd.DataFrame) -> pd.DataFrame:
    annual = (
        risk.assign(year=risk["date"].dt.year)
        .groupby(["region", "year"])["R_PC7"]
        .mean()
        .reset_index()
    )
    rows = []
    for region, group in annual.groupby("region"):
        linear = stats.linregress(group["year"], group["R_PC7"])
        sen = stats.theilslopes(group["R_PC7"], group["year"], 0.95)
        rows.append(
            {
                "region": region,
                "region_kr": REGION_KR[region],
                "n_years": len(group),
                "mean_risk": group["R_PC7"].mean(),
                "interannual_cv": group["R_PC7"].std(ddof=1) / group["R_PC7"].mean(),
                "ols_slope_per_year": linear.slope,
                "ols_p_value": linear.pvalue,
                "theil_sen_slope": sen.slope,
                "sen_ci_low": sen.low_slope,
                "sen_ci_high": sen.high_slope,
                "trend_direction": (
                    "감소" if sen.high_slope < 0 else "증가" if sen.low_slope > 0 else "불확실"
                ),
            }
        )
    return pd.DataFrame(rows)


def forecast_value(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = predictions.dropna(
        subset=["y", "y_persist", "y_model", "clim_target", "clim_now"]
    ).copy()
    frame["cluster"] = (
        frame["region"].astype(str) + "-" + frame["year"].astype(int).astype(str)
    )

    def metrics(group: pd.DataFrame) -> dict:
        now = group["y_persist"].to_numpy()
        later = group["y"].to_numpy()
        model_choice_later = group["y_model"].to_numpy() < now
        climate_choice_later = group["clim_target"].to_numpy() < group["clim_now"].to_numpy()
        model_realized = np.where(model_choice_later, later, now)
        climate_realized = np.where(climate_choice_later, later, now)
        oracle = np.minimum(now, later)
        base = now.mean()
        oracle_gain = base - oracle.mean()
        model_gain = base - model_realized.mean()
        correct_direction = model_choice_later == (later < now)
        return {
            "n_decisions": len(group),
            "always_now_risk": base,
            "model_rule_risk": model_realized.mean(),
            "climate_rule_risk": climate_realized.mean(),
            "oracle_risk": oracle.mean(),
            "model_improvement_pct": model_gain / base,
            "climate_improvement_pct": (base - climate_realized.mean()) / base,
            "oracle_improvement_pct": oracle_gain / base,
            "oracle_capture_pct": model_gain / oracle_gain if oracle_gain > 0 else np.nan,
            "direction_accuracy": correct_direction.mean(),
            "mean_regret": (model_realized - oracle).mean(),
            "delay_choice_rate": model_choice_later.mean(),
        }

    overall_rows = []
    stability_rows = []
    for horizon, horizon_frame in frame.groupby("horizon"):
        overall = metrics(horizon_frame)
        region_year_improvements = []
        year_realized = []
        for (region, year), group in horizon_frame.groupby(["region", "year"]):
            row = {
                "horizon": int(horizon),
                "region": region,
                "region_kr": REGION_KR[region],
                "year": int(year),
                **metrics(group),
            }
            stability_rows.append(row)
            region_year_improvements.append(row["model_improvement_pct"])
        for year, group in horizon_frame.groupby("year"):
            year_metrics = metrics(group)
            year_realized.append(
                {"year": int(year), "improvement": year_metrics["model_improvement_pct"]}
            )
        region_year_improvements = np.array(region_year_improvements)
        year_improvements = np.array([row["improvement"] for row in year_realized])
        draws = RNG.choice(
            year_improvements,
            size=(5000, len(year_improvements)),
            replace=True,
        ).mean(axis=1)
        overall_rows.append(
            {
                "horizon": int(horizon),
                **overall,
                "cluster_ci_low": np.percentile(draws, 2.5),
                "cluster_ci_high": np.percentile(draws, 97.5),
                "year_min_improvement_pct": year_improvements.min(),
                "year_max_improvement_pct": year_improvements.max(),
                "positive_year_share": (year_improvements > 0).mean(),
                "positive_region_year_share": (region_year_improvements > 0).mean(),
            }
        )
    return pd.DataFrame(overall_rows), pd.DataFrame(stability_rows)


def build_forecast_features(
    risk: pd.DataFrame, horizon: int, climate: dict[tuple[str, int], float]
) -> pd.DataFrame:
    """19_risk_forecast.py의 정보시점 규칙을 유지한 롤링 검증용 피처."""
    frames = []
    for (region, year), group in risk.groupby(["region", "year"]):
        group = group.sort_values("date").reset_index(drop=True)
        features = pd.DataFrame(
            {"region": region, "year": year, "date": group["date"]}
        )
        for column in [
            "R_PC7",
            "siconc_p90",
            "t2m_mean",
            "wind_p90",
            "swh_p90",
            "dewpoint_spread_mean",
        ]:
            features[column] = group[column]
        for lag in [1, 3, 7]:
            features[f"R_lag{lag}"] = group["R_PC7"].shift(lag)
            features[f"ice_lag{lag}"] = group["siconc_p90"].shift(lag)
        features["R_trend3"] = group["R_PC7"] - group["R_PC7"].shift(3)
        features["ice_trend3"] = group["siconc_p90"] - group["siconc_p90"].shift(3)
        features["R_roll7"] = group["R_PC7"].rolling(7, min_periods=3).mean()
        doy = group["date"].dt.dayofyear
        features["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
        features["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
        features["doy"] = doy
        target_doy = (group["date"] + pd.Timedelta(days=horizon)).dt.dayofyear
        features["clim_target"] = [
            climate.get((region, day), np.nan) for day in target_doy
        ]
        features["clim_now"] = [climate.get((region, day), np.nan) for day in doy]
        features["y"] = group["R_PC7"].shift(-horizon)
        features["y_persist"] = group["R_PC7"]
        frames.append(features)
    return pd.concat(frames, ignore_index=True).dropna(subset=["y"])


def rolling_forecast_backtest(
    risk: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """각 평가연도 직전 데이터만 학습하는 2020~2024 롤링 후향검증."""
    frame = risk.copy()
    frame["year"] = frame["date"].dt.year
    frame["doy"] = frame["date"].dt.dayofyear
    rows = []
    predictions = []
    for test_year in range(2020, 2025):
        train = frame[frame["year"].lt(test_year)]
        climate = train.groupby(["region", "doy"])["R_PC7"].mean().to_dict()
        for horizon in [3, 7]:
            features = build_forecast_features(frame, horizon, climate)
            feature_cols = [
                column
                for column in features.columns
                if column
                not in [
                    "region",
                    "year",
                    "date",
                    "y",
                    "y_persist",
                    "clim_target",
                    "clim_now",
                ]
            ]
            train_features = features[features["year"].lt(test_year)]
            test_features = features[features["year"].eq(test_year)].copy()
            model = HistGradientBoostingRegressor(
                max_iter=400,
                learning_rate=0.05,
                max_depth=6,
                min_samples_leaf=20,
                l2_regularization=1.0,
                random_state=42,
            )
            model.fit(train_features[feature_cols], train_features["y"])
            test_features["y_model"] = model.predict(test_features[feature_cols])
            test_features["horizon"] = horizon
            predictions.append(test_features)

            now = test_features["y_persist"].to_numpy()
            later = test_features["y"].to_numpy()
            predicted = test_features["y_model"].to_numpy()
            chosen = np.where(predicted < now, later, now)
            oracle = np.minimum(now, later)
            rmse_model = np.sqrt(np.mean((predicted - later) ** 2))
            rmse_persist = np.sqrt(np.mean((now - later) ** 2))
            rows.append(
                {
                    "test_year": test_year,
                    "horizon": horizon,
                    "train_year_start": int(train["year"].min()),
                    "train_year_end": test_year - 1,
                    "n_decisions": len(test_features),
                    "rmse_model": rmse_model,
                    "rmse_persistence": rmse_persist,
                    "skill_vs_persistence": 1
                    - (rmse_model**2 / rmse_persist**2),
                    "model_improvement_pct": (now.mean() - chosen.mean()) / now.mean(),
                    "oracle_improvement_pct": (now.mean() - oracle.mean()) / now.mean(),
                    "oracle_capture_pct": (
                        (now.mean() - chosen.mean())
                        / (now.mean() - oracle.mean())
                    ),
                    "direction_accuracy": ((predicted < now) == (later < now)).mean(),
                }
            )

    detail = pd.DataFrame(rows)
    summary = (
        detail.groupby("horizon")
        .agg(
            test_years=("test_year", "nunique"),
            mean_skill_vs_persistence=("skill_vs_persistence", "mean"),
            min_skill_vs_persistence=("skill_vs_persistence", "min"),
            positive_skill_year_share=("skill_vs_persistence", lambda x: x.gt(0).mean()),
            mean_decision_improvement_pct=("model_improvement_pct", "mean"),
            min_decision_improvement_pct=("model_improvement_pct", "min"),
            max_decision_improvement_pct=("model_improvement_pct", "max"),
            positive_decision_year_share=(
                "model_improvement_pct",
                lambda x: x.gt(0).mean(),
            ),
            mean_oracle_capture_pct=("oracle_capture_pct", "mean"),
            mean_direction_accuracy=("direction_accuracy", "mean"),
        )
        .reset_index()
    )
    return detail, summary


def validation_audit(
    matched: pd.DataFrame, validation_metrics: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    coverage = (
        matched.groupby(["cruise_year", "era5_region"])
        .agg(
            matched_rows=("datetime", "size"),
            temperature_pairs=("temp_c", lambda x: int(x.notna().sum())),
            wind_pairs=("wspd", lambda x: int(x.notna().sum())),
        )
        .reset_index()
    )
    checks = pd.DataFrame(
        [
            {
                "check": "확보 항차 수",
                "documented": "6개(2020~2025)",
                "observed": f"{matched['cruise_year'].nunique()}개({matched['cruise_year'].min()}~{matched['cruise_year'].max()})",
                "status": "주의",
                "interpretation": "원자료는 6개지만 ERA5 매칭 검증은 2020~2024의 5개 항차",
            },
            {
                "check": "ERA5 매칭 행",
                "documented": "2,450시간",
                "observed": f"{len(matched):,}행 / 기온 유효쌍 {matched['temp_c'].notna().sum():,}",
                "status": "정정",
                "interpretation": "2,450은 전체 매칭 행이 아니라 기온 유효쌍 수",
            },
            {
                "check": "구간별 매칭 합계",
                "documented": "추크치 1,372 + 동시베리아 1,250 = 2,622",
                "observed": ", ".join(
                    f"{REGION_KR.get(k, k)} {v:,}"
                    for k, v in matched["era5_region"].value_counts().items()
                ),
                "status": "정정",
                "interpretation": "문서의 구간별 수치는 전체/유효쌍 기준이 섞였을 가능성",
            },
            {
                "check": "기온 검증 연도 수",
                "documented": "6개 항차 전부",
                "observed": f"{validation_metrics[validation_metrics['변수'].eq('기온(°C)')]['연도'].nunique()}개 연도",
                "status": "정정",
                "interpretation": "2025는 ERA5 기간 밖이므로 기온 대조표에 없음",
            },
        ]
    )
    return coverage, checks


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    era5 = pd.read_csv(BASE / "era5_daily_features.csv", parse_dates=["date"])
    risk = pd.read_csv(RESULTS / "C_daily_risk.csv", parse_dates=["date"])
    nsidc = pd.read_csv(BASE / "nsidc_daily_extent.csv", parse_dates=["date"])
    araon = pd.read_csv(BASE / "araon_hourly.csv", parse_dates=["datetime"])
    matched = pd.read_csv(
        RESULTS / "V3_araon_era5_matched.csv", parse_dates=["datetime"]
    )
    transit = pd.read_csv(BASE / "nsr_transit_data.csv")
    predictions = pd.read_csv(RESULTS / "M2_predictions.csv", parse_dates=["date"])
    validation_metrics = pd.read_csv(RESULTS / "V3_validation_metrics.csv")

    quality, completeness, araon_year = data_quality(
        era5, risk, nsidc, araon, matched, transit
    )
    inventory = raw_file_inventory()
    araon_year = inventory.merge(araon_year, on="cruise_year", how="left")
    drivers, regional_risk = risk_driver_analysis(risk)
    delay_summary, delay_by_year = delay_robustness(risk)
    wave_sensitivity = wave_imputation_sensitivity(risk)
    windows, season_profile = season_windows(risk)
    corridor = corridor_window(season_profile)
    trends = annual_risk_trends(risk)
    forecast, forecast_stability = forecast_value(predictions)
    rolling_forecast, rolling_forecast_summary = rolling_forecast_backtest(risk)
    validation_coverage, validation_checks = validation_audit(
        matched, validation_metrics
    )

    outputs = {
        "data_quality.csv": quality,
        "era5_completeness.csv": completeness,
        "araon_year_audit.csv": araon_year,
        "risk_drivers.csv": drivers,
        "regional_risk.csv": regional_risk,
        "delay_robustness.csv": delay_summary,
        "delay_by_year.csv": delay_by_year,
        "wave_imputation_sensitivity.csv": wave_sensitivity,
        "season_windows.csv": windows,
        "season_profile.csv": season_profile,
        "corridor_window.csv": corridor,
        "annual_risk_trends.csv": trends,
        "forecast_value.csv": forecast,
        "forecast_stability.csv": forecast_stability,
        "rolling_forecast_backtest.csv": rolling_forecast,
        "rolling_forecast_summary.csv": rolling_forecast_summary,
        "validation_coverage.csv": validation_coverage,
        "validation_checks.csv": validation_checks,
    }
    for filename, frame in outputs.items():
        frame.to_csv(OUT / filename, index=False)
    workbook_data = {
        filename.removesuffix(".csv"): json.loads(
            frame.to_json(orient="records", force_ascii=False, date_format="iso")
        )
        for filename, frame in outputs.items()
    }
    with open(OUT / "workbook_data.json", "w", encoding="utf-8") as file:
        json.dump(workbook_data, file, ensure_ascii=False)

    overall_drivers = (
        drivers[drivers["region"].eq("ALL")]
        .sort_values("variance_share_pct", ascending=False)
        .reset_index(drop=True)
    )
    late = delay_summary[
        delay_summary["region"].eq("ALL") & delay_summary["month"].isin([9, 10])
    ].sort_values("month")
    summary = {
        "data_quality": {
            "era5_complete_region_year_cells": int(completeness["complete"].sum()),
            "era5_total_region_year_cells": len(completeness),
            "araon_raw_dat_files": int(inventory["raw_dat_files"].sum()),
            "araon_hourly_rows": len(araon),
            "matched_rows": len(matched),
            "temperature_pairs": int(matched["temp_c"].notna().sum()),
            "matched_cruises": int(matched["cruise_year"].nunique()),
            "transit_missing_years": transit.loc[
                transit["transits"].isna(), "year"
            ].astype(int).tolist(),
        },
        "top_variance_driver": overall_drivers.loc[0, "component"],
        "top_variance_driver_share": float(
            overall_drivers.loc[0, "variance_share_pct"]
        ),
        "late_delay": late[
            [
                "month",
                "mean_relative_pct",
                "median_relative_pct",
                "cluster_mean_ci_low",
                "cluster_mean_ci_high",
                "positive_cluster_share",
                "denominator_sensitive",
            ]
        ].to_dict(orient="records"),
        "wave_imputation_sensitivity": wave_sensitivity[
            wave_sensitivity["region"].eq("ALL")
        ].to_dict(orient="records"),
        "preferred_windows": windows[
            ["region_kr", "preferred_start", "preferred_end", "window_days"]
        ].to_dict(orient="records"),
        "corridor_window": corridor.to_dict(orient="records"),
        "forecast_value": forecast.to_dict(orient="records"),
        "rolling_forecast_summary": rolling_forecast_summary.to_dict(
            orient="records"
        ),
        "validation_corrections": validation_checks.to_dict(orient="records"),
    }
    with open(OUT / "summary.json", "w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)

    print("AURORA 심층 분석 완료")
    print(f"- 결과 디렉터리: {OUT}")
    print(
        f"- ERA5 완전 셀: {completeness['complete'].sum()}/{len(completeness)} "
        f"(각 구간·연도 123일)"
    )
    print(
        f"- ARAON 원자료 파일: {inventory['raw_dat_files'].sum():,}, "
        f"시간별 QC: {len(araon):,}, ERA5 매칭: {len(matched):,}"
    )
    print(
        f"- 최대 변동 기여 성분: {overall_drivers.loc[0, 'component']} "
        f"({overall_drivers.loc[0, 'variance_share_pct']:.1%})"
    )
    for row in late.itertuples():
        print(
            f"- {row.month}월 3일 연기: 평균 {row.mean_relative_pct:+.1f}%, "
            f"연도·구간 군집 95% CI [{row.cluster_mean_ci_low:+.1f}, "
            f"{row.cluster_mean_ci_high:+.1f}]%, 방향={row.robust_direction}"
        )
    for row in forecast.itertuples():
        print(
            f"- {row.horizon}일 예측 규칙: 실현위험 {row.model_improvement_pct:.1%} 개선, "
            f"양(+) 지역×연도 비율 {row.positive_region_year_share:.1%}"
        )


if __name__ == "__main__":
    main()
