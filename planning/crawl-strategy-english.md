# English News Site Crawling Strategies (Group E -- 12 Sites)

**Step**: 6/20 -- Crawl Strategy Design (English Group)
**Agent**: @crawl-strategist-en
**Date**: 2026-02-26
**Input Sources**: `planning/team-input/group-english.json`, `research/site-reconnaissance.md` (Step 1), `research/crawling-feasibility.md` (Step 3), `planning/architecture-blueprint.md` (Step 5)

---

## 1. Executive Summary

| Metric | Value |
|--------|-------|
| Total sites | 12 |
| Paywall breakdown | None: 4, Soft-metered: 3, Hard: 4, None (CSR): 1 |
| Primary method breakdown | RSS: 5, Sitemap: 4, API: 1, Playwright: 1, DOM: 1 |
| Estimated daily articles | ~1,920 |
| Estimated group crawl time | ~49.5 min (sequential) / ~16.5 min (parallel within group) |
| Hard paywall (title-only) | 4 sites: nytimes.com, ft.com, wsj.com, bloomberg.com |
| Requires Playwright | 1 site: buzzfeed.com |
| No proxy needed | All 12 (English sites accessible from general IPs) |
| Languages | 11 English, 1 Spanish (afmedios.com) |

### Paywall Classification

[trace:step-1:difficulty-classification-matrix] -- Tier classifications from Step 1 reconnaissance.

| Paywall Type | Sites | Strategy |
|-------------|-------|----------|
| **None** | voakorea.com, huffpost.com, edition.cnn.com, afmedios.com | Full article extraction |
| **None (CSR)** | buzzfeed.com | Full extraction via Playwright |
| **Soft-metered** | marketwatch.com, latimes.com, nationalpost.com | Cookie reset + full extraction |
| **Hard** | nytimes.com, ft.com, wsj.com, bloomberg.com | Title+metadata only |

### Fundus/Trafilatura Compatibility Notes

Both Fundus and Trafilatura are validated as GO for Python 3.12 (Step 2). Compatibility per site:

| Site | Fundus Publisher | Trafilatura | Recommended |
|------|-----------------|-------------|-------------|
| nytimes.com | NYT publisher class | Good (SSR) | Trafilatura (paywall blocks body anyway) |
| wsj.com | No publisher class | Good (SSR) | Trafilatura (title-only extraction) |
| ft.com | No publisher class | Good (SSR) | Trafilatura (title-only extraction) |
| bloomberg.com | No publisher class | Limited (403) | Custom selectors (403 blocks both) |
| edition.cnn.com | CNN publisher class | Good (SSR) | Fundus preferred (has CNN publisher) |
| huffpost.com | HuffPost publisher class | Good (SSR) | Fundus preferred (has HuffPost publisher) |
| latimes.com | No publisher class | Good (SSR) | Trafilatura (GrapheneCMS compatible) |
| marketwatch.com | No publisher class | Good (SSR) | Trafilatura (Dow Jones CMS) |
| nationalpost.com | No publisher class | Good (WordPress) | Trafilatura (WordPress SSR) |
| buzzfeed.com | BuzzFeed publisher class | Poor (CSR) | Fundus+Playwright (JS rendering needed) |
| voakorea.com | No publisher class | Good (SSR) | Trafilatura (VOA CMS) |
| afmedios.com | No publisher class | Good (WordPress) | Trafilatura (WordPress SSR) |

---

## 2. Strategy Matrix (All 12 Sites)

[trace:step-3:strategy-matrix] -- Inherits primary methods and rate limits from Step 3 feasibility analysis.
[trace:step-5:sources-yaml-schema] -- Output aligns with sources.yaml schema from Step 5 architecture.

| # | Site | Primary | Fallback | Rate Limit | UA Tier | Paywall | Daily Est. | Crawl Min | Risk | Difficulty |
|---|------|---------|----------|------------|---------|---------|-----------|-----------|------|------------|
| 20 | marketwatch.com | RSS | Sitemap+DOM | 10s+3s jitter | T3 (50) | soft-metered | ~200 | 5.0 | HIGH | Hard |
| 21 | voakorea.com | API (RSS) | Sitemap+DOM | 2s | T1 (1) | none | ~50 | 1.5 | LOW | Easy |
| 22 | huffpost.com | Sitemap | DOM+Playwright | 5s | T2 (10) | none | ~100 | 3.0 | HIGH | Medium |
| 23 | nytimes.com | Sitemap | DOM (title-only) | 10s+3s jitter | T3 (50) | hard | ~300 | 5.0 | EXTREME | Extreme |
| 24 | ft.com | Sitemap | DOM (title-only) | 10s+3s jitter | T3 (50) | hard | ~150 | 4.0 | EXTREME | Extreme |
| 25 | wsj.com | Sitemap | DOM (title-only) | 10s+3s jitter | T3 (50) | hard | ~200 | 4.0 | EXTREME | Extreme |
| 26 | latimes.com | RSS | Sitemap+DOM | 5s | T2 (10) | soft-metered | ~150 | 3.5 | HIGH | Medium |
| 27 | buzzfeed.com | Playwright | Sitemap+DOM | 10s+3s jitter | T3 (50) | none | ~50 | 6.0 | HIGH | Hard |
| 28 | nationalpost.com | RSS (WP) | Sitemap+DOM | 10s+3s jitter | T3 (50) | soft-metered | ~100 | 3.0 | HIGH | Hard |
| 29 | edition.cnn.com | Sitemap | DOM+RSS | 5s | T2 (10) | none | ~500 | 6.0 | HIGH | Medium |
| 30 | bloomberg.com | Sitemap | DOM (title-only) | 10s+3s jitter | T3 (50) | hard | ~200 | 4.0 | EXTREME | Extreme |
| 31 | afmedios.com | RSS | Sitemap (WP) | 2s | T1 (1) | none | ~20 | 0.5 | LOW | Easy |

---

## 3. Per-Site Detailed Strategies

### 3.1 marketwatch.com (MarketWatch)

**Cross-Reference**: Step 1 Site #20 -- Hard tier, soft-metered paywall, Dow Jones property
**Decision Rationale**: RSS-primary because MarketWatch publishes RSS feeds with article summaries; Dow Jones CMS renders SSR content accessible via httpx without JS rendering.

#### sources.yaml Configuration

```yaml
marketwatch:
  name: "MarketWatch"
  url: "https://www.marketwatch.com"
  region: "us"
  language: "en"
  group: "E"
  crawl:
    primary_method: "rss"
    fallback_methods:
      - "sitemap"
      - "dom"
    rss_url: "https://www.marketwatch.com/rss"
    rss_sections:
      - url: "https://feeds.marketwatch.com/marketwatch/topstories"
        section: "top_stories"
      - url: "https://feeds.marketwatch.com/marketwatch/marketpulse"
        section: "market_pulse"
      - url: "https://feeds.marketwatch.com/marketwatch/bulletins"
        section: "bulletins"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 10
    crawl_delay_mandatory: null
    max_requests_per_hour: 240
    jitter_seconds: 3
  anti_block:
    ua_tier: 3
    default_escalation_tier: 2
    max_escalation_tier: 5
    requires_proxy: false
    proxy_region: null
    bot_block_level: "HIGH"
  extraction:
    paywall_type: "soft-metered"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Hard"
    daily_article_estimate: 200
    sections_count: 12
    enabled: true
```

#### URL Discovery

- **Primary**: RSS feeds at `feeds.marketwatch.com/marketwatch/*`. Parse for article URLs using `feedparser`. Expected fields: `title`, `link`, `published`, `summary`.
- **Fallback chain**: Sitemap (`/sitemap.xml`) for URL discovery -> DOM parsing of section pages (`/latest-news`, `/economy-politics`, `/markets`).
- **Fallback trigger**: RSS returns < 10 articles OR HTTP 403/429 for > 30 minutes.

#### Article Extraction Selectors

```yaml
selectors:
  # Article list page (section pages)
  list:
    article_links: "h3.article__headline a[href]"
    pagination: null  # Infinite scroll; use RSS/sitemap instead
    section_urls:
      - "/latest-news"
      - "/economy-politics"
      - "/personal-finance"
      - "/markets"

  # Article detail page
  detail:
    title:
      primary: "h1.article__headline"
      fallback: "meta[property='og:title']"
    body:
      primary: "div.article__body"
      fallback: "div[class*='article-wrap'] div[class*='body']"
      strip:
        - "div.article__inset"           # Inline ads
        - "div[class*='newsletter']"     # Newsletter signup
        - "aside"                        # Sidebar widgets
        - "div[class*='related']"        # Related articles
    author:
      primary: "span.article__byline a"
      fallback: "meta[name='author']"
    date:
      primary: "time[datetime]"
      fallback: "meta[property='article:published_time']"
      format: "ISO 8601"
    category:
      primary: "a[class*='breadcrumb'] span"
      fallback: "meta[property='article:section']"
    canonical_url: "link[rel='canonical']"

  # Exclusion patterns
  exclude:
    - "div[class*='ad-']"
    - "div[id*='sponsored']"
    - "section.comment"
    - "div[class*='social-share']"
    - "div[class*='trendingNow']"
```

