"""
EIA API 연동 — WTI/Brent 국제유가 다운로드
AURORA 프로젝트 — NSR 통항량과 유가 상관관계 분석용 (§1.2, 우려사항 문서 "비단조 시계열" 근거자료)

사용법:
  python 04_eia_oil_price.py --start 2010-01-01 --end 2025-12-31

API 키는 환경변수 EIA_API_KEY 로 전달 (커밋 방지를 위해 코드에 하드코딩하지 않음)
  export EIA_API_KEY=xxxxxxxx
"""
import argparse
import os
import sys

import pandas as pd
import requests

BASE_URL = "https://api.eia.gov/v2/petroleum/pri/spt/data/"
SERIES = {"WTI": "RWTC", "Brent": "RBRTE"}
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "eia_data")


def fetch_series(api_key, series_id, start, end):
    params = {
        "api_key": api_key,
        "frequency": "daily",
        "data[0]": "value",
        "facets[series][]": series_id,
        "start": start,
        "end": end,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "offset": 0,
        "length": 5000,
    }
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    rows = payload["response"]["data"]
    df = pd.DataFrame(rows)[["period", "value"]]
    df.columns = ["date", "price_usd_bbl"]
    df["date"] = pd.to_datetime(df["date"])
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2010-01-01")
    parser.add_argument("--end", default="2025-12-31")
    args = parser.parse_args()

    api_key = os.environ.get("EIA_API_KEY")
    if not api_key:
        print("환경변수 EIA_API_KEY 가 설정되어 있지 않습니다. `export EIA_API_KEY=...` 후 재실행하세요.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for name, series_id in SERIES.items():
        print(f"[요청] {name} ({series_id}) {args.start} ~ {args.end}")
        df = fetch_series(api_key, series_id, args.start, args.end)
        target = os.path.join(OUTPUT_DIR, f"eia_{name.lower()}.csv")
        df.to_csv(target, index=False)
        print(f"[완료] {len(df)}행 저장 -> {target}")


if __name__ == "__main__":
    main()
