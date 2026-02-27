# PRD Analysis Engine Extract

> **Generated**: 2026-02-26T05:18:04Z
> **Source**: `coding-resource/PRD.md`
> **Extracted**: Section 5.2 (Analysis Engine) with all subsections
> **Purpose**: Focused input for pipeline-designer agent (Step 7)

## Extraction Summary

- **Subsections found**: 5
  - 5.2.1: 분석 기법 총괄 (56개)
  - 5.2.2: 8-Stage 분석 파이프라인
  - 5.2.3: 5-Layer 신호 탐지 체계
  - 5.2.4: 싱귤래리티 탐지 (L5 상세)
  - 5.2.5: 한국어 NLP 최적 스택
- **Analysis techniques counted**: 56
- **Pipeline stages found**: 8
- **Signal layers found**: 5

---

## Hard Constraints (Pipeline-Relevant)

> C1 (Claude API = $0) and C3 (MacBook M2 Pro 16GB) directly
> constrain analysis pipeline design choices.

### 핵심 제약 조건

| # | 제약 | 설명 |
|---|------|------|
| **C1** | **Claude API 비용 $0** | Claude API를 호출하지 않는다. 모든 분석은 로컬 Python 라이브러리로 수행한다. Claude Code 구독제 플랜만 사용한다. |
| **C2** | **Claude Code = 오케스트레이터** | Claude Code(구독 내)는 Python 스크립트 생성 → Bash 실행 → 결과 읽기 → 다음 판단의 루프를 수행한다. 데이터를 직접 처리하지 않는다. |
| **C3** | **로컬 머신 실행** | MacBook M2 Pro 16GB 기준. 클라우드 GPU 불필요. |
| **C4** | **산출물 = 구조화된 데이터** | Parquet(분석 데이터) + SQLite(인덱스/쿼리). 리포트/시각화는 범위 밖. |
| **C5** | **합법적 크롤링** | robots.txt 존중, Rate Limiting 준수, 개인정보 미수집. |



---

### 5.2 빅데이터 분석 엔진

#### 5.2.1 분석 기법 총괄 (56개)

**원칙**: "가능한 모든 빅데이터 분석 기법"을 사용한다. 모든 분석은 로컬 Python 라이브러리로 수행하며, Claude API는 사용하지 않는다.

**분석 대상**: 기사 **제목 + 본문** (K3 — 메타데이터만으로는 불충분)

| 영역 | 기법 수 | 대표 기법 | Python 라이브러리 |
|------|--------|----------|-----------------|
| **텍스트 처리·특성 추출** | 12 | SBERT 임베딩, TF-IDF, NER, KeyBERT, FastText, 형태소 분석 | sentence-transformers, scikit-learn, kiwipiepy, keybert |
| **토픽 모델링·클러스터링** | 8 | BERTopic, DTM, HDBSCAN, NMF, LDA, k-means, 계층적 클러스터링 | bertopic, hdbscan, scikit-learn, gensim |
| **감정·감성 분석** | 6 | KoBERT 감정, 8차원 감정(Plutchik), 입장 탐지, 사회 무드 지수, 감정 궤적 | transformers(로컬 모델), kcelectra |
| **시계열 분석** | 8 | STL 분해, 변화점 감지(PELT), Kleinberg 버스트, Prophet 예측, Wavelet, ARIMA, 이동평균 교차, 계절성 | prophet, ruptures, statsmodels, pywt |
| **네트워크·관계 분석** | 5 | 공출현 네트워크, 지식 그래프, 커뮤니티 탐지, 중심성 분석, 네트워크 진화 | networkx, igraph, community |
| **통계·수학 방법** | 7 | Novelty 탐지(LOF/Isolation Forest), 엔트로피 변화, Zipf 분포 편차, 생존 분석, KL Divergence, Z-score 이상 탐지, Granger 인과 | scikit-learn, scipy, lifelines, statsmodels |
| **교차 차원 분석** | 4 | 교차 국가 비교, 프레임 분석, 의제 설정, 시간 정렬 | sentence-transformers, scipy |
| **AI/ML 분석** | 6 | Zero-shot 분류, 인과 추론(PCMCI), 서사 추출, 모순 탐지, SetFit 분류, GraphRAG | setfit, tigramite, transformers(로컬) |

> **중요**: "AI/ML 분석" 영역의 모든 기법은 **로컬에서 실행되는 오픈소스 모델**을 사용한다. Claude API를 호출하지 않는다. Zero-shot 분류는 `facebook/bart-large-mnli` 등 로컬 모델을, SetFit는 8개 예시만으로 fine-tuning하는 few-shot 모델을 사용한다.

#### 5.2.2 8-Stage 분석 파이프라인

