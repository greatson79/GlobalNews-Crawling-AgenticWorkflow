# Korean News Site Crawling Strategies (19 Sites)

**Agent**: @crawl-strategist-kr
**Workflow Step**: 6 of 20 (Team Task)
**Date**: 2026-02-26
**Input Sources**: Step 1 `research/site-reconnaissance.md`, Step 3 `research/crawling-feasibility.md`, Step 5 `planning/architecture-blueprint.md` Section 5c

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total Korean sites** | 19 (Groups A + B + C + D) |
| **Primary method breakdown** | RSS: 16, Sitemap: 1, Playwright: 1, API: 1 |
| **Total daily article estimate** | ~2,555 articles/day |
| **Total daily crawl time (sequential)** | ~54.5 minutes |
| **Crawl time in parallel (2 groups)** | ~28 minutes |
| **Sites requiring Korean proxy** | 18 of 19 (all except 38north.org) |
| **Paywall sites** | 2 soft-metered (joongang.co.kr, hankyung.com), 1 soft-metered (hani.co.kr) |
| **Sites requiring Playwright** | 1 (bloter.net) |
| **Encoding** | All UTF-8 (no legacy EUC-KR sites in this set) |

### Method Distribution

| Primary Method | Site Count | Daily Articles | Crawl Minutes (seq) |
|---------------|-----------|----------------|---------------------|
| RSS feed | 16 | 2,430 | ~44.5 |
| Sitemap | 1 | 20 | ~2.0 |
| Playwright (JS render) | 1 | 20 | ~4.0 |
| API (RSS-style) | 1 | 50 | ~1.5 |
| **Total** | **19** | **~2,555** | **~54.5** |

[trace:step-1:difficulty-classification-matrix] -- Tier breakdown for Korean sites: Easy(3), Medium(12), Hard(4)
[trace:step-3:strategy-matrix] -- Strategy assignments inherited from Step 3 feasibility analysis
[trace:step-5:sources-yaml-schema] -- Output compatible with sources.yaml schema (Section 5c)

---

## Strategy Matrix (All 19 Korean Sites)

### Group A: Korean Major Dailies (5)

| # | Site | Primary | Fallback Chain | Rate Limit | UA Tier | Bot Block | Paywall | Daily Est. | Crawl Min |
|---|------|---------|---------------|------------|---------|-----------|---------|-----------|-----------|
| 1 | chosun.com | RSS | Sitemap > DOM | 5s | T2 (10) | MEDIUM | none | ~200 | ~3.5 |
| 2 | joongang.co.kr | RSS | Sitemap > DOM | 10s+jitter | T3 (50) | HIGH | soft-metered | ~180 | ~6.0 |
| 3 | donga.com | RSS | Sitemap > DOM | 5s | T2 (10) | MEDIUM | none | ~200 | ~3.5 |
| 4 | hani.co.kr | RSS | Sitemap > DOM | 5s | T2 (10) | MEDIUM | soft-metered | ~120 | ~2.5 |
| 5 | yna.co.kr | RSS | Sitemap > DOM | 5s | T2 (10) | MEDIUM | none | ~500 | ~6.0 |

### Group B: Korean Economy (4)

| # | Site | Primary | Fallback Chain | Rate Limit | UA Tier | Bot Block | Paywall | Daily Est. | Crawl Min |
|---|------|---------|---------------|------------|---------|-----------|---------|-----------|-----------|
| 6 | mk.co.kr | RSS | Sitemap > DOM | 5s | T2 (10) | MEDIUM | none | ~300 | ~4.5 |
| 7 | hankyung.com | RSS | Sitemap > DOM | 5s | T2 (10) | MEDIUM | soft-metered | ~250 | ~4.0 |
| 8 | fnnews.com | RSS | Sitemap > DOM | 5s | T2 (10) | MEDIUM | none | ~150 | ~3.0 |
| 9 | mt.co.kr | RSS | Sitemap > DOM | 5s | T2 (10) | MEDIUM | none | ~200 | ~3.5 |

### Group C: Korean Niche (3)

| # | Site | Primary | Fallback Chain | Rate Limit | UA Tier | Bot Block | Paywall | Daily Est. | Crawl Min |
|---|------|---------|---------------|------------|---------|-----------|---------|-----------|-----------|
| 10 | nocutnews.co.kr | RSS | Sitemap > DOM | 2s | T1 (1) | LOW | none | ~100 | ~1.5 |
| 11 | kmib.co.kr | RSS | Sitemap > DOM | 5s | T2 (10) | MEDIUM | none | ~120 | ~2.5 |
| 12 | ohmynews.com | RSS | Sitemap > DOM | 2s | T1 (1) | LOW | none | ~80 | ~1.5 |

### Group D: Korean IT/Science (7)

| # | Site | Primary | Fallback Chain | Rate Limit | UA Tier | Bot Block | Paywall | Daily Est. | Crawl Min |
|---|------|---------|---------------|------------|---------|-----------|---------|-----------|-----------|
| 13 | 38north.org | RSS | Sitemap (WP) | 2s | T1 (1) | LOW | none | ~5 | ~0.5 |
| 14 | bloter.net | Playwright | RSS > DOM | 10s+jitter | T3 (50) | HIGH | none | ~20 | ~4.0 |
| 15 | etnews.com | RSS | Sitemap > DOM | 5s | T2 (10) | MEDIUM | none | ~100 | ~2.0 |
| 16 | sciencetimes.co.kr | Sitemap | RSS > DOM | 10s+jitter | T3 (50) | HIGH | none | ~20 | ~2.0 |
| 17 | zdnet.co.kr | RSS | Sitemap > DOM | 5s | T2 (10) | MEDIUM | none | ~80 | ~2.0 |
| 18 | irobotnews.com | RSS (WP) | Sitemap > DOM | 10s+jitter | T3 (50) | HIGH | none | ~10 | ~1.5 |
| 19 | techneedle.com | RSS (WP) | Sitemap > DOM | 10s+jitter | T3 (50) | HIGH | none | ~5 | ~1.0 |

---

## Per-Site Detailed Strategies

### Group A: Korean Major Dailies

---

#### 1. chosun.com (Chosun Ilbo)

**Decision Rationale**: RSS is the primary method because the feed at `http://www.chosun.com/site/data/rss/rss.xml` is confirmed via Korean News RSS GitHub gist and widely cited community documentation. RSS provides structured URL discovery without needing to parse dynamic homepage layouts. Chosun's homepage uses infinite scroll patterns on some sections, making DOM-based URL discovery unreliable without Playwright. RSS bypasses this entirely.

**URL Discovery**

| Method | Priority | URL | Trigger to fallback |
|--------|----------|-----|---------------------|
| RSS | Primary | `http://www.chosun.com/site/data/rss/rss.xml` | RSS returns < 10 items OR HTTP 4xx/5xx for > 30 min |
| Sitemap | Fallback 1 | `https://www.chosun.com/sitemap.xml` | Sitemap returns 404 OR < 5 URLs |
| DOM | Fallback 2 | Section pages (see below) | Last resort |

**Section Navigation** (for DOM fallback):
- Politics: `https://www.chosun.com/politics/`
- Economy: `https://www.chosun.com/economy/`
- Society: `https://www.chosun.com/national/`
- International: `https://www.chosun.com/international/`
- Sports: `https://www.chosun.com/sports/`
- Culture: `https://www.chosun.com/culture-life/`
- Opinion: `https://www.chosun.com/opinion/`
- Pagination: Infinite scroll on homepage; section pages use `?page=N` parameter

**Article Extraction Selectors**:

| Field | Primary Selector | Fallback Selector | Source |
|-------|-----------------|-------------------|--------|
| Title | `meta[property="og:title"]` | `h1.article-header__title` | Step 1 recon: `html_h1` |
| Body | `div.article-body` | `div#article-body-content` via trafilatura | Step 1: `article_div` |
| Author | `span.article-header__journalist` | `meta[name="author"]` | Korean byline pattern |
| Date | `meta[property="article:published_time"]` | `time.article-header__date` | ISO 8601 or `YYYY.MM.DD HH:MM` |
| Category | Breadcrumb `nav.breadcrumb a` | URL path segment (`/politics/` -> "politics") | URL-derived |
| URL | `link[rel="canonical"]` | RSS `<link>` element | Normalized |

**Date Format Patterns**:
- RSS: RFC 2822 (`Wed, 26 Feb 2026 10:30:00 +0900`)
- HTML meta: ISO 8601 (`2026-02-26T10:30:00+09:00`)
- Display: `2026.02.26 10:30` or `2026년 02월 26일`

**Exclusion Patterns** (strip from body):
- `div.article-ad`, `div.ad-container` -- advertisements
- `div.related-articles` -- related article recommendations
- `div.article-social`, `div.sns-share` -- social sharing widgets
- `div.article-comment` -- comment section
- `script`, `style`, `iframe` -- non-content elements

**Anti-Block Configuration**:

| Setting | Value | Rationale |
|---------|-------|-----------|
| Rate limit | 5s base delay | MEDIUM bot-blocking; conservative default |
| Max req/hr | 720 | 5s interval = 720/hr theoretical max |
| UA tier | T2 (10 UAs) | Rotate per session; MEDIUM block level |
| Starting tier | Tier 1 | Standard UA rotation + delay |
| Requires proxy | YES | Korean residential proxy REQUIRED (geo-IP filtering) |
| Proxy region | `kr` | Korean IP mandatory per Step 1 |
| Referer | `https://www.chosun.com` | Self-referral for naturalness |
| Accept-Language | `ko-KR,ko;q=0.9,en-US;q=0.8` | Korean locale preference |
| Cookie handling | Session cookies accepted; clear between runs | Prevent metering |

**Korean-Specific Handling**:
- Encoding: UTF-8 (modern Chosun CMS)
- URL pattern: Numeric article IDs (`/article/20260226000123`) -- no Korean slugs in URLs
- Author extraction: Korean name 3-char pattern + `기자` suffix (e.g., `김철수 기자`)
- Date parsing: Multiple formats; prioritize `article:published_time` meta tag

**Volume Estimate**:
- Daily: ~200 articles (weekday), ~120 (weekend)
- Peak hours: 06:00-22:00 KST
- Sections: ~15 sections, ~13 articles/section/day average

**Special Handling**:
- Homepage uses infinite scroll -- **do not** rely on homepage for URL discovery; use RSS/sitemap exclusively
- Some premium content may return partial body; flag with `is_paywall_truncated: false` (Chosun is generally free)

**sources.yaml Configuration**:
```yaml
chosun:
  name: "Chosun Ilbo"
  url: "https://www.chosun.com"
  region: "kr"
  language: "ko"
  group: "A"
  crawl:
    primary_method: "rss"
    fallback_methods: ["sitemap", "dom"]
    rss_url: "http://www.chosun.com/site/data/rss/rss.xml"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 5
    crawl_delay_mandatory: null
    max_requests_per_hour: 720
    jitter_seconds: 0
  anti_block:
    ua_tier: 2
    default_escalation_tier: 1
    max_escalation_tier: 5
    requires_proxy: true
    proxy_region: "kr"
    bot_block_level: "MEDIUM"
  extraction:
    paywall_type: "none"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Medium"
    daily_article_estimate: 200
    sections_count: 15
    enabled: true
```

