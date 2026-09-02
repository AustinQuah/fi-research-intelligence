import React, {
  useEffect,
  useState
} from "react";

import {
  Activity,
  ArrowUpRight,
  BookOpen,
  CheckCircle2,
  ChevronRight,
  FileText,
  Gauge,
  Loader2,
  Search,
  ShieldCheck,
  Upload,
} from "lucide-react";


const API =
  "https://fi-research-intelligence-2.onrender.com/api";


const NAV = [
  [
    "overview",
    "Overview",
    Gauge
  ],
  [
    "document",
    "Document",
    FileText
  ],
  [
    "research",
    "Research & IP",
    BookOpen
  ],
  [
    "novelty",
    "Novelty",
    ShieldCheck
  ],
];


export default function App() {
  const [
    page,
    setPage
  ] = useState(
    "overview"
  );

  const [
    documentId,
    setDocumentId
  ] = useState(
    null
  );

  const [
    dossier,
    setDossier
  ] = useState(
    null
  );

  const [
    research,
    setResearch
  ] = useState({
    status: "not_started",
    queries: [],
    evidence: [],
  });

  const [
    novelty,
    setNovelty
  ] = useState(
    null
  );

  const [
    busy,
    setBusy
  ] = useState(
    false
  );

  const [
    message,
    setMessage
  ] = useState(
    ""
  );


  async function request(
    url,
    options = {},
  ) {
    let response;

    try {
      response = await fetch(
        url,
        options
      );

    } catch {
      throw new Error(
        "Could not reach the Render research server."
      );
    }

    let data = null;

    try {
      data = await response.json();

    } catch {
      data = null;
    }

    if (!response.ok) {
      throw new Error(
        data?.detail
        || `Server returned HTTP ${response.status}.`
      );
    }

    return data;
  }


  async function uploadProposal(
    file
  ) {
    if (!file) {
      return;
    }

    setBusy(true);

    setMessage(
      "Uploading proposal..."
    );

    setDossier(null);

    setNovelty(null);

    setResearch({
      status: "not_started",
      queries: [],
      evidence: [],
    });

    const body =
      new FormData();

    body.append(
      "file",
      file
    );

    try {
      const result =
        await request(
          `${API}/proposals/upload`,
          {
            method: "POST",
            body,
          }
        );

      setDocumentId(
        result.id
      );

      setDossier(
        result.document
      );

      setMessage(
        "Proposal received. Research is running in the background."
      );

      setPage(
        "document"
      );

    } catch (error) {
      setMessage(
        error.message
      );

    } finally {
      setBusy(false);
    }
  }


  useEffect(() => {
    if (!documentId) {
      return;
    }

    let cancelled = false;

    const poll = async () => {
      try {
        const result =
          await request(
            `${API}/proposals/${documentId}`
          );

        if (cancelled) {
          return;
        }

        setDossier(
          result.dossier
        );

        setResearch(
          result.research
        );

        setNovelty(
          result.novelty
        );

        if (
          result.research?.status
          === "running"
        ) {
          setTimeout(
            poll,
            2000
          );
        }

      } catch (error) {
        if (!cancelled) {
          setMessage(
            error.message
          );
        }
      }
    };

    poll();

    return () => {
      cancelled = true;
    };

  }, [
    documentId
  ]);


  return (
    <div className="app">

      <aside className="sidebar">

        <div className="brand">

          <div className="brand-mark">
            <Activity
              size={18}
            />
          </div>

          <div>
            <strong>
              FI Research
            </strong>

            <span>
              Intelligence
            </span>
          </div>

        </div>


        <nav>

          {NAV.map(
            (
              [
                id,
                label,
                Icon
              ]
            ) => (
              <button
                key={id}
                className={
                  page === id
                    ? "nav active"
                    : "nav"
                }
                onClick={() =>
                  setPage(id)
                }
              >
                <Icon
                  size={16}
                />

                <span>
                  {label}
                </span>

                {page === id && (
                  <ChevronRight
                    size={13}
                    className="nav-arrow"
                  />
                )}

              </button>
            )
          )}

        </nav>


        <div className="server-status">

          <CheckCircle2
            size={14}
          />

          Backend connected

        </div>

      </aside>


      <main>

        <header className="topbar">

          <div>

            <div className="eyebrow">
              RESEARCH WORKSPACE
            </div>

            <h1>
              {
                NAV.find(
                  ([id]) =>
                    id === page
                )?.[1]
              }
            </h1>

          </div>


          <div className="status-pill">

            <span className="status-dot" />

            {
              busy
                ? "Working"
                : research.status === "running"
                  ? "Researching"
                  : "Ready"
            }

          </div>

        </header>


        {message && (
          <div className="toast">

            <span>
              {message}
            </span>

            <button
              onClick={() =>
                setMessage("")
              }
            >
              ×
            </button>

          </div>
        )}


        {page === "overview" && (
          <Overview
            dossier={dossier}
            research={research}
            novelty={novelty}
            busy={busy}
            uploadProposal={
              uploadProposal
            }
            setPage={setPage}
          />
        )}


        {page === "document" && (
          <DocumentPage
            dossier={dossier}
            setPage={setPage}
          />
        )}


        {page === "research" && (
          <ResearchPage
            dossier={dossier}
            research={research}
          />
        )}


        {page === "novelty" && (
          <NoveltyPage
            novelty={novelty}
            dossier={dossier}
            research={research}
          />
        )}

      </main>

    </div>
  );
}


