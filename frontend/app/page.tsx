"use client";

import type { FormEvent, ReactNode } from "react";
import { useEffect, useRef, useState } from "react";

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

function getEvidenceClass(label: string) {
  const normalizedLabel = label.toLowerCase();

  if (normalizedLabel.includes("strong")) {
    return "strong";
  }

  if (normalizedLabel.includes("partial")) {
    return "partial";
  }

  return "limited";
}

export default function Home() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
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

  async function submitQuestion(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();

    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isLoading) {
      return;
    }

    setMessages((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        role: "user",
        content: trimmedQuestion,
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
          call_api: false,
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
            "I found relevant guidance passages for this question. Review the evidence cards below.",
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
        },
      ]);
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
      <aside
        className={`sideRail ${isSidebarCollapsed ? "collapsed" : ""}`}
        aria-label="Diasift navigation"
      >
        <div className="brandBlock">
          <div className="logoMark">
            <Icon name="spark" />
          </div>
          <div className="brandText">
            <span>DiaSift</span>
            <small>Type 2 DiabetesAssistant</small>
          </div>

         
        </div>

        <button className="newChatButton" type="button" onClick={startNewChat}>
          <Icon name="plus" />
          <span className="navLabel">New Chat</span>
        </button>

        <nav className="sidebarNav" aria-label="Primary navigation">
          <NavButton icon="chat" label="Chat" active />
          <NavButton icon="book" label="Sources" />
          <NavButton icon="bookmark" label="Saved Answers" />
          <NavButton icon="info" label="About" />
        </nav>
  <button
            className="collapseButton"
            type="button"
            aria-label={isSidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            onClick={() => setIsSidebarCollapsed((current) => !current)}
          >
            <Icon name={isSidebarCollapsed ? "expand" : "collapse"} />
          </button>
        <div className="railSpacer" />
       
        {/* <div className="safetyNote">
          <span className="navLabel">
            General health information only. Always consult your GP or diabetes
            care team.
          </span>
        </div> */}
      </aside>

      <section className={`chatCanvas ${hasMessages ? "hasMessages" : ""}`}>
        <header className="topStatus">
          {/* <span className={healthError ? "statusDot warning" : "statusDot"} /> */}
          <span>{healthError ?? health?.status ?? "Checking knowledge base"}</span>
          {health?.indexed_chunks ? <strong>{health.indexed_chunks} chunks</strong> : null}
        </header>

        {!hasMessages ? (
          <section className="homeStage" aria-label="Start chat">
            <div className="orb" />
            <h1>Good day, Oreoluwa</h1>
            <p>Ask a Type 2 Diabetes guidance question.</p>
            <PromptBox
              question={question}
              isLoading={isLoading}
              onQuestionChange={setQuestion}
              onSubmit={submitQuestion}
            />
          </section>
        ) : (
          <>
            <section className="transcript" aria-live="polite">
              {messages.map((message) => (
                <article key={message.id} className={`chatMessage ${message.role}`}>
                  <span>{message.role === "user" ? "You" : "Diasift"}</span>
                  <p>{message.content}</p>

                  {message.role === "assistant" ? (
                    <>
                      <div className="answerMeta">
                        <span className={getEvidenceClass(message.result.evidence_label)}>
                          {message.result.evidence_label}
                        </span>
                        <span>{message.result.api_called ? "LLM answer" : "Retrieved evidence"}</span>
                        <span>{message.result.model}</span>
                      </div>

                      {message.result.retrieved_chunks.length ? (
                        <section className="evidenceGrid" aria-label="Retrieved evidence">
                          {message.result.retrieved_chunks.slice(0, 4).map((chunk, index) => (
                            <article
                              className="evidenceCard"
                              key={`${chunk.source_file}-${chunk.chunk_index}-${index}`}
                            >
                              <div className="evidenceTopline">
                                <span>{chunk.source}</span>
                                <strong>{message.result.evidence_label}</strong>
                              </div>
                              <h2>{getSourceTitle(chunk)}</h2>
                              <p>{chunk.text}</p>
                            </article>
                          ))}
                        </section>
                      ) : null}
                    </>
                  ) : null}
                </article>
              ))}

              {isLoading ? (
                <article className="chatMessage assistant">
                  <span>Diasift</span>
                  <p>Searching trusted guidance...</p>
                </article>
              ) : null}

              <div ref={transcriptEndRef} />
            </section>

            <div className="floatingPrompt">
              <PromptBox
                question={question}
                isLoading={isLoading}
                onQuestionChange={setQuestion}
                onSubmit={submitQuestion}
                compact
              />
            </div>
          </>
        )}
      </section>
    </main>
  );
}

function NavButton({
  icon,
  label,
  active = false,
}: {
  icon: IconName;
  label: string;
  active?: boolean;
}) {
  return (
    <button
      className={`navButton ${active ? "active" : ""}`}
      type="button"
      aria-current={active ? "page" : undefined}
      title={label}
    >
      <Icon name={icon} />
      <span className="navLabel">{label}</span>
    </button>
  );
}

function PromptBox({
  question,
  isLoading,
  compact = false,
  onQuestionChange,
  onSubmit,
}: {
  question: string;
  isLoading: boolean;
  compact?: boolean;
  onQuestionChange: (question: string) => void;
  onSubmit: (event?: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form className={`promptBox ${compact ? "compact" : ""}`} onSubmit={onSubmit}>
      {/* <button className="promptAction" type="button" aria-label="Add context">
        <Icon name="plus" />
      </button> */}
      <input
        value={question}
        onChange={(event) => onQuestionChange(event.target.value)}
        placeholder="Ask anything"
        maxLength={1000}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            onSubmit();
          }
        }}
      />

      <div className="promptFooter">
        {/* <span className="qualityDot" />
        <span className="promptMode">Guidance</span> */}
        <span className="promptCount">{question.length}/1000</span>
        <button className="sendButton" type="submit" disabled={isLoading || !question.trim()} aria-label="Send">
          {isLoading ? "..." : <Icon name="send" />}
        </button>
      </div>
    </form>
  );
}

type IconName =
  | "spark"
  | "plus"
  | "chat"
  | "book"
  | "bookmark"
  | "info"
  | "collapse"
  | "expand"
  | "send";

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
    chat: (
      <>
        <path d="M5 6.5h14v9H9l-4 3v-12Z" />
        <path d="M9 11h.1" />
        <path d="M12 11h.1" />
        <path d="M15 11h.1" />
      </>
    ),
    book: (
      <>
        <path d="M4 5.5c2.8-1.1 5.3-.8 8 1v13c-2.7-1.8-5.2-2.1-8-1v-13Z" />
        <path d="M20 5.5c-2.8-1.1-5.3-.8-8 1v13c2.7-1.8 5.2-2.1 8-1v-13Z" />
      </>
    ),
    bookmark: <path d="M7 4.5h10v15l-5-3-5 3v-15Z" />,
    info: (
      <>
        <circle cx="12" cy="12" r="8" />
        <path d="M12 11v5" />
        <path d="M12 8h.1" />
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
    send: (
      <>
        <path d="M5 12h12" />
        <path d="m13 6 6 6-6 6" />
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