#### Anti-Bot Handling

- **CDN/WAF**: Cloudflare Enterprise (Dow Jones property)
- **Bot fingerprinting**: Active -- Dow Jones employs TLS fingerprinting + JS challenge pages
- **UA strategy**: Tier 3 pool (50 UAs), rotate per request. Avoid all AI-identifying strings. Required headers:
  ```
  Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
  Accept-Language: en-US,en;q=0.9
  Accept-Encoding: gzip, deflate, br
  Connection: keep-alive
  ```
- **Escalation plan**: Tier 2 (session management) -> Tier 3 (Playwright if JS challenge) -> Tier 4 (Patchright stealth) -> Tier 5 (residential proxy)
- **Escalation triggers**: 3+ consecutive HTTP 429/403 -> escalate. Cloudflare JS challenge (503 with challenge HTML) -> jump to Tier 3.

#### Paywall Handling

- **Type**: Soft-metered (Dow Jones subscriber pool shared with WSJ)
- **Strategy**: Cookie reset between crawl sessions. Clear `djcs_*` and `usr_*` cookies. MarketWatch allows several free articles per session from fresh IP/cookie state.
- **Fallback**: If metered limit hit, accept title + summary from RSS (RSS `description` field contains article summary).
- **Google AMP**: `https://www.google.com/amp/s/www.marketwatch.com/amp/...` -- may expose full article for some stories.

#### Volume & Timing

- **Daily estimate**: ~200 articles/day
- **Peak publishing**: 09:00-17:00 EST (market hours), with pre-market alerts starting 06:00 EST
- **Crawl time**: 200 articles x (10s delay + 2s load + 0.5s parse) x 1.1 overhead = ~5.0 minutes
- **Content types**: Market reports, financial news, opinion columns, personal finance

---

### 3.2 voakorea.com (VOA Korean Service)

**Cross-Reference**: Step 1 Site #21 -- Easy tier, no paywall, US government media
**Decision Rationale**: API-style RSS feeds confirmed via Step 1 direct probe. VOA uses non-standard API paths for feeds but serves standard content. Government media is deliberately accessible.

#### sources.yaml Configuration

```yaml
voakorea:
  name: "VOA Korea"
  url: "https://www.voakorea.com"
  region: "us"
  language: "ko"
  group: "E"
  crawl:
    primary_method: "api"
    fallback_methods:
      - "sitemap"
      - "dom"
    rss_url: null  # API-style feeds, not standard RSS
    api_feeds_page: "https://www.voakorea.com/rssfeeds"
    sitemap_url: "/sitemap.xml"
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
    daily_article_estimate: 50
    sections_count: 6
    enabled: true
```

#### URL Discovery

- **Primary**: API-style RSS feeds discovered from `/rssfeeds` page. Feed path pattern: `/api/z[encoded-id]-vomx-tpe[id]`. 17 category feeds available. Parse with `feedparser` (handles non-standard RSS).
- **Feed discovery**: At startup, scrape `/rssfeeds` page to extract all feed URLs dynamically (feed endpoints may change). Cache discovered URLs for subsequent runs.
- **Fallback chain**: Sitemap (`/sitemap.xml`) -> DOM parsing of section pages.
- **Fallback trigger**: All API feeds return empty or format changes.

#### Article Extraction Selectors

```yaml
selectors:
  detail:
    title:
      primary: "h1.page-header__title"
      fallback: "meta[property='og:title']"
    body:
      primary: "div.body-container div.wsw"  # VOA standard article wrapper
      fallback: "div[class*='article-body']"
      strip:
        - "div[class*='embed']"
        - "figure"                           # Image captions
        - "div[class*='related']"
    author:
      primary: "div.authors a span"
      fallback: "meta[name='author']"
    date:
      primary: "time[datetime]"
      fallback: "meta[property='article:published_time']"
      format: "ISO 8601"
    category:
      primary: "nav.breadcrumb li:last-child a"
      fallback: "meta[property='article:section']"
    canonical_url: "link[rel='canonical']"

  # JSON-LD extraction (confirmed present in Step 1 probe)
  json_ld:
    type: "NewsArticle"
    fields:
      title: "headline"
      date: "datePublished"
      author: "author.name"
      accessible: "isAccessibleForFree"  # Always "true" for VOA

  exclude:
    - "div[class*='share']"
    - "div[class*='comment']"
    - "aside"
```

#### Anti-Bot Handling

- **CDN/WAF**: Standard government infrastructure, no aggressive blocking
- **UA strategy**: Tier 1 -- single UA, rotate weekly. VOA is US government media with `isAccessibleForFree: true` in schema.org markup.
- **robots.txt**: Blocks AhrefsBot fully; disallows deep archive/media paths. General crawlers allowed.
- **No escalation expected**: Easy site. Maximum Tier 3 if unexpected blocking occurs.

#### Paywall Handling

- **Type**: None. US government-funded broadcaster; all content freely accessible.
- **Schema.org confirmation**: `isAccessibleForFree: true` in JSON-LD.

#### Volume & Timing

- **Daily estimate**: ~50 articles/day
- **Peak publishing**: Follows US news cycle; updates throughout US business hours
- **Crawl time**: 50 x (2s + 2s + 0.5s) x 1.1 = ~1.5 minutes
- **Content types**: Korean-language news articles, some bilingual English content
- **Note**: Despite `.co.kr` domain, VOA Korea is a US government service accessible globally without Korean proxy.

---

### 3.3 huffpost.com (HuffPost)

**Cross-Reference**: Step 1 Site #22 -- Medium tier, no paywall, blocks 25+ AI bots
**Decision Rationale**: Sitemap-primary because HuffPost has no confirmed RSS endpoint but has 5 well-structured sitemaps. Content is free (ad-supported) but AI bot blocking is aggressive, requiring careful UA management.

#### sources.yaml Configuration

```yaml
huffpost:
  name: "HuffPost"
  url: "https://www.huffpost.com"
  region: "us"
  language: "en"
  group: "E"
  crawl:
    primary_method: "sitemap"
    fallback_methods:
      - "dom"
      - "playwright"
    rss_url: null  # No confirmed RSS endpoint
    sitemap_urls:
      - "https://www.huffpost.com/static-assets/isolated/huffpostsitemapgeneratorjob-prod-public/us/sitemaps/sitemap-v1.xml"
      - "https://www.huffpost.com/static-assets/isolated/huffpostsitemapgeneratorjob-prod-public/us/sitemaps/sitemap-google-news.xml"
      - "https://www.huffpost.com/static-assets/isolated/huffpostsitemapgeneratorjob-prod-public/us/sitemaps/sections.xml"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 5
    crawl_delay_mandatory: null
    max_requests_per_hour: 720
    jitter_seconds: 0
  anti_block:
    ua_tier: 2
    default_escalation_tier: 1
    max_escalation_tier: 5
    requires_proxy: false
    proxy_region: null
    bot_block_level: "HIGH"
  extraction:
    paywall_type: "none"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Medium"
    daily_article_estimate: 100
    sections_count: 15
    enabled: true
```

#### URL Discovery

- **Primary**: 5 sitemaps confirmed via robots.txt probe (Step 1). Use `sitemap-google-news.xml` for freshest articles (Google News sitemaps include publication date and keywords).
- **Sitemap URLs** (verified from robots.txt):
  1. `sitemap-v1.xml` -- General articles
  2. `sitemap-google-news.xml` -- News articles with rich metadata
  3. `sitemap-google-video.xml` -- Video content
  4. `sections.xml` -- Section listing
  5. `sitemap-top-sections.xml` -- Top sections
- **Fallback chain**: DOM parsing of section pages -> Playwright (if DOM returns empty due to JS rendering).
- **Fallback trigger**: All sitemaps return 403 OR < 10 new URLs per day.

#### Article Extraction Selectors

```yaml
selectors:
  detail:
    title:
      primary: "h1[data-testid='headline']"
      fallback_1: "h1.headline__title"
      fallback_2: "meta[property='og:title']"
    body:
      primary: "div[data-testid='article-body']"
      fallback_1: "div.entry__text"
      fallback_2: "section.entry-body"
      strip:
        - "div[class*='newsletter']"
        - "div[class*='ad-']"
        - "div[class*='related']"
        - "div[data-testid*='embed']"
        - "aside"
        - "div[class*='social']"
    author:
      primary: "a[data-testid='byline-author'] span"
      fallback: "meta[name='author']"
    date:
      primary: "time[datetime]"
      fallback: "meta[property='article:published_time']"
      format: "ISO 8601"
    category:
      primary: "a[data-testid='breadcrumb-item'] span"
      fallback: "meta[property='article:section']"
    canonical_url: "link[rel='canonical']"

  # URL pattern for article pages
  url_pattern: "/entry/*_n_*"

  exclude:
    - "div[class*='connatix']"           # Video embeds
    - "div[class*='taboola']"            # Recommendation widget
    - "div[data-testid='inline-module']" # Inline ad modules
    - "div[class*='newsletter-signup']"
    - "section[class*='comments']"
```

#### Anti-Bot Handling

