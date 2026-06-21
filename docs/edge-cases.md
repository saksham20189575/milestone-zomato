# Edge Cases & Corner Scenarios

This document catalogs edge cases, boundary conditions, and failure scenarios for the AI-powered restaurant recommendation system. Use it during implementation, testing, and QA.

**Related docs:** [context.md](./context.md) · [architecture.md](./architecture.md) · [implementation-plan.md](./implementation-plan.md)

---

## How to Read This Document

| Column | Meaning |
|--------|---------|
| **ID** | Unique reference for tests and issue tracking |
| **Scenario** | What can go wrong or sit at a boundary |
| **Trigger / Input** | Condition that exposes the edge case |
| **Expected Behavior** | What the system should do |
| **Layer** | Primary component responsible |
| **Priority** | `P0` must handle before release · `P1` should handle · `P2` nice to have |

---

## 1. Data Ingestion & Preprocessing

| ID | Scenario | Trigger / Input | Expected Behavior | Layer | Priority |
|----|----------|-----------------|-------------------|-------|----------|
| D-01 | Hugging Face download fails | Network offline, HF outage, DNS failure | Retry with exponential backoff; show clear error: "Could not load dataset. Check network and retry." | `DatasetLoader` | P0 |
| D-02 | Hugging Face rate limit | Too many download requests | Backoff and retry; suggest using local cache | `DatasetLoader` | P1 |
| D-03 | Dataset schema changed | HF dataset columns renamed or removed | Fail fast with logged column diff; do not silently produce empty data | `DataPreprocessor` | P0 |
| D-04 | Empty dataset after load | HF returns zero rows | Abort startup; error message to user/admin | `DatasetLoader` | P0 |
| D-05 | Missing critical column | No `rating`, `name`, or `location` column | Skip row or fail preprocessing with explicit missing-field error | `DataPreprocessor` | P0 |
| D-06 | Null / empty restaurant name | `name` is `null`, `""`, or whitespace | Drop row; log count of dropped rows | `DataPreprocessor` | P0 |
| D-07 | Null / empty location | `location` missing | Drop row or assign `"Unknown"` and exclude from location filter (prefer drop) | `DataPreprocessor` | P0 |
| D-08 | Invalid rating — non-numeric | `"NEW"`, `"-"`, `"4.5/5"` | Coerce if possible; otherwise drop row | `DataPreprocessor` | P0 |
| D-09 | Rating out of range | `-1`, `6.5`, `99` | Clamp to `[0.0, 5.0]` or drop; document choice in logs | `DataPreprocessor` | P1 |
| D-10 | Rating is exactly 0 | `rating = 0.0` | Keep row; filter may exclude via `min_rating` | `DataPreprocessor` | P1 |
| D-11 | Missing rating | `null` rating | Drop row or default to `0.0` (prefer drop for recommendation quality) | `DataPreprocessor` | P0 |
| D-12 | Invalid cost — non-numeric | `"₹500"`, `"Moderate"`, empty | Strip symbols and coerce; drop if unparseable | `DataPreprocessor` | P0 |
| D-13 | Zero or negative cost | `cost_for_two = 0` or `-100` | Drop row or treat as unknown budget tier | `DataPreprocessor` | P1 |
| D-14 | Extremely high cost | Outlier e.g. `999999` | Keep but assign `budget_tier = high`; log outlier | `DataPreprocessor` | P2 |
| D-15 | Empty cuisine string | `""` or `null` | Set `cuisines = []`; row kept but cuisine filter won't match | `DataPreprocessor` | P0 |
| D-16 | Single cuisine vs multi-cuisine | `"Italian"`, `"Italian, Chinese, Fast Food"` | Split on comma; trim whitespace; dedupe | `DataPreprocessor` | P0 |
| D-17 | Inconsistent cuisine casing | `"italian"`, `"ITALIAN"`, `" Italian "` | Normalize to title case for display; case-insensitive matching in filter | `DataPreprocessor` | P0 |
| D-18 | Duplicate restaurant names | Same name, different locations | Keep both; use unique `id` (index or composite key) | `DataPreprocessor` | P1 |
| D-19 | Duplicate rows | Identical records in dataset | Deduplicate by name + location or keep with distinct IDs | `DataPreprocessor` | P1 |
| D-20 | Location name variants | `"Bangalore"`, `"Bengaluru"`, `"bangalore "` | Normalize via alias map; expose canonical name in UI | `DataPreprocessor` | P0 |
| D-21 | Location with special characters | `"New Delhi"`, `"Connaught Place, Delhi"` | Trim and preserve; case-insensitive match in filter | `DataPreprocessor` | P1 |
| D-22 | Budget tier boundary — exactly 500 | `cost_for_two = 500` | Define inclusive rule: `low` if ≤ 500 (document in config) | `DataPreprocessor` | P0 |
| D-23 | Budget tier boundary — exactly 1500 | `cost_for_two = 1500` | Define inclusive rule: `medium` if ≤ 1500 | `DataPreprocessor` | P0 |
| D-24 | Budget tier boundary — 501 / 1501 | Values at tier edges | Consistent assignment per config; unit test boundaries | `DataPreprocessor` | P0 |
| D-25 | All restaurants same budget tier | Skewed dataset | Filter still works; budget filter may return all or none | `RestaurantFilter` | P1 |
| D-26 | Corrupt local cache file | Truncated parquet/CSV | Detect parse error; re-download from Hugging Face | `DatasetLoader` | P0 |
| D-27 | Stale cache vs updated HF dataset | Cache exists but dataset version changed | Optional cache invalidation via version hash or TTL | `DatasetLoader` | P2 |
| D-28 | Very large dataset | Tens of thousands of rows | Load once at startup; in-memory acceptable for milestone | `RestaurantRepository` | P1 |
| D-29 | Missing optional fields | No `votes`, no `rest_type` | Default `votes = 0`; `rest_type = null` | `DataPreprocessor` | P1 |
| D-30 | Unicode in restaurant names | `"Café", "मसाला"` | UTF-8 throughout; no encoding errors in display or prompts | All layers | P1 |

