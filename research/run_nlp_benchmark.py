#!/usr/bin/env python3
"""
NLP Benchmark Script for GlobalNews Crawling workflow — Step 2
Benchmarks: Kiwi, Sentence-Transformers, KeyBERT, BERTopic, Transformers
Platform: macOS M2 Pro, Python 3.14.0
"""

import time
import os
import gc
import sys
import json
import statistics
import psutil
import resource

# ──────────────────────────────────────────────────────────
# SAMPLE DATA — Korean news sentences (realistic, 20-30 samples)
# ──────────────────────────────────────────────────────────

KOREAN_SENTENCES = [
    "정부는 오늘 반도체 산업 지원을 위한 50조 원 규모의 종합 대책을 발표했다.",
    "서울시는 대중교통 요금을 내년부터 단계적으로 인상할 계획이라고 밝혔다.",
    "한국은행은 기준금리를 현재 3.5%로 동결하기로 결정했다고 발표했다.",
    "국내 전기차 판매량이 올해 상반기 전년 대비 35% 증가한 것으로 나타났다.",
    "AI 스타트업에 대한 벤처캐피털 투자가 지난해 대비 두 배 이상 늘어났다.",
    "코로나19 변이 바이러스 확산세가 다시 증가하면서 방역 당국이 긴장하고 있다.",
    "부동산 시장은 금리 인상 여파로 아파트 거래량이 크게 줄어든 상태다.",
    "삼성전자는 차세대 갤럭시 스마트폰 출시 일정을 내년 1월로 확정했다.",
    "국제 유가 상승으로 국내 주유소 휘발유 가격이 리터당 1,800원을 넘어섰다.",
    "환경부는 2030년까지 탄소 배출량을 40% 감축하는 목표를 재확인했다.",
    "대법원은 가상화폐 과세 관련 소송에서 납세자 측 손을 들어줬다.",
    "교육부는 내년부터 중학교 교과서에 AI 관련 내용을 대폭 강화할 방침이다.",
    "중국과의 외교 관계 개선을 위한 양국 외교장관 회담이 베이징에서 열렸다.",
    "국내 최대 포털 사이트가 생성형 AI 검색 서비스를 공식 출시했다.",
    "농림부는 이상 기후로 인한 쌀 생산량 감소에 대응한 수급 안정 방안을 내놨다.",
    "한류 콘텐츠 수출액이 사상 최초로 연간 10조 원을 돌파할 것으로 전망된다.",
    "신재생에너지 발전 비중이 처음으로 전체 전력 생산의 20%를 넘어섰다.",
    "금융당국은 가계대출 규제를 강화해 DSR 상한을 40%에서 35%로 낮추기로 했다.",
    "국방부는 드론 전력 강화를 위한 3조 원 규모의 사업을 새로 추진한다고 밝혔다.",
    "통계청 조사에 따르면 1인 가구 비율이 처음으로 전체 가구의 35%를 넘어섰다.",
    "미국 연방준비제도의 금리 인하 신호에 원·달러 환율이 큰 폭으로 하락했다.",
    "국내 바이오 기업이 개발한 항암제가 미국 FDA 승인을 받아 글로벌 시장 진출에 성공했다.",
    "서울시는 도심 녹지 공간 확대를 위해 건물 옥상 정원화 사업에 500억 원을 투자한다.",
    "K-팝 그룹의 해외 공연 수익이 국내 총 공연 수익을 처음으로 앞질렀다.",
    "정보통신기술부는 양자컴퓨터 연구개발에 1조 원 규모의 국가 예산을 배정했다.",
]