- **CDN/WAF**: Not Cloudflare. HuffPost uses custom bot filtering (AOL/Verizon legacy infrastructure).
- **Explicitly blocked bots** (from robots.txt, confirmed Step 1): ClaudeBot, Claude-Web, Claude-SearchBot, Claude-User, anthropic-ai, GPTBot, ChatGPT-User, PerplexityBot, Amazonbot, and 20+ others.
- **UA strategy**: Tier 2 pool (10 UAs). CRITICAL: Must never use any AI-identifying UA string. Standard Chrome/Firefox UAs only:
  ```
  Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36
  Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36
  ```
- **robots.txt compliance**: Respect all Disallow paths (/member, /search, /api, /embed). Only fetch article pages matching `/entry/*` pattern.
- **Note**: `huffingtonpost.com` redirects 301 to `huffpost.com`. Use `huffpost.com` as canonical domain.

#### Paywall Handling

- **Type**: None. HuffPost is fully ad-supported with no paywall.
- **Content access**: All article bodies are freely accessible once past bot filtering.

#### Volume & Timing

- **Daily estimate**: ~100 articles/day
- **Peak publishing**: 08:00-22:00 EST
- **Crawl time**: 100 x (5s + 2s + 0.5s) x 1.1 = ~3.0 minutes
- **Content types**: News articles, opinion/commentary, lifestyle, politics

---

### 3.4 nytimes.com (The New York Times) -- EXTREME

**Cross-Reference**: Step 1 Site #23 -- Extreme tier, hard paywall, Cloudflare + proprietary protection
**Decision Rationale**: Sitemap-primary for URL discovery; title+metadata-only extraction. Full body extraction is infeasible without subscription. NYT is one of the most aggressively protected news sites globally. The dual-pass analysis strategy (PRD) supports meaningful analysis from titles alone.

#### sources.yaml Configuration

```yaml
nytimes:
  name: "The New York Times"
  url: "https://www.nytimes.com"
  region: "us"
  language: "en"
  group: "E"
  crawl:
    primary_method: "sitemap"
    fallback_methods:
      - "dom"
    rss_url: null  # RSS discontinued for general users ~2020
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 10
    crawl_delay_mandatory: null
    max_requests_per_hour: 240
    jitter_seconds: 3
  anti_block:
    ua_tier: 3
    default_escalation_tier: 3
    max_escalation_tier: 6
    requires_proxy: false
    proxy_region: null
    bot_block_level: "HIGH"
  extraction:
    paywall_type: "hard"
    title_only: true
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Extreme"
    daily_article_estimate: 300
    sections_count: 20
    enabled: true
```

#### URL Discovery

- **Primary**: Sitemap (`/sitemap.xml`). NYT sitemaps are structured by date and section, providing article URLs with `lastmod` timestamps.
- **Sitemap structure**: Index sitemap references daily sub-sitemaps (e.g., `/sitemaps/YYYY/MM/DD/sitemap.xml`). Parse index first, then fetch only today's sub-sitemap for new articles.
- **Fallback**: DOM parsing of section landing pages (`/section/world`, `/section/us`, `/section/politics`, `/section/business`) for headline + URL extraction.
- **Fallback trigger**: Main sitemap returns 403 (aggressive blocking).

#### Article Extraction Selectors (Title-Only Mode)

```yaml
selectors:
  # Title-only extraction (hard paywall blocks body)
  detail:
    title:
      primary: "h1[data-testid='headline']"
      fallback_1: "h1.e1h9p8200"  # NYT uses CSS module hashes; fragile
      fallback_2: "meta[property='og:title']"
      fallback_3: "title"  # Last resort: page <title> tag
    body:
      note: "BLOCKED by hard paywall. Empty string in output."
      primary: null
      first_paragraph_attempt: "p.css-at9mc1:first-of-type"  # First visible paragraph before paywall gate
    author:
      primary: "span[data-testid='byline'] a"
      fallback_1: "meta[name='byl']"  # NYT-specific meta tag
      fallback_2: "meta[property='article:author']"
    date:
      primary: "time[datetime]"
      fallback_1: "meta[property='article:published_time']"
      fallback_2: "meta[name='pdate']"  # NYT-specific
      format: "ISO 8601"
    category:
      primary: "meta[property='article:section']"
      fallback: "nav[data-testid='breadcrumbs'] li:last-child a"
    canonical_url: "link[rel='canonical']"

  # Section page headline extraction (fallback URL discovery)
  section_page:
    article_links: "section[data-testid='block-ModuleHeadline'] a[href*='/202']"
    headline_text: "h3"

  # Sitemap metadata (often sufficient without page fetch)
  sitemap_fields:
    url: "loc"
    lastmod: "lastmod"
    news_title: "news:title"
    news_publication_date: "news:publication_date"
    news_keywords: "news:keywords"

  exclude: []  # Minimal exclusion needed for title-only
```

#### Anti-Bot Handling

- **CDN/WAF**: Cloudflare + proprietary NYT bot detection (PerimeterX/HUMAN Security suspected)
- **Defenses observed**:
  - JavaScript challenge pages (Cloudflare managed challenge)
  - TLS fingerprinting (rejects non-browser TLS stacks)
  - Cookie-based session tracking for meter enforcement
  - IP reputation scoring
  - AI bot blocking in robots.txt (ClaudeBot, GPTBot explicitly listed)
- **UA strategy**: Tier 3 pool (50 UAs), rotate per request. Browser-realistic TLS fingerprints required.
- **Escalation plan**: Start at Tier 3 (Playwright) for consistent access. Tier 4 (Patchright CDP stealth) if Playwright blocked. Tier 5 (residential proxy) for IP-level bans. Tier 6 (Claude Code) for novel blocking.
- **SSR advantage**: Despite defenses, NYT uses Next.js with SSR. If access succeeds, content is in initial HTML (`__NEXT_DATA__` JSON contains article metadata).

#### Paywall Handling

- **Type**: Hard paywall. ~10 free articles/month (dynamic personalized meter) for real users; crawlers get 0 free articles.
- **Strategy**: Title+metadata-only extraction. Accept `is_paywall_truncated: true` in RawArticle output.
- **What IS available without subscription**:
  - Article title (from sitemap `news:title` or page `og:title`)
  - Publication date (from sitemap `lastmod` or page meta)
  - Author (from page meta if accessible)
  - Category/section (from URL path: `/section/world` -> "world")
  - Article URL (from sitemap)
  - First paragraph (sometimes visible before paywall gate)
- **What is NOT available**: Full article body text.
- **Potential bypass options** (documented for user; not implemented by default):
  - Google AMP cache: `https://www.google.com/amp/s/nytimes.com/...` -- occasionally exposes full article
  - Google web cache: `https://webcache.googleusercontent.com/search?q=cache:nytimes.com/...`
  - Subscriber cookie injection: If NYT subscription obtained, inject session cookies at Tier 2
  - NYT Archive API: Public API for pre-1981 articles; not useful for daily crawling
- **Dual-pass analysis support**: Titles alone support topic modeling, keyword extraction, trend detection, and STEEPS classification per PRD strategy.

#### Volume & Timing

- **Daily estimate**: ~300 articles/day (metadata)
- **Peak publishing**: 06:00-22:00 EST, with morning and evening publication peaks
- **Crawl time**: 300 x (10s + 2s + 0.5s) x 1.1 = ~5.0 minutes (metadata only)
- **Content types**: News, opinion, features, multimedia. Body text unavailable.

---

### 3.5 ft.com (Financial Times) -- EXTREME

**Cross-Reference**: Step 1 Site #24 -- Extreme tier, hard paywall, Cloudflare Enterprise + geo-filtering
**Decision Rationale**: Sitemap-primary for URL discovery with title-only extraction. FT is more aggressively locked than NYT. Geographic filtering (UK IP preferred) adds complexity. RSS requires FT account.

#### sources.yaml Configuration

```yaml
ft:
  name: "Financial Times"
  url: "https://www.ft.com"
  region: "uk"
  language: "en"
  group: "E"
  crawl:
    primary_method: "sitemap"
    fallback_methods:
      - "dom"
    rss_url: null  # RSS requires FT subscription
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 10
    crawl_delay_mandatory: null
    max_requests_per_hour: 240
    jitter_seconds: 3
  anti_block:
    ua_tier: 3
    default_escalation_tier: 3
    max_escalation_tier: 6
    requires_proxy: false
    proxy_region: null
    bot_block_level: "HIGH"
  extraction:
    paywall_type: "hard"
    title_only: true
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Extreme"
    daily_article_estimate: 150
    sections_count: 15
    enabled: true
```

#### URL Discovery

- **Primary**: Sitemap (`/sitemap.xml`). FT publishes sitemaps for SEO purposes.
- **Sitemap structure**: Standard sitemap index with sub-sitemaps by content type and date.
- **Fallback**: DOM parsing of section pages (`/world`, `/companies`, `/markets`, `/opinion`) for headline extraction.
- **Fallback trigger**: Sitemap returns 403.

#### Article Extraction Selectors (Title-Only Mode)

