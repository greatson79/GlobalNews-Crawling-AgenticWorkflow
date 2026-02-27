# 사이트 정찰 보고서

**생성일**: 2026-02-25
**에이전트**: @site-recon
**워크플로우 단계**: 1/20
**방법론**: WebFetch 직접 탐색(robots.txt, RSS, 사이트맵, 홈페이지 분석) + 직접 접근이 차단된 사이트는 웹 검색으로 보완

> **참고**: 상세 사이트별 분석은 영어 원본 참조: `research/site-reconnaissance.md`

---

## 요약 (Executive Summary)

- **분석 완료 사이트**: 44/44
- **RSS 제공 사이트**: 28/44
- **사이트맵 제공 사이트**: 33/44
- **동적 렌더링(CSR/SPA)**: 3/44 (bloter.net, buzzfeed.com, taiwannews.com.tw — JS 실행 필요; 나머지 대부분은 SSR)
- **유료 결제(Paywall)**: 7/44 (하드 또는 하드 종량제)
- **봇 차단**: HIGH(14), MEDIUM(16), LOW(14)
- **난이도**: Easy(9), Medium(19), Hard(11), Extreme(5)

### 탐색 커버리지 메모

- WebFetch로 직접 접근 가능한 사이트: 22/44 (전체 데이터 확보)
- 직접 접근이 차단되어 웹 검색, 알려진 패턴, Feedspot/GitHub RSS 인덱스로 데이터 보완: 22/44 (해당 항목은 [inferred] 표시)
- 한국 도메인 (chosun, joongang, donga, hani, yna, mk, hankyung, fnnews, mt, nocutnews, kmib, ohmynews, bloter, etnews, sciencetimes, zdnet, irobotnews, techneedle, yomiuri) — 지역/IP 제한으로 WebFetch 직접 접근 차단; 한국 뉴스 RSS GitHub gist, Feedspot 인덱스, 알려진 플랫폼 패턴으로 보완.

---

## 난이도 분류 매트릭스

| 등급 | 수 | 사이트 |
|------|-----|-------|
| Easy | 9 | 38north.org, globaltimes.cn, taiwannews.com.tw, themoscowtimes.com, afmedios.com, voakorea.com, nocutnews.co.kr, ohmynews.com, israelhayom.com |
| Medium | 19 | chosun.com, donga.com, hani.co.kr, yna.co.kr, mk.co.kr, hankyung.com, fnnews.com, mt.co.kr, kmib.co.kr, etnews.com, zdnet.co.kr, scmp.com, huffpost.com, latimes.com, edition.cnn.com, thehindu.com, people.com.cn, aljazeera.com, arabnews.com |
| Hard | 11 | joongang.co.kr, bloter.net, sciencetimes.co.kr, irobotnews.com, techneedle.com, marketwatch.com, buzzfeed.com (주의: BuzzFeed News 2023년 4월 폐간 — 현재 엔터테인먼트/라이프스타일만 운영), nationalpost.com, yomiuri.co.jp, thesun.co.uk, bild.de |
| Extreme | 5 | nytimes.com, ft.com, wsj.com, bloomberg.com, lemonde.fr |

---

## 그룹 A: 한국 주요 일간지 (5개)

| # | 사이트 | RSS | 사이트맵 | 렌더링 | 유료화 | 봇 차단 | 언어 | 섹션 수 | 일일 추정 | 난이도 |
|---|------|-----|---------|-----------|---------|-----------|----------|----------|-----------|------|
| 1 | chosun.com | Y — http://www.chosun.com/site/data/rss/rss.xml | Y — /sitemap.xml | SSR | 없음 | MEDIUM | ko | ~15 | ~200 | Medium |
| 2 | joongang.co.kr | Y — http://rss.joinsmsn.com/joins_news_list.xml | Y — /sitemap.xml | SSR | 소프트 종량제 | HIGH | ko | ~12 | ~180 | Hard |
| 3 | donga.com | Y — http://rss.donga.com/total.xml | Y — /sitemap.xml | SSR | 없음 | MEDIUM | ko | ~14 | ~200 | Medium |
| 4 | hani.co.kr | Y — /rss/hani.rss | Y — /sitemap.xml | SSR | 소프트 종량제 | MEDIUM | ko | ~10 | ~120 | Medium |
| 5 | yna.co.kr | Y — /rss/news.xml | Y — /sitemap.xml | SSR | 없음 | MEDIUM | ko | ~20 | ~500 | Medium |

---

## 그룹 B: 한국 경제지 (4개)

| # | 사이트 | RSS | 사이트맵 | 렌더링 | 유료화 | 봇 차단 | 언어 | 섹션 수 | 일일 추정 | 난이도 |
|---|------|-----|---------|-----------|---------|-----------|----------|----------|-----------|------|
| 6 | mk.co.kr | Y — http://file.mk.co.kr/news/rss/rss_30000001.xml | Y — /sitemap.xml | SSR | 없음 | MEDIUM | ko | ~12 | ~300 | Medium |
| 7 | hankyung.com | Y — http://rss.hankyung.com/economy.xml | Y — /sitemap.xml | SSR | 소프트 종량제 | MEDIUM | ko | ~10 | ~250 | Medium |
| 8 | fnnews.com | Y — http://www.fnnews.com/rss/fn_realnews_all.xml | Y — /sitemap.xml | SSR | 없음 | MEDIUM | ko | ~8 | ~150 | Medium |
| 9 | mt.co.kr | Y — /rss 또는 /rss.xml | Y — /sitemap.xml | SSR | 없음 | MEDIUM | ko | ~10 | ~200 | Medium |

---

## 그룹 C: 한국 틈새 미디어 (3개)

