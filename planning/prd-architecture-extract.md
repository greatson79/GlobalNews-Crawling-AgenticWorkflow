# PRD Architecture Extract

> **Generated**: 2026-02-26T04:36:06Z
> **Source**: `coding-resource/PRD.md`
> **Extracted sections**: 6 (System Architecture), 7 (Output Specs / Data Schemas), 8 (Tech Stack)
> **Purpose**: Focused input for system-architect agent (Step 5)

---

## Hard Constraints (from PRD intro)

### 핵심 제약 조건

| # | 제약 | 설명 |
|---|------|------|
| **C1** | **Claude API 비용 $0** | Claude API를 호출하지 않는다. 모든 분석은 로컬 Python 라이브러리로 수행한다. Claude Code 구독제 플랜만 사용한다. |
| **C2** | **Claude Code = 오케스트레이터** | Claude Code(구독 내)는 Python 스크립트 생성 → Bash 실행 → 결과 읽기 → 다음 판단의 루프를 수행한다. 데이터를 직접 처리하지 않는다. |
| **C3** | **로컬 머신 실행** | MacBook M2 Pro 16GB 기준. 클라우드 GPU 불필요. |
| **C4** | **산출물 = 구조화된 데이터** | Parquet(분석 데이터) + SQLite(인덱스/쿼리). 리포트/시각화는 범위 밖. |
| **C5** | **합법적 크롤링** | robots.txt 존중, Rate Limiting 준수, 개인정보 미수집. |



---

## 6. 시스템 아키텍처

### 6.1 Staged Monolith 아키텍처

마이크로서비스가 아닌 **단계적 모놀리스(Staged Monolith)** 접근을 채택한다.

**근거**:
- 단일 머신(MacBook)에서 실행
- 컴포넌트 간 통신 오버헤드 불필요
- 배포/운영 복잡성 최소화
- 필요 시 각 Stage를 독립 프로세스로 분리 가능 (모듈 경계 유지)

```
┌──────────────────────────────────────────────────────────────────┐
│                     GlobalNews Agentic Workflow                    │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │              Orchestration Layer                          │      │
│  │  ┌────────────┐   ┌─────────────┐   ┌──────────────┐   │      │
│  │  │ cron       │   │ Claude Code │   │ 상태 관리    │   │      │
│  │  │ (스케줄링) │   │ (구독제     │   │ (state.yaml) │   │      │
│  │  │            │   │  엣지 전용) │   │              │   │      │
│  │  └────────────┘   └─────────────┘   └──────────────┘   │      │
│  └─────────────────────────────────────────────────────────┘      │
│                              ↓                                     │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │              Crawling Layer (Python)                      │      │
│  │  RSS/Sitemap → HTTP/Trafilatura → Playwright/Patchright  │      │
│  │  → 차단 진단 → 6-Tier 에스컬레이션 → Circuit Breaker    │      │
│  └─────────────────────────────────────────────────────────┘      │
│                              ↓                                     │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │              Analysis Layer (Python — 8 Stages)           │      │
│  │  전처리 → 특성추출 → 기사별분석 → 집계 → 시계열          │      │
│  │  → 교차분석 → 신호분류 → 데이터출력                       │      │
│  └─────────────────────────────────────────────────────────┘      │
│                              ↓                                     │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │              Storage Layer                                │      │
│  │  Parquet (ZSTD) │ SQLite (FTS5+vec) │ DuckDB (쿼리)     │      │
│  └─────────────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 실행 모델

| 모드 | 빈도 | 트리거 | 설명 |
|------|------|--------|------|
| **자율 크롤링** | 매일 새벽 | cron | Python 스크립트 자율 실행 (Tier 1-5) |
| **자율 분석** | 크롤링 직후 | cron 체인 | 8-Stage 파이프라인 자동 실행 |
| **엣지 케이스** | 필요 시 | 수동 | Claude Code 대화형 (Tier 6, 실패 로그 분석) |
| **구조 재스캔** | 주 1회 | cron | 사이트 구조 변경 감지 |
| **모델 재학습** | 월 1회 | 수동 | BERTopic 재학습, SetFit 업데이트 |

### 6.3 데이터 플로우

```
sources.yaml
  ↓
[크롤링] → raw_articles/ (JSON Lines)
  ↓
[전처리] → processed_articles/ (Parquet)
  ↓
[특성추출] → features/ (Parquet — 임베딩, TF-IDF, NER)
  ↓
[기사별분석] → article_analysis/ (Parquet — 감정, 분류)
  ↓