```yaml
selectors:
  detail:
    title:
      primary: "h1.article-headline__heading"
      fallback_1: "meta[property='og:title']"
      fallback_2: "title"
    body:
      note: "BLOCKED by hard paywall. Content requires FT subscription."
      primary: null
      standfirst_attempt: "div.article__standfirst p"  # Subtitle/summary sometimes visible
    author:
      primary: "a.article-author__name"
      fallback: "meta[property='article:author']"
    date:
      primary: "time.article-content__timestamp[datetime]"
      fallback: "meta[property='article:published_time']"
      format: "ISO 8601"
    category:
      primary: "a.article-classifier__link"
      fallback: "meta[property='article:section']"
    canonical_url: "link[rel='canonical']"

  # FT uses React SSR (FT Next CMS)
  # __NEXT_DATA__ or similar hydration data may contain article metadata
  hydration_data:
    script_selector: "script#__NEXT_DATA__"
    title_path: "props.pageProps.article.headline"
    date_path: "props.pageProps.article.publishedDate"
    author_path: "props.pageProps.article.byline"

  exclude: []
```

#### Anti-Bot Handling

- **CDN/WAF**: Cloudflare Enterprise with geographic filtering
- **Defenses**: IP reputation, TLS fingerprinting, JS challenges, subscription cookie validation
- **UA strategy**: Tier 3, rotate per request
- **Geographic note**: UK IP may improve sitemap access. Not required but recommended.

#### Paywall Handling

- **Type**: Hard paywall. Virtually all content beyond headlines requires FT subscription.
- **Available without subscription**: Title, date, URL, author, category, standfirst (article summary/subtitle).
- **Not available**: Full article body.
- **Bypass options**: Google AMP/cache, subscriber cookies if subscription obtained.

#### Volume & Timing

- **Daily estimate**: ~150 articles/day (metadata)
- **Peak publishing**: 06:00-18:00 GMT (London business hours)
- **Crawl time**: 150 x (10s + 2s + 0.5s) x 1.1 = ~4.0 minutes
- **Content types**: Financial news, markets, companies, opinion

---

### 3.6 wsj.com (Wall Street Journal) -- EXTREME

**Cross-Reference**: Step 1 Site #25 -- Extreme tier, hard paywall, Dow Jones fingerprinting
**Decision Rationale**: Sitemap-primary with title-only extraction. WSJ is the most aggressively protected site in the Dow Jones portfolio. Same infrastructure as MarketWatch but stricter access controls.

#### sources.yaml Configuration

```yaml
wsj:
  name: "Wall Street Journal"
  url: "https://www.wsj.com"
  region: "us"
  language: "en"
  group: "E"
  crawl:
    primary_method: "sitemap"
    fallback_methods:
      - "dom"
    rss_url: null  # RSS subscriber-only
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 10
    crawl_delay_mandatory: null
    max_requests_per_hour: 240
    jitter_seconds: 3
  anti_block:
    ua_tier: 3
    default_escalation_tier: 3
    max_escalation_tier: 6
    requires_proxy: false
    proxy_region: null
    bot_block_level: "HIGH"
  extraction:
    paywall_type: "hard"
    title_only: true
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Extreme"
    daily_article_estimate: 200
    sections_count: 15
    enabled: true
```

#### URL Discovery

- **Primary**: Sitemap (`/sitemap.xml`). Dow Jones CMS generates standard sitemaps.
- **Sitemap structure**: Index sitemap with sub-sitemaps by section and date.
- **Fallback**: DOM parsing of section pages for headlines.
- **Fallback trigger**: Sitemap returns 403.

#### Article Extraction Selectors (Title-Only Mode)

```yaml
selectors:
  detail:
    title:
      primary: "h1.wsj-article-headline"
      fallback_1: "h1[class*='StyledHeadline']"  # React component class
      fallback_2: "meta[property='og:title']"
      fallback_3: "title"
    body:
      note: "BLOCKED by hard paywall. Subscription required."
      primary: null
      lead_paragraph: "p.article__lede"  # First paragraph sometimes visible
    author:
      primary: "span.article__byline a"
      fallback: "meta[name='author']"
    date:
      primary: "time.timestamp--pub[datetime]"
      fallback: "meta[property='article:published_time']"
      format: "ISO 8601"
    category:
      primary: "li.article-breadCrumb a"
      fallback: "meta[property='article:section']"
    canonical_url: "link[rel='canonical']"

  section_page:
    article_links: "h3[class*='WSJTheme--headline'] a"
    headline_text: "span.WSJTheme--headlineText"

  exclude: []
```

#### Anti-Bot Handling

- **CDN/WAF**: Cloudflare Enterprise + Dow Jones proprietary fingerprinting
- **Most aggressive**: WSJ is considered the hardest-to-crawl news site in the corpus alongside Bloomberg
- **Defenses**: Bot fingerprinting, subscription cookie validation, IP blocking, TLS fingerprinting
- **UA strategy**: Tier 3, rotate per request
- **Escalation**: Start Tier 3 -> Tier 4 (Patchright) -> Tier 5 (residential proxy) -> Tier 6 (Claude Code)

#### Paywall Handling

- **Type**: Hard paywall. Nearly all articles subscriber-only.
- **Available without subscription**: Title, date, URL, author, category, lead paragraph (sometimes).
- **Not available**: Full article body.
- **Bypass options**: Google AMP cache, subscriber cookies, Google web cache.

#### Volume & Timing

- **Daily estimate**: ~200 articles/day (metadata)
- **Peak publishing**: 06:00-18:00 EST
- **Crawl time**: 200 x (10s + 2s + 0.5s) x 1.1 = ~4.0 minutes
- **Content types**: Business news, markets, politics, opinion, tech

---

### 3.7 latimes.com (Los Angeles Times)

**Cross-Reference**: Step 1 Site #26 -- Medium tier, soft-metered paywall, GrapheneCMS
**Decision Rationale**: RSS-primary because LA Times publishes RSS feeds with article content. GrapheneCMS (migrated from Arc Publishing) renders SSR content accessible to httpx. Soft paywall manageable with cookie cycling.

#### sources.yaml Configuration

```yaml
latimes:
  name: "Los Angeles Times"
  url: "https://www.latimes.com"
  region: "us"
  language: "en"
  group: "E"
  crawl:
    primary_method: "rss"
    fallback_methods:
      - "sitemap"
      - "dom"
    rss_url: "https://www.latimes.com/rss2.0.xml"
    rss_sections:
      - url: "https://www.latimes.com/world-nation/rss2.0.xml"
        section: "world"
      - url: "https://www.latimes.com/politics/rss2.0.xml"
        section: "politics"
      - url: "https://www.latimes.com/california/rss2.0.xml"
        section: "california"
      - url: "https://www.latimes.com/business/rss2.0.xml"
        section: "business"
      - url: "https://www.latimes.com/entertainment-arts/rss2.0.xml"
        section: "entertainment"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 5
    crawl_delay_mandatory: null
    max_requests_per_hour: 720
    jitter_seconds: 0
  anti_block:
    ua_tier: 2
    default_escalation_tier: 1
    max_escalation_tier: 5
    requires_proxy: false
    proxy_region: null
    bot_block_level: "HIGH"
  extraction:
    paywall_type: "soft-metered"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Medium"
    daily_article_estimate: 150
    sections_count: 15
    enabled: true
```

#### URL Discovery

- **Primary**: RSS at `/rss2.0.xml` (main feed) and section-specific feeds. Format: RSS 2.0 with `title`, `link`, `pubDate`, `description`.
- **Fallback chain**: Sitemap (`/sitemap.xml`) -> DOM parsing of section pages.
- **Fallback trigger**: RSS returns < 10 articles OR HTTP 403 for > 30 minutes.

#### Article Extraction Selectors

```yaml
selectors:
  detail:
    title:
      primary: "h1.headline"
      fallback_1: "h1[class*='Title']"
      fallback_2: "meta[property='og:title']"
    body:
      primary: "div.page-article-body"
      fallback_1: "div[class*='RichTextArticleBody']"
      fallback_2: "div.article-body-content"
      strip:
        - "div[class*='ad-']"
        - "div[class*='newsletter']"
        - "div[class*='related']"
        - "aside"
        - "div[class*='social-share']"
        - "div[class*='inline-promo']"
    author:
      primary: "a[class*='author-name']"
      fallback: "meta[name='author']"
    date:
      primary: "time[datetime]"
      fallback: "meta[property='article:published_time']"
      format: "ISO 8601"
    category:
      primary: "a[class*='eyebrow']"
      fallback: "meta[property='article:section']"
    canonical_url: "link[rel='canonical']"

  exclude:
    - "div[class*='Enhancement']"
    - "div[id*='taboola']"
    - "div[class*='outbrain']"
    - "figure"  # Image blocks with captions
```

#### Anti-Bot Handling

- **CDN/WAF**: GrapheneCMS built-in protection (custom, migrated from Arc Publishing)
- **UA strategy**: Tier 2 pool (10 UAs), rotate per session
- **Escalation**: Standard 6-tier plan. Tier 3 (Playwright) if JS challenge detected.

#### Paywall Handling