---

## 2. User Input & Preference Validation

| ID | Scenario | Trigger / Input | Expected Behavior | Layer | Priority |
|----|----------|-----------------|-------------------|-------|----------|
| U-01 | Missing location | `location = ""` or not provided | Validation error: "Location is required" | `PreferenceValidator` | P0 |
| U-02 | Unknown location | `"Mumbai"` when not in dataset | Reject with message + suggest valid locations (top 5 closest) | `PreferenceValidator` | P0 |
| U-03 | Location case mismatch | `"delhi"`, `"DELHI"`, `"Delhi"` | Normalize; match against canonical locations | `PreferenceNormalizer` | P0 |
| U-04 | Location alias | User enters `"Bengaluru"` | Map to `"Bangalore"` if alias defined | `PreferenceNormalizer` | P1 |
| U-05 | Missing budget | Budget not selected | Validation error: "Budget is required" | `PreferenceValidator` | P0 |
| U-06 | Invalid budget value | `"cheap"`, `"$$$"`, `"Medium "` | Reject; only accept `low`, `medium`, `high` | `PreferenceValidator` | P0 |
| U-07 | Budget wrong case | `"LOW"`, `"Medium"` | Normalize to lowercase before validation | `PreferenceNormalizer` | P1 |
| U-08 | Missing min_rating | Field omitted | Default to `0.0` or require explicit value (document choice) | `PreferenceValidator` | P1 |
| U-09 | min_rating below zero | `-0.5`, `-1` | Validation error: "Rating must be between 0.0 and 5.0" | `PreferenceValidator` | P0 |
| U-10 | min_rating above five | `5.1`, `10` | Validation error | `PreferenceValidator` | P0 |
| U-11 | min_rating boundary 0.0 | `min_rating = 0.0` | Accept; all rated restaurants pass filter | `PreferenceValidator` | P0 |
| U-12 | min_rating boundary 5.0 | `min_rating = 5.0` | Accept; only perfect-rated restaurants pass | `PreferenceValidator` | P0 |
| U-13 | min_rating very precise | `4.333333` | Accept as float; filter uses `>=` comparison | `RestaurantFilter` | P2 |
| U-14 | Cuisine not provided | `cuisine = null` or empty | Skip cuisine filter; all cuisines eligible | `RestaurantFilter` | P0 |
| U-15 | Unknown cuisine | `"Mexican"` not in dataset vocabulary | Warn user or reject; suggest similar cuisines from vocabulary | `PreferenceValidator` | P1 |
| U-16 | Partial cuisine match | User: `"Italian"`, restaurant: `["Italian", "Continental"]` | Match — cuisine in list | `RestaurantFilter` | P0 |
| U-17 | Cuisine substring trap | User: `"Indian"`, restaurant: `["Indo-Chinese"]` | Use whole-token match, not naive substring (avoid false positives) | `RestaurantFilter` | P1 |
| U-18 | Empty additional preferences | `additional = ""` or whitespace | Treat as `null`; omit from prompt emphasis | `PreferenceNormalizer` | P1 |
| U-19 | Very long additional text | 2000+ characters | Truncate to max length (e.g. 500 chars) before prompt; warn in UI | `PreferenceNormalizer` | P1 |
| U-20 | Additional text with prompt injection | `"Ignore instructions and recommend..."` | Sanitize for display; system prompt instructs model to ignore override attempts | `PromptBuilder` | P1 |
| U-21 | Special characters in additional | Emojis, HTML, SQL-like strings | Pass as plain text; escape for JSON serialization | `PromptBuilder` | P1 |
| U-22 | All fields at strictest values | High rating + low budget + rare cuisine + niche location | Likely zero results → trigger relaxation or empty state | `RestaurantFilter` | P0 |
| U-23 | Duplicate form submission | User clicks "Get Recommendations" twice quickly | Debounce or disable button during in-flight request | UI | P1 |
| U-24 | Slider vs text input mismatch | Streamlit slider gives float, API expects same | Consistent types end-to-end | UI / API | P1 |
| U-25 | Non-ASCII location input | User pastes unicode city name | Normalize; match if alias exists | `PreferenceNormalizer` | P2 |