function Overview({
  dossier,
  research,
  novelty,
  busy,
  uploadProposal,
  setPage,
}) {
  return (
    <section className="workspace">

      <div className="hero">

        <div>

          <div className="hero-label">
            PROPOSAL INTELLIGENCE
          </div>

          <h2>
            Read the proposal.
            <br />
            Investigate what already exists.
          </h2>

          <p>
            Upload one proposal and let
            the system extract its structure,
            concepts, claims and KPIs,
            then build a research evidence set.
          </p>

        </div>


        <div className="hero-symbol">

          <ShieldCheck
            size={34}
          />

        </div>

      </div>


      <div className="stats">

        <Stat
          label="Document"
          value={
            dossier
              ? "Loaded"
              : "None"
          }
        />

        <Stat
          label="Pages"
          value={
            dossier?.document?.pages
            ?? "—"
          }
        />

        <Stat
          label="Concepts"
          value={
            dossier?.concepts?.length
            ?? 0
          }
        />

        <Stat
          label="Novelty"
          value={
            novelty?.score != null
              ? `${novelty.score}/100`
              : "Pending"
          }
        />

      </div>


      <div className="section-heading">

        <div>

          <h3>
            Start a research workspace
          </h3>

          <p>
            PDF, DOCX, TXT or Markdown.
          </p>

        </div>

      </div>


      <label className="upload-zone">

        <div className="upload-icon">

          {busy
            ? (
              <Loader2
                size={21}
                className="spin"
              />
            )
            : (
              <Upload
                size={21}
              />
            )
          }

        </div>


        <div className="upload-copy">

          <strong>
            {
              busy
                ? "Reading proposal..."
                : "Choose a proposal"
            }
          </strong>

          <span>
            Document analysis starts immediately.
          </span>

        </div>


        <span className="primary-button">
          Choose file
        </span>


        <input
          type="file"
          accept=".pdf,.docx,.txt,.md"
          disabled={busy}
          onChange={
            (event) =>
              uploadProposal(
                event.target.files?.[0]
              )
          }
        />

      </label>


      {dossier && (
        <div className="document-summary">

          <div>

            <div className="eyebrow">
              CURRENT PROPOSAL
            </div>

            <h3>
              {
                dossier.document?.title
              }
            </h3>

            <p>
              {
                (
                  dossier.concepts
                  || []
                )
                .slice(
                  0,
                  7
                )
                .join(" · ")
                || "No concepts detected."
              }
            </p>

          </div>


          <div className="summary-actions">

            <button
              onClick={() =>
                setPage(
                  "document"
                )
              }
            >
              Document
              <ArrowUpRight
                size={13}
              />
            </button>

            <button
              onClick={() =>
                setPage(
                  "research"
                )
              }
            >
              Research
              <Search
                size={13}
              />
            </button>

            <button
              onClick={() =>
                setPage(
                  "novelty"
                )
              }
            >
              Novelty
              <ShieldCheck
                size={13}
              />
            </button>

          </div>

        </div>
      )}


      {
        dossier
        && research.status === "running"
        && (
          <div className="progress-panel">

            <Loader2
              size={17}
              className="spin"
            />

            <div>

              <strong>
                Research is running in the background
              </strong>

              <span>
                Keep exploring the proposal
                while evidence is collected.
              </span>

            </div>

          </div>
        )
      }

    </section>
  );
}