- **Type**: Soft-metered. Some free articles per month before paywall activates.
- **Strategy**: Cookie reset between crawl sessions. Clear `_pcid`, `_pctx`, and metering-related cookies. Each fresh session resets the free article counter.
- **RSS advantage**: RSS feed `description` field often contains article summary even when page body is gated.

#### Volume & Timing

- **Daily estimate**: ~150 articles/day
- **Peak publishing**: 06:00-22:00 PST (Los Angeles timezone)
- **Crawl time**: 150 x (5s + 2s + 0.5s) x 1.1 = ~3.5 minutes
- **Content types**: California news, national news, politics, entertainment, business

---

### 3.8 buzzfeed.com (BuzzFeed)

**Cross-Reference**: Step 1 Site #27 -- Hard tier, no paywall, CSR React SPA, AI bots blocked
**Decision Rationale**: Playwright-primary because BuzzFeed is a React SPA requiring JS rendering. RSS is blocked by robots.txt (`/*.xml$`). AI bots explicitly blocked. Content is free but JS rendering is mandatory for body extraction.

**IMPORTANT NOTE**: BuzzFeed News shut down April 2023. Remaining content is entertainment/lifestyle only, not news journalism. This site may be deprioritized for news analysis purposes.

#### sources.yaml Configuration

```yaml
buzzfeed:
  name: "BuzzFeed"
  url: "https://www.buzzfeed.com"
  region: "us"
  language: "en"
  group: "E"
  crawl:
    primary_method: "playwright"
    fallback_methods:
      - "sitemap"
      - "dom"
    rss_url: null  # Blocked by robots.txt /*.xml$
    sitemap_urls:  # 8 sitemaps from robots.txt
      - "https://www.buzzfeed.com/sitemaps/buzzfeed/sitemap.xml"
      - "https://www.buzzfeed.com/sitemaps/buzzfeed/news/sitemap.xml"
      - "https://www.buzzfeed.com/sitemaps/tasty/sitemap.xml"
    sitemap_url: "/sitemaps/buzzfeed/sitemap.xml"
    rate_limit_seconds: 10
    crawl_delay_mandatory: null  # MSNBot: 120s, Slurp: 4s; use 10s as conservative default
    max_requests_per_hour: 240
    jitter_seconds: 3
  anti_block:
    ua_tier: 3
    default_escalation_tier: 3
    max_escalation_tier: 5
    requires_proxy: false
    proxy_region: null
    bot_block_level: "HIGH"
  extraction:
    paywall_type: "none"
    title_only: false
    rendering_required: true
    charset: "utf-8"
  meta:
    difficulty_tier: "Hard"
    daily_article_estimate: 50
    sections_count: 10
    enabled: true
```

#### URL Discovery

- **Primary**: Playwright -- navigate to section pages (`/`, `/news`, `/entertainment`, `/food`), wait for React rendering, extract article link elements.
- **Sitemap fallback**: Despite `/*.xml$` block in robots.txt (targeting RSS/Atom XML), the 8 sitemaps registered in robots.txt may still be accessible because sitemap index is a different path pattern. Test at runtime.
- **Fallback trigger**: Playwright crashes or returns empty DOM for > 3 consecutive attempts.

#### Article Extraction Selectors (Playwright-rendered DOM)

```yaml
selectors:
  # All selectors applied to Playwright-rendered DOM
  detail:
    title:
      primary: "h1[class*='title']"
      fallback_1: "h1"  # BuzzFeed uses simple h1 for article titles
      fallback_2: "meta[property='og:title']"
    body:
      primary: "div[class*='subbuzz-text']"  # BuzzFeed's content block pattern
      fallback_1: "div[data-module='subbuzz-text']"
      fallback_2: "div.js-subbuzz"
      strip:
        - "div[class*='ad-unit']"
        - "div[class*='newsletter']"
        - "div[class*='related-links']"
        - "aside"
        - "div[class*='sponsored']"
    author:
      primary: "span[class*='byline'] a"
      fallback: "meta[name='author']"
    date:
      primary: "time[datetime]"
      fallback: "meta[property='article:published_time']"
      format: "ISO 8601"
    category:
      primary: "a[class*='badge'] span"
      fallback: "meta[property='article:section']"
    canonical_url: "link[rel='canonical']"

  # Playwright-specific configuration
  playwright:
    wait_for: "div[class*='subbuzz']"  # Wait for content blocks to render
    timeout_ms: 15000
    scroll_to_bottom: false  # BuzzFeed loads all content on initial render
    block_resources:
      - "image"       # Block images to speed up rendering
      - "media"       # Block video/audio
      - "font"        # Block web fonts

  exclude:
    - "div[class*='ad-']"
    - "div[class*='promoted']"
    - "div[class*='shop']"
    - "div[class*='affiliate']"
```

#### Anti-Bot Handling

- **CDN/WAF**: Cloudflare
- **Explicitly blocked bots**: ClaudeBot, GPTBot, and 15+ AI crawlers
- **Dual blocking**: AI bots blocked in robots.txt AND `/*.xml$` blocks RSS/Atom feeds
- **UA strategy**: Tier 3 via Patchright stealth browser fingerprinting. No AI-identifying strings.
- **Escalation**: Start at Tier 3 (Playwright/Patchright baseline). Tier 4 (enhanced fingerprint). Tier 5 (residential proxy).
- **Resource cost**: Playwright adds ~3-5s page load time + ~415 MB memory per browser instance. Low volume (50 articles/day) makes this acceptable.

#### Paywall Handling

- **Type**: None. BuzzFeed is ad-supported.
- **Content note**: Since BuzzFeed News closure (April 2023), content is entertainment/lifestyle only.

#### Volume & Timing

- **Daily estimate**: ~50 articles/day
- **Peak publishing**: Throughout US business hours
- **Crawl time**: 50 x (10s + 5s render + 0.5s) x 1.1 = ~6.0 minutes
- **Content types**: Entertainment, lifestyle, food (Tasty), quizzes. NOT news journalism.

---

### 3.9 nationalpost.com (National Post, Canada)

**Cross-Reference**: Step 1 Site #28 -- Hard tier, soft-metered paywall, WordPress VIP
**Decision Rationale**: RSS-primary via WordPress `/feed` endpoint. WordPress VIP platform provides reliable RSS with `content:encoded` for full article text. Soft paywall (NP Connected) manageable with cookie cycling.

#### sources.yaml Configuration

```yaml
nationalpost:
  name: "National Post"
  url: "https://nationalpost.com"
  region: "us"  # Canada, but grouped with US/English
  language: "en"
  group: "E"
  crawl:
    primary_method: "rss"
    fallback_methods:
      - "sitemap"
      - "dom"
    rss_url: "https://nationalpost.com/feed"
    rss_sections:
      - url: "https://nationalpost.com/category/news/feed"
        section: "news"
      - url: "https://nationalpost.com/category/opinion/feed"
        section: "opinion"
      - url: "https://nationalpost.com/category/politics/feed"
        section: "politics"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 10
    crawl_delay_mandatory: null
    max_requests_per_hour: 240
    jitter_seconds: 3
  anti_block:
    ua_tier: 3
    default_escalation_tier: 2
    max_escalation_tier: 5
    requires_proxy: false
    proxy_region: null
    bot_block_level: "HIGH"
  extraction:
    paywall_type: "soft-metered"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Hard"
    daily_article_estimate: 100
    sections_count: 12
    enabled: true
```

#### URL Discovery

- **Primary**: RSS at `/feed` (WordPress VIP standard). Format: RSS 2.0 with `title`, `link`, `pubDate`, `dc:creator`, `category`, `content:encoded`.
- **WordPress RSS advantage**: `content:encoded` tag often contains full HTML article body, potentially bypassing the need to fetch individual article pages.
- **Section feeds**: WordPress category feeds at `/category/{section}/feed`.
- **Fallback chain**: Sitemap (`/sitemap.xml`, WordPress) -> DOM parsing.
- **Fallback trigger**: RSS returns < 10 articles OR `/feed` returns 403 for > 30 minutes.

#### Article Extraction Selectors

```yaml
selectors:
  # RSS content:encoded parsing (primary -- may contain full article)
  rss_content:
    full_body: "content:encoded"  # HTML body in RSS feed
    strip_html_tags:
      - "script"
      - "style"
      - "iframe"

  # Article page selectors (fallback if RSS content:encoded is truncated)
  detail:
    title:
      primary: "h1.article-title"
      fallback_1: "h1.entry-title"  # WordPress default
      fallback_2: "meta[property='og:title']"
    body:
      primary: "div.article-content"
      fallback_1: "div.entry-content"  # WordPress default
      fallback_2: "div[class*='story-content']"
      strip:
        - "div[class*='related-stories']"
        - "div[class*='newsletter']"
        - "div[class*='ad-']"
        - "aside"
        - "div[class*='social-share']"
        - "div[class*='paywall-prompt']"  # Remove paywall prompt overlay
    author:
      primary: "span.author-name a"
      fallback_1: "a[class*='author'] span"
      fallback_2: "meta[name='author']"
    date:
      primary: "time.published-date[datetime]"
      fallback: "meta[property='article:published_time']"
      format: "ISO 8601"
    category:
      primary: "a[class*='category-link']"
      fallback: "meta[property='article:section']"
    canonical_url: "link[rel='canonical']"

  exclude:
    - "div[class*='outbrain']"
    - "div[class*='taboola']"
    - "div[class*='wp-block-embed']"
    - "div[id*='piano-']"  # Piano paywall overlay elements
```

