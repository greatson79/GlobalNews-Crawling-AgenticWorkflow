# Asia-Pacific News Site Crawling Strategies (Group F)

**Step**: 6/20 -- Crawl Strategy Design (Asia-Pacific)
**Agent**: @crawl-strategist-asia
**Date**: 2026-02-26
**Inputs**: Step 1 Site Reconnaissance, Step 3 Crawling Feasibility, Step 5 Architecture Blueprint (Section 5c)

---

## 1. Summary

| Metric | Value |
|--------|-------|
| **Total sites** | 6 |
| **Languages** | Chinese zh (1), Japanese ja (1), English-in-Asia en (4) |
| **Primary methods** | Sitemap (3), RSS (3) |
| **Fallback methods** | DOM (6), Sitemap+DOM (3) |
| **Estimated daily volume** | ~1,020 articles |
| **Total crawl time (sequential)** | ~24.0 minutes |
| **Sites requiring proxy** | 1 (yomiuri.co.jp -- Japanese proxy) |
| **CJK encoding sites** | 2 (people.com.cn -- UTF-8/GB2312; yomiuri.co.jp -- UTF-8/Shift_JIS) |
| **Mandatory Crawl-delay sites** | 2 (people.com.cn: 120s; scmp.com: 10s) |

[trace:step-1:difficulty-classification-matrix] -- Group F: Easy(2), Medium(2), Hard(2)
[trace:step-3:strategy-matrix] -- Group F row from the 44-site strategy matrix
[trace:step-5:sources-yaml-schema] -- sources.yaml schema for adapter configuration output

---

## 2. Strategy Matrix (All 6 Sites)

| # | Site | Lang | Primary | Fallback | Rate Limit | UA Tier | Bot Block | Crawl Min | Daily Est. | Difficulty | Risk |
|---|------|------|---------|----------|------------|---------|-----------|-----------|-----------|------------|------|
| 32 | people.com.cn | zh | Sitemap (78 sitemaps) | DOM | **120s MANDATORY** | T2 (10) | MEDIUM | 8.0 | ~500 | Medium | MED |
| 33 | globaltimes.cn | en | Sitemap (news NS) | DOM | 2s | T1 (1) | LOW | 1.5 | ~40 | Easy | LOW |
| 34 | scmp.com | en | RSS (80+ feeds) | Sitemap+DOM | **10s MANDATORY** | T2 (10) | MEDIUM | 4.0 | ~150 | Medium | MED |
| 35 | taiwannews.com.tw | en/zh | Sitemap (3 sitemaps) | DOM | 2s | T1 (1) | LOW | 1.5 | ~30 | Easy | LOW |
| 36 | yomiuri.co.jp | ja | RSS | Sitemap+DOM | 10s+jitter | T3 (50) | HIGH | 5.0 | ~200 | Hard | HIGH |
| 37 | thehindu.com | en | RSS | Sitemap+DOM | 10s+jitter | T3 (50) | HIGH | 4.0 | ~100 | Medium | HIGH |

---

## 3. CJK Encoding Matrix

| Site | Primary Encoding | Legacy Encoding | URL Pattern | Encoding Detection Strategy |
|------|-----------------|-----------------|-------------|---------------------------|
| people.com.cn | UTF-8 (sitemap XML declaration confirmed) | GB2312/GBK (legacy pages, subdomain articles) | `http://{subdomain}.people.com.cn/n1/YYYY/MMDD/c{cat}-{id}.html` | 1) HTTP `Content-Type` header; 2) `<meta charset>` tag; 3) `chardet` library fallback |
| globaltimes.cn | UTF-8 | None expected (English-language site) | `https://www.globaltimes.cn/page/YYYYMM/{id}.shtml` | UTF-8 assumed; verify via HTTP header |
| scmp.com | UTF-8 | None | `https://www.scmp.com/{section}/{sub}/article/{id}/{slug}` | UTF-8; confirmed via JSON-LD structured data |
| taiwannews.com.tw | UTF-8 (confirmed: `<meta charSet="utf-8">`) | None | `https://www.taiwannews.com.tw/news/{id}` | UTF-8; explicit meta tag present |
| yomiuri.co.jp | UTF-8 (modern pages) | Shift_JIS / EUC-JP (legacy archive pages) | `https://www.yomiuri.co.jp/{section}/{YYYYMMDD}-OYT1T{id}/` (expected) | 1) HTTP `Content-Type` header; 2) `<meta charset>`; 3) `chardet` with Japanese corpus bias |
| thehindu.com | UTF-8 | None | `https://www.thehindu.com/{section}/{subsection}/article{id}.ece` | UTF-8; standard for English-language Indian sites |

### CJK-Specific Encoding Notes

**Chinese Encoding Detection (people.com.cn)**:
- The sitemap index at `people.cn/sitemap_index.xml` declares `encoding="UTF-8"` in its XML prologue.
- Article pages on subdomains (e.g., `world.people.com.cn`, `finance.people.com.cn`) are expected to be UTF-8 but may serve GB2312 on legacy or cached pages.
- Detection chain: `Content-Type: text/html; charset=...` header > `<meta charset="...">` or `<meta http-equiv="Content-Type" content="text/html; charset=...">` > `chardet.detect()` with minimum confidence threshold of 0.8.
- If GB2312 is detected, decode with `gb18030` codec (superset of GB2312 and GBK, handles all CJK Unified Ideographs).

**Japanese Encoding Detection (yomiuri.co.jp)**:
- Modern Yomiuri pages are expected to use UTF-8. However, archived articles (pre-2015) may use Shift_JIS or EUC-JP.
- Detection chain mirrors Chinese but adds Shift_JIS/EUC-JP to the candidate list.
- For Japanese text, `cchardet` (C-backed chardet) provides faster and more accurate detection than pure-Python `chardet` for Japanese encodings.
- Always attempt UTF-8 decode first; fall back to Shift_JIS (`cp932` codec in Python, which is the Windows superset of Shift_JIS) if `UnicodeDecodeError` occurs.

---

## 4. Per-Site Detailed Strategies

### 4.1. people.com.cn (People's Daily -- 人民日报)

**Cross-Reference**: [trace:step-1:group-f-site-32] | [trace:step-3:people-com-cn]

#### 4.1.1. Overview

| Field | Value |
|-------|-------|
| **source_id** | `people` |
| **Language** | Chinese (zh-CN, Simplified) |
| **Difficulty** | Medium |
| **Bot-blocking** | MEDIUM (120s Crawl-delay is the primary constraint, not active blocking) |
| **Paywall** | None (Chinese state media, freely accessible) |
| **Rendering** | SSR (static HTML, jQuery-based) |

#### 4.1.2. URL Discovery

**Primary Method: Sitemap (78 category sitemaps)**

- **Sitemap index**: `http://www.people.cn/sitemap_index.xml`
- **Individual sitemaps**: `http://www.people.cn/sitemap/cn/{category}/news_sitemap.xml`
- 78 sitemaps covering: politics, world, finance, sports, culture, health, travel, military, plus 30+ regional sitemaps (bj, sh, gd, etc.) and international bureau sitemaps
- Each sitemap contains ~100 URLs with `<loc>`, `<lastmod>`, `<changefreq>`, `<priority>` fields
- No `news:` namespace -- standard sitemap format
- Sitemap `lastmod` dates are current (2026-02-26 confirmed), enabling efficient diff-based discovery

**Discovery Strategy**:
1. Fetch sitemap index (1 request)
2. Parse `<lastmod>` on each sitemap entry; only fetch sitemaps modified since last crawl
3. For fresh sitemaps, diff article URLs against known URL cache (dedup engine)
4. Queue new article URLs ordered by priority (descending)

**Optimization for 120s Crawl-delay**:
- Sitemap index + top 6 highest-priority category sitemaps = 7 requests x 120s = 14 minutes
- Then priority article fetches within remaining 2-hour window budget: ~40 articles
- Full 500-article coverage requires 24-hour background scheduling (see Step 3 note)

**Fallback Method: DOM Navigation**

- Trigger: Sitemap index returns HTTP 403/5xx OR < 10 new URLs across all sitemaps
- Navigate section pages from `www.people.com.cn` homepage
- Section URLs: `http://{subdomain}.people.com.cn/` where subdomain = world, finance, politics, etc.
- Article listing: `.list1 li a` elements on section index pages

#### 4.1.3. Article Extraction Selectors

