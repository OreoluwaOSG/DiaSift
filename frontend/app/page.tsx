import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="site">
      <SiteHeader />
      <Hero />
      <HowItWorks />
      <EvidenceLabels />
      <KnowledgeBase />
      <Guardrails />
      <FinalCta />
      <SiteFooter />
    </main>
  );
}

function SiteHeader() {
  return (
    <header className="siteHeader">
      <div className="siteHeaderInner">
        <span className="siteLogo">DiaSift</span>

        <nav className="siteNav" aria-label="Primary">
          <a href="#how-it-works">How it works</a>
          <a href="#sources">Sources</a>
          <a href="#safety">Safety</a>
        </nav>

        <Link href="/ask" className="btn btnPrimary btnSmall">
          Ask DiaSift
        </Link>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="hero">
      <div className="heroCopy">
        <span className="overline">Required first use &middot; Educational information only</span>

        <h1>
          Type 2 diabetes, explained.{" "}
          <span className="accentText">Every answer traced to its source.</span>
        </h1>

        <p>
          Search results mix clinical guidance with blogs, forums and ads. DiaSift
          answers your questions using only trusted guidance from the NHS, NICE
          and WHO &mdash; and shows the evidence behind every answer.
        </p>

        <div className="heroActions">
          <Link href="/ask" className="btn btnPrimary">
            Ask DiaSift
          </Link>
          <a href="#how-it-works" className="btn btnGhost">
            See how it works
          </a>
        </div>
      </div>

      <div className="heroDemo">
        <div className="demoCard">
          <div className="demoQuestion">
            <span className="demoQuestionMark">?</span>
            <p>What does HbA1c actually measure?</p>
          </div>

          <div className="demoEvidence">
            <span className="evidenceDot strong" />
            <span>Strong evidence</span>
          </div>

          <p className="demoAnswer">
            HbA1c reflects your average blood glucose over the past two to three
            months. It&apos;s measured because day-to-day readings move around,
            while HbA1c reveals the longer pattern &mdash; so clinicians can see
            how well your diabetes is being managed over time.
          </p>

          <div className="demoSources">
            <span>NHS &middot; Type 2 diabetes</span>
            <span>NICE &middot; NG28</span>
          </div>
        </div>

        <span className="demoCaption">A real DiaSift answer, with its evidence</span>
      </div>
    </section>
  );
}

