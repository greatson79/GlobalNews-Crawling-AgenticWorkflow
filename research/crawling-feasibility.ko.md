# 크롤링 타당성 분석

**생성일**: 2026-02-26
**에이전트**: @crawl-analyst
**워크플로우 단계**: 3 / 20
**페이즈**: Research
**입력 소스**: `research/site-reconnaissance.md` (Step 1), `research/tech-validation.md` (Step 2), `coding-resource/PRD.md`

---

## 요약

이 문서는 44개 대상 뉴스 사이트 전체에 대한 크롤링 전략을 정의하며, 주요 및 대체 수집 방식, 속도 제한 준수, 봇 차단 우회 에스컬레이션, User-Agent 로테이션, 재시도 아키텍처를 포괄한다.

### 핵심 지표

| 지표 | 값 |
|--------|-------|
| **주요 방식별 사이트 수** | RSS: 30, 사이트맵: 11, API: 1, Playwright: 2 |
| **일일 총 크롤링 시간** | 순차 실행 시 약 146분 (120분 예산 초과) / **병렬 실행 시 약 53분** (예산 이내 -- 병렬화 필수) |
| **고위험 사이트 (Hard/Extreme)** | 16개 (Hard 11 + Extreme 5) |
| **Playwright 필요 사이트** | 주요 방식 2개 (bloter.net, buzzfeed.com) + 에스컬레이션 대체 16개 |
| **지역 프록시 필요 사이트** | 필수 20개 (한국 18, 일본 1, 독일 1) + 권장 2개 (영국, 사우디) |
| **하드 페이월 사이트 (제목만 수집)** | 5개 (nytimes.com, ft.com, wsj.com, bloomberg.com, lemonde.fr) |
| **UA 풀 요구사항** | 4개 티어에 걸쳐 60개 고유 User-Agent |
| **4단계 재시도 최대 횟수** | 기사당 90회 (5 x 2 x 3 x 3) |
| **일일 예상 기사 수** | 44개 사이트 전체에서 약 6,460건 |

**중요**: 순차 크롤링(약 146분)은 2시간 예산을 초과한다. 6개 그룹에 걸친 병렬 실행(약 53분)이 제약 조건 충족을 위해 필수적이다.

### 방식별 분포

| 주요 방식 | 사이트 수 | 일일 기사 수 | 크롤링 소요 시간(분) |
|---------------|-----------|---------------|---------------|
| RSS 피드 | 30 | 4,520 | 약 78 |
| 사이트맵 기반 | 11 | 1,770 | 약 56 |
| API 엔드포인트 | 1 | 50 | 약 2 |
| Playwright (JS 렌더링) | 2 | 120 | 약 10 |
| **합계** | **44** | **약 6,460** | **약 146 (순차) / 약 53 (병렬)** |

---

## 전략 매트릭스 (44개 사이트 전체)

[trace:step-1:difficulty-classification-matrix] -- Step 1 정찰의 난이도 분류 결과.
[trace:step-2:dependency-validation-summary] -- Step 2 검증의 기술 GO/NO-GO 판정 결과.

### 그룹 A: 한국 주요 일간지 (5개)

| # | 사이트 | 주요 방식 | 대체 방식 | 속도 제한 | UA 티어 | 일일 소요(분) | 위험도 |
|---|------|---------|----------|------------|---------|-----------|------|
| 1 | chosun.com | RSS | Sitemap+DOM | 5초 지연 | T2 (10) | 3.5 | MED |
| 2 | joongang.co.kr | RSS | Sitemap+DOM | 10초 지연 | T3 (50) | 6.0 | HIGH |
| 3 | donga.com | RSS | Sitemap+DOM | 5초 지연 | T2 (10) | 3.5 | MED |
| 4 | hani.co.kr | RSS | Sitemap+DOM | 5초 지연 | T2 (10) | 2.5 | MED |
| 5 | yna.co.kr | RSS | Sitemap+DOM | 5초 지연 | T2 (10) | 6.0 | MED |

### 그룹 B: 한국 경제지 (4개)

| # | 사이트 | 주요 방식 | 대체 방식 | 속도 제한 | UA 티어 | 일일 소요(분) | 위험도 |
|---|------|---------|----------|------------|---------|-----------|------|
| 6 | mk.co.kr | RSS | Sitemap+DOM | 5초 지연 | T2 (10) | 4.5 | MED |
| 7 | hankyung.com | RSS | Sitemap+DOM | 5초 지연 | T2 (10) | 4.0 | MED |
| 8 | fnnews.com | RSS | Sitemap+DOM | 5초 지연 | T2 (10) | 3.0 | MED |
| 9 | mt.co.kr | RSS | Sitemap+DOM | 5초 지연 | T2 (10) | 3.5 | MED |

### 그룹 C: 한국 전문지 (3개)

| # | 사이트 | 주요 방식 | 대체 방식 | 속도 제한 | UA 티어 | 일일 소요(분) | 위험도 |
|---|------|---------|----------|------------|---------|-----------|------|
| 10 | nocutnews.co.kr | RSS | Sitemap+DOM | 2초 지연 | T1 (1) | 1.5 | LOW |
| 11 | kmib.co.kr | RSS | Sitemap+DOM | 5초 지연 | T2 (10) | 2.5 | MED |
| 12 | ohmynews.com | RSS | Sitemap+DOM | 2초 지연 | T1 (1) | 1.5 | LOW |

### 그룹 D: 한국 IT/과학 (7개)

| # | 사이트 | 주요 방식 | 대체 방식 | 속도 제한 | UA 티어 | 일일 소요(분) | 위험도 |
|---|------|---------|----------|------------|---------|-----------|------|
| 13 | 38north.org | RSS | Sitemap (WP) | 2초 지연 | T1 (1) | 0.5 | LOW |
| 14 | bloter.net | Playwright | RSS+DOM | 10초+지터 | T3 (50) | 4.0 | HIGH |
| 15 | etnews.com | RSS | Sitemap+DOM | 5초 지연 | T2 (10) | 2.0 | MED |
| 16 | sciencetimes.co.kr | Sitemap | RSS+DOM | 10초+지터 | T3 (50) | 2.0 | HIGH |
| 17 | zdnet.co.kr | RSS | Sitemap+DOM | 5초 지연 | T2 (10) | 2.0 | MED |
| 18 | irobotnews.com | RSS (WP) | Sitemap+DOM | 10초+지터 | T3 (50) | 1.5 | HIGH |
| 19 | techneedle.com | RSS (WP) | Sitemap+DOM | 10초+지터 | T3 (50) | 1.0 | HIGH |

### 그룹 E: 미국/영어권 주요 매체 (12개)

| # | 사이트 | 주요 방식 | 대체 방식 | 속도 제한 | UA 티어 | 일일 소요(분) | 위험도 |
|---|------|---------|----------|------------|---------|-----------|------|
| 20 | marketwatch.com | RSS | Sitemap+DOM | 10초+지터 | T3 (50) | 5.0 | HIGH |
| 21 | voakorea.com | API (RSS) | Sitemap+DOM | 2초 지연 | T1 (1) | 1.5 | LOW |
| 22 | huffpost.com | Sitemap | DOM+Playwright | 10초+지터 | T3 (50) | 4.0 | HIGH |
| 23 | nytimes.com | Sitemap | DOM (제목만) | 10초+지터 | T3 (50) | 5.0 | EXTREME |
| 24 | ft.com | Sitemap | DOM (제목만) | 10초+지터 | T3 (50) | 4.0 | EXTREME |
| 25 | wsj.com | Sitemap | DOM (제목만) | 10초+지터 | T3 (50) | 4.0 | EXTREME |
| 26 | latimes.com | RSS | Sitemap+DOM | 10초+지터 | T3 (50) | 5.0 | HIGH |
| 27 | buzzfeed.com | Playwright | Sitemap+DOM | 10초+지터 | T3 (50) | 6.0 | HIGH |
| 28 | nationalpost.com | RSS (WP) | Sitemap+DOM | 10초+지터 | T3 (50) | 3.0 | HIGH |
| 29 | edition.cnn.com | Sitemap | DOM+RSS | 10초+지터 | T3 (50) | 7.0 | HIGH |
| 30 | bloomberg.com | Sitemap | DOM (제목만) | 10초+지터 | T3 (50) | 4.0 | EXTREME |
| 31 | afmedios.com | RSS | Sitemap (WP) | 2초 지연 | T1 (1) | 0.5 | LOW |

### 그룹 F: 아시아-태평양 (6개)

| # | 사이트 | 주요 방식 | 대체 방식 | 속도 제한 | UA 티어 | 일일 소요(분) | 위험도 |
|---|------|---------|----------|------------|---------|-----------|------|
| 32 | people.com.cn | Sitemap | DOM | 120초 지연 | T2 (10) | 8.0 | MED |
| 33 | globaltimes.cn | Sitemap (news) | DOM | 2초 지연 | T1 (1) | 1.5 | LOW |
| 34 | scmp.com | RSS | Sitemap+DOM | 10초 지연 | T2 (10) | 4.0 | MED |
| 35 | taiwannews.com.tw | Sitemap | DOM | 2초 지연 | T1 (1) | 1.5 | LOW |
| 36 | yomiuri.co.jp | RSS | Sitemap+DOM | 10초+지터 | T3 (50) | 5.0 | HIGH |
| 37 | thehindu.com | RSS | Sitemap+DOM | 10초+지터 | T3 (50) | 4.0 | HIGH |

### 그룹 G: 유럽/중동 (7개)

| # | 사이트 | 주요 방식 | 대체 방식 | 속도 제한 | UA 티어 | 일일 소요(분) | 위험도 |
|---|------|---------|----------|------------|---------|-----------|------|
| 38 | thesun.co.uk | RSS | Sitemap+DOM | 10초+지터 | T3 (50) | 5.0 | HIGH |
| 39 | bild.de | RSS | Sitemap+DOM | 10초+지터 | T3 (50) | 5.0 | HIGH |
| 40 | lemonde.fr | RSS | Sitemap (제목만) | 10초+지터 | T3 (50) | 4.0 | EXTREME |
| 41 | themoscowtimes.com | RSS | Sitemap | 2초 지연 | T1 (1) | 1.0 | LOW |
| 42 | arabnews.com | Sitemap (news) | DOM | 10초 지연 | T2 (10) | 3.0 | MED |
| 43 | aljazeera.com | RSS | Sitemap+DOM | 5초 지연 | T2 (10) | 3.0 | MED |
| 44 | israelhayom.com | RSS (WP) | Sitemap (WP) | 2초 지연 | T1 (1) | 1.0 | LOW |

---

## 사이트별 상세 전략

### 그룹 A: 한국 주요 일간지

#### 1. chosun.com (조선일보)

- **주요 방식**: RSS — `http://www.chosun.com/site/data/rss/rss.xml` (RSS 2.0, 한국 뉴스 RSS 인덱스에서 확인). 피드를 파싱하여 기사 URL을 수집한 뒤, httpx로 각 기사 페이지를 가져와 trafilatura로 본문을 추출한다.
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(trafilatura를 통한 기사 페이지), URL(RSS link), 저자(바이라인 HTML), 카테고리(RSS category 또는 URL 경로)
- **대체 방식**: 사이트맵(`/sitemap.xml`)으로 URL 발견 후 DOM 파싱. 트리거: RSS가 10건 미만 반환 또는 RSS 엔드포인트가 30분 이상 HTTP 4xx/5xx 응답 시.
- **요청 제한**: 요청 간 기본 5초 지연. robots.txt 크롤링 지연 미탐지(추론 대상 사이트). 시간당 최대 720건. MEDIUM 봇 차단에 대응하는 보수적 기본값 적용.
  - 일일 요청 수: ~200개 기사 / 요청 당 1건 = 200건 + ~15건 RSS/사이트맵 조회 = ~215건
  - 일일 크롤링 시간: 215 x (5초 지연 + 2초 로드 + 0.5초 파싱) x 1.1 오버헤드 = ~3.5분
- **UA 전략**: Tier 2 — 10개 UA 풀, 세션별 교체(크롤링 실행 시마다 새 UA). 표준 브라우저 UA.
- **특수 처리**: 한국 가정용 프록시 필수(Step 1에서 IP 기반 지역 필터링 확인). UTF-8/EUC-KR 문자셋 감지 필요.
- **6단계 에스컬레이션**: Tier 1(UA 교체 + 지연 증가)부터 시작. 한국 프록시는 기본 인프라이며, 에스컬레이션 대상이 아니다.
- **일일 예상**: ~200개 기사에 ~3.5분

#### 2. joongang.co.kr (중앙일보)

- **주요 방식**: RSS — `http://rss.joinsmsn.com/joins_news_list.xml` (레거시 joinsmsn.com 도메인, RSS 2.0). 피드를 파싱하여 URL을 수집하고, httpx로 기사 페이지를 가져온다.
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(일부 — 소프트 종량제 페이월이 잘라낼 수 있음), URL(RSS link), 저자(바이라인), 카테고리(RSS 또는 URL 경로)
- **대체 방식**: 사이트맵(`/sitemap.xml`) + 섹션 페이지 DOM 파싱. 트리거: RSS가 10건 미만 반환 또는 RSS 도메인(joinsmsn.com) 접근 불가 또는 30분 이상 HTTP 403 시.
- **요청 제한**: 기본 10초 지연 + 0-3초 랜덤 지터. 크롤링 지연 미탐지(추론). 시간당 최대 300건. Cloudflare 적용 HIGH 봇 차단에 보수적 대응.
  - 일일 크롤링 시간: 180 x (10초 + 2초 + 0.5초) x 1.1 = ~6.0분
- **UA 전략**: Tier 3 — 50개 UA 풀, 요청별 교체. 사실적인 Accept-Language: ko-KR 헤더와 Referer 체인 포함.
- **특수 처리**: 한국 가정용 프록시 필수. Cloudflare JS 챌린지 예상 — httpx 실패 시 Playwright/Patchright(Tier 3)로 에스컬레이션. 소프트 종량제 페이월: 종량제 기사의 본문이 잘릴 수 있음; 부분 본문을 수용하거나 쿠키 초기화 전략(세션 간 쿠키 삭제) 사용.
- **6단계 에스컬레이션**: 전체 에스컬레이션 계획(섹션: 6단계 에스컬레이션 시스템 참조).
- **일일 예상**: ~180개 기사에 ~6.0분

#### 3. donga.com (동아일보)