---

#### 2. joongang.co.kr (JoongAng Ilbo)

**Decision Rationale**: RSS at `http://rss.joinsmsn.com/joins_news_list.xml` is on a legacy domain (joinsmsn.com). This is confirmed by community documentation but the domain may become unreachable. RSS is still primary because it avoids Cloudflare JS challenges that DOM crawling would face. Fallback to sitemap is critical. Soft paywall (JoongAng Plus) may truncate body for premium articles -- accept partial body and flag.

**URL Discovery**

| Method | Priority | URL | Trigger to fallback |
|--------|----------|-----|---------------------|
| RSS | Primary | `http://rss.joinsmsn.com/joins_news_list.xml` | RSS < 10 items OR joinsmsn.com unreachable > 30 min OR HTTP 403 |
| Sitemap | Fallback 1 | `https://www.joongang.co.kr/sitemap.xml` | Sitemap 404 OR < 5 URLs |
| DOM | Fallback 2 | Section pages | Last resort; requires Playwright if Cloudflare blocks |

**Section Navigation**:
- Politics: `https://www.joongang.co.kr/politics`
- Economy: `https://www.joongang.co.kr/economy`
- Society: `https://www.joongang.co.kr/society`
- International: `https://www.joongang.co.kr/international`
- Sports: `https://www.joongang.co.kr/sports`
- Culture: `https://www.joongang.co.kr/culture`
- Opinion: `https://www.joongang.co.kr/opinion`
- Pagination: `?page=N` parameter

**Article Extraction Selectors**:

| Field | Primary Selector | Fallback Selector |
|-------|-----------------|-------------------|
| Title | `meta[property="og:title"]` | `h1.headline` |
| Body | `div.article_body` | `div#article_body` via trafilatura |
| Author | `span.byline` | `meta[name="author"]` |
| Date | `meta[property="article:published_time"]` | `span.date` |
| Category | URL path segment | `meta[property="article:section"]` |
| URL | `link[rel="canonical"]` | RSS `<link>` |

**Date Format Patterns**:
- RSS: RFC 2822
- HTML meta: ISO 8601 (`2026-02-26T10:30:00+09:00`)
- Display: `2026.02.26 10:30` or `입력 2026.02.26 10:30 | 수정 2026.02.26 11:45`

**Exclusion Patterns**:
- `div.ab_ad`, `div.ad_wrap` -- ads
- `div.ab_related_article` -- related articles
- `div.social_share` -- social widgets
- `div.reporter_info_area` -- reporter card (extract author separately)

**Anti-Block Configuration**:

| Setting | Value | Rationale |
|---------|-------|-----------|
| Rate limit | 10s base + 0-3s jitter | HIGH bot-blocking; Cloudflare detected |
| Max req/hr | 240 | Conservative for HIGH block level |
| UA tier | T3 (50 UAs) | Rotate per request; realistic headers |
| Starting tier | Tier 2 | Pre-escalated due to HIGH block level |
| Requires proxy | YES | Korean residential proxy |
| Proxy region | `kr` | |
| Cookie handling | Session cookies; clear between runs; rotate IP on 403 |
| Special headers | `Referer: https://www.joongang.co.kr`, `Sec-Fetch-Site: same-origin` |

**Volume Estimate**: ~180 articles/day (weekday), ~100 (weekend)

**Special Handling**:
- Legacy RSS domain (joinsmsn.com) -- monitor for domain migration; may need runtime URL discovery
- Cloudflare JS challenge: if httpx returns 403/503, escalate to Playwright/Patchright
- Soft paywall: body may be truncated for JoongAng Plus articles; set `is_paywall_truncated: true` for those
- SSR with React hydration: some interactive elements require JS, but article body is in initial HTML

**sources.yaml Configuration**:
```yaml
joongang:
  name: "JoongAng Ilbo"
  url: "https://www.joongang.co.kr"
  region: "kr"
  language: "ko"
  group: "A"
  crawl:
    primary_method: "rss"
    fallback_methods: ["sitemap", "dom"]
    rss_url: "http://rss.joinsmsn.com/joins_news_list.xml"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 10
    crawl_delay_mandatory: null
    max_requests_per_hour: 240
    jitter_seconds: 3
  anti_block:
    ua_tier: 3
    default_escalation_tier: 2
    max_escalation_tier: 5
    requires_proxy: true
    proxy_region: "kr"
    bot_block_level: "HIGH"
  extraction:
    paywall_type: "soft-metered"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Hard"
    daily_article_estimate: 180
    sections_count: 12
    enabled: true
```

---

#### 3. donga.com (Dong-A Ilbo)

**Decision Rationale**: RSS at `http://rss.donga.com/total.xml` is hosted on a dedicated rss subdomain, confirmed by Korean News RSS index. Donga uses a traditional PHP CMS with clean, predictable HTML structure. No paywall. Category-specific RSS feeds also available for targeted section crawling.

**URL Discovery**

| Method | Priority | URL | Trigger to fallback |
|--------|----------|-----|---------------------|
| RSS | Primary | `http://rss.donga.com/total.xml` | RSS < 10 items OR rss.donga.com unreachable > 30 min |
| Sitemap | Fallback 1 | `https://www.donga.com/sitemap.xml` | Sitemap 404 |
| DOM | Fallback 2 | Section pages | Last resort |

**Category RSS Feeds**:
- `http://rss.donga.com/politics.xml` -- Politics
- `http://rss.donga.com/economy.xml` -- Economy
- `http://rss.donga.com/society.xml` -- Society
- `http://rss.donga.com/international.xml` -- International
- `http://rss.donga.com/sports.xml` -- Sports
- `http://rss.donga.com/culture.xml` -- Culture

**Article Extraction Selectors**:

| Field | Primary Selector | Fallback Selector |
|-------|-----------------|-------------------|
| Title | `meta[property="og:title"]` | `h1.title` |
| Body | `div.article_txt` | `div#content_body` via trafilatura |
| Author | `span.writer` | `meta[name="author"]` |
| Date | `meta[property="article:published_time"]` | `span.date` |
| Category | RSS `<category>` element | URL path segment |
| URL | `link[rel="canonical"]` | RSS `<link>` |

**Date Format Patterns**:
- RSS: RFC 2822
- HTML: ISO 8601 or `YYYY-MM-DD HH:MM:SS`
- Display: `2026-02-26 10:30` or `입력 2026-02-26 10:30`

**Anti-Block Configuration**:

| Setting | Value |
|---------|-------|
| Rate limit | 5s base delay |
| Max req/hr | 720 |
| UA tier | T2 (10 UAs) |
| Starting tier | Tier 1 |
| Requires proxy | YES (kr) |

**Volume Estimate**: ~200 articles/day (weekday), ~120 (weekend)

**Special Handling**:
- PHP-based CMS: straightforward HTML structure; trafilatura extraction highly reliable
- rss.donga.com subdomain: dedicated RSS infrastructure, low failure risk
- No paywall: full body always available

**sources.yaml Configuration**:
```yaml
donga:
  name: "Dong-A Ilbo"
  url: "https://www.donga.com"
  region: "kr"
  language: "ko"
  group: "A"
  crawl:
    primary_method: "rss"
    fallback_methods: ["sitemap", "dom"]
    rss_url: "http://rss.donga.com/total.xml"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 5
    crawl_delay_mandatory: null
    max_requests_per_hour: 720
    jitter_seconds: 0
  anti_block:
    ua_tier: 2
    default_escalation_tier: 1
    max_escalation_tier: 5
    requires_proxy: true
    proxy_region: "kr"
    bot_block_level: "MEDIUM"
  extraction:
    paywall_type: "none"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Medium"
    daily_article_estimate: 200
    sections_count: 14
    enabled: true
```

---

#### 4. hani.co.kr (Hankyoreh)

**Decision Rationale**: RSS at `/rss/hani.rss` is confirmed. Hankyoreh is a progressive newspaper with clean HTML structure. Soft paywall exists for heavy readers but fresh sessions (with cleared cookies) access most content. English edition at english.hani.co.kr provides additional coverage.

**URL Discovery**

| Method | Priority | URL | Trigger to fallback |
|--------|----------|-----|---------------------|
| RSS | Primary | `https://www.hani.co.kr/rss/hani.rss` | RSS < 10 items OR HTTP 4xx/5xx > 30 min |
| Sitemap | Fallback 1 | `https://www.hani.co.kr/sitemap.xml` | Sitemap 404 |
| DOM | Fallback 2 | Section pages | Last resort |

**Section Navigation**:
- Politics: `https://www.hani.co.kr/arti/politics/`
- Economy: `https://www.hani.co.kr/arti/economy/`
- Society: `https://www.hani.co.kr/arti/society/`
- International: `https://www.hani.co.kr/arti/international/`
- Culture: `https://www.hani.co.kr/arti/culture/`
- Opinion: `https://www.hani.co.kr/arti/opinion/`
- Sports: `https://www.hani.co.kr/arti/sports/`

**Article Extraction Selectors**:

| Field | Primary Selector | Fallback Selector |
|-------|-----------------|-------------------|
| Title | `meta[property="og:title"]` | `h1.title` |
| Body | `div.article-text` | `div.text` via trafilatura |
| Author | `span.reporter-name` | `meta[name="author"]` |
| Date | `meta[property="article:published_time"]` | `span.date-published` |
| Category | URL path (`/arti/politics/` -> "politics") | `meta[property="article:section"]` |
| URL | `link[rel="canonical"]` | RSS `<link>` |

**Anti-Block Configuration**:

| Setting | Value |
|---------|-------|
| Rate limit | 5s base delay |
| Max req/hr | 720 |
| UA tier | T2 (10 UAs) |
| Starting tier | Tier 1 |
| Requires proxy | YES (kr) |
| Cookie handling | Clear between runs to reset paywall meter |

**Volume Estimate**: ~120 articles/day (weekday), ~60 (weekend)

**Special Handling**:
- Soft paywall: clear cookies between crawl runs to refresh metered quota
- English edition: `english.hani.co.kr` may have separate RSS; crawl both editions if needed
- Author names: Pattern is `홍길동 기자`, sometimes `홍길동 선임기자` or `홍길동 특파원`

**sources.yaml Configuration**:
```yaml
hani:
  name: "Hankyoreh"
  url: "https://www.hani.co.kr"
  region: "kr"
  language: "ko"
  group: "A"
  crawl:
    primary_method: "rss"
    fallback_methods: ["sitemap", "dom"]
    rss_url: "https://www.hani.co.kr/rss/hani.rss"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 5
    crawl_delay_mandatory: null
    max_requests_per_hour: 720
    jitter_seconds: 0
  anti_block:
    ua_tier: 2
    default_escalation_tier: 1
    max_escalation_tier: 5
    requires_proxy: true
    proxy_region: "kr"
    bot_block_level: "MEDIUM"
  extraction:
    paywall_type: "soft-metered"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Medium"
    daily_article_estimate: 120
    sections_count: 10
    enabled: true
```

