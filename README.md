# AURORA

**공개 해빙·기상·AIS 데이터를 활용한 북극해항로 구간별 동적 운항위험지수 및 보험 할증계수 프로토타입**

2026 극지 빅데이터-인공지능 활용 경진대회 (극지연구소 KOPRI 주최) 데이터 분석 부문 출품작

> POLARIS가 "갈 수 있는가"를 묻는다면, AURORA는 "어떻게 가야 위험과 보험 부담을 가장 줄일 수 있는가"를 답한다.

## 프로젝트 한눈에 보기

- **제품명**: AURORA — Arctic Underwriting & Route Operational Risk Assessment
- **핵심 아이디어**: 기존 POLARIS(해빙-내빙능력 기반 운항가능성 평가)를 기준모델로 삼아, 기상·구조접근성·안전조치를 더한 **잔여위험(Residual Risk)** 과 **상대 보험 할증계수**를 계산하고, 이를 **다중 독립자료(NSIDC 위성관측·KPDC 아라온 선상관측)로 교차검증**한 프로토타입
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

### 문서 위계 (충돌 시 위쪽이 정본)

| 문서 | 지위 | 내용 |
|---|---|---|
| **[07_competition_submission_master.md](docs/07_competition_submission_master.md)** | 🟢 **정본** | 제출용 단일 기준. 근거등급·제출용 문장·심사 예상질문 |
| [04_analysis_findings.md](docs/04_analysis_findings.md) | 🟢 정본 | 발견 1~7 상세와 방법론 한계 |
| [06_deep_analysis_report.md](docs/06_deep_analysis_report.md) | 🟢 정본 | 심층 감사, 강건성 검증, 수치 정정 |
| [01_project_concerns_and_positioning.md](docs/01_project_concerns_and_positioning.md) | 🟡 부분 유효 | §2 표현 원칙은 유효, 결과 수치는 위 문서 우선 |
| [05_kpdc_data_request.md](docs/05_kpdc_data_request.md) | 🟡 이력 | KPDC 신청 절차 (승인·확보 완료) |
| [02_differentiation_strategy.md](docs/02_differentiation_strategy.md) | ⚪ **원안 이력** | AIS 검증 전제가 성립하지 않음. 설계 이력으로만 인용 |
| [03_handoff_notes.md](docs/03_handoff_notes.md) | ⚪ 이력 | 초기 작업 기록. 데이터 현황은 크게 변경됨 |

## 분석 결과 요약

| # | 발견 | 근거 | 지위 |
|---|---|---|---|
| 5 | **예측을 쓰면 실제로 위험이 준다** — 이론적 최대이득의 55~66% 실현, 달력 규칙은 7~25%뿐 | 시간순 분할 backtest (검증 2022~24) | 견고 (이상화 설정 주의) |
| 4 | **출항연기 효과는 평균과 중앙값의 부호가 반대** — 꼬리위험 구조. 시즌 후반 연기는 위험을 키운다 | ERA5 실측 what-if | 방향 견고(부호유지율 100%), 크기 잠정 |
| 1 | **NSR의 병목은 동시베리아해** — 항행가능일 53일로 카라해(121일)의 44% | NSIDC 1979~2025, 전 해역 p<10⁻⁸ | 견고 |
| 3 | **선박등급 실익은 중간 빙조건(30~70%)에 집중** — 개빙수역·밀집빙에선 무의미 | ERA5 4,920일 | 모델 내부 성질 (지수의 구성에서 파생) |
| 7 | **합성지수는 해빙지수의 재포장이 아니다** — 출항결정 40%가 갈림 | ERA5 4,800건, 완전예지 조건 | 견고 (우열은 판정 불가) |
| 6 | **항행창은 2배 넓어졌으나 최적점은 고정** — 단 최적일 연간 변동 최대 16일 | NSIDC 1979~2025 관측 단독 | 견고 |
| 2 | 해빙 결정론 반례 — 2013→2015 해빙 −46%인데 통항 −75% | CHNL n=9 | **판단 보류** (사례 서술, 검정력 없음) |

### 검증 현황

| 검증 대상 | 자료 | 상태 |
|---|---|---|
| 해빙 입력자료 | NSIDC 위성관측 | ✅ r=0.91~0.95 |
| 지수 최적시점 | NSIDC 최소빙일 | ✅ 평균 2.8일 차 |
| 기온 입력자료 | **KPDC ARAON 선상관측** | ✅ **중앙값오차 ±0.53°C, MAD 0.36~0.50°C** |
| 풍속 입력자료 | **KPDC ARAON 선상관측** | ⚠️ 부분 (최량항차 r=0.855, 편의 +1~2 m/s) |
| 위험지수 vs 선박 행동(연구선) | KPDC ARAON GPS | ❌ **실패** — 연구선 임무 교란으로 검증 불가 |
| 위험지수 vs 선박 행동(화물선) | PAME ASTD | ❌ **금회 승인 무산** — 대체재 없음이 실증됨 |
| 예측가능성 | ERA5 시간순 분할 | ✅ 지속성 대비 skill 0.26~0.35 |

**부산물**: ERA5 대조로 아라온 기압센서가 2023년부터 결함(전량 500.00 고정)임을 탐지. 검증은 양방향으로 작동한다.

![예측·후향검증](nsr_analysis/figures/M_forecast_backtest.png)

![ARAON 검증](nsr_analysis/figures/V3_araon_validation.png)