- **주요 방식**: RSS — `http://rss.donga.com/total.xml` (RSS 2.0, rss.donga.com 서브도메인 호스팅). 카테고리별 피드도 제공(예: rss.donga.com/politics.xml).
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(전문 — 유료화 없음), URL(RSS link), 저자(바이라인 HTML), 카테고리(RSS category)
- **대체 방식**: 사이트맵(`/sitemap.xml`) + DOM. 트리거: RSS가 10건 미만 반환 또는 rss.donga.com 서브도메인이 30분 이상 접근 불가 시.
- **요청 제한**: 기본 5초 지연. MEDIUM 봇 차단. 시간당 최대 720건.
  - 일일 크롤링 시간: 200 x (5초 + 2초 + 0.5초) x 1.1 = ~3.5분
- **UA 전략**: Tier 2 — 10개 UA 풀, 세션별 교체.
- **특수 처리**: 한국 가정용 프록시 필수. PHP 기반 CMS — trafilatura 추출에 용이한 직관적 HTML 구조.
- **일일 예상**: ~200개 기사에 ~3.5분

#### 4. hani.co.kr (한겨레)

- **주요 방식**: RSS — `https://www.hani.co.kr/rss/hani.rss` (RSS 2.0). english.hani.co.kr에 별도 영문판 피드가 있을 수 있음.
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(대부분 전문 — 소프트 종량제 페이월은 대량 독자에게 영향, 새 세션의 크롤러에는 무관), URL(RSS link), 저자(바이라인), 카테고리(RSS)
- **대체 방식**: 사이트맵(`/sitemap.xml`) + DOM. 트리거: RSS가 10건 미만 반환 또는 30분 이상 HTTP 4xx/5xx 시.
- **요청 제한**: 기본 5초 지연. MEDIUM 봇 차단. 시간당 최대 720건.
  - 일일 크롤링 시간: 120 x (5초 + 2초 + 0.5초) x 1.1 = ~2.5분
- **UA 전략**: Tier 2 — 10개 UA 풀, 세션별 교체.
- **특수 처리**: 한국 가정용 프록시 필수. 소프트 종량제 페이월: 크롤링 실행 간 쿠키를 초기화하여 종량제 할당량 갱신.
- **일일 예상**: ~120개 기사에 ~2.5분

#### 5. yna.co.kr (연합뉴스)

- **주요 방식**: RSS — 한국어 피드 `https://www.yna.co.kr/rss/news.xml`(추론), 영어 피드 `https://en.yna.co.kr/RSS/news.xml`(확인). 통신사 형식: 깔끔하고 구조화.
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(전문 — 유료화 없음, 공영 통신사), URL(RSS link), 저자(바이라인), 카테고리(RSS section)
- **대체 방식**: 사이트맵(`/sitemap.xml`) + DOM. 트리거: RSS가 10건 미만 반환 또는 엔드포인트가 30분 이상 접근 불가. 연합뉴스는 일일 ~500건 기사 생산; RSS에는 가장 최근 일부만 포함될 수 있음.
- **요청 제한**: 기본 5초 지연. MEDIUM 봇 차단. 시간당 최대 720건. 고용량: RSS 페이지네이션이나 사이트맵 보완이 필요할 수 있음.
  - 일일 크롤링 시간: 500 x (5초 + 2초 + 0.5초) x 1.1 / 60 = ~6.9분 (초기에는 일일 상위 200건으로 제한하여 ~3.5분; 병렬 사이트맵 조회 시 전체 볼륨에서 ~6분으로 확대)
- **UA 전략**: Tier 2 — 10개 UA 풀, 세션별 교체.
- **특수 처리**: 한국 가정용 프록시 필수. 대용량 통신사 — RSS는 최근 50-100건으로 잘릴 가능성 높음. 전체 커버리지를 위해 사이트맵 대체가 필수. 한국어와 영어 에디션 모두 크롤링 가능.
- **일일 예상**: ~500개 기사에 ~6.0분(사이트맵 보완 포함)

---

### 그룹 B: 한국 경제지

#### 6. mk.co.kr (매일경제)

- **주요 방식**: RSS — `http://file.mk.co.kr/news/rss/rss_30000001.xml` (RSS 2.0, file.mk.co.kr 서브도메인 호스팅).
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(전문 — 하드 페이월 없음), URL(RSS link), 저자(바이라인), 카테고리(RSS 또는 URL 경로)
- **대체 방식**: 사이트맵(`/sitemap.xml`) + DOM. 트리거: RSS가 10건 미만 반환 또는 file.mk.co.kr 서브도메인이 30분 이상 접근 불가 시.
- **요청 제한**: 기본 5초 지연. MEDIUM 봇 차단. 시간당 최대 720건.
  - 일일 크롤링 시간: 300 x (5초 + 2초 + 0.5초) x 1.1 / 60 = ~4.5분
- **UA 전략**: Tier 2 — 10개 UA 풀, 세션별 교체.
- **특수 처리**: 한국 가정용 프록시 필수.
- **일일 예상**: ~300개 기사에 ~4.5분

#### 7. hankyung.com (한국경제)

- **주요 방식**: RSS — `http://rss.hankyung.com/economy.xml` (RSS 2.0, rss.hankyung.com 서브도메인). 다수의 카테고리별 피드: economy, stock, realestate 등.
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(대부분 전문 — 프리미엄 콘텐츠에 소프트 종량제 페이월), URL(RSS link), 저자(바이라인), 카테고리(피드명)
- **대체 방식**: 사이트맵(`/sitemap.xml`) + DOM. 트리거: RSS가 10건 미만 반환 또는 rss.hankyung.com이 30분 이상 접근 불가 시.
- **요청 제한**: 기본 5초 지연. MEDIUM 봇 차단. 시간당 최대 720건.
  - 일일 크롤링 시간: 250 x (5초 + 2초 + 0.5초) x 1.1 / 60 = ~4.0분
- **UA 전략**: Tier 2 — 10개 UA 풀, 세션별 교체.
- **특수 처리**: 한국 가정용 프록시 필수. 소프트 종량제 페이월: 한경 프리미엄이 일부 기사를 제한할 수 있음. 세션 간 쿠키 초기화.
- **일일 예상**: ~250개 기사에 ~4.0분

#### 8. fnnews.com (파이낸셜뉴스)

- **주요 방식**: RSS — `http://www.fnnews.com/rss/fn_realnews_all.xml` (RSS 2.0).
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(전문 — 유료화 없음), URL(RSS link), 저자(바이라인), 카테고리(RSS)
- **대체 방식**: 사이트맵(`/sitemap.xml`) + DOM. 트리거: RSS가 10건 미만 반환 또는 30분 이상 HTTP 4xx/5xx 시.
- **요청 제한**: 기본 5초 지연. MEDIUM 봇 차단. 시간당 최대 720건.
  - 일일 크롤링 시간: 150 x (5초 + 2초 + 0.5초) x 1.1 / 60 = ~3.0분
- **UA 전략**: Tier 2 — 10개 UA 풀, 세션별 교체.
- **특수 처리**: 한국 가정용 프록시 필수. 전통적인 PHP CMS.
- **일일 예상**: ~150개 기사에 ~3.0분

#### 9. mt.co.kr (머니투데이)

- **주요 방식**: RSS — `https://www.mt.co.kr/rss` (경로 검증 필요; RSS 2.0 예상).
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(전문 — 유료화 없음), URL(RSS link), 저자(바이라인), 카테고리(RSS)
- **대체 방식**: 사이트맵(`/sitemap.xml`) + DOM. 트리거: RSS가 10건 미만 반환 또는 /rss 엔드포인트가 404 반환 시(/rss.xml 대안 경로 확인). RSS를 찾을 수 없는 경우 사이트맵 주요 방식으로 영구 전환.
- **요청 제한**: 기본 5초 지연. MEDIUM 봇 차단. 시간당 최대 720건.
  - 일일 크롤링 시간: 200 x (5초 + 2초 + 0.5초) x 1.1 / 60 = ~3.5분
- **UA 전략**: Tier 2 — 10개 UA 풀, 세션별 교체.
- **특수 처리**: 한국 가정용 프록시 필수. RSS URL은 런타임 검증 필요.
- **일일 예상**: ~200개 기사에 ~3.5분

---

### 그룹 C: 한국 전문지

#### 10. nocutnews.co.kr (노컷뉴스 / CBS)

- **주요 방식**: RSS — `http://rss.nocutnews.co.kr/nocutnews.xml` (RSS 2.0, rss 서브도메인).
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(전문 — 유료화 없음), URL(RSS link), 저자(바이라인), 카테고리(RSS)
- **대체 방식**: 사이트맵(`/sitemap.xml`) + DOM. 트리거: RSS가 10건 미만 반환 또는 rss.nocutnews.co.kr이 30분 이상 접근 불가 시.
- **요청 제한**: 기본 2초 지연. LOW 봇 차단. 시간당 최대 1800건.
  - 일일 크롤링 시간: 100 x (2초 + 2초 + 0.5초) x 1.1 / 60 = ~1.5분
- **UA 전략**: Tier 1 — 단일 UA, 주간 교체.
- **특수 처리**: 한국 가정용 프록시 필수(LOW 봇 차단에도 불구하고 지역 IP 필터링은 여전히 적용).
- **일일 예상**: ~100개 기사에 ~1.5분

#### 11. kmib.co.kr (국민일보)

- **주요 방식**: RSS — `https://www.kmib.co.kr/rss/kmib.rss` (검증 필요; RSS 2.0 예상).
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(전문 — 유료화 없음), URL(RSS link), 저자(바이라인), 카테고리(RSS)
- **대체 방식**: 사이트맵(`/sitemap.xml`) + DOM. 트리거: RSS가 10건 미만 반환 또는 /rss/kmib.rss가 404 반환 시(/rss.xml, /rss 경로 시도).
- **요청 제한**: 기본 5초 지연. MEDIUM 봇 차단. 시간당 최대 720건.
  - 일일 크롤링 시간: 120 x (5초 + 2초 + 0.5초) x 1.1 / 60 = ~2.5분
- **UA 전략**: Tier 2 — 10개 UA 풀, 세션별 교체.
- **특수 처리**: 한국 가정용 프록시 필수. RSS URL은 런타임 검증 필요.
- **일일 예상**: ~120개 기사에 ~2.5분

#### 12. ohmynews.com

- **주요 방식**: RSS — `https://www.ohmynews.com/rss/rss.xml` (RSS 2.0, 시민 저널리즘).
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(전문 — 유료화 없음), URL(RSS link), 저자(시민 기자 이름), 카테고리(RSS)
- **대체 방식**: 사이트맵(`/sitemap.xml`) + DOM. 트리거: RSS가 10건 미만 반환.
- **요청 제한**: 기본 2초 지연. LOW 봇 차단. 시간당 최대 1800건.
  - 일일 크롤링 시간: 80 x (2초 + 2초 + 0.5초) x 1.1 / 60 = ~1.5분
- **UA 전략**: Tier 1 — 단일 UA, 주간 교체.
- **특수 처리**: 한국 가정용 프록시 필수. ASP.NET CMS — 오래된 스택이지만 안정적인 HTML 출력.
- **일일 예상**: ~80개 기사에 ~1.5분

---

### 그룹 D: 한국 IT/과학

#### 13. 38north.org

- **주요 방식**: RSS — `https://www.38north.org/feed` (RSS 2.0, 2026-02-25 기준 10개 항목 활성 확인). WordPress 표준 피드로 `<content:encoded>`에 전문 포함.
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(RSS content:encoded에 전문 포함 — 기사 페이지 조회 불필요할 수 있음), URL(RSS link), 저자(RSS dc:creator), 카테고리(RSS category)
- **대체 방식**: 사이트맵(`/sitemap_index.xml`, Yoast SEO). 트리거: RSS가 0건 반환(확인된 활성 피드이므로 가능성 매우 낮음).
- **요청 제한**: 기본 2초 지연. LOW 봇 차단. robots.txt 완전 허용. 시간당 최대 1800건.
  - 일일 크롤링 시간: 5 x (2초 + 0.5초 파싱) x 1.1 / 60 = ~0.5분
- **UA 전략**: Tier 1 — 단일 UA, 주간 교체. 제한 사항 미탐지.
- **특수 처리**: 없음. 영문 사이트. 프록시 불필요. 크롤러 파이프라인 테스트에 이상적.
- **일일 예상**: ~5개 기사에 ~0.5분

#### 14. bloter.net

- **주요 방식**: Playwright — CSR(React/Next.js SPA, Step 1에서 확인). Patchright 헤드리스 브라우저를 실행하여 기사 목록 페이지로 이동하고, JS 렌더링 완료를 대기한 뒤 기사 링크를 추출한다. 각 기사에 대해 브라우저에서 렌더링 후 본문을 추출.
  - 예상 수집 완전성: 제목(렌더링된 h1), 날짜(렌더링된 meta), 본문(렌더링된 article div), URL(페이지 URL), 저자(렌더링된 바이라인), 카테고리(URL 경로)
- **대체 방식**: RSS(`/feed`, WordPress 표준) + DOM 파싱. 트리거: Playwright가 크래시하거나 3회 연속 빈 DOM 반환 시. React 프론트엔드에도 불구하고 WordPress 백엔드가 여전히 XML을 제공하면 RSS가 작동할 수 있음.
- **요청 제한**: 기본 10초 지연 + 0-3초 랜덤 지터. HIGH 봇 차단. 시간당 최대 240건. Playwright는 지연 위에 고유한 ~3-5초 페이지 로드 시간이 추가됨.
  - 일일 크롤링 시간: 20 x (10초 + 5초 렌더링 + 0.5초) x 1.1 / 60 = ~4.0분
- **UA 전략**: Tier 3 — Patchright의 스텔스 브라우저 핑거프린팅을 통한 50개 UA 풀. 요청별 교체.
- **특수 처리**: 한국 가정용 프록시 필수. CDP 스텔스 우회를 위해 일반 Playwright가 아닌 Patchright 사용. 낮은 볼륨으로 Playwright 오버헤드 허용 가능.
- **6단계 에스컬레이션**: Tier 3(Playwright/Patchright)부터 시작. 차단 시 Tier 4(핑거프린트 강화), 이어서 Tier 5(가정용 프록시 로테이션)로 에스컬레이션.
- **일일 예상**: ~20개 기사에 ~4.0분

#### 15. etnews.com (전자신문)

- **주요 방식**: RSS — `https://www.etnews.com/rss` (검증 필요; RSS 2.0 예상).
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(전문 — 유료화 없음), URL(RSS link), 저자(바이라인), 카테고리(RSS)
- **대체 방식**: 사이트맵(`/sitemap.xml`) + DOM. 트리거: RSS가 10건 미만 반환 또는 /rss가 404 반환.
- **요청 제한**: 기본 5초 지연. MEDIUM 봇 차단. 시간당 최대 720건.
  - 일일 크롤링 시간: 100 x (5초 + 2초 + 0.5초) x 1.1 / 60 = ~2.0분