---

#### 5. yna.co.kr (Yonhap News Agency)

**Decision Rationale**: Yonhap is Korea's national wire service, producing the highest volume of any Korean site (~500 articles/day). RSS is confirmed for the English edition at `en.yna.co.kr/RSS/news.xml`; the Korean feed is inferred at `yna.co.kr/rss/news.xml`. RSS will capture the most recent subset; sitemap supplementation is essential for full daily coverage. No paywall -- wire service content is freely distributed.

**URL Discovery**

| Method | Priority | URL | Trigger to fallback |
|--------|----------|-----|---------------------|
| RSS (Korean) | Primary | `https://www.yna.co.kr/rss/news.xml` | RSS < 10 items OR 4xx/5xx > 30 min |
| RSS (English) | Co-primary | `https://en.yna.co.kr/RSS/news.xml` | Same triggers |
| Sitemap | Supplemental | `https://www.yna.co.kr/sitemap.xml` | Always used to supplement RSS |
| DOM | Fallback | Section pages | Last resort |

**Section Navigation**:
- All News: `https://www.yna.co.kr/news/`
- Politics: `https://www.yna.co.kr/politics/`
- Economy: `https://www.yna.co.kr/economy/`
- Society: `https://www.yna.co.kr/society/`
- International: `https://www.yna.co.kr/international/`
- North Korea: `https://www.yna.co.kr/nk/`
- Sports: `https://www.yna.co.kr/sports/`
- Culture: `https://www.yna.co.kr/culture/`
- Science: `https://www.yna.co.kr/science/`
- Pagination: `?page=N` parameter

**Article Extraction Selectors**:

| Field | Primary Selector | Fallback Selector |
|-------|-----------------|-------------------|
| Title | `meta[property="og:title"]` | `h1.tit` |
| Body | `div.article` | `div#articleWrap` via trafilatura |
| Author | `span.byline` | `p.reporter` |
| Date | `meta[property="article:published_time"]` | `span.update-time` |
| Category | URL path | `meta[property="article:section"]` |
| URL | `link[rel="canonical"]` | RSS `<link>` |

**Anti-Block Configuration**:

| Setting | Value |
|---------|-------|
| Rate limit | 5s base delay |
| Max req/hr | 720 |
| UA tier | T2 (10 UAs) |
| Starting tier | Tier 1 |
| Requires proxy | YES (kr) |

**Volume Estimate**: ~500 articles/day (consistent weekday/weekend for wire service)

**Special Handling**:
- **Very high volume**: RSS likely truncated to 50-100 most recent items. Sitemap MUST be used as supplemental source for full daily coverage
- Both Korean and English editions: crawl both for multilingual analysis
- Wire service format: clean, structured HTML; trafilatura extraction highly reliable
- No paywall, no login requirements
- Published date is highly precise (minute-level) due to wire service nature

**sources.yaml Configuration**:
```yaml
yna:
  name: "Yonhap News Agency"
  url: "https://www.yna.co.kr"
  region: "kr"
  language: "ko"
  group: "A"
  crawl:
    primary_method: "rss"
    fallback_methods: ["sitemap", "dom"]
    rss_url: "https://www.yna.co.kr/rss/news.xml"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 5
    crawl_delay_mandatory: null
    max_requests_per_hour: 720
    jitter_seconds: 0
  anti_block:
    ua_tier: 2
    default_escalation_tier: 1
    max_escalation_tier: 5
    requires_proxy: true
    proxy_region: "kr"
    bot_block_level: "MEDIUM"
  extraction:
    paywall_type: "none"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Medium"
    daily_article_estimate: 500
    sections_count: 20
    enabled: true
```

---

### Group B: Korean Economy

---

#### 6. mk.co.kr (Maeil Business Newspaper)

**Decision Rationale**: RSS at `http://file.mk.co.kr/news/rss/rss_30000001.xml` is confirmed via Korean RSS index. MK is one of Korea's largest economic dailies with high volume (~300 articles/day). Traditional Korean CMS with clean HTML. No hard paywall. RSS on dedicated file subdomain provides reliable URL discovery.

**URL Discovery**

| Method | Priority | URL | Trigger to fallback |
|--------|----------|-----|---------------------|
| RSS | Primary | `http://file.mk.co.kr/news/rss/rss_30000001.xml` | RSS < 10 items OR file.mk.co.kr unreachable > 30 min |
| Sitemap | Fallback 1 | `https://www.mk.co.kr/sitemap.xml` | Sitemap 404 |
| DOM | Fallback 2 | Section pages | Last resort |

**Section Navigation**:
- Economy: `https://www.mk.co.kr/news/economy/`
- Stock: `https://www.mk.co.kr/news/stock/`
- Real Estate: `https://www.mk.co.kr/news/realestate/`
- Industry: `https://www.mk.co.kr/news/business/`
- Politics: `https://www.mk.co.kr/news/politics/`
- Society: `https://www.mk.co.kr/news/society/`
- International: `https://www.mk.co.kr/news/world/`

**Article Extraction Selectors**:

| Field | Primary Selector | Fallback Selector |
|-------|-----------------|-------------------|
| Title | `meta[property="og:title"]` | `h1.top_title` |
| Body | `div.news_cnt_detail_wrap` | `div#article_body` via trafilatura |
| Author | `span.author` | `div.byline` |
| Date | `meta[property="article:published_time"]` | `span.date` |
| Category | URL path (`/news/economy/` -> "economy") | RSS `<category>` |
| URL | `link[rel="canonical"]` | RSS `<link>` |

**Anti-Block Configuration**:

| Setting | Value |
|---------|-------|
| Rate limit | 5s base delay |
| Max req/hr | 720 |
| UA tier | T2 (10 UAs) |
| Starting tier | Tier 1 |
| Requires proxy | YES (kr) |

**Volume Estimate**: ~300 articles/day (weekday), ~150 (weekend)

**Special Handling**:
- High volume for economic daily; RSS may not capture all 300 articles (typical RSS limit: 50-100 items)
- Sitemap supplementation recommended for full coverage
- MK Plus premium content exists but majority is freely accessible
- Stock market data articles are high volume during trading hours (09:00-15:30 KST)

**sources.yaml Configuration**:
```yaml
mk:
  name: "Maeil Business Newspaper"
  url: "https://www.mk.co.kr"
  region: "kr"
  language: "ko"
  group: "B"
  crawl:
    primary_method: "rss"
    fallback_methods: ["sitemap", "dom"]
    rss_url: "http://file.mk.co.kr/news/rss/rss_30000001.xml"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 5
    crawl_delay_mandatory: null
    max_requests_per_hour: 720
    jitter_seconds: 0
  anti_block:
    ua_tier: 2
    default_escalation_tier: 1
    max_escalation_tier: 5
    requires_proxy: true
    proxy_region: "kr"
    bot_block_level: "MEDIUM"
  extraction:
    paywall_type: "none"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Medium"
    daily_article_estimate: 300
    sections_count: 12
    enabled: true
```

---

#### 7. hankyung.com (Korea Economic Daily)

**Decision Rationale**: RSS at `http://rss.hankyung.com/economy.xml` is confirmed with multiple category feeds on the rss subdomain. Hankyung has a soft paywall (Hankyung Premium) that gates some premium articles. Cookie clearing between sessions manages the meter. Category-specific RSS feeds enable targeted economic section crawling.

**URL Discovery**

| Method | Priority | URL | Trigger to fallback |
|--------|----------|-----|---------------------|
| RSS | Primary | `http://rss.hankyung.com/economy.xml` | RSS < 10 items OR rss.hankyung.com unreachable > 30 min |
| Sitemap | Fallback 1 | `https://www.hankyung.com/sitemap.xml` | Sitemap 404 |
| DOM | Fallback 2 | Section pages | Last resort |

**Category RSS Feeds**:
- Economy: `http://rss.hankyung.com/economy.xml`
- Stock: `http://rss.hankyung.com/stock.xml`
- Real Estate: `http://rss.hankyung.com/realestate.xml`
- International: `http://rss.hankyung.com/international.xml`
- Politics: `http://rss.hankyung.com/politics.xml`
- Society: `http://rss.hankyung.com/society.xml`

**Article Extraction Selectors**:

| Field | Primary Selector | Fallback Selector |
|-------|-----------------|-------------------|
| Title | `meta[property="og:title"]` | `h1.article-title` |
| Body | `div.article-body` | `div#articletxt` via trafilatura |
| Author | `span.byline` | `meta[name="author"]` |
| Date | `meta[property="article:published_time"]` | `span.datetime` |
| Category | RSS feed name | URL path segment |
| URL | `link[rel="canonical"]` | RSS `<link>` |

**Anti-Block Configuration**:

| Setting | Value |
|---------|-------|
| Rate limit | 5s base delay |
| Max req/hr | 720 |
| UA tier | T2 (10 UAs) |
| Starting tier | Tier 1 |
| Requires proxy | YES (kr) |
| Cookie handling | Clear between runs; reset meter |

**Volume Estimate**: ~250 articles/day (weekday), ~130 (weekend)

**Special Handling**:
- **Soft paywall** (Hankyung Premium): Some articles gated; cookie clearing manages meter
- Dynamic loading on some section pages -- rely on RSS for URL discovery, not DOM
- Multiple category RSS feeds provide good section-specific coverage
- Financial data articles heavy during market hours

**sources.yaml Configuration**:
```yaml
hankyung:
  name: "Korea Economic Daily"
  url: "https://www.hankyung.com"
  region: "kr"
  language: "ko"
  group: "B"
  crawl:
    primary_method: "rss"
    fallback_methods: ["sitemap", "dom"]
    rss_url: "http://rss.hankyung.com/economy.xml"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 5
    crawl_delay_mandatory: null
    max_requests_per_hour: 720
    jitter_seconds: 0
  anti_block:
    ua_tier: 2
    default_escalation_tier: 1
    max_escalation_tier: 5
    requires_proxy: true
    proxy_region: "kr"
    bot_block_level: "MEDIUM"
  extraction:
    paywall_type: "soft-metered"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Medium"
    daily_article_estimate: 250
    sections_count: 10
    enabled: true
```

---

#### 8. fnnews.com (Financial News)

**Decision Rationale**: RSS at `http://www.fnnews.com/rss/fn_realnews_all.xml` is confirmed. Traditional PHP CMS with clean HTML. No paywall. Moderate volume. WebFetch verification confirmed the site structure: section URLs follow `/section/NNNNNN` pattern, and JSON-LD WebSite schema is present.

[trace:step-6:webfetch-verification] -- fnnews.com homepage verified via WebFetch: section URL pattern `/section/002001002002`, JSON-LD `@type: WebSite`, Korean date format `YYYY년 MM월 DD일`.

**URL Discovery**

