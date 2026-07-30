# Competition Team Master Document Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a single Korean Markdown reference that consolidates every competition-worthy AURORA result, its evidence level, usable wording, limitations, and the team’s report/PPT materials.

**Architecture:** One final document, `docs/07_competition_submission_master.md`, will act as the team’s source of truth. It will synthesize existing verified Markdown and CSV outputs without changing raw data or recalculating model results, and will clearly separate empirical findings, model-internal robustness, assumptions, and unsupported claims.

**Tech Stack:** Markdown, local CSV/Markdown source files, `rg`, Python/pandas consistency checks

## Global Constraints

- Write for internal team members who did not perform the analysis.
- Use only evidence already present in the workspace; do not add external research.
- Preserve the distinction between relative AURORA risk, actual accident probability, and insurance premiums.
- Every major statistic must state its population, period, statistic type, and evidence level.
- Use the corrected ARAON counts: 2,528 matched rows, 2,450 valid temperature pairs, and five validation cruises from 2020 through 2024.
- Treat PRGI, PC6/PC7 thresholds, and icebreaker mitigation as model assumptions unless independently validated.
- Do not interpret the incomplete NSR transit correlation as a statistical result.

---

### Task 1: Build the Authoritative Evidence Matrix

**Files:**
- Read: `README.md`
- Read: `docs/01_project_concerns_and_positioning.md`
- Read: `docs/02_differentiation_strategy.md`
- Read: `docs/03_handoff_notes.md`
- Read: `docs/04_analysis_findings.md`
- Read: `docs/06_deep_analysis_report.md`
- Read: `nsr_analysis/results/A_ice_trend.csv`
- Read: `nsr_analysis/results/C_region_month_risk.csv`
- Read: `nsr_analysis/results/D_delay_effect.csv`
- Read: `nsr_analysis/results/V1_era5_vs_nsidc.csv`
- Read: `nsr_analysis/results/V3_validation_metrics.csv`
- Read: `nsr_analysis/results/deep_analysis/delay_robustness.csv`
- Read: `nsr_analysis/results/deep_analysis/season_windows.csv`
- Read: `nsr_analysis/results/deep_analysis/corridor_window.csv`
- Read: `nsr_analysis/results/deep_analysis/risk_drivers.csv`
- Read: `nsr_analysis/results/deep_analysis/regional_risk.csv`
- Read: `nsr_analysis/results/deep_analysis/rolling_forecast_summary.csv`
- Read: `nsr_analysis/results/deep_analysis/validation_checks.csv`
- Create: `docs/07_competition_submission_master.md`

**Interfaces:**
- Consumes: verified workspace outputs listed above
- Produces: the “문서 사용법”, “한눈에 보는 결론”, and “근거 수준” sections in `docs/07_competition_submission_master.md`

- [ ] **Step 1: Create the document header and evidence taxonomy**

Write the title, intended audience, analysis scope, and the five evidence classes:

```markdown
| 등급 | 의미 | 사용 원칙 |
|---|---|---|
| A — 견고 | 관측자료나 데이터 품질로 직접 확인 | 정의와 범위를 붙여 단정 가능 |
| A — 모델 내 견고 | 여러 민감도 분석에서 방향 유지 | 현실 검증과 구분해 방향 단정 |
| B — 유망 | 외표본 또는 반복성 검증을 통과 | 잠정 지수 내부 결과로 표현 |
| C — 가정 의존 | 미검증 가정이 순위·크기를 결정 | 조건부 시나리오로만 표현 |
| 판단 불가 | 자료 부족 또는 구조적 교란 | 제출의 결과 주장으로 사용 금지 |
```

- [ ] **Step 2: Add the executive evidence table**

Include, at minimum:

- 9월 3일 연기 `+14.0%`, year-cluster interval `+10.0% to +18.3%`
- 10월 3일 연기 `+16.1%`, year-cluster interval `+12.0% to +20.6%`
- common low-risk window `09-13 to 09-17`
- rolling forecast decision improvements `5.6%` for three days and `7.4%` for seven days
- East Siberian navigable days `53` versus Kara `121`
- ice contribution `51.0%` to mean level and `81.7%` to variance
- ARAON pressure-valid rates `1.6%, 0%, 0%` for 2023–2025

- [ ] **Step 3: Verify the executive values against source CSV files**

Run:

```bash
.venv/bin/python -c "import pandas as pd; p='nsr_analysis/results/deep_analysis/'; d=pd.read_csv(p+'delay_robustness.csv'); print(d[(d.region=='ALL') & d.month.astype(str).isin(['9','10'])][['month','mean_relative_pct','cluster_mean_ci_low','cluster_mean_ci_high']].to_string(index=False)); print(pd.read_csv(p+'corridor_window.csv').to_string(index=False)); print(pd.read_csv(p+'rolling_forecast_summary.csv').to_string(index=False))"
```

Expected: the printed values match the executive evidence table exactly after rounding.

- [ ] **Step 4: Commit the evidence framework**