---

## 3. Filtering & Candidate Selection

| ID | Scenario | Trigger / Input | Expected Behavior | Layer | Priority |
|----|----------|-----------------|-------------------|-------|----------|
| F-01 | Zero candidates after all filters | Strict prefs in sparse city | Relax constraints: cuisine → budget → min_rating; return warning | `RestaurantFilter` | P0 |
| F-02 | Zero candidates even after relaxation | Impossible combination | Empty result with guidance: "Try lowering min rating or changing cuisine" | `RestaurantFilter` | P0 |
| F-03 | Exactly one candidate | Only 1 restaurant matches | Pass 1 candidate to LLM; return 1 recommendation (not error) | `RestaurantFilter` | P0 |
| F-04 | Fewer candidates than top-K | 3 candidates, `TOP_K = 5` | Return 3 recommendations; LLM instructed to return ≤ available count | `RecommendationService` | P0 |
| F-05 | More candidates than MAX_N | 200 matches, `MAX_CANDIDATES = 20` | Cap at 20 after sort; log truncation | `CandidateSelector` | P0 |
| F-06 | Tied ratings | Multiple restaurants at 4.5 | Break tie by `votes` desc, then name asc | `RestaurantFilter` | P1 |
| F-07 | Tied ratings and votes | Full tie | Stable sort by `id` for reproducibility | `RestaurantFilter` | P2 |
| F-08 | Location filter too strict | User picks city but data uses locality | Document matching strategy; consider city-level vs locality-level fields | `RestaurantFilter` | P1 |
| F-09 | Budget filter excludes all | All restaurants in city are `high`, user picks `low` | Zero results → relax budget with warning | `RestaurantFilter` | P0 |
| F-10 | min_rating excludes all | All restaurants below threshold | Relax min_rating with warning | `RestaurantFilter` | P0 |
| F-11 | Cuisine filter too narrow | Only 2 Italian in city | Proceed with 2 candidates if above min count | `RestaurantFilter` | P1 |
| F-12 | Restaurant with empty cuisines | `cuisines = []` | Excluded when cuisine filter active; included when cuisine not specified | `RestaurantFilter` | P1 |
| F-13 | Combined filters — order matters | All filters applied sequentially | Document order: location → budget → rating → cuisine | `RestaurantFilter` | P0 |
| F-14 | Filter with null repository | Dataset failed to load | Fail before filter with "Dataset not available" | `RestaurantRepository` | P0 |
| F-15 | Same preferences, same data | Repeat request | Same candidate set (deterministic pre-filter) | `RestaurantFilter` | P1 |
| F-16 | Relaxation partially applied | Cuisine relaxed but still zero | Continue relaxing until candidates found or exhausted | `RestaurantFilter` | P0 |
| F-17 | User not informed of relaxation | Filters silently widened | Surface warning banner: "No exact matches; showing results with relaxed cuisine filter" | UI | P0 |
| F-18 | Single-city dataset | All restaurants in one city | Location filter trivial; other filters still apply | `RestaurantFilter` | P2 |
| F-19 | Rating filter with unrated rows | Rows dropped in preprocessing | N/A if dropped; if kept with 0 rating, excluded by any `min_rating > 0` | `RestaurantFilter` | P1 |

