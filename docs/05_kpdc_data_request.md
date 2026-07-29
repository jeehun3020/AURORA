# KPDC ARAON 기상관측 데이터 신청 가이드

> **마감 역산**: KPDC 처리기간은 신청 후 **14일 이내 통보**(Data Disclosure 정책). 예선 자료접수 마감이 8/14이므로 **7/29~7/31 사이에 신청해야** 예선에 반영 가능하다. 그 이후 신청은 본선(8/17~8/31) 대상으로만 유효하다.

## 왜 이 데이터인가

현재 AURORA가 쓰는 자료는 NSIDC·ERA5·EIA·CHNL로 **전부 해외 출처다.** 본 대회가 KPDC 데이터 가치 확산을 취지로 하는 만큼 취지 부합도에서 불리할 수 있다.

동시에 우리 위험지수는 **ERA5 재분석값에만 의존**한다는 약점이 있다. 재분석은 모델+자료동화 산물이라 실제 관측이 아니다.

아라온호(IBRV ARAON)는 척치해·동시베리아해를 실제 항행하는 국내 쇄빙연구선이다. **선상 in-situ 기상관측으로 ERA5를 검증하면 두 문제가 동시에 해소된다.** 보조 챕터가 아니라 검증 챕터의 정식 구성요소가 된다.

## 신청 대상 목록 (6건 일괄 신청 권장)

ERA5 보유기간(2015~2024)과 겹치는 것은 2020~2024년 5개년. 2025년분은 ERA5 확장 시 사용 가능.

| Entry ID | 항해 | 링크 |
|---|---|---|
| KOPRI-KPDC-00002994 | Arctic cruise 2025 | https://kpdc.kopri.re.kr/search/008d8d20-c7cb-4cc9-8a24-dfc6be698182 |
| **KOPRI-KPDC-00002855** | **Arctic cruise 2024** | https://kpdc.kopri.re.kr/search/c6737273-2e1e-4990-98a6-e071f9386337 |
| KOPRI-KPDC-00002359 | Arctic cruise 2023 | https://kpdc.kopri.re.kr/search/04bbdb5f-6f00-4da6-a193-1fe9e43dbf35 |
| KOPRI-KPDC-00002146 | Arctic cruise 2022 | https://kpdc.kopri.re.kr/search/d5d8bba2-572d-4671-9d82-193b9a03f08b |
| KOPRI-KPDC-00001704 | Arctic cruise 2021 | https://kpdc.kopri.re.kr/search/630d84db-20ea-4d31-938c-75e6a655c342 |
| KOPRI-KPDC-00001463 | Arctic cruise 2020 | https://kpdc.kopri.re.kr/search/ed848c92-3b12-479f-8134-b898caf7fa3a |

2024년분 상세: 관측기간 2024-07-15~09-30, 공간범위 lat 60~80°N / lon 160°E~150°W, 변수 해면기압·해수면온도·표층풍, DOI `10.22663/KOPRI-KPDC-00002855`

**선택 추가** — 상층기상 검증이 필요하면 라디오존데도 함께:
`KOPRI-KPDC-00003011`(2025 ARA16A), `KOPRI-KPDC-00002646`(2024 ARA15A), `KOPRI-KPDC-00002225`(2023 ARA14B)

## 절차

