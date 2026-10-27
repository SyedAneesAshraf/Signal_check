# Implementation progress

## Status

Current phase: **Core manual verification milestone complete; Phase A — reliable claim verification next**

Started: 2026-10-27

## Phase 1

### Scope

Create a temporary, manual case container that can hold related text, URL, and image inputs. This phase establishes ingestion and lifecycle behavior only; it does not produce a fused verdict.

### Completed

- Phase scope and exit criteria documented.
- Implementation task dependencies recorded.
- Added `POST /api/cases` for creating a temporary manual case.
- Added text, URL, and image input routes under `/api/cases/{case_id}/inputs`.
- Added stable input IDs, SHA-256 content hashes, timestamps, and input metadata.
- Kept uploaded image bytes in process memory only and excluded them from responses.
- Added case retrieval and deletion routes.
- Added focused case API tests.
- Provider initialization now loads the local embedding model and FAISS index only for `EVIDENCE_PROVIDER=local`.
- The default live provider now combines Wikipedia reference search with Google News.
- Wikipedia and encyclopedia evidence receive reputable-source weighting. Tavily remains optional and is included automatically when `TAVILY_API_KEY` is configured.
- Added an optional Groq AI investigator for combined cases. When `GROQ_API_KEY` is configured, it inspects supplied message text, safely fetched public-page text, retrieved claims, and evidence to produce a contextual verdict, risk score, confidence, summary, and reasons. The deterministic fusion result remains the fallback when the key is absent.
- Groq model selection uses `GROQ_MODEL`; the default is `openai/gpt-oss-20b`, selected from the models available to the configured account during local verification.
- Live provider startup no longer requires local index artifacts.
- Health readiness now reports `analysis_ready` separately from optional local retrieval components.
- Restored frontend dependencies and verified the Vite production build.
- Generated the local FAISS index from the controlled corpus: 8 passages indexed.
- Validated the real Sentence Transformer retrieval model and BART NLI model.
- Added modality-neutral contracts for text, image, URL, audio, and video.
- Added a reusable factual-claim service and wired the main text pipeline to use it.
- Added deterministic URL phishing-risk signals that do not require external APIs.
- Added lightweight image dimensions, format, metadata, and perceptual-hash assessment.
- Combined case analysis now runs OCR on uploaded images, verifies OCR-derived claims through the normal evidence pipeline, and exposes the extracted text in image signals.
- Image-only inputs without readable text now return `needs_review` instead of being silently classified as genuine. This is intentionally conservative because no pixel-level vision/manipulation detector is configured yet.
- Combined decisions now abstain as `needs_review` when no relevant source-linked evidence is available. The response includes a decision basis, recommended action, limitations, and evidence provenance fields.
- The UI labels the risk value as a prototype score and displays source quality/provider information to avoid presenting heuristic scores as calibrated probabilities.
- Combined results now separate content status (`supported`, `refuted`, or `insufficient_evidence`) from deception risk and explicitly report that sender intent is not determinable from content alone.
- Added cross-input shared URL/entity/similarity correlation.
- Added documented weighted decision fusion for the first genuine/deceptive demonstration.
- Added asynchronous audio case ingestion with temporary raw bytes and transcript adapter support.
- Added `POST /api/cases/{case_id}/analyze` to combine available case signals into one typed result.
- Added backend integration coverage for claim contradiction, phishing risk, and cross-input correlation.
- Added a frontend “Analyze combined case” action using the collected text, URL, and image inputs.

### Verification

- Focused Phase 1 and health tests: **4 passed**.
- Full backend regression suite: **49 passed**.
- Registered routes inspected for case creation, retrieval, deletion, and all three input types.
- Full backend regression suite after stabilization changes: **52 passed**.
- Python syntax compilation: **passed**.
- Frontend `npm run build`: **passed**.
- Live-provider startup isolation test: **passed** without a local index.
- Local index generation: **passed**; `data/index/evidence.faiss` and `data/index/metadata.json` were created.
- Local provider preflight after index generation: **passed**.
- Real model-loading preflight for retrieval and NLI: **passed**.
- Full backend regression suite after index generation: **54 passed**.
- Full backend regression suite after Phases 3–9 implementation: **64 passed**.
- Audio case API test: **passed** with asynchronous `202` response and temporary input metadata.
- End-to-end case integration test: **passed** with a deceptive fused result.
- Full backend suite after case integration: **65 passed**.
- Frontend production build after case integration: **passed**.
- Full backend regression suite after abstention, provenance, intent-separation, and contradiction-guard changes: **78 passed**.
- Frontend production build after result-model and UI changes: **passed**.
- Live backend health check after restart: **ready**.
- Live text smoke test completed successfully; an ambiguous Earth-shape headline no longer creates a direct refutation.
- Live combined phishing smoke test completed successfully with `deceptive`, high deception risk, and `not_determinable_from_content` intent.

### Remaining limitations

- Case storage is expected to be process-local during the research prototype.
- Advanced hosted transcription is still deferred; audio cases currently require a transcript for completed processing.
- Raw uploads must remain temporary and must not be exposed in API responses.
- The generated index is ignored by Git and must be rebuilt by each environment that uses local retrieval.
- The current audio implementation accepts a supplied transcript through a replaceable adapter; a real hosted speech-to-text provider still needs configuration.
- The current case endpoint includes image metadata and OCR signals, but it does not yet infer image manipulation risk from pixels.
- URL analysis uses deterministic local signals; external reputation providers are not required yet.
- Sender intent is not inferable from content alone; `deceptive` means high content-risk, not proven malicious intent.
- The prototype risk score is not a calibrated probability.

## Phase history

| Phase | Status | Notes |
|---|---|---|
| 1. Manual case workflow | Complete | Case creation, related input ingestion, metadata, temporary raw content, retrieval, deletion, and tests are in place |
| 2. Prototype stabilization | Complete | Provider separation, preflight, index generation, real model loading, frontend build, and regression tests passed |
| 3. Common modality schema | Complete | Contracts cover planned modalities and validate scores/statuses |
| 4. Claim-verification service | Complete | Reusable factual-claim extraction boundary is wired into the text pipeline |
| 5. Phishing detection | Complete | Deterministic URL/page risk assessment implemented and tested |
| 6. Image analysis | In progress | Metadata, OCR, OCR claim verification, and conservative `needs_review` behavior implemented; pixel-level vision analysis remains |
| 7. Cross-input correlation | Complete | Shared URL/entity/similarity signals implemented and tested |
| 8. Decision fusion | Complete | Weighted risk fusion with abstention, decision basis, recommendation, and intent separation implemented and tested |
| 9. Audio support | Complete with limitation | Async audio case ingestion and transcript adapter implemented; hosted STT remains |
| Integration milestone | Complete with limitation | Backend and frontend run combined manual cases; advanced image/audio models, calibrated evaluation, and deeper phishing inspection remain future work |