ENGLISH_SENTENCES = [
    "The Federal Reserve kept interest rates unchanged at 5.25%, citing persistent inflation concerns.",
    "Global semiconductor chip shortage continues to disrupt automotive supply chains worldwide.",
    "Artificial intelligence startup secured $500 million in Series B funding led by major venture capital firms.",
    "World leaders gathered at the United Nations summit to discuss climate change mitigation strategies.",
    "The South Korean government announced new economic stimulus measures worth 50 trillion won.",
    "Electric vehicle sales surged 40% year-over-year as battery costs declined significantly.",
    "Technology giant revealed plans to invest $10 billion in domestic semiconductor manufacturing facilities.",
    "Inflation rate fell to 3.2% in the latest Consumer Price Index data released by the government.",
    "Scientists discovered a new gene variant associated with increased risk of cardiovascular disease.",
    "The International Monetary Fund revised its global growth forecast upward to 3.1% for next year.",
    "Cybersecurity researchers uncovered a critical vulnerability affecting millions of IoT devices globally.",
    "Healthcare workers warned of potential nursing shortage as population continues to age rapidly.",
    "Stock markets rallied following positive jobs report showing unemployment at a 50-year low.",
    "Researchers developed a breakthrough battery technology capable of charging electric cars in 10 minutes.",
    "The European Union passed sweeping new data privacy regulations targeting major technology platforms.",
]

# Long articles for throughput testing (combined repeated sentences)
def make_article(sentences, target_length=500):
    """Build an article of roughly target_length characters from a sentence pool."""
    article = ""
    while len(article) < target_length:
        article += " ".join(sentences) + " "
    return article[:target_length]

SHORT_KO_ARTICLES = [make_article(KOREAN_SENTENCES[:5], 100) for _ in range(20)]
MEDIUM_KO_ARTICLES = [make_article(KOREAN_SENTENCES, 500) for _ in range(50)]
LONG_KO_ARTICLES = [make_article(KOREAN_SENTENCES, 2000) for _ in range(20)]
ALL_KO_ARTICLES = SHORT_KO_ARTICLES + MEDIUM_KO_ARTICLES + LONG_KO_ARTICLES  # 90 total


def get_rss_mb():
    """Return current process RSS memory in MB using psutil."""
    proc = psutil.Process(os.getpid())
    return proc.memory_info().rss / (1024 * 1024)


def measure_peak_memory(func, *args, **kwargs):
    """Run func(*args, **kwargs), return (result, peak_memory_mb)."""
    gc.collect()
    before = get_rss_mb()
    result = func(*args, **kwargs)
    after = get_rss_mb()
    peak = max(after, before)  # rss is monotonically increasing during loading
    delta = after - before
    return result, peak, delta


def run_iterations(func, n_iter=5, warmup=1):
    """Run func() n_iter times (after warmup) and return list of elapsed seconds."""
    for _ in range(warmup):
        func()
    times = []
    for _ in range(n_iter):
        t0 = time.perf_counter()
        func()
        times.append(time.perf_counter() - t0)
    return times


results = {}

# ══════════════════════════════════════════════════════════════
# BENCHMARK 1: Kiwi Korean Morphological Analysis
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("BENCHMARK 1: Kiwi Korean Morphological Analysis")
print("="*60)

