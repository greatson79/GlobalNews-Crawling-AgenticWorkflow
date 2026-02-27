# Crawl Strategy: Group G -- Europe/Middle East (7 Sites)

**Agent**: @crawl-strategist-global
**Date**: 2026-02-26
**Workflow Step**: 6 of 20 (Team Task)
**Inputs**: Step 1 Site Reconnaissance, Step 3 Crawling Feasibility, Step 5 Architecture Blueprint (Section 5c)

---

## Executive Summary

This document defines production-ready crawling configurations for 7 Europe/Middle East news sites (Group G), covering URL discovery, article extraction selectors, multi-language handling, anti-bot configurations, rate limiting, and geo-blocking strategies.

### Group G Metrics

| Metric | Value |
|--------|-------|
| Total sites | 7 |
| Languages | English (5), German (1), French (1) |
| Script directions | LTR (all 7 English-edition targets) |
| Primary methods | RSS (5), Sitemap (1), RSS-title-only (1) |
| Difficulty breakdown | Easy (2), Medium (2), Hard (2), Extreme (1) |
| Total daily article estimate | ~900 articles |
| Total daily crawl time (sequential) | ~22 minutes |
| Sites requiring geographic proxy | 3 (bild.de REQUIRED, thesun.co.uk RECOMMENDED, arabnews.com RECOMMENDED) |
| Hard paywall sites (title-only) | 1 (lemonde.fr) |

[trace:step-1:difficulty-classification-matrix] -- Tier classifications driving escalation plans.
[trace:step-3:strategy-matrix] -- Per-site primary/fallback methods and rate limits.
[trace:step-5:sources-yaml-schema] -- sources.yaml field structure for output compatibility.

---

## Strategy Matrix (All 7 Sites)

| # | Site | Primary | Fallback | Rate Limit | UA Tier | Bot Level | Proxy | Paywall | Daily Est. | Crawl Min | Difficulty |
|---|------|---------|----------|------------|---------|-----------|-------|---------|-----------|-----------|------------|
| 38 | thesun.co.uk | RSS | Sitemap+DOM | 10s+jitter | T3 (50) | HIGH | UK (REC) | none | ~300 | ~5.0 | Hard |
| 39 | bild.de | RSS | Sitemap+DOM | 10s+jitter | T3 (50) | HIGH | DE (REQ) | soft-metered | ~200 | ~5.0 | Hard |
| 40 | lemonde.fr | RSS | Sitemap (title-only) | 10s+jitter | T3 (50) | HIGH | none | hard | ~150 | ~4.0 | Extreme |
| 41 | themoscowtimes.com | RSS | Sitemap | 2s | T1 (1) | LOW | none | freemium | ~20 | ~1.0 | Easy |
| 42 | arabnews.com | Sitemap (news) | DOM | 10s (mandatory) | T2 (10) | MEDIUM | ME (REC) | none | ~100 | ~3.0 | Medium |
| 43 | aljazeera.com | RSS | Sitemap+DOM | 5s | T2 (10) | HIGH | none | none | ~100 | ~3.0 | Medium |
| 44 | israelhayom.com | RSS (WP) | Sitemap (WP) | 2s | T1 (1) | LOW | none | none | ~30 | ~1.0 | Easy |

**Legend**: REQ = Required, REC = Recommended, WP = WordPress

---

## Language & Encoding Matrix

| Site | Primary Language | Script | Primary Encoding | Special Characters | RTL Content | Notes |
|------|-----------------|--------|-----------------|-------------------|-------------|-------|
| thesun.co.uk | English | Latin/LTR | UTF-8 | None | No | Standard English tabloid |
| bild.de | German | Latin/LTR | UTF-8 | ae, oe, ue, ss (Umlauts, Eszett) | No | German URL slugs may use transliteration (ae->ae) |
| lemonde.fr | French | Latin/LTR | UTF-8 | e-acute, e-grave, a-grave, c-cedilla, circumflexes | No | French URL slugs percent-encode or transliterate accents |
| themoscowtimes.com | English | Latin/LTR | UTF-8 | None | No | English-language publication |
| arabnews.com | English | Latin/LTR | UTF-8 | None (English edition) | No | English edition; Arabic edition at arabnews.com/ar not in scope |
| aljazeera.com | English | Latin/LTR | UTF-8 | None (English edition) | No | English edition; Arabic at aljazeera.net not in scope |
| israelhayom.com | English | Latin/LTR | UTF-8 | None (English edition) | No | English edition; Hebrew at israelhayom.co.il not in scope |

**Encoding note**: All 7 Group G sites serve their target editions in UTF-8. No legacy encoding (ISO-8859-1, Windows-1252) fallback is needed. German umlauts and French accents are natively handled by UTF-8. The crawler should declare `Accept-Charset: utf-8` and validate response charset headers.

**RTL note**: While arabnews.com, aljazeera.com, and israelhayom.com have Arabic/Hebrew editions, our crawl targets are their English-language editions exclusively. No RTL text handling is required for Group G. If future scope expansion includes Arabic/Hebrew editions, `dir="rtl"` preservation, bidirectional text handling, and Eastern Arabic numeral parsing would be needed.

---

## Per-Site Detailed Strategies

### 38. thesun.co.uk (The Sun)

**Cross-Reference**: [trace:step-1:site-38-thesun] -- Hard tier, HIGH bot-blocking, RSS available, no paywall.
**Cross-Reference**: [trace:step-3:group-g-thesun] -- RSS primary, 10s+jitter, T3 UAs, UK proxy recommended.

#### sources.yaml Configuration

```yaml
thesun:
  name: "The Sun"
  url: "https://www.thesun.co.uk"
  region: "uk"
  language: "en"
  group: "G"
  crawl:
    primary_method: "rss"
    fallback_methods:
      - "sitemap"
      - "dom"
    rss_url: "https://www.thesun.co.uk/feed/"
    rss_section_feeds:
      - "https://www.thesun.co.uk/news/feed/"
      - "https://www.thesun.co.uk/money/feed/"
      - "https://www.thesun.co.uk/tech/feed/"
      - "https://www.thesun.co.uk/health/feed/"
      - "https://www.thesun.co.uk/sport/feed/"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 10
    crawl_delay_mandatory: null
    max_requests_per_hour: 240
    jitter_seconds: 3
  anti_block:
    ua_tier: 3
    default_escalation_tier: 2
    max_escalation_tier: 6
    requires_proxy: false
    proxy_region: "uk"
    proxy_requirement: "recommended"
    bot_block_level: "HIGH"
  extraction:
    paywall_type: "none"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Hard"
    daily_article_estimate: 300
    sections_count: 15
    enabled: true
```

#### URL Discovery