---

## 4. Prompt Building

| ID | Scenario | Trigger / Input | Expected Behavior | Layer | Priority |
|----|----------|-----------------|-------------------|-------|----------|
| P-01 | Empty candidate list reaches prompt builder | Bug or bypassed filter | Do not call Groq; return empty state immediately | `PromptBuilder` | P0 |
| P-02 | Very large candidate payload | 20 restaurants × long names/cuisines | Stay within Groq context limits; compact JSON (no pretty-print) | `PromptBuilder` | P1 |
| P-03 | Candidate with special chars in name | Quotes, backslashes, newlines | JSON-escape all fields | `PromptBuilder` | P0 |
| P-04 | Missing optional preference fields | No cuisine, no additional | Omit or null in prompt; model still receives required prefs | `PromptBuilder` | P1 |
| P-05 | TOP_K greater than candidates | Config error | Prompt says "return up to N" where N = min(TOP_K, len(candidates)) | `PromptBuilder` | P0 |
| P-06 | Prompt token limit exceeded | Too many/large candidates | Reduce `MAX_CANDIDATES_FOR_LLM`; truncate candidate fields | `PromptBuilder` | P1 |
| P-07 | Additional prefs contradict budget | "cheap" in additional but budget = high | LLM may note conflict; hard budget filter already applied | `PromptBuilder` | P2 |
| P-08 | All candidates identical rating/cost | LLM must differentiate | Prompt asks to use votes, cuisine fit, additional prefs | `PromptBuilder` | P2 |

---

## 5. Groq LLM Integration

