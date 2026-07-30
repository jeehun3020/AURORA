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
- **[04_analysis_findings.md](docs/04_analysis_findings.md) — 📊 분석 결과 핵심 발견 (먼저 읽을 것)**
- [01_project_concerns_and_positioning.md](docs/01_project_concerns_and_positioning.md) — 심사 대응 우려사항 및 표현 원칙 (왜 "보험료 예측"이 아니라 "상대 위험지수"인지 등)
- [02_differentiation_strategy.md](docs/02_differentiation_strategy.md) — POLARIS 대비 차별화 전략 (잔여위험, PRGI, AIS 행동검증, What-if 시뮬레이션)
- [03_handoff_notes.md](docs/03_handoff_notes.md) — 데이터 소스 현황, 작업 진행상황, 다음 단계 전체 목록
- **[05_kpdc_data_request.md](docs/05_kpdc_data_request.md) — ⏰ KPDC ARAON 데이터 신청 가이드 (마감 임박)**

## 분석 결과 요약

| # | 발견 | 근거 | 지위 |
|---|---|---|---|
| 5 | **예측을 쓰면 실제로 위험이 준다** — 이론적 최대이득의 55~66% 실현, 달력 규칙은 7~25%뿐 | 시간순 분할 backtest (검증 2022~24) | 견고 (이상화 설정 주의) |
| 4 | **출항연기 효과는 평균과 중앙값의 부호가 반대** — 꼬리위험 구조. 시즌 후반 연기는 위험을 키운다 | ERA5 실측 what-if | 방향 견고(부호유지율 100%), 크기 잠정 |
| 1 | **NSR의 병목은 동시베리아해** — 항행가능일 53일로 카라해(121일)의 44% | NSIDC 1979~2025, 전 해역 p<10⁻⁸ | 견고 |
| 3 | **선박등급 실익은 중간 빙조건(30~70%)에 집중** — 개빙수역·밀집빙에선 무의미 | ERA5 4,920일 | 모델 내부 성질 (지수의 구성에서 파생) |
| 2 | 해빙 결정론 반례 — 2013→2015 해빙 −46%인데 통항 −75% | CHNL n=9 | **판단 보류** (사례 서술, 검정력 없음) |

### 검증 현황

| 검증 대상 | 자료 | 상태 |
|---|---|---|
| 해빙 입력자료 | NSIDC 위성관측 | ✅ r=0.91~0.95 |
| 지수 최적시점 | NSIDC 최소빙일 | ✅ 평균 2.8일 차 |
| 기온 입력자료 | **KPDC ARAON 선상관측** | ✅ **중앙값오차 ±0.53°C, MAD 0.36~0.50°C** |
| 풍속 입력자료 | **KPDC ARAON 선상관측** | ⚠️ 부분 (최량항차 r=0.855, 편의 +1~2 m/s) |
| 위험지수 vs 선박 행동(연구선) | KPDC ARAON GPS | ❌ **실패** — 연구선 임무 교란으로 검증 불가 |
| 위험지수 vs 선박 행동(화물선) | PAME ASTD | ⬜ 승인 대기 — **대체재 없음이 실증됨** |
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

전체 목록은 [docs/03_handoff_notes.md](docs/03_handoff_notes.md#2-반드시-지켜야-할-표현-원칙-심사-대응) 참고.

## 데이터 현황

| 데이터 | 상태 |
|---|---|
| EIA 국제유가 (WTI/Brent, 2010~2025) | ✅ 완료 |
| ERA5 기상/해양 (2015~2024, 카라해·랍테프해·동시베리아해·추크치해) | 🔄 다운로드 진행/완료 |
| PAME ASTD (AIS, 13종 선종) | 🔄 신청 완료, 승인 대기 |
| **KPDC ARAON 선상 기상관측 (6개 항차 2020~2025)** | ✅ 승인·확보 완료, 12,189시간 |
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

실행 순서대로 번호가 매겨져 있습니다. 04~05는 데이터 수집, 06~07은 전처리, 08~12는 분석입니다.

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

전체 파이프라인 재현:
```bash
python nsr_analysis/06_nsidc_extract.py
python nsr_analysis/07_era5_aggregate.py
python nsr_analysis/08_ice_trend_analysis.py
python nsr_analysis/09_decoupling_analysis.py
python nsr_analysis/10_risk_index.py
python nsr_analysis/11_whatif_residual.py
python nsr_analysis/12_figures.py
```

산출물은 `nsr_analysis/results/`(CSV)와 `nsr_analysis/figures/`(PNG)에 생성됩니다.

## 다음 단계

1. **CHNL에서 누락 연도(2014·2017·2019~2022) 통항 실적 재수집** — 발견 2의 검정력에 직결
2. POLARIS RIO 공식표(IMO MSC.1/Circ.1519) 적용해 해빙 위험 임계값 교체
3. PAME ASTD 승인 후 AIS 감속·대기·우회로 위험지수 검증 (AURORA 차별화의 핵심 축, 현재 공백)
4. 구간 박스 → 실제 NSR 항로선 기준 재집계
5. 발표자료(pptx) AURORA 버전으로 갱신
6. 분석보고서 초안 작성 — 발견 1·3·4 중심, 발견 2는 한계와 함께

방법론 한계 전체 목록은 [docs/04_analysis_findings.md](docs/04_analysis_findings.md#방법론-한계-보고서에-반드시-명시) 참고.

## 팀

- 역할 후보안(확정 아님): A=해빙·기상/리스크모델링, B=통항·경제지표/프리미엄로직, C=대시보드·시각화, D=보고서·발표
- 팀명: 미확정
