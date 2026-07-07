"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

type Provider = "gemini" | "openai";

type RetrievedChunk = {
  source: string;
  source_file: string | null;
  chunk_index: number | null;
  text: string;
  relevance_score: number | null;
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
    }
  | {
      id: string;
      role: "assistant";
      content: string;
      result: AnswerResponse;
    }
  | {
      id: string;
      role: "error";
      content: string;
    };

const fallbackSources: RetrievedChunk[] = [
  {
    source: "NHS",
    source_file: "nhs_type2diabetes_path_to_remission.txt",
    chunk_index: 1,
    text: "The NHS Type 2 Diabetes Path to Remission Programme can involve total diet replacement followed by gradual food reintroduction.",
    relevance_score: 2.8,
  },
  {
    source: "NICE",
    source_file: "nice_type2diabetes_overview.txt",
    chunk_index: 2,
    text: "Guidance may recommend referral to an intensive lifestyle-change programme for eligible adults with type 2 diabetes.",
    relevance_score: 2.4,
  },
  {
    source: "Diabetes UK",
    source_file: "nhs_diabetes_overview.txt",
    chunk_index: 3,
    text: "Remission means blood glucose levels are below the diabetes range without needing glucose-lowering medication.",
    relevance_score: 1.8,
  },
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

function getSourceLabel(chunk: RetrievedChunk) {
  const source = chunk.source.toLowerCase();

  if (source.includes("nice")) {
    return "NICE";
  }

  if (source.includes("diabetes uk")) {
    return "Diabetes UK";
  }

  if (source.includes("nhs")) {
    return "NHS";
  }

  return chunk.source;
}

function getEvidenceTone(label: string) {
  const normalizedLabel = label.toLowerCase();

  if (normalizedLabel.includes("strong")) {
    return "strong";
  }

  if (normalizedLabel.includes("partial") || normalizedLabel.includes("moderate")) {
    return "moderate";
  }

  return "limited";
}

function formatEvidenceLabel(label: string) {
  if (label.toLowerCase().includes("strong")) {
    return "Strong";
  }

  if (label.toLowerCase().includes("partial")) {
    return "Moderate";
  }

  return "Limited";
}

function getCardTitle(chunk: RetrievedChunk) {
  if (chunk.source_file) {
    return chunk.source_file
      .replace(".txt", "")
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  }

  return chunk.source;
}

export default function Home() {
  const [question, setQuestion] = useState("");
  const [provider, setProvider] = useState<Provider>("gemini");
  const [callApi, setCallApi] = useState(false);
  const [maxOutputTokens, setMaxOutputTokens] = useState(500);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const contentEndRef = useRef<HTMLDivElement | null>(null);

  const latestResult = useMemo(() => {
    return [...messages]
      .reverse()
      .find((message): message is Extract<ChatMessage, { role: "assistant" }> => {
        return message.role === "assistant";
      })?.result;
  }, [messages]);

  const latestUserQuestion = useMemo(() => {
    return [...messages]
      .reverse()
      .find((message): message is Extract<ChatMessage, { role: "user" }> => {
        return message.role === "user";
      })?.content;
  }, [messages]);

  const latestError = useMemo(() => {
    return [...messages]
      .reverse()
      .find((message): message is Extract<ChatMessage, { role: "error" }> => {
        return message.role === "error";
      })?.content;
  }, [messages]);

  const displayedChunks = latestResult?.retrieved_chunks.length
    ? latestResult.retrieved_chunks.slice(0, 5)
    : fallbackSources;

  const evidenceTone = getEvidenceTone(latestResult?.evidence_label ?? "Strong");
  const healthStatus = healthError
    ? "Knowledge base offline"
    : health?.status === "ok"
      ? "Knowledge base active"
      : "Checking knowledge base";

  useEffect(() => {
    async function loadHealth() {
      try {
        const response = await fetch("/api/health");
        const data = (await response.json()) as HealthResponse;

        if (!response.ok) {
          setHealthError("Backend is offline.");
        } else {
          setHealthError(null);
        }

        setHealth(data);
      } catch {
        setHealthError("Backend is offline.");
      }
    }

    loadHealth();
  }, []);

  useEffect(() => {
    contentEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isLoading]);

  async function submitQuestion(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();

    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isLoading) {
      return;
    }

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmedQuestion,
    };

    setMessages((current) => [...current, userMessage]);
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
          provider,
          call_api: callApi,
          max_output_tokens: maxOutputTokens,
        }),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(getErrorMessage(data, "Diasift could not answer that question."));
      }

      const result = data as AnswerResponse;
      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content:
          result.answer ??
          "Dry run complete. Diasift has retrieved the most relevant source passages for this question.",
        result,
      };

      setMessages((current) => [...current, assistantMessage]);
    } catch (error) {
      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "error",
        content:
          error instanceof Error
            ? error.message
            : "Something went wrong while contacting Diasift.",
      };
      setMessages((current) => [...current, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }

  function startNewChat() {
    setMessages([]);
    setQuestion("");
  }

  return (
    <main className="appShell">
      <aside className="sidebar" aria-label="Diasift navigation">
        <div className="brand">
          <div className="brandMark">*</div>
          <div>
            <div className="brandName">DiaSift</div>
            <div className="brandSub">T2D Assistant</div>
          </div>
        </div>

        <button className="newChatButton" type="button" onClick={startNewChat}>
          <span>+</span>
          New Chat
        </button>

        <nav className="navList" aria-label="Primary navigation">
          <a className="navItem active" href="#chat">
            <span>...</span>
            Chat
          </a>
          <a className="navItem" href="#sources">
            <span>[]</span>
            Sources
          </a>
          <a className="navItem" href="#saved">
            <span>[]</span>
            Saved Answers
          </a>
          <a className="navItem" href="#about">
            <span>i</span>
            About
          </a>
        </nav>

        <div className="safetyNote">
          This tool provides general health information and does not replace advice
          from a healthcare professional.
        </div>

        <div className="prototypeLabel">MSc Prototype - 2026</div>
      </aside>

      <section className="workspace" id="chat" aria-label="Type 2 Diabetes chat">
        <header className="topBar">
          <div>
            <h1>Type 2 Diabetes Chat</h1>
            <p>RAG-powered - NICE, NHS, Diabetes UK</p>
          </div>
          <div className="headerActions">
            <div className={`healthPill ${healthError ? "offline" : ""}`}>
              <span />
              {healthStatus}
            </div>
            <div className="devicePill">[] Mobile</div>
          </div>
        </header>

        <div className="contentArea">
          <div className="conversationStrip">
            {latestUserQuestion ? (
              <article className="questionPanel">
                <span>Your question</span>
                <p>{latestUserQuestion}</p>
              </article>
            ) : null}

            {latestResult?.answer ? (
              <article className="answerPanel">
                <span>Diasift answer</span>
                <p>{latestResult.answer}</p>
              </article>
            ) : null}

            {latestError ? (
              <article className="errorPanel">
                <span>Connection issue</span>
                <p>{latestError}</p>
              </article>
            ) : null}
          </div>

          <div className="sourceList" id="sources">
            {displayedChunks.map((chunk, index) => {
              const cardTone =
                index === 0 ? evidenceTone : index === 1 ? "strong" : "moderate";

              return (
                <article
                  className="sourceCard"
                  key={`${chunk.source_file}-${chunk.chunk_index}-${index}`}
                >
                  <div className="sourceCardHeader">
                    <span className="sourceBadge">{getSourceLabel(chunk)}</span>
                    <span className={`strengthBadge ${cardTone}`}>
                      ...{" "}
                      {latestResult
                        ? formatEvidenceLabel(latestResult.evidence_label)
                        : index < 2
                          ? "Strong"
                          : "Moderate"}
                    </span>
                  </div>

                  <h2>{getCardTitle(chunk)}</h2>
                  <blockquote>{chunk.text}</blockquote>

                  <div className="cardLinks">
                    <button type="button" title={latestResult?.evidence_reason}>
                      Why this answer?
                    </button>
                    <button type="button">
                      View full source -&gt;
                    </button>
                  </div>
                </article>
              );
            })}

            {isLoading ? (
              <article className="sourceCard loadingCard">
                <div className="sourceCardHeader">
                  <span className="sourceBadge">Diasift</span>
                  <span className="strengthBadge moderate">... Searching</span>
                </div>
                <h2>Searching trusted guidance</h2>
                <blockquote>
                  Diasift is retrieving relevant passages and checking evidence strength.
                </blockquote>
              </article>
            ) : null}
            <div ref={contentEndRef} />
          </div>
        </div>

        <form className="composer" onSubmit={submitQuestion}>
          <div className="inputRow">
            <input
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask about Type 2 Diabetes guidance..."
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  submitQuestion();
                }
              }}
            />
            <button type="submit" disabled={isLoading || !question.trim()} aria-label="Send">
              &gt;
            </button>
          </div>

          <div className="composerMeta">
            <label>
              Provider
              <select
                value={provider}
                onChange={(event) => setProvider(event.target.value as Provider)}
              >
                <option value="gemini">Gemini</option>
                <option value="openai">OpenAI</option>
              </select>
            </label>
            <label>
              Max tokens
              <input
                type="number"
                min={100}
                max={2000}
                step={100}
                value={maxOutputTokens}
                onChange={(event) => setMaxOutputTokens(Number(event.target.value))}
              />
            </label>
            <label>
              <input
                type="checkbox"
                checked={callApi}
                onChange={(event) => setCallApi(event.target.checked)}
              />
              Call LLM
            </label>
            <span>
              General health information only - Always consult your GP or diabetes
              care team
            </span>
          </div>
        </form>
      </section>
    </main>
  );
}
