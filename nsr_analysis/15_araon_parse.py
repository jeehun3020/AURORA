"""
KPDC ARAON DaDiS 선상 기상관측 파서
AURORA 프로젝트 — ERA5 in-situ 검증용

원자료: WT-YYYYMMDDHHMM.dat, 1초 간격, 파일당 3,600행
  컬럼: UTC Date, UTC Time, Latitude, N/S, Longitude, E/W, 일사량, 기온, 습도,
        풍속, 풍향, 전압, 기압, Heading, N/S, 위도, E/W, 경도
  ※ 헤더는 18개 필드로 적혀 있으나 'Speed'/'Course'는 실제 데이터에 없다.
    데이터 14~17번 필드는 두 번째 GPS의 (N/S, 위도, E/W, 경도)다.
    따라서 선속·침로는 GPS 좌표에서 직접 유도해야 한다.

좌표 형식: DDMM.mmmmm (예: 3728.09908 = 37도 28.09908분 = 37.4683도)

QC 방침:
  센서 결함이 실제로 존재한다(2024년 기압은 전량 500.00 고정, 풍속은 상한 절단 의심).
  결함값을 평균에 섞으면 검증이 아니라 오류가 되므로, 물리적으로 불가능한 값은
  집계 전에 제거하고 제거율 자체를 품질지표로 함께 보고한다.
"""
import argparse
import glob
import os

import numpy as np
import pandas as pd

BASE = os.path.dirname(__file__)
SRC = os.path.join(BASE, "kpdc_data")
OUT = os.path.join(BASE, "araon_hourly.csv")

COLS = ["date", "time", "lat_dm", "ns", "lon_dm", "ew", "solar", "temp_c", "rh",
        "wspd", "wdir", "volt", "pres_hpa", "heading", "ns2", "lat2_dm", "ew2", "lon2_dm"]

# 물리적으로 가능한 범위. 이를 벗어나면 센서 오류로 간주하고 제거한다.
VALID = {
    "temp_c": (-60.0, 40.0),
    "wspd": (0.0, 60.0),      # 60 m/s 초과는 북극 항해 중 관측 불가
    "wdir": (0.0, 360.0),
    "pres_hpa": (900.0, 1100.0),
    "rh": (0.0, 100.0),
}


def dm_to_dd(v):
    """DDMM.mmmm → 십진도."""
    d = np.floor(v / 100.0)
    return d + (v - d * 100.0) / 60.0