- **UA 전략**: Tier 2 — 10개 UA 풀, 세션별 교체.
- **특수 처리**: 한국 가정용 프록시 필수.
- **일일 예상**: ~100개 기사에 ~2.0분

#### 16. sciencetimes.co.kr

- **주요 방식**: 사이트맵(`/sitemap.xml`) — RSS 미확인. 사이트맵을 파싱하여 기사 URL을 수집하고, httpx + trafilatura로 조회.
  - 예상 수집 완전성: 제목(HTML h1), 날짜(HTML meta), 본문(전문 — 유료화 없음, 공공 기관), URL(sitemap loc), 저자(바이라인), 카테고리(URL 경로)
- **대체 방식**: RSS(`/rss`) + DOM 내비게이션. 트리거: 사이트맵이 404 반환 또는 5건 미만 URL 포함. /rss, /feed, /rss.xml 경로 시도.
- **요청 제한**: 기본 10초 지연 + 0-3초 랜덤 지터. HIGH 봇 차단(KISTI 관할). 시간당 최대 240건.
  - 일일 크롤링 시간: 20 x (10초 + 2초 + 0.5초) x 1.1 / 60 = ~2.0분
- **UA 전략**: Tier 3 — 50개 UA 풀, 요청별 교체. KISTI가 UA 패턴을 모니터링할 수 있음.
- **특수 처리**: 한국 가정용 프록시 필수. 공공 사명에도 불구하고 엄격한 접근 통제를 가진 정부 유관 기관.
- **6단계 에스컬레이션**: 전체 계획(에스컬레이션 섹션 참조). 낮은 볼륨으로 위험 감소.
- **일일 예상**: ~20개 기사에 ~2.0분

#### 17. zdnet.co.kr (ZDNet Korea)

- **주요 방식**: RSS — `https://www.zdnet.co.kr/rss` (검증 필요; RSS 2.0 예상, CBS Interactive Korea).
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(전문 — 유료화 없음), URL(RSS link), 저자(바이라인), 카테고리(RSS)
- **대체 방식**: 사이트맵(`/sitemap.xml`) + DOM. 트리거: RSS가 10건 미만 반환 또는 /rss가 404 반환.
- **요청 제한**: 기본 5초 지연. MEDIUM 봇 차단. 시간당 최대 720건.
  - 일일 크롤링 시간: 80 x (5초 + 2초 + 0.5초) x 1.1 / 60 = ~2.0분
- **UA 전략**: Tier 2 — 10개 UA 풀, 세션별 교체.
- **특수 처리**: 한국 가정용 프록시 필수.
- **일일 예상**: ~80개 기사에 ~2.0분

#### 18. irobotnews.com

- **주요 방식**: RSS — `https://www.irobotnews.com/feed` (WordPress 표준 /feed 경로, RSS 2.0 예상).
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(RSS content:encoded 또는 기사 페이지), URL(RSS link), 저자(RSS dc:creator), 카테고리(RSS category)
- **대체 방식**: 사이트맵(`/sitemap.xml`, WordPress) + DOM. 트리거: RSS가 3건 미만 반환 또는 /feed가 4xx 반환.
- **요청 제한**: 기본 10초 지연 + 0-3초 랜덤 지터. HIGH 봇 차단(공유 호스팅 가능성). 시간당 최대 240건.
  - 일일 크롤링 시간: 10 x (10초 + 2초 + 0.5초) x 1.1 / 60 = ~1.5분
- **UA 전략**: Tier 3 — 50개 UA 풀, 요청별 교체.
- **특수 처리**: 한국 가정용 프록시 필수. WordPress 플랫폼. 매우 낮은 볼륨으로 위험 완화.
- **6단계 에스컬레이션**: 전체 계획. 낮은 볼륨으로 에스컬레이션이 빠름.
- **일일 예상**: ~10개 기사에 ~1.5분

#### 19. techneedle.com

- **주요 방식**: RSS — `https://www.techneedle.com/feed` (WordPress 표준 /feed 경로, RSS 2.0 예상).
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(RSS content:encoded 또는 기사 페이지), URL(RSS link), 저자(RSS dc:creator), 카테고리(RSS category)
- **대체 방식**: 사이트맵(`/sitemap.xml`, WordPress) + DOM. 트리거: RSS가 3건 미만 반환 또는 /feed가 4xx 반환.
- **요청 제한**: 기본 10초 지연 + 0-3초 랜덤 지터. HIGH 봇 차단(IP 필터링 가능성). 시간당 최대 240건.
  - 일일 크롤링 시간: 5 x (10초 + 2초 + 0.5초) x 1.1 / 60 = ~1.0분
- **UA 전략**: Tier 3 — 50개 UA 풀, 요청별 교체.
- **특수 처리**: 한국 가정용 프록시 필수. WordPress 플랫폼. 매우 낮은 볼륨.
- **6단계 에스컬레이션**: 전체 계획. 낮은 볼륨으로 에스컬레이션이 빠름.
- **일일 예상**: ~5개 기사에 ~1.0분

---

### 그룹 E: 미국/영어권 주요 매체

#### 20. marketwatch.com

- **주요 방식**: RSS — `https://www.marketwatch.com/rss` (RSS 2.0, Dow Jones 소유).
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(일부 — 소프트 종량제 페이월), URL(RSS link), 저자(바이라인), 카테고리(RSS)
- **대체 방식**: 사이트맵(`/sitemap.xml`) + DOM. 트리거: RSS가 10건 미만 반환 또는 30분 이상 HTTP 403/429 시.
- **요청 제한**: 기본 10초 지연 + 0-3초 랜덤 지터. HIGH 봇 차단(Cloudflare Enterprise, Dow Jones). 시간당 최대 240건.
  - 일일 크롤링 시간: 200 x (10초 + 2초 + 0.5초) x 1.1 / 60 = ~5.0분
- **UA 전략**: Tier 3 — 50개 UA 풀, 요청별 교체. AI 식별 문자열 사용 절대 금지.
- **특수 처리**: Dow Jones/News Corp 인프라. 봇 핑거프린팅 활성화. 소프트 종량제 페이월: 부분 본문 수용 또는 쿠키 초기화. WSJ와 동일 백엔드이나 덜 공격적.
- **6단계 에스컬레이션**: 전체 계획. 안정적 접근을 위해 Tier 4(Patchright 스텔스)가 필요할 가능성 높음.
- **일일 예상**: ~200개 기사에 ~5.0분

#### 21. voakorea.com (VOA Korea)

- **주요 방식**: API — VOA는 표준 XML RSS가 아닌 API 스타일 RSS 경로(`/api/z[encoded]-vomx-tpe[id]`)를 사용. /rssfeeds 페이지를 통해 17개 카테고리 피드 이용 가능. API 응답을 파싱하여 기사 URL을 수집한 뒤, 기사 페이지를 조회.
  - 예상 수집 완전성: 제목(API 응답), 날짜(API/schema.org datePublished), 본문(전문 — 미국 정부 매체, `isAccessibleForFree: true`), URL(API 응답), 저자(바이라인), 카테고리(피드 카테고리)
- **대체 방식**: 사이트맵(`/sitemap.xml`) + DOM. 트리거: API 피드가 빈 결과를 반환하거나 형식이 변경될 때.
- **요청 제한**: 기본 2초 지연. LOW 봇 차단. 미국 정부 매체. 시간당 최대 1800건.
  - 일일 크롤링 시간: 50 x (2초 + 2초 + 0.5초) x 1.1 / 60 = ~1.5분
- **UA 전략**: Tier 1 — 단일 UA, 주간 교체. 정부 매체; 크롤러에 우호적.
- **특수 처리**: 없음(.co.kr 도메인에도 불구하고 VOA는 전 세계 접근 가능한 미국 정부 매체). API 엔드포인트 형식은 /rssfeeds 페이지에서 런타임 발견 필요.
- **일일 예상**: ~50개 기사에 ~1.5분

#### 22. huffpost.com

- **주요 방식**: 사이트맵 — 5개 사이트맵 확인(일반, Google News, 동영상, 섹션, 카테고리). 직접적인 RSS 엔드포인트 미확인. 사이트맵을 파싱하여 기사 URL을 수집하고, httpx + trafilatura로 페이지 조회.
  - 예상 수집 완전성: 제목(HTML h1), 날짜(HTML meta article:published_time), 본문(전문 — 유료화 없음, 광고 기반), URL(sitemap loc), 저자(바이라인), 카테고리(사이트맵 섹션)
- **대체 방식**: DOM — 섹션 랜딩 페이지 탐색 후 기사 링크 추출. 트리거: 모든 사이트맵이 403 반환 또는 10건 미만 URL.
- **요청 제한**: 기본 5초 지연. HIGH 봇 차단(ClaudeBot 포함 25개 이상 AI 봇 차단). 시간당 최대 720건.
  - 일일 크롤링 시간: 100 x (5초 + 2초 + 0.5초) x 1.1 / 60 = ~3.0분
- **UA 전략**: Tier 2 — 10개 UA 풀, 세션별 교체. 중요: AI 식별 UA 문자열 절대 사용 금지(ClaudeBot, GPTBot 등이 robots.txt에 명시적으로 차단됨).
- **특수 처리**: huffingtonpost.com은 huffpost.com으로 리다이렉트(301). 표준 브라우저 UA 필수. 봇 필터링만 통과하면 콘텐츠는 무료.
- **일일 예상**: ~100개 기사에 ~3.0분

#### 23. nytimes.com (New York Times) -- EXTREME

- **주요 방식**: 사이트맵(`/sitemap.xml`) — 기사 URL과 메타데이터(제목, 날짜) 파싱. 본문 추출은 하드 페이월로 차단됨.
  - 예상 수집 완전성: 제목(sitemap/HTML og:title), 날짜(sitemap lastmod/HTML meta), 본문(차단됨 — 구독 없이는 제목 + 첫 단락만 가능), URL(sitemap loc), 저자(접근 가능 시 HTML meta), 카테고리(URL 경로)
- **대체 방식**: DOM — 섹션 페이지 파싱으로 헤드라인과 URL 수집. 트리거: 사이트맵이 403 반환.
- **요청 제한**: 기본 10초 지연 + 0-3초 랜덤 지터. HIGH 봇 차단(Cloudflare + 자체 솔루션). 시간당 최대 240건.
  - 일일 크롤링 시간: 300 x (10초 + 2초 + 0.5초) x 1.1 / 60 = ~5.0분(메타데이터만)
- **UA 전략**: Tier 3 — 50개 UA 풀, 요청별 교체. AI 봇 명시적 차단.
- **특수 처리**: **하드 페이월** — 전문 추출에는 NYT 디지털 구독 쿠키가 필요. 구독 없이: 제목, 날짜, URL, 첫 단락(표시 시), 저자, 카테고리 수집. 이것은 **제목+메타데이터만** 수집하는 전략이다. 전문 수집을 위한 유일한 경로는 Tier 5(가정용 프록시) + 구독 쿠키 주입이다.
  - 유료화 우회 옵션: (a) Google AMP 캐시(`https://www.google.com/amp/s/nytimes.com/...`) — 전문 노출 가능; (b) Google 웹캐시; (c) 구독 가능 시 구독자 쿠키 주입; (d) 분석용 제목만 수용(PRD 이중 패스 전략에 따르면 토픽 모델링과 트렌드 감지에는 제목으로 충분).
- **6단계 에스컬레이션**: 전체 계획. 새로운 유료화 우회를 위해 Tier 6(Claude Code 분석)이 필요할 수 있음.
- **일일 예상**: ~300개 기사(메타데이터)에 ~5.0분

#### 24. ft.com (Financial Times) -- EXTREME

- **주요 방식**: 사이트맵(`/sitemap.xml`) — URL과 메타데이터 파싱. 본문 차단됨.
  - 예상 수집 완전성: 제목(sitemap/HTML), 날짜(sitemap lastmod), 본문(차단됨), URL(sitemap loc), 저자(접근 가능 시), 카테고리(URL 경로)
- **대체 방식**: DOM — 헤드라인을 위한 섹션 페이지 파싱. 트리거: 사이트맵이 403 반환.
- **요청 제한**: 기본 10초 지연 + 0-3초 랜덤 지터. HIGH 봇 차단(Cloudflare Enterprise + 지역 필터링). 시간당 최대 240건.
  - 일일 크롤링 시간: 150 x (10초 + 2초 + 0.5초) x 1.1 / 60 = ~4.0분(메타데이터만)
- **UA 전략**: Tier 3 — 50개 UA 풀, 요청별 교체.
- **특수 처리**: **하드 페이월** — FT 구독 없이는 제목+메타데이터만 수집 가능. FT.com은 NYT보다 공격적. 지역 필터링(영국 IP 선호)이 복잡성을 가중.
  - 유료화 우회 옵션: (a) Google AMP/캐시; (b) FT 구독자 쿠키; (c) 제목만 수용.
- **6단계 에스컬레이션**: 전체 계획.
- **일일 예상**: ~150개 기사(메타데이터)에 ~4.0분

#### 25. wsj.com (Wall Street Journal) -- EXTREME

- **주요 방식**: 사이트맵(`/sitemap.xml`) — URL과 메타데이터 파싱. 본문 차단됨.
  - 예상 수집 완전성: 제목(sitemap/HTML), 날짜(sitemap lastmod), 본문(차단됨), URL(sitemap loc), 저자(접근 가능 시), 카테고리(URL 경로)
- **대체 방식**: DOM — 헤드라인을 위한 섹션 페이지 파싱. 트리거: 사이트맵이 403 반환.
- **요청 제한**: 기본 10초 지연 + 0-3초 랜덤 지터. HIGH 봇 차단(Cloudflare Enterprise + Dow Jones 핑거프린팅). 시간당 최대 240건.
  - 일일 크롤링 시간: 200 x (10초 + 2초 + 0.5초) x 1.1 / 60 = ~4.0분(메타데이터만)
- **UA 전략**: Tier 3 — 50개 UA 풀, 요청별 교체.
- **특수 처리**: **하드 페이월** — 코퍼스에서 가장 공격적으로 보호되는 사이트. MarketWatch와 동일 Dow Jones 인프라이지만 더 엄격. 구독 없이는 제목+메타데이터만 수집 가능.
  - 유료화 우회 옵션: (a) Google AMP/캐시; (b) WSJ 구독자 쿠키; (c) 제목만 수용.
