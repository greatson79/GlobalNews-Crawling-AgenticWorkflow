# E2E 구조적 검증 보고서

## 테스트 환경
- **날짜**: 2026-02-26
- **Python**: 3.14.0
- **플랫폼**: Darwin 25.3.0 (arm64)
- **총 소요 시간**: 17.4초
- **최대 메모리 사용량**: 0.189 GB
- **테스트 유형**: 구조적 검증 (네트워크 접근 없음)

## 검증 요약

| 범주 | 전체 | Pass | Fail | Warn |
|------|------|------|------|------|
| 검사 항목 | 13 | 12 | 0 | 1 |
| 사이트 (어댑터) | 44 | 44 | 0 | - |
| 분석 단계 | 8 | 8 | 0 | - |

## 전체 구조적 판정: **PASS**

## PRD 검증 기준 (V1-V12)

| # | 기준 | 검증 유형 | Status | 비고 |
|---|------|----------|--------|------|
| V1 | 44개 사이트 전체 크롤링 | DEFERRED | DEFERRED | 44/44 어댑터가 구조적으로 유효함; 크롤링 미실행 |
| V2 | 성공률 >= 80% | DEFERRED | DEFERRED | 실제 크롤링 실행 필요 |
| V3 | 수집 기사 >= 500건 | DEFERRED | DEFERRED | 실제 크롤링 실행 필요 |
| V4 | 필수 필드 존재율 >= 99% | STRUCTURAL | PASS | 합성 데이터 왕복 검증으로 확인 |
| V5 | 중복 제거율 <= 1% | STRUCTURAL | PARTIAL | DedupEngine 임포트 가능, 3단계 캐스케이드 검증 완료; 런타임 중복 제거 테스트 미실행 |
| V6 | OOM 없이 분석 완료 | STRUCTURAL | PARTIAL | 파이프라인 배선 검증 완료, 메모리 모니터 존재; 런타임 실행 미수행 |
| V7 | 출력에 5개 신호 계층 모두 포함 | STRUCTURAL | PASS | L1-L5 계층이 stage7_signals.py 및 sqlite_builder.py에 정의됨 |
| V8 | FTS5 검색 동작 | STRUCTURAL | PARTIAL | DDL 검증 완료, 단위 테스트에서 FTS5 단독 확인; E2E 검색 테스트 미실행 |
| V9 | sqlite-vec 검색 동작 | DEFERRED | DEFERRED | sqlite-vec DDL에 우아한 성능 저하(graceful degradation) 포함; 설치 여부 불확실 |
| V10 | E2E 소요 시간 <= 3시간 | DEFERRED | DEFERRED | 실제 파이프라인 실행 필요 |
| V11 | 실패 보고서 생성 | STRUCTURAL | PASS | run_e2e_test.py에 보고서 생성 로직 존재 |
| V12 | 3단계 재시도 작동 | DEFERRED | DEFERRED | 재시도 상수 검증 완료 (최대 90회 시도); 런타임 작동 미관측 |

## 상세 검사 결과

