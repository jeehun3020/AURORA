"""
ERA5 netCDF → NSR 구간별 일별 기상 피처 CSV
AURORA 프로젝트 — 위험지수 입력변수 생성

입력: era5_data/era5_{region}_{year}_{month}/  (oper + wave 2개 스트림)
출력: era5_daily_features.csv
  [date, region, siconc_mean, siconc_p90, t2m_mean, t2m_min,
   wind_mean, wind_p90, swh_mean, swh_p90, dewpoint_spread_mean]

설계 메모:
- 위험은 평균이 아니라 극값이 만든다. 공간 평균만 쓰면 구간 내 위험한 지점이 지워지므로
  각 시각마다 공간 p90(상위 10%)도 함께 계산한다.
- 육지 격자는 제외해야 한다. ERA5에서 siconc는 육지에서 NaN이므로 이를 해양 마스크로 사용.
- dewpoint spread(t2m - d2m)는 작을수록 안개 가능성이 높다. 가시거리 프록시로 사용
  (ERA5 single-levels의 visibility 변수는 MARS에서 ambiguous 에러가 나 사용 불가).
"""
import glob
import os

import numpy as np
import pandas as pd
import xarray as xr

BASE = os.path.dirname(__file__)
SRC = os.path.join(BASE, "era5_data")
OUT = os.path.join(BASE, "era5_daily_features.csv")


def spatial_stats(da, ocean_mask=None):
    """각 시각별 공간 평균/p90/최솟값. ocean_mask 주면 해양 격자만 집계."""
    if ocean_mask is not None:
        da = da.where(ocean_mask)
    dims = [d for d in da.dims if d != "valid_time"]
    return (
        da.mean(dim=dims, skipna=True),
        da.quantile(0.9, dim=dims, skipna=True),
        da.min(dim=dims, skipna=True),
    )


def process_dir(d):
    region, year, month = os.path.basename(d).replace("era5_", "").rsplit("_", 2)

    oper = xr.open_dataset(os.path.join(d, "data_stream-oper_stepType-instant.nc"))
    wave_path = os.path.join(d, "data_stream-wave_stepType-instant.nc")

    # siconc는 육지에서 NaN → 해양 마스크. 항행시즌엔 얼음이 다 녹은 격자도 있으므로
    # 시간축 전체에서 한 번이라도 유효한 격자를 해양으로 본다.
    ocean = oper["siconc"].notnull().any(dim="valid_time")

    si_mean, si_p90, _ = spatial_stats(oper["siconc"], ocean)
    t2_mean, _, t2_min = spatial_stats(oper["t2m"], ocean)
    wind = np.sqrt(oper["u10"] ** 2 + oper["v10"] ** 2)
    w_mean, w_p90, _ = spatial_stats(wind, ocean)
    spread = oper["t2m"] - oper["d2m"]
    sp_mean, _, _ = spatial_stats(spread, ocean)

    df = pd.DataFrame({
        "valid_time": oper["valid_time"].values,
        "siconc_mean": si_mean.values, "siconc_p90": si_p90.values,
        "t2m_mean": t2_mean.values - 273.15, "t2m_min": t2_min.values - 273.15,
        "wind_mean": w_mean.values, "wind_p90": w_p90.values,
        "dewpoint_spread_mean": sp_mean.values,
    })
    oper.close()

    if os.path.exists(wave_path):
        wv = xr.open_dataset(wave_path)
        sw_mean, sw_p90, _ = spatial_stats(wv["swh"])
        wdf = pd.DataFrame({
            "valid_time": wv["valid_time"].values,
            "swh_mean": sw_mean.values, "swh_p90": sw_p90.values,
        })
        wv.close()
        df = df.merge(wdf, on="valid_time", how="left")
    else:
        df["swh_mean"] = np.nan
        df["swh_p90"] = np.nan

    # 6시간 간격 → 일별. 극값 변수는 일 최대, 상태 변수는 일 평균으로 집계.
    df["date"] = pd.to_datetime(df["valid_time"]).dt.date
    daily = df.groupby("date").agg(
        siconc_mean=("siconc_mean", "mean"), siconc_p90=("siconc_p90", "max"),
        t2m_mean=("t2m_mean", "mean"), t2m_min=("t2m_min", "min"),
        wind_mean=("wind_mean", "mean"), wind_p90=("wind_p90", "max"),
        swh_mean=("swh_mean", "mean"), swh_p90=("swh_p90", "max"),
        dewpoint_spread_mean=("dewpoint_spread_mean", "mean"),
    ).reset_index()
    daily["region"] = region
    return daily


def main():
    dirs = sorted(glob.glob(os.path.join(SRC, "era5_*")))
    dirs = [d for d in dirs if os.path.isdir(d)]
    print(f"처리 대상 {len(dirs)}개 폴더")

    frames = []
    for i, d in enumerate(dirs, 1):
        try:
            frames.append(process_dir(d))
        except Exception as e:
            print(f"[에러] {os.path.basename(d)}: {e}")
        if i % 20 == 0:
            print(f"  {i}/{len(dirs)}")

    out = pd.concat(frames, ignore_index=True)
    out = out.sort_values(["region", "date"]).reset_index(drop=True)
    out.to_csv(OUT, index=False)

    print(f"\n저장: {OUT}  ({len(out):,}행)")
    print(out.groupby("region")["date"].agg(["min", "max", "count"]))


if __name__ == "__main__":
    main()