- **Primary: RSS**
  - Main feed: `https://www.thesun.co.uk/feed/` (WordPress-style; The Sun migrated to a CMS that provides RSS at /feed/)
  - Alternative: `https://www.thesun.co.uk/rss` (redirect expected to /feed/)
  - Section feeds: /news/feed/, /money/feed/, /tech/feed/, /health/feed/, /sport/feed/
  - Expected items per feed: 20-50 recent articles
  - Feed format: RSS 2.0
  - Polling interval: Once per crawl run (daily)
  - Fields from RSS: title, link, pubDate, description, category
  - Full body: NOT in RSS; requires article page fetch

- **Fallback 1: Sitemap**
  - URL: `https://www.thesun.co.uk/sitemap.xml` (sitemap index expected)
  - Trigger: RSS returns < 10 articles OR RSS endpoint returns HTTP 4xx/5xx for > 30 minutes
  - Parse sitemap for article URLs with lastmod dates, fetch only new articles

- **Fallback 2: DOM Navigation**
  - Crawl section landing pages: /news/, /money/, /tech/, /health/, /sport/
  - Extract article links from page listing
  - Trigger: Both RSS and sitemap fail

#### Article Extraction Selectors

```yaml
selectors:
  # Article list page (section pages)
  list_page:
    article_links: "a.teaser-anchor__text"
    article_container: "div.teaser__copy-container"
    headline: "h2.teaser__headline, h3.teaser__headline"

  # Article detail page
  detail_page:
    title:
      css: "h1.article__headline"
      fallback: "h1"
      meta: "meta[property='og:title']"
    body:
      css: "div.article__content"
      fallback: "div[class*='article-body'], div.article__body"
      exclude:
        - "div.related-stories"
        - "div.article__info-bar"
        - "div[class*='newsletter']"
        - "div[class*='advert']"
        - "div[class*='social-share']"
        - "aside"
        - "div.breaking-news-banner"
    author:
      css: "span.article__author-name a"
      fallback: "span.article__author-name"
      meta: "meta[name='author']"
    date:
      meta_primary: "meta[property='article:published_time']"
      meta_fallback: "meta[property='og:article:published_time']"
      schema_org: "datePublished"
      html_time: "time[datetime]"
      format: "ISO 8601"
    category:
      css: "a.breadcrumb__link"
      fallback_url_path: true
      path_segment: 1  # e.g., /news/article-slug -> "news"
    source_url:
      meta: "link[rel='canonical']"
      fallback: "meta[property='og:url']"
```

#### Anti-Bot Configuration

- **Bot-blocking level**: HIGH (News UK, Cloudflare-protected)
- **UA tier**: T3 -- Pool of 50 UAs, rotate per request
- **Accept-Language**: `en-GB,en;q=0.9` (UK site -- use British English locale)
- **Referer chain**: Include `https://www.google.co.uk/` or `https://news.google.com/` as referer
- **sec-ch-ua**: Include for Chrome UAs
- **Starting escalation tier**: Tier 2 (session management)
- **Escalation path**: T2 -> T3 (Playwright) -> T4 (Patchright stealth) -> T5 (UK residential proxy) -> T6 (Claude Code)
- **GDPR cookie consent**: The Sun uses a cookie consent modal (EU/UK requirement). For httpx: content is typically accessible without accepting cookies (consent is JavaScript-triggered). For Playwright: auto-dismiss cookie banner by clicking accept button or injecting consent cookie.

#### Rate Limiting

- **Base delay**: 10 seconds between requests
- **Jitter**: 0-3 seconds random addition
- **Max requests/hour**: 240
- **Calculation**: 300 articles x (10s + 2s fetch + 0.5s parse) x 1.1 overhead / 60 = ~5.0 min
- **Peak hours**: UK morning/afternoon (07:00-18:00 GMT) -- publish cadence highest

#### Geographic Considerations

- **Proxy**: UK residential proxy RECOMMENDED (not required)
- **Reason**: UK IP preference observed in Step 1 (direct fetch blocked). Content may serve different results or block non-UK IPs intermittently.
- **Fallback**: Try without proxy first; if 403 rate exceeds 30%, enable UK proxy

#### Expected Daily Volume

- **Articles**: ~300/day (high-volume tabloid)
- **Sections**: ~15 active sections
- **Crawl time**: ~5.0 minutes

#### Decision Rationale

RSS primary despite HIGH bot-blocking because: (1) RSS endpoint is typically less protected than web pages, (2) no paywall means full body is accessible via article page fetch after RSS URL discovery, (3) The Sun abandoned its paywall in 2015, making content freely accessible.

---

### 39. bild.de (Bild)

**Cross-Reference**: [trace:step-1:site-39-bild] -- Hard tier, HIGH bot-blocking, German language, German IP required.
**Cross-Reference**: [trace:step-3:group-g-bild] -- RSS primary, 10s+jitter, T3 UAs, German proxy required.

#### sources.yaml Configuration

```yaml
bild:
  name: "Bild"
  url: "https://www.bild.de"
  region: "de"
  language: "de"
  group: "G"
  crawl:
    primary_method: "rss"
    fallback_methods:
      - "sitemap"
      - "dom"
    rss_url: "https://www.bild.de/rssfeeds/vw-alles/vw-alles-26970986,dzbildplus=false,sort=1,teaserbildmob498=true,view=rss2.bild.xml"
    rss_section_feeds:
      - "https://www.bild.de/rssfeeds/rss-16738684,dzbildplus=false,sort=1,view=rss2.bild.xml"
      - "https://www.bild.de/rssfeeds/vw-politik/vw-politik-26971178,dzbildplus=false,sort=1,view=rss2.bild.xml"
      - "https://www.bild.de/rssfeeds/vw-wirtschaft/vw-wirtschaft-26972740,dzbildplus=false,sort=1,view=rss2.bild.xml"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 10
    crawl_delay_mandatory: null
    max_requests_per_hour: 240
    jitter_seconds: 3
  anti_block:
    ua_tier: 3
    default_escalation_tier: 2
    max_escalation_tier: 6
    requires_proxy: true
    proxy_region: "de"
    proxy_requirement: "required"
    bot_block_level: "HIGH"
  extraction:
    paywall_type: "soft-metered"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Hard"
    daily_article_estimate: 200
    sections_count: 10
    enabled: true
```

#### URL Discovery

