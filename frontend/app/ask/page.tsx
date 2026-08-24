"use client";

import type { FormEvent, ReactNode } from "react";
import { useEffect, useMemo, useRef, useState } from "react";

type ScoreBreakdown = {
  semantic_score: number | null;
  lexical_score: number | null;
  intent_score: number | null;
};

type RetrievedChunk = {
  source: string;
  source_file: string | null;
  chunk_index: number | null;
  text: string;
  relevance_score: number | null;
  score_breakdown: ScoreBreakdown | null;
};

type AnswerResponse = {
  question: string;
  answer: string | null;
  evidence_label: string;
  evidence_reason: string;
  unsafe_question: boolean;
  scope_check: {
    in_scope: boolean;
    reason: string;
    matched_scope_terms: string[];
    matched_out_of_scope_terms: string[];
  };
  citations: string[];
  retrieved_sources: string[];
  retrieved_chunks: RetrievedChunk[];
  provider: string;
  model: string;
  api_called: boolean;
  usage_estimate: {
    input_tokens: number;
    max_output_tokens: number;
  };
};

type HealthResponse = {
  status: string;
  collection_name: string;
  vectorstore_path: string;
  indexed_chunks: number | null;
};

type ChatMessage =
  | {
      id: string;
      role: "user";
      content: string;
      createdAt: number;
    }
  | {
      id: string;
      role: "assistant";
      content: string;
      createdAt: number;
      result: AnswerResponse;
    }
  | {
      id: string;
      role: "error";
      content: string;
      createdAt: number;
    };

type Tone = "strong" | "partial" | "limited" | "outside";

const SUGGESTION_POOL = [
  "What does HbA1c measure, and why is it checked?",
  "How does the NHS Path to Remission Programme work?",
  "Which foods affect blood glucose the most?",
  "Why is blood sugar often higher in the morning?",
  "What are the early warning signs of type 2 diabetes?",
  "How often should blood glucose be checked at home?",
  "What role does exercise play in managing type 2 diabetes?",
  "What does the NICE NG28 guideline actually cover?",
];

function getErrorMessage(payload: unknown, fallback: string) {
  if (
    payload &&
    typeof payload === "object" &&
    "detail" in payload &&
    typeof payload.detail === "string"
  ) {
    return payload.detail;
  }

  return fallback;
}