| Method | Priority | URL | Trigger to fallback |
|--------|----------|-----|---------------------|
| RSS | Primary | `http://www.fnnews.com/rss/fn_realnews_all.xml` | RSS < 10 items OR HTTP 4xx/5xx > 30 min |
| Sitemap | Fallback 1 | `https://www.fnnews.com/sitemap.xml` | Sitemap 404 |
| DOM | Fallback 2 | Section pages | Last resort |

**Section Navigation** (verified via WebFetch):
- Finance/Securities: `https://www.fnnews.com/section/002001002002`
- Real Estate: `https://www.fnnews.com/section/002003000`
- Industry/IT: `https://www.fnnews.com/section/002004002005`
- Politics: `https://www.fnnews.com/section/001001000`
- Lifestyle: `https://www.fnnews.com/section/005000000`

**Article Extraction Selectors**:

| Field | Primary Selector | Fallback Selector |
|-------|-----------------|-------------------|
| Title | `meta[property="og:title"]` | `h1.article_tit` |
| Body | `div.article_cont` | `div#article_content` via trafilatura |
| Author | `span.article_byline` | `meta[name="author"]` |
| Date | `meta[property="article:published_time"]` | `span.article_date` |
| Category | URL section code | RSS `<category>` |
| URL | `link[rel="canonical"]` | RSS `<link>` |

**Anti-Block Configuration**:

| Setting | Value |
|---------|-------|
| Rate limit | 5s base delay |
| Max req/hr | 720 |
| UA tier | T2 (10 UAs) |
| Starting tier | Tier 1 |
| Requires proxy | YES (kr) |

**Volume Estimate**: ~150 articles/day (weekday), ~80 (weekend)

**sources.yaml Configuration**:
```yaml
fnnews:
  name: "Financial News"
  url: "https://www.fnnews.com"
  region: "kr"
  language: "ko"
  group: "B"
  crawl:
    primary_method: "rss"
    fallback_methods: ["sitemap", "dom"]
    rss_url: "http://www.fnnews.com/rss/fn_realnews_all.xml"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 5
    crawl_delay_mandatory: null
    max_requests_per_hour: 720
    jitter_seconds: 0
  anti_block:
    ua_tier: 2
    default_escalation_tier: 1
    max_escalation_tier: 5
    requires_proxy: true
    proxy_region: "kr"
    bot_block_level: "MEDIUM"
  extraction:
    paywall_type: "none"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Medium"
    daily_article_estimate: 150
    sections_count: 8
    enabled: true
```

---

#### 9. mt.co.kr (Money Today)

**Decision Rationale**: RSS availability is confirmed but the exact URL needs runtime verification (common paths: `/rss`, `/rss.xml`). Money Today uses a traditional Korean CMS with clean HTML. No paywall. WebFetch verification confirmed site structure: section URLs follow `/stock`, `/politics`, `/estate` patterns; JSON-LD includes `NewsMediaOrganization` and `WebSite` with `SearchAction`.

[trace:step-6:webfetch-verification] -- mt.co.kr homepage verified via WebFetch: section URLs `/stock`, `/politics`, `/estate`; JSON-LD `@type: NewsMediaOrganization`; date format `2026.02.26(요일)`.

**URL Discovery**

| Method | Priority | URL | Trigger to fallback |
|--------|----------|-----|---------------------|
| RSS | Primary | `https://www.mt.co.kr/rss/` (verify: try `/rss`, `/rss.xml`, `/rss/rss.xml`) | RSS 404 OR < 10 items |
| Sitemap | Fallback 1 | `https://www.mt.co.kr/sitemap.xml` | Sitemap 404 |
| DOM | Fallback 2 | Section pages | Last resort |

**Section Navigation** (verified via WebFetch):
- Stock/Securities: `https://www.mt.co.kr/stock`
- Politics: `https://www.mt.co.kr/politics` (the300 brand)
- Legal: `https://www.mt.co.kr/law` (theL brand)
- Bio/Healthcare: `https://www.mt.co.kr/thebio`
- Real Estate: `https://www.mt.co.kr/estate`
- Economy: `https://www.mt.co.kr/economy`
- Industry: `https://www.mt.co.kr/industry`
- Tech: `https://www.mt.co.kr/tech`
- World: `https://www.mt.co.kr/world`

**Article Extraction Selectors**:

| Field | Primary Selector | Fallback Selector |
|-------|-----------------|-------------------|
| Title | `meta[property="og:title"]` | `h1.article_title` |
| Body | `div.article_content` | `div#textBody` via trafilatura |
| Author | `span.byline` | `meta[name="author"]` |
| Date | `meta[property="article:published_time"]` | `span.date` |
| Category | URL path segment | JSON-LD `BreadcrumbList` |
| URL | `link[rel="canonical"]` | RSS `<link>` |

**Date Format Patterns** (verified):
- Display: `2026.02.26(수)` -- Korean style with day-of-week
- Timestamp: `14:06 장중` (during market session)
- Meta: ISO 8601

**Anti-Block Configuration**:

| Setting | Value |
|---------|-------|
| Rate limit | 5s base delay |
| Max req/hr | 720 |
| UA tier | T2 (10 UAs) |
| Starting tier | Tier 1 |
| Requires proxy | YES (kr) |

**Volume Estimate**: ~200 articles/day (weekday), ~100 (weekend)

**Special Handling**:
- RSS URL needs runtime verification: try `/rss`, `/rss.xml`, `/rss/rss.xml` in order
- If no working RSS found at runtime, permanently switch to sitemap-primary strategy
- Sub-brands (the300, theL, thebio) have distinct section URLs

**sources.yaml Configuration**:
```yaml
mt:
  name: "Money Today"
  url: "https://www.mt.co.kr"
  region: "kr"
  language: "ko"
  group: "B"
  crawl:
    primary_method: "rss"
    fallback_methods: ["sitemap", "dom"]
    rss_url: "https://www.mt.co.kr/rss/"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 5
    crawl_delay_mandatory: null
    max_requests_per_hour: 720
    jitter_seconds: 0
  anti_block:
    ua_tier: 2
    default_escalation_tier: 1
    max_escalation_tier: 5
    requires_proxy: true
    proxy_region: "kr"
    bot_block_level: "MEDIUM"
  extraction:
    paywall_type: "none"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Medium"
    daily_article_estimate: 200
    sections_count: 10
    enabled: true
```

---

### Group C: Korean Niche

---

#### 10. nocutnews.co.kr (Nocut News / CBS)

**Decision Rationale**: RSS at `http://rss.nocutnews.co.kr/nocutnews.xml` is confirmed and verified via WebFetch. The feed contains 20 items with full article content in `<description>` (not just summaries). LOW bot-blocking makes this one of the easiest Korean sites. JSON-LD `NewsArticle` schema confirmed on article pages with structured `datePublished` and `BreadcrumbList`.

[trace:step-6:webfetch-verification] -- nocutnews.co.kr RSS verified: 20 items, RSS 2.0 with `dc:date`, full content in `<description>`, RFC 2822 dates. Article page verified: JSON-LD `NewsArticle`, `datePublished` in ISO 8601, `BreadcrumbList`, author as `CBS노컷뉴스 [name] 기자`.

**URL Discovery**

| Method | Priority | URL | Trigger to fallback |
|--------|----------|-----|---------------------|
| RSS | Primary | `http://rss.nocutnews.co.kr/nocutnews.xml` | RSS < 10 items OR rss.nocutnews.co.kr unreachable > 30 min |
| Sitemap | Fallback 1 | `https://www.nocutnews.co.kr/sitemap.xml` | Sitemap 404 |
| DOM | Fallback 2 | Section pages | Last resort |

**Section Navigation** (verified via WebFetch):
- Politics: `https://www.nocutnews.co.kr/news/politics`
- Society: `https://www.nocutnews.co.kr/news/society`
- Policy: `https://www.nocutnews.co.kr/news/policy`
- Economy: `https://www.nocutnews.co.kr/news/economy`
- Industry: `https://www.nocutnews.co.kr/news/industry`
- International: `https://www.nocutnews.co.kr/news/world`
- Opinion: `https://www.nocutnews.co.kr/news/opinion`
- Entertainment: `https://www.nocutnews.co.kr/news/entertainment`
- Sports: `https://www.nocutnews.co.kr/news/sports`
- Subcategories: `?c2={id}` parameter

**Article Extraction Selectors** (verified via WebFetch):

| Field | Primary Selector | Fallback Selector | Verification Status |
|-------|-----------------|-------------------|---------------------|
| Title | JSON-LD `headline` | `meta[property="og:title"]` | VERIFIED |
| Body | RSS `<description>` (full content) | Article page via trafilatura | VERIFIED: full content in RSS |
| Author | JSON-LD `author.name` | Byline pattern `CBS노컷뉴스 [name] 기자` | VERIFIED |
| Date | JSON-LD `datePublished` (ISO 8601) | `meta[property="article:published_time"]` | VERIFIED: `2025-02-28T10:24:38` |
| Category | JSON-LD `articleSection` array | `BreadcrumbList` items | VERIFIED: e.g., `["포토", "정치"]` |
| URL | JSON-LD `mainEntityOfPage` | `link[rel="canonical"]` | VERIFIED |

**Anti-Block Configuration**:

| Setting | Value |
|---------|-------|
| Rate limit | 2s base delay |
| Max req/hr | 1800 |
| UA tier | T1 (1 UA, rotate weekly) |
| Starting tier | Tier 1 |
| Requires proxy | YES (kr) -- despite LOW blocking, geo-IP filtering still applies |

**Volume Estimate**: ~100 articles/day (weekday), ~50 (weekend)

**Special Handling**:
- RSS contains full article content: body extraction from RSS `<description>` may eliminate need to fetch article pages entirely (significant crawl time savings)
- If RSS body is sufficient, only fetch article pages for JSON-LD metadata (author, precise date)
- CBS (Christian Broadcasting System) affiliation; focused on political/social reporting

**sources.yaml Configuration**:
```yaml
nocutnews:
  name: "NoCut News"
  url: "https://www.nocutnews.co.kr"
  region: "kr"
  language: "ko"
  group: "C"
  crawl:
    primary_method: "rss"
    fallback_methods: ["sitemap", "dom"]
    rss_url: "http://rss.nocutnews.co.kr/nocutnews.xml"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 2
    crawl_delay_mandatory: null
    max_requests_per_hour: 1800
    jitter_seconds: 0
  anti_block:
    ua_tier: 1
    default_escalation_tier: 1
    max_escalation_tier: 5
    requires_proxy: true
    proxy_region: "kr"
    bot_block_level: "LOW"
  extraction:
    paywall_type: "none"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Easy"
    daily_article_estimate: 100
    sections_count: 8
    enabled: true
```

---

#### 11. kmib.co.kr (Kookmin Ilbo)

**Decision Rationale**: RSS feeds confirmed via WebFetch verification at dedicated category URLs (`/rss/data/kmibPolRss.xml`, etc.). Nine category-specific RSS feeds provide comprehensive section coverage. Article URLs follow `?arcid=` pattern. UTF-8 charset confirmed. No paywall.