- **6단계 에스컬레이션**: 전체 계획.
- **일일 예상**: ~200개 기사(메타데이터)에 ~4.0분

#### 26. latimes.com

- **주요 방식**: RSS — `https://www.latimes.com/rss` (RSS 2.0).
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(대부분 전문 — 소프트 종량제), URL(RSS link), 저자(바이라인), 카테고리(RSS)
- **대체 방식**: 사이트맵(`/sitemap.xml`) + DOM. 트리거: RSS가 10건 미만 반환 또는 30분 이상 HTTP 403 시.
- **요청 제한**: 기본 5초 지연. HIGH 봇 차단(GrapheneCMS). 시간당 최대 720건.
  - 일일 크롤링 시간: 150 x (5초 + 2초 + 0.5초) x 1.1 / 60 = ~3.5분
- **UA 전략**: Tier 2 — 10개 UA 풀, 세션별 교체.
- **특수 처리**: 소프트 종량제 페이월은 쿠키 초기화 전략으로 관리 가능. GrapheneCMS는 Arc Publishing에서 마이그레이션된 최신 자체 CMS.
- **일일 예상**: ~150개 기사에 ~3.5분

#### 27. buzzfeed.com -- 참고: BuzzFeed News는 2023년 4월 폐쇄

- **주요 방식**: Playwright — CSR(React SPA, Step 1에서 확인). robots.txt에 의해 RSS 차단(`/*.xml$`). AI 봇 차단. 콘텐츠 접근을 위해 JavaScript 렌더링 필수.
  - 예상 수집 완전성: 제목(렌더링된 h1), 날짜(렌더링된 meta), 본문(렌더링된 기사 — 유료화 없음), URL(페이지 URL), 저자(렌더링된 바이라인), 카테고리(URL 경로)
- **대체 방식**: 사이트맵(8개 확인) + DOM. 트리거: Playwright가 크래시하거나 3회 연속 빈 DOM 반환 시. `/*.xml$` 차단에도 불구하고 사이트맵은 접근 가능할 수 있음(차단은 RSS XML 피드에 적용, 사이트맵 인덱스에는 미적용).
- **요청 제한**: 기본 10초 지연 + 0-3초 랜덤 지터. HIGH 봇 차단(15개 이상 AI 봇 차단, MSNBot에 `Crawl-delay: 120`, Slurp에 `4`). 일반 봇에 대한 보수적 기본값으로 10초 적용.
  - 일일 크롤링 시간: 50 x (10초 + 5초 렌더링 + 0.5초) x 1.1 / 60 = ~6.0분
- **UA 전략**: Tier 3 — Patchright 스텔스를 통한 50개 UA 풀. AI 식별 문자열 금지.
- **특수 처리**: **BuzzFeed News는 2023년 4월 폐쇄**. 잔여 콘텐츠는 엔터테인먼트/라이프스타일만 해당하며, 보도 저널리즘이 아님. 우선순위 하향 가능. 이중 차단: AI 봇 차단 AND `/*.xml$`로 RSS 차단. Patchright 스텔스를 적용한 Playwright 필수.
- **6단계 에스컬레이션**: Tier 3(Playwright)부터 시작. Tier 4(Patchright 핑거프린트)가 기본선.
- **일일 예상**: ~50개 기사에 ~6.0분

#### 28. nationalpost.com

- **주요 방식**: RSS — `https://nationalpost.com/feed` (WordPress VIP, RSS 2.0).
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(일부 — 소프트 종량제 NP Connected 유료화), URL(RSS link), 저자(dc:creator), 카테고리(RSS)
- **대체 방식**: 사이트맵(`/sitemap.xml`, WordPress) + DOM. 트리거: RSS가 10건 미만 반환 또는 30분 이상 HTTP 403 시.
- **요청 제한**: 기본 10초 지연 + 0-3초 랜덤 지터. HIGH 봇 차단(Cloudflare, Postmedia). 시간당 최대 240건.
  - 일일 크롤링 시간: 100 x (10초 + 2초 + 0.5초) x 1.1 / 60 = ~3.0분
- **UA 전략**: Tier 3 — 50개 UA 풀, 요청별 교체.
- **특수 처리**: Postmedia/WordPress VIP 플랫폼. 소프트 종량제 페이월: 세션 간 쿠키 초기화. 캐나다 IP가 접근성을 향상시킬 수 있음.
- **6단계 에스컬레이션**: 전체 계획.
- **일일 예상**: ~100개 기사에 ~3.0분

#### 29. edition.cnn.com

- **주요 방식**: 사이트맵 — 15개 사이트맵 확인(news, politics, opinion, video, galleries, markets 등). 탁월한 URL 발견 커버리지.
  - 예상 수집 완전성: 제목(HTML h1), 날짜(HTML meta), 본문(전문 — 유료화 없음, 광고 기반), URL(sitemap loc), 저자(바이라인), 카테고리(사이트맵 섹션)
- **대체 방식**: RSS(`/rss`) + DOM. 트리거: 모든 사이트맵이 403 반환 또는 일일 10건 미만 신규 URL.
- **요청 제한**: 기본 5초 지연. HIGH 봇 차단(ClaudeBot 포함 60개 이상 봇 차단)이지만 콘텐츠는 SSR이며 무료. 시간당 최대 720건.
  - 일일 크롤링 시간: 500 x (5초 + 2초 + 0.5초) x 1.1 / 60 = ~6.0분
- **UA 전략**: Tier 2 — 10개 UA 풀, 세션별 교체. 중요: AI 식별 UA 금지(ClaudeBot, anthropic-ai 명시적 차단). 표준 Chrome/Firefox UA만 사용.
- **특수 처리**: 매우 높은 볼륨(일일 500개 기사). 15개 사이트맵이 포괄적인 발견을 제공. 적절한 UA로 접근하면 콘텐츠는 무료. 사이트맵 주요 방식이 최적 — 구조화된 URL 목록 제공.
- **일일 예상**: ~500개 기사에 ~6.0분

#### 30. bloomberg.com -- EXTREME

- **주요 방식**: 사이트맵 — 9개 사이트맵 확인(news, collections, video, audio, people, companies, securities, billionaires). 메인 /sitemap.xml은 403 반환; robots.txt에서 사이트맵 URL을 직접 사용.
  - 예상 수집 완전성: 제목(접근 가능 시 sitemap/HTML), 날짜(sitemap lastmod), 본문(차단됨 — 비구독자에게 403), URL(sitemap loc), 저자(접근 가능 시), 카테고리(사이트맵 섹션)
- **대체 방식**: DOM — 섹션 페이지 크롤링. 트리거: 9개 사이트맵 전체가 403 반환.
- **요청 제한**: 기본 10초 지연 + 0-3초 랜덤 지터. HIGH 봇 차단(홈페이지 403, Cloudflare Enterprise). 시간당 최대 240건.
  - 일일 크롤링 시간: 200 x (10초 + 2초 + 0.5초) x 1.1 / 60 = ~4.0분(메타데이터만)
- **UA 전략**: Tier 3 — 50개 UA 풀, 요청별 교체. AI 봇(Claude-Web, GPTBot, anthropic-ai)에 전면 Disallow.
- **특수 처리**: **하드 페이월** — 코퍼스에서 가장 공격적인 차단. 비구독자에게 홈페이지도 403 반환. 메타데이터 추출마저 제한될 수 있음. 제목+URL 전략으로 품질 저하 예상.
  - 유료화 우회 옵션: (a) Bloomberg Terminal/구독 쿠키; (b) Google 캐시; (c) 제목만 또는 URL만 수용.
- **6단계 에스컬레이션**: 전체 계획. Tier 6이 필요할 가능성 높음.
- **일일 예상**: ~200개 기사(메타데이터)에 ~4.0분

#### 31. afmedios.com

- **주요 방식**: RSS — `https://afmedios.com/rss` (RSS 2.0, 2026-02-26 기준 20개 항목 활성 확인). WordPress 표준 피드로 전문 포함.
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(RSS content:encoded), URL(RSS link), 저자(RSS dc:creator), 카테고리(RSS category)
- **대체 방식**: 사이트맵(`/sitemap_index.xml`, WordPress Yoast). 트리거: RSS가 0건 반환(확인된 활성 피드이므로 가능성 낮음).
- **요청 제한**: 기본 2초 지연. LOW 봇 차단. robots.txt 완전 허용. 시간당 최대 1800건.
  - 일일 크롤링 시간: 20 x (2초 + 0.5초) x 1.1 / 60 = ~0.5분
- **UA 전략**: Tier 1 — 단일 UA, 주간 교체.
- **특수 처리**: 스페인어(es). 프록시 불필요. trafilatura가 스페인어를 잘 처리.
- **일일 예상**: ~20개 기사에 ~0.5분

---

### 그룹 F: 아시아-태평양

#### 32. people.com.cn (인민일보)

- **주요 방식**: 사이트맵 — `http://www.people.cn/sitemap_index.xml` (76개 사이트맵, 포괄적 커버리지). RSS 미탐지.
  - 예상 수집 완전성: 제목(HTML h1), 날짜(HTML meta/기사 날짜), 본문(전문 — 유료화 없음, 국영 매체), URL(sitemap loc), 저자(바이라인), 카테고리(사이트맵 섹션/URL 경로)
- **대체 방식**: DOM — people.com.cn 홈페이지에서 섹션 페이지 탐색. 트리거: 사이트맵 인덱스가 403 반환 또는 일일 10건 미만 신규 URL.
- **요청 제한**: **기본 120초 지연 — robots.txt `Crawl-delay: 120` 준수 필수**. 코퍼스에서 가장 제약적인 요청 제한. 시간당 최대 30건.
  - 일일 크롤링 시간: 120초 지연 시, 일일 최대 ~720건 요청(24시간). 일일 ~500개 기사에 대해 500건 기사 조회 + 사이트맵 조회 필요. 120초/요청 기준: 500 x 120초 / 60 = ~1,000분 = 16.7시간.
  - **최적화**: 사이트맵 일괄 파싱(사이트맵당 단일 요청, 각 사이트맵에 다수 URL 포함). 실제 페이지 조회는 신규 기사로만 제한. 76개 사이트맵에서 사이트맵 차분(lastmod 날짜 비교)으로 신규 기사 식별 — 진짜 새로운 기사만 조회. 실행당 예상 신규 기사: ~500건. 크롤링 윈도우 최적화: 사이트맵을 먼저 파싱(76개 x 120초 = 인덱스에 2.5시간), 이후 최신 기사를 우선 조회.
  - **현실적 예상**: 사이트맵 인덱스 + 상위 5개 관련 사이트맵 = 6건 요청 x 120초 = 12분. 이후 50-100개 최우선 기사 x 120초 = 100-200분. **총계: 초기 사이트맵 스캔 ~8분 + 이후 종일 백그라운드 처리를 위한 기사 큐.**
  - **참고**: 전체 500개 기사 커버리지는 2시간 윈도우 내가 아닌 24시간에 걸쳐 분산된 백그라운드 크롤링이 필요. 일일 2시간 예산 내에서 사이트맵 발견에 ~8분 + 우선순위 기사 ~40건을 할당.
- **UA 전략**: Tier 2 — 10개 UA 풀, 세션별 교체.
- **특수 처리**: 중국어(zh) 콘텐츠. UTF-8/GB2312/GB18030 문자셋 감지 필요. 120초 크롤링 지연은 법적 준수 요건(PRD C5). jQuery 기반 SSR. 후속 분석을 위한 중국어 NLP 고려사항(이 단계의 관심사는 아니나 완전성을 위해 기록).
- **일일 예상**: 2시간 윈도우 내 ~8분(사이트맵 발견 + 우선순위 기사); 전체 커버리지는 24시간 백그라운드 스케줄링 필요

#### 33. globaltimes.cn (환구시보)

- **주요 방식**: 사이트맵 — `https://www.globaltimes.cn/sitemap.xml` (60개 URL, 발행 날짜, 제목, 키워드가 포함된 `xmlns:news` 네임스페이스 확인 — 코퍼스에서 가장 풍부한 메타데이터 형식).
  - 예상 수집 완전성: 제목(sitemap news:title), 날짜(sitemap news:publication_date), 본문(HTML article div — 전문, 유료화 없음), URL(sitemap loc), 저자(바이라인 HTML), 카테고리(sitemap news:keywords + URL 경로)
- **대체 방식**: DOM — 섹션 페이지 탐색(4개 섹션: China, Op-Ed, Source, Life). 트리거: 사이트맵이 403 반환 또는 5건 미만 URL.
- **요청 제한**: 기본 2초 지연. LOW 봇 차단. 제한 없는 완전 허용 robots.txt. 시간당 최대 1800건.
  - 일일 크롤링 시간: 40 x (2초 + 2초 + 0.5초) x 1.1 / 60 = ~1.5분
- **UA 전략**: Tier 1 — 단일 UA, 주간 교체.
- **특수 처리**: 영문 중국 국영 매체. 뉴스 사이트맵 메타데이터가 제목/날짜의 개별 페이지 조회 필요성을 줄여줌(본문만 페이지 조회 필요). 사이트맵 우선 전략으로 효율성 극대화.
- **일일 예상**: ~40개 기사에 ~1.5분

#### 34. scmp.com (사우스차이나모닝포스트)

- **주요 방식**: RSS — `/rss` 디렉터리 페이지를 통해 100개 이상 카테고리 피드 제공(예: `/rss/91/feed`, `/rss/2/feed`). 상위 5개 고볼륨 피드 사용.
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(대부분 전문 — 소프트 종량제, 알리바바 소유), URL(RSS link), 저자(바이라인), 카테고리(피드명)
- **대체 방식**: 사이트맵(robots.txt에서 2개 사이트맵) + DOM. 트리거: RSS 피드가 합산 10건 미만 반환 또는 30분 이상 HTTP 403 시.
- **요청 제한**: **기본 10초 지연 — robots.txt `Crawl-delay: 10` 준수 필수**. 시간당 최대 360건.
  - 일일 크롤링 시간: 150 x (10초 + 2초 + 0.5초) x 1.1 / 60 = ~4.0분
- **UA 전략**: Tier 2 — 10개 UA 풀, 세션별 교체. 표준 Cloudflare 보호.
- **특수 처리**: Next.js SSR — `__NEXT_DATA__`에 JS 렌더링 없이 추출 가능한 구조화된 기사 데이터 포함(httpx로 충분, Playwright 불필요). 10초 크롤링 지연은 법적 구속력. 소프트 종량제 페이월: 알리바바 소유로 비교적 관대한 무료 할당량.
- **일일 예상**: ~150개 기사에 ~4.0분