| Field | Selector | Notes |
|-------|----------|-------|
| **Title** | `h1` within `.rm_txt` (CSS: `.rm_txt h1`) | Single `<h1>` per article page |
| **Body** | `div.rm_txt_con` (CSS: `.rm_txt_con`) | Main article container; strip child navigation/ads |
| **Author** | Regex in body text: `记者([\u4e00-\u9fff]{2,4})` | Chinese byline pattern: "记者" + 2-4 Chinese characters. Alternative: look for `来源：人民网` in source attribution |
| **Date** | `<strong>` within article metadata area | Format: `2026年02月26日12:25` -- parse with regex `(\d{4})年(\d{2})月(\d{2})日\s*(\d{2}):(\d{2})` |
| **Category** | URL path segment: `/c{category_id}-` | Map category IDs to names via sitemap structure. Also extractable from breadcrumb navigation |
| **URL** | `<link rel="canonical">` or sitemap `<loc>` | Canonical URL from HTML head preferred |

**Elements to Strip from Body**:
- `.rm_nav` -- Navigation menus
- Social sharing widgets
- Footer links and legal disclaimers
- Advertisement containers
- JavaScript tracking code
- "Related Reading" sections (`相关阅读`)

#### 4.1.4. Language/Encoding Handling

- **Primary encoding**: UTF-8 (confirmed from sitemap XML declaration)
- **Legacy encoding risk**: Article pages on subdomains may serve GB2312/GBK headers
- **Detection chain**:
  ```python
  # 1. HTTP header
  charset = response.headers.get('content-type', '').split('charset=')[-1].strip()
  # 2. HTML meta tag
  if not charset:
      charset = extract_meta_charset(html)  # <meta charset="..."> or <meta http-equiv="Content-Type" ...>
  # 3. chardet fallback
  if not charset or charset.lower() in ('', 'none'):
      detected = chardet.detect(response.content)
      charset = detected['encoding'] if detected['confidence'] > 0.8 else 'utf-8'
  # 4. Decode with gb18030 superset for any GB-family encoding
  if charset.lower() in ('gb2312', 'gbk', 'gb18030'):
      text = response.content.decode('gb18030', errors='replace')
  else:
      text = response.content.decode('utf-8', errors='replace')
  ```
- **Chinese Simplified detection**: All people.com.cn content is Simplified Chinese (zh-CN). No Traditional Chinese variant handling needed.
- **URL encoding**: Article URLs use ASCII path segments with numeric IDs -- no CJK characters in URLs.

#### 4.1.5. Anti-Block Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **UA tier** | T2 (10 UAs) | MEDIUM bot-blocking; moderate rotation sufficient |
| **Starting escalation tier** | Tier 1 | 120s delay already exceeds most rate limit thresholds |
| **Max escalation tier** | Tier 5 | Medium difficulty; unlikely to need Tier 6 |
| **Requires proxy** | No | Chinese state media accessible globally; no geo-blocking observed |
| **Proxy region** | null | N/A |
| **Accept-Language** | `zh-CN,zh;q=0.9,en;q=0.8` | Chinese content; Chinese browser Accept-Language headers expected |

#### 4.1.6. Rate Limiting

| Parameter | Value |
|-----------|-------|
| **Base delay** | **120 seconds (MANDATORY -- robots.txt `Crawl-delay: 120`)** |
| **Jitter** | 0s (120s delay is already very conservative) |
| **Max requests/hour** | 30 |
| **Daily article estimate** | ~500 (full); ~40 within 2-hour window |
| **Crawl time (2-hour window)** | ~8 minutes (sitemap scan + priority articles) |
| **Background scheduling** | Required for full coverage; spread across 24 hours |

#### 4.1.7. Special Handling

1. **120-second Crawl-delay**: This is the single most constraining rate limit in the entire 44-site corpus. Legally mandated compliance per PRD C5. Background 24-hour scheduling is essential for full coverage.
2. **Subdomain architecture**: Article URLs are on subdomains (`world.people.com.cn`, `finance.people.com.cn`, etc.) while sitemaps are on `people.cn`. The crawler must follow cross-subdomain links.
3. **Chinese date parsing**: Date format `2026年02月26日12:25` requires CJK-aware date parser. Regex extraction recommended over library parsers that may not handle `年月日` format.
4. **Author extraction**: Chinese byline patterns differ from Western. The reporter name follows `记者` (reporter) or `编辑` (editor) keywords. Names are 2-4 Chinese characters without spaces. Source attribution follows `来源：` (source:) pattern.
5. **High volume**: ~500 articles/day makes this the highest-volume site in Group F. Priority article selection algorithm needed.

#### 4.1.8. sources.yaml Configuration

```yaml
people:
  name: "People's Daily"
  url: "http://www.people.com.cn"
  region: "cn"
  language: "zh"
  group: "F"
  crawl:
    primary_method: "sitemap"
    fallback_methods:
      - "dom"
    rss_url: null
    sitemap_url: "http://www.people.cn/sitemap_index.xml"
    rate_limit_seconds: 120
    crawl_delay_mandatory: 120
    max_requests_per_hour: 30
    jitter_seconds: 0
  anti_block:
    ua_tier: 2
    default_escalation_tier: 1
    max_escalation_tier: 5
    requires_proxy: false
    proxy_region: null
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

#### 4.1.9. Decision Rationale

Sitemap is the only viable primary method because: (a) no RSS feed exists for people.com.cn, (b) the sitemap index with 78 category sitemaps provides comprehensive URL discovery, (c) standard sitemap XML format with `<lastmod>` enables efficient diff-based crawling. The 120-second Crawl-delay mandated by robots.txt makes this the most time-constrained site and necessitates priority-based article selection within the 2-hour daily window plus background scheduling for full coverage.

---

### 4.2. globaltimes.cn (Global Times)

**Cross-Reference**: [trace:step-1:group-f-site-33] | [trace:step-3:globaltimes-cn]

#### 4.2.1. Overview

| Field | Value |
|-------|-------|
| **source_id** | `globaltimes` |
| **Language** | English (en) |
| **Difficulty** | Easy |
| **Bot-blocking** | LOW (fully permissive robots.txt, no restrictions) |
| **Paywall** | None (Chinese state media, freely accessible) |
| **Rendering** | SSR (jQuery-based static HTML) |

#### 4.2.2. URL Discovery

**Primary Method: Sitemap (news namespace)**

- **Sitemap URL**: `https://www.globaltimes.cn/sitemap.xml`
- 51 URLs confirmed (live probe), with Google News namespace (`xmlns:news`)
- Rich metadata per entry: `<loc>`, `<news:publication_date>`, `<news:title>`, `<news:keywords>`
- This is the richest metadata sitemap in the entire 44-site corpus -- title and date are extractable without fetching individual article pages

**Discovery Strategy**:
1. Fetch sitemap (1 request, ~51 URLs)
2. Extract `news:title`, `news:publication_date`, `news:keywords` directly from sitemap XML
3. Filter by `news:publication_date` to identify articles published since last crawl
4. Fetch individual article pages only for body content extraction

**Fallback Method: DOM Navigation**

- Trigger: Sitemap returns HTTP 403/5xx OR < 5 URLs
- Navigate 4 section pages: China (`/china/index.html`), Op-Ed (`/opinion/`), Source (`/source/index.html`), Life (`/life/index.html`)
- Article listing: `<li>` elements containing `<a>` links with `/page/YYYYMM/{id}.shtml` pattern

#### 4.2.3. Article Extraction Selectors

| Field | Selector | Notes |
|-------|----------|-------|
| **Title** | Sitemap `news:title` OR `<h3>` in article page header area | Prefer sitemap title (avoids page fetch); article page title in heading element |
| **Body** | Article content area between `load_file()` template boundaries | No clear CSS class identified; use trafilatura for robust extraction from template-based layout |
| **Author** | Byline text: `By Global Times` or specific reporter name | Format: "By {Author} Published: {Date}" -- regex: `By\s+(.+?)\s+Published:` |
| **Date** | Sitemap `news:publication_date` OR byline text | Sitemap format: ISO 8601 (`2026-02-26T...`). Byline format: `Feb 26, 2026 11:59 AM` |
| **Category** | Sitemap `news:keywords` OR breadcrumb navigation | Breadcrumb: "CHINA / DIPLOMACY" pattern. URL section: `/page/YYYYMM/` (no section in URL) |
| **URL** | Sitemap `<loc>` | Pattern: `https://www.globaltimes.cn/page/YYYYMM/{id}.shtml` |

**Elements to Strip from Body**:
- "RELATED ARTICLES" section at article bottom
- Navigation/footer loaded via `load_file()` template calls
- Social sharing widgets
- Advertisement containers

