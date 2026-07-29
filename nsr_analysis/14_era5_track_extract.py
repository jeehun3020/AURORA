"""
ERA5 항적 지점추출 — ARAON 선상관측 검증용 사전 준비
AURORA 프로젝트

목적: 선박 항적(시각, 위도, 경도) 각 점에 대해 가장 가까운 ERA5 격자·시각의 값을 뽑는다.
      기존 07_era5_aggregate.py는 구간 평균으로 축약하므로 지점 대조가 불가능하다.

KPDC ARAON 데이터 승인 대기 중이므로, ERA5 쪽 로직만 먼저 완성하고
합성 항적으로 검증해 둔다. 실제 CSV 도착 시 컬럼 매핑만 하면 된다.

사용법:
  python 14_era5_track_extract.py --selftest
  python 14_era5_track_extract.py --track araon_2024.csv --out matched.csv
"""
import argparse
import glob
import os

import numpy as np
import pandas as pd
import xarray as xr

BASE = os.path.dirname(__file__)
SRC = os.path.join(BASE, "era5_data")

# 경도 표기: ERA5 다운로드 시 추크치해는 180~205로 요청했으므로 해당 파일의 경도축은
# 음수(-180~-155)로 저장돼 있을 수 있다. 항적 경도를 파일 축에 맞춰 변환해야 한다.


def load_region_dataset(region, year, month):
    d = os.path.join(SRC, f"era5_{region}_{year}_{month:02d}")
    p = os.path.join(d, "data_stream-oper_stepType-instant.nc")
    if not os.path.exists(p):
        return None
    return xr.open_dataset(p)


def _align_lon(lon_query, lon_axis):
    """항적 경도를 ERA5 파일의 경도축 표기(-180~180 또는 0~360)에 맞춘다."""
    axis_has_negative = float(np.min(lon_axis)) < 0
    lon = np.asarray(lon_query, dtype=float)
    if axis_has_negative:
        return np.where(lon > 180, lon - 360, lon)
    return np.where(lon < 0, lon + 360, lon)


def extract_track(track, regions=("kara", "laptev", "east_siberian", "chukchi")):
    """
    track: DataFrame[datetime, latitude, longitude]
    반환: track + ERA5 최근접 격자값(t2m_C, wind_ms, siconc, d2m_C, msl_hPa 가능시)

    각 관측점을 해당 연-월의 구간 파일에서 찾는다. 한 점이 여러 구간 박스에 걸칠 수 있으므로
    격자 중심까지 거리가 가장 가까운 구간을 채택한다.
    """
    track = track.copy().reset_index(drop=True)
    track["datetime"] = pd.to_datetime(track["datetime"])
    out = {c: np.full(len(track), np.nan) for c in
           ["t2m_C", "wind_ms", "siconc", "d2m_C", "era5_lat", "era5_lon", "era5_region"]}
    out["era5_region"] = np.array([None] * len(track), dtype=object)

    for (year, month), grp in track.groupby([track["datetime"].dt.year,
                                             track["datetime"].dt.month]):
        best_dist = np.full(len(grp), np.inf)
        for region in regions:
            ds = load_region_dataset(region, year, month)
            if ds is None:
                continue
            lat_ax = ds["latitude"].values
            lon_ax = ds["longitude"].values
            lonq = _align_lon(grp["longitude"].values, lon_ax)
            latq = grp["latitude"].values

            # 박스 밖 점은 건너뛴다. sel(nearest)는 범위를 벗어나도 경계값을 반환하므로
            # 거리 검사를 직접 해야 잘못된 매칭을 막을 수 있다.
            inside = ((latq >= lat_ax.min()) & (latq <= lat_ax.max()) &
                      (lonq >= lon_ax.min()) & (lonq <= lon_ax.max()))
            if not inside.any():
                ds.close()
                continue

            sub = ds.sel(
                latitude=xr.DataArray(latq, dims="pt"),
                longitude=xr.DataArray(lonq, dims="pt"),
                valid_time=xr.DataArray(grp["datetime"].values, dims="pt"),
                method="nearest",
            )
            glat = sub["latitude"].values
            glon = sub["longitude"].values
            dist = np.hypot(glat - latq, (glon - lonq) * np.cos(np.radians(latq)))
            dist = np.where(inside, dist, np.inf)

            better = dist < best_dist
            if better.any():
                idx = grp.index.values[better]
                best_dist[better] = dist[better]
                u = sub["u10"].values[better]
                v = sub["v10"].values[better]
                out["t2m_C"][idx] = sub["t2m"].values[better] - 273.15
                out["d2m_C"][idx] = sub["d2m"].values[better] - 273.15
                out["wind_ms"][idx] = np.sqrt(u ** 2 + v ** 2)
                out["siconc"][idx] = sub["siconc"].values[better]
                out["era5_lat"][idx] = glat[better]
                out["era5_lon"][idx] = glon[better]
                out["era5_region"][idx] = region
            ds.close()

    for k, v in out.items():
        track[k] = v
    return track