function HowItWorks() {
  const steps = [
    {
      number: "01",
      title: "Ask",
      description: "Put your question in plain words — the way you'd ask a nurse, not a search engine.",
    },
    {
      number: "02",
      title: "Sift",
      description:
        "DiaSift searches a curated base of NHS, NICE and WHO guidance and keeps only the passages that genuinely answer you.",
    },
    {
      number: "03",
      title: "Answer",
      description: "You get a clear answer written from those passages, with named sources and an evidence label attached.",
    },
  ];

  return (
    <section className="section" id="how-it-works">
      <div className="sectionIntro">
        <span className="overline">How it works</span>
        <h2>Three points on a line.</h2>
        <p>
          DiaSift doesn&apos;t answer from an AI model&apos;s memory. It retrieves
          trusted guidance first, then writes the answer from what it found.
        </p>
      </div>

      <ol className="timeline">
        {steps.map((step) => (
          <li key={step.number} className="timelineStep">
            <span className="timelineDot" />
            <span className="timelineNumber">{step.number}</span>
            <h3>{step.title}</h3>
            <p>{step.description}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}

function EvidenceLabels() {
  const labels = [
    {
      tone: "strong",
      label: "Strong evidence",
      description:
        "Multiple trusted passages directly support the answer. DiaSift responds confidently and cites each source.",
    },
    {
      tone: "partial",
      label: "Partial evidence",
      description:
        "Related guidance was found, but it doesn't fully cover the question. DiaSift answers cautiously and tells you what's missing.",
    },
    {
      tone: "limited",
      label: "No clear evidence",
      description: (
        <>
          The sources don&apos;t support an answer &mdash; so DiaSift{" "}
          <strong>says so, instead of guessing.</strong>
        </>
      ),
    },
  ];

  return (
    <section className="section sectionAlt">
      <div className="sectionIntro">
        <span className="overline">Evidence labels</span>
        <h2>Every answer wears its confidence.</h2>
        <p>
          Before DiaSift answers, it weighs how well the retrieved guidance
          supports a response &mdash; and says so, plainly.
        </p>
      </div>

      <div className="evidenceLabelList">
        {labels.map((item) => (
          <div className="evidenceLabelRow" key={item.label}>
            <span className={`evidenceDot ${item.tone}`} />
            <span className="evidenceLabelName">{item.label}</span>
            <p>{item.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function KnowledgeBase() {
  const sources = [
    {
      name: "NHS",
      description: "Overview, treatment, complications and the Path to Remission Programme.",
    },
    {
      name: "NICE",
      description: "NG28 — the clinical guideline for type 2 diabetes in adults.",
    },
    {
      name: "WHO",
      description: "Global fact sheet on diabetes and its prevention.",
    },
    {
      name: "nidirect",
      description: "Northern Ireland's official health guidance on type 2 diabetes.",
    },
  ];

  return (
    <section className="section" id="sources">
      <div className="sectionIntro">
        <span className="overline">The knowledge base</span>
        <h2>Built on guidance, not the open web.</h2>
        <p>DiaSift only reads from a curated collection of recognised type 2 diabetes guidance.</p>
      </div>

      <div className="sourceGrid">
        {sources.map((source) => (
          <div className="sourceCard" key={source.name}>
            <h3>{source.name}</h3>
            <p>{source.description}</p>
          </div>
        ))}
      </div>

      <p className="sectionNote">
        When guidance changes, the collection is updated &mdash; no retraining,
        no stale answers baked into a model. Every stored passage keeps a record
        of where it came from.
      </p>
    </section>
  );
}

function Guardrails() {
  const rules = [
    {
      title: "No diagnosis",
      description:
        "DiaSift won't tell you whether you have diabetes, or interpret your symptoms. Those questions are redirected to your GP or nurse.",
    },
    {
      title: "No medication decisions",
      description:
        "It explains what treatments are and how they're generally used — never whether you should start, stop or change a dose.",
    },
    {
      title: "No personal data kept",
      description:
        "DiaSift asks for no personal details and stores nothing identifiable. Your questions are for answering, not collecting.",
    },
  ];

  return (
    <section className="section sectionAlt" id="safety">
      <div className="sectionIntro">
        <span className="overline">Guardrails, by design</span>
        <h2>What DiaSift won&apos;t do.</h2>
        <p>Refusing the wrong questions isn&apos;t a limitation of the system. It&apos;s the point.</p>
      </div>

      <div className="guardrailGrid">
        {rules.map((rule) => (
          <div className="guardrailCard" key={rule.title}>
            <span className="guardrailRule" />
            <h3>{rule.title}</h3>
            <p>{rule.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function FinalCta() {
  return (
    <section className="finalCta">
      <h2>Ask the internet less. Ask the guidance directly.</h2>
      <p>Free to use. No account, no personal details.</p>
      <Link href="/ask" className="btn btnPrimary">
        Ask DiaSift
      </Link>
    </section>
  );
}

function SiteFooter() {
  return (
    <footer className="siteFooter">
      <p className="disclaimer">
        DiaSift is an AI research prototype for educational use. It does not
        give medical diagnosis, treatment or personalised health advice, and it
        is not a substitute for your GP or pharmacist. If you&apos;re ever
        worried about your symptoms, contact your GP or NHS 111; in an
        emergency, call 999.
      </p>

      <div className="footerRow">
        <span className="footerBrand">DiaSift</span>
        <span className="footerLinks">
          <span>Privacy</span>
          <span>Terms</span>
          <span>About the research</span>
        </span>
        <span>&copy; 2026</span>
      </div>
    </footer>
  );
}