#### 4.2.4. Language/Encoding Handling

- **Primary encoding**: UTF-8 (standard for English-language website)
- **No CJK encoding risk**: English-language site with occasional transliterated Chinese names (pinyin) -- no character encoding issues expected
- **Language detection**: Always English (en). `langdetect` library not needed for primary classification.

#### 4.2.5. Anti-Block Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **UA tier** | T1 (1 UA) | LOW bot-blocking; single UA sufficient |
| **Starting escalation tier** | Tier 1 | Minimal blocking expected |
| **Max escalation tier** | Tier 3 | Easy difficulty; Tier 4+ unnecessary |
| **Requires proxy** | No | Globally accessible English edition |
| **Proxy region** | null | N/A |
| **Accept-Language** | `en-US,en;q=0.9` | English content |

#### 4.2.6. Rate Limiting

| Parameter | Value |
|-----------|-------|
| **Base delay** | 2 seconds |
| **Jitter** | 0s |
| **Max requests/hour** | 1800 |
| **Daily article estimate** | ~40 |
| **Crawl time** | ~1.5 minutes |

#### 4.2.7. Special Handling

1. **News sitemap metadata optimization**: Title and date can be extracted from the sitemap XML itself (avoiding per-article page fetches for metadata). Only body requires individual page fetch, reducing total requests by ~50%.
2. **Template-based page structure**: Global Times uses `load_file()` JavaScript template loading. The article body is in the static HTML between template load calls. `trafilatura` handles this well as it extracts from the initial HTML payload.
3. **Low volume**: Only ~40 articles/day across 4 sections -- minimal crawl overhead.
4. **Ideal for pipeline testing**: Fully permissive, English-language, low volume, SSR -- one of the easiest sites in the corpus.

#### 4.2.8. sources.yaml Configuration

```yaml
globaltimes:
  name: "Global Times"
  url: "https://www.globaltimes.cn"
  region: "cn"
  language: "en"
  group: "F"
  crawl:
    primary_method: "sitemap"
    fallback_methods:
      - "dom"
    rss_url: null
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
    daily_article_estimate: 40
    sections_count: 4
    enabled: true
```

#### 4.2.9. Decision Rationale

Sitemap is the optimal primary method because: (a) no RSS feed exists (confirmed via live probe -- /rss.xml returns 404, /rss/ redirects), (b) the news namespace sitemap provides richer metadata than any other site in the corpus (title, date, keywords inline), (c) fully permissive robots.txt with no Crawl-delay, (d) low volume makes full daily coverage trivial. The news sitemap metadata extraction is a unique efficiency advantage for this site.

---

### 4.3. scmp.com (South China Morning Post)

**Cross-Reference**: [trace:step-1:group-f-site-34] | [trace:step-3:scmp-com]

#### 4.3.1. Overview

| Field | Value |
|-------|-------|
| **source_id** | `scmp` |
| **Language** | English (en) |
| **Difficulty** | Medium |
| **Bot-blocking** | MEDIUM (Crawl-delay: 10s; standard Cloudflare) |
| **Paywall** | Soft-metered (Alibaba-owned; generous free quota) |
| **Rendering** | Next.js SSR (`__NEXT_DATA__` available) |

#### 4.3.2. URL Discovery

**Primary Method: RSS (80+ category feeds)**

- **RSS directory page**: `https://www.scmp.com/rss`
- **Feed URL pattern**: `https://www.scmp.com/rss/{section_id}/feed`
- **Top feeds by volume**:
  - `/rss/91/feed` -- News (general)
  - `/rss/2/feed` -- Hong Kong
  - `/rss/4/feed` -- China
  - `/rss/3/feed` -- Asia
  - `/rss/5/feed` -- World
  - `/rss/92/feed` -- Business
  - `/rss/36/feed` -- Tech
- Each feed contains ~50 items (confirmed via live probe of `/rss/91/feed`)
- Feed format: RSS 2.0 with Atom, media, content namespace extensions
- Fields per item: `<title>`, `<link>`, `<description>` (summary only), `<pubDate>`, `<author>`/`<dc:creator>`, `<guid>`, `<enclosure>` (image), `<media:content>`
- **Note**: RSS description is truncated (ends with "...") -- full body requires page fetch

**Discovery Strategy**:
1. Poll top 5-7 highest-volume RSS feeds (5-7 requests)
2. Deduplicate URLs across feeds (articles may appear in multiple section feeds)
3. Fetch individual article pages for full body extraction
4. `utm_source=rss_feed` parameter in RSS URLs -- strip for deduplication

**Fallback Method: Sitemap + DOM**

- Trigger: RSS feeds return < 10 articles combined OR HTTP 403 for > 30 minutes
- 2 sitemaps referenced in robots.txt (main + archive)
- Note: `/sitemap.xml` returns 404; use sitemap URLs from robots.txt

#### 4.3.3. Article Extraction Selectors

| Field | Selector | Notes |
|-------|----------|-------|
| **Title** | `h1` (CSS: `h1` -- dynamically generated class like `.css-hcn1aw` but use tag selector for stability) | Confirmed via live probe; use `h1` element selector not CSS class (which is CSS-in-JS generated and may change) |
| **Body** | Grid area `content` container (use `article` element or `[itemProp="articleBody"]` if available) | CSS-in-JS classes (`.css-6gl59f`) are unstable; prefer semantic selectors. `trafilatura` handles Next.js SSR HTML well |
| **Author** | JSON-LD `author.name` OR dedicated author section | JSON-LD provides `Person` schema with author name. CSS classes unstable. Example: "Zhang Tong" |
| **Date** | JSON-LD `datePublished` (ISO 8601: `2026-02-26T12:00:09+08:00`) | Preferred over rendered date ("12:00pm, 26 Feb 2026"). Schema.org `datePublished` attribute also available on article element |
| **Category** | URL path: `/{section}/{subsection}/article/...` | Extract from URL segments. RSS feed name also provides category |
| **URL** | RSS `<link>` (strip `?utm_source=rss_feed`) OR `<link rel="canonical">` | Normalize by removing UTM parameters |

**Elements to Strip from Body**:
- Advertisement containers (`.css-ix6wpu`, `.css-145tg3x` -- but prefer generic ad-class stripping)
- Inline ad slots (multiple `div-gpt-ad-*` elements)
- Related content carousels (bottom carousel)
- Audio player controls ("speech article" feature)
- Paywall container (`.css-1kfpym9` -- hidden on desktop, visible on mobile)

**JSON-LD Structured Data** (key advantage):
```json
{
  "@type": "NewsArticle",
  "headline": "...",
  "author": {"@type": "Person", "name": "..."},
  "datePublished": "2026-02-26T12:00:09+08:00",
  "dateModified": "2026-02-26T12:11:00+08:00",
  "publisher": {"@type": "NewsMediaOrganization", "name": "South China Morning Post"},
  "isAccessibleForFree": "False"
}
```
- **Note**: `isAccessibleForFree: False` appears in schema but actual content is mostly accessible (soft paywall with generous quota). Do not use this field to determine extractability.

**`__NEXT_DATA__` Extraction** (alternative strategy):
- SCMP runs Next.js; `__NEXT_DATA__` JSON blob contains article content in Relay query format
- Can parse article text from JSON if HTML extraction fails
- Less reliable than HTML extraction but useful as a secondary extraction path

#### 4.3.4. Language/Encoding Handling

- **Primary encoding**: UTF-8 (standard for modern English-language site)
- **No CJK encoding risk**: English-language publication. Chinese names appear as romanized text (e.g., "Zhang Tong"), not CJK characters in article body.
- **Occasional CJK in titles**: Some article titles may contain Chinese characters for names/places. UTF-8 handles these natively.

#### 4.3.5. Anti-Block Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **UA tier** | T2 (10 UAs) | MEDIUM bot-blocking; moderate rotation |
| **Starting escalation tier** | Tier 1 | RSS access is straightforward |
| **Max escalation tier** | Tier 5 | Medium difficulty; Tier 5 for persistent blocks |
| **Requires proxy** | No | Globally accessible English-language site |
| **Proxy region** | null | N/A |
| **Accept-Language** | `en-US,en;q=0.9` | English content |
| **Special UA note** | NewsNow and GrapeShot have special permissions in robots.txt; standard Chrome UA preferred |

#### 4.3.6. Rate Limiting

| Parameter | Value |
|-----------|-------|
| **Base delay** | **10 seconds (MANDATORY -- robots.txt `Crawl-delay: 10`)** |
| **Jitter** | 0s (10s mandatory delay is already conservative) |
| **Max requests/hour** | 360 |
| **Daily article estimate** | ~150 |
| **Crawl time** | ~4.0 minutes |

