# AURORA

**공개 해빙·기상·AIS 데이터를 활용한 북극해항로 구간별 동적 운항위험지수 및 보험 할증계수 프로토타입**

2026 극지 빅데이터-인공지능 활용 경진대회 (극지연구소 KOPRI 주최) 데이터 분석 부문 출품작

> POLARIS가 "갈 수 있는가"를 묻는다면, AURORA는 "어떻게 가야 위험과 보험 부담을 가장 줄일 수 있는가"를 답한다.

## 프로젝트 한눈에 보기

- **제품명**: AURORA — Arctic Underwriting & Route Operational Risk Assessment
- **핵심 아이디어**: 기존 POLARIS(해빙-내빙능력 기반 운항가능성 평가)를 기준모델로 삼아, 기상·구조접근성·안전조치를 더한 **잔여위험(Residual Risk)** 과 **상대 보험 할증계수**를 계산하고, 이를 AIS 선박 행동(감속·대기·우회)으로 검증하는 프로토타입
- **범위**: 2015~2024년 7~10월(항행시즌) NSR을 운항한 화물선 대상, 구간별 해빙·기상·구조접근성 결합 일별 상대 운항위험

핵심 수식:
```
사고가능성 P = f(POLARIS, 해빙두께, 파고, 풍속, 가시거리, 저온, 선박등급, 쇄빙지원)
사고결과 S   = g(구조기지거리, 선박가액, 화물유형, 승객수, 환경민감도)
고유위험     = P × S
극지구조공백지수 PRGI = w1·SAR거리 + w2·피난항거리 + w3·쇄빙지원부족 + w4·예상구조지연
잔여위험(안전조치 m) = 고유위험 × 극지손실증폭(PRGI) × (1 - η_m)
할증계수 M(m) = 1 + α · 잔여위험(m)
안전조치크레딧 = M(기준) - M(안전조치 적용)
```

자세한 배경과 논리는 [docs/](docs/) 폴더 참고:
- [01_project_concerns_and_positioning.md](docs/01_project_concerns_and_positioning.md) — 심사 대응 우려사항 및 표현 원칙 (왜 "보험료 예측"이 아니라 "상대 위험지수"인지 등)
- [02_differentiation_strategy.md](docs/02_differentiation_strategy.md) — POLARIS 대비 차별화 전략 (잔여위험, PRGI, AIS 행동검증, What-if 시뮬레이션)
- [03_handoff_notes.md](docs/03_handoff_notes.md) — 데이터 소스 현황, 작업 진행상황, 다음 단계 전체 목록

## 심사 대응 — 반드시 지킬 표현 원칙

| 피해야 할 표현 | 대신 사용할 표현 |
|---|---|
| "보험료를 예측한다" | "동일 조건 가정 시 상대적 위험 차이와 할증 방향을 제시하는 프로토타입" |
| "POLARIS를 대체한다" | "POLARIS를 기준모델로 삼아 기상·구조접근성·운항지원을 추가한 확장형 모델" |
| "해빙 감소 → 선박 증가" 단순 인과 | "해빙 감소는 필요조건이나 유가·제재·항구인프라·지정학이 더 크게 작용" |
| 정밀한 숫자 단정 (예: "할증계수 1.273배") | 범위 + 신뢰도 등급 (예: "1.20~1.34, 신뢰도 B") |

전체 목록은 [docs/03_handoff_notes.md](docs/03_handoff_notes.md#2-반드시-지켜야-할-표현-원칙-심사-대응) 참고.

## 데이터 현황

| 데이터 | 상태 |
|---|---|
| EIA 국제유가 (WTI/Brent, 2010~2025) | ✅ 완료 |
| ERA5 기상/해양 (2015~2024, 카라해·랍테프해·동시베리아해·추크치해) | 🔄 다운로드 진행/완료 |
| PAME ASTD (AIS, 13종 선종) | 🔄 신청 완료, 승인 대기 |
| NSR 통항 실적 (CHNL) | ⚠️ 부분 재구성 — 2014·2017·2019~2022년 누락, 재수집 필요 |

자세한 내용은 [docs/03_handoff_notes.md §3](docs/03_handoff_notes.md#3-데이터-소스-현황) 참고.

## 시작하기

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### EIA 유가 데이터 받기
```bash
export EIA_API_KEY=your_key_here   # https://www.eia.gov/opendata/register.php 에서 개별 발급
python nsr_analysis/04_eia_oil_price.py --start 2010-01-01 --end 2025-12-31
```

### ERA5 기상 데이터 받기
```bash
# ~/.cdsapirc 에 개인 CDS 토큰 설정 필요 (https://cds.climate.copernicus.eu 가입 후 발급)
# 최초 1회 https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels 에서 ToU 동의 필요
python nsr_analysis/05_era5_download.py --test          # 소량 테스트
python nsr_analysis/05_era5_download.py --years 2015-2024  # 전체 다운로드 (수 시간 소요)
```

## 코드 구조 (`nsr_analysis/`)

| 파일 | 상태 | 설명 |
|---|---|---|
| `01_transit_trend_analysis.py` | 🔲 TODO | NSR 통항 시계열 분석·시각화 |
| `02_risk_score_prototype.py` | 🔲 TODO | P×S 잔여위험/할증계수 계산 스켈레톤 |
| `03_weather_pipeline.py` | 🔲 TODO | 기상데이터 전처리·결측보간·파생변수 파이프라인 |
| `04_eia_oil_price.py` | ✅ | EIA API 연동 (WTI/Brent) |
| `05_era5_download.py` | ✅ | ERA5 다운로드 (NSR 4개 구간, 항행시즌 7~10월) |

TODO 항목 3개는 이전 작업 세션에서 작성되었으나 파일이 유실되어 재작성이 필요합니다. 자세한 내용은 [docs/03_handoff_notes.md §4](docs/03_handoff_notes.md#4-작성된-코드-전부-nsr_analysis-폴더)를 참고하세요.

## 다음 단계

1. `01_transit_trend_analysis.py`, `03_weather_pipeline.py` 재작성
2. `02_risk_score_prototype.py`의 placeholder 가중치를 POLARIS RIO 공식표(IMO MSC.1/Circ.1519) 기반으로 교체
3. PRGI용 구조기지·피난항 위치 데이터 수집
4. NSR 통항 데이터 누락 연도(2014·2017·2019~2022) CHNL에서 재수집
5. 발표자료(pptx) AURORA 버전으로 갱신
6. 분석보고서 초안 작성

전체 우선순위 목록은 [docs/03_handoff_notes.md §7](docs/03_handoff_notes.md#7-다음-단계-우선순위-순) 참고.

## 팀

- 역할 후보안(확정 아님): A=해빙·기상/리스크모델링, B=통항·경제지표/프리미엄로직, C=대시보드·시각화, D=보고서·발표
- 팀명: 미확정