```
Stage 1: 전처리
  • 한국어: Kiwi 형태소 분석 → 명사/동사/형용사 추출 → 불용어 제거
  • 영어: spaCy → lemmatization → 불용어 제거
  • 공통: 문장 분리, 정규화, 언어 감지
  ↓
Stage 2: 특성 추출
  • SBERT 임베딩 (한국어: snowflake-arctic-embed-l-v2.0-ko)
  • TF-IDF (단어/바이그램)
  • NER (한국어: KLUE-RoBERTa-large, 영어: spaCy)
  • KeyBERT 키워드 추출
  • FastText 단어 벡터 (언어별)
  ↓
Stage 3: 기사별 분석
  • 감정 분석 (한국어: KoBERT F1=94%, 영어: 로컬 transformer)
  • 8차원 감정 분류 (Plutchik 모델: 기쁨/신뢰/공포/놀람/슬픔/혐오/분노/기대)
  • Zero-shot 주제 분류 (STEEPS: Social/Technology/Economic/Environmental/Political/Security)
  • 중요도 점수 산출
  ↓
Stage 4: 집계 분석
  • BERTopic 토픽 모델링 (Model2Vec로 CPU 500x 속도)
  • Dynamic Topic Modeling (시간별 토픽 변화)
  • HDBSCAN 클러스터링
  • NMF/LDA 보조 토픽
  • 커뮤니티 탐지 (Louvain)
  ↓
Stage 5: 시계열 분석
  • STL 분해 (트렌드/계절/잔차)
  • Kleinberg 버스트 탐지 (이슈 폭발)
  • 변화점 감지 — PELT 알고리즘 (ruptures)
  • Prophet 예측 (다음 7/30일)
  • Wavelet 분석 (다중 주기)
  • 이동평균 교차 (단기/장기)
  ↓
Stage 6: 교차 분석
  • Granger 인과 검정 (토픽 간 시간적 선행 관계)
  • PCMCI 인과 추론 (tigramite — 다변량 시계열)
  • 공출현 네트워크 (entity-entity, topic-topic)
  • 교차 언어 토픽 정렬 (한국어↔영어)
  • 프레임 분석 (동일 이슈의 보도 프레임 비교)
  ↓
Stage 7: 신호 분류 (5-Layer)
  • 규칙 기반 5-Layer 분류 (아래 상세)
  • Novelty 탐지 (LOF, Isolation Forest)
  • BERTrend weak signal → emerging signal 전환 감지
  • 싱귤래리티 복합 점수 산출
  ↓
Stage 8: 데이터 출력
  • Parquet (ZSTD 압축) — 분석 결과 데이터
  • SQLite (FTS5 전문 검색 + sqlite-vec 벡터 검색) — 인덱스/쿼리
  • DuckDB 쿼리 호환
```

#### 5.2.3 5-Layer 신호 탐지 체계

| Layer | 신호 유형 | 시간 범위 | 핵심 탐지 기법 | 최소 데이터 |
|-------|----------|----------|-------------|-----------|
| **L1** | **유행 (Fad)** | 일 ~ 2주 | Kleinberg 버스트 + Z-score 이상 탐지 | 7일 |
| **L2** | **단기 트렌드** | 2주 ~ 3개월 | BERTopic DTM + 감정 궤적 + 이동평균 교차 | 30일 |
| **L3** | **중기 트렌드** | 3개월 ~ 1년 | 변화점 감지(PELT) + 네트워크 진화 + 프레임 분석 | 6개월 |
| **L4** | **장기 트렌드** | 1 ~ 5년 | 임베딩 드리프트 + Wavelet + STEEPS 분류 | 2년+ |
| **L5** | **싱귤래리티** | 비주기 | Novelty 점수 + 교차 도메인 출현 + BERTrend weak→emerging 전환 + 복합 7지표 점수 | 6개월+ |

**Dual-Pass 분석 전략 (K3 준수)**:

| Pass | 대상 | 역할 | 기법 |
|------|------|------|------|
| **Pass 1: 제목** | 기사 제목 | 신호 탐지 (빠른 스캔) | 키워드 빈도, 버스트 감지, 감정 극성 |
| **Pass 2: 본문** | 기사 전문 | 증거 확보 (심층 분석) | NER, 토픽 모델링, 프레임 분석, 인과 추론 |

> 제목은 "무엇이 일어나고 있는가"를, 본문은 "왜, 어떻게 일어나고 있는가"를 답한다.

#### 5.2.4 싱귤래리티 탐지 (L5 상세)

"전례 없는 신호"를 탐지하기 위한 3가지 독립 경로 교차 검증:

| 경로 | 방법 | 설명 |
|------|------|------|
| **OOD 감지** | Out-of-Distribution (LOF, Isolation Forest) | 기존 토픽 분류에 속하지 않는 기사 감지 |
| **변화점 감지** | PELT + 확률 분포 변화 | 기사 빈도, 감정, 토픽 분포의 구조적 전환점 |
| **BERTrend** | weak signal → emerging 전환 | 약한 신호가 처음 떠오르는 시점 포착 |

**싱귤래리티 복합 점수 공식**:

```
S_singularity = w1 × OOD_score
              + w2 × Changepoint_significance
              + w3 × CrossDomain_emergence
              + w4 × BERTrend_transition
              + w5 × Entropy_spike
              + w6 × Novelty_score
              + w7 × Network_anomaly

(w1-w7: 도메인 전문가 또는 그리드 서치로 조정)
```

#### 5.2.5 한국어 NLP 최적 스택

| 용도 | 최적 도구 | 버전 | 근거 |
|------|---------|------|------|
| 형태소 분석 | **Kiwi** (kiwipiepy) | 0.22.2 | 속도+정확도+설치 용이성 최적 조합, 뉴스 도메인 94% |
| 감정 분석 (뉴스) | **KoBERT** | - | 뉴스 도메인 F1=94% |
| 감정 분석 (비격식) | **KcELECTRA** | Base-v3 | 웹 텍스트 최적, 감정 90.6%, NER 88.1% |
| NER | **KLUE-RoBERTa-large** | - | KLUE 벤치마크 최고 성능 |
| 문서 임베딩 | **snowflake-arctic-embed-l-v2.0-ko** | - | 7개 한국어 검색 벤치마크 SOTA |
| 토픽 모델링 | **BERTopic** + **Model2Vec** | 0.17.4 | CPU에서 500x 속도 향상, 품질 유지 |
| 분류 | **SetFit** | - | 8개 예시만으로 RoBERTa 3K 수준 달성 |

---


---

## Output Schema Reference (PRD 7.1 — Parquet)

> The pipeline-designer must ensure each stage's output columns
> align with these Parquet schema definitions.

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