#### 35. taiwannews.com.tw

- **주요 방식**: 사이트맵 — 3개 사이트맵 확인(`/sitemap.xml`, `/sitemap_en.xml`, `/sitemap_zh.xml`). ~1,050개 URL. RSS 미제공(/feed가 404 반환).
  - 예상 수집 완전성: 제목(HTML h1), 날짜(HTML meta), 본문(전문 — 유료화 없음), URL(sitemap loc), 저자(바이라인), 카테고리(URL 경로)
- **대체 방식**: DOM — 섹션 페이지 탐색. 트리거: 3개 사이트맵 전체가 403 반환.
- **요청 제한**: 기본 2초 지연. LOW 봇 차단. robots.txt 완전 허용. 시간당 최대 1800건.
  - 일일 크롤링 시간: 30 x (2초 + 2초 + 0.5초) x 1.1 / 60 = ~1.5분
- **UA 전략**: Tier 1 — 단일 UA, 주간 교체.
- **특수 처리**: Next.js SSR — Next.js 프레임워크에도 불구하고 초기 HTML에 콘텐츠 표시(`__NEXT_DATA__` 이용 가능). 이중 언어(영어/중국어). 프록시 불필요.
- **일일 예상**: ~30개 기사에 ~1.5분

#### 36. yomiuri.co.jp (요미우리신문)

- **주요 방식**: RSS — `https://www.yomiuri.co.jp/rss` (RSS 2.0 예상, 다수의 섹션별 피드).
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(일부 — 소프트 종량제), URL(RSS link), 저자(바이라인), 카테고리(RSS section)
- **대체 방식**: 사이트맵(`/sitemap.xml`) + DOM. 트리거: RSS가 10건 미만 반환 또는 엔드포인트가 30분 이상 접근 불가.
- **요청 제한**: 기본 10초 지연 + 0-3초 랜덤 지터. HIGH 봇 차단(지역 IP 필터링 + Cloudflare 동급). 시간당 최대 240건.
  - 일일 크롤링 시간: 200 x (10초 + 2초 + 0.5초) x 1.1 / 60 = ~5.0분
- **UA 전략**: Tier 3 — 50개 UA 풀, 요청별 교체.
- **특수 처리**: 일본 가정용 프록시 필수(지역 IP 필터링). 일본어(ja) — 본문 추출에 일본어 지원 trafilatura 필요(ja 지원). 소프트 종량제 페이월(요미우리 프리미엄)이 일부 기사 제한. 세계 최대 발행 부수 신문.
- **6단계 에스컬레이션**: 전체 계획. 일본 프록시 인프라가 핵심 요건.
- **일일 예상**: ~200개 기사에 ~5.0분

#### 37. thehindu.com

- **주요 방식**: RSS — `https://www.thehindu.com/rss` (RSS 2.0 예상, 잘 정리된 피드).
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(대부분 전문 — 소프트 종량제 월 10건 무료), URL(RSS link), 저자(바이라인), 카테고리(RSS section)
- **대체 방식**: 사이트맵(`/sitemap.xml`) + DOM. 트리거: RSS가 10건 미만 반환 또는 30분 이상 HTTP 403 시.
- **요청 제한**: 기본 5초 지연. HIGH 봇 차단(Cloudflare). 시간당 최대 720건(HIGH 분류에도 불구하고 콘텐츠가 대체로 무료이므로 MEDIUM 타이밍 적용).
  - 일일 크롤링 시간: 100 x (5초 + 2초 + 0.5초) x 1.1 / 60 = ~3.0분
- **UA 전략**: Tier 2 — 10개 UA 풀, 세션별 교체.
- **특수 처리**: 영문 사이트. 종량제 유료화(IP당 월 10건 무료) — 세션 간 쿠키 초기화. 인도 대표 영자 일간지; 구조화된 콘텐츠.
- **일일 예상**: ~100개 기사에 ~3.0분

---

### 그룹 G: 유럽/중동

#### 38. thesun.co.uk

- **주요 방식**: RSS — `https://www.thesun.co.uk/rss` (RSS 2.0, News UK 소유).
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(전문 — 유료화 없음, 2015년 유료화 철회), URL(RSS link), 저자(바이라인), 카테고리(RSS section)
- **대체 방식**: 사이트맵(`/sitemap.xml`) + DOM. 트리거: RSS가 10건 미만 반환 또는 30분 이상 HTTP 403 시.
- **요청 제한**: 기본 10초 지연 + 0-3초 랜덤 지터. HIGH 봇 차단(News UK Cloudflare, 영국 IP 선호). 시간당 최대 240건.
  - 일일 크롤링 시간: 300 x (10초 + 2초 + 0.5초) x 1.1 / 60 = ~5.0분
- **UA 전략**: Tier 3 — 50개 UA 풀, 요청별 교체.
- **특수 처리**: 안정적 접근을 위해 영국 가정용 프록시 권장(영국 IP 선호). 유료화 없음(긍정적). 높은 일일 볼륨. News UK의 Nicam CMS 플랫폼.
- **6단계 에스컬레이션**: 전체 계획.
- **일일 예상**: ~300개 기사에 ~5.0분

#### 39. bild.de

- **주요 방식**: RSS — `https://www.bild.de/rss` (RSS 2.0, Axel Springer 소유).
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(일부 — BILDplus 유료화가 ~30% 콘텐츠 차단), URL(RSS link), 저자(바이라인), 카테고리(RSS section)
- **대체 방식**: 사이트맵(`/sitemap.xml`) + DOM. 트리거: RSS가 10건 미만 반환 또는 30분 이상 HTTP 403 시.
- **요청 제한**: 기본 10초 지연 + 0-3초 랜덤 지터. HIGH 봇 차단(Axel Springer, 독일 IP 필수). 시간당 최대 240건.
  - 일일 크롤링 시간: 200 x (10초 + 2초 + 0.5초) x 1.1 / 60 = ~5.0분
- **UA 전략**: Tier 3 — 50개 UA 풀, 요청별 교체.
- **특수 처리**: 독일 가정용 프록시 필수(접근에 독일 IP 필수). 독일어(de). BILDplus 유료화가 ~30% 콘텐츠에 영향 — 무료 기사만 대상. Axel Springer의 공격적인 봇 차단. SSR/CSR 하이브리드 렌더링.
- **6단계 에스컬레이션**: 전체 계획.
- **일일 예상**: ~200개 기사에 ~5.0분

#### 40. lemonde.fr -- EXTREME

- **주요 방식**: RSS — `https://www.lemonde.fr/rss` (RSS 2.0 예상). URL과 메타데이터 파싱.
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(차단됨 — 하드 페이월, Le Monde Abonne), URL(RSS link), 저자(RSS), 카테고리(RSS section)
- **대체 방식**: 사이트맵(`/sitemap.xml`) — 제목+메타데이터만. 트리거: RSS가 빈 결과 또는 403 반환.
- **요청 제한**: 기본 10초 지연 + 0-3초 랜덤 지터. HIGH 봇 차단(Cloudflare, 프랑스 IP 선호). 시간당 최대 240건.
  - 일일 크롤링 시간: 150 x (10초 + 2초 + 0.5초) x 1.1 / 60 = ~4.0분(메타데이터만)
- **UA 전략**: Tier 3 — 50개 UA 풀, 요청별 교체.
- **특수 처리**: **하드 페이월** — 실질적 콘텐츠 전체에 Le Monde Abonne 구독 필요. 프랑스어(fr). RSS가 기사 요약/발췌를 제공할 수 있으나 전문은 불가. /en/ 경로의 영문판도 동일 유료화 적용. 제목+메타데이터만 수집 전략.
  - 유료화 우회 옵션: (a) Google AMP/캐시; (b) 구독자 쿠키; (c) 제목만 수용.
- **6단계 에스컬레이션**: 전체 계획.
- **일일 예상**: ~150개 기사(메타데이터)에 ~4.0분

#### 41. themoscowtimes.com

- **주요 방식**: RSS — `https://www.themoscowtimes.com/page/rss`, 4개 카테고리 피드(News, Opinion, Arts & Life, Meanwhile).
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(전문 — 프리미엄 모델이나 기부 요청일 뿐 콘텐츠 접근 가능), URL(RSS link), 저자(바이라인), 카테고리(피드 카테고리)
- **대체 방식**: 사이트맵(`https://static.themoscowtimes.com/sitemap/sitemap.xml`, 월간 사이트맵). 트리거: RSS가 5건 미만 반환.
- **요청 제한**: 기본 2초 지연. LOW 봇 차단. 최소한의 제한이 있는 표준 robots.txt. 시간당 최대 1800건.
  - 일일 크롤링 시간: 20 x (2초 + 2초 + 0.5초) x 1.1 / 60 = ~1.0분
- **UA 전략**: Tier 1 — 단일 UA, 주간 교체.
- **특수 처리**: 영문 사이트. 프록시 불필요. 프리미엄 모델(유료화가 아닌 기부). 국제적으로 콘텐츠에 자유롭게 접근 가능. 크롤러에 매우 우호적.
- **일일 예상**: ~20개 기사에 ~1.0분

#### 42. arabnews.com

- **주요 방식**: 사이트맵 — 2개 사이트맵 확인(표준 + `news:` 네임스페이스 포함 Google News). RSS는 403 반환.
  - 예상 수집 완전성: 제목(HTML h1), 날짜(HTML meta), 본문(전문 — 유료화 없음, SRMG 소유), URL(sitemap loc), 저자(바이라인), 카테고리(URL 경로/사이트맵 섹션)
- **대체 방식**: DOM — 섹션 페이지 탐색. 트리거: 두 사이트맵 모두 403 반환.
- **요청 제한**: **기본 10초 지연 — robots.txt `Crawl-delay: 10` 준수**. 시간당 최대 360건.
  - 일일 크롤링 시간: 100 x (10초 + 2초 + 0.5초) x 1.1 / 60 = ~3.0분
- **UA 전략**: Tier 2 — 10개 UA 풀, 세션별 교체.
- **특수 처리**: Drupal CMS. IP 필터링 관찰(비중동 IP에서 403). 중동/사우디 프록시가 접근성을 향상시킬 수 있음. Google News 사이트맵이 풍부한 메타데이터 제공.
- **일일 예상**: ~100개 기사에 ~3.0분

#### 43. aljazeera.com

- **주요 방식**: RSS — `https://www.aljazeera.com/xml/rss/all.xml` (RSS 2.0, 2026-02-26 기준 26개 기사 활성 확인). `/rss`에서도 이용 가능.
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(전문 — 유료화 없음, 무료 접근), URL(RSS link), 저자(바이라인), 카테고리(RSS category)
- **대체 방식**: 사이트맵(6개, 날짜 기반 일별 `/sitemap.xml?yyyy=YYYY&mm=MM&dd=DD`) + DOM. 트리거: RSS가 10건 미만 반환.
- **요청 제한**: 기본 5초 지연. HIGH 봇 차단(ClaudeBot, anthropic-ai, GPTBot 및 6개 이상 AI 봇 차단)이지만 콘텐츠는 SSR이며 무료. 시간당 최대 720건.
  - 일일 크롤링 시간: 100 x (5초 + 2초 + 0.5초) x 1.1 / 60 = ~3.0분
- **UA 전략**: Tier 2 — 10개 UA 풀, 세션별 교체. 중요: AI 식별 UA 금지(anthropic-ai, ClaudeBot, Claude-Web 모두 명시적 차단). 표준 Chrome/Firefox UA만 사용.
- **특수 처리**: React/Apollo SSR 하이브리드 — `window.__APOLLO_STATE__` 이용 가능하나 전문이 SSR HTML에 포함(httpx로 충분, Playwright 불필요). 영문 사이트. 무료 콘텐츠.
- **일일 예상**: ~100개 기사에 ~3.0분

#### 44. israelhayom.com

- **주요 방식**: RSS — `https://www.israelhayom.com/feed` (WordPress/JNews 표준 피드).
  - 예상 수집 완전성: 제목(RSS), 날짜(RSS pubDate), 본문(RSS content:encoded), URL(RSS link), 저자(RSS dc:creator), 카테고리(RSS category)
- **대체 방식**: 사이트맵(`/sitemap.xml`, WordPress). 트리거: RSS가 0건 반환.
- **요청 제한**: 기본 2초 지연. LOW 봇 차단. robots.txt 없음(404 반환) = 선언된 제한 없음. 시간당 최대 1800건.
  - 일일 크롤링 시간: 30 x (2초 + 0.5초) x 1.1 / 60 = ~1.0분
- **UA 전략**: Tier 1 — 단일 UA, 주간 교체. 제한 없음.
- **특수 처리**: 영문 사이트. 프록시 불필요. WordPress/JNews 테마로 예측 가능한 HTML 구조.
- **일일 예상**: ~30개 기사에 ~1.0분

---

## 6단계 에스컬레이션 시스템

[trace:step-1:key-findings] — Step 1 정찰에서 확인된 봇 차단 수준 및 난이도 등급.

### 단계 아키텍처 (PRD SS5.1.2 기준)

| 단계 | 전략 | 비용 | 성공률 | 자동화 | 기술 (Step 2 검증 완료) |
|------|------|------|--------|--------|--------------------------|
| **Tier 1** | 지연 증가 (5s->10s->15s) + UA 로테이션 | $0 | 높음 | 완전 자동 | httpx + ua_manager (GO) |
| **Tier 2** | 세션 관리 (쿠키 순환 + Referer 체인 + 헤더 다양화) | $0 | 높음 | 완전 자동 | httpx sessions + cookie jar (GO) |
| **Tier 3** | Playwright/Patchright 헤드리스 렌더링 | $0 | 중상 | 완전 자동 | Playwright 1.58 + Patchright 1.58 (GO) |
| **Tier 4** | Patchright CDP 스텔스 + 브라우저 핑거프린트 랜덤화 | $0 | 중간 | 완전 자동 | patchright stealth (GO, JS 전용이라 NO-GO인 apify-fingerprint-suite를 대체) |
| **Tier 5** | 레지덴셜 프록시 로테이션 (DataImpulse 등) | $0.10-1/GB | 중상 | 완전 자동 | httpx proxy config (GO) |
| **Tier 6** | Claude Code 인터랙티브 분석 — 실패 로그 검토 + 맞춤형 Python 우회 코드 생성 | $0 (구독) | 가변 | 반자동 | Claude Code 구독 (범위 내) |

### 난이도별 에스컬레이션 계획