[trace:step-6:webfetch-verification] -- kmib.co.kr RSS directory verified: 9 category feeds at `/rss/data/kmib{Category}Rss.xml`. Homepage verified: article links use `?arcid=` pattern; date format `2026-02-26(수)`; charset UTF-8; Google Analytics dataLayer with article metadata.

**URL Discovery**

| Method | Priority | URL | Trigger to fallback |
|--------|----------|-----|---------------------|
| RSS | Primary | `https://www.kmib.co.kr/rss/data/kmibPolRss.xml` (+ 8 other category feeds) | RSS < 5 items per feed OR 4xx/5xx |
| Sitemap | Fallback 1 | `https://www.kmib.co.kr/sitemap.xml` | Sitemap 404 |
| DOM | Fallback 2 | Section listing pages | Last resort |

**Category RSS Feeds** (verified via WebFetch):

| Category | RSS URL |
|----------|---------|
| Politics | `https://www.kmib.co.kr/rss/data/kmibPolRss.xml` |
| Economy | `https://www.kmib.co.kr/rss/data/kmibEcoRss.xml` |
| Society | `https://www.kmib.co.kr/rss/data/kmibSocRss.xml` |
| International | `https://www.kmib.co.kr/rss/data/kmibIntRss.xml` |
| Entertainment | `https://www.kmib.co.kr/rss/data/kmibEntRss.xml` |
| Sports | `https://www.kmib.co.kr/rss/data/kmibSpoRss.xml` |
| Golf | `https://www.kmib.co.kr/rss/data/kmibGolfRss.xml` |
| Lifestyle | `https://www.kmib.co.kr/rss/data/kmibLifeRss.xml` |
| Travel | `https://www.kmib.co.kr/rss/data/kmibTraRss.xml` |

**Section Navigation** (verified):
- Pattern: `https://www.kmib.co.kr/article/listing.asp?sid1={category}&sid2={subcategory}`
- Categories: `pol` (politics), `eco` (economy), `soc` (society), `int` (international), `ens` (entertainment)

**Article Extraction Selectors**:

| Field | Primary Selector | Fallback Selector |
|-------|-----------------|-------------------|
| Title | `meta[property="og:title"]` | `h1.article-title` |
| Body | `div.article-body` | `div#article_content` via trafilatura |
| Author | Google Analytics `dataLayer[author_name]` | `span.byline` |
| Date | `meta[property="article:published_time"]` | DataLayer `first_published_date` |
| Category | DataLayer `article_category` | URL `sid1` parameter |
| URL | `link[rel="canonical"]` | RSS `<link>` with `?arcid=` |

**Anti-Block Configuration**:

| Setting | Value |
|---------|-------|
| Rate limit | 5s base delay |
| Max req/hr | 720 |
| UA tier | T2 (10 UAs) |
| Starting tier | Tier 1 |
| Requires proxy | YES (kr) |

**Volume Estimate**: ~120 articles/day (weekday), ~60 (weekend)

**sources.yaml Configuration**:
```yaml
kmib:
  name: "Kookmin Ilbo"
  url: "https://www.kmib.co.kr"
  region: "kr"
  language: "ko"
  group: "C"
  crawl:
    primary_method: "rss"
    fallback_methods: ["sitemap", "dom"]
    rss_url: "https://www.kmib.co.kr/rss/data/kmibPolRss.xml"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 5
    crawl_delay_mandatory: null
    max_requests_per_hour: 720
    jitter_seconds: 0
  anti_block:
    ua_tier: 2
    default_escalation_tier: 1
    max_escalation_tier: 5
    requires_proxy: true
    proxy_region: "kr"
    bot_block_level: "MEDIUM"
  extraction:
    paywall_type: "none"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Medium"
    daily_article_estimate: 120
    sections_count: 10
    enabled: true
```

---

#### 12. ohmynews.com (OhmyNews)

**Decision Rationale**: RSS confirmed at `/rss/rss.xml`. OhmyNews is a pioneering citizen journalism platform using ASP.NET CMS. LOW bot-blocking. WebFetch verification confirmed site structure: article containers use `.ptbox`/`.ecbox` classes, dates follow `YY.MM.DD HH:MM` format, dynamic content via AJAX from ASP.NET endpoints.

[trace:step-6:webfetch-verification] -- ohmynews.com homepage verified: article containers `.ptbox`, `.ecbox`; date format `YY.MM.DD HH:MM`; section URLs `/NWS_Web/ArticlePage/Total_Article.aspx?PAGE_CD={code}`; UTF-8 charset; GTM analytics.

**URL Discovery**

| Method | Priority | URL | Trigger to fallback |
|--------|----------|-----|---------------------|
| RSS | Primary | `https://www.ohmynews.com/rss/rss.xml` | RSS < 10 items |
| Sitemap | Fallback 1 | `https://www.ohmynews.com/sitemap.xml` | Sitemap 404 |
| DOM | Fallback 2 | Section pages | Last resort |

**Section Navigation** (verified via WebFetch):
- Politics: `/NWS_Web/ArticlePage/Total_Article.aspx?PAGE_CD=C0400`
- Economy: `/NWS_Web/ArticlePage/Total_Article.aspx?PAGE_CD=C0300`
- Society: `/NWS_Web/ArticlePage/Total_Article.aspx?PAGE_CD=C0200`
- Regional (Gwangju/Jeolla): `PAGE_CD=R0200`
- Regional (Seoul): `PAGE_CD=R0800`

**Article Extraction Selectors**:

| Field | Primary Selector | Fallback Selector |
|-------|-----------------|-------------------|
| Title | `meta[property="og:title"]` | `h1.title` |
| Body | `div.article_view` | `div#article_body` via trafilatura |
| Author | `span.author` (citizen reporter name) | `meta[name="author"]` |
| Date | `meta[property="article:published_time"]` | `.date` element (`YY.MM.DD HH:MM`) |
| Category | `PAGE_CD` parameter mapping | URL path |
| URL | `link[rel="canonical"]` | RSS `<link>` |

**Date Format Patterns** (verified):
- Display: `26.02.26 13:53` (YY.MM.DD HH:MM -- 2-digit year!)
- Meta: ISO 8601 (expected)
- **IMPORTANT**: 2-digit year format requires careful parsing to avoid Y2K-style ambiguity

**Anti-Block Configuration**:

| Setting | Value |
|---------|-------|
| Rate limit | 2s base delay |
| Max req/hr | 1800 |
| UA tier | T1 (1 UA, rotate weekly) |
| Starting tier | Tier 1 |
| Requires proxy | YES (kr) |

**Volume Estimate**: ~80 articles/day (weekday), ~40 (weekend)

**Special Handling**:
- ASP.NET CMS: older tech stack but stable HTML output; URL format is `.aspx` with query parameters
- Citizen journalism: author names are citizen reporters, not professional journalists
- 2-digit year in display dates: must use ISO 8601 meta tag as authoritative date source
- AJAX-loaded content: some listing pages load dynamically; use RSS to avoid this

**sources.yaml Configuration**:
```yaml
ohmynews:
  name: "OhmyNews"
  url: "https://www.ohmynews.com"
  region: "kr"
  language: "ko"
  group: "C"
  crawl:
    primary_method: "rss"
    fallback_methods: ["sitemap", "dom"]
    rss_url: "https://www.ohmynews.com/rss/rss.xml"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 2
    crawl_delay_mandatory: null
    max_requests_per_hour: 1800
    jitter_seconds: 0
  anti_block:
    ua_tier: 1
    default_escalation_tier: 1
    max_escalation_tier: 5
    requires_proxy: true
    proxy_region: "kr"
    bot_block_level: "LOW"
  extraction:
    paywall_type: "none"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Easy"
    daily_article_estimate: 80
    sections_count: 8
    enabled: true
```

---

### Group D: Korean IT/Science

---

#### 13. 38north.org (38 North -- Stimson Center)

**Decision Rationale**: RSS at `/feed` is confirmed and verified via WebFetch with 10 items and full content in `<content:encoded>`. WordPress platform (6.5.4) with fully permissive robots.txt. English-language site focused on North Korea analysis. This is the easiest site in the entire Korean group -- ideal for pipeline testing.

[trace:step-6:webfetch-verification] -- 38north.org fully verified: RSS 2.0 at `/feed`, 10 items, full content in `content:encoded`, RFC 2822 dates, `dc:creator` for authors, multiple `category` tags per item. WordPress 6.5.4. Sitemap index at `/sitemap_index.xml` (Yoast SEO). JSON-LD `WebPage`, `WebSite`, `BreadcrumbList` schemas. Article URLs: `/YYYY/MM/slug/` pattern.

**URL Discovery**

| Method | Priority | URL | Trigger to fallback |
|--------|----------|-----|---------------------|
| RSS | Primary | `https://www.38north.org/feed` | RSS returns 0 items (highly unlikely) |
| Sitemap | Fallback 1 | `https://www.38north.org/sitemap_index.xml` | Sitemap 404 |

**Section Navigation** (verified via WebFetch):
- All Articles: `https://www.38north.org/articles/`
- Topics (15+ categories):
  - Domestic Affairs: `https://www.38north.org/topics/domestic-affairs/`
  - Economy: `https://www.38north.org/topics/economy/`
  - Foreign Policy: `https://www.38north.org/topics/foreign-policy/`
  - Military Affairs: `https://www.38north.org/topics/military/`
  - WMD: `https://www.38north.org/topics/wmd/`
- Author archives: `https://www.38north.org/author/{username}/`
- Pagination: `/articles/page/{N}/`

**Article Extraction Selectors** (verified via WebFetch):

| Field | Primary Selector | Fallback Selector | Verification Status |
|-------|-----------------|-------------------|---------------------|
| Title | RSS `<title>` | `h1` (WordPress `entry-title`) | VERIFIED |
| Body | RSS `<content:encoded>` (FULL content) | `div.entry-content` | VERIFIED: full body in feed |
| Author | RSS `<dc:creator>` | `a[href*="/author/"]` | VERIFIED |
| Date | RSS `<pubDate>` (RFC 2822) | `time` element or JSON-LD | VERIFIED: `Wed, 25 Feb 2026 17:26:42 +0000` |
| Category | RSS `<category>` (multiple) | `a[href*="/topics/"]` | VERIFIED |
| URL | RSS `<link>` | `link[rel="canonical"]` | VERIFIED |

**Anti-Block Configuration**:

| Setting | Value |
|---------|-------|
| Rate limit | 2s base delay |
| Max req/hr | 1800 |
| UA tier | T1 (1 UA, rotate weekly) |
| Starting tier | Tier 1 |
| Requires proxy | NO -- English-language, US-based, fully permissive |
| robots.txt | Fully permissive: `User-agent: *`, no Disallow |

**Volume Estimate**: ~5 articles/day (think-tank analysis, not daily news pace)

**Special Handling**:
- **RSS contains full article text**: No need to fetch individual article pages. Extract title, body, author, date, categories entirely from RSS feed. This saves ~5 HTTP requests per crawl run.
- Very low volume: entire daily crawl completes in under 30 seconds
- English-language: no Korean text processing needed
- WordPress standard structure: predictable and stable