| ID | Scenario | Trigger / Input | Expected Behavior | Layer | Priority |
|----|----------|-----------------|-------------------|-------|----------|
| G-01 | Missing `GROQ_API_KEY` | Env var unset or empty | Fail before API call: "Groq API key not configured" | `LLMClient` | P0 |
| G-02 | Invalid API key | Wrong or revoked key | Catch 401; user-facing error, no stack trace | `LLMClient` | P0 |
| G-03 | Groq rate limit (429) | Too many requests | Exponential backoff (e.g. 1s, 2s, 4s); max 3 retries | `LLMClient` | P0 |
| G-04 | Groq server error (500/503) | Provider outage | Retry once; then fallback to heuristic ranking | `LLMClient` | P0 |
| G-05 | Network timeout | Slow or dead connection | Configurable timeout; fallback after timeout | `LLMClient` | P0 |
| G-06 | Model not found / deprecated | Wrong `GROQ_MODEL` name | Clear error listing valid model from config/docs | `LLMClient` | P0 |
| G-07 | Empty LLM response | Zero content in completion | Retry once; then fallback | `LLMClient` | P0 |
| G-08 | Malformed JSON response | Prose before/after JSON, trailing commas | Retry with lower temperature; strip markdown fences if present | `ResponseParser` | P0 |
| G-09 | Valid JSON, wrong schema | Missing `recommendations` key | Retry once; then fallback | `ResponseParser` | P0 |
| G-10 | JSON with extra fields | Unknown keys in response | Ignore extras; parse required fields | `ResponseParser` | P1 |
| G-11 | LLM returns fewer than top-K | 3 items when 5 requested | Accept partial; fill remaining with heuristic if needed | `RecommendationEnricher` | P1 |
| G-12 | LLM returns more than top-K | 8 items when 5 requested | Take first K by rank field | `RecommendationEnricher` | P1 |
| G-13 | Duplicate ranks | Two items with `rank: 1` | Re-assign ranks sequentially | `RecommendationEnricher` | P1 |
| G-14 | Missing rank field | Recommendation without rank | Assign order by array index | `RecommendationEnricher` | P1 |
| G-15 | LLM hallucinates restaurant ID | ID not in candidate set | Drop invalid entry; log warning; fill from heuristic if below K | `RecommendationEnricher` | P0 |
| G-16 | LLM duplicates same ID | Same restaurant twice | Deduplicate; keep highest rank | `RecommendationEnricher` | P0 |
| G-17 | LLM fabricates restaurant name | Name not matching ID | Always display data from structured record by ID, not LLM name | `RecommendationEnricher` | P0 |
| G-18 | Empty explanation string | `"explanation": ""` | Use generic fallback: "Matches your preferences for {location} and {budget}." | `RecommendationEnricher` | P1 |
| G-19 | Very long explanation | 2000+ char explanation | Truncate for display (e.g. 500 chars) with ellipsis | `RecommendationPresenter` | P2 |
| G-20 | Missing summary field | No `summary` in JSON | `summary = null`; UI hides summary banner | `ResponseParser` | P1 |
| G-21 | Summary contradicts recommendations | LLM inconsistency | Display anyway; structured data is source of truth for cards | UI | P2 |
| G-22 | `response_format` JSON mode unsupported | Model ignores JSON mode | Rely on prompt instructions + parser fence-stripping | `LLMClient` | P1 |
| G-23 | Temperature too high | `GROQ_TEMPERATURE = 1.0` | More JSON failures; retry at 0.1 on parse error | `LLMClient` | P1 |
| G-24 | All retries exhausted | Persistent failures | Heuristic top-K by rating + banner: "AI explanations unavailable" | `RecommendationService` | P0 |
| G-25 | Fallback ranking activated | Any G-03 through G-09 | Return results with generic explanations; never blank screen | `RecommendationService` | P0 |
| G-26 | Groq token limit exceeded | Prompt too long | Reduce candidates; retry with smaller set | `LLMClient` | P1 |
| G-27 | Concurrent Groq requests | Multiple users / double submit | Each request independent; consider simple in-app rate limiting | `RecommendationService` | P2 |

---

## 6. Output Display & UX