#### Anti-Bot Handling

- **CDN/WAF**: Cloudflare (Postmedia Network uses Cloudflare across all properties)
- **UA strategy**: Tier 3, rotate per request
- **Escalation**: Tier 2 -> Tier 3 -> Tier 4 -> Tier 5

#### Paywall Handling

- **Type**: Soft-metered (NP Connected / Postmedia subscription)
- **Strategy**: Cookie reset between crawl sessions. Clear `piano_*` and `_pc*` cookies (Piano paywall platform).
- **RSS bypass**: WordPress RSS `content:encoded` may contain full body even when web page is gated.
- **Canadian IP note**: Canadian IP may improve access but is not required.

#### Volume & Timing

- **Daily estimate**: ~100 articles/day
- **Peak publishing**: 08:00-18:00 EST (Toronto timezone)
- **Crawl time**: 100 x (10s + 2s + 0.5s) x 1.1 = ~3.0 minutes
- **Content types**: Canadian news, politics, opinion, business

---

### 3.10 edition.cnn.com (CNN International)

**Cross-Reference**: Step 1 Site #29 -- Medium tier, no paywall, blocks 60+ bots, SSR
**Decision Rationale**: Sitemap-primary because CNN has 15 well-structured sitemaps providing excellent URL discovery coverage for ~500 daily articles. Content is free (ad-supported) and SSR, so httpx is sufficient despite HIGH bot-blocking -- the blocking targets AI-specific UAs, not standard browser UAs.

#### sources.yaml Configuration

```yaml
cnn:
  name: "CNN"
  url: "https://edition.cnn.com"
  region: "us"
  language: "en"
  group: "E"
  crawl:
    primary_method: "sitemap"
    fallback_methods:
      - "dom"
      - "rss"
    rss_url: "http://rss.cnn.com/rss/edition.rss"
    sitemap_url: "/sitemaps/sitemap-index.xml"
    sitemap_sections:
      - "sitemap-articles-*.xml"       # News articles
      - "sitemap-section-*.xml"        # Section pages
      - "cnn-news-sitemap.xml"         # Google News sitemap
    rate_limit_seconds: 5
    crawl_delay_mandatory: null
    max_requests_per_hour: 720
    jitter_seconds: 0
  anti_block:
    ua_tier: 2
    default_escalation_tier: 1
    max_escalation_tier: 5
    requires_proxy: false
    proxy_region: null
    bot_block_level: "HIGH"
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

#### URL Discovery

- **Primary**: 15 sitemaps (confirmed via robots.txt probe, Step 1). Parse sitemap index for sub-sitemaps covering news, politics, opinion, video, galleries, markets, live stories, election content.
- **Google News sitemap**: CNN's news sitemap includes `news:title`, `news:publication_date`, `news:keywords` -- rich metadata for URL discovery.
- **Fallback chain**: DOM parsing of section pages (`/world`, `/us`, `/politics`, `/business`, `/tech`, `/entertainment`, `/health`) -> RSS (`rss.cnn.com`).
- **Fallback trigger**: All sitemaps return 403 OR < 10 new URLs per day.
- **High volume strategy**: CNN publishes ~500 articles/day. Sitemap-based discovery ensures no articles are missed. Filter by `lastmod` or `news:publication_date` to fetch only today's articles.

#### Article Extraction Selectors

```yaml
selectors:
  detail:
    title:
      primary: "h1.headline__text"
      fallback_1: "h1[data-editable='headlineText']"
      fallback_2: "meta[property='og:title']"
    body:
      primary: "div.article__content"
      fallback_1: "div[class*='BasicArticle__body']"
      fallback_2: "section.body-text"
      strip:
        - "div.ad"
        - "div[class*='related-content']"
        - "div[class*='el__embedded']"     # Embedded widgets
        - "div[class*='zn-body__read-all']" # "Read more" links
        - "aside"
        - "div[class*='social']"
        - "div[class*='gallery-inline']"
    author:
      primary: "span.byline__name"
      fallback_1: "meta[name='author']"
      fallback_2: "meta[property='article:author']"
    date:
      primary: "div.timestamp[data-timestamp]"  # CNN uses data-timestamp attribute
      fallback_1: "meta[property='article:published_time']"
      fallback_2: "time[datetime]"
      format: "ISO 8601"
    category:
      primary: "meta[name='section']"
      fallback: "meta[property='article:section']"
    canonical_url: "link[rel='canonical']"

  # CNN article URL pattern
  url_pattern: "/202*/*/index.html"

  # Section page link extraction (DOM fallback)
  section_page:
    article_links: "a.container__link[href*='/202']"
    headline_text: "span.container__headline-text"

  exclude:
    - "div[class*='video-player']"
    - "div[class*='factbox']"
    - "div[class*='editor-note']"
    - "div[class*='image__credit']"
    - "nav"
```

#### Anti-Bot Handling

- **CDN/WAF**: Custom CNN infrastructure (CNNdigital CMS)
- **Explicitly blocked bots** (Step 1 confirmed): 60+ user agents including ClaudeBot, Claude-Web, GPTBot, anthropic-ai, PerplexityBot, Amazonbot, and many others.
- **Key insight**: Despite blocking 60+ bots, CNN content is SSR and free. Standard browser UAs work.
- **UA strategy**: Tier 2 pool (10 UAs). CRITICAL: No AI-identifying UA strings. Standard Chrome/Firefox only.
- **Googlebot-News**: Blocked from `/sponsor` content only; otherwise allowed. This confirms CNN wants search engine indexing of legitimate news content.

#### Paywall Handling

- **Type**: None. CNN is fully ad-supported.
- **Content access**: All article bodies freely accessible with proper UA.

#### Volume & Timing

- **Daily estimate**: ~500 articles/day (highest volume in Group E)
- **Peak publishing**: 24/7 operation with peaks during US business hours
- **Crawl time**: 500 x (5s + 2s + 0.5s) x 1.1 = ~6.0 minutes
- **Content types**: Breaking news, politics, world, business, tech, entertainment, health, sports
- **Live blogs**: CNN publishes live blogs that continuously update. Treat each live blog as a single article; re-crawl URL if `lastmod` changes in sitemap.

---

### 3.11 bloomberg.com (Bloomberg) -- EXTREME

**Cross-Reference**: Step 1 Site #30 -- Extreme tier, hard paywall, 403 on homepage
**Decision Rationale**: Sitemap-primary for URL discovery with title-only (or URL-only) extraction. Bloomberg is the most aggressively blocked site in the entire 44-site corpus. Homepage returns 403 for non-subscribers. Even metadata extraction will be degraded.

#### sources.yaml Configuration

```yaml
bloomberg:
  name: "Bloomberg"
  url: "https://www.bloomberg.com"
  region: "us"
  language: "en"
  group: "E"
  crawl:
    primary_method: "sitemap"
    fallback_methods:
      - "dom"
    rss_url: null  # No public RSS; requires account
    sitemap_urls:  # 9 sitemaps from robots.txt (note: /sitemap.xml returns 403)
      - "https://www.bloomberg.com/feeds/sitemap_news.xml"
      - "https://www.bloomberg.com/feeds/sitemap_collection.xml"
      - "https://www.bloomberg.com/feeds/sitemap_video.xml"
      - "https://www.bloomberg.com/feeds/sitemap_audio.xml"
      - "https://www.bloomberg.com/feeds/sitemap_people.xml"
      - "https://www.bloomberg.com/feeds/sitemap_companies.xml"
      - "https://www.bloomberg.com/feeds/sitemap_securities.xml"
      - "https://www.bloomberg.com/feeds/sitemap_billionaires.xml"
    sitemap_url: "/feeds/sitemap_news.xml"  # Use direct sitemap URL, not /sitemap.xml
    rate_limit_seconds: 10
    crawl_delay_mandatory: null
    max_requests_per_hour: 240
    jitter_seconds: 3
  anti_block:
    ua_tier: 3
    default_escalation_tier: 3
    max_escalation_tier: 6
    requires_proxy: false
    proxy_region: null
    bot_block_level: "HIGH"
  extraction:
    paywall_type: "hard"
    title_only: true
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Extreme"
    daily_article_estimate: 200
    sections_count: 15
    enabled: true