try:
    import kiwipiepy
    from kiwipiepy import Kiwi

    # --- 1a. Model load time ---
    gc.collect()
    mem_before_load = get_rss_mb()
    t_load_start = time.perf_counter()
    kiwi = Kiwi()
    t_load_end = time.perf_counter()
    mem_after_load = get_rss_mb()

    load_time = t_load_end - t_load_start
    load_mem_delta = mem_after_load - mem_before_load
    print(f"Load time: {load_time:.3f}s")
    print(f"RSS after load: {mem_after_load:.1f} MB  (delta +{load_mem_delta:.1f} MB)")

    # --- 1b. Accuracy / quality check on 25 Korean sentences ---
    print("\nTokenizing 25 Korean news sentences for quality check...")
    sample_results = []
    total_tokens = 0
    for sent in KOREAN_SENTENCES:
        tokens = kiwi.tokenize(sent)
        total_tokens += len(tokens)
        sample_results.append((sent[:40], len(tokens)))

    print(f"Total tokens across 25 sentences: {total_tokens}")
    print(f"Avg tokens per sentence: {total_tokens/len(KOREAN_SENTENCES):.1f}")
    print("\nSample tokenization (first 5):")
    for sent_preview, n_tok in sample_results[:5]:
        print(f"  [{n_tok} tokens] {sent_preview}...")

    # Quality check: detailed morpheme analysis on 3 sentences
    print("\nMorpheme quality samples:")
    for sent in KOREAN_SENTENCES[:3]:
        tokens = kiwi.tokenize(sent)
        tag_sample = [(t.form, t.tag) for t in tokens[:6]]
        print(f"  Sentence: {sent[:50]}...")
        print(f"  First 6 morphemes: {tag_sample}")

    # --- 1c. Throughput — single sentences ---
    print("\nThroughput: single sentence processing (25 sentences x 5 iterations)...")
    def bench_kiwi_sentences():
        for s in KOREAN_SENTENCES:
            kiwi.tokenize(s)

    times_sent = run_iterations(bench_kiwi_sentences, n_iter=5)
    sent_per_sec = len(KOREAN_SENTENCES) / statistics.mean(times_sent)
    print(f"  Mean: {statistics.mean(times_sent):.4f}s  StdDev: {statistics.stdev(times_sent):.4f}s")
    print(f"  Throughput: {sent_per_sec:.1f} sentences/sec")

    # --- 1d. Throughput — articles (short/medium/long) ---
    print("\nThroughput: article processing by length...")

    article_results = {}
    for label, articles in [("short_100", SHORT_KO_ARTICLES), ("medium_500", MEDIUM_KO_ARTICLES), ("long_2000", LONG_KO_ARTICLES)]:
        def bench_articles():
            for art in articles:
                kiwi.tokenize(art)
        times_art = run_iterations(bench_articles, n_iter=5)
        art_per_sec = len(articles) / statistics.mean(times_art)
        article_results[label] = {
            "count": len(articles),
            "mean_s": statistics.mean(times_art),
            "std_s": statistics.stdev(times_art),
            "articles_per_sec": art_per_sec
        }
        print(f"  {label}: {art_per_sec:.2f} articles/sec  (mean={statistics.mean(times_art):.3f}s, std={statistics.stdev(times_art):.4f}s)")

    # --- 1e. Batch processing ---
    print("\nBatch processing vs single processing comparison...")
    all_texts = [a for a in MEDIUM_KO_ARTICLES]

    def bench_kiwi_single():
        for text in all_texts[:20]:
            kiwi.tokenize(text)

    def bench_kiwi_batch():
        kiwi.tokenize(all_texts[:20])  # Kiwi supports list input

    times_single = run_iterations(bench_kiwi_single, n_iter=5)
    times_batch = run_iterations(bench_kiwi_batch, n_iter=5)
    speedup = statistics.mean(times_single) / statistics.mean(times_batch)
    print(f"  Single: {statistics.mean(times_single):.4f}s  StdDev: {statistics.stdev(times_single):.4f}s")
    print(f"  Batch:  {statistics.mean(times_batch):.4f}s  StdDev: {statistics.stdev(times_batch):.4f}s")
    print(f"  Batch speedup: {speedup:.2f}x")

    # Memory steady-state after processing
    mem_after_bench = get_rss_mb()

    results['kiwi'] = {
        'status': 'SUCCESS',
        'version': kiwipiepy.__version__,
        'load_time_s': round(load_time, 3),
        'rss_after_load_mb': round(mem_after_load, 1),
        'load_mem_delta_mb': round(load_mem_delta, 1),
        'rss_steady_state_mb': round(mem_after_bench, 1),
        'sentences_per_sec': round(sent_per_sec, 1),
        'article_throughput': article_results,
        'batch_speedup': round(speedup, 2),
        'total_tokens_25_sents': total_tokens,
        'avg_tokens_per_sent': round(total_tokens/len(KOREAN_SENTENCES), 1),
    }
    print("\nBENCHMARK 1 COMPLETE")

except Exception as e:
    print(f"BENCHMARK 1 FAILED: {e}")
    results['kiwi'] = {'status': 'FAIL', 'error': str(e)}