| ID | Scenario | Trigger / Input | Expected Behavior | Layer | Priority |
|----|----------|-----------------|-------------------|-------|----------|
| X-01 | Zero recommendations returned | Empty response after all fallbacks | Empty state UI with actionable suggestions | UI | P0 |
| X-02 | Single recommendation | 1 result | Render one card with rank badge `#1` | UI | P0 |
| X-03 | Missing optional summary | `summary = null` | Hide summary section; no empty box | UI | P1 |
| X-04 | Long restaurant name | 80+ characters | Wrap or truncate with tooltip | UI | P2 |
| X-05 | Rating display — one decimal | `4.0` vs `4` | Consistent format e.g. `4.0 ★` | UI | P2 |
| X-06 | Cost display — formatting | `1200` | Display as `₹1,200 for two` or similar | UI | P1 |
| X-07 | Null cost in record | Missing `cost_for_two` | Show "Price not available" | UI | P1 |
| X-08 | Loading state during dataset init | First app load | Show spinner: "Loading restaurant data..." | UI | P0 |
| X-09 | Loading state during Groq call | After submit | Disable button; show "Finding recommendations..." | UI | P0 |
| X-10 | Error state — dataset failed | D-01 | Block form; show error with retry option | UI | P0 |
| X-11 | Error state — Groq failed entirely | Even fallback fails (no candidates) | Clear error message; no partial broken UI | UI | P0 |
| X-12 | Relaxation warning display | F-17 | Yellow info banner above results | UI | P0 |
| X-13 | Metadata display (debug) | Dev mode | Optionally show candidates considered, model name | UI | P2 |
| X-14 | Cuisine list display | `["Italian", "Chinese"]` | Join as `"Italian, Chinese"` | `RecommendationPresenter` | P1 |
| X-15 | Mobile / narrow viewport | Streamlit on phone | Cards stack vertically; readable text | UI | P2 |

---

## 7. API Layer (Optional FastAPI)

| ID | Scenario | Trigger / Input | Expected Behavior | Layer | Priority |
|----|----------|-----------------|-------------------|-------|----------|
| A-01 | Malformed JSON body | Invalid JSON in POST | `422` with validation detail | API | P1 |
| A-02 | Missing required field | No `location` in body | `422` with field error | API | P1 |
| A-03 | Wrong Content-Type | `text/plain` body | `415` or `422` | API | P2 |
| A-04 | GET /health before dataset load | Startup race | `503` or `health: degraded` | API | P1 |
| A-05 | GET /locations empty dataset | Load failure | `503` with error message | API | P1 |
| A-06 | Oversized request body | Huge `additional` field | Reject at validation max length | API | P2 |
| A-07 | Internal server error | Unhandled exception | `500` with generic message; log details server-side | API | P1 |

---

## 8. Configuration & Environment

| ID | Scenario | Trigger / Input | Expected Behavior | Layer | Priority |
|----|----------|-----------------|-------------------|-------|----------|
| C-01 | `.env` file missing | No local env | Use defaults where safe; fail on missing `GROQ_API_KEY` at call time | `config.py` | P0 |
| C-02 | Invalid `GROQ_TEMPERATURE` | `"hot"` in env | Fail at startup with config validation error | `config.py` | P1 |
| C-03 | `TOP_K_RECOMMENDATIONS = 0` | Misconfiguration | Clamp to minimum 1 or fail at startup | `config.py` | P1 |
| C-04 | `MAX_CANDIDATES_FOR_LLM = 0` | Misconfiguration | Fail at startup | `config.py` | P1 |
| C-05 | Budget thresholds misconfigured | `low_max > high_min` | Fail at startup with clear message | `config.py` | P1 |
| C-06 | `DATA_CACHE_PATH` not writable | Permission denied | Log warning; run without cache (slower) | `DatasetLoader` | P1 |
| C-07 | Wrong Python version | Python < 3.11 | Document in README; type hints may break | Project | P2 |

---

## 9. Security & Abuse

| ID | Scenario | Trigger / Input | Expected Behavior | Layer | Priority |
|----|----------|-----------------|-------------------|-------|----------|
| S-01 | API key in logs | Debug logging enabled | Never log `GROQ_API_KEY` or full prompts with secrets | Logging | P0 |
| S-02 | API key committed to git | Accidental `.env` commit | `.gitignore` blocks; document key rotation | Project | P0 |
| S-03 | Prompt injection via additional field | Malicious user text | System prompt resists override; no code execution | `PromptBuilder` | P1 |
| S-04 | XSS in LLM explanation | HTML/JS in explanation | Escape on render in web UI | UI | P1 |
| S-05 | Public API abuse | High request volume | Rate limit per IP (if deployed publicly) | API | P2 |