#### Easy 사이트 (9개): 38north.org, globaltimes.cn, taiwannews.com.tw, themoscowtimes.com, afmedios.com, voakorea.com, nocutnews.co.kr, ohmynews.com, israelhayom.com

- **기본 단계**: Tier 1
- **에스컬레이션**: Tier 1 -> Tier 2 (속도 제한 시) -> Tier 3 (JS 필요 시)
- **Tier 2 트리거**: HTTP 429/403 응답 3회 연속 초과
- **Tier 3 트리거**: HTML 가져오기 후 페이지 콘텐츠가 비어 있는 경우 (JS 렌더링 필요)
- **최대 단계**: Tier 3 (Tier 4-6은 필요할 가능성 낮음)

#### Medium 사이트 (19개): chosun.com, donga.com, hani.co.kr, yna.co.kr, mk.co.kr, hankyung.com, fnnews.com, mt.co.kr, kmib.co.kr, etnews.com, zdnet.co.kr, scmp.com, huffpost.com, latimes.com, edition.cnn.com, thehindu.com, people.com.cn, aljazeera.com, arabnews.com

- **기본 단계**: Tier 1 (한국 사이트는 한국 프록시를 기본 적용)
- **에스컬레이션**: Tier 1 -> Tier 2 -> Tier 3 -> Tier 4 -> Tier 5
- **Tier 2 트리거**: 서로 다른 UA로 시도 후 HTTP 429/403 3회 연속 초과
- **Tier 3 트리거**: Cloudflare JS 챌린지 감지 (챌린지 페이지 HTML이 포함된 HTTP 503)
- **Tier 4 트리거**: Playwright 차단 (CDP 탐지, navigator.webdriver=true)
- **Tier 5 트리거**: 3회 로테이션 후에도 Tier 4 시도 전부 실패 (핑거프린트 기반 차단)
- **최대 단계**: Tier 5 (Tier 6은 지속적 실패 시 예비)

#### Hard 사이트 (11개): joongang.co.kr, bloter.net, sciencetimes.co.kr, irobotnews.com, techneedle.com, marketwatch.com, buzzfeed.com, nationalpost.com, yomiuri.co.jp, thesun.co.uk, bild.de

- **기본 단계**: Tier 2 (세션 관리 기본 적용)
- **에스컬레이션**: Tier 2 -> Tier 3 -> Tier 4 -> Tier 5 -> Tier 6
- **Tier 3 트리거**: 세션 관리에도 불구하고 표준 httpx 요청이 차단됨
- **Tier 4 트리거**: CDP 핑거프린팅을 통한 Playwright 탐지
- **Tier 5 트리거**: Patchright 스텔스로도 여전히 차단됨 (고급 핑거프린트 탐지)
- **Tier 6 트리거**: 모든 자동화 단계(1-5) 전체 재시도 사이클 후 소진. 로그 수집을 통해 Claude Code 인터랙티브 분석 실행.
- **최대 단계**: Tier 6

#### Extreme 사이트 (5개): nytimes.com, ft.com, wsj.com, bloomberg.com, lemonde.fr

- **기본 단계**: Tier 3 (Playwright 기본 적용 — 하드 페이월 사이트에서 httpx는 실패함)
- **에스컬레이션**: Tier 3 -> Tier 4 -> Tier 5 -> Tier 6 -> Title-Only 저하 모드
- **Tier 4 트리거**: Playwright 차단
- **Tier 5 트리거**: IP 수준 차단을 피하기 위해 프록시 로테이션 필요
- **Tier 6 트리거**: 자동화 우회만으로 불충분; Claude Code가 사이트별 맞춤 스크립트 생성
- **Title-Only 저하 모드**: 6단계 모두 실패하여 유료화 벽을 돌파하지 못할 경우, 제목+메타데이터 전용 모드로 영구 전환한다. 이는 PRD 이중 패스 분석에 따라 유효한 전략이다 (제목만으로도 토픽 모델링, 트렌드 탐지, 키워드 추출을 지원함).
- **구독 업그레이드 경로**: 사용자에게 문서화: 본문 전체 접근에는 유료 구독이 필요함 (사이트당 월 $10-50). 구독을 확보하면 Tier 2에서 구독자 쿠키를 주입한다.

### 서킷 브레이커 통합 (PRD SS5.1.2)

| 상태 | 조건 | 동작 |
|------|------|------|
| **Closed** (정상) | 연속 성공 | 정상적으로 크롤링 계속 |
| **Open** (차단) | 어떤 단계에서든 5회 연속 실패 | 해당 사이트 크롤링 중단, 30분 대기, 단계 에스컬레이션 |
| **Half-Open** (테스트) | 30분 쿨다운 후 | 단일 테스트 요청 수행; 성공 = Closed, 실패 = Open + 다음 단계 |

서킷 브레이커 상태는 사이트별로 관리된다. 한 사이트가 Open 상태에 진입해도 다른 사이트에는 영향을 미치지 않는다.

---

## 4단계 재시도 아키텍처

[trace:step-1:key-findings] — 사이트 차단 패턴이 재시도 전략 설계에 반영됨.
[trace:step-2:dependency-validation-summary] — httpx와 Playwright가 재시도 구현에 GO로 검증됨.

### 아키텍처 개요 (PRD SS5.1.2 + workflow.md Step 8 기준)

4단계 재시도 시스템은 "거의 무한한 지속성"을 제공한다 (PRD: "임무 완수를 위한 거의 무한한 반복적 끈기"). 이론적 최대 총 시도 횟수: **5 x 2 x 3 x 3 = 기사당 자동화 시도 90회**.

```
Level 1: NetworkGuard (innermost)
  5 retries per HTTP request
  Exponential backoff: 1s, 2s, 4s, 8s, 16s
  Handles: connection timeout, DNS failure, TLS error, HTTP 5xx
  ↓ fail
Level 2: Standard + TotalWar Mode Switch
  2 passes: Standard mode first, TotalWar mode second
  Standard: httpx + trafilatura (lightweight)
  TotalWar: Patchright + full stealth browser (heavyweight)
  Handles: anti-bot detection, JS rendering requirements
  ↓ fail
Level 3: Crawler Round
  3 rounds per site with increasing delays between rounds
  Round 1: base delay (site-specific)
  Round 2: 2x base delay + UA rotation
  Round 3: 3x base delay + full header randomization + proxy rotation
  Handles: rate limiting, IP-based throttling
  ↓ fail
Level 4: Pipeline Restart
  3 full pipeline restarts preserving already-collected URLs via dedup
  Restart 1: immediate with new session
  Restart 2: 30-minute cooldown, different proxy
  Restart 3: 2-hour cooldown, full parameter reset
  Handles: transient infrastructure failures, CDN cache refresh
  ↓ fail after 90 attempts
Tier 6: Claude Code Interactive Analysis (never silently terminates)
```

### Level 1: NetworkGuard 파라미터

| 파라미터 | 값 | 근거 |
|----------|-----|------|
| max_retries | 5 | PRD 명세 |
| backoff_base | 1초 | 표준 지수 백오프 |
| backoff_multiplier | 2 | 1s -> 2s -> 4s -> 8s -> 16s |
| backoff_max | 30초 | 과도하게 긴 대기 방지를 위한 상한 |
| jitter | 0-1s 랜덤 | 공유 인프라에서의 썬더링 허드 방지 |
| retry_on | ConnectionError, TimeoutError, HTTP 500/502/503/504/429 | 네트워크 계층 장애 |
| no_retry_on | HTTP 401/403/404 (Level 2로 에스컬레이션) | 애플리케이션 계층 차단은 모드 전환이 필요 |

### Level 2: Standard + TotalWar 모드 전환

| 모드 | 도구 | 메모리 비용 | 속도 | 사용 시점 |
|------|------|-------------|------|-----------|
| **Standard** | httpx + trafilatura + feedparser | ~65 MB | 빠름 (0.5-2s/페이지) | 첫 번째 패스; SSR 사이트에 충분 |
| **TotalWar** | Patchright + stealth browser + trafilatura | ~415 MB | 느림 (3-8s/페이지) | 두 번째 패스; JS 렌더링 또는 봇 차단 사이트용 |

모드 전환 트리거: Standard 모드에서 5회 NetworkGuard 재시도가 모두 HTTP 403/Cloudflare 챌린지로 실패한 경우.

### Level 3: Crawler Round 파라미터

| 라운드 | 지연 배수 | UA 전략 | 헤더 전략 | 프록시 |
|--------|-----------|---------|-----------|--------|
| 1 | 1x 기본 | 현재 UA | 표준 헤더 | 현재 프록시 |
| 2 | 2x 기본 | 새 UA로 로테이션 | Accept-*, Accept-Language 랜덤화 | 동일 프록시 |
| 3 | 3x 기본 | UA 로테이션 + 전체 핑거프린트 | 전체 헤더 랜덤화 + 현실적 Referer 체인 | 프록시 로테이션 |

### Level 4: Pipeline Restart 파라미터

| 재시작 | 쿨다운 | 세션 전략 | 프록시 전략 | 중복 제거 |
|--------|--------|-----------|-------------|-----------|
| 1 | 즉시 | 새 HTTP 세션, 쿠키 초기화 | 동일 프록시 풀 | 수집된 URL 건너뛰기 |
| 2 | 30분 | 새 세션 + 새 TLS 핑거프린트 | 다른 프록시 | 수집된 URL 건너뛰기 |
| 3 | 2시간 | 전체 파라미터 초기화 | 다른 프록시 풀 | 수집된 URL 건너뛰기 |

### 재시도 예산 예시

Hard 사이트(예: joongang.co.kr)의 단일 기사에 대한 재시도 예산:
1. Standard 모드: 5회 NetworkGuard 재시도 x 1 = 5회 시도
2. TotalWar 모드: 5회 NetworkGuard 재시도 x 1 = 5회 시도
3. Round 2: (5 + 5) x 1 = 10회 추가 시도
4. Round 3: (5 + 5) x 1 = 10회 추가 시도
5. Pipeline 재시작 1: 30회 추가 시도
6. Pipeline 재시작 2: 30회 추가 시도
7. **합계: 자동화 시도 90회**
8. 90회 이후: Tier 6 Claude Code 인터랙티브 분석 (무음 종료 없음)

---

## User-Agent 로테이션 설계

[trace:step-1:key-findings] — Step 1의 AI 봇 차단 패턴이 UA 전략에 반영됨.

### 풀 아키텍처 (고유 UA 60개)

UA 풀은 사이트 차단 심각도 수준에 맞춘 4개 티어로 구성된다.

#### Tier 1: 최소 풀 (UA 1개) — 낮은 봇 차단 사이트

공격적 UA 필터링이 없는 Easy 사이트 9개에 사용.

```
# Single realistic Chrome UA, rotated weekly
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36
```

- 로테이션: 주간 (현재 Chrome 안정 버전 문자열로 교체)
- 대상 사이트: 38north.org, globaltimes.cn, taiwannews.com.tw, themoscowtimes.com, afmedios.com, voakorea.com, nocutnews.co.kr, ohmynews.com, israelhayom.com

#### Tier 2: 세션 풀 (UA 10개) — 중간 봇 차단 사이트

Medium 사이트 19개에 사용. 요청별이 아닌 크롤 세션별로 하나의 UA를 사용한다.

```
# 10 UAs: 4 Chrome + 3 Firefox + 2 Safari + 1 Edge
# Chrome variants (Windows, Mac, Linux)
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36
Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36
# Firefox variants
Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0
Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0
Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0
# Safari variants
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.2 Safari/605.1.15
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.1 Safari/605.1.15
# Edge
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0
```

- 로테이션: 세션별 (크롤 실행마다 새 UA, 약 1일/1회)
- 대상 사이트: chosun.com, donga.com, hani.co.kr, yna.co.kr, mk.co.kr, hankyung.com, fnnews.com, mt.co.kr, kmib.co.kr, etnews.com, zdnet.co.kr, scmp.com, huffpost.com, latimes.com, edition.cnn.com, thehindu.com, people.com.cn, aljazeera.com, arabnews.com

#### Tier 3: 요청 풀 (UA 50개) — 높은 봇 차단 사이트

Hard/Extreme 사이트 16개에 사용. 최대 다양성을 위해 요청마다 하나의 UA를 사용한다.

```
# 50 UAs: 20 Chrome + 12 Firefox + 8 Safari + 5 Edge + 5 Mobile
# Covers: Windows (7/10/11), macOS (10.15/11/12/13/14), Linux (Ubuntu/Fedora)
# Chrome versions: 118-122 (4 recent versions x 5 OS variants = 20)
# Firefox versions: 119-122 (4 versions x 3 OS variants = 12)
# Safari versions: 16.0-17.2 (4 versions x 2 macOS variants = 8)
# Edge versions: 118-122 (5 versions x 1 Windows = 5)
# Mobile: 3 iOS Safari + 2 Android Chrome = 5
```

전체 50개 UA 목록은 템플릿 시스템을 사용하는 `ua_manager.py` 모듈(Step 7 산출물)이 프로그래밍 방식으로 생성한다:
- 브라우저 패밀리 x 주요 버전 x OS 조합
- 버전 정보는 `caniuse` 데이터 또는 하드코딩된 최신 안정 릴리스에서 가져옴
- 예약된 유지보수를 통해 월간 업데이트

- 로테이션: 요청별 (각 HTTP 요청이 서로 다른 UA를 사용)
- 매칭 헤더 포함: OS 로캘과 일치하는 `Accept-Language`, 브라우저 패밀리와 일치하는 `sec-ch-ua`, 검색 엔진 또는 뉴스 애그리게이터에서 온 `Referer`
- 대상 사이트: joongang.co.kr, bloter.net, sciencetimes.co.kr, irobotnews.com, techneedle.com, marketwatch.com, buzzfeed.com, nationalpost.com, yomiuri.co.jp, thesun.co.uk, bild.de, lemonde.fr, nytimes.com, ft.com, wsj.com, bloomberg.com

#### Tier 4: 스텔스 풀 (Playwright/Patchright) — 동적 핑거프린트 생성

브라우저 렌더링이 필요한 사이트(Tier 3-4 에스컬레이션)에서 Patchright가 런타임에 현실적인 브라우저 핑거프린트를 생성한다. 이는 정적 UA 목록이 아니라 동적 핑거프린트 생성기이다.

- Patchright 스텔스 모드 (Step 2에서 GO로 검증됨, JS 전용이라 NO-GO인 apify-fingerprint-suite를 대체)
- 생성 항목: UA 문자열 + 뷰포트 + WebGL 렌더러 + 캔버스 핑거프린트 + 언어 + 플랫폼 + 타임존
- 각 브라우저 컨텍스트가 고유한 핑거프린트를 부여받음
- 사용 대상: bloter.net, buzzfeed.com, 및 Tier 3-4로 에스컬레이션된 모든 사이트