```

#### URL Discovery

- **Primary**: Direct sitemap URLs from robots.txt (Step 1 confirmed 9 sitemaps). IMPORTANT: `/sitemap.xml` returns 403; use `/feeds/sitemap_news.xml` directly.
- **Sitemap structure**: Separate sitemaps for news, collections, video, audio, people, companies, securities, billionaires. Use `sitemap_news.xml` for daily articles.
- **Fallback**: DOM parsing of section pages (if any section pages load without authentication).
- **Fallback trigger**: All 9 sitemap URLs return 403.
- **Degraded mode**: If all sitemaps blocked, Bloomberg may only contribute URL patterns from Google News aggregation or social media links.

#### Article Extraction Selectors (Title-Only Mode)

```yaml
selectors:
  detail:
    title:
      primary: "h1.lede-text-v2__hed"
      fallback_1: "h1[class*='headline']"
      fallback_2: "meta[property='og:title']"
      fallback_3: "title"  # Last resort
    body:
      note: "BLOCKED. Bloomberg returns 403 for non-subscriber article pages."
      primary: null
    author:
      primary: "div.authors a"
      fallback: "meta[name='author']"
    date:
      primary: "time[datetime]"
      fallback: "meta[property='article:published_time']"
      format: "ISO 8601"
    category:
      primary: "a[class*='breadcrumb'] span"
      fallback: "meta[property='article:section']"
    canonical_url: "link[rel='canonical']"

  # Bloomberg sitemap metadata
  sitemap_fields:
    url: "loc"
    lastmod: "lastmod"
    news_title: "news:title"
    news_publication_date: "news:publication_date"

  exclude: []
```

#### Anti-Bot Handling

- **CDN/WAF**: Cloudflare Enterprise (most aggressive configuration observed in corpus)
- **Homepage 403**: Bloomberg returns HTTP 403 for direct homepage access from non-subscriber IPs (confirmed Step 1 probe).
- **Defenses**: IP blocking, subscription cookie validation, TLS fingerprinting, AI bot blanket Disallow.
- **Explicitly blocked bots**: Claude-Web, GPTBot, anthropic-ai (blanket Disallow with limited allows for /professional, /company, /latam, /faq, /tc).
- **UA strategy**: Tier 3, rotate per request. Even standard browser UAs may receive 403.
- **Escalation**: Start Tier 3 (Playwright) -> Tier 4 (Patchright) -> Tier 5 (residential proxy with Bloomberg-compatible cookies) -> Tier 6 (Claude Code analysis).
- **Realistic expectation**: Even with full escalation, body extraction without subscription is likely impossible. Title+URL from sitemaps is the achievable target.

#### Paywall Handling

- **Type**: Hard paywall (Bloomberg Terminal or Bloomberg.com subscription)
- **Most aggressive in corpus**: Not just paywall -- active blocking of non-subscriber access to article pages.
- **Available without subscription**: URLs from sitemaps, titles from sitemap `news:title` field, dates from `lastmod`.
- **Not available**: Article body, author, category (page access blocked).
- **Potential fallback**: Google cache of Bloomberg articles may provide title+summary.
- **Subscription upgrade**: Full access requires Bloomberg subscription ($35/month for Bloomberg.com; Bloomberg Terminal is $24,000/year). Document for user decision.

#### Volume & Timing

- **Daily estimate**: ~200 articles/day (metadata, possibly degraded to URL-only)
- **Peak publishing**: 24/7 financial news; peaks during US and European market hours
- **Crawl time**: 200 x (10s + 2s + 0.5s) x 1.1 = ~4.0 minutes (metadata only)
- **Content types**: Financial markets, economics, technology, politics, opinion

---

### 3.12 afmedios.com (AF Medios)

**Cross-Reference**: Step 1 Site #31 -- Easy tier, no paywall, WordPress, fully permissive
**Decision Rationale**: RSS-primary with full article content in `content:encoded`. WordPress platform with standard theme makes extraction trivially easy. Easiest site in Group E.

#### sources.yaml Configuration

```yaml
afmedios:
  name: "AF Medios"
  url: "https://afmedios.com"
  region: "mx"
  language: "es"
  group: "E"
  crawl:
    primary_method: "rss"
    fallback_methods:
      - "sitemap"
    rss_url: "https://afmedios.com/rss"
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
    daily_article_estimate: 20
    sections_count: 6
    enabled: true
```

#### URL Discovery

- **Primary**: RSS at `/rss` (RSS 2.0, 20 items confirmed active 2026-02-26 from Step 1 direct probe). WordPress standard feed with `content:encoded`.
- **RSS content**: Full article HTML body available in `content:encoded` tag -- may not need individual page fetches.
- **Fallback**: Sitemap index at `/sitemap_index.xml` (WordPress Yoast SEO).
- **Fallback trigger**: RSS returns 0 articles (highly unlikely given confirmed active feed).

#### Article Extraction Selectors

```yaml
selectors:
  # RSS extraction (primary -- contains full article)
  rss_content:
    title: "title"
    link: "link"
    date: "pubDate"
    author: "dc:creator"
    category: "category"
    full_body: "content:encoded"

  # Article page selectors (fallback if RSS truncated)
  detail:
    title:
      primary: "h1.entry-title"
      fallback: "meta[property='og:title']"
    body:
      primary: "div.entry-content"
      fallback: "div.post-content"
      strip:
        - "div[class*='sharedaddy']"     # WordPress sharing buttons
        - "div[class*='related-posts']"
        - "div[class*='wp-block-embed']"
    author:
      primary: "span.author-name a"
      fallback: "meta[name='author']"
    date:
      primary: "time.entry-date[datetime]"
      fallback: "meta[property='article:published_time']"
      format: "ISO 8601"
    category:
      primary: "span.cat-links a"
      fallback: "meta[property='article:section']"
    canonical_url: "link[rel='canonical']"

  exclude:
    - "div.sharedaddy"
    - "div[class*='wp-block-embed']"
    - "nav.post-navigation"