[집계분석] → aggregate/ (Parquet — 토픽, 클러스터, 커뮤니티)
  ↓
[시계열] → timeseries/ (Parquet — 버스트, 변화점, 예측)
  ↓
[교차분석] → cross_analysis/ (Parquet — 인과, 네트워크, 프레임)
  ↓
[신호분류] → signals/ (Parquet — 5-Layer 태깅)
  ↓
[최종 출력] → output/
  ├── analysis.parquet (전체 분석 결과)
  ├── signals.parquet (5-Layer 신호)
  ├── index.sqlite (FTS5 전문 검색 + sqlite-vec)
  └── topics.parquet (토픽 모델 결과)
```

### 6.4 Claude Code 오케스트레이터 패턴 (Conductor Pattern)

Claude Code(구독제)는 데이터를 직접 처리하지 않는다. **Generate → Execute → Read → Decide** 루프를 수행한다:

```
┌──────────────────────────────────────────────┐
│           Claude Code (구독제)                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Generate  │→│ Execute   │→│ Read &    │   │
│  │ Python    │  │ via Bash  │  │ Decide    │   │
│  │ Scripts   │  │ Tool      │  │ Next Step │   │
│  └──────────┘  └──────────┘  └──────────┘   │
│       ↑                            │          │
│       └────────────────────────────┘          │
│              (결과 기반 다음 판단)              │
└──────────────────────────────────────────────┘
```

**역할 분리**:

| 컴포넌트 | 역할 | 비용 |
|---------|------|------|
| **cron + Python** | 일상 크롤링 + 분석 (95%) | $0 |
| **Claude Code** | 워크플로우 설계, 스크립트 생성, 엣지 케이스 해결 (5%) | $0 (구독 내) |

---

---

## 7. 산출물 명세

### 7.1 Parquet 스키마 (분석 데이터)

#### 7.1.1 articles.parquet — 기사 원본 + 기본 분석

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `article_id` | STRING | 고유 ID (UUID) |
| `url` | STRING | 원본 URL |
| `title` | STRING | 기사 제목 |
| `body` | STRING | 기사 본문 |
| `source` | STRING | 소스 사이트명 |
| `category` | STRING | 카테고리 (정치/경제/사회/...) |
| `language` | STRING | 언어 코드 (ko/en) |
| `published_at` | TIMESTAMP | 발행일시 |
| `crawled_at` | TIMESTAMP | 수집일시 |
| `author` | STRING (nullable) | 저자 |
| `word_count` | INT32 | 단어 수 |
| `content_hash` | STRING | 본문 해시 (중복 제거) |

#### 7.1.2 analysis.parquet — 기사별 분석 결과

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `article_id` | STRING | FK → articles |
| `sentiment_label` | STRING | 감정 (positive/negative/neutral) |
| `sentiment_score` | FLOAT | 감정 점수 (-1.0 ~ 1.0) |
| `emotion_joy` | FLOAT | Plutchik 기쁨 (0-1) |
| `emotion_trust` | FLOAT | Plutchik 신뢰 (0-1) |
| `emotion_fear` | FLOAT | Plutchik 공포 (0-1) |
| `emotion_surprise` | FLOAT | Plutchik 놀람 (0-1) |
| `emotion_sadness` | FLOAT | Plutchik 슬픔 (0-1) |
| `emotion_disgust` | FLOAT | Plutchik 혐오 (0-1) |
| `emotion_anger` | FLOAT | Plutchik 분노 (0-1) |
| `emotion_anticipation` | FLOAT | Plutchik 기대 (0-1) |
| `topic_id` | INT32 | BERTopic 토픽 ID |
| `topic_label` | STRING | 토픽 레이블 |
| `topic_probability` | FLOAT | 토픽 소속 확률 |
| `steeps_category` | STRING | STEEPS 분류 (S/T/E/En/P/Se) |
| `importance_score` | FLOAT | 중요도 점수 (0-100) |
| `keywords` | LIST<STRING> | KeyBERT 추출 키워드 (Top 10) |
| `entities_person` | LIST<STRING> | NER 인물 |
| `entities_org` | LIST<STRING> | NER 조직 |
| `entities_location` | LIST<STRING> | NER 장소 |
| `embedding` | LIST<FLOAT> | SBERT 임베딩 벡터 |

#### 7.1.3 signals.parquet — 5-Layer 신호 분류

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `signal_id` | STRING | 고유 ID |
| `signal_layer` | STRING | L1_fad / L2_short / L3_mid / L4_long / L5_singularity |
| `signal_label` | STRING | 신호 레이블 |
| `detected_at` | TIMESTAMP | 탐지 시점 |
| `topic_ids` | LIST<INT32> | 관련 토픽 ID 목록 |
| `article_ids` | LIST<STRING> | 관련 기사 ID 목록 |
| `burst_score` | FLOAT (nullable) | Kleinberg 버스트 점수 |
| `changepoint_significance` | FLOAT (nullable) | 변화점 유의도 |
| `novelty_score` | FLOAT (nullable) | LOF/IF 이상 점수 |
| `singularity_composite` | FLOAT (nullable) | 싱귤래리티 복합 점수 (L5만) |
| `evidence_summary` | STRING | 탐지 근거 요약 |
| `confidence` | FLOAT | 분류 신뢰도 (0-1) |

### 7.2 SQLite 스키마 (인덱스/쿼리)

```sql
-- 기사 인덱스 (FTS5 전문 검색)
CREATE VIRTUAL TABLE articles_fts USING fts5(
    article_id UNINDEXED,
    title,
    body,
    source UNINDEXED,
    category UNINDEXED,
    language UNINDEXED,
    published_at UNINDEXED,
    tokenize='unicode61'
);