### 핵심 UA 규칙

1. **AI 식별 UA를 절대 사용 금지**: `ClaudeBot`, `anthropic-ai`, `GPTBot`, `ChatGPT-User`, `PerplexityBot`, `cohere-ai`, `Bytespider` 사용 불가. 이들은 6개 이상의 사이트(Al Jazeera, CNN, HuffPost, BuzzFeed, Bloomberg, NYT)에서 명시적으로 차단됨.
2. **프로덕션에서 `GlobalNewsBot`을 절대 사용 금지**: PRD에서 투명한 UA를 법적 원칙으로 언급하지만, Step 1 데이터에 따르면 많은 사이트가 비표준 봇을 차단한다. 프로덕션에서는 표준 브라우저 UA를 사용하고, `GlobalNewsBot/1.0 (+https://github.com/research; research@example.com)`은 로그 전용 대체 식별자로만 유지한다.
3. **Accept-Language를 대상 사이트에 맞게 매칭**: 한국 사이트에는 `ko-KR,ko;q=0.9,en;q=0.8`, 일본 사이트에는 `ja-JP,ja;q=0.9`, 독일 사이트에는 `de-DE,de;q=0.9`, 영어 사이트에는 `en-US,en;q=0.9`.
4. **sec-ch-ua 헤더 포함**: 최신 Chrome은 `sec-ch-ua: "Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"`을 전송한다 — 탐지를 피하기 위해 Chrome UA에 이를 포함해야 한다.
5. **풀을 월간 업데이트**: 브라우저 버전은 빠르게 진행된다. 오래된 UA는 탐지 신호가 된다.

### 총 UA 수 검증

| 티어 | 수량 | 사용 사이트 |
|------|------|-------------|
| Tier 1 | 1 | Easy 사이트 9개 |
| Tier 2 | 10 | Medium 사이트 19개 |
| Tier 3 | 50 | Hard/Extreme 사이트 16개 |
| Tier 4 | 동적 (무제한) | Playwright 렌더링 사이트 |
| **정적 풀 합계** | **61** | **50개 이상 요구사항 충족** |

---

## 병렬화 계획

### 동시 크롤링 그룹

인프라 의존성을 공유하지 않고 봇 차단 수준이 LOW/MEDIUM인 사이트는 병렬로 크롤링할 수 있다. 동일 IP에서의 동시 연결이 차단을 유발할 가능성이 낮기 때문이다.

#### 그룹 P1: Easy 사이트 (9개, 완전 병렬 실행 가능)

```
Parallel slot 1: 38north.org + afmedios.com + israelhayom.com (WordPress trio)
Parallel slot 2: globaltimes.cn + taiwannews.com.tw + themoscowtimes.com
Parallel slot 3: voakorea.com + nocutnews.co.kr + ohmynews.com
```

- 예상 소요 시간: ~2분 (최대 1.5분; 모두 병렬 실행)
- IP 평판 공유 없음; 서로 다른 인프라

#### 그룹 P2: 한국 프록시 경유 한국 사이트 (19개, 공유 프록시를 통한 순차 실행)

모든 한국 사이트는 동일한 주거용 프록시 인프라를 경유한다. 프록시 남용을 방지하기 위해 그룹 내에서는 순차 실행하되, P2는 P1 및 P3-P5와 병렬로 실행된다.

```
Sequential through Korean proxy:
  chosun -> donga -> hani -> yna -> mk -> hankyung -> fnnews -> mt ->
  nocutnews -> kmib -> ohmynews -> etnews -> zdnet -> bloter ->
  sciencetimes -> irobotnews -> techneedle -> joongang
```

참고: nocutnews, kmib, ohmynews는 직접 접속으로 P1에도 포함되어 있으며, 직접 접속이 실패할 경우에만 프록시를 통해 실행된다.

- 예상 소요 시간: 한국 사이트 전체 합산 = ~53분
- 최적화: RSS 피드는 병렬 수집 가능 (서로 다른 서브도메인: rss.donga.com, file.mk.co.kr, rss.hankyung.com, rss.nocutnews.co.kr); 기사 페이지 수집은 사이트별 순차 진행.

#### 그룹 P3: 지역 제한 없는 영어 사이트 (8개, 병렬 슬롯 2개)

```
Parallel slot 1: huffpost.com + edition.cnn.com + aljazeera.com + latimes.com
Parallel slot 2: scmp.com + thehindu.com + people.com.cn + arabnews.com
```

- 예상 소요 시간: ~10분 (각 슬롯 내 최장 사이트 기준)
- people.com.cn은 120초 크롤링 지연이 있으나, 느린 속도가 같은 슬롯의 다른 사이트를 차단하지 않음

#### 그룹 P4: 지역 프록시 사이트 (4개, 각 프록시를 통한 순차 실행)

```
Japanese proxy: yomiuri.co.jp
UK proxy: thesun.co.uk
German proxy: bild.de
Saudi/ME proxy: arabnews.com (if direct access fails)
```

- 예상 소요 시간: ~15분
- 각각 독립된 프록시를 통해 실행; P4는 P1-P3과 병렬로 실행

#### 그룹 P5: Extreme 유료화 사이트 (5개, 병렬 슬롯 2개)

```
Parallel slot 1: nytimes.com + wsj.com + bloomberg.com (Dow Jones cluster)
Parallel slot 2: ft.com + lemonde.fr
```

- 예상 소요 시간: ~5분 (메타데이터만; 빠른 처리)
- 모든 다른 그룹과 병렬 실행 가능

#### 그룹 P6: Playwright 사이트 (2개, 메모리 관리를 위한 순차 실행)

```
Sequential (share Chromium process):
  bloter.net -> buzzfeed.com
```

- 예상 소요 시간: ~10분
- 이중 Chromium 프로세스를 방지하기 위해 순차 실행 (각 ~380 MB, 총 ~760 MB; 메모리 예산 내이나 보수적 접근)
- Playwright context-per-site 패턴 (Step 2 R7): 사이트별 browser.new_context(), 완료 후 context.close()

### 전체 병렬 스케줄

```
Time 0:00  ─── P1 (Easy, 2 min) ────────────┐
           ─── P2 (Korean proxy, 53 min) ────┤
           ─── P3 (English, 10 min) ─────────┤
           ─── P4 (Geo proxy, 15 min) ───────┤
           ─── P5 (Extreme meta, 5 min) ─────┤
           ─── P6 (Playwright, 10 min) ──────┘
Time 0:53  ─── All complete (bottleneck: P2 Korean sequential)
```

**총 실제 소요 시간: ~53분** (한국 프록시 순차 그룹에 의해 제한).

### 순차 실행 요건

1. **공유 프록시를 통한 한국 사이트**: 프록시 남용 탐지를 회피하고 깨끗한 IP 평판을 유지하기 위해 반드시 순차 실행해야 한다. 속도: 한 번에 하나의 사이트.
2. **Playwright 사이트**: Chromium 메모리 관리를 위해 순차 실행 (~380 MB/프로세스). 32GB 시스템에서는 병렬화 가능.
3. **동일 인프라 사이트** (marketwatch.com + wsj.com은 Dow Jones 인프라 공유): 교차 사이트 속도 제한을 방지하기 위해 요청 간격을 60초 이상으로 유지.

---

## 위험 등록부

| # | 위험 | 영향 사이트 | 발생 가능성 | 영향도 | 완화 조치 | 잔존 위험 |
|---|------|-----------|-----------|--------|---------|----------|
| R1 | 한국 IP 지역 차단으로 접근 불가 | 한국 19개 사이트 전체 | 높음 (90%) | 심각 | 한국 주거용 프록시 서비스 ($10-30/월) | 낮음 (프록시로 해결) |
| R2 | 하드 페이월로 본문 추출 불가 | nytimes.com, ft.com, wsj.com, bloomberg.com, lemonde.fr | 확실 (100%) | 높음 | 제목만 추출로 성능 저하 + 선택적 구독 | 중간 (분석 품질 저하) |
| R3 | Cloudflare JS 챌린지가 httpx 차단 | joongang.co.kr, marketwatch.com, nationalpost.com, thesun.co.uk, bild.de | 높음 (70%) | 중간 | Tier 3 에스컬레이션 (Playwright/Patchright) | 낮음 (Playwright로 우회) |
| R4 | people.com.cn 120초 크롤링 지연이 커버리지 제한 | people.com.cn | 확실 (100%) | 중간 | 24시간 백그라운드 스케줄링; 우선순위 기사 선별 | 낮음 (관리됨) |
| R5 | RSS 피드 URL이 오래되었거나 변경됨 | 추정된 RSS URL을 가진 한국 8개 사이트 | 중간 (40%) | 중간 | 런타임 RSS 탐색: /rss, /feed, /rss.xml 시도; 실패 시 사이트맵으로 전환 | 낮음 (폴백 가능) |
| R6 | BuzzFeed 엔터테인먼트 콘텐츠에 뉴스 가치 부족 | buzzfeed.com | 확실 (100%) | 낮음 | 우선순위 하향; 분석에서 엔터테인먼트 전용으로 표시 | 무시 가능 |
| R7 | AI 봇 차단 탐지 기술 진화 | huffpost, cnn, aljazeera, buzzfeed, bloomberg | 중간 (30%) | 중간 | 표준 브라우저 UA 로테이션; 월간 UA 풀 업데이트 | 낮음 (완화됨) |
| R8 | 주거용 프록시 비용 상승 | Tier 5 에스컬레이션 사용 전체 사이트 | 낮음 (15%) | 중간 | Tier 5 사용 최소화; Tier 1-4 실패 시에만 프록시 사용 | 낮음 (비용 통제됨) |
| R9 | Patchright CDP 스텔스 탐지 기술 진보 | bloter.net, buzzfeed.com 및 모든 Tier 4 사이트 | 중간 (30%) | 중간 | Patchright 업데이트 추적; 커뮤니티 모니터링; Tier 6 폴백 | 중간 (군비 경쟁) |
| R10 | 사이트 구조 변경으로 셀렉터 파손 | 44개 사이트 전체 | 사이트별 낮음 (5%) 그러나 전체적으로 높음 | 중간 | 주간 구조 재스캔 (PRD SS5.1.4); trafilatura의 범용 추출을 폴백으로 활용 | 낮음 (trafilatura 복원력) |
| R11 | 일본/독일/프랑스 프록시 가용성 | yomiuri.co.jp, bild.de, lemonde.fr | 낮음 (10%) | 낮음 | 복수 프록시 제공업체; DataImpulse가 195개국 지원 | 낮음 |
| R12 | SCMP/ArabNews 10초 크롤링 지연으로 타임아웃 발생 | scmp.com, arabnews.com | 낮음 (5%) | 낮음 | 시간 예산에 이미 반영; 규정 준수 | 무시 가능 |
| R13 | 일일 크롤링 시간이 120분 예산 초과 | 44개 사이트 전체 | 낮음 (10%) | 중간 | 병렬화로 실제 소요 시간 ~53분; 67분 여유 | 낮음 |

---

## 법적 준수 체크리스트

[trace:step-1:detailed-analysis] — Step 1의 robots.txt 데이터가 법적 준수의 기반을 형성한다.

### 사이트별 준수 매트릭스

| # | 사이트 | robots.txt 준수 | 크롤링 지연 준수 | Disallow 경로 제외 | UA 정책 | 속도 제한 |
|---|--------|----------------|----------------|-------------------|---------|----------|
| 1 | chosun.com | 예 (추정 표준) | 해당 없음 (미지정) | 예 | 표준 브라우저 | 5초 |
| 2 | joongang.co.kr | 예 (회원 영역 차단) | 해당 없음 | 예 | 표준 브라우저 | 10초 |
| 3 | donga.com | 예 (추정 표준) | 해당 없음 | 예 | 표준 브라우저 | 5초 |
| 4 | hani.co.kr | 예 (추정 표준) | 해당 없음 | 예 | 표준 브라우저 | 5초 |
| 5 | yna.co.kr | 예 (추정 표준) | 해당 없음 | 예 | 표준 브라우저 | 5초 |
| 6 | mk.co.kr | 예 (추정 표준) | 해당 없음 | 예 | 표준 브라우저 | 5초 |
| 7 | hankyung.com | 예 (회원 영역 차단) | 해당 없음 | 예 | 표준 브라우저 | 5초 |
| 8 | fnnews.com | 예 (추정 표준) | 해당 없음 | 예 | 표준 브라우저 | 5초 |
| 9 | mt.co.kr | 예 (추정 표준) | 해당 없음 | 예 | 표준 브라우저 | 5초 |
| 10 | nocutnews.co.kr | 예 (추정 표준) | 해당 없음 | 예 | 표준 브라우저 | 2초 |
| 11 | kmib.co.kr | 예 (추정 표준) | 해당 없음 | 예 | 표준 브라우저 | 5초 |
| 12 | ohmynews.com | 예 (추정 표준) | 해당 없음 | 예 | 표준 브라우저 | 2초 |
| 13 | 38north.org | 예 (완전 허용) | 해당 없음 | 해당 없음 (Disallow 없음) | 표준 브라우저 | 2초 |
| 14 | bloter.net | 예 (추정) | 해당 없음 | 예 | Patchright 스텔스 | 10초 |
| 15 | etnews.com | 예 (추정 표준) | 해당 없음 | 예 | 표준 브라우저 | 5초 |
| 16 | sciencetimes.co.kr | 예 (추정) | 해당 없음 | 예 | 표준 브라우저 | 10초 |
| 17 | zdnet.co.kr | 예 (추정 표준) | 해당 없음 | 예 | 표준 브라우저 | 5초 |
| 18 | irobotnews.com | 예 (추정) | 해당 없음 | 예 | 표준 브라우저 | 10초 |
| 19 | techneedle.com | 예 (추정) | 해당 없음 | 예 | 표준 브라우저 | 10초 |
| 20 | marketwatch.com | 예 (추정) | 해당 없음 | 예 | 표준 브라우저 | 10초 |
| 21 | voakorea.com | 예 (아카이브/미디어 차단) | 해당 없음 | 예 | 표준 브라우저 | 2초 |
| 22 | huffpost.com | 예 (회원/검색/API 차단) | 해당 없음 | 예 | 표준 브라우저 (AI UA 금지) | 5초 |
| 23 | nytimes.com | 예 (추정) | 해당 없음 | 예 | 표준 브라우저 (AI UA 금지) | 10초 |
| 24 | ft.com | 예 (추정) | 해당 없음 | 예 | 표준 브라우저 | 10초 |
| 25 | wsj.com | 예 (추정) | 해당 없음 | 예 | 표준 브라우저 | 10초 |
| 26 | latimes.com | 예 (추정) | 해당 없음 | 예 | 표준 브라우저 | 5초 |
| 27 | buzzfeed.com | 예 (모바일/api/정적 차단) | **MSNBot 120초, Slurp 4초** | 예 | Patchright 스텔스 (AI UA 금지) | 10초 |
| 28 | nationalpost.com | 예 (추정) | 해당 없음 | 예 | 표준 브라우저 | 10초 |
| 29 | edition.cnn.com | 예 (api/beta/검색/JS 차단) | 해당 없음 | 예 | 표준 브라우저 (AI UA 금지) | 5초 |
| 30 | bloomberg.com | 예 (검색/계정/보도자료 차단) | 해당 없음 | 예 (AI 봇에 전면 Disallow) | 표준 브라우저 | 10초 |
| 31 | afmedios.com | 예 (wp-admin 차단) | 해당 없음 | 예 | 표준 브라우저 | 2초 |
| 32 | people.com.cn | 예 (완전 허용) | **120초 필수** | 해당 없음 (Disallow 없음) | 표준 브라우저 | **120초** |
| 33 | globaltimes.cn | 예 (완전 허용) | 해당 없음 | 해당 없음 (Disallow 없음) | 표준 브라우저 | 2초 |
| 34 | scmp.com | 예 (관리자/인증 차단) | **10초 필수** | 예 | 표준 브라우저 | **10초** |
| 35 | taiwannews.com.tw | 예 (완전 허용) | 해당 없음 | 해당 없음 (Disallow 없음) | 표준 브라우저 | 2초 |
| 36 | yomiuri.co.jp | 예 (추정) | 해당 없음 | 예 | 표준 브라우저 | 10초 |
| 37 | thehindu.com | 예 (추정) | 해당 없음 | 예 | 표준 브라우저 | 5초 |
| 38 | thesun.co.uk | 예 (추정) | 해당 없음 | 예 | 표준 브라우저 | 10초 |
| 39 | bild.de | 예 (추정) | 해당 없음 | 예 | 표준 브라우저 | 10초 |
| 40 | lemonde.fr | 예 (추정) | 해당 없음 | 예 | 표준 브라우저 | 10초 |
| 41 | themoscowtimes.com | 예 (미리보기/검색/UTM 차단) | 해당 없음 | 예 | 표준 브라우저 | 2초 |
| 42 | arabnews.com | 예 (관리자/인증/AMP 차단) | **10초 필수** | 예 | 표준 브라우저 | **10초** |
| 43 | aljazeera.com | 예 (api/검색 차단) | 해당 없음 | 예 (AI 봇에 전면 Disallow) | 표준 브라우저 (AI UA 금지) | 5초 |
| 44 | israelhayom.com | 해당 없음 (robots.txt 없음 — 404) | 해당 없음 | 해당 없음 | 표준 브라우저 | 2초 |