1. **회원가입** — https://kpdc.kopri.re.kr/user/login 의 `Sign Up`. Google 계정 연동 가능.
2. 위 표의 데이터셋 페이지로 이동
3. 페이지 상단 **`+ Add Disclosure Request`** 클릭
4. 신청 사유(연구목적) 작성 — 아래 초안 활용
5. 제출 후 **`My Page > Request List`**(https://kpdc.kopri.re.kr/user/request/)에서 상태 확인
6. 14일 내 결과 통보. 지연 시 kpdc@kopri.re.kr 문의

## 신청 사유 초안

> **연구목적**
>
> 2026 극지 빅데이터-인공지능 활용 경진대회(데이터 분석 부문) 출품 연구 「공개 해빙·기상 데이터를 활용한 북극해항로 구간별 동적 운항위험지수 및 보험 할증계수 프로토타입」의 입력자료 검증에 사용하고자 합니다.
>
> 본 연구는 ERA5 재분석자료를 이용해 북극해항로(NSR) 4개 구간(카라해·랍테프해·동시베리아해·추크치해)의 일별 환경위험지수를 산출하였습니다. 그러나 ERA5는 모델과 자료동화의 산물이므로 실제 해상 관측과의 정합성 검증이 필요합니다.
>
> 아라온호 북극항해 선상 기상관측 자료(표층풍·해면기압·해수면온도)는 관측기간(7~9월)과 공간범위(동시베리아해·추크치해)가 본 연구의 분석 대상과 직접 일치합니다. 해당 자료를 ERA5 재분석값과 대조하여 위험지수 기상 입력변수의 in-situ 타당성을 확인하는 데 활용하겠습니다.
>
> 산출물은 대회 제출용 분석보고서이며 상업적 이용 계획은 없습니다. 데이터 출처는 KPDC 표준 인용형식으로 명기하고, 결과물은 데이터센터에 보고하겠습니다.

## 승인 시 준수 의무 (실제 이행해야 함)

KPDC 데이터 이용 규정상 다음이 요구된다. 형식적 체크박스가 아니라 실제 이행 대상이다.

- 신청한 연구목적으로만 사용, 제3자 판매·양도 금지
- 성과물에 KPDC 인용정보 기재 — 표준 형식:
  > The data(KOPRI-KPDC-00002855) used in this work was provided by the Korea Polar Research Institute.
- 지적재산권 등록 전 사전협의
- **성과물 제출 및 추가 획득 데이터 등록·공개** — 대회 종료 후 보고서를 KPDC에 제출해야 함

## 신청 현황

**제출 완료** (2026-07-29). 접수 확인 메일 수신.

> 확인된 사실: 승인 주체는 데이터센터가 아니라 **연구책임자(the researcher)**다.
> "Your application is pending approval by the researcher and will be sent to you immediately upon approval."
>
> 즉 정책상 14일은 상한이고, 실제 소요는 PI 응답 속도에 달렸다. 1주일 내 회신이 없으면 아래로 직접 문의하는 편이 빠르다.

| 역할 | 연락처 |
|---|---|
| PI (ARAON DaDiS 기상) | Dong Seob Shin — dsshin@kopri.re.kr |
| 공동 | Su-hwan Kim — idsuhwan@kopri.re.kr |
| 공동 | Hyung-gyu Choi — langyu7@kopri.re.kr |
| 공동 | GoHeung Kim — ghkim@kopri.re.kr |
| 데이터센터 | kpdc@kopri.re.kr |

문의 시 대회 출품 일정(예선 8/14)을 명시하면 우선 처리를 기대할 수 있다. 신청 상태는 `My Page > Request List`에서 확인.

## 승인 후 분석 연결

[`nsr_analysis/13_validation.py`](../nsr_analysis/13_validation.py)의 `validate_araon()`에 CSV 경로를 넘기면 된다.

```bash
ARAON_CSV=nsr_analysis/kpdc_data/araon_arctic_2024.csv python nsr_analysis/13_validation.py
```

ERA5 쪽 지점추출은 **완성·검증 완료**다. [`14_era5_track_extract.py`](../nsr_analysis/14_era5_track_extract.py)가 항적(시각·위경도)별 최근접 격자값을 뽑는다. 합성 항적 61점으로 자체검증한 결과 매칭률 100%, 격자 이격 최대 0.121도(ERA5 반격자 0.125도 이내), 물리범위 검사 통과.

```bash
python nsr_analysis/14_era5_track_extract.py --selftest              # 로직 검증
python nsr_analysis/14_era5_track_extract.py --track araon.csv --out matched.csv
```

따라서 데이터 도착 후 남은 작업은 **컬럼명 매핑 하나뿐**이다 (`datetime`, `latitude`, `longitude`, `wind_speed`, `air_temp`, `pressure`).

구현 시 주의: 추크치해 구간은 날짜변경선을 넘으므로 경도 표기 규약(-180~180 vs 0~360)을 반드시 정렬해야 한다. `_align_lon()`이 처리하지만, 진단 지표에서도 같은 정렬을 적용해야 한다 — 정렬 없이 뺀 이격거리는 360도로 나와 오정렬을 탐지하지 못한다.

## 검증 설계 (승인 전 미리 확정해둘 것)

| 항목 | 내용 |
|---|---|
| 대조 변수 | 표층풍속(1순위), 해면기압, 해수면온도 |
| 대조 방법 | 항적 각 시점의 위경도에 최근접한 ERA5 격자·시각 값 추출 |
| 평가 지표 | Pearson r, RMSE, 평균편의(bias) |
| 판정 기준 | 풍속 r>0.7이면 ERA5 기상 입력 타당성 확보로 서술 |
| 주의 | 선상 풍속계는 선체 교란·상대풍 보정 문제가 있다. 원자료가 true wind인지 apparent wind인지 반드시 메타데이터로 확인할 것. 이를 확인 안 하고 대조하면 검증이 아니라 오류가 된다. |
