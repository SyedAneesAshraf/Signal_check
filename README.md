# A Multimodal Fusion Framework for Evidence-Based Cross-Channel Deception Verification

Initial review prototype for evidence-grounded deception verification.

## Phase 1

Phase 1 provides the FastAPI project foundation and a health endpoint. The
retrieval index, claim extraction, and NLI verification are added in later
phases.

## Phase 2

Phase 2 adds a small, multi-domain local evidence corpus in
`data/evidence/documents.json`. Each document includes source provenance,
retrieval date, and trust notes. The corpus loader validates the metadata and
the passage splitter preserves that metadata for every generated passage.

The corpus is intentionally limited to controlled examples for the prototype,
covering public health, consumer fraud, employment scams, cybersecurity,
climate science, public safety, and an insufficient-evidence scope note. It is
not a live web-search index.

## Phase 3

Phase 3 adds semantic retrieval with
`sentence-transformers/all-mpnet-base-v2` and FAISS. Build the persisted index
with:

```bash
python -m scripts.build_index
```

This writes `data/index/evidence.faiss` and `data/index/metadata.json`. The
metadata order matches FAISS vector IDs exactly. Similarity indicates semantic
relevance only; it does not establish that a claim is true.

## Phase 4

Phase 4 adds a transparent, domain-independent rule-based claim extractor in
`app/services/claim_extractor.py`. It splits input into candidate statements,
extracts basic named entities and URLs, and labels statements conservatively.
Extraction only structures the input; it does not verify claims or determine
whether they are true.

## Phase 6

Phase 6 connects extraction, FAISS retrieval, and NLI verification through the
`POST /api/analyze/text` endpoint. Heavy models are loaded lazily on the first
analysis request. The response includes claims, source metadata, similarity,
NLI signals, cautious statuses, and explicit limitations.

## Phase 5

Phase 5 adds NLI-based claim verification with
`facebook/bart-large-mnli`. Evidence is passed as the premise and the
extracted claim as the hypothesis. The model's configured labels are
normalized at runtime, and multiple signals are aggregated conservatively into
`supported`, `refuted`, `conflicting_evidence`, or `insufficient_evidence`.
NLI results are model estimates, not proof of truth.

## Phase 8

The pipeline now uses a pluggable `EvidenceProvider` boundary. The live Google
News provider is the API default; the local provider is available for
reproducible tests. A Tavily live provider is available when `TAVILY_API_KEY`
is configured; it fails explicitly when the key is missing and never silently
substitutes local evidence. No API key is stored in the repository.

To opt into live web retrieval, configure the key in the shell that starts the
API and explicitly select the provider:

```bash
export TAVILY_API_KEY="your-key"
export EVIDENCE_PROVIDER=tavily
uvicorn app.main:app --reload
```

The default API provider is now `EVIDENCE_PROVIDER=live`, which searches current
Google News results without an API key. Use `EVIDENCE_PROVIDER=local` for
reproducible demonstrations and tests. Tavily remains available as an optional
provider when `TAVILY_API_KEY` is configured.

## Phase 9

Evidence results preserve source type, source-quality category, retrieval date,
and canonicalized URLs. Duplicate live results are removed before NLI
verification. Source quality is an evidence attribute, not a truth decision:
official sources are marked `official`, known reference categories can be
`reputable`, and unclassified live results remain `unknown`.

## Phase 10

Verification aggregation now combines NLI confidence, retrieval similarity,
and source-quality weights. A passage must meet both relevance and weighted
confidence thresholds before it can support or refute a claim. This reduces
false verdicts from highly confident NLI predictions on weakly related or
context-only passages.

## Phase 11

The API now exposes component readiness through `GET /health`, validates
runtime configuration, and records model/index loading failures. Limits such
as maximum text length, retrieval `top_k`, and minimum similarity can be
configured with environment variables:

```text
MAX_TEXT_LENGTH
TOP_K
MINIMUM_SIMILARITY
MODEL_LOAD_TIMEOUT_SECONDS
EVIDENCE_PROVIDER=local|live|tavily
```

## Phase 12

The manually reviewed local evaluation set is stored separately from demo
cases in `data/evaluation/text_cases.json`. It records expected statuses,
traceable evidence IDs, and review notes. Run the real-model evaluation with:

```bash
OMP_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false python -m scripts.evaluate_text
```

The printed metrics describe only this small controlled set; they are not
general accuracy claims.

## Text pipeline diagnostics

The backend emits structured stage-count logs at `INFO` level for text
analysis. They include generated search queries, provider status, raw and
deduplicated result counts, relevance and similarity filtering, NLI input
counts, aggregation, and the final status. Start Uvicorn with:

```bash
uvicorn app.main:app --log-level info
```

For life-status claims, the text pipeline searches the original claim plus
small claim-preserving variants such as `"<subject> death"` and
`"<subject> alive"`. Results mentioning a different person or a non-human
object are not accepted as direct evidence for the subject's life status.

The evaluation currently contains three manually reviewed cases and reports
only final-status accuracy and a confusion count. Larger, independently
annotated data is required before making any general performance claim.

## Phase 7

Phase 7 adds labelled demonstrations in `data/demo_cases.json` covering
supported, refuted, and insufficient-evidence outcomes. Run them with the
actual local models using:

```bash
OMP_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false python -m scripts.run_demo
```

The demo compares expected labels from the controlled corpus with the actual
pipeline statuses. These are preliminary demonstrations, not accuracy claims.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e .
```

The editable install makes the `app` package importable in the active virtualenv,
which avoids `ModuleNotFoundError: No module named 'app'` when running the API
or utility scripts from the project root.

## Run the API

```bash
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`.

## Run the interactive frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. The frontend sends claims to the FastAPI
endpoint, displays the verdict, and lets you expand each source to inspect its
evidence and open the original article. It also displays a concise,
evidence-grounded natural-language analysis generated from the verification
model's verdict and the retrieved sources. Set `VITE_API_URL` if the API is
running on a different host or port.

The frontend is built with React, Vite, and Tailwind CSS. Text, URL, and image
workspaces keep their input, loading, error, and result state independent, so
you can test each modality without replacing another modality's result.

The UI has independent tabs for:

- **Text claim**: submit a claim directly.
- **Article URL**: fetch a public HTML page, extract its title/description/body,
  and verify the extracted factual claims.
- **Image / screenshot**: upload a clear printed-text image. A lazy-loaded
  pretrained `microsoft/trocr-base-printed` model extracts the text before it
  is sent through the same claim, retrieval, and verification pipeline.

Image OCR works best with high-contrast screenshots and large, horizontal text.
OCR output is model-generated and should be checked in the extracted claim
shown by the result.

## Health check

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

## Tests

```bash
pytest
```