| Check ID | 설명 | Status | 소요 시간 | 세부사항 |
|----------|------|--------|----------|---------|
| ENV_001 | Python 버전 >= 3.11 및 핵심 의존성 임포트 가능 | **PASS** | 0.64초 | Python 3.14.0, 7개 핵심 의존성 모두 정상 |
| CFG_001 | 설정 파일(sources.yaml, pipeline.yaml) 존재 및 유효 | **PASS** | 0.04초 | 양쪽 설정 파일 존재 및 파싱 가능, 44개 사이트 설정됨 |
| ADP_001 | 44개 사이트 어댑터 모두 ADAPTER_REGISTRY를 통해 임포트 가능 | **PASS** | 0.02초 | 44개 어댑터 등록: 38north, afmedios, aljazeera, arabnews, bild, bloomberg, bloter, buzzfeed, chosun, cnn, donga, e... |
| ADP_002 | 사이트별 어댑터 인터페이스 검증 (44개 사이트) | **PASS** | 0.00초 | 44개 사이트 중 44 PASS, 0 FAIL |
| STG_001 | 8개 분석 단계 모두 run 함수와 함께 임포트 가능 | **PASS** | 0.03초 | 8개 단계 모두 run 함수와 함께 임포트 가능 |
| PIP_001 | AnalysisPipeline에 _run_stage1부터 _run_stage8까지 존재 | **PASS** | 0.00초 | 8개 단계 실행기 모두 배선 완료 (_run_stage1부터 _run_stage8) |
| STR_001 | 저장 계층: Parquet 스키마(12/21/12 컬럼) + SQLite DDL | **PASS** | 0.00초 | Parquet: ARTICLES(12), ANALYSIS(21), SIGNALS(12); SQLite: 5개 테이블 (articles_fts, article_embeddings, signals_index, top... |
| DDP_001 | DedupEngine 임포트 가능, 3단계 캐스케이드(URL + Title + S) | **PASS** | 0.00초 | DedupEngine 정상: 3단계, SimHash 64비트, threshold=8 |
| RTY_001 | 재시도 시스템: URL당 5 x 2 x 3 x 3 = 최대 90회 시도 | **PASS** | 0.00초 | L1=5 x L2=2 x L3=3 x L4=3 = 90 (NetworkGuard x Strategy x Round x Restart) |
| CLI_001 | main.py --mode crawl --dry-run 오류 없이 실행 | **PASS** | 0.08초 | 드라이 런 정상 완료 (exit code 0) |
| CLI_002 | main.py --mode analyze --all-stages --dry-run 오류 없이 실행 | **PASS** | 0.04초 | 분석 드라이 런 완료 (exit code 0) |
| SYN_001 | 합성 기사: JSONL 기사 10건 생성 및 왕복 검증 | **PASS** | 0.00초 | 합성 기사 10건: JSONL 왕복 정상, 모든 필수 필드(title, url, body, source_id) 존재 |
| TST_001 | 기존 pytest 테스트 스위트 상태 (pass/fail/skip 카운트) | **WARN** | 16.51초 | 1657 통과, 8 실패, 13 건너뜀 (전체 1678, exit code 1) |

## 분석 파이프라인 단계

| 단계 | 이름 | 임포트 가능 | Run 함수 | 의존성 선언 | Status |
|------|------|-----------|---------|-----------|--------|
| 1 | 전처리 | Y | Y | Y | **PASS** |
| 2 | 피처 추출 | Y | Y | Y | **PASS** |
| 3 | 기사 분석 | Y | Y | Y | **PASS** |
| 4 | 집계 | Y | Y | Y | **PASS** |
| 5 | 시계열 | Y | Y | Y | **PASS** |
| 6 | 교차 분석 | Y | Y | Y | **PASS** |
| 7 | 신호 분류 | Y | Y | Y | **PASS** |
| 8 | 데이터 출력 | Y | Y | Y | **PASS** |

## 사이트별 어댑터 검증 (44/44 PASS)

### 성공한 어댑터

| Site ID | Group | 임포트 가능 | 메서드 | 속성 | Status |
|---------|-------|-----------|--------|------|--------|
| 38north | D | Y | Y | Y | **PASS** |
| afmedios | E | Y | Y | Y | **PASS** |
| aljazeera | G | Y | Y | Y | **PASS** |
| arabnews | G | Y | Y | Y | **PASS** |
| bild | G | Y | Y | Y | **PASS** |
| bloomberg | E | Y | Y | Y | **PASS** |
| bloter | D | Y | Y | Y | **PASS** |
| buzzfeed | E | Y | Y | Y | **PASS** |
| chosun | A | Y | Y | Y | **PASS** |
| cnn | E | Y | Y | Y | **PASS** |
| donga | A | Y | Y | Y | **PASS** |
| etnews | D | Y | Y | Y | **PASS** |
| fnnews | B | Y | Y | Y | **PASS** |
| ft | E | Y | Y | Y | **PASS** |
| globaltimes | F | Y | Y | Y | **PASS** |
| hani | A | Y | Y | Y | **PASS** |
| hankyung | B | Y | Y | Y | **PASS** |
| huffpost | E | Y | Y | Y | **PASS** |
| irobotnews | D | Y | Y | Y | **PASS** |
| israelhayom | G | Y | Y | Y | **PASS** |
| joongang | A | Y | Y | Y | **PASS** |
| kmib | C | Y | Y | Y | **PASS** |
| latimes | E | Y | Y | Y | **PASS** |
| lemonde | G | Y | Y | Y | **PASS** |
| marketwatch | E | Y | Y | Y | **PASS** |
| mk | B | Y | Y | Y | **PASS** |
| mt | B | Y | Y | Y | **PASS** |
| nationalpost | E | Y | Y | Y | **PASS** |
| nocutnews | C | Y | Y | Y | **PASS** |
| nytimes | E | Y | Y | Y | **PASS** |
| ohmynews | C | Y | Y | Y | **PASS** |
| people | F | Y | Y | Y | **PASS** |
| sciencetimes | D | Y | Y | Y | **PASS** |
| scmp | F | Y | Y | Y | **PASS** |
| taiwannews | F | Y | Y | Y | **PASS** |
| techneedle | D | Y | Y | Y | **PASS** |
| thehindu | F | Y | Y | Y | **PASS** |
| themoscowtimes | G | Y | Y | Y | **PASS** |
| thesun | G | Y | Y | Y | **PASS** |
| voakorea | E | Y | Y | Y | **PASS** |
| wsj | E | Y | Y | Y | **PASS** |
| yna | A | Y | Y | Y | **PASS** |
| yomiuri | F | Y | Y | Y | **PASS** |
| zdnet_kr | D | Y | Y | Y | **PASS** |

## 기존 테스트 스위트 상태

- **전체 테스트 수**: 1678
- **통과**: 1657
- **실패**: 8
- **건너뜀**: 13
- **Exit code**: 1

참고: 기존에 존재하던 테스트 실패가 관측되었다. 이 실패들은 E2E 검증으로 인한 것이 아니며, 별도로 조사해야 한다.

## 권장 사항

1. **실제 E2E 테스트 실행**: `python3 testing/run_e2e_test.py`를 실행하여 실제 네트워크 크롤링이 필요한 V2, V3, V10 기준을 검증한다.
2. **기존 테스트 실패 해결**: 기존 pytest 테스트 스위트에 8건의 실패 테스트가 있으며, 별도로 조사해야 한다.

---
`testing/validate_e2e.py`에 의해 2026-02-26에 17.4초 소요로 생성됨.