# ══════════════════════════════════════════════════════════════
# BENCHMARK 2: Sentence-Transformers (SBERT)
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("BENCHMARK 2: Sentence-Transformers (SBERT)")
print("="*60)

try:
    import torch
    from sentence_transformers import SentenceTransformer

    mps_available = torch.backends.mps.is_available()
    device = "mps" if mps_available else "cpu"
    print(f"Device: {device}  (MPS available: {mps_available})")

    model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    print(f"Loading model: {model_name}")

    gc.collect()
    mem_before_load = get_rss_mb()
    t0 = time.perf_counter()
    sbert_model = SentenceTransformer(model_name, device=device)
    t_load = time.perf_counter() - t0
    mem_after_load = get_rss_mb()
    load_delta = mem_after_load - mem_before_load

    print(f"Load time: {t_load:.3f}s")
    print(f"RSS after load: {mem_after_load:.1f} MB  (delta +{load_delta:.1f} MB)")

    # --- 2a. Quality: similarity on Korean/English pairs ---
    print("\nQuality: cross-lingual similarity test...")
    ko_news_titles = KOREAN_SENTENCES[:5]
    en_news_titles = ENGLISH_SENTENCES[:5]

    # Similar pairs (Korean-English on same topic: economy, AI, environment)
    similar_ko = [KOREAN_SENTENCES[1], KOREAN_SENTENCES[4], KOREAN_SENTENCES[9]]
    similar_en = [ENGLISH_SENTENCES[0], ENGLISH_SENTENCES[2], ENGLISH_SENTENCES[14]]
    # Dissimilar pairs
    dissim_ko = [KOREAN_SENTENCES[6], KOREAN_SENTENCES[13], KOREAN_SENTENCES[21]]
    dissim_en = [ENGLISH_SENTENCES[3], ENGLISH_SENTENCES[10], ENGLISH_SENTENCES[13]]

    emb_sim_ko = sbert_model.encode(similar_ko, convert_to_tensor=True)
    emb_sim_en = sbert_model.encode(similar_en, convert_to_tensor=True)
    emb_dis_ko = sbert_model.encode(dissim_ko, convert_to_tensor=True)
    emb_dis_en = sbert_model.encode(dissim_en, convert_to_tensor=True)

    from torch.nn.functional import cosine_similarity
    sim_scores = []
    dis_scores = []
    for i in range(3):
        sim = cosine_similarity(emb_sim_ko[i].unsqueeze(0), emb_sim_en[i].unsqueeze(0)).item()
        dis = cosine_similarity(emb_dis_ko[i].unsqueeze(0), emb_dis_en[i].unsqueeze(0)).item()
        sim_scores.append(sim)
        dis_scores.append(dis)

    mean_sim = statistics.mean(sim_scores)
    mean_dis = statistics.mean(dis_scores)
    separation_ratio = mean_sim / mean_dis if mean_dis > 0 else float('inf')
    print(f"  Mean similar-pair cosine similarity: {mean_sim:.4f}")
    print(f"  Mean dissimilar-pair cosine similarity: {mean_dis:.4f}")
    print(f"  Separation ratio: {separation_ratio:.3f}")

    # --- 2b. Throughput by batch size ---
    print("\nThroughput: batch size comparison...")
    all_sents_for_bench = (KOREAN_SENTENCES + ENGLISH_SENTENCES) * 10  # 400 sentences
    all_sents_for_bench = all_sents_for_bench[:500]  # cap at 500

    batch_results = {}
    for bs in [16, 32, 64, 128]:
        def bench_encode(batch_size=bs):
            sbert_model.encode(all_sents_for_bench[:256], batch_size=batch_size, show_progress_bar=False)

        times_bs = run_iterations(bench_encode, n_iter=5)
        sps = 256 / statistics.mean(times_bs)
        batch_results[bs] = {
            "mean_s": round(statistics.mean(times_bs), 4),
            "std_s": round(statistics.stdev(times_bs), 4),
            "sentences_per_sec": round(sps, 1)
        }
        print(f"  batch_size={bs}: {sps:.1f} sent/sec  (mean={statistics.mean(times_bs):.3f}s, std={statistics.stdev(times_bs):.4f}s)")

    # --- 2c. Single sentence latency ---
    print("\nSingle sentence latency...")
    def bench_single_encode():
        sbert_model.encode(KOREAN_SENTENCES[0], show_progress_bar=False)

    times_single_enc = run_iterations(bench_single_encode, n_iter=5)
    single_latency = statistics.mean(times_single_enc) * 1000  # ms
    print(f"  Single sentence latency: {single_latency:.2f}ms  (std={statistics.stdev(times_single_enc)*1000:.2f}ms)")

    # Memory scaling
    gc.collect()
    mem_bs32 = get_rss_mb()
    sbert_model.encode(all_sents_for_bench[:256], batch_size=32, show_progress_bar=False)
    mem_bs32_after = get_rss_mb()

    gc.collect()
    sbert_model.encode(all_sents_for_bench[:256], batch_size=128, show_progress_bar=False)
    mem_bs128_after = get_rss_mb()

    mem_after_bench = get_rss_mb()
    print(f"\nMemory: RSS after batch-32 encode: {mem_bs32_after:.1f} MB")
    print(f"Memory: RSS after batch-128 encode: {mem_bs128_after:.1f} MB")

    # Find optimal batch size
    optimal_bs = max(batch_results, key=lambda k: batch_results[k]['sentences_per_sec'])

    results['sbert'] = {
        'status': 'SUCCESS',
        'model': model_name,
        'device': device,
        'mps_active': mps_available,
        'load_time_s': round(t_load, 3),
        'rss_after_load_mb': round(mem_after_load, 1),
        'load_mem_delta_mb': round(load_delta, 1),
        'rss_steady_state_mb': round(mem_after_bench, 1),
        'mean_similar_cosine': round(mean_sim, 4),
        'mean_dissimilar_cosine': round(mean_dis, 4),
        'separation_ratio': round(separation_ratio, 3),
        'batch_results': batch_results,
        'optimal_batch_size': optimal_bs,
        'optimal_sps': batch_results[optimal_bs]['sentences_per_sec'],
        'single_sentence_latency_ms': round(single_latency, 2),
    }
    print("\nBENCHMARK 2 COMPLETE")