-- 벡터 인덱스 (sqlite-vec)
CREATE VIRTUAL TABLE article_embeddings USING vec0(
    article_id TEXT PRIMARY KEY,
    embedding FLOAT[384]  -- snowflake-arctic-embed 차원
);

-- 신호 인덱스
CREATE TABLE signals_index (
    signal_id TEXT PRIMARY KEY,
    signal_layer TEXT NOT NULL,
    signal_label TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    confidence REAL,
    article_count INTEGER
);
CREATE INDEX idx_signals_layer ON signals_index(signal_layer);
CREATE INDEX idx_signals_date ON signals_index(detected_at);

-- 토픽 인덱스
CREATE TABLE topics_index (
    topic_id INTEGER PRIMARY KEY,
    label TEXT,
    article_count INTEGER,
    first_seen TEXT,
    last_seen TEXT,
    trend_direction TEXT  -- rising/stable/declining
);

-- 크롤링 상태
CREATE TABLE crawl_status (
    source TEXT NOT NULL,
    last_crawled TEXT NOT NULL,
    articles_count INTEGER,
    success_rate REAL,
    current_tier INTEGER DEFAULT 1
);
```

### 7.3 디렉터리 구조

```
data/
├── raw/                    # 크롤링 원본
│   ├── 2026-02-25/
│   │   ├── chosun.jsonl
│   │   ├── joongang.jsonl
│   │   └── ...
│   └── ...
├── processed/              # 전처리 완료
│   └── articles.parquet
├── features/               # 특성 추출
│   ├── embeddings.parquet
│   ├── tfidf.parquet
│   └── ner.parquet
├── analysis/               # 분석 결과
│   ├── article_analysis.parquet
│   ├── topics.parquet
│   ├── timeseries.parquet
│   ├── networks.parquet
│   └── cross_analysis.parquet
├── output/                 # 최종 산출물
│   ├── analysis.parquet    # 통합 분석 데이터
│   ├── signals.parquet     # 5-Layer 신호
│   └── index.sqlite        # 검색 인덱스
├── models/                 # 학습된 모델
│   ├── bertopic/
│   ├── setfit/
│   └── embeddings/
├── logs/                   # 실행 로그
│   ├── crawl.log
│   ├── analysis.log
│   └── errors.log
└── config/
    ├── sources.yaml        # 뉴스 소스 설정
    └── pipeline.yaml       # 파이프라인 설정
