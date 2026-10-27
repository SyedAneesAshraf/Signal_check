import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowUpRight,
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  FileImage,
  FileText,
  Link2,
  LoaderCircle,
  Search,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import "./styles.css";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const examples = ["Trump is dead", "The Earth is flat", "NASA landed astronauts on the Moon"];

function App() {
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [image, setImage] = useState(null);
  const [textState, setTextState] = useState({ loading: false, error: "", result: null });
  const [urlState, setUrlState] = useState({ loading: false, error: "", result: null });
  const [imageState, setImageState] = useState({ loading: false, error: "", result: null });

  async function submit(kind, endpoint, options) {
    const setters = { text: setTextState, url: setUrlState, image: setImageState };
    const setState = setters[kind];
    setState({ loading: true, error: "", result: null });
    try {
      const response = await fetch(`${API_URL}${endpoint}`, options);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Analysis failed.");
      setState({ loading: false, error: "", result: payload });
    } catch (requestError) {
      setState({
        loading: false,
        result: null,
        error: `${requestError.message} Check that the API is running on ${API_URL}.`,
      });
    }
  }

  function analyzeText(event) {
    event.preventDefault();
    if (!text.trim() || textState.loading) return;
    return submit("text", "/api/analyze/text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text.trim() }),
    });
  }

  function analyzeUrl(event) {
    event.preventDefault();
    if (!url.trim() || urlState.loading) return;
    return submit("url", "/api/analyze/url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: url.trim() }),
    });
  }

  function analyzeImage(event) {
    event.preventDefault();
    if (!image || imageState.loading) return;
    const formData = new FormData();
    formData.append("file", image);
    return submit("image", "/api/analyze/image", { method: "POST", body: formData });
  }

  return (
    <div className="min-h-screen bg-mist text-ink">
      <header className="border-b border-slate-200/80 bg-white/80">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 lg:px-8">
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-coral text-white shadow-lg shadow-orange-200"><ShieldCheck size={21} /></span>
            <div><p className="font-display text-lg font-bold tracking-tight">SignalCheck</p><p className="font-mono text-[10px] uppercase tracking-[.18em] text-slate-400">Multimodal verification</p></div>
          </div>
          <div className="flex items-center gap-2 font-mono text-[11px] text-slate-500"><span className="h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_0_4px_#dcfce7]" /> Live evidence</div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-5 py-12 lg:px-8 lg:py-16">
        <section className="max-w-3xl">
          <p className="mb-5 flex items-center gap-2 font-mono text-xs uppercase tracking-[.16em] text-coral"><Sparkles size={15} /> Evidence before opinion</p>
          <h1 className="font-display text-5xl font-bold leading-[.98] tracking-[-.06em] sm:text-7xl">Check the claim.<br /><span className="text-coral">See the evidence.</span></h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-500">Three independent workspaces for text claims, article URLs, and image screenshots. Each one extracts the claim, searches live evidence, and writes a personalized explanation.</p>
        </section>

        <section className="mt-12 grid gap-5 xl:grid-cols-3">
          <Workspace icon={<FileText size={19} />} title="Text claim" eyebrow="Direct input" description="Paste a statement and verify it against current evidence." accent="coral">
            <form onSubmit={analyzeText}>
              <textarea value={text} onChange={(event) => setText(event.target.value)} placeholder="Example: Trump is dead" className="h-32 w-full resize-none rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm outline-none transition focus:border-coral focus:bg-white focus:ring-4 focus:ring-orange-100" />
              <div className="mt-3 flex flex-wrap gap-2">{examples.map((example) => <button type="button" key={example} onClick={() => setText(example)} className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-[11px] text-slate-500 transition hover:border-coral hover:text-coral">{example}</button>)}</div>
              <SubmitButton loading={textState.loading} disabled={!text.trim()} label="Verify text claim" />
            </form>
            <ResultPanel state={textState} />
          </Workspace>

          <Workspace icon={<Link2 size={19} />} title="Article URL" eyebrow="Source input" description="Fetch an article, extract its readable text, then verify its factual claims." accent="blue">
            <form onSubmit={analyzeUrl}>
              <input value={url} onChange={(event) => setUrl(event.target.value)} type="url" placeholder="https://news.example/article" className="w-full rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm outline-none transition focus:border-sky-500 focus:bg-white focus:ring-4 focus:ring-sky-100" />
              <p className="mt-3 text-xs leading-5 text-slate-400">Best with a specific public article URL, not a homepage or login page.</p>
              <SubmitButton loading={urlState.loading} disabled={!url.trim()} label="Analyze article" />
            </form>
            <ResultPanel state={urlState} />
          </Workspace>

          <Workspace icon={<FileImage size={19} />} title="Image / screenshot" eyebrow="Visual input" description="Upload a clear screenshot. Pretrained OCR extracts the printed claim first." accent="violet">
            <form onSubmit={analyzeImage}>
              <label className="flex min-h-32 cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 text-center text-sm text-slate-500 transition hover:border-violet-400 hover:bg-violet-50">
                <FileImage className="text-violet-500" size={27} />
                <span>{image ? image.name : "Choose a PNG, JPG, or screenshot"}</span>
                <span className="text-[11px] text-slate-400">Large, high-contrast printed text works best</span>
                <input type="file" accept="image/*" className="hidden" onChange={(event) => setImage(event.target.files?.[0] || null)} />
              </label>
              <SubmitButton loading={imageState.loading} disabled={!image} label="Read and verify image" />
            </form>
            <ResultPanel state={imageState} />
          </Workspace>
        </section>
      </main>
      <footer className="border-t border-slate-200 bg-white px-5 py-8 text-center font-mono text-[11px] text-slate-400">SignalCheck uses retrieval, pretrained models, and source-linked evidence. Results are signals for review, not absolute truth.</footer>
    </div>
  );
}

function Workspace({ icon, title, eyebrow, description, accent, children }) {
  const accents = { coral: "bg-orange-50 text-coral", blue: "bg-sky-50 text-sky-600", violet: "bg-violet-50 text-violet-600" };
  return <article className="flex flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_18px_50px_rgba(29,48,82,.07)]">
    <div className="mb-5 flex items-start gap-3"><span className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${accents[accent]}`}>{icon}</span><div><p className="font-mono text-[10px] uppercase tracking-[.16em] text-slate-400">{eyebrow}</p><h2 className="mt-1 font-display text-xl font-bold">{title}</h2><p className="mt-2 text-sm leading-6 text-slate-500">{description}</p></div></div>
    {children}
  </article>;
}

function SubmitButton({ loading, disabled, label }) {
  return <button disabled={disabled || loading} className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-ink px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40">{loading ? <><LoaderCircle className="animate-spin" size={17} /> Analyzing evidence...</> : <><Search size={17} /> {label}</>}</button>;
}

function ResultPanel({ state }) {
  const [expanded, setExpanded] = useState(null);
  const result = state.result;
  const claim = result?.claims?.[0];
  if (state.loading) return <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500"><LoaderCircle className="mr-2 inline animate-spin" size={15} /> Extracting, retrieving, and verifying...</div>;
  if (state.error) return <div className="mt-5 flex gap-2 rounded-xl border border-red-100 bg-red-50 p-4 text-xs leading-5 text-red-700"><CircleAlert className="mt-0.5 shrink-0" size={16} />{state.error}</div>;
  if (!result) return <div className="mt-5 rounded-xl border border-dashed border-slate-200 p-4 text-center text-xs text-slate-400">Your extracted claim, verdict, analysis, and evidence will appear here.</div>;
  if (!claim) return <div className="mt-5 rounded-xl border border-amber-100 bg-amber-50 p-4 text-xs leading-5 text-amber-800">No factual claim was extracted from this input. Try a direct statement.</div>;
  const status = claim.verification_status;
  const statusStyle = status === "supported" ? "border-emerald-200 bg-emerald-50 text-emerald-800" : status === "refuted" ? "border-red-200 bg-red-50 text-red-800" : "border-amber-200 bg-amber-50 text-amber-800";
  const label = status === "supported" ? "Likely supported" : status === "refuted" ? "Likely refuted" : "Needs more evidence";
  return <div className="mt-5 space-y-3">
    <div className={`rounded-xl border p-4 ${statusStyle}`}><div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[.14em]"><span>{status === "refuted" ? <CircleAlert size={15} /> : <CheckCircle2 size={15} />}</span> Verdict</div><p className="mt-2 font-display text-lg font-bold">{label}</p><p className="mt-1 text-xs leading-5 opacity-80">{claim.reason}</p></div>
    <div className="rounded-xl border border-coral/20 bg-orange-50/60 p-4"><p className="font-mono text-[10px] uppercase tracking-[.14em] text-coral">Extracted claim</p><p className="mt-2 text-sm font-semibold leading-6 text-slate-700">{claim.claim_text}</p></div>
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4"><div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[.14em] text-coral"><Sparkles size={14} /> Personalized analysis</div><p className="mt-2 text-sm leading-6 text-slate-600">{claim.analysis}</p></div>
    <p className="font-mono text-[10px] uppercase tracking-[.12em] text-slate-400">{claim.evidence.length} source{claim.evidence.length === 1 ? "" : "s"} matched</p>
    {claim.evidence.map((item, index) => <div key={item.passage_id} className="rounded-xl border border-slate-200 p-4"><div className="flex items-center justify-between gap-2 text-[10px] text-slate-400"><span>0{index + 1} · {item.source_name}</span><span>{Math.round(item.nli_score * 100)}% {item.nli_label}</span></div><p className="mt-2 text-sm font-semibold leading-5 text-slate-700">{item.title}</p><button type="button" onClick={() => setExpanded(expanded === item.passage_id ? null : item.passage_id)} className="mt-3 flex items-center gap-1 text-xs font-semibold text-coral">{expanded === item.passage_id ? "Hide evidence" : "Read evidence"} <ChevronDown className={expanded === item.passage_id ? "rotate-180" : ""} size={14} /></button>{expanded === item.passage_id && <div className="mt-3 border-t border-slate-100 pt-3 text-xs leading-5 text-slate-500"><p>{item.passage}</p>{item.source_url && <a className="mt-2 inline-flex items-center gap-1 font-semibold text-coral" href={item.source_url} target="_blank" rel="noreferrer">Open source <ArrowUpRight size={13} /></a>}</div>}</div>)}
  </div>;
}

createRoot(document.getElementById("root")).render(<App />);
