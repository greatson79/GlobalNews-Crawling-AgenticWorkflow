# GlobalNews 크롤링 및 분석 시스템

44개 국제 뉴스 사이트를 매일 크롤링하고, 56개 기법으로 구성된 8단계 NLP 분석 파이프라인을 실행하며, 소셜 트렌드 연구를 위한 Parquet/SQLite 데이터셋을 생산하는 단계별 모놀리스(Staged Monolith) Python 시스템이다. 자동 복구, 4단계 재시도, 6계층 봇 차단 에스컬레이션을 갖춰 macOS에서 무인 운영이 가능하도록 설계되었다.

---

## 목차

- [빠른 시작](#quick-start)
- [시스템 요구 사항](#system-requirements)
- [설치](#installation)
- [사용법](#usage)
- [디렉터리 구조](#directory-structure)
- [설정](#configuration)
- [분석 파이프라인](#analysis-pipeline)
- [5계층 신호 분류](#5-layer-signal-classification)
- [문제 해결](#troubleshooting)
- [참고 자료](#further-reading)
- [라이선스](#license)

---

## 빠른 시작

5분 이내에 시스템을 실행하고 첫 번째 크롤링을 완료하는 방법이다.

```bash
# 1. 저장소 클론
git clone https://github.com/your-org/GlobalNews-Crawling-AgenticWorkflow.git
cd GlobalNews-Crawling-AgenticWorkflow

# 2. 가상 환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. spaCy 영어 모델 다운로드
python3 -m spacy download en_core_web_sm

# 5. Playwright 브라우저 설치 (JS 렌더링 사이트에 필요)
playwright install chromium

# 6. 설정 확인
python3 main.py --mode status

# 7. 드라이 런으로 정상 동작 검증
python3 main.py --mode crawl --dry-run

# 8. 첫 번째 크롤링 실행 (오늘 날짜)
python3 main.py --mode crawl --date $(date +%Y-%m-%d)

# 9. 분석 파이프라인 실행
python3 main.py --mode analyze --all-stages

# 10. 결과 확인
ls -la data/output/
```

---

## 시스템 요구 사항

| 항목 | 사양 |
|-------------|--------------|
| **운영체제** | macOS (Apple Silicon M2 Pro 이상 권장) |
| **Python** | 3.12 이상 |
| **RAM** | 최소 16 GB (파이프라인 예산 10 GB) |
| **디스크** | 최소 여유 공간 5 GB (월간 데이터 약 2~4 GB) |
| **네트워크** | 안정적인 인터넷 연결 |
| **선택 사항** | GNU `timeout`용 `coreutils` (`brew install coreutils`) |

---

## 설치

### 1단계: Python 환경 설정

```bash
# Python 버전 확인 (3.12+ 필요)
python3 --version

# 가상 환경 생성
python3 -m venv .venv
source .venv/bin/activate
```

### 2단계: 의존성 설치

```bash
pip install -r requirements.txt
```

시스템은 44개 이상의 Python 패키지를 사용한다. 주요 의존성은 다음과 같다:

| 범주 | 패키지 |
|----------|----------|
| 크롤링 | httpx, beautifulsoup4, trafilatura, playwright, patchright |
| 한국어 NLP | kiwipiepy |
| 영어 NLP | spacy |
| 임베딩 | sentence-transformers, torch |
| 토픽 | bertopic, hdbscan |
| 시계열 | statsmodels, prophet, ruptures |
| 저장소 | pyarrow, duckdb, sqlite-vec |

### 3단계: NLP 모델 설치

```bash
# spaCy 영어 모델
python3 -m spacy download en_core_web_sm

# Playwright 브라우저
playwright install chromium
```

그 외 모델(SBERT, KoBERT, BERTopic)은 HuggingFace transformers가 첫 사용 시 자동으로 다운로드한다.

### 4단계: 설치 검증

```bash
python3 main.py --mode status
```

예상 출력:

```
============================================================
GlobalNews Crawling & Analysis System -- Status
============================================================

Configuration Files:
  sources.yaml:  FOUND (data/config/sources.yaml)
  pipeline.yaml: FOUND (data/config/pipeline.yaml)

  Sites: 44 total, 44 enabled
  Daily article estimate: ~6395
  Groups: A(5), B(4), C(3), D(7), E(12), F(6), G(7)

Data Directories:
  data/raw/:       EXISTS (0 files)
  data/processed/: MISSING (0 files)
  ...
```

### 5단계: 크론 설정 (선택, 일일 자동화용)

```bash
# crontab 템플릿에서 PROJECT_DIR 편집
nano config/crontab.txt

# 크론 작업 설치
(crontab -l 2>/dev/null; cat config/crontab.txt) | crontab -

# 확인
crontab -l
```

---

## 사용법

### CLI 명령어

시스템은 `main.py`를 통해 네 가지 모드로 제어한다.

#### Crawl 모드

설정된 모든 뉴스 사이트에서 URL을 탐색하고 기사를 추출한다.

```bash
# 오늘 날짜로 활성화된 모든 사이트 크롤링
python3 main.py --mode crawl

# 특정 날짜 크롤링
python3 main.py --mode crawl --date 2026-02-25

# 특정 사이트만 크롤링
python3 main.py --mode crawl --sites chosun,donga,yna

# 특정 그룹만 크롤링 (A=한국 주요 언론, E=영어권)
python3 main.py --mode crawl --groups A,E

# 드라이 런 (설정 검증, 계획 출력, 네트워크 요청 없음)
python3 main.py --mode crawl --dry-run
```

출력: `data/raw/YYYY-MM-DD/all_articles.jsonl`

#### Analyze 모드

크롤링된 기사에 대해 8단계 NLP 분석 파이프라인을 실행한다.

```bash
# 8개 단계 전체 실행
python3 main.py --mode analyze --all-stages

# 특정 단계만 실행 (예: 3단계)
python3 main.py --mode analyze --stage 3

# 드라이 런 (의존성 확인, 계획 출력)
python3 main.py --mode analyze --all-stages --dry-run
```

출력: `data/processed/`, `data/features/`, `data/analysis/`, `data/output/` 내 Parquet 파일

#### Full 모드

크롤링과 8개 분석 단계 전체를 순차적으로 실행한다.

```bash
# 오늘 날짜 전체 파이프라인 실행
python3 main.py --mode full

# 특정 날짜 전체 파이프라인 실행
python3 main.py --mode full --date 2026-02-25

# 전체 파이프라인 드라이 런
python3 main.py --mode full --dry-run
```

#### Status 모드

설정 요약 및 데이터 현황을 출력한다.

```bash
python3 main.py --mode status
```

### 공통 옵션

| 플래그 | 설명 |
|------|-------------|
| `--mode` | 필수. `crawl`, `analyze`, `full`, `status` 중 하나 |
| `--date YYYY-MM-DD` | 대상 날짜 (기본값: 오늘) |
| `--sites s1,s2,...` | 쉼표로 구분된 사이트 ID (기본값: 활성화된 전체) |
| `--groups A,B,...` | 쉼표로 구분된 그룹 문자 (기본값: 전체) |
| `--stage N` | 특정 분석 단계 1~8 (`--mode analyze`와 함께 사용) |
| `--all-stages` | 8개 분석 단계 전체 실행 |
| `--dry-run` | 실행 없이 검증만 수행 |
| `--log-level LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` (기본값: `INFO`) |
| `--version` | 버전 출력 |

### 자동화 스크립트

| 스크립트 | 실행 일정 | 목적 |
|--------|----------|---------|
| `scripts/run_daily.sh` | 매일 오전 02:00 | 잠금, 상태 점검, 타임아웃을 포함한 전체 파이프라인 실행 |
| `scripts/run_weekly_rescan.sh` | 매주 일요일 오전 01:00 | 어댑터 상태 및 사이트 구조 검증 |
| `scripts/archive_old_data.sh` | 매월 1일 오전 03:00 | 30일 이상 된 데이터 압축 및 아카이브 |

---

## 디렉터리 구조

```
GlobalNews-Crawling-AgenticWorkflow/
|
+-- main.py                              # CLI 진입점
+-- requirements.txt                     # Python 의존성 (44개 이상 패키지)
+-- pyproject.toml                       # 프로젝트 메타데이터, 도구 설정
|
+-- config/
|   +-- sources.yaml                     # 사이트 목록 초안 (44개 사이트, 7개 그룹)
|   +-- crontab.txt                      # Cron 스케줄 템플릿
|
+-- data/
|   +-- config/
|   |   +-- sources.yaml                 # 런타임 사이트 설정 (권위 있는 출처)
|   |   +-- pipeline.yaml               # 분석 파이프라인 설정
|   +-- raw/                             # 날짜별 JSONL 기사 (gitignored)
|   |   +-- YYYY-MM-DD/
|   |       +-- all_articles.jsonl       # 해당 날짜의 전체 기사
|   |       +-- crawl_report.json        # 사이트별 크롤링 통계
|   +-- processed/                       # 1단계 출력 (gitignored)
|   |   +-- articles.parquet             # 전처리된 기사 (12개 컬럼)
|   +-- features/                        # 2단계 출력 (gitignored)
|   |   +-- embeddings.parquet           # SBERT 384차원 임베딩
|   |   +-- tfidf.parquet                # TF-IDF 벡터
|   |   +-- ner.parquet                  # 개체명 인식 결과
|   +-- analysis/                        # 3~6단계 출력 (gitignored)
|   |   +-- article_analysis.parquet     # 감성, 감정, STEEPS
|   |   +-- topics.parquet               # BERTopic 토픽
|   |   +-- networks.parquet             # 동시 출현 네트워크
|   |   +-- timeseries.parquet           # 시계열 분해
|   |   +-- cross_analysis.parquet       # Granger, PCMCI, 교차 언어
|   +-- output/                          # 최종 출력 (gitignored)
|   |   +-- signals.parquet              # 5계층 신호 분류 (12개 컬럼)
|   |   +-- analysis.parquet             # 통합 분석 결과 (21개 컬럼)
|   |   +-- index.sqlite                 # FTS5 + 벡터 검색 인덱스
|   +-- models/                          # 캐시된 NLP 모델 (gitignored)
|   +-- logs/                            # 구조화된 JSON 로그 (gitignored)
|   |   +-- crawl.log                    # 크롤링 이벤트
|   |   +-- analysis.log                 # 분석 이벤트
|   |   +-- errors.log                   # 전체 오류
|   |   +-- daily/                       # 일별 파이프라인 로그
|   |   +-- weekly/                      # 주별 재스캔 보고서
|   |   +-- alerts/                      # 장애 알림
|   |   +-- cron/                        # Cron 출력 로그
|   +-- archive/                         # 압축된 구 데이터 (gitignored)
|   +-- dedup.sqlite                     # 중복 제거 데이터베이스 (gitignored)
|
+-- src/
|   +-- config/
|   |   +-- constants.py                 # 프로젝트 전역 상수
|   +-- crawling/
|   |   +-- pipeline.py                  # 크롤링 Orchestrator
|   |   +-- network_guard.py             # 복원력 있는 HTTP 클라이언트 (5회 재시도)
|   |   +-- url_discovery.py             # 3단계 URL 탐색 (RSS/Sitemap/DOM)
|   |   +-- article_extractor.py         # 다중 라이브러리 추출 체인
|   |   +-- dedup.py                     # 3단계 중복 제거 (URL/제목/SimHash)
|   |   +-- anti_block.py               # 6단계 에스컬레이션 엔진
|   |   +-- block_detector.py            # 7가지 유형의 차단 진단
|   |   +-- retry_manager.py             # 4단계 재시도 (최대 90회 시도)
|   |   +-- circuit_breaker.py           # 사이트별 Circuit Breaker
|   |   +-- ua_manager.py               # 4단계 User-Agent 로테이션 (61개 이상)
|   |   +-- session_manager.py           # 쿠키/헤더 관리
|   |   +-- stealth_browser.py           # Playwright/Patchright 스텔스
|   |   +-- url_normalizer.py            # URL 정규화
|   |   +-- contracts.py                 # RawArticle 데이터 계약
|   |   +-- crawler.py                   # JSONL 작성기, 크롤링 상태
|   |   +-- crawl_report.py              # 통계 보고서 생성기
|   |   +-- adapters/                    # 44개 사이트별 어댑터
|   |       +-- base_adapter.py          # 추상 기본 클래스
|   |       +-- kr_major/                # 그룹 A+B+C: 한국 사이트 11개
|   |       +-- kr_tech/                 # 그룹 D: 한국 IT/과학 8개
|   |       +-- english/                 # 그룹 E: 영어 사이트 12개
|   |       +-- multilingual/            # 그룹 F+G: 아시아태평양/유럽 13개
|   +-- analysis/
|   |   +-- pipeline.py                  # 8단계 Orchestrator
|   |   +-- stage1_preprocessing.py      # Kiwi + spaCy 토큰화
|   |   +-- stage2_features.py           # SBERT, TF-IDF, NER, KeyBERT
|   |   +-- stage3_article_analysis.py   # 감성, 감정, STEEPS
|   |   +-- stage4_aggregation.py        # BERTopic, HDBSCAN, 커뮤니티
|   |   +-- stage5_timeseries.py         # STL, PELT, Kleinberg, Prophet
|   |   +-- stage6_cross_analysis.py     # Granger, PCMCI, 네트워크 분석
|   |   +-- stage7_signals.py            # 5계층 L1-L5 분류
|   |   +-- stage8_output.py             # Parquet 병합 + SQLite 인덱스
|   +-- storage/
|   |   +-- parquet_writer.py            # 스키마 검증된 ZSTD Parquet
|   |   +-- sqlite_builder.py            # FTS5 + sqlite-vec 인덱스
|   +-- utils/
|       +-- config_loader.py             # YAML 설정 로딩/검증
|       +-- error_handler.py             # 예외 계층, circuit breaker
|       +-- logging_config.py            # 구조화된 JSON 로깅
|       +-- self_recovery.py             # 잠금 파일, 상태 확인, 체크포인트
|
+-- scripts/
|   +-- run_daily.sh                     # 일별 cron 래퍼 (4시간 타임아웃)
|   +-- run_weekly_rescan.sh             # 주별 어댑터 상태 확인
|   +-- archive_old_data.sh              # 월별 데이터 아카이빙
|
+-- testing/
|   +-- validate_e2e.py                  # 구조적 검증 (13개 체크)
|   +-- run_e2e_test.py                  # 라이브 E2E 테스트 실행기
|   +-- e2e-test-report.md               # 최신 검증 보고서
|
+-- docs/
    +-- operations-guide.md              # 일별 운영, cron, 사이트 추가
    +-- architecture-guide.md            # 시스템 설계, 데이터 흐름, 확장
```

---

## 설정

### sources.yaml

권위 있는 사이트 설정 파일은 `data/config/sources.yaml`에 위치한다. 각 사이트 항목의 구조는 다음과 같다.

```yaml
  chosun:                           # 사이트 ID (고유 키, 어댑터에서 사용)
    name: "Chosun Ilbo"             # 사람이 읽을 수 있는 이름
    url: "https://www.chosun.com"   # 표준 기본 URL
    region: "kr"                    # 지역 코드 (kr, us, uk, cn, jp, ...)
    language: "ko"                  # ISO 639-1 언어 코드
    group: "A"                      # 사이트 그룹 (A-G)
    crawl:
      primary_method: "rss"         # 기본 URL 탐색 방식 (rss, sitemap, api, playwright, dom)
      fallback_methods:             # 순서가 있는 대체 체인
        - "sitemap"
        - "dom"
      rss_url: "http://www.chosun.com/site/data/rss/rss.xml"
      sitemap_url: "/sitemap.xml"
      rate_limit_seconds: 5         # 요청 간 최소 지연 시간 (초)
      crawl_delay_mandatory: null   # robots.txt Crawl-delay (null = 미지정)
      max_requests_per_hour: 720    # 안전 상한선
      jitter_seconds: 0             # 지연에 추가되는 무작위 지터
    anti_block:
      ua_tier: 2                    # User-Agent 로테이션 티어 (1=봇, 2=데스크탑, 3=다양, 4=Patchright)
      default_escalation_tier: 1    # 차단 방지 시작 티어 (1-6)
      bot_block_level: "MEDIUM"     # 예상 차단 수준 (LOW, MEDIUM, HIGH)
      requires_proxy: false         # 프록시 필요 여부
      proxy_region: null            # 필요한 프록시 지역
    extraction:
      paywall_type: "none"          # none, soft-metered, hard
      rendering_required: false     # JS 렌더링 필요 여부
      charset: "utf-8"             # 문자 인코딩
    meta:
      enabled: true                 # 해당 사이트 크롤링 활성화 여부
      daily_article_estimate: 200   # 일별 예상 기사 수
      difficulty: "Medium"          # Easy, Medium, Hard, Extreme
```

### pipeline.yaml

분석 파이프라인 설정 파일은 `data/config/pipeline.yaml`에 위치한다. 주요 설정 항목은 다음과 같다.

```yaml
pipeline:
  global:
    max_memory_gb: 10               # 메모리 상한선 (초과 시 중단)
    gc_between_stages: true         # 단계 간 가비지 컬렉션 강제 실행
    parquet_compression: "zstd"     # 압축 알고리즘
    parquet_compression_level: 3    # ZSTD 압축 레벨
    batch_size_default: 500         # 기본 기사 배치 크기

  stages:
    stage_1_preprocessing:
      enabled: true
      memory_limit_gb: 1.5
      timeout_seconds: 1800
      models:
        - name: "kiwipiepy"
          singleton: true           # 1회 로딩 필수 (760 MB)
    # ... 2~8단계도 동일한 구조를 따른다
```

### 환경 변수

| 변수 | 용도 | 기본값 |
|----------|---------|---------|
| `GLOBALNEWS_LOG_LEVEL` | 로그 레벨 재정의 | `INFO` |
| `PROXY_URL` | 5단계 에스컬레이션용 HTTP 프록시 | 없음 |
| `PROXY_USERNAME` | 프록시 인증 | 없음 |
| `PROXY_PASSWORD` | 프록시 인증 | 없음 |

프록시 자격 증명은 안전하게 보관해야 한다 (예: macOS Keychain 또는 제한된 권한의 `.env` 파일).

### 사이트 그룹

| 그룹 | 지역 | 사이트 | 언어 |
|-------|--------|-------|-----------|
| A | 국내 주요 일간지 | 조선, 중앙, 동아, 한겨레, 연합 | ko |
| B | 국내 경제지 | MK, 한경, FNNews, 머니투데이 | ko |
| C | 국내 특화 | 국민, 노컷, 오마이뉴스 | ko |
| D | 국내 IT/과학 | 38노스, 블로터, ETNews, iRobot, 사이언스타임즈, TechNeedle, ZDNet | ko |
| E | 영어권 | Bloomberg, BuzzFeed, CNN, FT, HuffPost, LA Times, MarketWatch, National Post, NYT, VOA Korea, WSJ 외 | en |
| F | 아시아태평양 | Global Times, 인민일보, SCMP, Taiwan News, The Hindu, 요미우리 | zh, ja, en |
| G | 유럽/중동 | Al Jazeera, Arab News, Bild, Israel Hayom, Le Monde, Moscow Times, The Sun | ar, de, fr, he, en |

---

## 분석 파이프라인

8단계 분석 파이프라인은 원시 JSONL 기사를 구조화된 분석 데이터셋으로 변환한다.

| 단계 | 이름 | 기법 | 출력 |
|-------|------|-----------|--------|
| 1 | 전처리 | Kiwi 형태소 분석(한국어), spaCy 표제어 추출(영어), langdetect, 정규화 | `articles.parquet` |
| 2 | 피처 추출 | SBERT 임베딩, TF-IDF, NER, KeyBERT 키워드 | `embeddings.parquet`, `tfidf.parquet`, `ner.parquet` |
| 3 | 기사 분석 | 감성, 감정, STEEPS 분류, 논조 탐지 | `article_analysis.parquet` |
| 4 | 집계 | BERTopic, HDBSCAN 클러스터링, NMF/LDA, 커뮤니티 탐지 | `topics.parquet`, `networks.parquet` |
| 5 | 시계열 | STL 분해, Kleinberg 버스트, PELT 변화점, Prophet, 웨이블릿 | `timeseries.parquet` |
| 6 | 교차 분석 | Granger 인과성, PCMCI, 동시 출현, 교차 언어 토픽 정렬 | `cross_analysis.parquet` |
| 7 | 신호 분류 | 5계층 L1-L5 계층 구조, 이상치 탐지(LOF/IF), 특이점 점수화 | `signals.parquet` |
| 8 | 데이터 출력 | Parquet 병합, SQLite FTS5/vec 인덱싱 | `analysis.parquet`, `index.sqlite` |

---

## 5계층 신호 분류

시스템은 탐지된 신호를 시간적 지속성에 따라 5개 계층으로 분류한다.

| 계층 | 이름 | 지속 기간 | 특성 |
|-------|------|----------|-----------------|
| L1 | 일시적 유행 | 1주 미만 | 급등-급락, 단일 출처, 볼륨 Z-점수 > 3.0 |
| L2 | 단기 | 1~4주 | 2개 이상 출처, 기준선 대비 7일 이상 지속 |
| L3 | 중기 | 1~6개월 | 구조적 변화 지표, 변화점 유의성 > 0.8 |
| L4 | 장기 | 6개월 이상 | 제도적 도입, 임베딩 드리프트 > 0.3, 웨이블릿 주기 > 90일 |
| L5 | 특이점 | 전례 없음 | 복합 점수 >= 0.65, 독립적인 탐지 경로 3개 중 2개 충족 |

**특이점 복합 점수(Singularity Composite Score)**는 7개의 가중 지표를 사용한다.

```
Score = 0.20 * OOD_score
      + 0.15 * changepoint_score
      + 0.20 * cross_domain_score
      + 0.15 * BERTrend_score
      + 0.10 * entropy_change
      + 0.10 * novelty_score
      + 0.10 * network_anomaly
```

---

## 문제 해결

### 문제 1: 사이트가 크롤링 요청을 차단함 (R1)

**증상**: 403 상태 코드, 빈 기사 본문, HTML에 CAPTCHA 페이지가 나타남.

**해결 방법**:
1. 탐지된 차단 유형을 확인한다: `grep "block_detected" data/logs/crawl.log | tail -20`
2. `data/config/sources.yaml`에서 해당 사이트의 `ua_tier`를 높인다 (1 → 2 → 3)
3. `default_escalation_tier`를 높인다 (1 → 2 → 3)
4. `rate_limit_seconds`를 높인다 (5 → 10 → 15)
5. 지역 차단(geo-block)된 경우, 프록시를 활성화한다: `proxy_region`과 함께 `requires_proxy: true` 설정
6. 차단이 지속되면 `logs/tier6-escalation/`에서 상세 진단 정보를 확인한다

### 문제 2: BERTopic이 저품질 토픽을 생성함 (R2)

**증상**: 키워드가 일관되지 않은 토픽, 클러스터가 너무 많거나 너무 적음.

**해결 방법**:
1. 한국어 전처리(Preprocessing)가 정상 작동하는지 확인한다: `articles.parquet`에서 토크나이즈된 필드를 점검
2. Kiwi가 싱글턴(Singleton)으로 로드되었는지 확인한다 (로그에서 "Kiwi singleton" 메시지 확인)
3. `data/config/pipeline.yaml`의 스테이지 4 설정에서 `min_topic_size`를 조정한다
4. 토픽 모델링(Topic modeling)에는 최소 50개의 기사가 필요하다 (`constants`의 `MIN_ARTICLES_FOR_TOPICS` 참조)

### 문제 3: 메모리 부족(OOM) (R3)

**증상**: OS에 의한 프로세스 강제 종료, 로그에 "MemoryLimitError" 표시, 시스템 응답 없음.

**해결 방법**:
1. OOM을 유발한 스테이지를 확인한다: `grep "peak_memory" data/logs/analysis.log`
2. `src/config/constants.py`에서 `SBERT_BATCH_SIZE`를 줄인다 (기본값 64 → 32 시도)
3. `DEFAULT_BATCH_SIZE`를 줄인다 (기본값 500 → 250 시도)
4. `data/config/pipeline.yaml`에서 `gc_between_stages: true`로 설정되어 있는지 확인한다
5. 파이프라인 실행 중에는 다른 메모리 집약적 애플리케이션을 종료한다
6. 다음 명령으로 메모리를 모니터링한다: `python3 -c "import resource; print(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024, 'GB')"`

### 문제 4: 사이트 구조 변경으로 어댑터(Adapter)가 작동하지 않음 (R4)

**증상**: 이전에는 정상이던 사이트에서 기사가 0건 수집됨, 로그에 CSS 셀렉터 오류 발생.

**해결 방법**:
1. 주간 재스캔을 실행한다: `scripts/run_weekly_rescan.sh`
2. 재스캔 보고서를 확인한다: `cat data/logs/weekly/rescan-$(date +%Y-%m-%d).md`
3. 브라우저로 해당 사이트에 접속하여 현재 HTML 구조를 검사한다
4. 해당 사이트의 어댑터 파일에서 CSS 셀렉터를 업데이트한다 (예: `src/crawling/adapters/kr_major/chosun.py`)
5. 수정 사항을 테스트한다: `python3 main.py --mode crawl --sites chosun --date $(date +%Y-%m-%d)`

### 문제 5: 크롤링이 DDoS 공격으로 오인됨 (R5)

**증상**: 여러 사이트에서 IP 차단됨, ISP 경고 수신.

**해결 방법**:
1. 즉시 모든 크롤링을 중단한다: 실행 중인 `main.py` 프로세스를 모두 종료
2. 영향받은 사이트의 `rate_limit_seconds`를 높인다 (최소 10초)
3. robots.txt의 `Crawl-delay`가 준수되고 있는지 확인한다
4. 투명한 User-Agent를 사용한다 (T1 티어는 Googlebot 호환 UA를 포함)
5. 사이트당 `MAX_REQUESTS_PER_HOUR` 줄이는 것을 고려한다

### 문제 6: 분석 결과 품질 문제 (R6)

**증상**: 감성(Sentiment)이 항상 중립으로 분류됨, 언어 감지 오류, 개체명(NER) 누락.

**해결 방법**:
1. 스테이지 1 출력을 확인한다: `python3 -c "import pyarrow.parquet as pq; t = pq.read_table('data/processed/articles.parquet'); print(t.schema); print(t.num_rows)"`
2. 로그에서 언어 감지 정확도를 확인한다
3. spaCy 모델이 설치되어 있는지 확인한다: `python3 -m spacy validate`
4. SBERT 모델이 올바르게 다운로드되었는지 확인한다: 스테이지 2 로그에서 다운로드 오류를 검색

### 문제 7: 디스크 공간 부족 (R9)

**증상**: 헬스체크에서 "Insufficient disk space" 실패, 파이프라인 중단.

**해결 방법**:
1. 현재 사용량을 확인한다: `du -sh data/*/`
2. 즉시 아카이브를 실행한다: `scripts/archive_old_data.sh`
3. 긴급한 경우, 더 짧은 보존 기간으로 아카이브한다: `scripts/archive_old_data.sh --days 14`
4. 오래된 로그를 수동으로 삭제한다: `find data/logs/ -name "*.log" -mtime +30 -delete`
5. 아카이브 디렉터리를 확인한다: `du -sh data/archive/`

### 문제 8: Python/의존성 버전 충돌 (R10)

**증상**: ImportError, 버전 불일치 경고, "No module named X" 오류.

**해결 방법**:
1. Python 버전을 확인한다: `python3 --version` (3.12 이상이어야 함)
2. 가상 환경이 활성화되어 있는지 확인한다: `which python3` 출력이 `.venv/bin/python3`를 가리켜야 함
3. 모든 의존성을 재설치한다: `pip install -r requirements.txt --force-reinstall`
4. 헬스체크를 실행한다: `python3 -m src.utils.self_recovery --health-check`
5. 특정 실패를 확인한다: `python3 -c "import yaml; import pyarrow; import torch; print('OK')"`

### 문제 9: 동시 실행 충돌 (잠금 문제)

**증상**: "Lock acquisition failed" 오류, 두 개의 파이프라인 인스턴스가 동시에 실행됨.

**해결 방법**:
1. 잠금 상태를 확인한다: `python3 -m src.utils.self_recovery --check-lock daily`
2. 잠금이 오래된 경우(해당 프로세스가 더 이상 실행되지 않는 경우): `python3 -m src.utils.self_recovery --force-release-lock daily`
3. 오래된 잠금 임계값은 4시간으로, 이보다 오래된 잠금은 자동으로 감지된다
4. 파이프라인 프로세스가 실제로 실행 중인지 확인하려면: `ps aux | grep main.py`

### 문제 10: 파이프라인이 4시간 타임아웃을 초과함

**증상**: 일간 로그에 "Pipeline timed out" 표시, 알림 생성.

**해결 방법**:
1. 가장 느린 스테이지를 확인한다: `data/logs/analysis.log`에서 스테이지별 소요 시간 검토
2. 범위를 줄인다: `scripts/run_daily.sh`에서 `--groups A,B,E`로 더 적은 그룹만 크롤링
3. `data/config/pipeline.yaml`에서 배치 크기를 줄인다
4. 파이프라인 설정에서 `enabled: false`로 설정하여 필수적이지 않은 스테이지를 건너뛴다
5. 필요시 타임아웃을 늘린다: `scripts/run_daily.sh`에서 `PIPELINE_TIMEOUT=14400`을 수정
6. 체크포인트 재개를 사용한다: `python3 main.py --mode analyze --stage N`으로 마지막으로 완료된 스테이지부터 재시작

---

## 추가 자료

| 문서 | 설명 |
|------|------|
| [운영 가이드](operations-guide.md) | 일일 모니터링, cron 작업, 사이트 추가, 장애 처리 |
| [아키텍처 가이드](architecture-guide.md) | 시스템 설계, 모듈 인터페이스, 데이터 흐름, 확장 지점 |
| [E2E 테스트 보고서](../testing/e2e-test-report.md) | 최신 구조적 검증 결과 (검사 항목 13개, 어댑터 44개, 스테이지 8개) |
| [개발 가이드](../DEVELOPMENT.md) | 개발 환경 설정, 테스트, 디버깅, 기여 방법 |

---

## 라이선스

MIT 라이선스. 자세한 내용은 `pyproject.toml`을 참조한다.