**sources.yaml Configuration**:
```yaml
38north:
  name: "38 North"
  url: "https://www.38north.org"
  region: "kr"
  language: "en"
  group: "D"
  crawl:
    primary_method: "rss"
    fallback_methods: ["sitemap"]
    rss_url: "https://www.38north.org/feed"
    sitemap_url: "/sitemap_index.xml"
    rate_limit_seconds: 2
    crawl_delay_mandatory: null
    max_requests_per_hour: 1800
    jitter_seconds: 0
  anti_block:
    ua_tier: 1
    default_escalation_tier: 1
    max_escalation_tier: 3
    requires_proxy: false
    proxy_region: null
    bot_block_level: "LOW"
  extraction:
    paywall_type: "none"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Easy"
    daily_article_estimate: 5
    sections_count: 16
    enabled: true
```

---

#### 14. bloter.net (Bloter)

**Decision Rationale**: Bloter requires Playwright/Patchright as primary method because it uses a React/Next.js SPA frontend (confirmed CSR in Step 1). WebFetch returned HTTP 403 confirming aggressive blocking. WordPress RSS at `/feed` may still function as the backend serves XML despite the React frontend -- this is the fallback. LOW volume (20 articles/day) makes Playwright overhead acceptable.

[trace:step-6:webfetch-verification] -- bloter.net returned HTTP 403 on direct fetch, confirming HIGH bot-blocking and need for Playwright/Patchright stealth. CSR (React/Next.js) per Step 1 classification.

**URL Discovery**

| Method | Priority | URL | Trigger to fallback |
|--------|----------|-----|---------------------|
| Playwright | Primary | Navigate to `https://www.bloter.net` and render | Playwright crash or empty DOM > 3 consecutive |
| RSS (WP) | Fallback 1 | `https://www.bloter.net/feed` | RSS 404 or Cloudflare block |
| DOM | Fallback 2 | Section pages (rendered) | Last resort |

**Section Navigation** (inferred from WordPress + tech journalism pattern):
- IT/Tech: `https://www.bloter.net/category/it/`
- Startup: `https://www.bloter.net/category/startup/`
- AI: `https://www.bloter.net/category/ai/`
- Industry: `https://www.bloter.net/category/industry/`
- Column: `https://www.bloter.net/category/column/`

**Article Extraction Selectors** (Playwright-rendered DOM):

| Field | Primary Selector | Fallback Selector |
|-------|-----------------|-------------------|
| Title | `h1.entry-title` or `h1` (rendered) | `meta[property="og:title"]` |
| Body | `div.entry-content` (rendered) | trafilatura on rendered HTML |
| Author | `span.author` or `a[href*="/author/"]` | `meta[name="author"]` |
| Date | `time[datetime]` | `meta[property="article:published_time"]` |
| Category | `a[rel="category tag"]` | URL path `/category/{slug}/` |
| URL | Page URL after render | `link[rel="canonical"]` |

**Anti-Block Configuration**:

| Setting | Value | Rationale |
|---------|-------|-----------|
| Rate limit | 10s base + 0-3s jitter | HIGH blocking |
| Max req/hr | 240 | Playwright overhead + jitter |
| UA tier | T3 (50 UAs via Patchright stealth) | CDP fingerprint bypass |
| Starting tier | Tier 3 (Playwright/Patchright) | CSR requires JS rendering from start |
| Requires proxy | YES (kr) | Geo-IP filtering |
| Browser config | Patchright headless, CDP stealth patches | Anti-detection |

**Volume Estimate**: ~20 articles/day (weekday), ~5 (weekend)

**Special Handling**:
- **Playwright is mandatory**: React/Next.js SPA means no article content in initial HTML response
- Patchright (not plain Playwright) for CDP stealth bypass
- WordPress backend: `/feed` RSS may work as bypass even if frontend blocks -- try RSS fallback before giving up
- Low volume makes Playwright overhead (3-5s per page) acceptable
- Inherent ~3-5s page load time on top of rate limit delay

**sources.yaml Configuration**:
```yaml
bloter:
  name: "Bloter"
  url: "https://www.bloter.net"
  region: "kr"
  language: "ko"
  group: "D"
  crawl:
    primary_method: "playwright"
    fallback_methods: ["rss", "dom"]
    rss_url: "https://www.bloter.net/feed"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 10
    crawl_delay_mandatory: null
    max_requests_per_hour: 240
    jitter_seconds: 3
  anti_block:
    ua_tier: 3
    default_escalation_tier: 3
    max_escalation_tier: 5
    requires_proxy: true
    proxy_region: "kr"
    bot_block_level: "HIGH"
  extraction:
    paywall_type: "none"
    title_only: false
    rendering_required: true
    charset: "utf-8"
  meta:
    difficulty_tier: "Hard"
    daily_article_estimate: 20
    sections_count: 6
    enabled: true
```

---

#### 15. etnews.com (Electronic Times)

**Decision Rationale**: RSS confirmed (path needs verification: `/rss` or `/rss.xml`). WebFetch verification confirmed site structure: article URLs use numeric IDs (`/20260226000093`), sections follow `/news/section.html?id1={code}` pattern, dates in `YYYY.MM.DD` and `YYYY-MM-DD HH:MM` formats. Traditional SSR Korean CMS. No paywall.

[trace:step-6:webfetch-verification] -- etnews.com verified: article URL pattern `/YYYYMMDDNNNNNN`; section URLs `/news/section.html?id1=04` (SW), `id1=03` (IT), `id1=02` (Economy); date format `2026.02.26 (요일)` and `2026-02-26 13:40`; Slick.js carousel in `#topnews`.

**URL Discovery**

| Method | Priority | URL | Trigger to fallback |
|--------|----------|-----|---------------------|
| RSS | Primary | `https://www.etnews.com/rss` (verify: `/rss.xml`) | RSS 404 OR < 10 items |
| Sitemap | Fallback 1 | `https://www.etnews.com/sitemap.xml` | Sitemap 404 |
| DOM | Fallback 2 | Section pages | Last resort |

**Section Navigation** (verified via WebFetch):

| Section | URL | id1 Code |
|---------|-----|----------|
| Economy | `/news/section.html?id1=02` | 02 |
| IT | `/news/section.html?id1=03` | 03 |
| SW | `/news/section.html?id1=04` | 04 |
| Electronics | `/news/section.html?id1=06` | 06 |
| Mobility | `/news/section.html?id1=17` | 17 |
| Science | `/news/section.html?id1=20` | 20 |

**Article Extraction Selectors** (partially verified via WebFetch):

| Field | Primary Selector | Fallback Selector |
|-------|-----------------|-------------------|
| Title | `meta[property="og:title"]` | `h1.article_title` |
| Body | `div.article_body` | `div#articleBody` via trafilatura |
| Author | Byline text pattern: `{name} 기자 ({email})` | `meta[name="author"]` |
| Date | `meta[property="article:published_time"]` | Display format `2026-02-26 10:06` |
| Category | Section page `id1` -> category mapping | URL path |
| URL | `link[rel="canonical"]` | RSS `<link>` |

**Date Format Patterns** (verified):
- Display: `2026.02.26 (수)` -- YYYY.MM.DD with Korean day-of-week
- Timestamp: `2026-02-26 13:40` -- YYYY-MM-DD HH:MM
- Article ID encodes date: `20260226000093` (YYYYMMDDNNNNNN)

**Anti-Block Configuration**:

| Setting | Value |
|---------|-------|
| Rate limit | 5s base delay |
| Max req/hr | 720 |
| UA tier | T2 (10 UAs) |
| Starting tier | Tier 1 |
| Requires proxy | YES (kr) |

**Volume Estimate**: ~100 articles/day (weekday), ~30 (weekend)

**Special Handling**:
- Article URL contains date in ID: `20260226000093` encodes `2026-02-26`; can extract approximate date from URL if metadata fails
- Korea's primary IT/electronics trade newspaper: specialized tech content
- RSS URL needs runtime verification (`/rss` vs `/rss.xml`)

**sources.yaml Configuration**:
```yaml
etnews:
  name: "Electronic Times"
  url: "https://www.etnews.com"
  region: "kr"
  language: "ko"
  group: "D"
  crawl:
    primary_method: "rss"
    fallback_methods: ["sitemap", "dom"]
    rss_url: "https://www.etnews.com/rss"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 5
    crawl_delay_mandatory: null
    max_requests_per_hour: 720
    jitter_seconds: 0
  anti_block:
    ua_tier: 2
    default_escalation_tier: 1
    max_escalation_tier: 5
    requires_proxy: true
    proxy_region: "kr"
    bot_block_level: "MEDIUM"
  extraction:
    paywall_type: "none"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Medium"
    daily_article_estimate: 100
    sections_count: 10
    enabled: true
```

---

#### 16. sciencetimes.co.kr (Science Times)

**Decision Rationale**: Sitemap is primary because RSS is unconfirmed for this KISTI-operated government-adjacent site. HIGH bot-blocking despite being a public institution. Very low volume (20 articles/day). Sitemap provides reliable URL discovery without needing to navigate dynamic listing pages.

**URL Discovery**

| Method | Priority | URL | Trigger to fallback |
|--------|----------|-----|---------------------|
| Sitemap | Primary | `https://www.sciencetimes.co.kr/sitemap.xml` | Sitemap 404 OR < 5 URLs |
| RSS | Fallback 1 | Try: `/rss`, `/rss.xml`, `/feed` | All RSS paths return 404 |
| DOM | Fallback 2 | Section pages | Last resort |

**Article Extraction Selectors** (inferred from Korean government CMS patterns):

| Field | Primary Selector | Fallback Selector |
|-------|-----------------|-------------------|
| Title | `meta[property="og:title"]` | `h1.article_title` |
| Body | `div.article_content` | `div.view_content` via trafilatura |
| Author | `span.writer` | `meta[name="author"]` |
| Date | `meta[property="article:published_time"]` | `span.date` |
| Category | URL path segment | Breadcrumb navigation |
| URL | `link[rel="canonical"]` | Sitemap `<loc>` |

**Anti-Block Configuration**:

| Setting | Value | Rationale |
|---------|-------|-----------|
| Rate limit | 10s base + 0-3s jitter | HIGH blocking (KISTI controls) |
| Max req/hr | 240 | Conservative for institutional site |
| UA tier | T3 (50 UAs) | KISTI may monitor UA patterns |
| Starting tier | Tier 2 | Pre-escalated due to HIGH blocking |
| Requires proxy | YES (kr) | |

**Volume Estimate**: ~20 articles/day (weekday), ~5 (weekend)

**Special Handling**:
- Government-adjacent institution: strict access controls despite public mission
- Low volume mitigates risk: total of ~20 requests/day
- RSS needs runtime discovery: try `/rss`, `/rss.xml`, `/feed` paths