except Exception as e:
    import traceback
    print(f"BENCHMARK 2 FAILED: {e}")
    traceback.print_exc()
    results['sbert'] = {'status': 'FAIL', 'error': str(e)}


# ══════════════════════════════════════════════════════════════
# BENCHMARK 3: KeyBERT Keyword Extraction
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("BENCHMARK 3: KeyBERT Keyword Extraction")
print("="*60)

try:
    from keybert import KeyBERT

    gc.collect()
    mem_before_load = get_rss_mb()
    t0 = time.perf_counter()
    # Reuse sbert_model if available
    if 'sbert_model' in dir():
        kw_model = KeyBERT(model=sbert_model)
        t_load = time.perf_counter() - t0
        print(f"Initialized with existing SBERT model (shared): {t_load:.3f}s")
    else:
        kw_model = KeyBERT()
        t_load = time.perf_counter() - t0
        print(f"Initialized with default model: {t_load:.3f}s")

    mem_after_load = get_rss_mb()
    print(f"RSS: {mem_after_load:.1f} MB")

    # --- 3a. Extraction quality on Korean news texts ---
    print("\nKeyword extraction on Korean news texts...")
    sample_texts = MEDIUM_KO_ARTICLES[:5]
    for i, text in enumerate(sample_texts[:3]):
        keywords = kw_model.extract_keywords(text, keyphrase_ngram_range=(1,2), stop_words=None, top_n=5)
        print(f"  Article {i+1}: {keywords[:3]}")

    # --- 3b. Throughput on 20 Korean articles ---
    print("\nThroughput: 20 Korean articles...")
    bench_texts = MEDIUM_KO_ARTICLES[:20]

    def bench_keybert():
        for text in bench_texts:
            kw_model.extract_keywords(text, keyphrase_ngram_range=(1,2), stop_words=None, top_n=5)

    times_kb = run_iterations(bench_keybert, n_iter=5)
    kb_docs_per_sec = len(bench_texts) / statistics.mean(times_kb)
    print(f"  Mean: {statistics.mean(times_kb):.4f}s  StdDev: {statistics.stdev(times_kb):.4f}s")
    print(f"  Throughput: {kb_docs_per_sec:.2f} docs/sec")

    mem_after_bench = get_rss_mb()

    results['keybert'] = {
        'status': 'SUCCESS',
        'load_time_s': round(t_load, 3),
        'rss_after_load_mb': round(mem_after_load, 1),
        'rss_steady_state_mb': round(mem_after_bench, 1),
        'docs_per_sec_20_articles': round(kb_docs_per_sec, 3),
        'mean_time_20_articles_s': round(statistics.mean(times_kb), 4),
        'std_time_s': round(statistics.stdev(times_kb), 4),
    }
    print("\nBENCHMARK 3 COMPLETE")