function DocumentPage({
  dossier,
  setPage,
}) {
  if (!dossier) {
    return (
      <Empty
        title="No proposal loaded"
        text="Upload a proposal from Overview."
      />
    );
  }

  if (
    dossier.status
    === "needs_visual_processing"
  ) {
    return (
      <section className="workspace">

        <div className="warning-panel">

          <FileText
            size={22}
          />

          <div>

            <strong>
              This document needs visual processing.
            </strong>

            <p>
              No usable native text layer was found.
              The MVP flags scanned PDFs rather
              than pretending they were read.
            </p>

          </div>

        </div>

      </section>
    );
  }


  return (
    <section className="workspace">

      <div className="document-header">

        <div>

          <div className="eyebrow">
            DOCUMENT
          </div>

          <h2>
            {
              dossier.document?.title
            }
          </h2>

        </div>


        <button
          className="research-button"
          onClick={() =>
            setPage(
              "research"
            )
          }
        >
          Investigate evidence
          <ArrowUpRight
            size={13}
          />
        </button>

      </div>


      <div className="document-layout">

        <div className="proposal-pane">

          <div className="pane-title">
            Extracted proposal
          </div>

          {
            (
              dossier.page_analysis
              || []
            ).map(
              (page) => (
                <article
                  className="page-block"
                  key={page.page}
                >

                  <div className="page-number">
                    PAGE {page.page}
                  </div>

                  <p>
                    {
                      page.text_preview
                      || "No text extracted."
                    }
                  </p>

                </article>
              )
            )
          }

        </div>


        <aside className="analysis-pane">

          <AnalysisSection
            title="Concepts"
            items={
              dossier.concepts
              || []
            }
          />

          <AnalysisSection
            title="Claims"
            items={
              (
                dossier.claims
                || []
              ).map(
                item =>
                  `p.${item.page}: ${item.text}`
              )
            }
          />

          <AnalysisSection
            title="KPIs"
            items={
              (
                dossier.kpis
                || []
              ).map(
                item =>
                  `p.${item.page}: ${item.text}`
              )
            }
          />

        </aside>

      </div>

    </section>
  );
}


function AnalysisSection({
  title,
  items,
}) {
  return (
    <div className="analysis-section">

      <div className="pane-title">
        {title}
      </div>

      {
        items.length
          ? items
            .slice(
              0,
              12
            )
            .map(
              (
                item,
                index
              ) => (
                <div
                  className="analysis-item"
                  key={index}
                >
                  {item}
                </div>
              )
            )
          : (
            <div className="muted">
              None detected.
            </div>
          )
      }

    </div>
  );
}


function ResearchPage({
  dossier,
  research,
}) {
  if (!dossier) {
    return (
      <Empty
        title="No research context"
        text="Upload a proposal first."
      />
    );
  }

  return (
    <section className="workspace">

      <div className="research-header">

        <div>

          <div className="eyebrow">
            EVIDENCE
          </div>

          <h2>
            Research generated from the proposal
          </h2>

          <p>
            Queries are created from
            extracted concepts and claims.
          </p>

        </div>


        <div
          className={
            `research-status ${research.status}`
          }
        >
          {research.status}
        </div>

      </div>


      <div className="evidence-list">

        {
          (
            research.evidence
            || []
          ).map(
            (
              group,
              index
            ) => (
              <EvidenceGroup
                key={index}
                group={group}
              />
            )
          )
        }


        {
          !research.evidence?.length
          && (
            <div className="empty-inline">
              Research results will appear
              here while the background
              pass runs.
            </div>
          )
        }

      </div>

    </section>
  );
}


function EvidenceGroup({
  group,
}) {
  return (
    <article className="evidence-group">

      <div className="evidence-heading">

        <div>

          <div className="eyebrow">
            SEARCH QUERY
          </div>

          <strong>
            {group.query}
          </strong>

        </div>


        <span>
          {
            group.papers?.length
            || 0
          } results
        </span>

      </div>


      <div className="evidence-body">

        <div className="source-links">

          <ExternalLink
            href={
              group.links?.google_scholar
            }
            label="Google Scholar"
          />

          <ExternalLink
            href={
              group.links?.google_patents
            }
            label="Google Patents"
          />

          <ExternalLink
            href={
              group.links?.semantic_scholar
            }
            label="Semantic Scholar"
          />

          <ExternalLink
            href={
              group.links?.wipo
            }
            label="WIPO"
          />

        </div>


        {
          (
            group.papers
            || []
          ).map(
            (
              paper,
              index
            ) => (
              <a
                className="paper"
                href={
                  paper.url
                  || "#"
                }
                target="_blank"
                rel="noreferrer"
                key={index}
              >

                <div className="paper-meta">

                  <span>
                    {paper.source}
                  </span>

                  <span>
                    {
                      paper.year
                      || "—"
                    }
                  </span>

                  <span>
                    {
                      paper.citations
                      || 0
                    } citations
                  </span>

                </div>


                <strong>
                  {paper.title}
                </strong>

                <ArrowUpRight
                  size={14}
                />

              </a>
            )
          )
        }

      </div>

    </article>
  );
}