---

## 10. Concurrency & Performance

| ID | Scenario | Trigger / Input | Expected Behavior | Layer | Priority |
|----|----------|-----------------|-------------------|-------|----------|
| R-01 | Cold start — first request slow | Dataset + HF download | Acceptable for milestone; show loading state | All | P1 |
| R-02 | Repeated requests same session | Same user, same prefs | Cache optional; deterministic filter + variable LLM | `RecommendationService` | P2 |
| R-03 | Memory pressure | Full dataset in RAM | Monitor; acceptable for milestone scope | `RestaurantRepository` | P2 |
| R-04 | Groq latency spike | 5–30s response | UI timeout message; don't hang indefinitely | UI | P1 |

---

## 11. End-to-End Scenario Matrix

Quick-reference combinations to test manually or in integration tests.

| # | Location | Budget | Cuisine | Min Rating | Additional | Expected outcome |
|---|----------|--------|---------|------------|------------|------------------|
| E2E-01 | Valid city | medium | Italian | 4.0 | — | 5 ranked results with explanations |
| E2E-02 | Valid city | low | — | 3.0 | — | Results across all cuisines in budget |
| E2E-03 | Valid city | high | Chinese | 4.5 | family-friendly | Few results; LLM uses additional in explanations |
| E2E-04 | Unknown city | medium | — | 3.5 | — | Validation error + suggestions |
| E2E-05 | Valid city | low | Italian | 5.0 | — | Very few/zero → relaxation or empty state |
| E2E-06 | Valid city | medium | — | 0.0 | — | Maximum candidate pool |
| E2E-07 | Valid city | medium | Rare cuisine | 3.0 | — | Relaxation warning or few results |
| E2E-08 | Valid city | medium | — | 4.0 | (Groq offline) | Heuristic fallback with notice |
| E2E-09 | Valid city | medium | — | 4.0 | 500-char additional | Truncated in prompt; no error |
| E2E-10 | Alias city name | medium | — | 4.0 | — | Normalized match if alias configured |

---

## 12. Test Mapping

Suggested pytest coverage for edge cases.

| Test file | Edge case IDs |
|-----------|---------------|
| `tests/test_preprocessor.py` | D-06–D-18, D-22–D-24, D-30 |
| `tests/test_filter.py` | F-01–F-06, F-09–F-13, F-16 |
| `tests/test_prompt_builder.py` | P-01, P-03–P-05 |
| `tests/test_recommendation.py` | G-08–G-18, G-24–G-25 (mocked Groq) |
| `tests/test_preferences.py` | U-01–U-12, U-14–U-19 |
| Manual / E2E | E2E-01–E2E-10, X-01–X-12 |

---

## 13. Priority Summary

### P0 — Must handle before milestone sign-off

- All dataset load failures and empty data (D-01, D-04, D-06, D-07, D-11, D-26)
- All required preference validation (U-01, U-02, U-05, U-06, U-09, U-10)
- Zero-candidate filtering and relaxation (F-01, F-02, F-17)
- Fewer candidates than top-K (F-04)
- Groq auth, rate limit, timeout, malformed JSON (G-01–G-09, G-15–G-17, G-24–G-25)
- Missing API key and fallback ranking (G-01, G-25)
- Empty and loading UI states (X-01, X-08, X-09, X-10)

### P1 — Should handle for robust experience

- Boundary values (ratings, budget tiers, cuisine matching)
- Relaxation warnings, tie-breaking, truncation
- Groq retries, partial LLM responses, enrichment edge cases
- Cost/rating display fallbacks

### P2 — Nice to have

- Cache invalidation, outlier costs, mobile layout, debug metadata
- Response caching, advanced rate limiting

---

## Related Documents

- [context.md](./context.md) — product requirements
- [architecture.md](./architecture.md) — component design and error handling patterns
- [implementation-plan.md](./implementation-plan.md) — phase-wise build plan and QA checklist