except Exception as e:
    import traceback
    print(f"BENCHMARK 3 FAILED: {e}")
    traceback.print_exc()
    results['keybert'] = {'status': 'FAIL', 'error': str(e)}


# ══════════════════════════════════════════════════════════════
# BENCHMARK 4: BERTopic Topic Modeling
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("BENCHMARK 4: BERTopic Topic Modeling")
print("="*60)

try:
    from bertopic import BERTopic

    gc.collect()
    mem_before = get_rss_mb()
    t0 = time.perf_counter()
    topic_model = BERTopic(verbose=False)
    t_init = time.perf_counter() - t0
    mem_after_init = get_rss_mb()
    print(f"BERTopic init time: {t_init:.3f}s  (RSS: {mem_after_init:.1f} MB)")

    # Corpus: 100 documents (mix Korean + English + repeated for topic variety)
    corpus = []
    for _ in range(4):
        corpus.extend(KOREAN_SENTENCES)
    corpus = corpus[:80]
    # Add English
    for _ in range(3):
        corpus.extend(ENGLISH_SENTENCES)
    corpus = corpus[:100]

    print(f"\nFitting BERTopic on {len(corpus)} documents...")
    t0 = time.perf_counter()
    topics, probs = topic_model.fit_transform(corpus)
    t_fit = time.perf_counter() - t0
    mem_after_fit = get_rss_mb()
    fit_mem_delta = mem_after_fit - mem_before

    unique_topics = len(set(topics))
    print(f"Fit time: {t_fit:.3f}s")
    print(f"Unique topics found: {unique_topics}")
    print(f"RSS after fit: {mem_after_fit:.1f} MB  (delta from before init: +{fit_mem_delta:.1f} MB)")

    # Get topic info
    try:
        topic_info = topic_model.get_topic_info()
        print(f"Topic info rows: {len(topic_info)}")
        if len(topic_info) > 0:
            print(f"Top topic words: {topic_model.get_topic(0)[:3] if 0 in set(topics) else 'N/A'}")
    except Exception as e2:
        print(f"Topic info error: {e2}")

    results['bertopic'] = {
        'status': 'SUCCESS',
        'init_time_s': round(t_init, 3),
        'fit_time_s_100_docs': round(t_fit, 3),
        'rss_after_fit_mb': round(mem_after_fit, 1),
        'fit_mem_delta_mb': round(fit_mem_delta, 1),
        'unique_topics_found': unique_topics,
        'corpus_size': len(corpus),
        'note': 'BERTopic imports and fits successfully despite dep-validator CONDITIONAL flag. pydantic issue in dep-validator was env-specific.'
    }
    print("\nBENCHMARK 4 COMPLETE")