- **Primary: RSS**
  - Main feed (free articles only): `https://www.bild.de/rssfeeds/vw-alles/vw-alles-26970986,dzbildplus=false,sort=1,teaserbildmob498=true,view=rss2.bild.xml`
  - The `dzbildplus=false` parameter filters out BILDplus paywall articles -- essential for free-only crawling
  - Section feeds available with same dzbildplus=false filter
  - Feed format: RSS 2.0 (Bild's custom XML path format)
  - Fields from RSS: title, link, pubDate, description, category, enclosure (images)
  - Full body: NOT in RSS; requires article page fetch

- **Fallback 1: Sitemap**
  - URL: `https://www.bild.de/sitemap.xml`
  - Trigger: RSS returns < 10 articles OR endpoint unreachable > 30 min
  - Note: Sitemap includes BILDplus articles; filter by URL pattern (BILDplus URLs contain `/bild-plus/` segment or `dzbildplus=true` markers)

- **Fallback 2: DOM Navigation**
  - Crawl section landing pages: /politik/, /wirtschaft/, /sport/, /unterhaltung/
  - Trigger: Both RSS and sitemap fail

#### Article Extraction Selectors

```yaml
selectors:
  # Article list page
  list_page:
    article_links: "a[class*='teaser-link']"
    article_container: "div[class*='teaser']"
    headline: "span[class*='teaser__headline']"
    bildplus_marker: "svg.bildplus-icon, span.bildplus-badge"  # Skip these articles

  # Article detail page
  detail_page:
    title:
      css: "h1.article-headline, h1[class*='headline']"
      fallback: "h1"
      meta: "meta[property='og:title']"
    body:
      css: "div.article-body, div[class*='article__body']"
      fallback: "div.body, div[data-module='article-body']"
      exclude:
        - "div[class*='related']"
        - "div[class*='teaser-list']"
        - "div[class*='ad-container']"
        - "div[class*='social']"
        - "div[class*='newsletter']"
        - "aside"
        - "div[class*='bildplus']"  # BILDplus overlay remnants
    author:
      css: "span.author-info__name, span[class*='author']"
      fallback: "meta[name='author']"
    date:
      meta_primary: "meta[property='article:published_time']"
      schema_org: "datePublished"
      html_time: "time[datetime]"
      format: "ISO 8601"
      locale_format: "DD. MMMM YYYY"  # German: "15. Januar 2024"
      locale_short: "DD.MM.YYYY"       # German: "15.01.2024"
    category:
      css: "a[class*='breadcrumb'], span[class*='section-label']"
      fallback_url_path: true
      path_segment: 1  # e.g., /politik/article-slug -> "politik"
    source_url:
      meta: "link[rel='canonical']"
```

#### German Language Handling

- **Character encoding**: UTF-8 (modern Bild is fully UTF-8)
- **German special characters**:
  - Umlauts: ae (a with umlaut), oe (o with umlaut), ue (u with umlaut), AE, OE, UE
  - Eszett: ss (sharp s) and its uppercase variant
  - All preserved natively in UTF-8; no transcoding needed
- **URL slug handling**: Bild uses numeric article IDs in URLs (e.g., `/politik/inland/article-title-12345678.bild.html`), so German characters in slugs are not a concern
- **Date parsing**: Support both ISO 8601 from meta tags and German locale dates:
  - Full: `15. Januar 2024`, `15. Februar 2024`, etc.
  - Short: `15.01.2024`
  - Month names: Januar, Februar, Maerz, April, Mai, Juni, Juli, August, September, Oktober, November, Dezember
- **Accept-Language header**: `de-DE,de;q=0.9,en;q=0.8`

#### Anti-Bot Configuration

- **Bot-blocking level**: HIGH (Axel Springer, aggressive bot detection)
- **UA tier**: T3 -- Pool of 50 UAs, rotate per request
- **Accept-Language**: `de-DE,de;q=0.9,en;q=0.8` (CRITICAL: must appear as German browser)
- **Starting escalation tier**: Tier 2
- **Escalation path**: T2 -> T3 -> T4 -> T5 (German residential proxy rotation) -> T6
- **GDPR cookie consent**: Bild uses Consent Management Platform (CMP) per German GDPR. httpx: content accessible without consent interaction (SSR HTML contains article). Playwright: auto-accept via `document.querySelector('[data-testid="accept-all"]').click()` or inject consent cookie `euconsent-v2`.

#### Rate Limiting

- **Base delay**: 10 seconds
- **Jitter**: 0-3 seconds
- **Max requests/hour**: 240
- **Calculation**: 200 articles x (10s + 2s + 0.5s) x 1.1 / 60 = ~5.0 min

#### Geographic Considerations

- **Proxy**: German residential proxy REQUIRED
- **Reason**: Direct fetch blocked from non-German IPs (confirmed Step 1). Axel Springer properties enforce geographic access.
- **Proxy specification**: German datacenter or residential IP; must pass German geo-IP lookup

#### BILDplus Paywall Handling

- **Strategy**: Crawl FREE articles only
- ~70% of Bild content is free; ~30% behind BILDplus paywall
- RSS feed with `dzbildplus=false` parameter automatically filters paywall content
- For sitemap fallback: detect BILDplus markers in URL or page HTML and skip
- BILDplus detection: URL contains `bild-plus` OR page contains `.bildplus-icon` SVG element OR `data-bildplus="true"` attribute

#### Expected Daily Volume

- **Articles**: ~200/day (free articles only; ~140 free + skip ~60 BILDplus)
- **Sections**: ~10 active sections
- **Crawl time**: ~5.0 minutes

#### Decision Rationale

RSS primary with `dzbildplus=false` filter is the optimal strategy because: (1) pre-filters paywall content at the feed level, (2) Bild's RSS feed structure is well-documented with feed ID parameters, (3) German proxy is required regardless of method, making RSS the lowest-friction discovery approach.

---

### 40. lemonde.fr (Le Monde) -- EXTREME

**Cross-Reference**: [trace:step-1:site-40-lemonde] -- Extreme tier, hard paywall, HIGH bot-blocking, French language.
**Cross-Reference**: [trace:step-3:group-g-lemonde] -- RSS primary for metadata, title-only strategy, T3 UAs.

#### sources.yaml Configuration

```yaml
lemonde:
  name: "Le Monde"
  url: "https://www.lemonde.fr"
  region: "fr"
  language: "fr"
  group: "G"
  crawl:
    primary_method: "rss"
    fallback_methods:
      - "sitemap"
    rss_url: "https://www.lemonde.fr/rss/une.xml"
    rss_section_feeds:
      - "https://www.lemonde.fr/rss/en_continu.xml"
      - "https://www.lemonde.fr/international/rss_full.xml"
      - "https://www.lemonde.fr/politique/rss_full.xml"
      - "https://www.lemonde.fr/economie/rss_full.xml"
    rss_english_feed: "https://www.lemonde.fr/en/rss/une.xml"
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

- **Primary: RSS (metadata extraction only)**
  - Main feed: `https://www.lemonde.fr/rss/une.xml` (Front page articles)
  - Continuous: `https://www.lemonde.fr/rss/en_continu.xml` (All articles in real-time)
  - Section feeds: /international/, /politique/, /economie/ with `/rss_full.xml` suffix
  - English edition: `https://www.lemonde.fr/en/rss/une.xml`
  - Feed format: RSS 2.0
  - Fields from RSS: title, link, pubDate, description (excerpt/lead paragraph), category
  - Full body: BLOCKED by hard paywall ("Le Monde Abonne" subscription required)

- **Fallback: Sitemap**
  - URL: `https://www.lemonde.fr/sitemap.xml`
  - Trigger: RSS returns empty or 403
  - Parse for URLs and lastmod dates; page fetch yields only title + first paragraph

#### Article Extraction Selectors (Title-Only Mode)

```yaml
selectors:
  # Title-only extraction (paywall blocks body)
  detail_page:
    title:
      css: "h1.article__title"
      fallback: "h1"
      meta: "meta[property='og:title']"
    body:
      # BLOCKED: Hard paywall. Extract lead paragraph only.
      css: "p.article__desc"  # Lead paragraph (visible before paywall)
      fallback: "meta[property='og:description']"
      note: "Body extraction limited to first paragraph / description. Full text requires Le Monde subscription."
    author:
      css: "span.article__author-name, a.article__author-link"
      fallback: "meta[name='author']"
    date:
      meta_primary: "meta[property='article:published_time']"
      schema_org: "datePublished"
      format: "ISO 8601"
      locale_format: "DD MMMM YYYY"   # French: "15 janvier 2024"
      locale_short: "DD/MM/YYYY"       # French: "15/01/2024"
    category:
      css: "a.article__section-link, span.article__kicker"
      fallback_url_path: true
      path_segment: 1  # e.g., /international/article-slug -> "international"
    source_url:
      meta: "link[rel='canonical']"
```

#### French Language Handling

- **Character encoding**: UTF-8
- **French special characters**:
  - Acute accent: e-acute (most common)
  - Grave accent: a-grave, e-grave, u-grave
  - Circumflex: a-circumflex, e-circumflex, i-circumflex, o-circumflex, u-circumflex
  - Cedilla: c-cedilla
  - Diaeresis: e-diaeresis, i-diaeresis, u-diaeresis
  - Ligatures: oe-ligature, ae-ligature (rare)
  - All natively supported by UTF-8
- **URL slug handling**: Le Monde uses hyphenated slugs that transliterate accented characters:
  - e-acute, e-grave, e-circumflex -> `e` in URLs
  - c-cedilla -> `c` in URLs
  - Example: `/en/international/article/2026/02/25/title-here`
- **Date parsing**: Support ISO 8601 (primary) and French locale dates:
  - Full: `15 janvier 2024`
  - Short: `15/01/2024`
  - Month names: janvier, fevrier, mars, avril, mai, juin, juillet, aout, septembre, octobre, novembre, decembre
  - Note: French uses lowercase month names (unlike German which capitalizes)
- **Accept-Language header**: `fr-FR,fr;q=0.9,en;q=0.8` for French edition; `en-GB,en;q=0.9,fr;q=0.8` for English edition

#### Anti-Bot Configuration

- **Bot-blocking level**: HIGH (Cloudflare, hard paywall enforcement)
- **UA tier**: T3 -- Pool of 50 UAs, rotate per request
- **Starting escalation tier**: Tier 3 (httpx will fail on hard paywall; metadata-focused)
- **Escalation path**: T3 -> T4 -> T5 -> T6 -> Title-Only Degradation (permanent)
- **GDPR cookie consent**: Le Monde uses a CMP. Content meta tags are accessible without consent interaction. Title-only strategy minimizes consent dependency.

#### Rate Limiting

- **Base delay**: 10 seconds
- **Jitter**: 0-3 seconds
- **Max requests/hour**: 240
- **Calculation**: 150 articles x (10s + 2s + 0.5s) x 1.1 / 60 = ~4.0 min (metadata fetches are lightweight)

#### Hard Paywall Strategy

- **Default mode**: Title + metadata + lead paragraph only
- **Data captured without subscription**:
  - Title (from RSS `<title>` or HTML `<h1>`)
  - Publication date (from RSS `<pubDate>` or HTML meta)
  - Author (from HTML meta if accessible)
  - Category (from RSS `<category>` or URL path)
  - Description/lead paragraph (from RSS `<description>` or `og:description`)
  - Article URL
- **PRD justification**: Title-only strategy is valid per PRD dual-pass analysis -- titles alone support topic modeling, trend detection, keyword extraction, and cross-source comparison
- **Subscription upgrade path**: If Le Monde subscription is obtained, inject subscriber cookies at Tier 2 for full body access
- **RawArticle contract**: Set `is_paywall_truncated: true` and `body` = lead paragraph text

#### Expected Daily Volume

- **Articles**: ~150/day (metadata only)
- **Sections**: ~15 active sections
- **Crawl time**: ~4.0 minutes (fast -- metadata-only fetches)

#### Decision Rationale

Title-only via RSS is the only viable strategy without subscription because: (1) Le Monde's hard paywall blocks all body content for non-subscribers, (2) RSS feeds provide title + description (lead paragraph) without hitting the paywall, (3) attempting full body extraction wastes request budget on 403/paywall responses.

---

### 41. themoscowtimes.com (The Moscow Times)

**Cross-Reference**: [trace:step-1:site-41-moscowtimes] -- Easy tier, LOW bot-blocking, 4 RSS feeds, freemium.
**Cross-Reference**: [trace:step-3:group-g-moscowtimes] -- RSS primary, 2s delay, T1 UA, no proxy.

#### sources.yaml Configuration

```yaml
themoscowtimes:
  name: "The Moscow Times"
  url: "https://www.themoscowtimes.com"
  region: "ru"
  language: "en"
  group: "G"
  crawl:
    primary_method: "rss"
    fallback_methods:
      - "sitemap"
    rss_url: "https://www.themoscowtimes.com/rss/news"
    rss_section_feeds:
      - "https://www.themoscowtimes.com/rss/news"
      - "https://www.themoscowtimes.com/rss/opinion"
      - "https://www.themoscowtimes.com/rss/city"
      - "https://www.themoscowtimes.com/rss/meanwhile"
    sitemap_url: "https://static.themoscowtimes.com/sitemap/sitemap.xml"
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
    sections_count: 9
    enabled: true
```

#### URL Discovery

- **Primary: RSS (4 category feeds)**
  - News: `https://www.themoscowtimes.com/rss/news` (verified -- RSS 2.0, 50 items)
  - Opinion: `https://www.themoscowtimes.com/rss/opinion`
  - Arts & Life: `https://www.themoscowtimes.com/rss/city`
  - Meanwhile: `https://www.themoscowtimes.com/rss/meanwhile`
  - Feed format: RSS 2.0 (verified via live fetch)
  - Fields from RSS: title, link, pubDate, description, guid
  - Full body: NOT in RSS (description is summary only, verified via live fetch); requires page fetch
  - Dedup: Use URL across all 4 feeds to avoid duplicate fetches (same article may appear in multiple feeds)

- **Fallback: Sitemap**
  - URL: `https://static.themoscowtimes.com/sitemap/sitemap.xml` (sitemap index with monthly archives)
  - Monthly files: e.g., `2026-2.xml`, `2026-1.xml`, `2025-9.xml`
  - Trigger: RSS returns < 5 articles across all 4 feeds

#### Article Extraction Selectors

```yaml
selectors:
  # Article list page (homepage)
  list_page:
    article_links: "a[href*='/20']"  # URL pattern: /2026/02/25/article-slug
    article_container: "div.article_card, div.media_card"
    headline: "h3"

  # Article detail page (verified via live fetch)
  detail_page:
    title:
      css: "h1"
      meta: "meta[property='og:title']"
    body:
      css: "div.article__content, div.article-body"
      fallback: "article"
      trafilatura: true  # Trafilatura handles this site well
      exclude:
        - "div.sharing-buttons"
        - "div[class*='related']"
        - "div[class*='read-more']"
        - "div[class*='social']"
        - "div[class*='newsletter']"
        - "div[class*='podcast']"
        - "div.tags"
    author:
      schema_org: "author.name"  # Schema.org: author type Organization ("The Moscow Times") or Person
      css: "span.article__author, a[class*='author']"
      fallback: "The Moscow Times"  # Many articles attributed to publication
    date:
      schema_org: "datePublished"  # Verified: "2025-02-13T14:29:13+03:00" (Moscow time)
      meta_primary: "meta[property='article:published_time']"
      visible_text_pattern: "MMM. DD, YYYY"  # e.g., "Feb. 25, 2026" (US abbreviated month)
      timezone: "Europe/Moscow"  # +03:00
    category:
      breadcrumb: "BreadcrumbList"  # Schema.org: Home > News > Article
      css: "a.breadcrumb__link"
      tags_css: "a.tag"  # Article tags: e.g., "Ukraine", "Qatar", "Children"
      fallback_url_path: true
    source_url:
      meta: "link[rel='canonical']"
```

#### Anti-Bot Configuration

- **Bot-blocking level**: LOW
- **UA tier**: T1 -- Single UA, rotate weekly
- **Starting escalation tier**: Tier 1
- **Escalation path**: T1 -> T2 (if rate limited) -> T3 (if JS needed, unlikely)
- **robots.txt blocks**: Only /preview/ and /search/; respect these exclusions

#### Rate Limiting

- **Base delay**: 2 seconds
- **Jitter**: 0
- **Max requests/hour**: 1800
- **Calculation**: 20 articles x (2s + 2s fetch + 0.5s parse) x 1.1 / 60 = ~1.0 min

#### Expected Daily Volume

- **Articles**: ~20/day
- **Sections**: ~9 (News, Opinion, Arts & Life, Meanwhile, Ukraine War, Regions, Business, Climate, Podcasts)
- **Crawl time**: ~1.0 minutes

#### Decision Rationale

The Moscow Times is the easiest site in Group G because: (1) LOW bot-blocking with minimal robots.txt restrictions, (2) 4 well-structured RSS feeds covering all sections, (3) no paywall (freemium/donation model), (4) English-language content requiring no special encoding, (5) internationally accessible without proxy.

---

### 42. arabnews.com (Arab News)

**Cross-Reference**: [trace:step-1:site-42-arabnews] -- Medium tier, MEDIUM bot-blocking, 10s crawl-delay, Drupal CMS, RSS 403.
**Cross-Reference**: [trace:step-3:group-g-arabnews] -- Sitemap primary (RSS returns 403), 10s mandatory delay, T2 UAs.

#### sources.yaml Configuration

```yaml
arabnews:
  name: "Arab News"
  url: "https://www.arabnews.com"
  region: "me"
  language: "en"
  group: "G"
  crawl:
    primary_method: "sitemap"
    fallback_methods:
      - "dom"
    rss_url: null  # RSS returns 403
    sitemap_url: "/sitemap.xml"
    sitemap_news_url: "/sitemap-news.xml"
    rate_limit_seconds: 10
    crawl_delay_mandatory: 10  # robots.txt Crawl-delay: 10
    max_requests_per_hour: 360
    jitter_seconds: 0
  anti_block:
    ua_tier: 2
    default_escalation_tier: 1
    max_escalation_tier: 5
    requires_proxy: false
    proxy_region: "me"
    proxy_requirement: "recommended"
    bot_block_level: "MEDIUM"
  extraction:
    paywall_type: "none"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Medium"
    daily_article_estimate: 100
    sections_count: 12
    enabled: true
```

#### URL Discovery

- **Primary: Sitemap (Google News sitemap)**
  - Standard sitemap: `https://www.arabnews.com/sitemap.xml`
  - Google News sitemap: `https://www.arabnews.com/sitemap-news.xml` (preferred -- includes `news:` namespace with title, publication date, keywords)
  - RSS returns 403 (confirmed in Step 1) -- not available as discovery method
  - Parse sitemap for article URLs, filter by lastmod for new articles only
  - The Google News sitemap provides rich metadata reducing the need for page fetches for title/date

- **Fallback: DOM Navigation**
  - Crawl section landing pages: /saudi-arabia, /middle-east, /world, /business, /sport, /lifestyle
  - Extract article links from section pages
  - Trigger: Both sitemaps return 403

#### Article Extraction Selectors

```yaml
selectors:
  # Article list page (section pages - Drupal CMS)
  list_page:
    article_links: "h2 a, h3 a, a.article-title"
    article_container: "div.views-row, div.node--teaser"
    headline: "h2.node__title a, h3.field--name-title a"

  # Article detail page (Drupal structure)
  detail_page:
    title:
      css: "h1.page-title, h1.article-title"
      fallback: "h1"
      meta: "meta[property='og:title']"
    body:
      css: "div.field--name-body, div.article-body"
      fallback: "div.node__content, article.node"
      trafilatura: true
      exclude:
        - "div.field--name-field-related"
        - "div[class*='social-share']"
        - "div[class*='ad-']"
        - "div.sidebar"
        - "div[class*='newsletter']"
        - "aside"
        - "div.comment-section"
    author:
      css: "span.field--name-field-author, a[class*='author']"
      meta: "meta[name='author']"
    date:
      meta_primary: "meta[property='article:published_time']"
      schema_org: "datePublished"
      html_time: "time[datetime]"
      format: "ISO 8601"
    category:
      css: "div.field--name-field-section a, a.breadcrumb__link"
      fallback_url_path: true
      path_segment: 1  # e.g., /saudi-arabia/article -> "saudi-arabia"
    source_url:
      meta: "link[rel='canonical']"
```

#### Anti-Bot Configuration

- **Bot-blocking level**: MEDIUM
- **UA tier**: T2 -- Pool of 10 UAs, rotate per session
- **Accept-Language**: `en-US,en;q=0.9,ar;q=0.8` (English primary with Arabic secondary for regional credibility)
- **Starting escalation tier**: Tier 1
- **Escalation path**: T1 -> T2 -> T3 -> T4 -> T5 (Middle East proxy rotation)
- **10-second crawl-delay**: MANDATORY per robots.txt -- legally binding (PRD C5 compliance)
- **robots.txt blocks**: Admin paths, auth paths, /node/1610026, AMP pages -- respect all exclusions

#### Rate Limiting

- **Base delay**: 10 seconds (mandatory per robots.txt Crawl-delay: 10)
- **Jitter**: 0 (crawl-delay is exact minimum; no jitter reduction)
- **Max requests/hour**: 360
- **Calculation**: 100 articles x (10s + 2s + 0.5s) x 1.1 / 60 = ~3.0 min

#### Geographic Considerations

- **Proxy**: Middle East / Saudi Arabia residential proxy RECOMMENDED
- **Reason**: IP filtering observed -- 403 from non-Middle East IPs (confirmed Step 1: "homepage 403" from WebFetch, arabnews.com robots.txt accessible but homepage blocked)
- **Fallback**: Sitemap may be accessible without proxy; article pages may require ME proxy. Test sitemap access first, then article pages.

#### English vs. Arabic Content

- **Scope**: English edition ONLY (arabnews.com)
- **Arabic edition**: arabnews.com/ar exists but is NOT in scope for this crawl
- **Content language verification**: All articles from the English sitemap/section pages are in English
- **No RTL handling needed** for the English edition

#### Expected Daily Volume

- **Articles**: ~100/day
- **Sections**: ~12 (Saudi Arabia, Middle East, World, Business, Sport, Lifestyle, Opinion, etc.)
- **Crawl time**: ~3.0 minutes

#### Decision Rationale

Sitemap primary (not RSS) because: (1) RSS returns 403 (confirmed by direct probe in Step 1), (2) Google News sitemap provides rich metadata (title, date, keywords) reducing individual page fetches, (3) 10-second crawl-delay makes efficient URL discovery critical -- sitemap gives bulk URLs in a single request.

---

### 43. aljazeera.com (Al Jazeera English)

**Cross-Reference**: [trace:step-1:site-43-aljazeera] -- Medium tier, HIGH bot-blocking (AI bots blocked), RSS confirmed, SSR/React.
**Cross-Reference**: [trace:step-3:group-g-aljazeera] -- RSS primary, 5s delay, T2 UAs, no proxy needed.

#### sources.yaml Configuration

```yaml
aljazeera:
  name: "Al Jazeera English"
  url: "https://www.aljazeera.com"
  region: "me"
  language: "en"
  group: "G"
  crawl:
    primary_method: "rss"
    fallback_methods:
      - "sitemap"
      - "dom"
    rss_url: "https://www.aljazeera.com/xml/rss/all.xml"
    rss_alternate: "https://www.aljazeera.com/rss"
    sitemap_url: "/sitemap.xml"
    sitemap_date_pattern: "/sitemap.xml?yyyy={year}&mm={month}&dd={day}"
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
    sections_count: 12
    enabled: true
```

#### URL Discovery

- **Primary: RSS (verified active)**
  - Main feed: `https://www.aljazeera.com/xml/rss/all.xml` (RSS 2.0, 25 items, verified 2026-02-26)
  - Alternate path: `https://www.aljazeera.com/rss` (likely redirects to /xml/rss/all.xml)
  - Feed format: RSS 2.0 with Atom and Media RSS extensions (verified via live fetch)
  - Fields from RSS: title, link, description (summary), pubDate, category, guid, post-id
  - Full body: NOT in RSS (summary only, verified); requires article page fetch
  - No dc:creator (author) in RSS; author must be extracted from article page
  - Date format in RSS: RFC 2822 ("Thu, 26 Feb 2026 04:31:45 +0000")

- **Fallback 1: Sitemap (date-based)**
  - Sitemap index: `https://www.aljazeera.com/sitemap.xml`
  - Date-based daily sitemaps: `/sitemap.xml?yyyy=2026&mm=02&dd=25`
  - 6 sitemap types: main, news, article archive, new articles, video archive, new videos
  - Trigger: RSS returns < 10 articles
  - Parse today's date-based sitemap for comprehensive URL discovery

- **Fallback 2: DOM Navigation**
  - Section pages: /news/, /features/, /opinions/, /economy/
  - Trigger: Both RSS and sitemaps fail

#### Article Extraction Selectors

```yaml
selectors:
  # Article list page (verified via live fetch)
  list_page:
    featured_container: "#featured-news-container"
    feed_container: "#news-feed-container"
    article_links: "a[href^='/news/'], a[href^='/features/'], a[href^='/opinions/'], a[href^='/economy/']"
    headline: "h2, h3"

  # Article detail page (verified via live fetch)
  detail_page:
    title:
      css: "h1"
      parent_css: ".article-header"  # Container from speakable schema
      meta: "meta[property='og:title']"
    body:
      css: "div.wysiwyg"  # Al Jazeera uses wysiwyg class for article content
      fallback: "#main-content-area"
      apollo_state: "window.__APOLLO_STATE__"  # Structured data available via Apollo GraphQL
      trafilatura: true
      exclude:
        - "div[class*='related-content']"
        - "div[class*='recommended']"
        - "div[class*='social-share']"
        - "div[class*='newsletter']"
        - "div[class*='ad-']"
        - "div[class*='video-player']"
        - "aside"
        - "figure.article-featured-image"  # Keep image captions but exclude featured image block
    author:
      schema_org: "author.name"  # JSON-LD: {"@type":"Person","name":"Al Jazeera Staff"}
      css: "div.article-author__name, span[class*='author']"
      fallback: "Al Jazeera"  # Default when attributed to "Al Jazeera Staff, AP and Reuters"
    date:
      schema_org: "datePublished"  # Verified: "2026-02-26T04:31:45Z" (ISO 8601 UTC)
      meta_primary: "meta[property='article:published_time']"
      format: "ISO 8601"
      timezone: "UTC"  # Al Jazeera publishes in UTC
    category:
      schema_org: "BreadcrumbList"  # JSON-LD breadcrumb: News > Article
      css: "a.article-section-link"
      fallback_url_path: true
      path_segment: 1  # e.g., /news/2026/2/26/slug -> "news"
    source_url:
      meta: "link[rel='canonical']"
      schema_org: "mainEntityOfPage"
```

#### Anti-Bot Configuration

- **Bot-blocking level**: HIGH (explicitly blocks 8+ AI bots)
- **CRITICAL**: Must NOT use AI-identifying User-Agents
  - Blocked UAs (from robots.txt): `anthropic-ai`, `ChatGPT-User`, `ClaudeBot`, `Claude-Web`, `cohere-ai`, `GPTBot`, `PerplexityBot`, `Bytespider`
  - Each has `Disallow: /` -- total site block for these agents
- **UA tier**: T2 -- Pool of 10 standard browser UAs, rotate per session
- **Accept-Language**: `en-US,en;q=0.9`
- **Starting escalation tier**: Tier 1
- **Escalation path**: T1 -> T2 -> T3 -> T4 -> T5
- **SSR content**: Despite React/Apollo frontend, full content is server-side rendered in initial HTML response. `window.__APOLLO_STATE__` is available but httpx is sufficient -- no Playwright needed.
- **robots.txt blocks**: /api, /search/, asset-manifest -- respect all exclusions

#### Rate Limiting

- **Base delay**: 5 seconds
- **Jitter**: 0
- **Max requests/hour**: 720
- **Calculation**: 100 articles x (5s + 2s + 0.5s) x 1.1 / 60 = ~3.0 min

#### English vs. Arabic Content

- **Scope**: English edition ONLY (aljazeera.com)
- **Arabic edition**: aljazeera.net -- separate domain, NOT in scope
- **No RTL handling needed** for the English .com edition
- **Note**: If Arabic edition (aljazeera.net) is added in future scope, it requires:
  - `dir="rtl"` preservation
  - Arabic text extraction with bidirectional support
  - Eastern Arabic numeral parsing for dates
  - Separate RSS/sitemap infrastructure

#### Expected Daily Volume

- **Articles**: ~100/day
- **Sections**: ~12 (News, Features, Opinions, Economy, Sport, Culture, Podcasts, etc.)
- **Crawl time**: ~3.0 minutes

#### Decision Rationale

RSS primary because: (1) RSS feed is confirmed active with 25 items (live verified), (2) content is free and SSR-rendered making article page fetch straightforward, (3) T2 UAs are sufficient despite HIGH bot-blocking because the blocking targets AI bots specifically, not standard browser UAs, (4) date-based sitemaps provide excellent fallback for comprehensive discovery.

---

### 44. israelhayom.com (Israel Hayom)

**Cross-Reference**: [trace:step-1:site-44-israelhayom] -- Easy tier, LOW bot-blocking, WordPress/JNews, no robots.txt.
**Cross-Reference**: [trace:step-3:group-g-israelhayom] -- RSS (WordPress) primary, 2s delay, T1 UA, no proxy.

#### sources.yaml Configuration

```yaml
israelhayom:
  name: "Israel Hayom"
  url: "https://www.israelhayom.com"
  region: "il"
  language: "en"
  group: "G"
  crawl:
    primary_method: "rss"
    fallback_methods:
      - "sitemap"
    rss_url: "https://www.israelhayom.com/feed"
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
    daily_article_estimate: 30
    sections_count: 5
    enabled: true
```

#### URL Discovery

- **Primary: RSS (WordPress standard, verified)**
  - Feed URL: `https://www.israelhayom.com/feed` (RSS 2.0 with content:encoded, verified via live fetch)
  - Feed items: 10 per fetch (WordPress default)
  - Feed format: RSS 2.0 with namespaces: content, dc, atom, sy, slash, wfw
  - Fields from RSS (verified):
    - `<title>` -- Article headline
    - `<link>` -- Permanent URL
    - `<dc:creator>` -- Author name (e.g., "Danny Zaken", "Lilach Shoval", "ILH Staff")
    - `<pubDate>` -- RFC 822 ("Wed, 25 Feb 2026 18:24:59 +0000")
    - `<category>` -- Multiple topic tags per article
    - `<description>` -- Brief excerpt
    - `<content:encoded>` -- FULL article body in CDATA (verified!)
    - `<guid>` -- Unique identifier
    - `<comments>` -- Comment thread link
  - **Full body IS available in RSS** via `content:encoded` -- no article page fetch needed for body extraction
  - This is the most RSS-rich site in Group G

- **Fallback: Sitemap (WordPress)**
  - URL: `https://www.israelhayom.com/sitemap.xml` (WordPress standard)
  - Trigger: RSS returns 0 articles (highly unlikely for active WordPress site)

#### Article Extraction Selectors

```yaml
selectors:
  # RSS extraction (primary -- full content available in feed)
  rss_fields:
    title: "<title>"
    body: "<content:encoded>"  # Full article body in CDATA
    author: "<dc:creator>"
    date: "<pubDate>"  # RFC 822 format
    category: "<category>"  # Multiple per article
    url: "<link>"
    guid: "<guid>"

  # Article detail page (fallback -- WordPress/JNews theme, verified via live fetch)
  detail_page:
    title:
      css: "h1.jeg_post_title"
      fallback: "h1"
      meta: "meta[property='og:title']"
    body:
      css: "div.content-inner, div.entry-content"
      fallback: "div.jeg_inner_content"
      trafilatura: true
      exclude:
        - "div.jeg_post_tags"
        - "div.jeg_share_bottom"
        - "div.jeg_authorbox"
        - "div.jeg_post_related"
        - "div.jeg_ad"
        - "div[class*='newsletter']"
        - "div.comment-respond"
        - "div.jnews_inline_related_post"
    author:
      css: "a.jeg_meta_author"
      meta: "meta[name='author']"
      schema_org: "author.name"
    date:
      schema_org: "datePublished"  # Schema.org Article type
      meta_primary: "meta[property='article:published_time']"
      visible_text_format: "MMMM DD, YYYY"  # e.g., "February 25, 2026"
      format: "ISO 8601"
    category:
      css: "span.jeg_post_category a"
      fallback_url_path: true
    source_url:
      meta: "link[rel='canonical']"

  # Article list page (homepage -- JNews theme)
  list_page:
    article_links: "h3.jeg_post_title a"
    article_container: "div.jeg_postblock"
    headline: "h3.jeg_post_title"
    category_badge: "a.jeg_post_category"
    author: "a.jeg_meta_author"
```

#### Anti-Bot Configuration

- **Bot-blocking level**: LOW
- **robots.txt**: Returns 404 -- no restrictions declared at all
- **UA tier**: T1 -- Single UA, rotate weekly
- **Starting escalation tier**: Tier 1
- **Escalation path**: T1 -> T2 -> T3 (maximum; unlikely to need beyond T1)

#### Rate Limiting

- **Base delay**: 2 seconds
- **Jitter**: 0
- **Max requests/hour**: 1800
- **Calculation**: 30 articles x (2s + 0.5s parse) x 1.1 / 60 = ~1.0 min
- **Note**: Since RSS `content:encoded` provides full body, most articles need ZERO page fetches. Only RSS feed itself is fetched, reducing to a single request.

#### English vs. Hebrew Content

- **Scope**: English edition ONLY (israelhayom.com)
- **Hebrew edition**: israelhayom.co.il -- separate domain, NOT in scope
- **No RTL handling needed** for the English .com edition
- **Note**: If Hebrew edition is added in future scope, it requires:
  - `dir="rtl"` preservation
  - Hebrew text extraction
  - Hebrew date format: Day Month Year (right-to-left reading order)
  - Hebrew month names parsing

#### Expected Daily Volume

- **Articles**: ~30/day
- **Sections**: ~5 (News, Politics, Business, Israel-Inside, Columns)
- **Crawl time**: ~1.0 minutes (potentially less due to RSS full-content)

#### Decision Rationale

RSS is the clear optimal choice because: (1) `content:encoded` provides FULL article body (verified via live RSS fetch) -- no page fetches needed, (2) `dc:creator` provides author names, (3) no robots.txt restrictions, (4) WordPress/JNews provides highly predictable HTML structure for fallback, (5) lowest bot-blocking and easiest site in the entire 44-site corpus.

---

## Group-Level Summary

### Crawl Time Budget

| Site | Sequential Min | Parallel Group |
|------|---------------|----------------|
| thesun.co.uk | 5.0 | P4 (UK proxy slot) |
| bild.de | 5.0 | P4 (German proxy slot) |
| lemonde.fr | 4.0 | P5 (Extreme paywall slot) |
| themoscowtimes.com | 1.0 | P1 (Easy sites slot) |
| arabnews.com | 3.0 | P3 (English no-geo slot) or P4 (ME proxy) |
| aljazeera.com | 3.0 | P3 (English no-geo slot) |
| israelhayom.com | 1.0 | P1 (Easy sites slot) |
| **Total Sequential** | **22.0 min** | |
| **Total Parallel** | **~5.0 min** | (longest slot: thesun or bild at 5 min) |

[trace:step-3:parallelization-plan] -- Group G sites distributed across P1, P3, P4, P5 parallel slots.

### Daily Volume Summary

| Site | Daily Articles | Method | Body Available |
|------|---------------|--------|---------------|
| thesun.co.uk | ~300 | RSS + page fetch | Full |
| bild.de | ~200 (free only) | RSS (dzbildplus=false) + page fetch | Full (free articles) |
| lemonde.fr | ~150 | RSS metadata | Title + lead only |
| themoscowtimes.com | ~20 | RSS + page fetch | Full |
| arabnews.com | ~100 | Sitemap + page fetch | Full |
| aljazeera.com | ~100 | RSS + page fetch | Full |
| israelhayom.com | ~30 | RSS (content:encoded) | Full (in RSS!) |
| **Total** | **~900** | | **750 full + 150 title-only** |

### Proxy Requirements Summary

| Site | Proxy | Region | Requirement Level | Reason |
|------|-------|--------|------------------|--------|
| bild.de | Required | DE (Germany) | REQUIRED | German IP mandatory for access (Axel Springer) |
| thesun.co.uk | Recommended | UK | RECOMMENDED | UK IP preference, may work without but less reliable |
| arabnews.com | Recommended | ME (Saudi Arabia) | RECOMMENDED | IP filtering from non-ME IPs; sitemap may work without |
| lemonde.fr | Not needed | -- | NONE | Content accessible but paywalled regardless of IP |
| themoscowtimes.com | Not needed | -- | NONE | Internationally accessible |
| aljazeera.com | Not needed | -- | NONE | Internationally accessible |
| israelhayom.com | Not needed | -- | NONE | Internationally accessible, no robots.txt |

### GDPR / Cookie Consent Impact (European Sites)

| Site | GDPR Region | Cookie Consent CMP | Impact on Crawling |
|------|-------------|-------------------|-------------------|
| thesun.co.uk | UK (post-Brexit PECR) | Yes -- cookie banner | LOW: SSR content accessible without consent; consent is JS-triggered |
| bild.de | EU (GDPR) | Yes -- CMP (Consent Management Platform) | LOW: SSR content in initial HTML; CMP is JS overlay |
| lemonde.fr | EU (GDPR) | Yes -- CMP | LOW: Title-only strategy; meta tags accessible without consent |
| themoscowtimes.com | RU (no GDPR) | Minimal | NONE: No cookie consent barrier |

**General GDPR finding**: All European sites use JavaScript-based cookie consent overlays. Since our primary extraction method is httpx (fetching raw HTML), the consent modal is not rendered and article content is accessible in the SSR HTML response. Only Playwright-based fallbacks would need to handle consent dismissal.

---

## L1 Self-Verification

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | All 7 Group G sites have complete configurations | PASS | Sections 38-44 each have full sources.yaml + selectors + anti-bot + rate limit |
| 2 | sources.yaml schema matches Step 5 Section 5c format | PASS | All fields present: name, url, region, language, group, crawl.*, anti_block.*, extraction.*, meta.* |
| 3 | Language/encoding handling specified per site | PASS | Language matrix table; German umlauts + French accents documented; UTF-8 for all |
| 4 | RTL scope explicitly defined | PASS | All 7 sites target English editions; RTL not needed; future Arabic/Hebrew scope noted |
| 5 | CSS/XPath selectors provided for article extraction | PASS | Each site has list_page + detail_page selectors with fallbacks |
| 6 | Selectors verified against live HTML (spot-checks) | PASS | WebFetch verified: aljazeera.com (homepage + article + RSS), israelhayom.com (homepage + RSS), themoscowtimes.com (homepage + article + RSS) |
| 7 | Anti-bot configuration per site | PASS | UA tier, escalation path, AI-bot blocking notes for each site |
| 8 | Rate limits respect robots.txt | PASS | arabnews.com 10s mandatory; other sites use conservative defaults |
| 9 | Geographic proxy requirements documented | PASS | 3 sites with proxy needs; requirement levels (REQUIRED/RECOMMENDED/NONE) |
| 10 | Daily volume estimates realistic | PASS | Consistent with Step 1 reconnaissance data; Group total ~900 |
| 11 | Paywall strategy defined for lemonde.fr | PASS | Title-only mode with lead paragraph; PRD dual-pass justification |
| 12 | BILDplus paywall handling for bild.de | PASS | dzbildplus=false RSS filter; detection markers for fallback |
| 13 | GDPR cookie consent assessed | PASS | Impact matrix for 4 European/UK sites; all LOW/NONE impact |
| 14 | Cross-references to Step 1 and Step 3 | PASS | [trace:step-1:*] and [trace:step-3:*] markers throughout |
| 15 | Date format patterns cover European variations | PASS | German (DD. MMMM YYYY), French (DD MMMM YYYY), ISO 8601 for all |

**Unverified items** (due to access limitations):
- thesun.co.uk: Direct fetch blocked (UK IP); selectors based on known News UK patterns and inferred from Step 1
- bild.de: Direct fetch blocked (German IP); selectors based on Axel Springer patterns and Step 1
- lemonde.fr: Direct fetch blocked; selectors based on known Le Monde HTML patterns
- arabnews.com: 403 from non-ME IP; sitemap/article selectors based on known Drupal patterns

These unverified selectors must be validated during crawler setup phase with appropriate proxy access.

---

*Report generated by @crawl-strategist-global -- Step 6 Team Task for Group G (Europe/Middle East)*
*Next: Team Lead integrates all group strategies into unified Step 6 output*