def selftest():
    """합성 항적으로 추출 로직 검증. ARAON 실제 항로를 모사한 좌표를 사용."""
    print("=" * 72)
    print("ERA5 항적추출 자체검증 — 합성 항적 (아라온 북극항해 모사)")
    print("=" * 72)

    # 2024년 8월, 추크치해 -> 동시베리아해 방향 항적을 6시간 간격으로 생성
    t = pd.date_range("2024-08-05", "2024-08-20", freq="6h")
    n = len(t)
    track = pd.DataFrame({
        "datetime": t,
        "latitude": np.linspace(70.5, 74.5, n),
        "longitude": np.linspace(-168.0, 165.0 - 360, n),  # -168 -> -195(=165E)
    })
    track["longitude"] = np.where(track["longitude"] < -180,
                                  track["longitude"] + 360, track["longitude"])

    res = extract_track(track)
    matched = res["t2m_C"].notna().sum()
    print(f"\n관측점 {n}개 중 매칭 {matched}개 ({matched/n:.0%})")

    if matched == 0:
        print("매칭 0건 — 좌표 정렬 로직 점검 필요")
        return

    print(f"\n구간별 매칭 분포:")
    print(res["era5_region"].value_counts().to_string())

    # 이격거리는 경도 표기 규약(-180~180 vs 0~360)을 맞춘 뒤 계산해야 한다.
    # 정렬 없이 빼면 360도 차이가 나 진단 자체가 무의미해진다.
    dlon = (res["era5_lon"].values - res["longitude"].values + 180) % 360 - 180
    dlat = res["era5_lat"].values - res["latitude"].values
    gap = np.hypot(dlat, dlon * np.cos(np.radians(res["latitude"].values)))
    print(f"\n격자 이격거리: 최대 {np.nanmax(gap):.3f}도, 중앙값 {np.nanmedian(gap):.3f}도")
    print(f"  (ERA5 해상도 0.25도 → 0.2도 이하여야 정상)")
    if np.nanmax(gap) > 0.2:
        print(f"  ⚠️ 이격 과대 — 좌표 정렬 오류 가능")

    print(f"\n추출값 요약:")
    print(res[["t2m_C", "wind_ms", "siconc", "d2m_C"]].describe().round(2).to_string())

    # 물리 타당성: 8월 북극해 표층기온은 대략 -5~+10도, 풍속 0~25 m/s
    ok = (res["t2m_C"].between(-15, 15).all() and
          res["wind_ms"].between(0, 30).all() and
          res["siconc"].between(0, 1).all() and
          (res["d2m_C"] <= res["t2m_C"] + 0.01).all())  # 이슬점은 기온을 넘을 수 없다
    print(f"물리 범위 검사: {'통과' if ok else '실패 — 값 확인 필요'}")
    print(f"격자 정렬 검사: {'통과' if np.nanmax(gap) <= 0.2 else '실패'}")
    print("\n실제 ARAON CSV 도착 시 컬럼 매핑만 하면 즉시 대조 가능.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--track", help="항적 CSV (datetime, latitude, longitude)")
    ap.add_argument("--out", default="era5_matched.csv")
    a = ap.parse_args()

    if a.selftest or not a.track:
        selftest()
        return

    track = pd.read_csv(a.track)
    res = extract_track(track)
    res.to_csv(a.out, index=False)
    print(f"저장: {a.out} ({res['t2m_C'].notna().sum()}/{len(res)} 매칭)")


if __name__ == "__main__":
    main()
