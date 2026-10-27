# SignalCheck

SignalCheck is a research prototype for **multimodal content-risk and
evidence verification**. It accepts manually supplied text, public URLs, and
images/screenshots, retrieves relevant evidence, checks factual claims, looks
for phishing indicators, compares related inputs, and reports when the
evidence is insufficient.

It does **not** prove that a person intentionally lied. The system evaluates
the content and the risk of trusting it; sender intent is explicitly reported
as not determinable from content alone.

## What it can do

- Extract factual claims from text, webpages, and OCR output.
- Search live Wikipedia and Google News evidence by default.
- Use optional Tavily web search when configured.
- Compare claims with retrieved passages using semantic relevance and BART NLI.
- Preserve source provenance, quality, provider, domain, and retrieval dates.
- Detect baseline phishing indicators in URLs and related messages.
- Correlate related inputs through shared URLs, entities, and similar wording.
- OCR uploaded screenshots with `microsoft/trocr-base-printed`.
- Analyze combined text, URL, and image cases.
- Return `deceptive`, `genuine`, or `needs_review` as a content-risk decision.
- Separate:
  - `content_assessment`: `supported`, `refuted`, or `insufficient_evidence`
  - `deception_risk`: `low`, `high`, or `unknown`
  - `intent_assessment`: currently `not_determinable_from_content`

## What it cannot do yet

- Prove sender intent or maliciousness.
- Determine whether arbitrary image pixels are authentic.
- Detect deepfakes or reliably judge unusual scenes such as a flying car.
- Provide calibrated probabilities from the prototype risk score.
- Guarantee that live search results are complete or correct.
- Persist cases after the backend process stops.
- Transcribe audio automatically; audio currently needs a supplied transcript.

An image without readable text is deliberately classified as `needs_review`
unless other evidence establishes a high-risk content decision. This is safer
than treating a valid image file as proof of authenticity.

## Architecture

```text
Manual inputs
    |
    +-- text --------------------+
    +-- public URL --------------+--> claim extraction
    +-- screenshot --> OCR ------+    evidence retrieval
                                      NLI verification
                                      phishing signals
                                      cross-input correlation
                                      prototype decision fusion
                                      optional Groq investigation
                                              |
                                              v
                       content status + deception risk + limitations
```

Important backend locations:

- [app/services/pipeline.py](app/services/pipeline.py): claim extraction,
  retrieval, relevance filtering, NLI, and evidence aggregation.
- [app/services/evidence_provider.py](app/services/evidence_provider.py):
  local, Wikipedia, Google News, hybrid, and optional Tavily providers.
- [app/services/phishing.py](app/services/phishing.py): URL and message risk
  signals.
- [app/services/case_analysis.py](app/services/case_analysis.py): combined
  case orchestration and decision output.
- [app/services/verifier.py](app/services/verifier.py): cautious evidence
  aggregation and contradiction filtering.
- [app/services/image_analysis.py](app/services/image_analysis.py): image
  metadata and perceptual-hash inspection.
- [app/services/multimodal.py](app/services/multimodal.py): OCR and public
  webpage extraction.

## Requirements

- Python 3.11 or newer
- Node.js and npm
- Internet access for the live evidence provider and optional Groq investigator
- A Groq API key only if AI investigation is desired

The local FAISS index and model files are generated or downloaded locally.
They are not required when using the default live provider, although the
retrieval and NLI models may still be downloaded on first use.

## Windows setup

From the project root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

Install frontend dependencies:

```powershell
Set-Location frontend
npm install
Set-Location ..
```

## Environment configuration

Create a local `.env` file. Never commit it or paste its values into an issue
or chat:

```text
EVIDENCE_PROVIDER=live
GROQ_API_KEY=your-key
GROQ_MODEL=openai/gpt-oss-20b
ANALYSIS_TRACE=false
```

Optional:

```text
TAVILY_API_KEY=your-key
EVIDENCE_PROVIDER=tavily
TOP_K=3
MINIMUM_SIMILARITY=0.3
MAX_TEXT_LENGTH=10000
```

`.env` is ignored by Git. API keys are not required for the deterministic
text, URL, OCR, and evidence pipeline when Groq is disabled.

## Run the project

Start the backend in one PowerShell terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Start the frontend in another:

```powershell
Set-Location frontend
npm run dev
```

Open:

- Frontend: [http://localhost:5173](http://localhost:5173)
- API: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

The backend API can also be started without reload for a stable manual test:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Main API routes

### Single-input analysis

- `POST /api/analyze/text`
- `POST /api/analyze/url`
- `POST /api/analyze/image`

### Manual combined cases

- `POST /api/cases`
- `POST /api/cases/{case_id}/inputs/text`
- `POST /api/cases/{case_id}/inputs/url`
- `POST /api/cases/{case_id}/inputs/image`
- `POST /api/cases/{case_id}/inputs/audio`
- `POST /api/cases/{case_id}/analyze`
- `GET /api/cases/{case_id}`
- `DELETE /api/cases/{case_id}`

Uploaded bytes are held in process memory for the prototype and are excluded
from API responses. They are lost when the backend process stops.

## Interpreting results

`deceptive` means that the content crossed the configured content-risk
threshold, commonly because of strong phishing or contradiction signals. It
does not prove intentional deception.

`genuine` means the available evidence did not indicate deception and relevant
evidence was available. It does not prove that the content is authentic.

`needs_review` means the evidence is missing, weak, conflicting, or the input
requires visual inspection that the current models cannot perform.

Always inspect the linked evidence and the `limitations` field before taking
action.

## Development and validation

Run the backend tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Build the frontend:

```powershell
Set-Location frontend
npm run build
```

The current verified baseline is **78 backend tests passing** and a successful
frontend production build.

For detailed progress and known limitations, see
[docs/PROGRESS.md](docs/PROGRESS.md). The implementation roadmap is in
[docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).