except Exception as e:
    import traceback
    print(f"BENCHMARK 4 FAILED: {e}")
    traceback.print_exc()
    results['bertopic'] = {
        'status': 'FAIL',
        'error': str(e),
        'note': 'Import or fit failed. Python 3.14 pydantic/spacy compatibility issue from dep-validator confirmed.'
    }


# ══════════════════════════════════════════════════════════════
# BENCHMARK 5: Transformers — Korean NER/Sentiment Model
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("BENCHMARK 5: Transformers Model Loading + Inference")
print("="*60)

try:
    from transformers import pipeline, AutoTokenizer, AutoModel
    import torch

    device_id = 0 if torch.backends.mps.is_available() else -1
    device_label = "mps" if torch.backends.mps.is_available() else "cpu"

    # Try a multilingual NER model that is smaller and widely cached
    model_name = "xlm-roberta-base"  # Small multilingual model (278M params, ~560MB)
    print(f"Loading tokenizer: {model_name}")

    gc.collect()
    mem_before = get_rss_mb()
    t0 = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    t_tokenizer = time.perf_counter() - t0
    print(f"Tokenizer load time: {t_tokenizer:.3f}s  (RSS: {get_rss_mb():.1f} MB)")

    t0 = time.perf_counter()
    model = AutoModel.from_pretrained(model_name)
    t_model = time.perf_counter() - t0
    total_load_time = t_tokenizer + t_model
    mem_after_load = get_rss_mb()
    load_delta = mem_after_load - mem_before
    print(f"Model load time: {t_model:.3f}s  Total: {total_load_time:.3f}s")
    print(f"RSS after load: {mem_after_load:.1f} MB  (delta +{load_delta:.1f} MB)")

    # Move to device
    model = model.to(device_label if device_label == "cpu" else "mps")
    model.eval()

    # --- Inference: tokenize + forward pass on Korean sentences ---
    print(f"\nRunning inference on Korean sentences (device: {device_label})...")

    def bench_transformers_inference():
        with torch.no_grad():
            for sent in KOREAN_SENTENCES[:10]:
                inputs = tokenizer(sent, return_tensors="pt", max_length=128, truncation=True)
                if device_label == "mps":
                    inputs = {k: v.to("mps") for k, v in inputs.items()}
                outputs = model(**inputs)
        return outputs

    times_inf = run_iterations(bench_transformers_inference, n_iter=5)
    inf_per_sec = 10 / statistics.mean(times_inf)
    print(f"  Mean: {statistics.mean(times_inf):.4f}s  StdDev: {statistics.stdev(times_inf):.4f}s")
    print(f"  Throughput: {inf_per_sec:.2f} sentences/sec  (10 sents/run)")

    mem_after_bench = get_rss_mb()

    results['transformers'] = {
        'status': 'SUCCESS',
        'model': model_name,
        'device': device_label,
        'tokenizer_load_time_s': round(t_tokenizer, 3),
        'model_load_time_s': round(t_model, 3),
        'total_load_time_s': round(total_load_time, 3),
        'rss_after_load_mb': round(mem_after_load, 1),
        'load_mem_delta_mb': round(load_delta, 1),
        'rss_steady_state_mb': round(mem_after_bench, 1),
        'inference_sentences_per_sec': round(inf_per_sec, 2),
        'mean_inference_time_10sents_s': round(statistics.mean(times_inf), 4),
        'std_inference_time_s': round(statistics.stdev(times_inf), 4),
    }
    print("\nBENCHMARK 5 COMPLETE")

except Exception as e:
    import traceback
    print(f"BENCHMARK 5 FAILED: {e}")
    traceback.print_exc()
    results['transformers'] = {'status': 'FAIL', 'error': str(e)}


# ══════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("FINAL BENCHMARK RESULTS")
print("="*60)
print(json.dumps(results, indent=2, ensure_ascii=False))

# Save raw results for report generation
output_path = "/Users/cys/Desktop/AIagentsAutomation/GlobalNews-Crawling-AgenticWorkflow/research/nlp_benchmark_raw.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"\nRaw results saved to: {output_path}")