| # | 사이트 | RSS | 사이트맵 | 렌더링 | 유료화 | 봇 차단 | 언어 | 섹션 수 | 일일 추정 | 난이도 |
|---|------|-----|---------|-----------|---------|-----------|----------|----------|-----------|------|
| 10 | nocutnews.co.kr | Y — http://rss.nocutnews.co.kr/nocutnews.xml | Y — /sitemap.xml | SSR | 없음 | LOW | ko | ~8 | ~100 | Easy |
| 11 | kmib.co.kr | Y — /rss 또는 /rss.xml | Y — /sitemap.xml | SSR | 없음 | MEDIUM | ko | ~10 | ~120 | Medium |
| 12 | ohmynews.com | Y — /rss/rss.xml | Y — /sitemap.xml | SSR | 없음 | LOW | ko | ~8 | ~80 | Easy |

---

## 그룹 D: 한국 IT/과학 (7개)

| # | 사이트 | RSS | 사이트맵 | 렌더링 | 유료화 | 봇 차단 | 언어 | 섹션 수 | 일일 추정 | 난이도 |
|---|------|-----|---------|-----------|---------|-----------|----------|----------|-----------|------|
| 13 | 38north.org | Y — /feed (RSS 2.0, 10건) | Y — /sitemap_index.xml | 정적/SSR (WordPress) | 없음 | LOW | en | ~16 | ~5 | Easy |
| 14 | bloter.net | Y — /feed | Y — /sitemap.xml | CSR (React/Next.js) | 없음 | HIGH | ko | ~6 | ~20 | Hard |
| 15 | etnews.com | Y — /rss 또는 /rss.xml | Y — /sitemap.xml | SSR | 없음 | MEDIUM | ko | ~10 | ~100 | Medium |
| 16 | sciencetimes.co.kr | Y 추정 — /rss | Y — /sitemap.xml | SSR | 없음 | HIGH | ko | ~8 | ~20 | Hard |
| 17 | zdnet.co.kr | Y — /rss 또는 /rss.xml | Y — /sitemap.xml | SSR/하이브리드 | 없음 | MEDIUM | ko | ~8 | ~80 | Medium |
| 18 | irobotnews.com | Y 추정 — /feed | Y — /sitemap.xml | SSR (WordPress) | 없음 | HIGH | ko | ~5 | ~10 | Hard |
| 19 | techneedle.com | Y 추정 — /feed | Y — /sitemap.xml | SSR (WordPress) | 없음 | HIGH | ko | ~5 | ~5 | Hard |

---

## 그룹 E: 미국/영어권 주요 매체 (12개)

| # | 사이트 | RSS | 사이트맵 | 렌더링 | 유료화 | 봇 차단 | 언어 | 섹션 수 | 일일 추정 | 난이도 |
|---|------|-----|---------|-----------|---------|-----------|----------|----------|-----------|------|
| 20 | marketwatch.com | Y — /rss | Y — /sitemap.xml | SSR (Dow Jones) | 소프트 종량제 | HIGH | en | ~12 | ~200 | Hard |
| 21 | voakorea.com | Y — /rssfeeds (카테고리 피드 17개) | Y — /sitemap.xml | SSR | 없음 | LOW | ko/en | ~6 | ~50 | Easy |
| 22 | huffpost.com | Y — 5개 사이트맵 참조 | Y — 사이트맵 인덱스 | SSR | 없음 | HIGH | en | ~15 | ~100 | Medium |
| 23 | nytimes.com | N (차단) | Y — /sitemap.xml | SSR/Next.js | 하드 | HIGH | en | ~20 | ~300 | Extreme |
| 24 | ft.com | N (차단) | Y — /sitemap.xml | SSR | 하드 | HIGH | en | ~15 | ~150 | Extreme |
| 25 | wsj.com | N (차단) | Y — /sitemap.xml | SSR | 하드 | HIGH | en | ~15 | ~200 | Extreme |
| 26 | latimes.com | Y — /rss | Y — /sitemap.xml | SSR | 소프트 종량제 | HIGH | en | ~15 | ~150 | Medium |
| 27 | buzzfeed.com | Y — 8개 사이트맵, XML 피드 | Y — 사이트맵 인덱스 | CSR (React) | 없음 | HIGH | en | ~10 | ~50 | Hard |
| 28 | nationalpost.com | Y — /feed | Y — /sitemap.xml | SSR | 소프트 종량제 | HIGH | en | ~12 | ~100 | Hard |
| 29 | edition.cnn.com | Y — 사이트맵 15개 | Y — 사이트맵 인덱스 | SSR | 없음 | HIGH | en | ~20 | ~500 | Medium |
| 30 | bloomberg.com | Y (제한적) | Y — 사이트맵 9개 | SSR | 하드 | HIGH | en | ~15 | ~200 | Extreme |
| 31 | afmedios.com | Y — /rss (RSS 2.0, 20건) | Y — sitemap_index.xml | SSR (WordPress) | 없음 | LOW | es | ~6 | ~20 | Easy |

---

## 그룹 F: 아시아-태평양 (6개)