```bash
git add docs/07_competition_submission_master.md
git commit -m "docs: add competition evidence framework"
```

---

### Task 2: Write the Full Team Master Narrative

**Files:**
- Modify: `docs/07_competition_submission_master.md`

**Interfaces:**
- Consumes: the evidence taxonomy and executive table from Task 1
- Produces: complete competition narrative, detailed findings, model audit, data corrections, writing kit, and priority actions

- [ ] **Step 1: Write the recommended submission storyline**

Use this exact logical sequence:

1. Full-route risk is determined by segment bottlenecks, not route-wide averages.
2. Departure timing is a controllable operational decision.
3. Delaying departure has a skewed distribution and becomes robustly harmful late in the season.
4. A repeatable corridor-wide low-risk window can be identified.
5. Short-horizon prediction can select lower realized AURORA-index states out of sample.
6. Inputs are externally validated, but actual cargo-vessel behavior and insurance loss remain unvalidated.

- [ ] **Step 2: Write each detailed result using a consistent template**

For each result, include these six subsections:

```markdown
#### 정의
#### 데이터와 표본
#### 핵심 수치
#### 의미
#### 제출용 문장
#### 제한사항
```

Cover the eight findings specified in the approved design:

1. late-season delay
2. tail-risk distribution
3. common low-risk window
4. rolling three-/seven-day forecast
5. East Siberian bottleneck
6. non-monotonic PC6/PC7 value
7. ERA5/NSIDC/ARAON validation
8. ARAON sensor defect

- [ ] **Step 3: Add the model-structure audit**

State explicitly:

- ice produces `51.0%` of mean risk level and `81.7%` of daily variance
- Chukchi environmental risk is the lowest (`0.335`) but PRGI raises final risk to `0.488`
- the Chukchi ranking is conditional on the unvalidated `45.4%` loss amplification
- all four 2015–2024 annual composite-risk trends are statistically unclear
- all 40 missing `swh_p90` observations occur in October in East Siberian or Laptev seas, and alternative imputations do not change the late-season direction

- [ ] **Step 4: Add corrected data definitions**

Include a correction table containing:

- six ARAON raw cruises versus five ERA5 validation cruises
- 2,528 total matched rows versus 2,450 temperature-valid pairs
- 1,326 Chukchi and 1,202 East Siberian matched rows
- six missing NSR transit years: 2014, 2017, and 2019–2022

- [ ] **Step 5: Add the report and presentation writing kit**

Provide:

- three title candidates
- one recommended title
- a 150–250 Korean-character abstract summary
- a six-to-eight-slide presentation structure
- recommended existing figure for each slide
- at least eight likely judge questions with concise, evidence-bounded answers
- a table of prohibited wording and approved replacement wording

- [ ] **Step 6: Add next-action priorities**

Order actions as:

1. PAME ASTD cargo-vessel AIS validation
2. operational SAR availability for PRGI
3. real route geometry and segment arrival-time propagation
4. missing CHNL transit years
5. official POLARIS RIO structure

- [ ] **Step 7: Commit the complete narrative**

```bash
git add docs/07_competition_submission_master.md
git commit -m "docs: complete competition team master"
```

---

### Task 3: Validate Consistency and Team Usability

**Files:**
- Verify: `docs/07_competition_submission_master.md`
- Read: `docs/superpowers/specs/2026-07-30-competition-team-master-doc-design.md`

**Interfaces:**
- Consumes: complete team master document
- Produces: a verified Markdown file with no placeholder, contradictory number, or unsupported claim

- [ ] **Step 1: Scan for unfinished or prohibited language**

Run:

```bash
rg -n "T[B]D|T[O]DO|보험료를 예측|사고를 [0-9]|POLARIS를 대체|해빙 감소.*통항 증가" docs/07_competition_submission_master.md
```

Expected: no unfinished markers; any prohibited phrase appears only inside a clearly labeled “금지 표현” example.

- [ ] **Step 2: Run numeric consistency assertions**

Run:

```bash
.venv/bin/python -c "from pathlib import Path; t=Path('docs/07_competition_submission_master.md').read_text(); required=['+14.0%','+16.1%','+10.0~+18.3%','+12.0~+20.6%','9월 13~17일','5.6%','7.4%','81.7%','2,528','2,450','1,326','1,202']; missing=[x for x in required if x not in t]; assert not missing, missing; print('numeric_text_checks_ok', len(required))"
```

Expected: `numeric_text_checks_ok 12`.

- [ ] **Step 3: Check internal links and Markdown structure**

Run:

```bash
rg -n "^#|^\|.*\|$|docs/|nsr_analysis/" docs/07_competition_submission_master.md
```

Expected: heading hierarchy is sequential, tables have header separators, and every local path exists.

- [ ] **Step 4: Check the final diff**

Run:

```bash
git diff --check HEAD~2 -- docs/07_competition_submission_master.md
```

Expected: no whitespace errors.

- [ ] **Step 5: Final commit if validation required corrections**

```bash
git add docs/07_competition_submission_master.md
git commit -m "docs: validate competition team master"
```