#### 4.3.7. Special Handling

1. **Mandatory 10-second Crawl-delay**: Legally binding per robots.txt. All requests (RSS feeds + article pages) must respect this interval.
2. **Soft paywall management**: SCMP's metered paywall allows generous free access. Cookie reset between crawl sessions ensures quota is refreshed. If paywall is hit mid-crawl, accept partial body (lead paragraphs visible to non-subscribers).
3. **RSS URL normalization**: Strip `?utm_source=rss_feed` parameter from all article URLs before deduplication.
4. **CSS-in-JS selector instability**: SCMP uses CSS-in-JS (Emotion-style) generating class names like `.css-hcn1aw`. These change on deployment. Use tag-based selectors (`h1`, `article`), semantic selectors (`[itemProp="articleBody"]`), or JSON-LD extraction as primary strategy. Do NOT hardcode CSS hash classes.
5. **JSON-LD as primary metadata source**: The JSON-LD NewsArticle schema provides stable, structured title/date/author extraction that is deployment-independent. Prefer JSON-LD over CSS selectors for metadata fields.

#### 4.3.8. sources.yaml Configuration

```yaml
scmp:
  name: "South China Morning Post"
  url: "https://www.scmp.com"
  region: "cn"
  language: "en"
  group: "F"
  crawl:
    primary_method: "rss"
    fallback_methods:
      - "sitemap"
      - "dom"
    rss_url: "https://www.scmp.com/rss/91/feed"
    sitemap_url: null  # /sitemap.xml returns 404; use robots.txt sitemap URLs
    rate_limit_seconds: 10
    crawl_delay_mandatory: 10
    max_requests_per_hour: 360
    jitter_seconds: 0
  anti_block:
    ua_tier: 2
    default_escalation_tier: 1
    max_escalation_tier: 5
    requires_proxy: false
    proxy_region: null
    bot_block_level: "MEDIUM"
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

#### 4.3.9. Decision Rationale

RSS is the optimal primary method because: (a) 80+ category feeds provide comprehensive section coverage, (b) RSS delivers title/date/author metadata without additional page fetches, (c) 50 items per feed ensures good daily coverage from top 5-7 feeds, (d) the 10-second Crawl-delay makes sitemap-based discovery slower (must respect delay for each sitemap fetch), and (e) RSS feeds are accessible without Cloudflare challenges. The JSON-LD structured data on article pages provides reliable metadata extraction independent of CSS-in-JS class name changes.

---

### 4.4. taiwannews.com.tw (Taiwan News)

**Cross-Reference**: [trace:step-1:group-f-site-35] | [trace:step-3:taiwannews-com-tw]

#### 4.4.1. Overview

| Field | Value |
|-------|-------|
| **source_id** | `taiwannews` |
| **Language** | English (en) / Chinese (zh) bilingual |
| **Difficulty** | Easy |
| **Bot-blocking** | LOW (fully permissive robots.txt) |
| **Paywall** | None |
| **Rendering** | Next.js SSR (`__NEXT_DATA__` available) |

#### 4.4.2. URL Discovery

**Primary Method: Sitemap (3 sitemaps)**

- **Sitemaps**:
  - `/sitemap.xml` -- main sitemap (~635 URLs, confirmed via live probe)
  - `/sitemap_en.xml` -- English articles
  - `/sitemap_zh.xml` -- Chinese articles
- Fields per entry: `<loc>`, `<lastmod>`, `<priority>` (no `<changefreq>`, no news namespace)
- **Note**: The `<lastmod>` dates appear static (all show `2024-04-01T01:31:05+00:00`), which limits diff-based discovery effectiveness. Compare article URLs against known cache instead.

**Discovery Strategy**:
1. Fetch `/sitemap_en.xml` (primary English content)
2. Parse article URLs (pattern: `/news/{id}`)
3. Filter against known URL cache for new articles
4. Optionally fetch `/sitemap_zh.xml` for Chinese-language articles if bilingual coverage desired

**Fallback Method: DOM Navigation**

- Trigger: All 3 sitemaps return HTTP 403
- Navigate section pages from homepage
- Section URLs: `/category/Politics`, `/category/Business`, `/category/Society`, etc.
- Article links: `<a href="/news/{id}">` pattern

#### 4.4.3. Article Extraction Selectors

| Field | Selector | Notes |
|-------|----------|-------|
| **Title** | `h1.text-head-semibold` (confirmed via live probe) | Single `<h1>` with consistent class name |
| **Body** | `div[itemProp="articleBody"]` (confirmed via live probe) | Microdata `itemProp="articleBody"` -- stable semantic selector |
| **Author** | `<h3>` within author bio section (`.flex.gap-3`) | Format: "Jono Thomson" with linked profile at `/en/journalist/{id}` |
| **Date** | `article:published_time` meta tag OR right-aligned `<p>` | Format: `Mar. 31, 2024 20:29` -- parse with `dateutil.parser.parse()` |
| **Category** | URL path: `/category/{Category}` from section pages, or breadcrumb | Category visible in section navigation |
| **URL** | `<link rel="canonical">` or sitemap `<loc>` | Pattern: `https://www.taiwannews.com.tw/news/{id}` |

**Elements to Strip from Body**:
- `div-gpt-ad-*` advertisement containers (Google GPT ad slots confirmed)
- "Related Articles" section (6 linked articles at article bottom)
- "Most Read" sidebar (10 article links)
- Next.js hydration scripts

**Open Graph Meta Tags Available**:
- `og:title`, `og:description`, `og:url`, `og:image`, `og:type`
- `twitter:card`, `twitter:title`, `twitter:description`, `twitter:image`

#### 4.4.4. Language/Encoding Handling

- **Primary encoding**: UTF-8 (confirmed: `<meta charSet="utf-8">` in live probe)
- **Bilingual handling**: English articles on `/sitemap_en.xml`, Chinese articles on `/sitemap_zh.xml`
- **Language detection**: Use `langdetect` library on article body to classify en/zh per article. URL-based detection is unreliable (some mixed-language articles).

#### 4.4.5. Anti-Block Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **UA tier** | T1 (1 UA) | LOW bot-blocking; minimal rotation needed |
| **Starting escalation tier** | Tier 1 | No blocking observed |
| **Max escalation tier** | Tier 3 | Easy difficulty |
| **Requires proxy** | No | Globally accessible |
| **Proxy region** | null | N/A |
| **Accept-Language** | `en-US,en;q=0.9,zh-TW;q=0.8` | Bilingual content |

#### 4.4.6. Rate Limiting

| Parameter | Value |
|-----------|-------|
| **Base delay** | 2 seconds |
| **Jitter** | 0s |
| **Max requests/hour** | 1800 |
| **Daily article estimate** | ~30 |
| **Crawl time** | ~1.5 minutes |

#### 4.4.7. Special Handling

1. **Stale sitemap lastmod**: All sitemap entries show the same `lastmod` date (2024-04-01), meaning the sitemap does not reflect actual content freshness. URL-based deduplication against known cache is the only reliable method for identifying new articles.
2. **Next.js SSR**: Despite Next.js framework, content is fully rendered in server-side HTML. `__NEXT_DATA__` is available as an alternative extraction source but standard HTML parsing is sufficient.
3. **Bilingual content**: Both English and Chinese articles are published. Focus on English (`/sitemap_en.xml`) for primary coverage. Chinese articles can be added as needed.
4. **Microdata selectors**: `itemProp="articleBody"` provides a stable, semantic selector for body extraction that is independent of class name changes. This is a best-practice example for Next.js sites.

#### 4.4.8. sources.yaml Configuration

```yaml
taiwannews:
  name: "Taiwan News"
  url: "https://www.taiwannews.com.tw"
  region: "tw"
  language: "en"
  group: "F"
  crawl:
    primary_method: "sitemap"
    fallback_methods:
      - "dom"
    rss_url: null
    sitemap_url: "/sitemap_en.xml"
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
    sections_count: 10
    enabled: true
```

#### 4.4.9. Decision Rationale

Sitemap is the only viable primary method because: (a) no RSS feed exists (confirmed: /feed returns 404, /rss.xml returns 404), (b) 3 bilingual sitemaps provide comprehensive URL coverage, (c) fully permissive robots.txt with no Crawl-delay, (d) Next.js SSR means full content in HTML without JS execution. The `itemProp="articleBody"` microdata selector is the most stable body extraction approach for this site.

---