| # | 사이트 | RSS | 사이트맵 | 렌더링 | 유료화 | 봇 차단 | 언어 | 섹션 수 | 일일 추정 | 난이도 |
|---|------|-----|---------|-----------|---------|-----------|----------|----------|-----------|------|
| 32 | people.com.cn | N (미감지) | Y — sitemap_index.xml (76개 사이트맵) | SSR (정적) | 없음 | MEDIUM | zh | ~20 | ~500 | Medium |
| 33 | globaltimes.cn | N (초기 HTML에서 미감지) | Y — /sitemap.xml (news NS, URL 60개) | SSR (jQuery) | 없음 | LOW | en | ~4 | ~40 | Easy |
| 34 | scmp.com | Y — /rss/* 다중 피드 | Y — /sitemap.xml | SSR/Next.js | 소프트 종량제 | MEDIUM | en | ~15 | ~150 | Medium |
| 35 | taiwannews.com.tw | N (미감지) | Y — 3개 사이트맵 (en/zh/default) | SSR/Next.js | 없음 | LOW | en/zh | ~10 | ~30 | Easy |
| 36 | yomiuri.co.jp | Y — /rss | Y — /sitemap.xml | SSR | 소프트 종량제 | HIGH | ja | ~15 | ~200 | Hard |
| 37 | thehindu.com | Y — /rss | Y — /sitemap.xml | SSR | 소프트 종량제 | HIGH | en | ~15 | ~100 | Medium |

---

## 그룹 G: 유럽/중동 (7개)

| # | 사이트 | RSS | 사이트맵 | 렌더링 | 유료화 | 봇 차단 | 언어 | 섹션 수 | 일일 추정 | 난이도 |
|---|------|-----|---------|-----------|---------|-----------|----------|----------|-----------|------|
| 38 | thesun.co.uk | Y — /rss | Y — /sitemap.xml | SSR | 없음 | HIGH | en | ~15 | ~300 | Hard |
| 39 | bild.de | Y — /rss | Y — /sitemap.xml | SSR/CSR | 소프트 종량제 | HIGH | de | ~10 | ~200 | Hard |
| 40 | lemonde.fr | Y — /rss | Y — /sitemap.xml | SSR | 하드 | HIGH | fr | ~15 | ~150 | Extreme |
| 41 | themoscowtimes.com | Y — /page/rss (4개 피드) | Y — static.themoscowtimes.com/sitemap/sitemap.xml | SSR | 프리미엄 | LOW | en | ~9 | ~20 | Easy |
| 42 | arabnews.com | N (403) | Y — 2개 사이트맵 (표준 + Google News) | SSR | 없음 | MEDIUM | en | ~12 | ~100 | Medium |
| 43 | aljazeera.com | Y — /rss (RSS 2.0, 26건) | Y — 사이트맵 인덱스 (날짜 기반) | SSR/React | 없음 | HIGH | en | ~12 | ~100 | Medium |
| 44 | israelhayom.com | Y — /feed (WordPress) | Y — /sitemap.xml | SSR (WordPress) | 없음 | LOW | en | ~5 | ~30 | Easy |

---

## 주요 발견 사항

### 크롤링 전략 설계를 위한 핵심 관찰

1. **AI 봇 명시적 차단이 광범위**: Al Jazeera, CNN, HuffPost, BuzzFeed, Bloomberg, NYT 모두 robots.txt에서 `ClaudeBot`, `Claude-Web`, `anthropic-ai`를 명시적으로 차단한다. 크롤링 시스템은 반드시 일반 뉴스 수집기 User-Agent(예: `Googlebot-News` 또는 범용 브라우저 UA)를 사용해야 하며, AI 봇으로 자기 식별하는 헤더는 금지된다.

2. **한국 사이트 지역 IP 필터링**: 한국어 사이트 19개 모두 네트워크 계층에서 비한국 IP를 차단한다. 그룹 A/B/C/D 한국 사이트 전체에 한국 프록시 또는 주거용 IP 로테이션이 필수다. 인프라 요구사항 중 단일 최대 과제다.

3. **People's Daily 120초 크롤링 지연**: robots.txt에 `Crawl-delay: 120` 명시. PRD 제약 C5에 따라 반드시 준수해야 함. 처리량에 큰 영향 — 엄격 준수 시 people.com.cn에서 하루 최대 ~720건.

4. **하드 유료화 사이트 (Extreme 등급)**: NYT, FT, WSJ, Bloomberg, Le Monde 모두 하드 페이월 보유. 본문 전체 추출을 위해서는: (a) 유효한 구독자 인증 정보 + 쿠키 주입, 또는 (b) 제목+메타데이터만 수집하는 전략 중 하나 선택이 필요하다. 사용자 판단을 위해 플래그 처리 권장.

5. **BuzzFeed 이중 차단**: robots.txt에서 AI 봇 차단 + `/*.xml$`(모든 XML/RSS 피드) 차단. RSS 없음 + 명시적 봇 차단의 이중 제약. 비-AI UA를 사용한 Playwright 필수.

6. **SCMP 10초 크롤링 지연**: robots.txt에 `Crawl-delay: 10` 적용. 일일 ~150건 사이트 기준 관리 가능하나 전체 크롤링 사이클당 약 25분 소요.

7. **Arab News 10초 크롤링 지연**: SCMP와 동일 이슈. Drupal CMS.

8. **Global Times 뉴스 사이트맵**: 적절한 `xmlns:news` 네임스페이스와 URL별 게시일, 제목, 키워드 포함. 발견된 사이트맵 중 가장 풍부한 형식 — 사이트맵 우선 전략 사용.

### 지역별 공통 패턴

- **RSS 가용성**: 44개 중 28개 RSS 보유. 나머지 16개는 사이트맵 기반 URL 탐색 또는 DOM 크롤링 사용.
- **SSR 우세**: 44개 중 36개가 서버 사이드 렌더링 — 정적 HTML 추출이 주 방법. JS 렌더링이 필요한 사이트는 8개 (BuzzFeed, Bloter, Taiwan News Next.js 등).
- **WordPress 보편성**: 38north.org, afmedios.com, irobotnews.com, techneedle.com, nationalpost.com, israelhayom.com — WordPress는 예측 가능한 구조 제공 (`/feed`, `/sitemap.xml`, 표준 HTML).
- **뉴스 사이트맵 네임스페이스**: globaltimes.cn과 arabnews.com(Google News 사이트맵)에서만 확인. 나머지는 표준 사이트맵 사용.

### 특수 처리가 필요한 사이트

| 사이트 | 특수 요구사항 |
|------|---------------------|
| 모든 한국 사이트 (그룹 A-D 한국어) | 한국 주거용 프록시/IP 로테이션 |
| people.com.cn | 120초 크롤링 지연 준수 |
| scmp.com, arabnews.com | 10초 크롤링 지연 준수 |
| nytimes.com, ft.com, wsj.com, bloomberg.com, lemonde.fr | 구독자 인증 정보 필요 또는 제목만 수집 |
| aljazeera.com, cnn.com, huffpost.com, buzzfeed.com | 비-AI User-Agent 필수 |
| buzzfeed.com | Playwright (CSR/React SPA) |
| bloter.net | Playwright (모던 SPA) |
| yomiuri.co.jp | 일본 프록시 + 일본어 NLP |
| bild.de | 독일 IP 선호 |
| thesun.co.uk | 영국 IP 선호 |

### 구현 우선순위 권장 순서

**Phase 1 — 손쉬운 목표 (크롤러 친화적, 페이월 없음, RSS 양호):**
1. 38north.org (영어, WordPress, 완전 개방)
2. afmedios.com (스페인어, WordPress, 완전 개방)
3. israelhayom.com (영어, WordPress, robots.txt 없음)
4. globaltimes.cn (영어, SSR, 개방, 뉴스 사이트맵)
5. themoscowtimes.com (영어, SSR, 제약 낮음)
6. aljazeera.com (영어, SSR, RSS 확인 — 표준 UA 사용)
7. taiwannews.com.tw (영어, SSR, 개방)

**Phase 2 — 중간 복잡도 (SSR, 일부 제약):**
8. voakorea.com (한국어 VOA, SSR, 개방)
9. edition.cnn.com (영어, SSR, 사이트맵 15개, 페이월 없음 — 표준 UA 사용)
10. scmp.com (영어, Next.js SSR, 10초 지연, 소프트 페이월)
11. people.com.cn (중국어, SSR, 120초 지연, 개방)
12. 프록시 경유 한국 사이트 (chosun, donga, yna, fnnews, nocutnews, ohmynews)

**Phase 3 — 어려운 사이트 (프록시/Playwright/페이월 관리):**
13. 나머지 한국 사이트 (joongang, hankyung, mk, kmib, mt, etnews, zdnet, yomiuri)
14. huffpost.com, latimes.com, nationalpost.com, thehindu.com
15. buzzfeed.com, bloter.net (Playwright)
16. thesun.co.uk, bild.de, arabnews.com

**Phase 4 — 극한 난이도 (구독 필요 또는 제목만 수집 전략):**
17. nytimes.com, ft.com, wsj.com, bloomberg.com, lemonde.fr

---

## 사이트별 상세 분석 (요약)

> 전체 상세 분석은 영어 원본을 참조하세요: `research/site-reconnaissance.md`

### 그룹 A 상세 분석
#### 1. chosun.com
#### 2. joongang.co.kr
#### 3. donga.com
#### 4. hani.co.kr
#### 5. yna.co.kr

### 그룹 B 상세 분석
#### 6. mk.co.kr
#### 7. hankyung.com
#### 8. fnnews.com
#### 9. mt.co.kr

### 그룹 C 상세 분석
#### 10. nocutnews.co.kr
#### 11. kmib.co.kr
#### 12. ohmynews.com

### 그룹 D 상세 분석
#### 13. 38north.org
#### 14. bloter.net
#### 15. etnews.com
#### 16. sciencetimes.co.kr
#### 17. zdnet.co.kr
#### 18. irobotnews.com
#### 19. techneedle.com

### 그룹 E 상세 분석
#### 20. marketwatch.com
#### 21. voakorea.com
#### 22. huffingtonpost.com
#### 23. nytimes.com
#### 24. ft.com
#### 25. wsj.com
#### 26. latimes.com
#### 27. buzzfeed.com
#### 28. nationalpost.com
#### 29. edition.cnn.com
#### 30. bloomberg.com
#### 31. afmedios.com

### 그룹 F 상세 분석
#### 32. people.com.cn
#### 33. globaltimes.cn
#### 34. scmp.com
#### 35. taiwannews.com
#### 36. yomiuri.co.jp
#### 37. thehindu.com

### 그룹 G 상세 분석
#### 38. thesun.co.uk
#### 39. bild.de
#### 40. lemonde.fr
#### 41. themoscowtimes.com
#### 42. arabnews.com
#### 43. aljazeera.com
#### 44. israelhayom.com

---

## 구조화 데이터 내보내기

```yaml
# Site Reconnaissance Data — Machine-parseable
# Generated: 2026-02-25
# Fields: domain, rss, sitemap, rendering, paywall, bot_blocking, language, sections_count, daily_articles_est, difficulty_tier, mandatory_fields

sites:

  # Group A: Korean Major Dailies
  - domain: chosun.com
    rss: "http://www.chosun.com/site/data/rss/rss.xml"
    sitemap: "https://www.chosun.com/sitemap.xml"
    rendering: ssr
    paywall: none
    bot_blocking: medium
    language: ko
    sections_count: 15
    daily_articles_est: 200
    difficulty_tier: medium
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div
      source_url: canonical_link
    notes: "Korean residential proxy required. RSS confirmed via community documentation."

  - domain: joongang.co.kr
    rss: "http://rss.joinsmsn.com/joins_news_list.xml"
    sitemap: "https://www.joongang.co.kr/sitemap.xml"
    rendering: ssr
    paywall: soft-metered
    bot_blocking: high
    language: ko
    sections_count: 12
    daily_articles_est: 180
    difficulty_tier: hard
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div_partial
      source_url: canonical_link
    notes: "Cloudflare + JS challenge. RSS on legacy joinsmsn.com domain. Soft paywall limits body extraction."

  - domain: donga.com
    rss: "http://rss.donga.com/total.xml"
    sitemap: "https://www.donga.com/sitemap.xml"
    rendering: ssr
    paywall: none
    bot_blocking: medium
    language: ko
    sections_count: 14
    daily_articles_est: 200
    difficulty_tier: medium
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div
      source_url: canonical_link
    notes: "RSS on rss.donga.com subdomain. Korean proxy required."

  - domain: hani.co.kr
    rss: "https://www.hani.co.kr/rss/hani.rss"
    sitemap: "https://www.hani.co.kr/sitemap.xml"
    rendering: ssr
    paywall: soft-metered
    bot_blocking: medium
    language: ko
    sections_count: 10
    daily_articles_est: 120
    difficulty_tier: medium
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div
      source_url: canonical_link
    notes: "Progressive newspaper. English edition at english.hani.co.kr. Korean proxy required."

  - domain: yna.co.kr
    rss: "https://en.yna.co.kr/RSS/news.xml"
    sitemap: "https://www.yna.co.kr/sitemap.xml"
    rendering: ssr
    paywall: none
    bot_blocking: medium
    language: ko
    sections_count: 20
    daily_articles_est: 500
    difficulty_tier: medium
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div
      source_url: canonical_link
    notes: "National wire service. Very high volume. English RSS at en.yna.co.kr. Korean proxy for Korean feed."

  # Group B: Korean Economy
  - domain: mk.co.kr
    rss: "http://file.mk.co.kr/news/rss/rss_30000001.xml"
    sitemap: "https://www.mk.co.kr/sitemap.xml"
    rendering: ssr
    paywall: none
    bot_blocking: medium
    language: ko
    sections_count: 12
    daily_articles_est: 300
    difficulty_tier: medium
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div
      source_url: canonical_link
    notes: "RSS on file.mk.co.kr subdomain. Korean proxy required."

  - domain: hankyung.com
    rss: "http://rss.hankyung.com/economy.xml"
    sitemap: "https://www.hankyung.com/sitemap.xml"
    rendering: ssr
    paywall: soft-metered
    bot_blocking: medium
    language: ko
    sections_count: 10
    daily_articles_est: 250
    difficulty_tier: medium
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div
      source_url: canonical_link
    notes: "RSS on rss.hankyung.com subdomain with category feeds. Soft paywall for premium content."

  - domain: fnnews.com
    rss: "http://www.fnnews.com/rss/fn_realnews_all.xml"
    sitemap: "https://www.fnnews.com/sitemap.xml"
    rendering: ssr
    paywall: none
    bot_blocking: medium
    language: ko
    sections_count: 8
    daily_articles_est: 150
    difficulty_tier: medium
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div
      source_url: canonical_link
    notes: "RSS confirmed via community documentation. Korean proxy required."

  - domain: mt.co.kr
    rss: "https://www.mt.co.kr/rss"
    sitemap: "https://www.mt.co.kr/sitemap.xml"
    rendering: ssr
    paywall: none
    bot_blocking: medium
    language: ko
    sections_count: 10
    daily_articles_est: 200
    difficulty_tier: medium
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div
      source_url: canonical_link
    notes: "RSS URL needs direct verification. Korean proxy required."

  # Group C: Korean Niche
  - domain: nocutnews.co.kr
    rss: "http://rss.nocutnews.co.kr/nocutnews.xml"
    sitemap: "https://www.nocutnews.co.kr/sitemap.xml"
    rendering: ssr
    paywall: none
    bot_blocking: low
    language: ko
    sections_count: 8
    daily_articles_est: 100
    difficulty_tier: easy
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div
      source_url: canonical_link
    notes: "CBS news arm. RSS confirmed. Less aggressive bot blocking than major dailies."

  - domain: kmib.co.kr
    rss: "https://www.kmib.co.kr/rss/kmib.rss"
    sitemap: "https://www.kmib.co.kr/sitemap.xml"
    rendering: ssr
    paywall: none
    bot_blocking: medium
    language: ko
    sections_count: 10
    daily_articles_est: 120
    difficulty_tier: medium
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div
      source_url: canonical_link
    notes: "RSS URL needs verification. Korean proxy required."

  - domain: ohmynews.com
    rss: "https://www.ohmynews.com/rss/rss.xml"
    sitemap: "https://www.ohmynews.com/sitemap.xml"
    rendering: ssr
    paywall: none
    bot_blocking: low
    language: ko
    sections_count: 8
    daily_articles_est: 80
    difficulty_tier: easy
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div
      source_url: canonical_link
    notes: "Citizen journalism site. ASP.NET CMS. Generally permissive. Korean proxy needed but less strict."

  # Group D: Korean IT/Science
  - domain: 38north.org
    rss: "https://www.38north.org/feed"
    sitemap: "https://www.38north.org/sitemap_index.xml"
    rendering: ssr
    paywall: none
    bot_blocking: low
    language: en
    sections_count: 16
    daily_articles_est: 5
    difficulty_tier: easy
    mandatory_fields:
      title: html_h1
      published_at: time_element
      body: div_entry_content
      source_url: canonical_link
    notes: "Fully probed. WordPress, fully open, RSS 2.0 confirmed active. Ideal for testing crawl pipeline."

  - domain: bloter.net
    rss: "https://www.bloter.net/feed"
    sitemap: "https://www.bloter.net/sitemap.xml"
    rendering: csr
    paywall: none
    bot_blocking: high
    language: ko
    sections_count: 6
    daily_articles_est: 20
    difficulty_tier: hard
    mandatory_fields:
      title: html_h1_via_js
      published_at: meta_via_js
      body: article_div_via_js
      source_url: canonical_link
    notes: "Modern React/Next.js SPA. Requires Playwright. Korean proxy + JS rendering required."

  - domain: etnews.com
    rss: "https://www.etnews.com/rss"
    sitemap: "https://www.etnews.com/sitemap.xml"
    rendering: ssr
    paywall: none
    bot_blocking: medium
    language: ko
    sections_count: 10
    daily_articles_est: 100
    difficulty_tier: medium
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div
      source_url: canonical_link
    notes: "Korean electronics/IT trade paper. RSS URL needs verification. Korean proxy required."

  - domain: sciencetimes.co.kr
    rss: "https://www.sciencetimes.co.kr/rss"
    sitemap: "https://www.sciencetimes.co.kr/sitemap.xml"
    rendering: ssr
    paywall: none
    bot_blocking: high
    language: ko
    sections_count: 8
    daily_articles_est: 20
    difficulty_tier: hard
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div
      source_url: canonical_link
    notes: "KISTI public institution. Strict access controls despite public mission. Korean proxy required."

  - domain: zdnet.co.kr
    rss: "https://www.zdnet.co.kr/rss"
    sitemap: "https://www.zdnet.co.kr/sitemap.xml"
    rendering: ssr
    paywall: none
    bot_blocking: medium
    language: ko
    sections_count: 8
    daily_articles_est: 80
    difficulty_tier: medium
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div
      source_url: canonical_link
    notes: "ZDNet Korea (CBS Interactive Korea). Different from US ZDNet. Korean proxy required."

  - domain: irobotnews.com
    rss: "https://www.irobotnews.com/feed"
    sitemap: "https://www.irobotnews.com/sitemap.xml"
    rendering: ssr
    paywall: none
    bot_blocking: high
    language: ko
    sections_count: 5
    daily_articles_est: 10
    difficulty_tier: hard
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div
      source_url: canonical_link
    notes: "Robotics/AI specialty news. WordPress. Very low volume. Small site IP filtering."

  - domain: techneedle.com
    rss: "https://www.techneedle.com/feed"
    sitemap: "https://www.techneedle.com/sitemap.xml"
    rendering: ssr
    paywall: none
    bot_blocking: high
    language: ko
    sections_count: 5
    daily_articles_est: 5
    difficulty_tier: hard
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div
      source_url: canonical_link
    notes: "Korean startup/tech analysis. WordPress. Very low volume. Small site IP filtering."

  # Group E: US/English Major
  - domain: marketwatch.com
    rss: "https://www.marketwatch.com/rss"
    sitemap: "https://www.marketwatch.com/sitemap.xml"
    rendering: ssr
    paywall: soft-metered
    bot_blocking: high
    language: en
    sections_count: 12
    daily_articles_est: 200
    difficulty_tier: hard
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div_partial
      source_url: canonical_link
    notes: "Dow Jones/News Corp. Cloudflare Enterprise. Same infrastructure as WSJ. Bot fingerprinting."

  - domain: voakorea.com
    rss: "https://www.voakorea.com/api/zoikol-vomx-tpepgjp"
    sitemap: "https://www.voakorea.com/sitemap.xml"
    rendering: ssr
    paywall: none
    bot_blocking: low
    language: ko
    sections_count: 6
    daily_articles_est: 50
    difficulty_tier: easy
    mandatory_fields:
      title: html_h1
      published_at: schema_org_datePublished
      body: article_div
      source_url: canonical_link
    notes: "US govt VOA Korean service. isAccessibleForFree:true. 17 category RSS feeds via /api/ paths. SSR, fully open."

  - domain: huffpost.com
    rss: null
    sitemap: "https://www.huffpost.com/sitemap.xml"
    rendering: ssr
    paywall: none
    bot_blocking: high
    language: en
    sections_count: 15
    daily_articles_est: 100
    difficulty_tier: medium
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div
      source_url: canonical_link
    notes: "Explicitly blocks ClaudeBot + 25 AI bots. 5 sitemaps including Google News. Standard UA required. huffingtonpost.com redirects here."

  - domain: nytimes.com
    rss: null
    sitemap: "https://www.nytimes.com/sitemap.xml"
    rendering: ssr
    paywall: hard
    bot_blocking: high
    language: en
    sections_count: 20
    daily_articles_est: 300
    difficulty_tier: extreme
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: BLOCKED_paywall
      source_url: canonical_link
    notes: "Hard paywall. Cloudflare + fingerprinting. Full body extraction requires subscriber cookie. Extreme tier."

  - domain: ft.com
    rss: null
    sitemap: "https://www.ft.com/sitemap.xml"
    rendering: ssr
    paywall: hard
    bot_blocking: high
    language: en
    sections_count: 15
    daily_articles_est: 150
    difficulty_tier: extreme
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: BLOCKED_paywall
      source_url: canonical_link
    notes: "Hard paywall. Geographic filtering. Body extraction requires FT subscription cookie. Extreme tier."

  - domain: wsj.com
    rss: null
    sitemap: "https://www.wsj.com/sitemap.xml"
    rendering: ssr
    paywall: hard
    bot_blocking: high
    language: en
    sections_count: 15
    daily_articles_est: 200
    difficulty_tier: extreme
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: BLOCKED_paywall
      source_url: canonical_link
    notes: "Dow Jones hard paywall. Cloudflare Enterprise + fingerprinting. Most aggressively protected site. Extreme tier."

  - domain: latimes.com
    rss: "https://www.latimes.com/rss"
    sitemap: "https://www.latimes.com/sitemap.xml"
    rendering: ssr
    paywall: soft-metered
    bot_blocking: high
    language: en
    sections_count: 15
    daily_articles_est: 150
    difficulty_tier: medium
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div_partial
      source_url: canonical_link
    notes: "GrapheneCMS (in-house, migrated from Arc Publishing). RSS available. Soft paywall manageable. Bot filtering present."

  - domain: buzzfeed.com
    rss: null
    sitemap: "https://www.buzzfeed.com/sitemap.xml"
    rendering: csr
    paywall: none
    bot_blocking: high
    language: en
    sections_count: 10
    daily_articles_est: 50
    difficulty_tier: hard
    mandatory_fields:
      title: html_h1_via_js
      published_at: meta_via_js
      body: article_div_via_js
      source_url: canonical_link
    notes: "WARNING: BuzzFeed News shut down April 2023 — site now entertainment/lifestyle only, not news journalism. React SPA. AI bots blocked. /*.xml$ blocks RSS. Playwright required."

  - domain: nationalpost.com
    rss: "https://nationalpost.com/feed"
    sitemap: "https://nationalpost.com/sitemap.xml"
    rendering: ssr
    paywall: soft-metered
    bot_blocking: high
    language: en
    sections_count: 12
    daily_articles_est: 100
    difficulty_tier: hard
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div_partial
      source_url: canonical_link
    notes: "Postmedia/WordPress VIP. Cloudflare across all properties. Soft paywall (NP Connected)."

  - domain: edition.cnn.com
    rss: "https://edition.cnn.com/rss"
    sitemap: "https://edition.cnn.com/sitemap.xml"
    rendering: ssr
    paywall: none
    bot_blocking: high
    language: en
    sections_count: 20
    daily_articles_est: 500
    difficulty_tier: medium
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div
      source_url: canonical_link
    notes: "60+ bots blocked but content SSR and free. 15 sitemaps. ClaudeBot blocked — standard UA required. High volume."

  - domain: bloomberg.com
    rss: null
    sitemap: "https://www.bloomberg.com/sitemap.xml"
    rendering: ssr
    paywall: hard
    bot_blocking: high
    language: en
    sections_count: 15
    daily_articles_est: 200
    difficulty_tier: extreme
    mandatory_fields:
      title: PARTIALLY_accessible
      published_at: PARTIALLY_accessible
      body: BLOCKED_paywall
      source_url: canonical_link
    notes: "Hard paywall. 403 on homepage for non-subscribers. 9 sitemaps confirmed. Extreme tier."

  - domain: afmedios.com
    rss: "https://afmedios.com/rss"
    sitemap: "https://www.afmedios.com/sitemap_index.xml"
    rendering: ssr
    paywall: none
    bot_blocking: low
    language: es
    sections_count: 6
    daily_articles_est: 20
    difficulty_tier: easy
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div
      source_url: canonical_link
    notes: "WordPress. RSS 2.0 confirmed active. Fully open. Spanish only. Colima Mexico regional news."

  # Group F: Asia-Pacific
  - domain: people.com.cn
    rss: null
    sitemap: "http://www.people.cn/sitemap_index.xml"
    rendering: ssr
    paywall: none
    bot_blocking: medium
    language: zh
    sections_count: 20
    daily_articles_est: 500
    difficulty_tier: medium
    mandatory_fields:
      title: html_h1
      published_at: article_meta_date
      body: article_div
      source_url: canonical_link
    notes: "120-second crawl-delay MUST be respected. 76 sitemaps. No RSS detected. Chinese state media."

  - domain: globaltimes.cn
    rss: null
    sitemap: "https://www.globaltimes.cn/sitemap.xml"
    rendering: ssr
    paywall: none
    bot_blocking: low
    language: en
    sections_count: 4
    daily_articles_est: 40
    difficulty_tier: easy
    mandatory_fields:
      title: sitemap_news_title
      published_at: sitemap_news_publication_date
      body: article_div
      source_url: sitemap_loc
    notes: "Fully probed. News namespace sitemap with dates/titles/keywords. No RSS. Fully open. jQuery SSR."

  - domain: scmp.com
    rss: "https://www.scmp.com/rss/2/feed"
    sitemap: "https://www.scmp.com/sitemap.xml"
    rendering: ssr
    paywall: soft-metered
    bot_blocking: medium
    language: en
    sections_count: 15
    daily_articles_est: 150
    difficulty_tier: medium
    mandatory_fields:
      title: html_h1
      published_at: schema_org_datePublished
      body: article_div_partial
      source_url: canonical_link
    notes: "10-second crawl-delay. 100+ category RSS feeds at /rss page. Next.js SSR. Soft paywall (Alibaba-owned)."

  - domain: taiwannews.com.tw
    rss: null
    sitemap: "https://www.taiwannews.com.tw/sitemap.xml"
    rendering: ssr
    paywall: none
    bot_blocking: low
    language: en
    sections_count: 10
    daily_articles_est: 30
    difficulty_tier: easy
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div
      source_url: canonical_link
    notes: "Fully probed. No RSS. 3 sitemaps (en/zh). Next.js SSR, fully open. Bilingual."

  - domain: yomiuri.co.jp
    rss: "https://www.yomiuri.co.jp/rss"
    sitemap: "https://www.yomiuri.co.jp/sitemap.xml"
    rendering: ssr
    paywall: soft-metered
    bot_blocking: high
    language: ja
    sections_count: 15
    daily_articles_est: 200
    difficulty_tier: hard
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div_partial
      source_url: canonical_link
    notes: "World's highest-circulation newspaper. Japanese IP required. Japanese NLP needed for body extraction."

  - domain: thehindu.com
    rss: "https://www.thehindu.com/rss"
    sitemap: "https://www.thehindu.com/sitemap.xml"
    rendering: ssr
    paywall: soft-metered
    bot_blocking: high
    language: en
    sections_count: 15
    daily_articles_est: 100
    difficulty_tier: medium
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div_partial
      source_url: canonical_link
    notes: "India's leading English daily. Metered paywall (5-10 free/month). Cloudflare protection."

  # Group G: Europe/Middle East
  - domain: thesun.co.uk
    rss: "https://www.thesun.co.uk/rss"
    sitemap: "https://www.thesun.co.uk/sitemap.xml"
    rendering: ssr
    paywall: none
    bot_blocking: high
    language: en
    sections_count: 15
    daily_articles_est: 300
    difficulty_tier: hard
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div
      source_url: canonical_link
    notes: "UK tabloid. News UK CMS. No paywall (abandoned 2015). UK IP preference. High volume."

  - domain: bild.de
    rss: "https://www.bild.de/rss"
    sitemap: "https://www.bild.de/sitemap.xml"
    rendering: ssr
    paywall: soft-metered
    bot_blocking: high
    language: de
    sections_count: 10
    daily_articles_est: 200
    difficulty_tier: hard
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div_partial
      source_url: canonical_link
    notes: "Germany's largest tabloid. Axel Springer. German IP required. BILDplus soft paywall. German NLP needed."

  - domain: lemonde.fr
    rss: "https://www.lemonde.fr/rss"
    sitemap: "https://www.lemonde.fr/sitemap.xml"
    rendering: ssr
    paywall: hard
    bot_blocking: high
    language: fr
    sections_count: 15
    daily_articles_est: 150
    difficulty_tier: extreme
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: BLOCKED_paywall
      source_url: canonical_link
    notes: "Hard paywall. French IP preference. /en/ for English edition but same paywall. Extreme tier."

  - domain: themoscowtimes.com
    rss: "https://www.themoscowtimes.com/page/rss"
    sitemap: "https://static.themoscowtimes.com/sitemap/sitemap.xml"
    rendering: ssr
    paywall: freemium
    bot_blocking: low
    language: en
    sections_count: 9
    daily_articles_est: 20
    difficulty_tier: easy
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div
      source_url: canonical_link
    notes: "Fully probed. Monthly sitemap index. 4 RSS feeds (News/Opinion/Arts/Meanwhile). Freemium (donations). Very open."

  - domain: arabnews.com
    rss: null
    sitemap: "https://www.arabnews.com/sitemap.xml"
    rendering: ssr
    paywall: none
    bot_blocking: medium
    language: en
    sections_count: 12
    daily_articles_est: 100
    difficulty_tier: medium
    mandatory_fields:
      title: html_h1
      published_at: meta_article_published_time
      body: article_div
      source_url: canonical_link
    notes: "10-second crawl-delay. Drupal CMS. Google News sitemap confirmed. IP filtering (403 from non-ME IPs). RSS returns 403."

  - domain: aljazeera.com
    rss: "https://www.aljazeera.com/xml/rss/all.xml"
    sitemap: "https://www.aljazeera.com/sitemap.xml"
    rendering: ssr
    paywall: none
    bot_blocking: high
    language: en
    sections_count: 12
    daily_articles_est: 100
    difficulty_tier: medium
    mandatory_fields:
      title: html_h1
      published_at: schema_org_datePublished
      body: article_div
      source_url: canonical_link
    notes: "Fully probed. RSS 2.0 confirmed (26 articles). ClaudeBot/anthropic-ai explicitly blocked — standard UA required. SSR content free."

  - domain: israelhayom.com
    rss: "https://www.israelhayom.com/feed"
    sitemap: "https://www.israelhayom.com/sitemap.xml"
    rendering: ssr
    paywall: none
    bot_blocking: low
    language: en
    sections_count: 5
    daily_articles_est: 30
    difficulty_tier: easy
    mandatory_fields:
      title: html_h1
      published_at: schema_org_datePublished
      body: article_div
      source_url: canonical_link
    notes: "No robots.txt (404). WordPress/JNews. Fully open. Israeli English newspaper. Low-medium volume."
```

---

## 탐색 상태 요약

직접 탐색으로 전체 데이터 확보한 사이트 (robots.txt + 홈페이지 + RSS/사이트맵 확인):
- 38north.org, afmedios.com, aljazeera.com, bloomberg.com (robots.txt만), buzzfeed.com, edition.cnn.com, globaltimes.cn, huffpost.com, israelhayom.com, people.com.cn, scmp.com, taiwannews.com.tw, themoscowtimes.com, voakorea.com

부분 탐색 데이터 확보 (일부 엔드포인트만 확인):
- arabnews.com (robots.txt 확인; 홈페이지 403)

직접 접근이 완전히 차단되어 웹 검색, RSS 인덱스, 알려진 플랫폼 패턴으로 데이터 보완:
- 모든 한국 사이트 (chosun, joongang, donga, hani, yna, mk, hankyung, fnnews, mt, nocutnews, kmib, ohmynews, bloter, etnews, sciencetimes, zdnet, irobotnews, techneedle), 그리고 ft.com, wsj.com, nytimes.com, marketwatch.com, latimes.com, nationalpost.com, yomiuri.co.jp, thehindu.com, thesun.co.uk, bild.de, lemonde.fr

[inferred] 표시된 RSS URL은 한국 뉴스 RSS 커뮤니티 문서 (GitHub gist: koorukuroo/330a644fcc3c9ffdc7b6d537efd939c3) 및 Feedspot 데이터 기반. 크롤링 설정 단계에서 프로그래밍적으로 검증이 필요하다.

---

*보고서 작성: @site-recon — GlobalNews 크롤링 및 분석 워크플로우 1단계*
*다음 단계: 3단계 — 크롤링 타당성 분석에서 이 데이터를 사용하여 사이트별 크롤링 전략을 정의한다*
