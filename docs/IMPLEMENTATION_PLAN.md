# Multimodal Deception Verification Prototype

## Project direction

This project is a research prototype for manually submitted multimodal cases. The near-term objective is to detect phishing and coordinated deception using claim verification, rather than to build a production monitoring platform.

The first demonstration will accept related text, image, and URL inputs and return a genuine/deceptive result. Audio will be added by Phase 9. Video and continuous source monitoring remain future work.

## Decisions

- **Project type:** Research prototype
- **Initial workflow:** Manual case submission
- **Initial modalities:** Text, image, URL
- **Later modality:** Asynchronous audio by Phase 9
- **Processing:** Hosted/free APIs may be used behind replaceable provider interfaces; the prototype must retain a controlled offline path where practical
- **Storage:** Raw uploads are temporary; derived case results may be retained for evaluation
- **Primary goal:** Coordinated deception detection and phishing detection supported by claim verification
- **Primary output:** `genuine` or `deceptive`
- **Evaluation data:** Controlled prototype cases initially
- **Explainability:** Not a primary research requirement for the first implementation
- **Deployment direction:** Manual inputs now; continuous multi-source monitoring is future work

## Phase gates

Every phase must pass its implementation checks before the next phase begins:

1. Implement only the phase scope.
2. Add or update focused tests.
3. Run the relevant backend and frontend checks.
4. Manually inspect the resulting behavior where applicable.
5. Record what was verified and any remaining limitations in `docs/PROGRESS.md`.

## Phases

### Phase 1 — Manual case workflow

Create a case-oriented workflow that accepts multiple related manual inputs. Support case creation, text/URL/image input ingestion, input metadata, temporary raw content handling, case retrieval, and deletion. Do not claim to produce a fused verdict yet.

**Exit criteria**

- A case can be created.
- Text, URL, and image inputs can be added to the same case.
- Inputs have stable IDs and metadata.
- Raw image bytes are held temporarily and are not returned by the API.
- Missing cases and invalid input types fail explicitly.
- Focused API tests pass.

### Phase 2 — Stabilize the existing prototype

Make current text, URL, OCR, index, model, and frontend behavior reproducibly runnable. Separate provider dependencies, fix readiness reporting, add startup/smoke checks, and render all extracted claims.

### Phase 3 — Common modality schema

Define modality-neutral case, input, claim, signal, evidence, and result contracts that can represent text, image, URL, audio, and video.

### Phase 4 — Reusable claim-verification service

Separate input ingestion from claim extraction, retrieval, NLI verification, and claim-level results. Make the service reusable for OCR and later transcripts.

### Phase 5 — Phishing detection

Implement a provider-independent URL risk detector using controlled lexical, domain, redirect, credential, payment, and urgency signals. Add optional hosted reputation providers without making them mandatory.

### Phase 6 — Real image analysis

Extend OCR with temporary image handling, hashes, metadata, screenshot indicators, and text-image processing.

### Phase 7 — Cross-input correlation

Detect shared claims, entities, URLs, domains, hashes, and similar content across inputs in one case.

### Phase 8 — Decision fusion

Combine claim verification, phishing, image, and correlation signals into a documented genuine/deceptive decision with uncertainty handled internally.

### Phase 9 — Asynchronous audio support

Add temporary audio uploads, background processing, transcription through a replaceable provider, claim verification, and correlation with existing case inputs.

### Integration milestone — End-to-end manual case

After Phase 9, connect the implemented services through one manual case-analysis endpoint and frontend action. The case must collect text, URL, image, and transcript-backed audio inputs; produce claim, phishing, image, and correlation signals; and return one fused genuine/deceptive result. This milestone is required before adding more advanced models or continuous monitoring.

## Deferred work

- Video processing and video forensics
- Continuous listening or source monitoring
- Production authentication and multi-user operation
- Large public dataset integration
- Advanced explainability research
- Full deepfake detection across all modalities