```

### 7.4 데이터 품질 기준

| 기준 | 임계값 | 측정 방법 |
|------|--------|----------|
| 기사 추출 정확도 | ≥ 95% | 수동 샘플링 100건 |
| 중복률 | ≤ 1% | content_hash 기준 |
| 필수 필드 완성률 | ≥ 99% | title, body, source, published_at |
| 감정 분석 정확도 | ≥ 85% | 수동 라벨링 200건 대비 |
| 토픽 일관성 | ≥ 3.0/5.0 | BERTopic coherence score |
| NER 정확도 | ≥ 80% (한국어) | KLUE 벤치마크 기준 |
| 5-Layer 분류 정밀도 | ≥ 70% | 전문가 검토 50건 |

---

---

## 8. 기술 스택

### 8.1 Python 패키지 (전체 목록)

#### 크롤링

| 패키지 | 버전 | 용도 |
|--------|------|------|
| `playwright` | 1.40+ | 동적 브라우저 자동화 |
| `patchright` | - | Playwright CDP 탐지 우회 |
| `trafilatura` | 2.0.0 | 기사 본문 추출 (범용) |
| `fundus` | 0.4.x | 기사 본문 추출 (고정밀) |
| `newspaper4k` | - | 기사 본문 추출 (폴백) |
| `httpx` | 0.27+ | 비동기 HTTP 클라이언트 |
| `feedparser` | 6.0+ | RSS/Atom 파싱 |
| `beautifulsoup4` | 4.12+ | HTML 파싱 |
| `lxml` | 5.0+ | XML/HTML 고속 파싱 |
| `apify-fingerprint-suite` | - | 브라우저 핑거프린트 위장 |
| `simhash` / `datasketch` | - | 콘텐츠 중복 제거 |

#### NLP / 텍스트 분석

| 패키지 | 버전 | 용도 |
|--------|------|------|
| `kiwipiepy` | 0.22.2 | 한국어 형태소 분석 |
| `spacy` | 3.7+ | 영어 NLP 파이프라인 |
| `sentence-transformers` | 3.0+ | SBERT 임베딩 |
| `transformers` | 4.40+ | 로컬 Transformer 모델 |
| `keybert` | 0.8+ | 키워드 추출 |
| `bertopic` | 0.17.4 | 토픽 모델링 |
| `model2vec` | - | BERTopic CPU 가속 |
| `setfit` | 1.0+ | Few-shot 분류 |
| `gensim` | 4.3+ | LDA, Word2Vec |
| `fasttext` | 0.9+ | FastText 단어 벡터 |
| `langdetect` | 1.0+ | 언어 자동 감지 |

#### 시계열 / 통계

| 패키지 | 버전 | 용도 |
|--------|------|------|
| `prophet` | 1.3.0 | 시계열 예측 (10x 속도 향상) |
| `ruptures` | 1.1.10 | 변화점 감지 (PELT) |
| `statsmodels` | 0.14+ | STL 분해, Granger 인과, ARIMA |
| `tigramite` | 5.2.10 | PCMCI 인과 추론 |
| `pywt` | 1.5+ | Wavelet 분석 |
| `scipy` | 1.12+ | 통계 검정, KL Divergence |
| `lifelines` | 0.29+ | 생존 분석 |

#### 네트워크 / 클러스터링

| 패키지 | 버전 | 용도 |
|--------|------|------|
| `networkx` | 3.2+ | 네트워크 분석 |
| `igraph` | 0.11+ | 고속 네트워크 연산 |
| `hdbscan` | 0.8+ | 밀도 기반 클러스터링 |
| `scikit-learn` | 1.4+ | LOF, Isolation Forest, k-means |
| `community` (python-louvain) | 0.16+ | Louvain 커뮤니티 탐지 |

#### 데이터 저장 / 처리

| 패키지 | 버전 | 용도 |
|--------|------|------|
| `pyarrow` | 15.0+ | Parquet 읽기/쓰기 |
| `duckdb` | 0.10+ | 분석 쿼리 |
| `sqlite-vec` | - | SQLite 벡터 확장 |
| `pandas` | 2.2+ | 데이터프레임 처리 |
| `polars` | 0.20+ | 고속 데이터프레임 (대량 처리) |
| `pyyaml` | 6.0+ | YAML 설정 파싱 |

### 8.2 인프라 요구사항

| 항목 | 최소 | 권장 |
|------|------|------|
| **CPU** | Apple M2 (8-core) | Apple M2 Pro (12-core) |
| **RAM** | 16GB | 32GB |
| **저장공간** | 50GB 여유 | 100GB 여유 |
| **Python** | 3.11+ | 3.12 |
| **OS** | macOS 13+ | macOS 14+ |
| **네트워크** | 안정적 인터넷 | 유선 연결 권장 |

### 8.3 메모리 예산

| 컴포넌트 | 피크 메모리 |
|---------|-----------|
| Playwright 브라우저 인스턴스 | ~500MB |
| SBERT 모델 (snowflake-arctic) | ~1.5GB |
| BERTopic + HDBSCAN | ~1-2GB |
| KoBERT/KcELECTRA 감정 모델 | ~500MB |
| 데이터 처리 (pandas/polars) | ~1-2GB |
| **총 피크** | **5-7GB** |

> MacBook M2 Pro 16GB에서 여유 있게 실행 가능. 32GB면 병렬 처리 가능.

---