def read_dat(path):
    try:
        raw = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return None
    raw = raw.replace("\x00", "").replace("\r", "")
    lines = [l for l in raw.split("\n")[2:] if l.strip()]
    rows = [l.split(",") for l in lines]
    rows = [r for r in rows if len(r) == 18]
    if not rows:
        return None

    df = pd.DataFrame(rows, columns=COLS)
    for c in ["lat_dm", "lon_dm", "solar", "temp_c", "rh", "wspd", "wdir",
              "volt", "pres_hpa", "heading", "lat2_dm", "lon2_dm"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["lat"] = dm_to_dd(df["lat_dm"]) * np.where(df["ns"].str.strip() == "S", -1, 1)
    df["lon"] = dm_to_dd(df["lon_dm"]) * np.where(df["ew"].str.strip() == "W", -1, 1)

    df["datetime"] = pd.to_datetime(
        df["date"] + df["time"].str.split(".").str[0].str.zfill(6),
        format="%Y%m%d%H%M%S", errors="coerce")
    return df.dropna(subset=["datetime", "lat", "lon"])


def qc(df):
    """물리범위 밖 값을 NaN 처리하고 변수별 제거율을 반환."""
    rates = {}
    for c, (lo, hi) in VALID.items():
        bad = ~df[c].between(lo, hi)
        rates[c] = float(bad.mean())
        df.loc[bad, c] = np.nan
    return df, rates


def circular_mean(deg):
    """풍향은 각도이므로 산술평균하면 안 된다(350도와 10도의 평균은 0도지 180도가 아니다)."""
    d = deg.dropna()
    if len(d) == 0:
        return np.nan
    r = np.radians(d.values)
    return float(np.degrees(np.arctan2(np.sin(r).mean(), np.cos(r).mean())) % 360)


def ship_motion(df):
    """
    GPS 좌표에서 선속(SOG)·침로(COG)를 유도한다.
    1초 간격 원자료는 GPS 잡음이 지배하므로 60초로 리샘플한 뒤 변위를 계산한다.
    선속은 겉보기풍/실제풍 판별에 필요하다.
    """
    g = df.set_index("datetime")[["lat", "lon"]].resample("60s").median().dropna()
    if len(g) < 3:
        return np.nan, np.nan
    lat = g["lat"].values
    lon = g["lon"].values
    latm = np.radians((lat[:-1] + lat[1:]) / 2)
    dy = np.radians(np.diff(lat)) * 6371000.0
    dx = np.radians(np.diff(lon)) * 6371000.0 * np.cos(latm)
    dt = np.diff(g.index.values).astype("timedelta64[s]").astype(float)
    ok = dt > 0
    if not ok.any():
        return np.nan, np.nan
    sog = np.hypot(dx[ok], dy[ok]) / dt[ok]
    cog = np.degrees(np.arctan2(dx[ok], dy[ok])) % 360
    # 이상치(GPS 점프) 제거: 아라온 최대속력은 약 8 m/s
    m = sog < 10
    if not m.any():
        return np.nan, np.nan
    r = np.radians(cog[m])
    return float(np.median(sog[m])), float(np.degrees(
        np.arctan2(np.sin(r).mean(), np.cos(r).mean())) % 360)


# 파일 단위 품질게이트.
# 한 시간치 원자료의 상당수가 물리범위 밖이면, 살아남은 소수도 신뢰할 수 없다.
# 실제로 2020년 일부 시간대는 원자료의 85~99%가 범위 밖이었고 잔존값 중앙값이
# 북위 73도 8월에 36°C였다. 값 단위 필터만으로는 이런 시간대를 걸러내지 못한다.
GATE = 0.20


def aggregate_file(path):
    df = read_dat(path)
    if df is None or len(df) < 60:
        return None
    df, rates = qc(df)
    sog, cog = ship_motion(df)

    # 불량률이 게이트를 넘은 변수는 해당 시간 전체를 무효 처리
    for var, key in [("temp_c", "temp_c"), ("wspd", "wspd"), ("pres_hpa", "pres_hpa")]:
        if rates[key] > GATE:
            df[var] = np.nan
    if rates["wspd"] > GATE:
        df["wdir"] = np.nan

    return {
        "datetime": df["datetime"].iloc[len(df) // 2].floor("h"),
        "n_sec": len(df),
        "latitude": df["lat"].median(), "longitude": df["lon"].median(),
        "temp_c": df["temp_c"].median(), "rh": df["rh"].median(),
        "wspd": df["wspd"].median(), "wspd_max": df["wspd"].max(),
        "wdir": circular_mean(df["wdir"]),
        "pres_hpa": df["pres_hpa"].median(),
        "heading": circular_mean(df["heading"]),
        "sog_ms": sog, "cog_deg": cog,
        "qc_bad_temp": rates["temp_c"], "qc_bad_wspd": rates["wspd"],
        "qc_bad_pres": rates["pres_hpa"],
        "wspd_zero_frac": float((df["wspd"] == 0).mean()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="2020,2024")
    a = ap.parse_args()

    frames = []
    for yr in a.years.split(","):
        files = sorted(glob.glob(os.path.join(SRC, yr, "*.dat")))
        if not files:
            print(f"[건너뜀] {yr} 파일 없음")
            continue
        print(f"{yr}: {len(files)}개 파일 처리 중...")
        recs = []
        for i, f in enumerate(files, 1):
            r = aggregate_file(f)
            if r:
                r["cruise_year"] = int(yr)
                recs.append(r)
            if i % 400 == 0:
                print(f"  {i}/{len(files)}")
        frames.append(pd.DataFrame(recs))

    out = pd.concat(frames, ignore_index=True).sort_values(["cruise_year", "datetime"])
    out.to_csv(OUT, index=False)

    print(f"\n저장: {OUT} ({len(out):,}시간)")
    print("\n[항차 요약]")
    for yr, g in out.groupby("cruise_year"):
        arctic = g[g["latitude"] > 66]
        print(f"\n{yr}년: {g['datetime'].min():%Y-%m-%d} ~ {g['datetime'].max():%Y-%m-%d}, {len(g):,}시간")
        print(f"  위도범위 {g['latitude'].min():.1f} ~ {g['latitude'].max():.1f}  "
              f"북극권(66N+) {len(arctic):,}시간 ({len(arctic)/len(g):.0%})")
        print(f"  풍속 중앙 {g['wspd'].median():.1f} m/s, 0값비율 {g['wspd_zero_frac'].mean():.1%}")
        print(f"  기압 유효율 {(1-g['qc_bad_pres'].mean()):.1%}")
        print(f"  선속 중앙 {g['sog_ms'].median():.1f} m/s")


if __name__ == "__main__":
    main()