⚠️ 절대 수치(+26.3%, 2.3배 등)는 전부 잠정 가중치의 함수다. 발표 시 [견고/잠정/근거부족 3분류](docs/04_analysis_findings.md#이-결론-중-어디까지가-가중치와-무관한가-중요)를 지킬 것.

![위험지수](nsr_analysis/figures/C_risk_index.png)

## 심사 대응 — 반드시 지킬 표현 원칙

| 피해야 할 표현 | 대신 사용할 표현 |
|---|---|
| "보험료를 예측한다" | "동일 조건 가정 시 상대적 위험 차이와 할증 방향을 제시하는 프로토타입" |
| "POLARIS를 대체한다" | "POLARIS를 기준모델로 삼아 기상·구조접근성·운항지원을 추가한 확장형 모델" |
| "해빙 감소 → 선박 증가" 단순 인과 | "해빙 감소는 필요조건이나 유가·제재·항구인프라·지정학이 더 크게 작용" |
| 정밀한 숫자 단정 (예: "할증계수 1.273배") | 범위 + 신뢰도 등급 (예: "1.20~1.34, 신뢰도 B") |

전체 목록은 [docs/07_competition_submission_master.md §6](docs/07_competition_submission_master.md) 참고.

## 데이터 현황

| 데이터 | 상태 |
|---|---|
| EIA 국제유가 (WTI/Brent, 2010~2025) | ✅ 완료 |
| ERA5 기상/해양 (2015~2024, 4개 해역) | ✅ 완료 (160개 파일) |
| PAME ASTD (AIS, 13종 선종) | ❌ 금회 승인 무산 |
| **KPDC ARAON 선상 기상관측 (6개 항차 2020~2025)** | ✅ 승인·확보 완료, 12,189시간 |
| NSR 통항 실적 (CHNL) | ⚠️ 부분 재구성 — 2014·2017·2019~2022년 누락, 재수집 필요 |

자세한 내용은 [docs/07_competition_submission_master.md](docs/07_competition_submission_master.md) 참고.

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

실행 순서대로 번호가 매겨져 있습니다. 04~05 수집 / 06~07 전처리 / 08~12 분석 / 13~18 검증 / 19~24 예측·확장분석.

| 파일 | 설명 |
|---|---|
| `04_eia_oil_price.py` | EIA API 연동 (WTI/Brent) |
| `05_era5_download.py` | ERA5 다운로드 (NSR 4개 구간, 항행시즌 7~10월) |
| `06_nsidc_extract.py` | NSIDC 지역별 해빙 xlsx → tidy CSV |
| `07_era5_aggregate.py` | ERA5 netCDF → 구간별 일별 기상 피처 |
| `08_ice_trend_analysis.py` | 발견 1 — 항행가능일수 47년 추세 |
| `09_decoupling_analysis.py` | 발견 2 — 해빙·통항 탈동조화 |
| `10_risk_index.py` | 발견 3 — P×S 위험지수, PRGI, 가중치 민감도 |
| `11_whatif_residual.py` | 발견 4 — 출항연기·쇄빙지원 what-if |
| `12_figures.py` | 보고서용 figure 4종 |
| `13_validation.py` | 검증1·2 — NSIDC 독립 대조 |
| `14_era5_track_extract.py` | 항적별 ERA5 최근접 격자 추출 |
| `15_araon_parse.py` | KPDC ARAON 1초 원자료 → 시간별 집계 (4계층 QC) |
| `16_araon_era5_validation.py` | 검증3 — ARAON in-situ vs ERA5 |
| `17_validation_figures.py` | 검증3 figure |
| `18_behavioral_validation.py` | 검증4 — ARAON GPS 행동검증 (실패 기록) |
| `19_risk_forecast.py` | 발견 5 — 예측모델 + 의사결정 후향검증 |
| `20_forecast_figures.py` | 발견 5 figure |
| `21_deep_analysis.py` | 심층 감사 — 강건성·군집 불확실성·롤링 검증 |
| `22_index_divergence.py` | 발견 7 — 합성 vs 해빙단독 결정 분기 |
| `23_window_shift.py` | 발견 6 — NSIDC 47년 항행창 이동 |
| `24_window_figures.py` | 발견 6·7 figure |

전체 파이프라인 재현:
```bash
python nsr_analysis/06_nsidc_extract.py
python nsr_analysis/07_era5_aggregate.py
python nsr_analysis/08_ice_trend_analysis.py
python nsr_analysis/09_decoupling_analysis.py
python nsr_analysis/10_risk_index.py
python nsr_analysis/11_whatif_residual.py
python nsr_analysis/12_figures.py
python nsr_analysis/13_validation.py
python nsr_analysis/19_risk_forecast.py
python nsr_analysis/22_index_divergence.py
python nsr_analysis/23_window_shift.py
```

ARAON 검증(15~18)은 KPDC 원자료가 `nsr_analysis/kpdc_data/`에 있어야 실행됩니다.

산출물은 `nsr_analysis/results/`(CSV)와 `nsr_analysis/figures/`(PNG)에 생성됩니다.

## 다음 단계

1. **분석보고서·발표자료 작성** — [07 §7 발표 키트](docs/07_competition_submission_master.md) 사용
2. **KPDC 회신** — 아라온 기압센서 결함(2023~2025) 전달. 데이터 이용 규정상 성과 보고 의무
3. PAME ASTD 재신청 (차기) — 합성지수 추가가치 검증의 유일한 경로
4. SAR 거점 실제 출동능력 자료 — PRGI가 추크치해 순위를 뒤집는데 미검증
5. 구간 박스 → 실제 NSR 항로선 기준 재집계
6. CHNL 누락 6개 연도 재수집 — 발견 2를 사례에서 결과물로 승격

방법론 한계 전체 목록은 [docs/04_analysis_findings.md](docs/04_analysis_findings.md#방법론-한계-보고서에-반드시-명시) 참고.

## 팀

- 역할 후보안(확정 아님): A=해빙·기상/리스크모델링, B=통항·경제지표/프리미엄로직, C=대시보드·시각화, D=보고서·발표
- 팀명: 미확정