function ExternalLink({
  href,
  label,
}) {
  if (!href) {
    return null;
  }

  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
    >
      {label}

      <ArrowUpRight
        size={11}
      />
    </a>
  );
}


function NoveltyPage({
  novelty,
  dossier,
}) {
  if (!dossier) {
    return (
      <Empty
        title="No novelty assessment"
        text="Upload a proposal first."
      />
    );
  }

  if (!novelty) {
    return (
      <section className="workspace">

        <div className="progress-panel">

          <Loader2
            size={17}
            className="spin"
          />

          <div>

            <strong>
              Novelty score is being calculated.
            </strong>

            <span>
              It appears after the
              research pass completes.
            </span>

          </div>

        </div>

      </section>
    );
  }


  const components =
    novelty.components
    || {};


  return (
    <section className="workspace">

      <div className="research-header">

        <div>

          <div className="eyebrow">
            EVIDENCE-BASED SCREENING
          </div>

          <h2>
            Novelty assessment
          </h2>

          <p>
            This is a decision-support signal,
            not a funding recommendation.
          </p>

        </div>

      </div>


      <div className="novelty-hero">

        <div>

          <div className="eyebrow">
            NOVELTY SCORE
          </div>

          <div className="big-score">

            {novelty.score}

            <small>
              /100
            </small>

          </div>

          <span className="classification">
            {novelty.classification} novelty
          </span>

        </div>


        <div className="confidence">

          <span>
            CONFIDENCE
          </span>

          <strong>

            {novelty.confidence}

            <small>
              /100
            </small>

          </strong>


          <div className="score-bar">

            <span
              style={{
                width:
                  `${novelty.confidence}%`
              }}
            />

          </div>

        </div>

      </div>


      <div className="component-grid">

        <NoveltyComponent
          label="Prior-art distance"
          item={
            components.prior_art_distance
          }
        />

        <NoveltyComponent
          label="Patent distance"
          item={
            components.patent_distance
          }
        />

        <NoveltyComponent
          label="Concept novelty"
          item={
            components.concept_novelty
          }
        />

        <NoveltyComponent
          label="Claim novelty"
          item={
            components.claim_novelty
          }
        />

        <NoveltyComponent
          label="Evidence confidence"
          item={
            components.evidence_confidence
          }
        />

      </div>


      <div className="panel">

        <div className="panel-head">

          <div>

            <h3>
              Closest retrieved prior work
            </h3>

            <p>
              {
                novelty.evidence?.query_count
                || 0
              } queries · {
                novelty.evidence?.paper_count
                || 0
              } records
            </p>

          </div>

        </div>


        {
          (
            novelty.evidence
              ?.closest_prior_work
            || []
          ).map(
            (
              item,
              index
            ) => (
              <a
                className="prior-work"
                href={
                  item.url
                  || "#"
                }
                target="_blank"
                rel="noreferrer"
                key={index}
              >

                <div>

                  <strong>
                    {item.title}
                  </strong>

                  <span>
                    {item.source}
                    {" · "}
                    {
                      item.year
                      || "—"
                    }
                  </span>

                </div>


                <b>
                  {item.similarity}% similarity
                </b>

              </a>
            )
          )
        }

      </div>


      <div className="methodology">

        <strong>
          How the number works
        </strong>

        <p>
          {novelty.methodology}
        </p>

      </div>

    </section>
  );
}


function NoveltyComponent({
  label,
  item,
}) {
  return (
    <div className="novelty-component">

      <div>

        <span>
          {label}
        </span>

        <strong>
          {
            item?.measured
              ? `${item.score}/100`
              : "Not measured"
          }
        </strong>

      </div>


      <div className="component-bar">

        <span
          style={{
            width:
              item?.measured
                ? `${item.score}%`
                : "0%"
          }}
        />

      </div>


      <p>
        {
          item?.description
          || "Not measured in this MVP."
        }
      </p>

    </div>
  );
}


function Stat({
  label,
  value,
}) {
  return (
    <div className="stat">

      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>

    </div>
  );
}


function Empty({
  title,
  text,
}) {
  return (
    <section className="workspace">

      <div className="empty-state">

        <FileText
          size={27}
        />

        <h3>
          {title}
        </h3>

        <p>
          {text}
        </p>

      </div>

    </section>
  );
}
