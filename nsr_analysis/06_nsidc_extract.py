"""
NSIDC Sea Ice Index 지역별 일별 해빙면적(extent) → tidy CSV 변환
AURORA 프로젝트 — NSR 4개 해역(카라/랍테프/동시베리아/추크치) 해빙 시계열

원본: N_Sea_Ice_Index_Regional_Daily_Data_G02135_v4.0.xlsx
  시트 구조: 'Kara-Extent-km^2' 등, 행=(month, day), 열=연도(1978~)
출력: nsidc_daily_extent.csv  [date, sea, extent_km2]
"""
import os

import pandas as pd

BASE = os.path.dirname(__file__)
SRC = os.path.join(BASE, "nsidc_data", "N_Sea_Ice_Index_Regional_Daily_Data_G02135_v4.0.xlsx")
OUT = os.path.join(BASE, "nsidc_daily_extent.csv")

# NSR 항로가 지나는 4개 해역 (NSIDC 시트명 기준)
NSR_SEAS = ["Kara", "Laptev", "East-Siberian", "Chukchi"]

MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12,
}


def extract_sea(sea):
    df = pd.read_excel(SRC, sheet_name=f"{sea}-Extent-km^2")
    df["month"] = df["month"].ffill().map(MONTHS)

    year_cols = [c for c in df.columns if isinstance(c, int)]
    long = df.melt(
        id_vars=["month", "day"], value_vars=year_cols,
        var_name="year", value_name="extent_km2",
    ).dropna(subset=["extent_km2"])

    # 2/30, 2/31 같은 존재하지 않는 날짜는 errors="coerce"로 NaT 처리 후 제거
    long["date"] = pd.to_datetime(
        dict(year=long["year"], month=long["month"], day=long["day"]), errors="coerce"
    )
    long = long.dropna(subset=["date"])
    long["sea"] = sea
    return long[["date", "sea", "extent_km2"]]


def main():
    out = pd.concat([extract_sea(s) for s in NSR_SEAS], ignore_index=True)
    out = out.sort_values(["sea", "date"]).reset_index(drop=True)
    out.to_csv(OUT, index=False)

    print(f"저장: {OUT}  ({len(out):,}행)")
    print(out.groupby("sea")["date"].agg(["min", "max", "count"]))


if __name__ == "__main__":
    main()
