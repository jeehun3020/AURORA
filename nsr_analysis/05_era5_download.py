"""
ERA5 (reanalysis-era5-single-levels) 다운로드 스크립트
AURORA 프로젝트 — NSR 4개 해역(카라해/랍테프해/동시베리아해/추크치해) 기상 데이터

사용법:
  python 05_era5_download.py --test                 # 자격증명 확인용 소량 테스트 (카라해, 2024-07 1개월)
  python 05_era5_download.py --years 2015-2024       # 항행시즌(7~10월) 전체 다운로드

전제조건: ~/.cdsapirc 에 CDS API 토큰 설정 필요, CDS 웹사이트에서
"ERA5 hourly data on single levels from 1940 to present" Terms of Use 동의 필요
(동의 안 하면 403 에러 발생 — 에러 메시지에 동의 URL이 포함됨)
"""
import argparse
import os
import sys
import time
import zipfile

import cdsapi

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "era5_data")

# NSR 4개 구간 대략적 경계 [North, West, South, East], 경도는 0~360 기준(날짜변경선 통과 구간 대응)
REGIONS = {
    "kara": [82, 55, 65, 95],
    "laptev": [81, 95, 70, 145],
    "east_siberian": [77, 145, 68, 180],
    "chukchi": [75, 180, 65, 205],  # 205 = -155 + 360, 날짜변경선 통과
}

# 주의: "visibility"는 reanalysis-era5-single-levels 에서 유효한 변수명이 아님(MARS에서 ambiguous 에러) —
# 제거함. 가시거리는 안개 프록시(2m 이슬점-기온차, 상대습도)로 대체하거나 별도 데이터셋 확인 필요.
VARIABLES = [
    "2m_temperature",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "significant_height_of_combined_wind_waves_and_swell",
    "2m_dewpoint_temperature",
    "sea_ice_cover",
]

NAV_SEASON_MONTHS = ["07", "08", "09", "10"]


def download_month(client, region_name, area, year, month):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    target = os.path.join(OUTPUT_DIR, f"era5_{region_name}_{year}_{month}.nc")
    extract_dir = target[: -len(".nc")]
    if os.path.exists(target) or os.path.isdir(extract_dir):
        print(f"[skip] {region_name} {year}-{month} 이미 존재함")
        return

    request = {
        "product_type": "reanalysis",
        "variable": VARIABLES,
        "year": str(year),
        "month": month,
        "day": [f"{d:02d}" for d in range(1, 32)],
        "time": [f"{h:02d}:00" for h in range(0, 24, 6)],  # 6시간 간격 (00/06/12/18Z)
        "area": area,
        "data_format": "netcdf",
    }

    print(f"[요청] {region_name} {year}-{month} area={area}")
    client.retrieve("reanalysis-era5-single-levels", request, target)

    # CDS 신형 API는 여러 스트림(surface/wave)을 묶어 zip으로 내려주는 경우가 있음 (확장자는 .nc지만 실제 zip)
    if zipfile.is_zipfile(target):
        extract_dir = target[: -len(".nc")]
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(target) as zf:
            zf.extractall(extract_dir)
        os.remove(target)
        print(f"[완료] zip 압축 해제 -> {extract_dir}/")
    else:
        print(f"[완료] {target}")


def parse_year_range(s):
    if "-" in s:
        start, end = s.split("-")
        return list(range(int(start), int(end) + 1))
    return [int(s)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="카라해 2024-07 1개월만 다운로드하여 자격증명/ToS 확인")
    parser.add_argument("--years", type=str, default="2015-2024", help="예: 2015-2024 또는 2020")
    parser.add_argument("--regions", type=str, default="kara,laptev,east_siberian,chukchi")
    args = parser.parse_args()

    client = cdsapi.Client()

    if args.test:
        download_month(client, "kara", REGIONS["kara"], 2024, "07")
        return

    years = parse_year_range(args.years)
    regions = args.regions.split(",")

    for region_name in regions:
        if region_name not in REGIONS:
            print(f"[경고] 알 수 없는 구간명: {region_name}, 건너뜀")
            continue
        area = REGIONS[region_name]
        for year in years:
            for month in NAV_SEASON_MONTHS:
                try:
                    download_month(client, region_name, area, year, month)
                except Exception as e:
                    print(f"[에러] {region_name} {year}-{month}: {e}", file=sys.stderr)
                time.sleep(1)


if __name__ == "__main__":
    main()
