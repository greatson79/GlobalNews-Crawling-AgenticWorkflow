# 운영 가이드 — GlobalNews 크롤링 및 분석 시스템

이 가이드는 GlobalNews 파이프라인의 일상적인 운영을 담당하는 운영자를 위한 문서입니다. 모니터링, 예약 작업, 사이트 관리, 장애 처리, 데이터 아카이빙, 성능 튜닝을 다룹니다.

---

## 목차

1. [일일 모니터링](#1-daily-monitoring)
2. [크론 작업](#2-cron-jobs)
3. [신규 사이트 추가](#3-adding-a-new-site)
4. [차단된 사이트 처리](#4-handling-blocked-sites)
5. [Tier 6 에스컬레이션](#5-tier-6-escalation)
6. [데이터 아카이빙](#6-data-archival)
7. [자가 복구 시스템](#7-self-recovery-system)
8. [성능 튜닝](#8-performance-tuning)
9. [재해 복구](#9-disaster-recovery)

---

## 1. 일일 모니터링

매일 아침, 전날 밤의 파이프라인 실행이 성공했는지 확인합니다.

### 1.1 일일 로그 확인

```bash
# 오늘의 일일 로그
cat data/logs/daily/$(date +%Y-%m-%d)-daily.log

# SUCCESS 또는 FAILED 라인 검색
grep "GlobalNews Daily Pipeline --" data/logs/daily/$(date +%Y-%m-%d)-daily.log
```

성공 시 예상 출력:

```
[2026-02-26T02:47:12Z] [INFO]  GlobalNews Daily Pipeline -- SUCCESS
```

### 1.2 알림 확인

```bash
ls -la data/logs/alerts/
# 오늘 날짜의 파일이 있으면 처리가 필요한 장애가 발생한 것입니다
cat data/logs/alerts/$(date +%Y-%m-%d)-daily-failure.log 2>/dev/null || echo "No alerts."
```

### 1.3 수집 기사 수 확인

```bash
# 어제 날짜의 원본 JSONL 출력 확인
YESTERDAY=$(date -v -1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)
wc -l data/raw/${YESTERDAY}/all_articles.jsonl 2>/dev/null || echo "No articles file found."
```

목표: 전체 사이트 합산 하루 500건 이상. 지속적으로 300건 미만이면 차단된 사이트를 점검하십시오.

### 1.4 크롤 리포트 확인

```bash
# 크롤에서 생성된 구조화된 JSON 리포트
python3 -c "
import json
with open('data/raw/${YESTERDAY}/crawl_report.json') as f:
    r = json.load(f)
print(f\"Total articles: {r.get('total_articles', 0)}\")
print(f\"Sites attempted: {r.get('total_sites_attempted', 0)}\")
print(f\"Sites failed: {r.get('sites_failed', 0)}\")
print(f\"Elapsed: {r.get('elapsed_seconds', 0):.0f}s\")
" 2>/dev/null || echo "No crawl report found."
```

### 1.5 에러 로그 확인

```bash
# 최근 에러 (마지막 50줄)
tail -50 data/logs/errors.log

# 최근 24시간의 에러 건수 집계
grep "$(date +%Y-%m-%d)" data/logs/errors.log | wc -l
```

### 1.6 파이프라인 상태 확인

```bash
python3 main.py --mode status
```

설정 파일 상태, 사이트 수, 일일 기사 예상 수, 그룹별 현황, 데이터 디렉터리 목록을 표시합니다.

### 1.7 잠금 파일 확인

```bash
# 오래된 잠금 파일이 없는지 확인
python3 -m src.utils.self_recovery --check-lock daily
python3 -m src.utils.self_recovery --check-lock weekly
```

잠금이 오래된 경우(파이프라인이 정리 없이 종료된 경우) 강제로 해제합니다:

```bash
python3 -m src.utils.self_recovery --force-release-lock daily
```

---

## 2. 크론 작업

세 가지 예약 작업이 파이프라인을 자동화합니다. 크론 일정은 `config/crontab.txt`에 정의되어 있습니다.

### 2.1 일정 개요

| 일정 | 스크립트 | 목적 |
|------|---------|------|
| 매일 오전 02:00 | `scripts/run_daily.sh` | 전체 크롤 + 8단계 분석 |
| 매주 일요일 오전 01:00 | `scripts/run_weekly_rescan.sh` | 어댑터 상태 검증, 깨진 셀렉터 탐지 |
| 매월 1일 오전 03:00 | `scripts/archive_old_data.sh` | 30일 이상 된 데이터 압축 및 아카이빙 |

### 2.2 크론 작업 설치

1. `config/crontab.txt`를 열어 `PROJECT_DIR`을 실제 프로젝트 경로로 변경합니다:

```bash
# 템플릿 열기
nano config/crontab.txt

# 아래 줄을 수정합니다:
PROJECT_DIR=/path/to/GlobalNews-Crawling-AgenticWorkflow
```

2. 크론탭을 설치합니다:

```bash
# 기존 크론탭 교체 (주의: 모든 크론 작업이 덮어씌워짐)
crontab config/crontab.txt

# 또는 기존 크론탭에 추가 (더 안전한 방법)
(crontab -l 2>/dev/null; cat config/crontab.txt) | crontab -
```

3. 설치를 확인합니다:

```bash
crontab -l
```

### 2.3 크론 실행 확인

```bash
# 크론 로그 출력 확인
tail -20 data/logs/cron/daily.log
tail -20 data/logs/cron/weekly.log
tail -20 data/logs/cron/archive.log
```

### 2.4 크론 문제 해결

| 증상 | 원인 | 해결책 |
|------|------|--------|
| 크론이 실행되지 않음 | 크론탭에 `PATH`가 설정되지 않음 | `config/crontab.txt`의 `PATH` 라인 확인 |
| "No virtualenv found" | 가상 환경이 예상 위치에 없음 | 프로젝트 루트에 `.venv` 생성: `python3 -m venv .venv` |
| 잠금 획득 실패 | 이전 실행이 아직 진행 중이거나 비정상 종료됨 | `--check-lock daily`로 확인 후 오래된 경우 강제 해제 |
| 권한 거부 | 스크립트에 실행 권한 없음 | `chmod +x scripts/run_daily.sh scripts/run_weekly_rescan.sh scripts/archive_old_data.sh` |

### 2.5 수동 실행

크론 작업을 언제든 수동으로 실행할 수 있습니다:

```bash
# 일일 파이프라인 (특정 날짜 지정)
scripts/run_daily.sh --date 2026-02-25

# 일일 파이프라인 (드라이 런)
scripts/run_daily.sh --dry-run

# 주간 재스캔
scripts/run_weekly_rescan.sh

# 월간 아카이빙 (미리 보기용 드라이 런)
scripts/archive_old_data.sh --dry-run
```

---

## 3. 새 사이트 추가

이 섹션은 시스템에 45번째 사이트를 추가하는 과정을 단계별로 안내한다.

### 3.1 사전 조건

사이트를 추가하기 전에 다음 항목을 확인한다:

- **도메인**: 예: `example.com`
- **언어**: ISO 639-1 코드 (예: `en`, `ko`, `ja`)
- **그룹**: 해당 사이트가 속하는 그룹 (A-G)
- **RSS/사이트맵 제공 여부**: `https://example.com/rss`, `https://example.com/sitemap.xml` 확인
- **봇 차단(Bot-blocking) 수준**: LOW, MEDIUM, 또는 HIGH
- **유료화(Paywall) 유형**: `none`, `soft-metered`, 또는 `hard`

### 3.2 1단계: 사이트 어댑터(Adapter) 생성

`src/crawling/adapters/` 하위의 적절한 서브디렉터리에 새 어댑터 파일을 생성한다:

| 그룹 | 디렉터리 |
|-------|-----------|
| A (Korean Major), B (Korean Economy), C (Korean Niche) | `src/crawling/adapters/kr_major/` |
| D (Korean IT/Science) | `src/crawling/adapters/kr_tech/` |
| E (English-Language Western) | `src/crawling/adapters/english/` |
| F (Asia-Pacific), G (Europe/ME) | `src/crawling/adapters/multilingual/` |

예를 들어 `src/crawling/adapters/english/example.py` 파일을 아래와 같이 생성한다:

```python
"""Example News (example.com) site adapter.

Group E -- English-Language Western.
Primary method: RSS. Fallback: Sitemap > DOM.
Bot block level: LOW. Proxy: Not required.
"""

from __future__ import annotations

import logging
from src.crawling.adapters.base_adapter import BaseSiteAdapter

logger = logging.getLogger(__name__)


class ExampleAdapter(BaseSiteAdapter):
    """Adapter for Example News (example.com)."""

    # --- Site identity ---
    SITE_ID = "example"
    SITE_NAME = "Example News"
    SITE_URL = "https://www.example.com"
    LANGUAGE = "en"
    REGION = "us"
    GROUP = "E"

    # --- URL discovery ---
    RSS_URL = "https://www.example.com/rss/all"
    RSS_URLS = []
    SITEMAP_URL = "https://www.example.com/sitemap.xml"

    # --- Article extraction selectors ---
    TITLE_CSS = 'meta[property="og:title"]'
    TITLE_CSS_FALLBACK = "h1.article-title"
    BODY_CSS = "div.article-body"
    BODY_CSS_FALLBACK = "article"
    DATE_CSS = 'meta[property="article:published_time"]'
    AUTHOR_CSS = "span.byline"
    ARTICLE_LINK_CSS = 'a[href*="/article/"]'

    BODY_EXCLUDE_CSS = "script, style, iframe, div.ad-container"

    # --- Section pages for DOM discovery ---
    SECTION_URLS = [
        "https://www.example.com/world",
        "https://www.example.com/business",
        "https://www.example.com/technology",
    ]
    PAGINATION_TYPE = "page_number"
    PAGINATION_PARAM = "page"
    MAX_PAGES = 5

    # --- Rate limiting ---
    RATE_LIMIT_SECONDS = 5
    MAX_REQUESTS_PER_HOUR = 720
    JITTER_SECONDS = 1

    # --- Anti-block ---
    ANTI_BLOCK_TIER = 1
    UA_TIER = 2
    REQUIRES_PROXY = False
    BOT_BLOCK_LEVEL = "LOW"

    # --- Paywall ---
    PAYWALL_TYPE = "none"
    CHARSET = "utf-8"
    RENDERING_REQUIRED = False
```

### 3.3 2단계: 어댑터 등록

서브패키지의 `__init__.py`에 어댑터를 추가한다. 영어권 사이트의 경우 `src/crawling/adapters/english/__init__.py`를 편집한다:

```python
from src.crawling.adapters.english.example import ExampleAdapter

ENGLISH_ADAPTERS["example"] = ExampleAdapter
```

### 3.4 3단계: sources.yaml에 추가

`data/config/sources.yaml`에 사이트 설정을 추가한다:

```yaml
  example:
    name: "Example News"
    url: "https://www.example.com"
    region: "us"
    language: "en"
    group: "E"
    crawl:
      primary_method: "rss"
      fallback_methods: ["sitemap", "dom"]
      rss_url: "https://www.example.com/rss/all"
      sitemap_url: "/sitemap.xml"
      rate_limit_seconds: 5
      crawl_delay_mandatory: null
      max_requests_per_hour: 720
      jitter_seconds: 1
    anti_block:
      ua_tier: 2
      default_escalation_tier: 1
      bot_block_level: "LOW"
      requires_proxy: false
    extraction:
      paywall_type: "none"
      rendering_required: false
      charset: "utf-8"
    meta:
      enabled: true
      daily_article_estimate: 100
      difficulty: "Easy"
```

### 3.5 4단계: 어댑터 테스트

```bash
# 1. Verify the adapter imports without errors
python3 -c "from src.crawling.adapters import get_adapter; a = get_adapter('example'); print(f'{a.SITE_ID}: OK')"

# 2. Dry-run crawl to check config validity
python3 main.py --mode crawl --sites example --dry-run

# 3. Test a live crawl (single site)
python3 main.py --mode crawl --sites example --date $(date +%Y-%m-%d)

# 4. Check output
wc -l data/raw/$(date +%Y-%m-%d)/all_articles.jsonl
```

### 3.6 5단계: 사이트 커버리지 검증 실행

```bash
python3 scripts/validate_site_coverage.py
```

`sources.yaml`에 등록된 모든 사이트에 어댑터가 존재하는지, 그 역방향도 일치하는지를 검증한다.

---

## 4. 차단된 사이트 처리

사이트가 크롤링 요청을 차단하기 시작하면, 시스템은 6단계 티어를 자동으로 순차 에스컬레이션(Escalation)한다.

### 4.1 진단 플로차트

```
Site returning errors or empty content
    |
    v
[1] Check robots.txt compliance
    - Is the site's robots.txt disallowing the paths you crawl?
    - Is the Crawl-delay being respected?
    |
    v
[2] Check UA rotation
    - Is the UA tier appropriate for the site's bot-block level?
    - Upgrade UA tier: T1 -> T2 -> T3 in sources.yaml
    |
    v
[3] Check rate limits
    - Increase rate_limit_seconds (e.g., 5 -> 10 -> 15)
    - Check if the site returns 429 or Retry-After headers
    |
    v
[4] Check anti-block tier
    - Current tier vs. block type (see block_detector.py for 7 types)
    - Increase default_escalation_tier in sources.yaml
    |
    v
[5] Check if proxy is needed
    - Geo-blocked sites require a regional proxy
    - Set requires_proxy: true and proxy_region: "XX"
    |
    v
[6] Manual intervention (Tier 6)
    - See Section 5 below
```

### 4.2 차단 유형 및 대응 방법

| 차단 유형 | 감지 방법 | 대응 방법 |
|------------|-----------|----------------|
| IP 차단 | 403 상태 코드, "access denied" 메시지 | 세션 순환 (T2), 프록시 로테이션 (T5) |
| UA 필터 | 406 상태 코드, 봇 인증 리다이렉트 | UA 티어 업그레이드 (T2/T3) |
| 요청 제한(Rate Limit) | 429 상태 코드, Retry-After 헤더 | 지연 시간 증가, Retry-After 준수 |
| CAPTCHA | reCAPTCHA/hCaptcha/Turnstile 마커 | 스텔스(Stealth) 브라우저 (T3/T4) |
| JS 챌린지 | Cloudflare 챌린지, 빈 응답 본문 | Playwright/Patchright (T3/T4) |
| 핑거프린트(Fingerprint) | TLS 거부, CDN 헤더와 함께 403 | Patchright 핑거프린트 스텔스 (T4) |
| 지역 차단(Geo-Block) | 지역 사이트로 리다이렉트 | 해당 지역 프록시 사용 (T5) |

### 4.3 봇 차단 방지 설정 조정

`data/config/sources.yaml`에서 해당 사이트 설정을 편집한다:

```yaml
  chosun:
    anti_block:
      ua_tier: 3                    # Was 2, upgraded due to UA detection
      default_escalation_tier: 2    # Was 1, start at session cycling
      bot_block_level: "HIGH"       # Was "MEDIUM"
      requires_proxy: true          # Enable proxy
      proxy_region: "kr"
    crawl:
      rate_limit_seconds: 10        # Was 5, increased to reduce detection
```

---

## 5. 티어 6 에스컬레이션

한 사이트에 대해 총 90회(5 × 2 × 3 × 3)의 재시도가 모두 소진되면 티어 6 에스컬레이션 보고서가 생성된다.

### 5.1 에스컬레이션 보고서 위치

```
logs/tier6-escalation/{site_id}-{date}.json
```

예시: `logs/tier6-escalation/chosun-2026-02-25.json`

### 5.2 에스컬레이션 보고서 읽기

```bash
python3 -c "
import json
with open('logs/tier6-escalation/chosun-2026-02-25.json') as f:
    report = json.load(f)
print(json.dumps(report, indent=2))
"
```

보고서에는 다음 항목이 포함된다:

- `site_id`: 실패한 사이트 식별자
- `date`: 발생 일시
- `total_attempts`: 시도 횟수 (최대 90회)
- `block_types_observed`: 감지된 차단 유형 목록
- `last_error`: 최종 에러 메시지
- `tier_history`: 에스컬레이션 티어 진행 이력
- `recommendation`: 권장 다음 조치

### 5.3 수동 개입 절차

1. **보고서를 읽어** 차단 유형과 진행 과정을 파악한다.

2. **브라우저로 직접 접속**하여 사이트가 여전히 접근 가능한지 확인한다:

```bash
# Quick check with curl
curl -s -o /dev/null -w "%{http_code}" https://www.example.com/

# Check with the system's network guard
python3 -c "
from src.crawling.network_guard import NetworkGuard
ng = NetworkGuard()
resp = ng.fetch('https://www.example.com/')
print(f'Status: {resp.status_code}, Length: {len(resp.body)}')
"
```

3. **어댑터를 업데이트**한다 — 사이트가 재설계되어 CSS 셀렉터가 변경된 경우.

4. 확인한 내용을 바탕으로 `data/config/sources.yaml`의 **봇 차단 방지 설정을 업데이트**한다.

5. **수정 사항을 테스트**한다:

```bash
python3 main.py --mode crawl --sites example --date $(date +%Y-%m-%d)
```

6. 해결 후 **오래된 에스컬레이션 보고서를 삭제**한다:

```bash
rm logs/tier6-escalation/example-*.json
```

---

## 6. 데이터 아카이빙

### 6.1 월별 아카이빙 동작 방식

`scripts/archive_old_data.sh` 스크립트는 매월 1일 오전 03:00에 실행된다. 실행 내용은 다음과 같다:

1. `data/raw/`와 `data/processed/`에서 30일을 초과한 날짜별 디렉터리를 탐색
2. `data/archive/YYYY/MM/`에 압축된 tar.gz 아카이브 생성
3. 각 아카이브에 대한 SHA-256 체크섬 생성
4. 원본 삭제 전 아카이브 무결성 검증
5. 2일 안전 마진 유지 (최근 2일은 아카이빙하지 않음)

### 6.2 아카이브 구조

```
data/archive/
  2026/
    01/
      raw-2026-01-15.tar.gz
      raw-2026-01-15.tar.gz.sha256
      processed-2026-01-15.tar.gz
      processed-2026-01-15.tar.gz.sha256
```

### 6.3 수동 아카이빙

```bash
# 아카이브 대상 미리 확인
scripts/archive_old_data.sh --dry-run

# 60일 이상 된 데이터 아카이브
scripts/archive_old_data.sh --days 60

# 일반 실행 (30일 기준)
scripts/archive_old_data.sh
```

### 6.4 아카이브 데이터 복원

```bash
# 사용 가능한 아카이브 목록 확인
ls data/archive/2026/01/

# 복원 전 체크섬 검증
cd data/archive/2026/01
shasum -a 256 -c raw-2026-01-15.tar.gz.sha256

# 원래 위치로 복원
tar -xzf raw-2026-01-15.tar.gz -C ../../raw/
```

---

## 7. 자체 복구 시스템

자체 복구 인프라를 통해 7일 이상 무인 운영을 지원하며, 자동 복구율 90% 이상을 달성한다.

### 7.1 구성 요소

| 구성 요소 | 목적 | CLI |
|-----------|------|-----|
| LockFileManager | PID 기반 잠금 파일, 장기 방치(4시간 초과) 감지 | `--acquire-lock`, `--release-lock`, `--check-lock` |
| HealthChecker | 실행 전 검증 (디스크, Python, 의존성, 설정) | `--health-check` |
| CheckpointManager | 파이프라인 진행 상태 추적, 충돌 후 재개 | `--checkpoint-status` |
| CleanupManager | 오래된 임시 파일 정리, 로그 순환 | `--cleanup` |
| RecoveryOrchestrator | 최상위 조율 | `--status` |

### 7.2 상태 확인(Health Check)

```bash
# 모든 상태 확인 실행
python3 -m src.utils.self_recovery --health-check
```

상태 확인 항목:

- **디스크 공간**: 2 GB 이상 여유 공간
- **Python 버전**: 3.11 이상
- **핵심 의존성**: 임포트 가능 여부 (yaml, requests, pyarrow 등)
- **설정 파일**: `data/config/sources.yaml` 및 `data/config/pipeline.yaml` 존재 및 유효성 확인
- **로그 디렉터리**: 쓰기 가능 여부

### 7.3 Circuit Breaker 상태

각 사이트는 세 가지 상태를 갖는 독립적인 Circuit Breaker를 보유한다:

```
CLOSED ----[5회 연속 실패]----> OPEN
   ^                                       |
   |                                   [300초 대기]
   |                                       |
   +----[3회 연속 성공]---- HALF_OPEN
```

- **CLOSED**: 정상 운영 상태. 실패 횟수를 카운트한다.
- **OPEN**: 해당 사이트를 건너뜀. 300초(5분) 후 HALF_OPEN으로 전환된다.
- **HALF_OPEN**: 단일 탐침 요청이 허용된다. 3회 연속 성공 시 CLOSED로 복귀하고, 실패 시 OPEN으로 돌아간다.

### 7.4 체크포인트 재개

분석 파이프라인이 중간 단계에서 충돌한 경우, 마지막으로 완료된 단계부터 재개할 수 있다:

```bash
# 체크포인트 상태 확인
python3 -m src.utils.self_recovery --checkpoint-status

# 특정 단계부터 분석 재개 (예: 3단계)
python3 main.py --mode analyze --stage 3
```

파이프라인은 각 단계를 시작하기 전 상위 Parquet 파일의 존재를 확인한다. N단계의 모든 의존 파일이 디스크에 존재하면 N단계를 독립적으로 실행할 수 있다.

### 7.5 수동 복구 명령어

```bash
# 전체 시스템 상태 확인
python3 -m src.utils.self_recovery --status

# 오래된 임시 파일 및 오래된 로그 정리
python3 -m src.utils.self_recovery --cleanup

# 장기 방치된 잠금 강제 해제
python3 -m src.utils.self_recovery --force-release-lock daily
```

---

## 8. 성능 튜닝

### 8.1 크롤링 동시성

크롤링 파이프라인은 각 그룹 내 사이트를 순차 처리하되, 최대 6개 그룹을 동시에 처리할 수 있다. `src/config/constants.py`의 주요 설정:

| 상수 | 기본값 | 설명 |
|------|--------|------|
| `MAX_CONCURRENT_CRAWL_GROUPS` | 6 | 병렬 처리 최대 그룹 수 |
| `DEFAULT_RATE_LIMIT_SECONDS` | 5 | 사이트별 요청 최소 간격(초) |
| `DEFAULT_REQUEST_TIMEOUT_SECONDS` | 30 | HTTP 요청 타임아웃 |
| `MAX_ARTICLES_PER_SITE_PER_DAY` | 1000 | 사이트별 일일 안전 상한선 |

### 8.2 분석 파이프라인 메모리 예산(Memory Budget)

각 분석 단계에는 메모리 예산(Memory Budget)이 설정되어 있다. RSS가 10 GB를 초과하면 파이프라인이 중단되고, 5 GB를 초과하면 경고가 발생한다. M2 Pro 16GB 기준 단계별 메모리 프로파일:

| 단계 | 설명 | 최대 메모리 |
|------|------|------------|
| 1 | 전처리(Preprocessing) | ~1.0 GB |
| 2 | 피처 추출(Feature Extraction)(SBERT) | ~2.4 GB |
| 3 | 기사 분석 | ~1.8 GB |
| 4 | 집계(Aggregation)(BERTopic) | ~1.5 GB |
| 5 | 시계열(Time Series) | ~0.5 GB |
| 6 | 교차 분석(Cross Analysis) | ~0.8 GB |
| 7 | 신호 분류(Signal Classification) | ~0.5 GB |
| 8 | 데이터 출력 | ~0.5 GB |

단계 사이에 `gc.collect()`를 호출하여 메모리를 해제한다. Torch CUDA/MPS 캐시도 함께 비워진다.

### 8.3 배치 크기

`data/config/pipeline.yaml` 또는 `src/config/constants.py`에서 조정한다:

| 상수 | 기본값 | 효과 |
|------|--------|------|
| `DEFAULT_BATCH_SIZE` | 500 | 일반 기사 배치 크기 |
| `SBERT_BATCH_SIZE` | 64 | SBERT 임베딩(Embedding) 배치 (M2 Pro 최적화) |
| `NER_BATCH_SIZE` | 32 | NER 처리 배치 |
| `KEYBERT_TOP_N` | 10 | 기사당 키워드 수 |

배치 크기를 줄이면 처리 속도가 낮아지는 대신 메모리 사용량이 감소한다.

### 8.4 파이프라인 타임아웃

일일 파이프라인 스크립트는 4시간 타임아웃을 적용한다:

```bash
# In scripts/run_daily.sh
PIPELINE_TIMEOUT=14400  # seconds (4 hours)
```

파이프라인이 지속적으로 타임아웃되는 경우:

1. 가장 느린 단계 확인 (`data/logs/analysis.log` 검토)
2. 크롤링 사이트 수 축소 (`--groups A,B,E`)
3. 배치 크기 축소
4. `data/config/pipeline.yaml`에서 선택적 분석 단계 비활성화 (`enabled: false` 설정)

---

## 9. 재해 복구

### 9.1 전체 재크롤

특정 날짜의 모든 사이트를 다시 크롤링하는 방법:

```bash
# 해당 날짜의 기존 데이터 삭제
rm -rf data/raw/2026-02-25/

# 재크롤 실행
python3 main.py --mode crawl --date 2026-02-25
```

### 9.2 분석 재실행

전체 분석 파이프라인을 다시 실행하는 방법:

```bash
# 처리된 데이터 삭제 (선택 사항 — 깨끗한 재실행 시)
rm -f data/processed/articles.parquet
rm -f data/features/*.parquet
rm -f data/analysis/*.parquet
rm -f data/output/*.parquet data/output/index.sqlite

# 모든 단계 재실행
python3 main.py --mode analyze --all-stages
```

특정 단계부터 재실행하는 방법:

```bash
# 4단계부터 재실행
python3 main.py --mode analyze --stage 4
python3 main.py --mode analyze --stage 5
python3 main.py --mode analyze --stage 6
python3 main.py --mode analyze --stage 7
python3 main.py --mode analyze --stage 8
```

### 9.3 아카이브에서 복원

```bash
# 전체 아카이브 목록 확인
find data/archive/ -name "*.tar.gz" | sort

# 특정 날짜 검증 및 복원
cd data/archive/2026/01
shasum -a 256 -c raw-2026-01-15.tar.gz.sha256
tar -xzf raw-2026-01-15.tar.gz -C ../../raw/

# 복원된 데이터에 대해 분석 재실행
python3 main.py --mode analyze --all-stages
```

### 9.4 데이터베이스 재구성

SQLite 인덱스가 손상된 경우 기존 Parquet 파일로부터 재구성한다:

```bash
# 손상된 데이터베이스 삭제
rm -f data/output/index.sqlite

# 8단계만 재실행 (Parquet에서 SQLite 구성)
python3 main.py --mode analyze --stage 8
```

### 9.5 초기화 리셋

모든 것을 초기화하고 새로 시작하는 방법:

```bash
# 모든 런타임 데이터 삭제 (파괴적 작업)
rm -rf data/raw/ data/processed/ data/features/ data/analysis/ data/output/ data/logs/

# 필수 디렉터리 재생성 (첫 실행 시 자동 생성됨)
mkdir -p data/config

# 필요 시 설정 파일 복사
# data/config/의 설정 파일은 이미 존재해야 함

# 전체 파이프라인 실행
python3 main.py --mode full --date $(date +%Y-%m-%d)
```

---

## 부록: 로그 파일 위치

| 로그 | 경로 | 순환 정책 |
|------|------|-----------|
| 일일 파이프라인 | `data/logs/daily/YYYY-MM-DD-daily.log` | 30일, 500 MB 초과 시 정리 |
| 크롤 로그 | `data/logs/crawl.log` | 10 MB, 백업 5개 |
| 분석 로그 | `data/logs/analysis.log` | 10 MB, 백업 5개 |
| 에러 로그 | `data/logs/errors.log` | 10 MB, 백업 5개 |
| 크론 일일 | `data/logs/cron/daily.log` | 수동 |
| 크론 주간 | `data/logs/cron/weekly.log` | 수동 |
| 크론 아카이브 | `data/logs/cron/archive.log` | 수동 |
| 알림 | `data/logs/alerts/YYYY-MM-DD-*.log` | 수동 검토 |
| 주간 재스캔 | `data/logs/weekly/rescan-YYYY-MM-DD.log` | 수동 |
| 주간 리포트 | `data/logs/weekly/rescan-YYYY-MM-DD.md` | 수동 |
| Tier 6 에스컬레이션 | `logs/tier6-escalation/{site}-{date}.json` | 수동 |
| 아카이빙 | `data/logs/archive/YYYY-MM-DD-archive.log` | 수동 |