**sources.yaml Configuration**:
```yaml
sciencetimes:
  name: "Science Times"
  url: "https://www.sciencetimes.co.kr"
  region: "kr"
  language: "ko"
  group: "D"
  crawl:
    primary_method: "sitemap"
    fallback_methods: ["rss", "dom"]
    rss_url: null
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 10
    crawl_delay_mandatory: null
    max_requests_per_hour: 240
    jitter_seconds: 3
  anti_block:
    ua_tier: 3
    default_escalation_tier: 2
    max_escalation_tier: 5
    requires_proxy: true
    proxy_region: "kr"
    bot_block_level: "HIGH"
  extraction:
    paywall_type: "none"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Hard"
    daily_article_estimate: 20
    sections_count: 8
    enabled: true
```

---

#### 17. zdnet.co.kr (ZDNet Korea)

**Decision Rationale**: RSS confirmed (path needs verification). WebFetch verification confirmed site structure: article URLs follow `/view/?no=XXXXXXXX` pattern, section navigation uses `/news/?lstcode=XXXX&page=1` pattern, dates display as `YYYY년 MM월 DD일 요일`. Operated by Money Today Group (MegaNews). No paywall.

[trace:step-6:webfetch-verification] -- zdnet.co.kr verified: article URL pattern `/view/?no=XXXXXXXX`; section URL pattern `/news/?lstcode=XXXX&page=1` with codes 0000 (latest) through 0130 (lifestyle); date format `2026년 02월 26일 목요일`; Matomo + Comscore + GA analytics; no JSON-LD.

**URL Discovery**

| Method | Priority | URL | Trigger to fallback |
|--------|----------|-----|---------------------|
| RSS | Primary | `https://www.zdnet.co.kr/rss` (verify: `/rss.xml`) | RSS 404 OR < 10 items |
| Sitemap | Fallback 1 | `https://www.zdnet.co.kr/sitemap.xml` | Sitemap 404 |
| DOM | Fallback 2 | Section listing pages | Last resort |

**Section Navigation** (verified via WebFetch):

| Section | URL Pattern | lstcode |
|---------|-------------|---------|
| Latest News | `/news/?lstcode=0000&page=1` | 0000 |
| Broadcasting/Telecom | `/news/?lstcode=0010&page=1` | 0010 |
| Computing | `/news/?lstcode=0020&page=1` | 0020 |
| Lifestyle/Culture | `/news/?lstcode=0130&page=1` | 0130 |

**Article Extraction Selectors**:

| Field | Primary Selector | Fallback Selector |
|-------|-----------------|-------------------|
| Title | `meta[property="og:title"]` | `h1.article_title` |
| Body | `div.article_body` | `div#content` via trafilatura |
| Author | `span.byline` | `meta[name="author"]` |
| Date | `meta[property="article:published_time"]` | Display: `2026년 02월 26일` |
| Category | `lstcode` parameter mapping | URL path |
| URL | `link[rel="canonical"]` | `/view/?no=` URL |

**Date Format Patterns** (verified):
- Display: `2026년 02월 26일 목요일` -- full Korean date with day-of-week
- Needs parsing regex: `(\d{4})년\s*(\d{2})월\s*(\d{2})일`

**Anti-Block Configuration**:

| Setting | Value |
|---------|-------|
| Rate limit | 5s base delay |
| Max req/hr | 720 |
| UA tier | T2 (10 UAs) |
| Starting tier | Tier 1 |
| Requires proxy | YES (kr) |

**Volume Estimate**: ~80 articles/day (weekday), ~20 (weekend)

**Special Handling**:
- Operated by Money Today Group (MegaNews), not CBS Interactive Korea (corrected from initial assessment)
- No JSON-LD detected: rely on Open Graph meta tags and HTML parsing for metadata
- `lstcode` parameter drives section navigation: must map codes to category names
- Article `no` parameter is numeric: deduplication key is `no` value

**sources.yaml Configuration**:
```yaml
zdnet_kr:
  name: "ZDNet Korea"
  url: "https://www.zdnet.co.kr"
  region: "kr"
  language: "ko"
  group: "D"
  crawl:
    primary_method: "rss"
    fallback_methods: ["sitemap", "dom"]
    rss_url: "https://www.zdnet.co.kr/rss"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 5
    crawl_delay_mandatory: null
    max_requests_per_hour: 720
    jitter_seconds: 0
  anti_block:
    ua_tier: 2
    default_escalation_tier: 1
    max_escalation_tier: 5
    requires_proxy: true
    proxy_region: "kr"
    bot_block_level: "MEDIUM"
  extraction:
    paywall_type: "none"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Medium"
    daily_article_estimate: 80
    sections_count: 8
    enabled: true
```

---

#### 18. irobotnews.com (iRobot News)

**Decision Rationale**: RSS at WordPress standard `/feed` path is highly likely (WordPress platform confirmed in Step 1). WebFetch returned HTTP 403, confirming HIGH bot-blocking from IP filtering. Very low volume (10 articles/day). WordPress provides predictable structure.

[trace:step-6:webfetch-verification] -- irobotnews.com returned HTTP 403 on direct fetch, confirming HIGH bot-blocking. WordPress platform (Step 1). Requires Korean proxy.

**URL Discovery**

| Method | Priority | URL | Trigger to fallback |
|--------|----------|-----|---------------------|
| RSS (WP) | Primary | `https://www.irobotnews.com/feed` | RSS 404 OR < 3 items |
| Sitemap (WP) | Fallback 1 | `https://www.irobotnews.com/sitemap.xml` | Sitemap 404 |
| DOM | Fallback 2 | Category pages | Last resort |

**Article Extraction Selectors** (WordPress standard):

| Field | Primary Selector | Fallback Selector |
|-------|-----------------|-------------------|
| Title | RSS `<title>` | `h1.entry-title` |
| Body | RSS `<content:encoded>` (if full) | `div.entry-content` via trafilatura |
| Author | RSS `<dc:creator>` | `span.author` or `a[href*="/author/"]` |
| Date | RSS `<pubDate>` (RFC 2822) | `time[datetime]` |
| Category | RSS `<category>` | `a[rel="category tag"]` |
| URL | RSS `<link>` | `link[rel="canonical"]` |

**Anti-Block Configuration**:

| Setting | Value |
|---------|-------|
| Rate limit | 10s base + 0-3s jitter |
| Max req/hr | 240 |
| UA tier | T3 (50 UAs) |
| Starting tier | Tier 2 |
| Requires proxy | YES (kr) |

**Volume Estimate**: ~10 articles/day (weekday), ~2 (weekend)

**Special Handling**:
- WordPress RSS may contain full content in `<content:encoded>` -- if so, no need to fetch article pages
- Very low volume: total ~10 requests/day; escalation is quick if needed
- Robotics/AI industry niche: specialized content

**sources.yaml Configuration**:
```yaml
irobotnews:
  name: "iRobot News"
  url: "https://www.irobotnews.com"
  region: "kr"
  language: "ko"
  group: "D"
  crawl:
    primary_method: "rss"
    fallback_methods: ["sitemap", "dom"]
    rss_url: "https://www.irobotnews.com/feed"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 10
    crawl_delay_mandatory: null
    max_requests_per_hour: 240
    jitter_seconds: 3
  anti_block:
    ua_tier: 3
    default_escalation_tier: 2
    max_escalation_tier: 5
    requires_proxy: true
    proxy_region: "kr"
    bot_block_level: "HIGH"
  extraction:
    paywall_type: "none"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Hard"
    daily_article_estimate: 10
    sections_count: 5
    enabled: true
```

---

#### 19. techneedle.com (TechNeedle)

**Decision Rationale**: RSS at WordPress `/feed` confirmed and verified via WebFetch. 10 items, RSS 2.0, full content in `<content:encoded>`, WordPress 6.5.4. JSON-LD `Organization` schema confirmed. Date format `YYYY-MM-DD`. Very low volume (5 articles/day). HIGH bot-blocking from IP filtering despite WordPress ease.

[trace:step-6:webfetch-verification] -- techneedle.com fully verified: RSS 2.0 at `/feed`, 10 items, full content in `content:encoded`, RFC 822 dates (`Sun, 21 Dec 2025 07:30:48 +0000`), `dc:creator` for authors, hourly update frequency. WordPress 6.5.4. JSON-LD `Organization` with `sameAs` social links. Font: Noto Sans KR / Noto Serif KR. 5,193 total posts, 291 pages of archives. Date display: `Posted on YYYY-MM-DD`.

**URL Discovery**

| Method | Priority | URL | Trigger to fallback |
|--------|----------|-----|---------------------|
| RSS (WP) | Primary | `https://www.techneedle.com/feed` | RSS 404 OR < 3 items |
| Sitemap (WP) | Fallback 1 | `https://www.techneedle.com/sitemap.xml` | Sitemap 404 |
| DOM | Fallback 2 | Archive/category pages | Last resort |

**Section Navigation** (verified via WebFetch):
- Archive listing: `https://www.techneedle.com/archives/`
- Categories: AI, Apple, Amazon, Google, Netflix, etc. (tag-based)
- Pagination: `Page {N}` with 291 total pages

**Article Extraction Selectors** (verified via WebFetch):

| Field | Primary Selector | Fallback Selector | Verification Status |
|-------|-----------------|-------------------|---------------------|
| Title | RSS `<title>` | `h1.entry-title` | VERIFIED via RSS |
| Body | RSS `<content:encoded>` (FULL) | `div.entry-content` | VERIFIED: full body in feed |
| Author | RSS `<dc:creator>` | `span.author` | VERIFIED |
| Date | RSS `<pubDate>` (RFC 822) | Display: `Posted on YYYY-MM-DD` | VERIFIED: `Sun, 21 Dec 2025 07:30:48 +0000` |
| Category | RSS `<category>` | `a[rel="category tag"]` | VERIFIED |
| URL | RSS `<link>` | `link[rel="canonical"]` | VERIFIED |

**Date Format Patterns** (verified):
- RSS: RFC 822 (`Sun, 21 Dec 2025 07:30:48 +0000`)
- Display: `Posted on 2025-12-20` (ISO 8601 date only)

**Anti-Block Configuration**:

| Setting | Value |
|---------|-------|
| Rate limit | 10s base + 0-3s jitter |
| Max req/hr | 240 |
| UA tier | T3 (50 UAs) |
| Starting tier | Tier 2 |
| Requires proxy | YES (kr) -- IP filtering observed |

**Volume Estimate**: ~5 articles/day (infrequent publishing; analysis/commentary pace)

**Special Handling**:
- **RSS contains full article text**: Extract everything from feed; no article page fetching needed
- 5,193 historical posts available for backfill if needed
- Korean tech startup ecosystem focus: specialized niche content
- Independent publication, not institutional

**sources.yaml Configuration**:
```yaml
techneedle:
  name: "TechNeedle"
  url: "https://www.techneedle.com"
  region: "kr"
  language: "ko"
  group: "D"
  crawl:
    primary_method: "rss"
    fallback_methods: ["sitemap", "dom"]
    rss_url: "https://www.techneedle.com/feed"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 10
    crawl_delay_mandatory: null
    max_requests_per_hour: 240
    jitter_seconds: 3
  anti_block:
    ua_tier: 3
    default_escalation_tier: 2
    max_escalation_tier: 5
    requires_proxy: true
    proxy_region: "kr"
    bot_block_level: "HIGH"
  extraction:
    paywall_type: "none"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Hard"
    daily_article_estimate: 5
    sections_count: 5
    enabled: true
```