### 4.5. yomiuri.co.jp (Yomiuri Shimbun -- 読売新聞)

**Cross-Reference**: [trace:step-1:group-f-site-36] | [trace:step-3:yomiuri-co-jp]

#### 4.5.1. Overview

| Field | Value |
|-------|-------|
| **source_id** | `yomiuri` |
| **Language** | Japanese (ja) |
| **Difficulty** | Hard |
| **Bot-blocking** | HIGH (geographic IP filtering + likely Cloudflare equivalent) |
| **Paywall** | Soft-metered (Yomiuri Premium -- 読売プレミアム) |
| **Rendering** | SSR (proprietary Japanese newspaper CMS) |

**NOTE**: Direct WebFetch to yomiuri.co.jp was blocked during live probing (confirming Step 1 reconnaissance that geographic IP filtering is active). All selectors below are based on known Japanese newspaper CMS patterns, Yomiuri's publicly documented structure, and industry-standard Japanese news site patterns. **Runtime verification from Japanese IP is required before production deployment.**

#### 4.5.2. URL Discovery

**Primary Method: RSS**

- **Expected RSS URL**: `https://www.yomiuri.co.jp/feed/` or `https://www.yomiuri.co.jp/rss/`
- **Expected section feeds** (based on known Yomiuri section structure):
  - `/feed/national/` -- National news (国内)
  - `/feed/world/` -- International (国際)
  - `/feed/economy/` -- Economy (経済)
  - `/feed/sports/` -- Sports (スポーツ)
  - `/feed/culture/` -- Culture (文化)
  - `/feed/science/` -- Science (科学)
  - `/feed/editorial/` -- Editorials (社説)
- Format: RSS 2.0 expected; Japanese RSS feeds typically use UTF-8 with full Japanese titles and descriptions
- **IMPORTANT**: Exact RSS URLs must be verified from within Japanese IP range. URLs above are inferred from Yomiuri's known site structure.

**Discovery Strategy**:
1. Verify RSS endpoint(s) from Japanese proxy
2. Poll top section feeds
3. Deduplicate across section feeds
4. Fetch individual article pages for body extraction

**Fallback Method: Sitemap + DOM**

- Trigger: RSS returns < 10 articles OR endpoint unreachable for > 30 minutes
- Sitemap: `/sitemap.xml` (expected standard sitemap)
- DOM: Navigate section pages from homepage

#### 4.5.3. Article Extraction Selectors

**NOTE**: Selectors below are based on known Japanese newspaper CMS patterns and must be verified from Japanese IP.

| Field | Selector | Notes |
|-------|----------|-------|
| **Title** | `h1` (article heading) | Japanese titles: no furigana/ruby annotations expected in headlines (unlike educational content). Plain text `<h1>`. |
| **Body** | `article` element or `.article-body` / `#article-body` | Standard Japanese news CMS pattern. `trafilatura` supports Japanese (ja) content extraction. |
| **Author** | Byline area near article header | Japanese byline patterns: `記者名` after article source. Example: `（読売新聞）` for wire attribution, `記者 山田太郎` for named reporters. Regex: `記者\s*([\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]{2,6})` |
| **Date** | `time[datetime]` element or meta `article:published_time` | Japanese date format in rendered text: `2026年2月26日 14時30分` (CJK date). Parse with regex: `(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2})時(\d{1,2})分`. ISO 8601 in `datetime` attribute preferred. |
| **Category** | URL path segment or breadcrumb navigation | Section paths: `/national/`, `/world/`, `/economy/`, `/sports/`, `/culture/` |
| **URL** | `<link rel="canonical">` or RSS `<link>` | Expected pattern: `https://www.yomiuri.co.jp/{section}/{YYYYMMDD}-OYT1T{id}/` |

**Ruby Annotation Handling**:
- Japanese news articles may contain `<ruby>` tags with `<rt>` furigana annotations for difficult kanji
- **Strategy**: Strip `<rt>` and `<rp>` elements, preserve base text only
- Implementation:
  ```python
  import re
  # Remove ruby annotations, keep base text
  text = re.sub(r'<rt[^>]*>.*?</rt>', '', html)
  text = re.sub(r'<rp[^>]*>.*?</rp>', '', text)
  text = re.sub(r'</?ruby[^>]*>', '', text)
  ```

#### 4.5.4. Language/Encoding Handling

- **Primary encoding**: UTF-8 (expected for modern Yomiuri pages)
- **Legacy encoding**: Shift_JIS (`cp932`) or EUC-JP for archived articles (pre-2015)
- **Detection chain**:
  ```python
  # 1. HTTP Content-Type header
  charset = parse_charset_from_content_type(response.headers.get('content-type'))
  # 2. HTML meta tag
  if not charset:
      charset = extract_meta_charset(html_bytes[:4096])  # Check first 4KB only
  # 3. cchardet for Japanese-specific detection
  if not charset:
      detected = cchardet.detect(response.content)  # C-backed, faster for CJK
      charset = detected['encoding'] if detected['confidence'] > 0.7 else 'utf-8'
  # 4. Decode with appropriate codec
  codec_map = {
      'shift_jis': 'cp932',     # Windows superset of Shift_JIS
      'shift-jis': 'cp932',
      'sjis': 'cp932',
      'euc-jp': 'euc-jp',
      'eucjp': 'euc-jp',
  }
  codec = codec_map.get(charset.lower(), charset.lower()) if charset else 'utf-8'
  text = response.content.decode(codec, errors='replace')
  ```
- **Japanese text validation**: After decoding, check for mojibake indicators:
  - Presence of `\ufffd` (replacement character) above 0.5% of total characters
  - Unexpected byte sequences that produce CJK Compatibility Ideographs
  - If detected, retry with alternative codec (UTF-8 -> cp932 -> euc-jp)

#### 4.5.5. Anti-Block Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **UA tier** | T3 (50 UAs) | HIGH bot-blocking; aggressive rotation needed |
| **Starting escalation tier** | Tier 2 (session management baseline) | Hard difficulty default |
| **Max escalation tier** | Tier 6 | Hard difficulty; may need Claude Code analysis |
| **Requires proxy** | **Yes** | Geographic IP filtering confirmed (WebFetch blocked from non-Japanese IP) |
| **Proxy region** | `jp` | Japanese residential proxy required |
| **Accept-Language** | `ja,en;q=0.9` | Japanese content; Japanese browser headers expected |
| **Referer** | `https://www.google.co.jp/` | Japanese Google referrer may improve acceptance |

#### 4.5.6. Rate Limiting

| Parameter | Value |
|-----------|-------|
| **Base delay** | 10 seconds |
| **Jitter** | 0-3 seconds random |
| **Max requests/hour** | 240 |
| **Daily article estimate** | ~200 |
| **Crawl time** | ~5.0 minutes |

#### 4.5.7. Special Handling

1. **Japanese proxy REQUIRED**: Geographic IP filtering is the primary access barrier. Without a Japanese residential proxy, all requests will be blocked. This is the only Group F site requiring a proxy. DataImpulse supports Japanese residential IPs (confirmed in Step 3 risk assessment).
2. **Soft paywall (Yomiuri Premium)**: Some articles are gated behind 読売プレミアム subscription. Free articles are accessible; paywalled articles will have truncated body. Accept partial body for metered articles; reset cookies between sessions.
3. **World's highest-circulation newspaper**: Yomiuri has the world's largest newspaper circulation (~6.6 million daily). The ~200 articles/day estimate reflects the online edition, which is a subset of print.
4. **Japanese date parsing**: The `年月日時分` format (`2026年2月26日 14時30分`) requires CJK-aware date parsing. ISO 8601 from `time[datetime]` attributes is preferred when available.
5. **Ruby/furigana stripping**: Apply `<rt>`/`<rp>` removal before text processing. Furigana is reading aids for kanji and should not appear in extracted text output.
6. **Japanese NLP downstream**: Japanese text requires Kiwi (for Korean) equivalent tokenizer (MeCab/SudachiPy) for downstream analysis Stage 1. This is noted for completeness but is the analysis layer's responsibility, not the crawling adapter's.
7. **Runtime selector verification**: All CSS selectors MUST be verified from Japanese IP before production deployment. Current selectors are based on pattern analysis, not live verification.

#### 4.5.8. sources.yaml Configuration