```

#### Anti-Bot Handling

- **CDN/WAF**: None (standard WordPress hosting)
- **robots.txt**: Fully permissive -- only `/wp-admin/` blocked (with admin-ajax.php exception). Standard WordPress default.
- **UA strategy**: Tier 1 -- single UA, rotate weekly. No restrictions.
- **No escalation needed**: Easy site with no blocking.

#### Paywall Handling

- **Type**: None. Freely accessible regional news site.

#### Volume & Timing

- **Daily estimate**: ~20 articles/day
- **Peak publishing**: Mexican business hours (GMT-6)
- **Crawl time**: 20 x (2s + 0.5s) x 1.1 = ~0.5 minutes
- **Content types**: Spanish-language regional news from Colima, Mexico
- **Language note**: This is the only Spanish-language site in Group E. Trafilatura handles Spanish extraction well.

---

## 4. Anti-Bot Mitigation Matrix

[trace:step-3:6-tier-escalation-system] -- Escalation tiers from Step 3 feasibility analysis.
[trace:step-5:anti-block-component] -- Anti-block system design from Step 5 architecture.

| Site | CDN/WAF | Bot Block Level | Blocked Bots | Starting Tier | Max Tier | Strategy |
|------|---------|----------------|--------------|---------------|----------|----------|
| marketwatch.com | Cloudflare Enterprise | HIGH | AI bots | T2 | T5 | Session mgmt + UA rotation |
| voakorea.com | Government std | LOW | AhrefsBot only | T1 | T3 | Single UA, no issues |
| huffpost.com | Custom (AOL legacy) | HIGH | 28+ AI bots | T1 | T5 | Standard browser UA critical |
| nytimes.com | Cloudflare + proprietary | HIGH | AI bots, all | T3 | T6 | Playwright baseline, title-only |
| ft.com | Cloudflare Enterprise | HIGH | AI bots | T3 | T6 | Playwright baseline, title-only |
| wsj.com | Cloudflare Enterprise | HIGH | AI bots + fingerprint | T3 | T6 | Most aggressive, title-only |
| latimes.com | GrapheneCMS | HIGH | Standard | T1 | T5 | Standard httpx + cookie reset |
| buzzfeed.com | Cloudflare | HIGH | 15+ AI bots | T3 | T5 | Playwright mandatory (CSR) |
| nationalpost.com | Cloudflare | HIGH | Standard | T2 | T5 | Session mgmt + RSS bypass |
| edition.cnn.com | Custom (CNNdigital) | HIGH | 60+ bots | T1 | T5 | Standard UA works despite list |
| bloomberg.com | Cloudflare Enterprise | HIGH | AI bots, 403 default | T3 | T6 | 403 on homepage, degraded |
| afmedios.com | None | LOW | None | T1 | T3 | No blocking, trivial |

### UA Pool Requirements

| Tier | Pool Size | Sites | Rotation Strategy |
|------|-----------|-------|-------------------|
| T1 | 1 UA | voakorea.com, afmedios.com | Rotate weekly |
| T2 | 10 UAs | huffpost.com, latimes.com, edition.cnn.com | Rotate per session |
| T3 | 50 UAs | marketwatch.com, nytimes.com, ft.com, wsj.com, buzzfeed.com, nationalpost.com, bloomberg.com | Rotate per request |

### Critical UA Rules (ALL Group E Sites)

1. **NEVER** use AI-identifying UA strings (ClaudeBot, Claude-Web, anthropic-ai, GPTBot, ChatGPT-User, PerplexityBot)
2. Use realistic browser UAs with current Chrome/Firefox version numbers
3. Include proper `Accept`, `Accept-Language: en-US,en;q=0.9`, `Accept-Encoding: gzip, deflate, br` headers
4. Set `Connection: keep-alive` for session persistence

---

## 5. Paywall Handling Summary

[trace:step-1:paywall-classification] -- Paywall types from Step 1 reconnaissance.
[trace:step-3:extreme-sites] -- Title-only strategy from Step 3 feasibility analysis.

### Hard Paywall Sites (Title-Only Mode)

| Site | Paywall Provider | Available Metadata | Body Access | Subscription Cost |
|------|-----------------|-------------------|-------------|-------------------|
| nytimes.com | NYT proprietary | Title, date, author, category, URL, 1st paragraph | Requires NYT Digital ($17/month) | $17/month |
| ft.com | FT Next | Title, date, author, category, URL, standfirst | Requires FT subscription ($40/month) | $40/month |
| wsj.com | Dow Jones | Title, date, author, category, URL, lead paragraph | Requires WSJ subscription ($40/month) | $40/month |
| bloomberg.com | Bloomberg | URL from sitemap, title from sitemap (page access 403) | Requires Bloomberg ($35/month) | $35/month |

**Total subscription cost for full access**: ~$132/month. Document for user decision.

### Soft-Metered Paywall Sites (Cookie Reset Strategy)

| Site | Meter Type | Free Quota | Cookie Reset Strategy |
|------|-----------|------------|----------------------|
| marketwatch.com | Dow Jones shared meter | Several articles/session | Clear `djcs_*`, `usr_*` cookies |
| latimes.com | GrapheneCMS meter | Several articles/month | Clear `_pcid`, `_pctx` cookies |
| nationalpost.com | Piano (Postmedia) | Several articles/month | Clear `piano_*`, `_pc*` cookies |

### RawArticle Output for Paywall Sites

```python
# For hard paywall sites, RawArticle will have:
RawArticle(
    url="https://www.nytimes.com/2026/02/25/...",
    title="Article Headline Here",
    body="",  # Empty string -- body blocked
    source_id="nytimes",
    source_name="The New York Times",
    language="en",
    published_at=datetime(2026, 2, 25, ...),
    crawled_at=datetime.now(UTC),
    author="Author Name",
    category="politics",
    content_hash="",  # Empty body -> empty hash
    crawl_tier=3,
    crawl_method="sitemap",
    is_paywall_truncated=True,  # Signals title-only mode
)
```

---

## 6. Volume Estimates and Crawl Time Budget

[trace:step-3:parallelization-plan] -- Group-level parallelization from Step 3.

### Per-Site Volume

| Site | Daily Articles | Crawl Min | Content | Peak Hours |
|------|---------------|-----------|---------|------------|
| edition.cnn.com | ~500 | 6.0 | Full body | 24/7 |
| nytimes.com | ~300 | 5.0 | Title-only | 06:00-22:00 EST |
| marketwatch.com | ~200 | 5.0 | Partial (metered) | 06:00-17:00 EST |
| wsj.com | ~200 | 4.0 | Title-only | 06:00-18:00 EST |
| bloomberg.com | ~200 | 4.0 | Title-only/URL | 24/7 |
| latimes.com | ~150 | 3.5 | Full (with cookie reset) | 06:00-22:00 PST |
| ft.com | ~150 | 4.0 | Title-only | 06:00-18:00 GMT |
| huffpost.com | ~100 | 3.0 | Full body | 08:00-22:00 EST |
| nationalpost.com | ~100 | 3.0 | Partial (metered) | 08:00-18:00 EST |
| buzzfeed.com | ~50 | 6.0 | Full (Playwright) | US hours |
| voakorea.com | ~50 | 1.5 | Full body | US hours |
| afmedios.com | ~20 | 0.5 | Full body | MX hours |
| **TOTAL** | **~1,920** | **~49.5** | -- | -- |

### Group E Crawl Time Budget

- **Sequential**: ~49.5 minutes
- **Parallel (3 subgroups)**: ~16.5 minutes
  - Subgroup E1 (Easy+Medium): voakorea + huffpost + latimes + cnn + afmedios = ~14.0 min
  - Subgroup E2 (Hard): marketwatch + buzzfeed + nationalpost = ~14.0 min
  - Subgroup E3 (Extreme): nytimes + ft + wsj + bloomberg = ~17.0 min
- **Within 2-hour budget**: Group E parallel time (~16.5 min) fits within the overall 6-group parallel budget (~53 min total for all 44 sites).

### Content Breakdown

| Content Type | Articles/Day | % of Total |
|-------------|-------------|-----------|
| Full body (no paywall) | ~720 | 37.5% |
| Partial body (soft-metered) | ~450 | 23.4% |
| Title-only (hard paywall) | ~750 | 39.1% |
| **Total** | **~1,920** | **100%** |

---

## 7. L1 Self-Verification

### Verification Checklist

| # | Criterion | Status | Evidence |
|---|----------|--------|----------|
| 1 | All 12 English sites covered | PASS | Sections 3.1-3.12 cover all 12 sites from group-english.json |
| 2 | Paywall strategies are realistic | PASS | Hard paywall sites use title-only mode; no optimistic assumptions about free access. Subscription costs documented. |
| 3 | CSS selectors specified for each site | PASS | Every site has title, body (or null for hard paywall), author, date, category selectors with fallbacks |
| 4 | Fundus/Trafilatura compatibility noted | PASS | Section 1 Executive Summary includes compatibility matrix |
| 5 | Anti-bot handling matches observed defenses | PASS | CDN/WAF identified per site; UA tier matches blocking level; AI bot blocking noted where confirmed |
| 6 | Rate limits consistent with Step 3 | PASS | All rate limits match Step 3 feasibility analysis values |
| 7 | Volume estimates match Step 1 | PASS | Daily article counts from Step 1 reconnaissance data |
| 8 | sources.yaml configurations align with Step 5 schema | PASS | All configs follow Section 5c schema from architecture blueprint |
| 9 | Fallback chains defined for every site | PASS | Each site has primary + ordered fallback methods with explicit triggers |
| 10 | Decision Rationale included per site | PASS | Each section 3.x begins with Cross-Reference + Decision Rationale |
| 11 | Cross-references to Step 1 recon | PASS | [trace:step-1:*] markers and explicit Step 1 Site # references |
| 12 | BuzzFeed News shutdown noted | PASS | Section 3.8 includes warning about April 2023 shutdown |

### Selector Verification Notes

- **Spot-checked via WebFetch**: voakorea.com (confirmed JSON-LD with `isAccessibleForFree: true`), huffpost.com robots.txt (confirmed 5 sitemaps and 28+ blocked AI bots).
- **Sites blocking WebFetch**: nytimes.com, marketwatch.com, wsj.com, ft.com, bloomberg.com, latimes.com, nationalpost.com, buzzfeed.com, edition.cnn.com -- all blocked WebFetch tool, confirming HIGH bot-blocking classification.
- **Selector sources**: CSS selectors are based on known CMS patterns (WordPress, Dow Jones, GrapheneCMS, CNNdigital, Next.js), Step 1 reconnaissance notes, and standard news site conventions. Selectors include 2-3 fallback levels to handle CSS class changes across site redesigns.
- **Runtime selector validation**: All selectors should be verified against live site HTML during Step 8 (adapter implementation). Selectors using CSS module hashes (e.g., NYT's `e1h9p8200`) are fragile and should fall back to `meta[property='og:title']`.

---

## 8. Special Considerations

### 8.1 Playwright Resource Budget

Only 1 site in Group E requires Playwright: buzzfeed.com.

| Site | Playwright Required | Reason | Memory Cost | Articles/Day |
|------|-------------------|--------|------------|-------------|
| buzzfeed.com | Yes (primary) | React CSR SPA | ~415 MB per instance | ~50 |
| All others | No (escalation only) | SSR content | ~65 MB (httpx) | ~1,870 |

Playwright is available as escalation (Tier 3+) for all other sites but should rarely be needed since they are SSR.

### 8.2 Google News Sitemap Advantage

Several Group E sites publish Google News sitemaps with rich metadata:

| Site | News Sitemap | Metadata Fields |
|------|-------------|-----------------|
| huffpost.com | `sitemap-google-news.xml` | title, publication_date, keywords |
| edition.cnn.com | `cnn-news-sitemap.xml` | title, publication_date, keywords |
| bloomberg.com | `sitemap_news.xml` | title, publication_date |

Google News sitemaps are particularly valuable for hard paywall sites (bloomberg.com) where page access is blocked -- the sitemap itself provides title and date without needing to fetch the article page.

### 8.3 Language Distribution

| Language | Sites | Note |
|----------|-------|------|
| English | 11 | All except afmedios.com |
| Spanish | 1 | afmedios.com (Colima, Mexico) |
| Korean | 1 (bilingual) | voakorea.com (primarily Korean with some English) |

### 8.4 Time Zone Coverage

Group E sites cover 3 primary time zones:
- **EST/EDT** (UTC-5/-4): nytimes.com, wsj.com, bloomberg.com, huffpost.com, edition.cnn.com, nationalpost.com
- **PST/PDT** (UTC-8/-7): latimes.com, buzzfeed.com
- **GMT** (UTC+0): ft.com
- **CST** (UTC-6): afmedios.com
- **Mixed/24/7**: voakorea.com, marketwatch.com (pre-market + post-market)

Optimal crawl window for Group E: **06:00-08:00 EST** (catches overnight publications + early morning US content + FT morning edition).