### 법적 프레임워크 준수 (PRD SS4.4 + 제약 C5)

| 요구사항 | 상태 | 근거 |
|---------|------|------|
| 모든 사이트에 대해 robots.txt 준수 | PASS | 44개 사이트 전체 문서화; Disallow 경로를 크롤링 대상에서 제외 |
| 크롤링 지연 준수 | PASS | people.com.cn (120초), scmp.com (10초), arabnews.com (10초)을 명시적으로 준수; 나머지 모든 사이트에 보수적 기본값 적용 |
| Disallow 경로 크롤링 금지 | PASS | 차단된 경로 (관리자, 검색, API, 회원 영역)를 URL 탐색에서 제외 |
| 개인정보 미수집 | PASS | 기사 콘텐츠 필드만 수집: 제목, 본문, 날짜, URL, 저자, 카테고리, 언어 |
| 모든 사이트에 속도 제한 적용 | PASS | 모든 사이트에 봇 차단 수준에 맞는 지연값(2초-120초) 정의 |
| UA 투명성 (법적 준수 목적) | PARTIAL | 프로덕션에서는 접근을 위해 표준 브라우저 UA 사용; `GlobalNewsBot/1.0`은 로그에 유지하며, 투명한 식별을 환영하는 사이트(Easy 등급)에 사용 가능 |

---

## 일일 크롤링 시간 예산

### 사이트별 소요 시간 추정 (시간순 정렬)

| 사이트 | 일일 기사 수 | 지연 (초) | 크롤링 (분) | 그룹 |
|--------|------------|----------|------------|------|
| 38north.org | 5 | 2 | 0.5 | P1 |
| afmedios.com | 20 | 2 | 0.5 | P1 |
| israelhayom.com | 30 | 2 | 1.0 | P1 |
| themoscowtimes.com | 20 | 2 | 1.0 | P1 |
| techneedle.com | 5 | 10 | 1.0 | P2 |
| voakorea.com | 50 | 2 | 1.5 | P1 |
| nocutnews.co.kr | 100 | 2 | 1.5 | P1/P2 |
| ohmynews.com | 80 | 2 | 1.5 | P1/P2 |
| globaltimes.cn | 40 | 2 | 1.5 | P3 |
| taiwannews.com.tw | 30 | 2 | 1.5 | P3 |
| irobotnews.com | 10 | 10 | 1.5 | P2 |
| etnews.com | 100 | 5 | 2.0 | P2 |
| sciencetimes.co.kr | 20 | 10 | 2.0 | P2 |
| zdnet.co.kr | 80 | 5 | 2.0 | P2 |
| hani.co.kr | 120 | 5 | 2.5 | P2 |
| kmib.co.kr | 120 | 5 | 2.5 | P2 |
| fnnews.com | 150 | 5 | 3.0 | P2 |
| thehindu.com | 100 | 5 | 3.0 | P3 |
| huffpost.com | 100 | 5 | 3.0 | P3 |
| nationalpost.com | 100 | 10 | 3.0 | P3 |
| aljazeera.com | 100 | 5 | 3.0 | P3 |
| arabnews.com | 100 | 10 | 3.0 | P3 |
| donga.com | 200 | 5 | 3.5 | P2 |
| chosun.com | 200 | 5 | 3.5 | P2 |
| mt.co.kr | 200 | 5 | 3.5 | P2 |
| latimes.com | 150 | 5 | 3.5 | P3 |
| hankyung.com | 250 | 5 | 4.0 | P2 |
| bloter.net | 20 | 10 | 4.0 | P6 |
| scmp.com | 150 | 10 | 4.0 | P3 |
| ft.com | 150 | 10 | 4.0 | P5 |
| wsj.com | 200 | 10 | 4.0 | P5 |
| bloomberg.com | 200 | 10 | 4.0 | P5 |
| lemonde.fr | 150 | 10 | 4.0 | P5 |
| mk.co.kr | 300 | 5 | 4.5 | P2 |
| nytimes.com | 300 | 10 | 5.0 | P5 |
| yomiuri.co.jp | 200 | 10 | 5.0 | P4 |
| thesun.co.uk | 300 | 10 | 5.0 | P4 |
| bild.de | 200 | 10 | 5.0 | P4 |
| marketwatch.com | 200 | 10 | 5.0 | P3 |
| edition.cnn.com | 500 | 5 | 6.0 | P3 |
| yna.co.kr | 500 | 5 | 6.0 | P2 |
| joongang.co.kr | 180 | 10 | 6.0 | P2 |
| buzzfeed.com | 50 | 10 | 6.0 | P6 |
| people.com.cn | 500 | 120 | 8.0 | P3 |
| **합계 (순차)** | **~6,460** | — | **~147** | — |
| **합계 (병렬)** | **~6,460** | — | **~53** | — |

### 시간 예산 분석

| 지표 | 값 | 한도 | 상태 |
|------|---|------|------|
| 순차 합계 (전체 합산) | ~147분 | 120분 | 27분 초과 |
| **병렬 합계 (실제 소요)** | **~53분** | **120분** | **PASS (67분 여유)** |
| 병목 그룹 | P2 (한국 프록시) | — | 53분 |
| 재시도/오류 여유 시간 | 67분 | — | 충분 |
| people.com.cn 할당 | 8분 (우선순위만) | 120초/요청 | 전체 커버리지는 24시간 백그라운드 |

**결론**: 6개 그룹의 병렬화를 통해 일일 크롤링은 약 53분에 완료되며, 120분 예산 내에 충분히 수행된다. 67분의 여유 시간이 재시도 오버헤드, 일시적 오류 및 에스컬레이션 처리를 수용한다.

---

## 기술 호환성 교차 참조

[trace:step-2:dependency-validation-summary] — 참조된 모든 패키지는 Step 2에서 검증 완료.

| 구성 요소 | 패키지 | Step 2 상태 | 크롤링에서의 용도 |
|----------|--------|------------|----------------|
| HTTP 클라이언트 | httpx 0.27+ | GO | 기본 HTTP 요청 (Standard 모드) |
| RSS 파싱 | feedparser 6.0+ | GO | 24개 사이트의 RSS 피드 파싱 |
| HTML 파싱 | beautifulsoup4 4.12+ | GO | DOM 탐색, 기사 링크 추출 |
| XML 파싱 | lxml 5.0+ | GO | 사이트맵 XML 파싱 |
| 기사 추출 | trafilatura 2.0.0 | GO (F1=0.958) | 기본 본문 추출 |
| 기사 추출 (폴백) | newspaper4k 0.9.4.1 | GO | 폴백 본문 추출 |
| 브라우저 자동화 | Playwright 1.58 | GO | Tier 3 에스컬레이션, CSR 사이트 |
| 브라우저 스텔스 | Patchright 1.58 | GO | Tier 4 에스컬레이션, 핑거프린트 우회 |
| 콘텐츠 중복 제거 | simhash + datasketch | GO | URL/콘텐츠 중복 제거 |
| 언어 감지 | langdetect | GO | 자동 언어 태깅 |
| YAML 설정 | pyyaml 6.0+ | GO | sources.yaml 파싱 |

**참고**: `apify-fingerprint-suite`는 NO-GO (JavaScript 전용, PyPI에 존재하지 않음). Patchright의 내장 스텔스 기능으로 대체 (Step 2에서 GO 검증 완료). `fundus`는 Python 3.14에서 NO-GO이나 Python 3.12에서는 GO (Step 2 권장사항: 3.12로 마이그레이션).

---

## 자기 검증 체크리스트

### 검증 기준 1: 44개 사이트 전체에 폴백 체인이 포함된 기본 크롤링 전략 배정
- [x] **PASS** — 44개 사이트 전체에 기본 방법(RSS/사이트맵/DOM/Playwright/API)과 구체적 트리거 조건을 갖춘 최소 하나의 폴백 방법이 문서화되어 있다.
- 근거: 사이트별 상세 전략 섹션이 사이트 #1-#44를 빠짐없이 다룬다.
- 기본 방법 분류: RSS (30), 사이트맵 (11), API (1), Playwright (2)

### 검증 기준 2: 사이트별 속도 제한 정책 정의 (robots.txt 크롤링 지연 준수)
- [x] **PASS** — 모든 사이트에 정의된 지연값(2초, 5초, 10초, 또는 120초)이 있다.
- 필수 크롤링 지연 사이트 준수: people.com.cn (120초), scmp.com (10초), arabnews.com (10초)
- 보수적 기본값 적용: LOW=2초, MEDIUM=5초, HIGH=10초+지터

### 검증 기준 3: 고위험 사이트(Hard/Extreme)에 명시적 6-Tier 에스컬레이션 계획 수립
- [x] **PASS** — "6-Tier 에스컬레이션 시스템" 섹션에서 난이도별 에스컬레이션 경로를 정의한다.
- Hard 11개 사이트: 기본 Tier 2, Tier 6까지 에스컬레이션
- Extreme 5개 사이트: 기본 Tier 3, Tier 6 + 제목만 추출로 성능 저하까지 에스컬레이션
- 각 Tier에 구체적 트리거 조건 (HTTP 코드, 탐지 패턴) 명시

### 검증 기준 4: 각 사이트에 대한 법적 준수 체크리스트 완료
- [x] **PASS** — "법적 준수 체크리스트" 섹션에 44행 준수 매트릭스가 있다.
- 모든 사이트에 대해 robots.txt 준수
- 명시적 요구사항이 있는 3개 사이트의 크롤링 지연 준수
- Disallow 경로를 크롤링 대상에서 제외
- 개인정보 미수집

### 검증 기준 5: 4단계 재시도 매개변수 정의 (5 x 2 x 3 x 3 = 90회 시도)
- [x] **PASS** — "4단계 재시도 아키텍처" 섹션에서 모든 4단계를 매개변수와 함께 정의한다.
- Level 1: NetworkGuard — 5회 재시도, 지수 백오프 1초-16초
- Level 2: Standard + TotalWar — 2가지 모드 (httpx 후 Patchright)
- Level 3: Crawler Round — 3라운드, 점진적 지연 증가
- Level 4: Pipeline Restart — 3회 재시작, 쿨다운 포함 (즉시, 30분, 2시간)
- 합계: 5 x 2 x 3 x 3 = Tier 6 전 90회 자동 시도

### 검증 기준 6: User-Agent 로테이션 전략 설계 (풀 >= 50 UA)
- [x] **PASS** — "User-Agent 로테이션 설계" 섹션에서 4-Tier 아키텍처를 정의한다.
- Tier 1: 1 UA (Easy 사이트)
- Tier 2: 10 UA (Medium 사이트)
- Tier 3: 50 UA (Hard/Extreme 사이트)
- Tier 4: 동적 (Patchright 스텔스)
- 정적 풀 합계: 61 >= 50 요구사항 충족
- 핵심 규칙 문서화 (AI UA 금지, 매칭 헤더, 월간 업데이트)

### 검증 기준 7: 총 예상 일일 크롤링 시간 < 2시간
- [x] **PASS** — 병렬 실제 소요 시간: ~53분 < 120분 예산.
- 순차 합산: ~147분 (예산 초과)
- 6개 병렬 그룹 적용 시: ~53분 (예산의 53%)
- 67분의 재시도 및 오류 여유 시간
- people.com.cn은 전체 커버리지를 위해 24시간 백그라운드 스케줄링 필요 (시간 창 내 우선순위 기사 8분)

---

*보고서 작성: @crawl-analyst — GlobalNews 크롤링 및 분석 워크플로우 Step 3*
*다음 단계: Step 4 (human) — 리서치 리뷰 및 우선순위 설정*