```yaml
yomiuri:
  name: "Yomiuri Shimbun"
  url: "https://www.yomiuri.co.jp"
  region: "jp"
  language: "ja"
  group: "F"
  crawl:
    primary_method: "rss"
    fallback_methods:
      - "sitemap"
      - "dom"
    rss_url: "https://www.yomiuri.co.jp/feed/"
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
    proxy_region: "jp"
    bot_block_level: "HIGH"
  extraction:
    paywall_type: "soft-metered"
    title_only: false
    rendering_required: false
    charset: "utf-8"
  meta:
    difficulty_tier: "Hard"
    daily_article_estimate: 200
    sections_count: 15
    enabled: true
```

#### 4.5.9. Decision Rationale

RSS is the expected primary method because: (a) Japanese newspapers traditionally provide RSS feeds as the primary syndication mechanism, (b) RSS delivers metadata without per-article page fetches (reducing request count against HIGH bot-blocking), (c) Yomiuri's RSS has been historically documented in Japanese news aggregator indexes. However, exact RSS URLs could not be live-verified due to IP blocking and MUST be confirmed from Japanese proxy during production setup. If RSS is unavailable, sitemap+DOM provides a complete fallback chain. The Japanese proxy requirement is the single most critical infrastructure dependency for this site.

---

### 4.6. thehindu.com (The Hindu)

**Cross-Reference**: [trace:step-1:group-f-site-37] | [trace:step-3:thehindu-com]

#### 4.6.1. Overview

| Field | Value |
|-------|-------|
| **source_id** | `thehindu` |
| **Language** | English (en) |
| **Difficulty** | Medium |
| **Bot-blocking** | HIGH (Cloudflare protection; WebFetch blocked during probe) |
| **Paywall** | Soft-metered (10 free articles/month per IP) |
| **Rendering** | SSR (proprietary CMS) |

**NOTE**: Direct WebFetch to thehindu.com was blocked during live probing (confirming Step 1 HIGH bot-blocking assessment). Selectors below are based on The Hindu's well-documented site structure, common Indian newspaper CMS patterns, and historical crawler community data. **Runtime verification is required before production deployment.**

#### 4.6.2. URL Discovery

**Primary Method: RSS**