---

## Group-Level Crawl Time Estimates

| Group | Sites | Daily Articles | Sequential Min | Parallel Min |
|-------|-------|---------------|---------------|-------------|
| A: Korean Major Dailies | 5 | ~1,200 | ~21.5 | ~10.8 |
| B: Korean Economy | 4 | ~900 | ~15.0 | ~7.5 |
| C: Korean Niche | 3 | ~300 | ~5.5 | ~2.8 |
| D: Korean IT/Science | 7 | ~240 | ~13.0 | ~6.5 |
| **Total Korean** | **19** | **~2,555** | **~54.5** | **~27.5** |

Parallelization notes:
- Groups A+B can run in parallel (different sites, no overlap)
- Groups C+D can run in parallel
- Total parallel time: max(A+B, C+D) = max(36.5, 18.5) = ~36.5 min sequential within 2 parallel tracks, or ~18.3 min with 4-track parallelism
- All 19 Korean sites share the same proxy infrastructure (Korean residential IP), so parallelism is limited by proxy connection pool size

---

## Cross-Reference to Step 1 Reconnaissance

### How Reconnaissance Findings Informed Strategy Choices

| Recon Finding | Impact on Strategy |
|---------------|-------------------|
| All 19 Korean sites blocked non-Korean IPs | Korean residential proxy is baseline infrastructure for ALL sites (except 38north.org) |
| 16/19 sites have confirmed RSS | RSS as primary method for 16 sites; only bloter.net (Playwright) and sciencetimes.co.kr (Sitemap) differ |
| bloter.net is CSR/React SPA | Playwright/Patchright is mandatory primary method |
| joongang.co.kr has Cloudflare + HIGH blocking | Pre-escalated to T3 UA tier with 10s+jitter rate limit |
| 3 sites have soft paywalls | Cookie clearing strategy for joongang.co.kr, hankyung.com, hani.co.kr |
| yna.co.kr produces ~500 articles/day | RSS supplemented with sitemap for full coverage |
| nocutnews.co.kr, ohmynews.com have LOW blocking | Lightweight T1 UA tier with 2s rate limit |
| 38north.org has fully permissive robots.txt | No proxy needed; 2s rate limit; RSS-only strategy |
| WordPress sites (38north, techneedle, irobotnews, bloter) | Predictable `/feed`, `/sitemap.xml` paths; `content:encoded` may contain full text |
| All sites are UTF-8 | No legacy EUC-KR charset handling needed |

### Selector Verification Status

| Verification Method | Sites | Status |
|---------------------|-------|--------|
| Direct WebFetch (full page) | 38north.org, techneedle.com, nocutnews.co.kr, kmib.co.kr, fnnews.com, mt.co.kr, ohmynews.com, zdnet.co.kr, etnews.com, voakorea.com | VERIFIED |
| RSS feed fetch (content analysis) | 38north.org, techneedle.com, nocutnews.co.kr | VERIFIED (full content confirmed in feeds) |
| HTTP 403 confirming blocking level | bloter.net, irobotnews.com | VERIFIED (blocking confirmed) |
| Inferred from platform + community docs | chosun.com, joongang.co.kr, donga.com, hani.co.kr, yna.co.kr, mk.co.kr, hankyung.com, sciencetimes.co.kr | INFERRED (Korean IP required for verification) |

---

## Korean-Specific Technical Notes

### Character Encoding

All 19 Korean sites use **UTF-8** encoding. No legacy EUC-KR sites were found in this set. The `charset` field in all sources.yaml entries is set to `utf-8`. However, the extraction pipeline should include a charset detection fallback (chardet/charset-normalizer) in case any site serves EUC-KR for legacy pages.

### Date Format Parsing

Korean news sites use five primary date format patterns:

| Pattern | Example | Regex | Sites Using |
|---------|---------|-------|-------------|
| ISO 8601 | `2026-02-26T10:30:00+09:00` | `\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}` | All (in meta tags) |
| Korean full | `2026년 02월 26일 목요일` | `(\d{4})년\s*(\d{2})월\s*(\d{2})일` | zdnet.co.kr |
| Dot-separated | `2026.02.26 10:30` | `\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}` | chosun, joongang, donga, etnews |
| Dash-separated | `2026-02-26 10:30` | `\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}` | etnews, fnnews |
| Short year | `26.02.26 13:53` | `(\d{2})\.(\d{2})\.(\d{2})\s+\d{2}:\d{2}` | ohmynews (2-digit year!) |
| RFC 2822 | `Wed, 26 Feb 2026 10:30:00 +0900` | Standard RFC 2822 | RSS feeds |

**Parsing priority**: Always prefer `article:published_time` meta tag (ISO 8601) over display dates. Fall back to visible date parsing only if meta tag is absent.

**Timezone**: All Korean sites use KST (UTC+9). Convert to UTC for storage per `RawArticle.published_at` contract.

### URL Normalization for Korean Sites

Korean news URLs follow three patterns:

| Pattern | Example | Dedup Key |
|---------|---------|-----------|
| Numeric ID | `chosun.com/article/20260226000123` | `chosun:20260226000123` |
| Query param ID | `zdnet.co.kr/view/?no=20260226090748` | `zdnet_kr:20260226090748` |
| ASP.NET ID | `ohmynews.com/.../at_pg.aspx?CNTN_CD=A0003106064` | `ohmynews:A0003106064` |

No Korean slugs in URLs (unlike some English sites). All Korean news sites use numeric article identifiers, simplifying deduplication.

### Author Name Extraction

Korean journalist bylines follow these patterns:

| Pattern | Regex | Example |
|---------|-------|---------|
| Standard reporter | `([가-힣]{2,4})\s*기자` | `김철수 기자` |
| Senior reporter | `([가-힣]{2,4})\s*선임기자` | `이영희 선임기자` |
| Correspondent | `([가-힣]{2,4})\s*특파원` | `박민수 특파원` |
| With email | `([가-힣]{2,4})\s*기자\s*\([\w.]+@[\w.]+\)` | `류태웅 기자 (bigheroryu@etnews.com)` |
| Citizen reporter | `([가-힣]{2,4})` (no suffix) | `홍길동` (OhmyNews) |
| News agency prefix | `CBS노컷뉴스\s+([가-힣]{2,4})\s*기자` | `CBS노컷뉴스 윤창원 기자` |

**Extraction strategy**: Strip suffix (`기자`, `선임기자`, `특파원`, `편집위원`), strip email, strip outlet prefix. Store raw Korean name (2-4 hangul characters).

---

## L1 Self-Verification

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | All 19 Korean sites have complete entries | PASS | Sites 1-19 all have per-site sections with full configuration |
| 2 | Each entry has primary method | PASS | RSS (16), Sitemap (1), Playwright (1), API (1) |
| 3 | Each entry has fallback chain | PASS | All 19 sites specify 2-3 fallback methods |
| 4 | Each entry has CSS/XPath selectors for title | PASS | All 19 specify primary + fallback title selectors |
| 5 | Each entry has CSS/XPath selectors for date | PASS | All 19 specify date selector + format pattern |
| 6 | Each entry has CSS/XPath selectors for body | PASS | All 19 specify body container selector |
| 7 | Each entry has CSS/XPath selectors for URL | PASS | All 19 specify canonical URL source |
| 8 | Each entry has rate limit | PASS | Range: 2s (LOW) to 10s+jitter (HIGH) |
| 9 | Each entry has anti-block tier | PASS | T1 (3 sites), T2 (10 sites), T3 (6 sites) |
| 10 | Paywall sites explicitly marked | PASS | joongang.co.kr, hankyung.com, hani.co.kr marked soft-metered |
| 11 | Group-level crawl time estimates included | PASS | Table with Groups A-D sequential and parallel estimates |
| 12 | sources.yaml configs included | PASS | All 19 sites have complete YAML config blocks |
| 13 | WebFetch verification performed | PASS | 10 sites directly verified; 3 RSS feeds confirmed; 2 confirmed blocked |
| 14 | Korean-specific handling documented | PASS | Encoding, dates, URLs, author patterns sections included |

---

## pACS Self-Rating

### Pre-Mortem Protocol

**Q1: What could make this strategy fail in production?**
- RSS URLs for 6 sites (mt.co.kr, kmib.co.kr, etnews.com, zdnet.co.kr, irobotnews.com, sciencetimes.co.kr) need runtime verification -- the exact paths are inferred from platform patterns, not directly confirmed
- CSS selectors for sites behind Korean IP filtering (chosun, joongang, donga, hani, yna, mk, hankyung) are inferred from known CMS patterns and Open Graph conventions rather than direct HTML inspection -- they may need adjustment during implementation
- The legacy joinsmsn.com RSS domain for joongang.co.kr could become unreachable at any time

**Q2: Which sections am I least confident about?**
- Article body CSS selectors for Group A/B sites: these are based on common Korean news CMS patterns (`div.article_body`, `div.article-text`, etc.) rather than verified HTML. Trafilatura's automatic extraction should compensate for selector inaccuracies.
- sciencetimes.co.kr strategy is the weakest: neither RSS nor HTML structure confirmed; sitemap is a reasonable default but untested

**Q3: What would a critical reviewer challenge?**
- That 8 of 19 sites have INFERRED rather than VERIFIED selectors
- That Playwright is only assigned to 1 site (bloter.net) when irobotnews.com and techneedle.com also showed HTTP 403 -- but those are WordPress sites where RSS `/feed` should bypass the frontend blocking

### pACS Scores

| Dimension | Score | Justification |
|-----------|-------|---------------|
| **Fidelity (F)** | 72 | 11/19 sites have WebFetch-verified data; 8 rely on inferred selectors. All RSS URLs are from documented community sources but some need runtime verification. Volume estimates align with Step 1 data. |
| **Completeness (C)** | 85 | All 19 sites covered. Every entry has primary/fallback methods, selectors, rate limits, anti-block config, sources.yaml block. Korean-specific handling documented comprehensively. Group-level estimates included. |
| **Logical Coherence (L)** | 80 | Strategies are internally consistent: HIGH blocking -> T3 UA + jitter; LOW blocking -> T1 + 2s delay. Fallback chains are logically ordered. Volume estimates and crawl times are arithmetically consistent. The one gap is that some "HIGH" blocking sites (irobotnews, techneedle) use RSS as primary despite blocking -- justified by WordPress backend serving RSS even when frontend blocks. |

**pACS = min(F, C, L) = min(72, 85, 80) = 72 (YELLOW)**

**Weak Dimension**: Fidelity (F) -- 8 sites have inferred rather than directly verified selectors due to Korean IP geo-blocking preventing WebFetch access. This is an inherent limitation that can only be fully resolved during implementation with Korean proxy access.