function getSourceTitle(chunk: RetrievedChunk) {
  if (!chunk.source_file) {
    return chunk.source;
  }

  return chunk.source_file
    .replace(".txt", "")
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function clampToBarWidth(value: number | null) {
  if (value === null || Number.isNaN(value)) {
    return 0;
  }

  return Math.max(0, Math.min(1, value)) * 100;
}

function formatTime(ms: number) {
  return new Date(ms).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function formatSessionDate(ms: number) {
  return new Date(ms).toLocaleDateString([], {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

function getTone(result: AnswerResponse): { tone: Tone; label: string } {
  if (result.unsafe_question || !result.scope_check.in_scope) {
    return { tone: "outside", label: "Outside my scope — speak to your care team" };
  }

  const normalized = result.evidence_label.toLowerCase();

  if (normalized.includes("strong")) {
    return { tone: "strong", label: result.evidence_label };
  }

  if (normalized.includes("partial")) {
    return { tone: "partial", label: result.evidence_label };
  }

  return { tone: "limited", label: `${result.evidence_label} — read with care` };
}

function getSourceChips(result: AnswerResponse) {
  const seen = new Set<string>();
  const chips: string[] = [];

  for (const chunk of result.retrieved_chunks) {
    const title = getSourceTitle(chunk);
    const label =
      title.trim().toLowerCase() === chunk.source.trim().toLowerCase()
        ? chunk.source
        : `${chunk.source} · ${title}`;

    if (!seen.has(label)) {
      seen.add(label);
      chips.push(label);
    }
    if (chips.length >= 4) break;
  }

  return chips;
}

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [isRailCollapsed, setIsRailCollapsed] = useState(false);
  const [sessionStartedAt, setSessionStartedAt] = useState<number | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement | null>(null);
  const hasMessages = messages.length > 0;

  useEffect(() => {
    async function loadHealth() {
      try {
        const response = await fetch("/api/health");
        const data = (await response.json()) as HealthResponse;

        setHealth(data);
        setHealthError(response.ok ? null : "Backend offline");
      } catch {
        setHealthError("Backend offline");
      }
    }

    loadHealth();
  }, []);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isLoading]);

  const suggestions = useMemo(() => {
    const asked = new Set(
      messages.filter((message) => message.role === "user").map((message) => message.content)
    );
    const pool = SUGGESTION_POOL.filter((item) => !asked.has(item));
    const offset = messages.length % SUGGESTION_POOL.length;
    const rotated = [...pool.slice(offset), ...pool.slice(0, offset)];
    return rotated.slice(0, 3);
  }, [messages]);

  async function submitQuestion(event?: FormEvent<HTMLFormElement>, overrideQuestion?: string) {
    event?.preventDefault();

    const trimmedQuestion = (overrideQuestion ?? question).trim();
    if (!trimmedQuestion || isLoading) {
      return;
    }

    const now = Date.now();
    setSessionStartedAt((current) => current ?? now);

    setMessages((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        role: "user",
        content: trimmedQuestion,
        createdAt: now,
      },
    ]);
    setQuestion("");
    setIsLoading(true);

    try {
      const response = await fetch("/api/answer", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: trimmedQuestion,
          provider: "gemini",
          call_api: true,
          max_output_tokens: 500,
        }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(getErrorMessage(data, "Diasift could not answer that question."));
      }

      const result = data as AnswerResponse;

      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content:
            result.answer ??
            "I found relevant guidance passages for this question. Review the evidence below.",
          createdAt: Date.now(),
          result,
        },
      ]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "error",
          content:
            error instanceof Error
              ? error.message
              : "Something went wrong while contacting Diasift.",
          createdAt: Date.now(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  function startNewChat() {
    setMessages([]);
    setQuestion("");
    setSessionStartedAt(null);
  }

  const headerTitle = hasMessages ? messages[0].content : "Ask something about type 2 diabetes";
  const headerMeta = hasMessages
    ? `Session in progress · ${formatTime(sessionStartedAt ?? Date.now())}`
    : `New conversation · ${formatTime(Date.now())}`;

  return (
    <main className={`dsShell ${isRailCollapsed ? "railCollapsed" : ""}`}>
      <aside className="dsRail" aria-label="DiaSift session panel">
        <div className="dsBrand">
          <span className="dsBrandMark">
            <img src="/logo-icon.png" alt="DiaSift" width={24} height={24} />
          </span>
          <div className="dsBrandText">
            <span>DiaSift</span>
            <small>Type 2 diabetes assistant</small>
          </div>
          {/* <button
            className="dsCollapse"
            type="button"
            aria-label={isRailCollapsed ? "Expand panel" : "Collapse panel"}
            onClick={() => setIsRailCollapsed((current) => !current)}
          >
            <Icon name={isRailCollapsed ? "expand" : "collapse"} />
          </button> */}
        </div>

        <button className="dsNewChat" type="button" onClick={startNewChat}>
          <Icon name="plus" />
          <span>New conversation</span>
        </button>

        <div className="dsDossier">
          <DossierCard
            label="Session"
            value={formatSessionDate(sessionStartedAt ?? Date.now())}
            sub={hasMessages ? `${messages.length} exchanges · nothing saved` : "Nothing is stored"}
          />
          {/* <DossierCard
            label="Evidence base"
            value="NHS · NICE · WHO"
            sub={
              health?.indexed_chunks
                ? `${health.indexed_chunks} indexed passages`
                : healthError ?? "Checking knowledge base"
            }
          />
          <DossierCard
            label="Scope"
            value="Type 2 diabetes"
            sub="Education only — not medical advice"
          /> */}
        </div>

    
{/* 
        <p className="dsRailFoot">
           Education only: not medical advice
        </p> */}

      </aside>

      <section className="dsCanvas">
        <header className="dsCanvasHead">
          <span className="dsEyebrow">{headerMeta}</span>
          {/* <h1>{headerTitle}</h1> */}
        </header>

        <div className="dsTranscriptWrap">
          <ol className="tlList" aria-live="polite">
            {messages.map((message) => (
              <TimelineItem key={message.id} message={message} />
            ))}

            {isLoading ? (
              <li className="tlItem assistant pending">
                <span className="tlMarker assistant">
                  <span className="tlDot pulsing" />
                </span>
                <div className="tlBody">
                  <div className="tlHead">
                    <span className="tlWho">DiaSift</span>
                  </div>
                  <p className="tlTyping">
                    Sifting trusted evidence<span className="tlCaret">▍</span>
                  </p>
                </div>
              </li>
            ) : null}

            <div ref={transcriptEndRef} />
          </ol>

          {!hasMessages ? (
            <div className="dsStarter">
              <span className="dsStarterLabel">Try asking</span>
              <div className="dsStarterList">
                {SUGGESTION_POOL.slice(0, 4).map((item) => (
                  <button
                    key={item}
                    type="button"
                    className="dsStarterRow"
                    onClick={() => submitQuestion(undefined, item)}
                  >
                    <span>{item}</span>
                    <span className="dsStarterArrow">
                      <svg
                        viewBox="0 0 512 512"
                        width="14"
                        height="14"
                        fill="currentColor"
                        aria-hidden="true"
                      >
                        <path d="M0 0 C9.18169561 5.60100568 16.68256623 13.90920335 24.23968506 21.47424316 C25.59984895 22.82995037 25.59984895 22.82995037 26.98749089 24.2130456 C29.4752826 26.69286554 31.96002227 29.175723 34.44420266 31.6591599 C37.13498327 34.34807283 39.828604 37.03413838 42.52180481 39.72062683 C48.39401515 45.57932832 54.26251241 51.44173945 60.13017941 57.30499077 C63.79787706 60.96991605 67.4663073 64.63410744 71.13486481 68.298172 C81.30582131 78.45695072 91.4758412 88.61666503 101.64240646 98.77983856 C102.61587872 99.75298147 102.61587872 99.75298147 103.60901709 100.74578384 C104.25946684 101.39601531 104.90991659 102.04624678 105.58007693 102.71618223 C106.89794687 104.03360872 108.21581837 105.35103365 109.53369141 106.66845703 C110.18738839 107.32193259 110.84108538 107.97540815 111.51459137 108.64868599 C122.1192415 119.2493836 132.73063552 129.84330305 143.34493348 140.43433958 C154.26005923 151.32573843 165.16953762 162.22276743 176.07338929 173.12545347 C182.18874795 179.23989668 188.30648679 185.35191493 194.43047333 191.4577179 C199.64103849 196.65286474 204.84641139 201.85314515 210.04514757 207.06013024 C212.69528936 209.71417096 215.34776426 212.36576044 218.00688362 215.01080894 C220.89388024 217.88266835 223.76903283 220.76610708 226.64324951 223.65075684 C227.8966515 224.89207422 227.8966515 224.89207422 229.17537475 226.15846872 C237.01211358 234.06179116 243.49486151 241.83763696 244 253.375 C243.73642204 261.1505498 242.01852547 266.99060553 236.66343689 272.76444435 C235.85517393 273.63701228 235.04691097 274.50958022 234.2141552 275.4085896 C230.19969243 279.62524112 226.12554859 283.775955 222.01000977 287.89389038 C221.06800238 288.8399259 220.12620155 289.78616713 219.18458652 290.73259318 C216.62494967 293.30404776 214.06228913 295.87246933 211.49903917 298.44032168 C208.72428098 301.22109177 205.95231931 304.00464755 203.17990112 306.78775024 C196.50408821 313.4879413 189.82345519 320.18331576 183.1419158 326.87779564 C181.25336171 328.77006917 179.36493433 330.66246905 177.47655106 332.55491304 C165.73105789 344.32562527 153.98397284 356.09474629 142.23210144 367.85909081 C139.51832143 370.57580004 136.8045577 373.29252554 134.09082031 376.00927734 C133.07920552 377.02201121 133.07920552 377.02201121 132.04715407 378.05520435 C121.1041708 389.01086198 110.17152197 399.97677327 99.24302256 410.94687693 C88.00728236 422.2250386 76.76213495 433.49375161 65.50777721 444.7533356 C59.19506348 451.06946065 52.88656995 457.38967901 46.58865356 463.72056198 C41.2306769 469.10654151 35.86427291 474.48394069 30.48668122 479.85033886 C27.74499652 482.58683992 25.00749692 485.32720554 22.28081894 488.07866669 C19.32234476 491.06380572 16.34477 494.02913967 13.36499023 496.99301147 C12.51020867 497.86167512 11.65542711 498.73033877 10.77474308 499.62532556 C3.7765725 506.53177066 -2.67661221 510.63584326 -12.75 510.625 C-24.98773556 510.23417411 -31.84075972 504.34228242 -40.3125 496.0625 C-41.26898438 495.15628906 -42.22546875 494.25007813 -43.2109375 493.31640625 C-51.59715849 485.27670023 -58.02321702 477.87673604 -58.6875 465.8125 C-58.27937031 451.72002202 -48.71993734 443.31117898 -39.37147522 434.0012207 C-38.60186995 433.23076101 -37.83226469 432.46030132 -37.03933805 431.66649437 C-34.47919322 429.10471224 -31.91550886 426.54650294 -29.35180664 423.98828125 C-27.50821814 422.14497502 -25.66485021 420.30144817 -23.82168579 418.4577179 C-19.86300703 414.49851664 -15.90251217 410.54113976 -11.94075203 406.58502197 C-6.21282577 400.86524812 -0.48768688 395.14269087 5.23679144 389.4194665 C14.52610255 380.13234004 23.81764121 370.84744554 33.1105957 361.56396484 C42.13390769 352.54984216 51.15616113 343.53466212 60.17700195 334.51806641 C61.01209562 333.68336683 61.01209562 333.68336683 61.86405986 332.83180463 C64.65720397 330.03996562 67.45032739 327.2481059 70.24344051 324.45623589 C93.38825185 301.32177889 116.53668448 278.19094859 139.6875 255.0625 C138.33506616 252.04412461 136.82912622 249.95783827 134.48807049 247.63094139 C133.82532673 246.96729903 133.16258296 246.30365666 132.47975606 245.61990392 C131.74971216 244.89909631 131.01966827 244.1782887 130.26750183 243.43563843 C129.49344586 242.66340144 128.71938989 241.89116445 127.92187768 241.09552634 C125.31873812 238.50082153 122.70853752 235.91333587 120.09838867 233.32568359 C118.23384525 231.46988708 116.36977678 229.61361328 114.50614929 227.75689697 C110.48756535 223.7543242 106.46561631 219.75515903 102.44164085 215.75800705 C96.07755083 209.43584931 89.72326442 203.10388883 83.37043762 196.77041626 C81.19587636 194.60273507 79.02123922 192.43513004 76.84657001 190.26755714 C76.30308068 189.72583946 75.75959135 189.18412178 75.19963264 188.62598842 C69.01308163 182.45993222 62.82420657 176.29621074 56.63452148 170.13330078 C56.06874723 169.56996909 55.50297298 169.00663739 54.92005406 168.42623504 C45.75840738 159.304565 36.59084636 150.1888558 27.42196544 141.07445841 C18.00313003 131.71111109 8.59397935 122.33810296 -0.80713671 112.95696509 C-6.60263588 107.17452151 -12.40598145 101.4001844 -18.21975841 95.63611694 C-22.20706505 91.68160072 -26.18517591 87.71798672 -30.15627984 83.74720065 C-32.44524377 81.45900105 -34.73938636 79.17646297 -37.04206085 76.90205002 C-39.54364806 74.42992491 -42.02922574 71.94270839 -44.5115509 69.45126343 C-45.5965785 68.3901285 -45.5965785 68.3901285 -46.70352584 67.30755651 C-53.34033627 60.58442327 -57.88283536 53.10964265 -58.37890625 43.50390625 C-58.03171022 30.73934642 -50.71259556 22.9210203 -42.03027344 14.27929688 C-40.56493419 12.81493257 -39.1222866 11.33048028 -37.6796875 9.84375 C-27.30401802 -0.67166883 -14.70829838 -6.68137213 0 0 Z" transform="translate(163.3125,1.9375)" />
                      </svg>
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {hasMessages && !isLoading && suggestions.length ? (
            <div className="dsFollowUps">
              <span className="dsFollowUpsLabel">Keep exploring</span>
              {suggestions.map((item) => (
                <button
                  key={item}
                  type="button"
                  className="dsStarterRow"
                  onClick={() => submitQuestion(undefined, item)}
                >
                  <span>{item}</span>
                  <span className="dsStarterArrow">→</span>
                </button>
              ))}
            </div>
          ) : null}
        </div>

        <div className="dsDock">
          <PromptBox
            question={question}
            isLoading={isLoading}
            onQuestionChange={setQuestion}
            onSubmit={submitQuestion}
          />
          {/* <p className="dsDisclaimer">
            DiaSift is an AI assistant for education about type 2 diabetes, answering from trusted
            sources like the NHS and NICE. It isn&apos;t a substitute for your care team. If
            you&apos;re worried about symptoms, contact your GP or NHS 111 — in an emergency, call
            999.
          </p> */}
        </div>
      </section>
    </main>
  );
}

function DossierCard({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="dossierCard">
      <span className="dossierLabel">{label}</span>
      <strong className="dossierValue">{value}</strong>
      <span className="dossierSub">{sub}</span>
    </div>
  );
}

function TimelineItem({ message }: { message: ChatMessage }) {
  const time = formatTime(message.createdAt);

  if (message.role === "user") {
    return (
      <li className="tlItem user">
        <span className="tlMarker user">
          <span className="tlRing" />
        </span>
        <div className="tlBody">
          <div className="tlHead">
            <span className="tlWho">You</span>
            <span className="tlTime">{time}</span>
          </div>
          <p className="tlText">{message.content}</p>
        </div>
      </li>
    );
  }

  if (message.role === "error") {
    return (
      <li className="tlItem error">
        <span className="tlMarker error">
          <span className="tlDot" />
        </span>
        <div className="tlBody">
          <div className="tlHead">
            <span className="tlWho">DiaSift</span>
            <span className="tlTime">{time}</span>
          </div>
          <div className="evidenceStamp tone-error">
            <span className="stampDot" /> Connection issue
          </div>
          <p className="tlText">{message.content}</p>
        </div>
      </li>
    );
  }

  const { tone, label } = getTone(message.result);
  const chips = getSourceChips(message.result);

  return (
    <li className={`tlItem assistant tone-${tone}`}>
      <span className={`tlMarker assistant tone-${tone}`}>
        <span className="tlDot" />
      </span>
      <div className="tlBody">
        <div className="tlHead">
          <span className="tlWho">DiaSift</span>
          <span className="tlTime">{time}</span>
        </div>

        <div className={`evidenceStamp tone-${tone}`}>
          <span className="stampDot" /> {label}
        </div>

        <p className="tlText">{message.content}</p>

        {chips.length ? (
          <div className="sourceChips">
            {chips.map((chip) => (
              <span className="sourceChip" key={chip}>
                {chip}
              </span>
            ))}
          </div>
        ) : null}

        {message.result.retrieved_chunks.length ? (
          <details className="evidenceDrawer">
            <summary>Show retrieval evidence</summary>

            <div className="evidenceGrid">
              {message.result.retrieved_chunks.slice(0, 3).map((chunk, index) => (
                <article
                  className="evidenceCard"
                  key={`${chunk.source_file}-${chunk.chunk_index}-${index}`}
                >
                  <div className="evidenceTopline">
                    <span>{chunk.source}</span>
                    <strong>{label}</strong>
                  </div>
                  <h2>{getSourceTitle(chunk)}</h2>
                  <p>{chunk.text}</p>

                  {chunk.score_breakdown ? (
                    <details className="scoreBreakdown">
                      <summary>Why this matched</summary>
                      <ScoreBar label="Semantic similarity" value={chunk.score_breakdown.semantic_score} />
                      <ScoreBar label="Keyword overlap" value={chunk.score_breakdown.lexical_score} />
                      <ScoreBar label="Intent match" value={chunk.score_breakdown.intent_score} />
                    </details>
                  ) : null}
                </article>
              ))}
            </div>

            <p className="techMeta">
              {message.result.provider} · {message.result.model} ·{" "}
              {message.result.api_called ? "LLM answer" : "Retrieved evidence"}
            </p>
          </details>
        ) : null}
      </div>
    </li>
  );
}

function ScoreBar({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="scoreRow">
      <span className="scoreLabel">{label}</span>
      <div className="scoreBarTrack">
        <div className="scoreBarFill" style={{ width: `${clampToBarWidth(value)}%` }} />
      </div>
      <span className="scoreValue">{value === null ? "-" : value.toFixed(2)}</span>
    </div>
  );
}

function PromptBox({
  question,
  isLoading,
  onQuestionChange,
  onSubmit,
}: {
  question: string;
  isLoading: boolean;
  onQuestionChange: (question: string) => void;
  onSubmit: (event?: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form className="promptBox" onSubmit={onSubmit}>
      <input
        value={question}
        onChange={(event) => onQuestionChange(event.target.value)}
        placeholder="Ask about type 2 diabetes…"
        maxLength={1000}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            onSubmit();
          }
        }}
      />

      <button className="sendButton" type="submit" disabled={isLoading || !question.trim()}>
        {isLoading ? "…" : "Send"}
      </button>
    </form>
  );
}

type IconName = "spark" | "plus" | "collapse" | "expand";

function Icon({ name }: { name: IconName }) {
  const paths: Record<IconName, ReactNode> = {
    spark: (
      <>
        <path d="M12 3v3" />
        <path d="M12 18v3" />
        <path d="M3 12h3" />
        <path d="M18 12h3" />
        <path d="m5.6 5.6 2.1 2.1" />
        <path d="m16.3 16.3 2.1 2.1" />
        <path d="m18.4 5.6-2.1 2.1" />
        <path d="m7.7 16.3-2.1 2.1" />
        <circle cx="12" cy="12" r="3" />
      </>
    ),
    plus: (
      <>
        <path d="M12 5v14" />
        <path d="M5 12h14" />
      </>
    ),
    collapse: (
      <>
        <path d="M15 6 9 12l6 6" />
        <path d="M20 6v12" />
      </>
    ),
    expand: (
      <>
        <path d="m9 6 6 6-6 6" />
        <path d="M4 6v12" />
      </>
    ),
  };

  return (
    <svg
      aria-hidden="true"
      className="icon"
      fill="none"
      viewBox="0 0 24 24"
      xmlns="http://www.w3.org/2000/svg"
    >
      {paths[name]}
    </svg>
  );
}