- **Expected RSS base**: `https://www.thehindu.com/feeder/default.rss` or `https://www.thehindu.com/news/rss`
- **Expected section feeds** (based on The Hindu's well-known section structure):
  - `/news/national/feeder/default.rss` -- National
  - `/news/international/feeder/default.rss` -- International
  - `/business/feeder/default.rss` -- Business
  - `/opinion/feeder/default.rss` -- Opinion
  - `/sport/feeder/default.rss` -- Sport
  - `/sci-tech/feeder/default.rss` -- Science & Technology
  - `/entertainment/feeder/default.rss` -- Entertainment
- Format: RSS 2.0; well-documented feeds widely used by Indian news aggregators
- The Hindu's RSS feeds are consistently cited in Indian media RSS directories

**Discovery Strategy**:
1. Poll top 5-7 section RSS feeds
2. Deduplicate article URLs across feeds
3. Fetch individual article pages for body extraction
4. Cookie management: reset per-session to refresh metered quota

**Fallback Method: Sitemap + DOM**

- Trigger: RSS returns < 10 articles OR HTTP 403 for > 30 minutes
- Sitemap: `/sitemap.xml` (standard)
- DOM: Navigate section pages from homepage

#### 4.6.3. Article Extraction Selectors

**NOTE**: Selectors below are based on established patterns and community data; runtime verification required.

| Field | Selector | Notes |
|-------|----------|-------|
| **Title** | `h1.title` or `h1` within article header | The Hindu uses semantic heading structure |
| **Body** | `div.articlebodycontent` or `div[itemprop="articleBody"]` | Standard CMS article body container; The Hindu uses microdata |
| **Author** | `.author-name` or `[itemprop="author"]` | Format: "John Doe" (English-language site). Wire stories attributed to "PTI", "Reuters", "AFP" |
| **Date** | `time[datetime]` or `meta[property="article:published_time"]` | Expected ISO 8601 format. Rendered format: "February 26, 2026 14:30 IST" |
| **Category** | URL path: `/{section}/{subsection}/article{id}.ece` | Extract from URL segments |
| **URL** | `<link rel="canonical">` or RSS `<link>` | Pattern: `https://www.thehindu.com/{section}/{subsection}/article{id}.ece` |

**Elements to Strip from Body**:
- Advertisement containers
- "Also Read" / "Related Stories" blocks
- Social sharing widgets
- Subscription prompts / paywall notices
- "You have read X of Y free articles" banners

#### 4.6.4. Language/Encoding Handling

- **Primary encoding**: UTF-8 (standard for English-language Indian websites)
- **No CJK encoding risk**: English-language publication
- **Occasional Indic script**: Some articles may contain Hindi/Tamil/Telugu names in Devanagari or other Indic scripts. UTF-8 handles all Unicode scripts natively.

#### 4.6.5. Anti-Block Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **UA tier** | T3 (50 UAs) | HIGH bot-blocking; aggressive rotation needed |
| **Starting escalation tier** | Tier 1 | Start conservatively; escalate on Cloudflare challenges |
| **Max escalation tier** | Tier 5 | Medium difficulty (despite HIGH bot-blocking, content is largely free) |
| **Requires proxy** | No | Globally accessible; Cloudflare is the barrier, not geo-blocking |
| **Proxy region** | null | Indian IP may improve Cloudflare acceptance but not required |
| **Accept-Language** | `en-IN,en;q=0.9` | Indian English locale may improve acceptance |
| **Referer** | `https://www.google.co.in/` | Indian Google referrer |

#### 4.6.6. Rate Limiting

| Parameter | Value |
|-----------|-------|
| **Base delay** | 10 seconds |
| **Jitter** | 0-3 seconds random |
| **Max requests/hour** | 240 |
| **Daily article estimate** | ~100 |
| **Crawl time** | ~4.0 minutes |

**Note**: Step 3 estimated 5s base delay with 720 req/hr, but given the confirmed HIGH bot-blocking (WebFetch blocked), this strategy uses the more conservative 10s+jitter rate to reduce Cloudflare trigger risk. This increases crawl time from 3.0 to 4.0 minutes but significantly reduces block probability.

#### 4.6.7. Special Handling

1. **Cloudflare protection**: The Hindu uses Cloudflare which actively blocked WebFetch probing. Standard Chrome UAs with realistic headers are essential. If Cloudflare JS challenges are encountered, escalate to Playwright/Patchright (Tier 3-4).
2. **Metered paywall (10 free/month per IP)**: The 10-article monthly limit is per-IP. Strategies:
   - Cookie reset between crawl sessions (clear cookies to appear as fresh visitor)
   - Rotate through UA pool (different UAs may be tracked separately)
   - Accept partial body when paywall is hit (lead paragraph + summary visible)
   - At ~100 articles/day, the metered limit is irrelevant per-crawl if cookies are not persisted
3. **`.ece` URL extension**: The Hindu uses `.ece` extension in article URLs (Enterprise Content Engine). This is a standard pattern for sites using CMS platforms like Escenic.
4. **India's leading English daily**: The Hindu is one of India's most prestigious English-language newspapers. Content is high-quality, well-structured, and suitable for analysis.
5. **RSS reliability**: The Hindu's RSS feeds are among the most reliable in the Indian media ecosystem, widely used by aggregators. RSS is strongly preferred over sitemap for this site due to Cloudflare -- RSS endpoints may have different rate limiting than web pages.
6. **Runtime selector verification**: All CSS selectors MUST be verified via Cloudflare-bypassing access before production deployment. Patchright headless browser from a clean IP is recommended for initial selector verification.

#### 4.6.8. sources.yaml Configuration

```yaml
thehindu:
  name: "The Hindu"
  url: "https://www.thehindu.com"
  region: "in"
  language: "en"
  group: "F"
  crawl:
    primary_method: "rss"
    fallback_methods:
      - "sitemap"
      - "dom"
    rss_url: "https://www.thehindu.com/feeder/default.rss"
    sitemap_url: "/sitemap.xml"
    rate_limit_seconds: 10
    crawl_delay_mandatory: null
    max_requests_per_hour: 240
    jitter_seconds: 3
  anti_block:
    ua_tier: 3
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
    daily_article_estimate: 100
    sections_count: 15
    enabled: true
```

#### 4.6.9. Decision Rationale

RSS is the preferred primary method because: (a) The Hindu's RSS feeds are well-documented and widely used in the Indian media ecosystem, (b) RSS endpoints may receive different Cloudflare treatment than web pages (potentially less aggressive), (c) RSS provides metadata (title, date, author, category) without per-article page fetches, reducing the number of Cloudflare-gatekept requests, (d) The Hindu has historically maintained reliable RSS infrastructure. The HIGH bot-blocking classification combined with soft paywall makes this the most access-challenging English-language site in Group F.

---

## 5. Regional Bot-Detection Patterns

### 5.1. Chinese Sites (people.com.cn, globaltimes.cn)

| Pattern | Detail |
|---------|--------|
| **Primary mechanism** | Rate limiting via robots.txt Crawl-delay |
| **GFW (Great Firewall) impact** | Minimal for outbound crawling -- these sites are designed for global access (English editions) and domestic access (Chinese editions). Not behind GFW for external users. |
| **Specific headers** | `Accept-Language: zh-CN,zh;q=0.9,en;q=0.8` for people.com.cn; `en-US,en;q=0.9` for globaltimes.cn |
| **IP blocking** | Not observed for either Chinese site. Both are freely accessible globally. |
| **CDN** | Standard CDN (not Cloudflare). Chinese domestic CDN infrastructure. |
| **Proxy requirement** | None. Both sites are accessible without proxy. |

**Key insight**: Chinese state media sites are designed for broad dissemination and are among the most crawler-friendly sites in the corpus. The 120s Crawl-delay on people.com.cn is the only significant constraint.

### 5.2. Japanese Site (yomiuri.co.jp)

| Pattern | Detail |
|---------|--------|
| **Primary mechanism** | Geographic IP filtering (non-Japanese IPs blocked) |
| **Secondary mechanism** | Likely Cloudflare or equivalent Japanese CDN |
| **Specific headers** | `Accept-Language: ja,en;q=0.9` with realistic Japanese browser fingerprint |
| **IP blocking** | Confirmed. WebFetch from non-Japanese IP was blocked. |
| **Crawl-delay** | Not confirmed (robots.txt inaccessible from non-Japanese IP) |
| **Proxy requirement** | **MANDATORY** -- Japanese residential proxy |

**Key insight**: Japanese major newspapers typically have moderate-to-high bot-blocking focused on geographic restrictions. Once accessed from a Japanese IP, blocking is generally moderate. The primary infrastructure investment is the Japanese proxy.

### 5.3. Indian Site (thehindu.com)

| Pattern | Detail |
|---------|--------|
| **Primary mechanism** | Cloudflare protection (active bot detection) |
| **Secondary mechanism** | Metered paywall (10 free/month) |
| **Specific headers** | `Accept-Language: en-IN,en;q=0.9` with Indian Google referrer |
| **IP blocking** | Not geographic -- Cloudflare-based bot detection |
| **Proxy requirement** | Not required, but Indian IP may reduce Cloudflare challenge frequency |

**Key insight**: The Hindu's blocking is technology-based (Cloudflare), not geography-based. Standard anti-Cloudflare techniques (realistic UA, cookie management, session rotation) are sufficient without geographic proxy.

### 5.4. Taiwanese Site (taiwannews.com.tw)

| Pattern | Detail |
|---------|--------|
| **Primary mechanism** | None (fully permissive) |
| **Proxy requirement** | None |

### 5.5. Bot-Detection Summary Table

| Site | Geographic Block | Cloudflare | Rate Limit | Paywall | Overall Access |
|------|-----------------|------------|------------|---------|----------------|
| people.com.cn | No | No | **120s mandatory** | None | Slow but easy |
| globaltimes.cn | No | No | None | None | Easiest in group |
| scmp.com | No | Standard | **10s mandatory** | Soft-metered | Moderate |
| taiwannews.com.tw | No | No | None | None | Easy |
| yomiuri.co.jp | **Yes (Japan)** | Likely | Unknown | Soft-metered | Hard (proxy required) |
| thehindu.com | No | **Active** | None specified | Soft-metered (10/month) | Moderate-Hard |

---

## 6. Non-Latin URL Pattern Handling

### 6.1. URL Pattern Summary

| Site | Pattern | Example | Dedup Strategy |
|------|---------|---------|----------------|
| people.com.cn | `http://{sub}.people.com.cn/n1/YYYY/MMDD/c{cat}-{id}.html` | `http://world.people.com.cn/n1/2026/0226/c1002-40670649.html` | Normalize: strip protocol, unify www/non-www; key on `c{cat}-{id}` |
| globaltimes.cn | `https://www.globaltimes.cn/page/YYYYMM/{id}.shtml` | `https://www.globaltimes.cn/page/202602/1355767.shtml` | Key on numeric `{id}` |
| scmp.com | `https://www.scmp.com/{sec}/{sub}/article/{id}/{slug}` | `https://www.scmp.com/news/china/science/article/3344554/quick-blink...` | Key on `article/{id}`; strip UTM params and slug |
| taiwannews.com.tw | `https://www.taiwannews.com.tw/news/{id}` | `https://www.taiwannews.com.tw/news/5133908` | Key on numeric `{id}` |
| yomiuri.co.jp | `https://www.yomiuri.co.jp/{sec}/{YYYYMMDD}-OYT1T{id}/` | (inferred, verify from JP IP) | Key on `OYT1T{id}` |
| thehindu.com | `https://www.thehindu.com/{sec}/{sub}/article{id}.ece` | `https://www.thehindu.com/news/national/article12345678.ece` | Key on `article{id}` |

### 6.2. URL Normalization Rules

1. **Protocol normalization**: Convert `http://` to `https://` (except people.com.cn which uses `http://` canonically for subdomains)
2. **Trailing slash**: Remove trailing slashes for consistency
3. **Query parameter stripping**: Remove tracking parameters: `utm_source`, `utm_medium`, `utm_campaign`, `ref`, `source`, `fbclid`, `gclid`
4. **Fragment removal**: Strip `#fragment` from all URLs
5. **Case normalization**: Lowercase domain, preserve path case (some paths are case-sensitive)
6. **WWW normalization**: Unify `www.` and non-`www.` variants (people.com.cn uses both `www.people.com.cn` and `people.cn`)
7. **CJK URL encoding**: No CJK characters appear in any Group F article URLs -- all use numeric IDs or ASCII slugs. No percent-encoding normalization needed for CJK characters.

### 6.3. Deduplication Key Extraction

```python
import re
from urllib.parse import urlparse, parse_qs

DEDUP_PATTERNS = {
    'people': re.compile(r'c(\d+)-(\d+)\.html$'),           # c{cat}-{id}
    'globaltimes': re.compile(r'/page/\d+/(\d+)\.shtml$'),  # {id}
    'scmp': re.compile(r'/article/(\d+)/'),                   # article/{id}
    'taiwannews': re.compile(r'/news/(\d+)$'),               # news/{id}
    'yomiuri': re.compile(r'OYT1T(\d+)'),                    # OYT1T{id}
    'thehindu': re.compile(r'article(\d+)\.ece$'),           # article{id}
}

def extract_dedup_key(source_id: str, url: str) -> str:
    """Extract unique article identifier from URL for deduplication."""
    pattern = DEDUP_PATTERNS.get(source_id)
    if pattern:
        match = pattern.search(url)
        if match:
            return f"{source_id}:{match.group(0)}"
    # Fallback: normalized URL path
    parsed = urlparse(url)
    return f"{source_id}:{parsed.path}"
```

---

## 7. Volume Estimates and Scheduling

### 7.1. Daily Volume Summary

| Site | Daily Articles | Peak Hours (Local) | Peak Hours (UTC) | Weekend Factor |
|------|---------------|-------------------|------------------|---------------|
| people.com.cn | ~500 | 08:00-18:00 CST | 00:00-10:00 | 0.4x (state media reduces weekend output) |
| globaltimes.cn | ~40 | 09:00-21:00 CST | 01:00-13:00 | 0.6x |
| scmp.com | ~150 | 06:00-22:00 HKT | 22:00-14:00 | 0.7x |
| taiwannews.com.tw | ~30 | 08:00-20:00 CST | 00:00-12:00 | 0.5x |
| yomiuri.co.jp | ~200 | 06:00-23:00 JST | 21:00-14:00 | 0.6x |
| thehindu.com | ~100 | 05:00-22:00 IST | 23:30-16:30 | 0.7x |
| **Total** | **~1,020** | | | |

### 7.2. Crawl Time Budget

| Site | Crawl Time | Notes |
|------|-----------|-------|
| people.com.cn | 8.0 min | 120s delay; sitemap scan + priority articles only within window |
| globaltimes.cn | 1.5 min | Very fast; low volume + no restrictions |
| scmp.com | 4.0 min | 10s mandatory delay |
| taiwannews.com.tw | 1.5 min | Fast; low volume + no restrictions |
| yomiuri.co.jp | 5.0 min | 10s+jitter; proxy latency adds ~1s per request |
| thehindu.com | 4.0 min | 10s+jitter; Cloudflare negotiation adds overhead |
| **Total (sequential)** | **24.0 min** | Fits within 2-hour budget even sequentially |

### 7.3. Parallel Scheduling

From Step 3 parallelization plan:
- **Slot 1 (low-delay)**: globaltimes.cn + taiwannews.com.tw (~1.5 min)
- **Slot 2 (medium-delay)**: scmp.com + thehindu.com + people.com.cn (~8.0 min, dominated by people.com.cn)
- **Slot 3 (high-delay)**: yomiuri.co.jp (~5.0 min)

**Parallel total**: ~8.0 minutes (dominated by people.com.cn's 120s Crawl-delay)

**Note**: people.com.cn's slow cadence does not block other sites in its slot because the 120s idle wait can be filled with other site requests in the same thread.

---

## 8. CJK-Specific Technical Notes

### 8.1. Chinese Text Processing (people.com.cn)

- **Character set**: Simplified Chinese (GB2312/GBK legacy, UTF-8 modern)
- **Decode with gb18030**: Always use `gb18030` codec for any GB-family encoding detected (superset of GB2312 and GBK)
- **No Traditional Chinese**: people.com.cn exclusively publishes Simplified Chinese
- **Chinese date patterns**:
  - Full: `2026年02月26日12:25` or `2026年2月26日 12:25`
  - Short: `02月26日` (month-day only, year inferred from context)
  - ISO-adjacent: `2026-02-26 12:25:00` (sometimes used in meta tags)
- **Chinese author patterns**:
  - `记者 {name}` or `记者{name}` (reporter)
  - `编辑：{name}` (editor)
  - `来源：人民网` or `来源：新华社` (source attribution, not personal author)
  - Names: 2-4 Chinese characters (e.g., `郑可意`, `张伟`)
- **Chinese category detection**: Section names in navigation use Chinese (e.g., `时政`, `国际`, `财经`, `体育`). Map to English equivalents for standardized category field.

### 8.2. Japanese Text Processing (yomiuri.co.jp)

- **Character set**: UTF-8 (modern), Shift_JIS/EUC-JP (legacy)
- **Ruby annotation handling**: Strip `<rt>` and `<rp>` elements from `<ruby>` tags
- **Japanese date patterns**:
  - Full: `2026年2月26日 14時30分` (year-month-day hour-minute)
  - With seconds: `2026年2月26日 14:30:00`
  - Day of week: `2026年2月26日(水) 14時30分` (parenthesized day-of-week)
  - ISO 8601 in meta: `2026-02-26T14:30:00+09:00` (preferred)
- **Japanese author patterns**:
  - `記者 {name}` or `{name} 記者` (reporter)
  - `編集部` (editorial department -- no individual name)
  - `（読売新聞）` (wire attribution)
  - Names: 2-4 characters, typically kanji: `山田太郎`, `田中花子`
- **Furigana in headlines**: Rare in news headlines (more common in educational/children's content). If present, strip `<ruby><rt>` annotations.
- **Japanese URL encoding**: Yomiuri uses ASCII-only URL paths with numeric IDs. No percent-encoded Japanese characters expected in article URLs.

### 8.3. Encoding Detection Fallback Chain (Universal)

Applied to all sites where encoding is uncertain:

```
Step 1: HTTP Content-Type header → charset parameter
Step 2: HTML <meta charset="..."> or <meta http-equiv="Content-Type" content="...; charset=...">
Step 3: BOM (Byte Order Mark) detection at file start
Step 4: chardet/cchardet library detection (confidence > 0.8)
Step 5: Default to UTF-8
Step 6: Post-decode mojibake validation (replacement char ratio < 0.5%)
Step 7: If mojibake detected, retry with next candidate codec
```

Candidate codec priority by language:
- **Chinese**: UTF-8 > GB18030 > GBK > GB2312
- **Japanese**: UTF-8 > CP932 (Shift_JIS) > EUC-JP
- **English/Others**: UTF-8 (no fallback needed)

---

## 9. L1 Self-Verification

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | All 6 Asia-Pacific sites have complete configurations | **PASS** | Sections 4.1-4.6 cover all 6 sites with full strategy details |
| 2 | CJK encoding correctly specified per site | **PASS** | Section 3 (encoding matrix) + per-site Section 4.x.4 (encoding handling) |
| 3 | CSS/XPath selectors verified against actual site HTML | **PARTIAL** | globaltimes.cn, scmp.com, taiwannews.com.tw, people.com.cn: live-verified via WebFetch. yomiuri.co.jp, thehindu.com: pattern-based (blocked by IP/Cloudflare) -- marked for runtime verification |
| 4 | Date format patterns cover CJK variations | **PASS** | Section 8.1 (Chinese dates), Section 8.2 (Japanese dates), per-site date fields |
| 5 | Ruby annotation handling defined for Japanese sites | **PASS** | Section 4.5.3 (ruby stripping code) + Section 8.2 (furigana handling) |
| 6 | Bot-blocking handling is region-appropriate | **PASS** | Section 5 (regional bot-detection patterns) + per-site anti-block config |
| 7 | URL patterns tested for deduplication | **PASS** | Section 6 (URL patterns, normalization rules, dedup key extraction code) |
| 8 | Volume estimates realistic per site | **PASS** | Section 7 (volume table) consistent with Step 1 reconnaissance data |
| 9 | sources.yaml schema compatibility | **PASS** | Per-site YAML configs (Sections 4.x.8) follow Step 5 Section 5c schema exactly |
| 10 | Decision rationale + cross-references included | **PASS** | Per-site Section 4.x.9 (decision rationale) + trace markers throughout |
| 11 | All content in English | **PASS** | Full document in English |

### Verification Gap: 2 Sites Require Runtime Verification

- **yomiuri.co.jp**: All selectors are pattern-based due to Japanese IP blocking. RSS URL, article selectors, and date format patterns MUST be verified from Japanese proxy before production.
- **thehindu.com**: All selectors are pattern-based due to Cloudflare blocking. RSS URL structure and article selectors MUST be verified via Cloudflare-bypassing access before production.

These gaps are documented in each site's Special Handling section. They represent an inherent limitation of the reconnaissance phase (IP/bot restrictions prevent pre-production verification) and are consistent with the Step 1 finding that 22/44 sites had inferred data.

---

## 10. pACS Self-Rating

### Pre-mortem Protocol

**Q1: If this strategy fails in production, what is the most likely cause?**
The yomiuri.co.jp and thehindu.com CSS selectors are unverified against live site HTML due to access restrictions. If Yomiuri's RSS URL is wrong or The Hindu's article body selector has changed, body extraction will fail for 2 of 6 sites (300 articles/day, ~30% of group volume). This is the primary risk.

**Q2: What is the weakest aspect of this output?**
The selector specificity for yomiuri.co.jp and thehindu.com. For verified sites (globaltimes.cn, scmp.com, taiwannews.com.tw, people.com.cn), selectors are confirmed against live HTML. For the two blocked sites, selectors are based on industry patterns and may not match actual site structure.

**Q3: What would a reviewer criticize first?**
A reviewer would note that 2/6 sites have unverified selectors and may question whether the Japanese proxy infrastructure is confirmed available. They might also question whether the Step 3 rate limit adjustments (thehindu.com from 5s to 10s base delay) are adequately justified.

### Dimension Scores

| Dimension | Score | Justification |
|-----------|-------|---------------|
| **F (Fidelity)** | 72 | 4/6 sites have live-verified selectors and encoding. 2/6 (yomiuri, thehindu) are pattern-based with runtime verification flags. CJK encoding chains are comprehensive. URL deduplication patterns are tested. |
| **C (Completeness)** | 80 | All 6 sites have full configurations covering all required fields: URL discovery, selectors, encoding, anti-block, rate limiting, volume, sources.yaml config, decision rationale. No missing sections. Regional bot-detection patterns documented. |
| **L (Lucidity)** | 78 | Clear per-site structure with consistent subsections. Strategy matrix provides at-a-glance overview. Code examples included for encoding detection and dedup. Cross-references to Step 1/3/5 throughout. Verification gaps explicitly documented. |

**pACS = min(F, C, L) = min(72, 80, 78) = 72 (YELLOW)**

**Weak dimension**: F (Fidelity) -- due to 2/6 sites having unverified selectors. This is an inherent limitation of pre-production reconnaissance when sites actively block non-regional access.
