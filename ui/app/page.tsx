"use client";

import {
  Check, ChevronDown, ChevronRight, CircleHelp, Clipboard, Code2, Download,
  FlaskConical, House, LoaderCircle, Play, RefreshCw, Server, Trash2,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";

type Question = {
  type: "choice" | "score" | "noul";
  instructions: unknown;
  criteria?: unknown;
};
type Sample = { name: string; format: "text" | "json"; state: unknown; checkpoint?: string };
type Preset = {
  id: string;
  name: string;
  description: string;
  checkpoint: string;
  questions: Record<string, Question>;
  samples: Sample[];
};
type Health = {
  mode: string;
  status: string;
  checkpoint: string | null;
  busy: boolean;
  actual_device: string | null;
};
type Answer = {
  type: "choice" | "score" | "noul";
  choice?: string;
  score?: number;
  noul?: number;
  confidence?: number;
  probabilities?: Record<string, number>;
  legend?: Record<string, string>;
};
type Prediction = {
  mode: "laya";
  result: { answers: Record<string, Answer>; model: string };
  runtime: { checkpoint: string; device: string; total_ms: number; cold_load: boolean };
  warnings: string[];
  context?: { truncated_questions?: string[] };
};

const checkpoints = [
  { value: "typed-decisions", label: "Typed decisions" },
  { value: "english", label: "English" },
  { value: "multilingual", label: "Multilingual" },
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isPreset(value: unknown): value is Preset {
  return isRecord(value) && typeof value.id === "string" &&
    typeof value.name === "string" && typeof value.description === "string" &&
    typeof value.checkpoint === "string" && isRecord(value.questions) &&
    Array.isArray(value.samples) && value.samples.length > 0 && value.samples.every((sample: unknown) =>
      isRecord(sample) && typeof sample.name === "string" &&
      (sample.format === "text" || sample.format === "json") && "state" in sample);
}

function isPrediction(value: unknown): value is Prediction {
  return isRecord(value) && value.mode === "laya" && isRecord(value.result) &&
    isRecord(value.result.answers) && isRecord(value.runtime) &&
    typeof value.runtime.total_ms === "number" &&
    typeof value.runtime.checkpoint === "string" &&
    Array.isArray(value.warnings);
}

function jsonText(value: unknown): string {
  return JSON.stringify(value, null, 2) ?? "";
}

function instructionText(value: unknown): string {
  if (typeof value === "string") return value;
  if (isRecord(value)) {
    return Object.entries(value).map(([key, item]) => key + ": " + String(item)).join("\n");
  }
  return jsonText(value);
}

function percent(value: number | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  return Math.round(Math.max(0, Math.min(1, value)) * 100) + "%";
}

async function errorMessage(response: Response): Promise<string> {
  const body: unknown = await response.json().catch(() => null);
  return isRecord(body) && typeof body.error === "string" ? body.error : "The request failed. Check the backend terminal.";
}

function CodeEditor({
  id, label, value, onChange, hint, action, invalid,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  hint: string;
  action?: React.ReactNode;
  invalid?: boolean;
}) {
  const gutter = useRef<HTMLDivElement>(null);
  const lines = Math.max(1, value.split("\n").length);
  return (
    <section className={"editorPane" + (invalid ? " editorPaneInvalid" : "")} aria-label={label}>
      <div className="paneHeading">
        <label htmlFor={id}>{label}</label>
        <div className="paneHeadingActions"><span className="paneHint">{hint}</span>{action}</div>
      </div>
      <div className="codeField">
        <div className="lineNumbers" ref={gutter} aria-hidden="true">
          {Array.from({ length: lines }, (_, index) => <div key={index}>{index + 1}</div>)}
        </div>
        <textarea
          id={id}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onScroll={(event) => {
            if (gutter.current) gutter.current.scrollTop = event.currentTarget.scrollTop;
          }}
          spellCheck={false}
          autoCapitalize="off"
          autoCorrect="off"
          aria-invalid={invalid || undefined}
          className="codeInput"
        />
      </div>
    </section>
  );
}

function ProbabilityMark({ value }: { value: number }) {
  const safe = Math.max(0, Math.min(1, value));
  return (
    <span className="probability">
      <span>{percent(safe)}</span>
      <span
        className="probabilityRing"
        style={{ background: "conic-gradient(var(--probability) " + Math.round(safe * 100) + "%, var(--ring-track) 0)" }}
        aria-hidden="true"
      />
    </span>
  );
}

function ResponseRow({ id, question, answer }: { id: string; question?: Question; answer: Answer }) {
  const [expanded, setExpanded] = useState(true);
  const [showAll, setShowAll] = useState(false);
  const kind = answer.type;
  let options: [string, number][];
  if (kind === "noul") {
    const yes = answer.noul ?? 0;
    options = [["true", yes], ["false", 1 - yes]];
  } else {
    options = Object.entries(answer.probabilities ?? {}).sort((left, right) => right[1] - left[1]);
  }
  const visible = showAll ? options : options.slice(0, 3);
  const primary = kind === "choice" ? answer.choice :
    kind === "score" ? (answer.score?.toFixed(2) ?? "—") : percent(answer.noul);
  const typeLabel = kind === "noul" ? "Yes / no" : kind === "score" ? "Score" : "Choice";
  return (
    <article className="responseRow">
      <div className="responseQuestion">
        <button
          className="collapseButton"
          type="button"
          onClick={() => setExpanded(!expanded)}
          aria-label={(expanded ? "Collapse " : "Expand ") + id}
          aria-expanded={expanded}
        >
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>
        <div className="questionCopy">
          <div className="questionKey">{id}</div>
          {expanded && <div className="questionInstruction">{instructionText(question?.instructions)}</div>}
        </div>
      </div>
      <div className="responseAnswer">
        <div className={"primaryAnswer" + (kind === "score" ? " visible" : "")}>{kind === "score" ? "Score " + primary + " / " + (options.length - 1) : primary}</div>
        {expanded && (
          <>
            <div className="optionList">
              {visible.map(([label, probability]) => (
                <div className="optionLine" key={label}>
                  <span title={answer.legend?.[label]}>{label}</span>
                  <ProbabilityMark value={probability} />
                </div>
              ))}
            </div>
            {options.length > 3 && (
              <button className="textButton" type="button" onClick={() => setShowAll(!showAll)}>
                {showAll ? "Show less" : "Show all " + options.length + " options"}
              </button>
            )}
            <div className="confidence" title="Model confidence is not measured accuracy.">
              Confidence {percent(answer.confidence)}
            </div>
          </>
        )}
      </div>
      <div className="answerMeta">
        <span className="typeTag">{typeLabel}</span>
        {kind === "choice" && <span>{options.length} options</span>}
      </div>
    </article>
  );
}

export default function Page() {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState("");
  const [sampleIndex, setSampleIndex] = useState(0);
  const [stateMode, setStateMode] = useState<"json" | "text">("json");
  const [stateText, setStateText] = useState("");
  const [questionsText, setQuestionsText] = useState("");
  const [checkpoint, setCheckpoint] = useState("typed-decisions");
  const [health, setHealth] = useState<Health | null>(null);
  const [checking, setChecking] = useState(true);
  const [running, setRunning] = useState(false);
  const [response, setResponse] = useState<Prediction | null>(null);
  const [ranAt, setRanAt] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [invalidField, setInvalidField] = useState<"state" | "questions" | null>(null);
  const [responseView, setResponseView] = useState<"overview" | "json">("overview");

  useEffect(() => {
    let active = true;
    let initialized = false;
    async function refresh() {
      try {
        const healthResponse = await fetch("/api/laya/health", { cache: "no-store" });
        if (!healthResponse.ok) throw new Error("offline");
        const value: unknown = await healthResponse.json();
        if (!isRecord(value) || typeof value.status !== "string" || typeof value.mode !== "string") {
          throw new Error("invalid health");
        }
        if (active) {
          setHealth(value as Health);
          setChecking(false);
        }
        if (!initialized) {
          const presetsResponse = await fetch("/api/laya/presets", { cache: "no-store" });
          if (presetsResponse.ok) {
            const data: unknown = await presetsResponse.json();
            if (Array.isArray(data)) {
              const available = data.filter(isPreset);
              if (active && available.length > 0) {
                setPresets(available);
                const first = available[0];
                setSelectedPreset(first.id);
                setSampleIndex(0);
                setStateMode(first.samples[0].format);
                setStateText(first.samples[0].format === "json" ? jsonText(first.samples[0].state) : String(first.samples[0].state));
                setQuestionsText(jsonText(first.questions));
                setCheckpoint(first.samples[0].checkpoint ?? first.checkpoint);
                initialized = true;
              }
            }
          }
        }
      } catch {
        if (active) {
          setHealth(null);
          setChecking(false);
        }
      }
    }
    void refresh();
    const timer = window.setInterval(() => void refresh(), 5000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  const activePreset = presets.find((preset) => preset.id === selectedPreset);
  const statusText = checking ? "Checking backend" : health === null ? "Backend offline" :
    health.mode !== "laya" ? "Restart real backend" :
    health.busy ? "Model busy" : health.status === "ready" ? "Model ready" : "Backend online";
  const statusKind = checking ? "checking" : health === null || health.mode !== "laya" ? "offline" :
    health.busy ? "busy" : "ready";
  const canRun = health?.mode === "laya" && !running && !health.busy;

  function chooseSample(preset: Preset, index: number) {
    const sample = preset.samples[index];
    if (!sample) return;
    setSelectedPreset(preset.id);
    setSampleIndex(index);
    setStateMode(sample.format);
    setStateText(sample.format === "json" ? jsonText(sample.state) : String(sample.state));
    setQuestionsText(jsonText(preset.questions));
    setCheckpoint(sample.checkpoint ?? preset.checkpoint);
    setResponse(null);
    setError("");
    setNotice("");
    setInvalidField(null);
  }

  function parseRequest(): { state: unknown; questions: Record<string, unknown>; checkpoint: string } {
    let state: unknown = stateText;
    if (stateMode === "json") {
      try {
        state = JSON.parse(stateText) as unknown;
      } catch {
        setInvalidField("state");
        throw new Error("State is not valid JSON. Fix it or switch to Text.");
      }
    }
    if ((typeof state === "string" && !state.trim()) || state === null) {
      setInvalidField("state");
      throw new Error("State cannot be empty.");
    }
    let questions: unknown;
    try {
      questions = JSON.parse(questionsText) as unknown;
    } catch {
      setInvalidField("questions");
      throw new Error("Questions are not valid JSON.");
    }
    if (!isRecord(questions) || Object.keys(questions).length === 0) {
      setInvalidField("questions");
      throw new Error("Questions must be a nonempty JSON object.");
    }
    setInvalidField(null);
    return { state, questions, checkpoint };
  }

  async function runRequest() {
    setError("");
    setNotice("");
    let payload: { state: unknown; questions: Record<string, unknown>; checkpoint: string };
    try {
      payload = parseRequest();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Check the JSON editors.");
      return;
    }
    setRunning(true);
    setResponse(null);
    try {
      const request = await fetch("/api/laya/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!request.ok) throw new Error(await errorMessage(request));
      const result: unknown = await request.json();
      if (!isPrediction(result)) throw new Error("The backend returned an unexpected response.");
      setResponse(result);
      setRanAt(new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }));
      setResponseView("overview");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Request failed. Check the backend terminal.");
    } finally {
      setRunning(false);
    }
  }

  async function copyRequest() {
    try {
      const payload = parseRequest();
      await navigator.clipboard.writeText(jsonText(payload));
      setNotice("Request JSON copied.");
      setError("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not copy the request.");
    }
  }

  function downloadResponse() {
    if (!response) return;
    const blob = new Blob([jsonText(response)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "laya-response.json";
    link.click();
    URL.revokeObjectURL(url);
  }

  async function unloadModel() {
    try {
      const result = await fetch("/api/laya/unload", { method: "POST" });
      if (!result.ok) throw new Error(await errorMessage(result));
      setNotice("Model unloaded. The next request will load it again.");
      setHealth((current) => current ? { ...current, status: "not loaded", checkpoint: null } : current);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not unload the model.");
    }
  }

  return (
    <div className="appShell">
      <aside className="sidebar">
        <div className="brand"><span className="brandGlyph"><FlaskConical size={17} /></span><span>LAYA</span><span className="brandSuffix">/ playground</span></div>
        <nav className="primaryNav" aria-label="Primary">
          <div className="navLabel">Workspace</div>
          <Link className="navItem selected" href="/"><FlaskConical size={16} /> Playground</Link>
          <a className="navItem" href="https://github.com/NandhaKishorM/laya" target="_blank" rel="noreferrer"><House size={16} /> About Laya</a>
          <div className="navLabel examplesLabel">Examples</div>
          {presets.map((preset) => (
            <button
              className={"navItem exampleNav" + (preset.id === selectedPreset ? " exampleSelected" : "")}
              type="button"
              key={preset.id}
              onClick={() => chooseSample(preset, 0)}
              aria-current={preset.id === selectedPreset ? "page" : undefined}
            >
              <Code2 size={15} /> {preset.name}
            </button>
          ))}
        </nav>
        <div className="sidebarBottom">
          <div className={"serviceStatus " + statusKind} aria-live="polite">
            <span className="statusDot" /><span>{statusText}</span>
          </div>
          {health && <div className="serviceDetail">{health.checkpoint ?? "No model loaded"}{health.actual_device ? " · " + health.actual_device : ""}</div>}
          {health?.checkpoint && <button className="sidebarAction" type="button" onClick={() => void unloadModel()}><Trash2 size={13} /> Unload model</button>}
        </div>
      </aside>

      <main className="workbench">
        <div className="editorColumn">
          <header className="topbar">
            <div className="pageTitle"><FlaskConical size={16} /> Playground</div>
            <div className="toolbarActions">
              <button className="toolbarButton" type="button" onClick={() => {
                setStateText(""); setQuestionsText(""); setResponse(null); setError(""); setNotice("");
              }}>Clear</button>
              <button className="toolbarButton outlined" type="button" onClick={() => void copyRequest()}><Clipboard size={14} /> Copy request</button>
            </div>
          </header>

          <div className="editors">
            <CodeEditor
              id="state-editor"
              label="State"
              value={stateText}
              onChange={(value) => { setStateText(value); setResponse(null); }}
              hint={stateMode.toUpperCase()}
              invalid={invalidField === "state"}
              action={<button className="miniButton" type="button" onClick={() => setStateMode(stateMode === "json" ? "text" : "json")} title="Switch State editor between JSON and text">{stateMode === "json" ? <Code2 size={15} /> : <span>TXT</span>}</button>}
            />
            <CodeEditor
              id="questions-editor"
              label="Questions"
              value={questionsText}
              onChange={(value) => { setQuestionsText(value); setResponse(null); }}
              hint="JSON"
              invalid={invalidField === "questions"}
              action={<span className="questionCount" title="Question count"><CircleHelp size={13} /> {(() => { try { const value: unknown = JSON.parse(questionsText); return isRecord(value) ? Object.keys(value).length : 0; } catch { return "!" } })()}</span>}
            />
          </div>

          <div className="runBar">
            <div className="runOptions">
              <label className="visuallyHidden" htmlFor="sample-picker">Example input</label>
              <select
                id="sample-picker"
                value={sampleIndex}
                onChange={(event) => { if (activePreset) chooseSample(activePreset, Number(event.target.value)); }}
                disabled={!activePreset}
                className="sampleSelect"
              >
                {(activePreset?.samples ?? []).map((sample, index) => <option value={index} key={sample.name}>{sample.name}</option>)}
              </select>
              <label className="visuallyHidden" htmlFor="checkpoint-picker">Model checkpoint</label>
              <select id="checkpoint-picker" value={checkpoint} onChange={(event) => { setCheckpoint(event.target.value); setResponse(null); }} className="modelSelect">
                {checkpoints.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}
              </select>
            </div>
            <button className="runButton" type="button" onClick={() => void runRequest()} disabled={!canRun}>
              {running ? <LoaderCircle size={16} className="spin" /> : <Play size={15} fill="currentColor" />}
              {running ? "Running…" : "Run request"}
            </button>
          </div>
        </div>

        <section className="responseColumn" aria-label="Response">
          <header className="topbar responseTopbar">
            <div className="responseTitle">Response <span>· {running ? "Running now" : response ? "Ran at " + ranAt : "Waiting for request"}</span></div>
            <div className="viewSwitch" role="group" aria-label="Response view">
              <button className={responseView === "overview" ? "active" : ""} type="button" onClick={() => setResponseView("overview")} title="Overview"><span aria-hidden="true">☰</span><span className="visuallyHidden">Overview</span></button>
              <button className={responseView === "json" ? "active" : ""} type="button" onClick={() => setResponseView("json")} title="JSON"><Code2 size={15} /><span className="visuallyHidden">JSON</span></button>
              <button type="button" onClick={downloadResponse} disabled={!response} title="Download response"><Download size={15} /><span className="visuallyHidden">Download response</span></button>
            </div>
          </header>
          <div className="responseBody" aria-live="polite">
            {error && <div className="notice errorNotice" role="alert">{error}</div>}
            {notice && <div className="notice infoNotice"><Check size={15} /> {notice}</div>}
            {!health && !checking && <div className="offlinePanel"><Server size={24} /><h2>Backend offline</h2><p>Start the Python service in a second terminal, then this page will connect automatically.</p><code>.\backend\run.ps1</code><button type="button" onClick={() => window.location.reload()}><RefreshCw size={14} /> Check again</button></div>}
            {running && <div className="emptyResponse"><LoaderCircle size={24} className="spin" /><h2>Laya is evaluating</h2><p>The first request may download and load the model. Keep the backend terminal open for progress.</p></div>}
            {!response && !running && health && !error && (
              <div className="emptyResponse"><FlaskConical size={24} /><h2>Ready for a decision</h2><p>Edit the state and questions, then run a request. Results from the real Laya model will appear here.</p></div>
            )}
            {response && responseView === "json" && <pre className="rawResponse">{jsonText(response)}</pre>}
            {response && responseView === "overview" && (
              <>
                <div className="responseTableHeading">
                  <span>Key &amp; instructions</span>
                  <span>{response.runtime.checkpoint} · {Math.round(response.runtime.total_ms)}ms</span>
                  <span>Type</span>
                </div>
                {Object.entries(response.result.answers).map(([id, answer]) => (
                  <ResponseRow key={id} id={id} answer={answer} question={(() => {
                    try {
                      const value: unknown = JSON.parse(questionsText);
                      return isRecord(value) && isRecord(value[id]) ? value[id] as Question : undefined;
                    } catch { return undefined; }
                  })()} />
                ))}
                <div className="responseFooter">
                  <span>{response.result.model} · {response.runtime.device}</span>
                  {response.runtime.cold_load && <span>Model loaded for this request</span>}
                </div>
                {response.warnings.map((warning) => <div className="warningLine" key={warning}>{warning}</div>)}
              </>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
