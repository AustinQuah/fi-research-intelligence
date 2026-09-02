import React, {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Activity,
  ArrowUpRight,
  BookOpen,
  CheckCircle2,
  FileSearch,
  FileText,
  FlaskConical,
  Gauge,
  Loader2,
  Search,
  ShieldCheck,
  Upload,
} from "lucide-react";


const API =
  "https://fi-research-intelligence-2.onrender.com/api";


const NAVIGATION = [
  {
    id: "overview",
    label: "Overview",
    icon: Gauge,
  },
  {
    id: "document",
    label: "Document",
    icon: FileText,
  },
  {
    id: "research",
    label: "Research",
    icon: BookOpen,
  },
  {
    id: "review",
    label: "Review",
    icon: ShieldCheck,
  },
];


export default function App() {
  const [
    page,
    setPage,
  ] = useState("overview");

  const [
    documentId,
    setDocumentId,
  ] = useState(null);

  const [
    dossier,
    setDossier,
  ] = useState(null);

  const [
    research,
    setResearch,
  ] = useState({
    status: "not_started",
    queries: [],
    evidence: [],
  });

  const [
    uploadStatus,
    setUploadStatus,
  ] = useState("idle");

  const [
    message,
    setMessage,
  ] = useState("");

  const [
    researchStarted,
    setResearchStarted,
  ] = useState(false);


  async function apiRequest(
    url,
    options = {},
  ) {
    let response;

    try {
      response = await fetch(
        url,
        options,
      );
    } catch (error) {
      throw new Error(
        "Could not reach the research server. "
        + "The Render backend may be sleeping "
        + "or unavailable."
      );
    }

    let data = null;

    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (!response.ok) {
      const detail =
        data?.detail
        || `Server returned HTTP ${response.status}.`;

      throw new Error(detail);
    }

    return data;
  }


  async function uploadProposal(file) {
    if (!file) {
      return;
    }

    setUploadStatus(
      "uploading"
    );

    setMessage(
      "Uploading proposal..."
    );

    setDossier(null);

    setDocumentId(null);

    setResearch({
      status: "not_started",
      queries: [],
      evidence: [],
    });

    setResearchStarted(false);

    const form =
      new FormData();

    form.append(
      "file",
      file,
    );

    try {
      const result =
        await apiRequest(
          `${API}/proposals/upload`,
          {
            method: "POST",
            body: form,
          },
        );

      setDocumentId(
        result.id
      );

      setDossier(
        result.document
      );

      setUploadStatus(
        "ready"
      );

      setMessage(
        "Document analysed."
      );

      setPage(
        "document"
      );

    } catch (error) {
      setUploadStatus(
        "error"
      );

      setMessage(
        error.message
      );
    }
  }


  async function beginResearch() {
    if (
      !documentId
      || researchStarted
    ) {
      return;
    }

    setResearchStarted(
      true
    );

    setResearch({
      status: "running",
      queries: [],
      evidence: [],
    });

    try {
      await apiRequest(
        `${API}/proposals/${documentId}/research`,
        {
          method: "POST",
        },
      );

    } catch (error) {
      setResearchStarted(
        false
      );

      setResearch({
        status: "error",
        queries: [],
        evidence: [],
        error: error.message,
      });

      setMessage(
        error.message
      );
    }
  }


  useEffect(() => {
    if (
      dossier
      && documentId
      && !researchStarted
    ) {
      beginResearch();
    }
  }, [
    dossier,
    documentId,
    researchStarted,
  ]);


  useEffect(() => {
    if (
      !documentId
      || research.status !== "running"
    ) {
      return;
    }

    const timer =
      window.setInterval(
        async () => {
          try {
            const result =
              await apiRequest(
                `${API}/proposals/${documentId}/research`
              );

            setResearch(
              result
            );

            if (
              result.status
              === "complete"
            ) {
              setMessage(
                "Research complete."
              );
            }

          } catch (error) {
            setResearch({
              status: "error",
              queries: [],
              evidence: [],
              error: error.message,
            });

            setMessage(
              error.message
            );
          }
        },
        2000,
      );

    return () => {
      window.clearInterval(
        timer
      );
    };

  }, [
    documentId,
    research.status,
  ]);


  const title =
    dossier?.document?.title
    || "No proposal loaded";


  return (
    <div className="app">

      <aside className="sidebar">

        <div className="brand">

          <div className="brand-mark">
            <Activity size={18} />
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
          {NAVIGATION.map(
            item => {
              const Icon =
                item.icon;

              return (
                <button
                  key={item.id}
                  className={
                    page === item.id
                      ? "nav-item active"
                      : "nav-item"
                  }
                  onClick={() =>
                    setPage(
                      item.id
                    )
                  }
                >
                  <Icon size={17} />

                  <span>
                    {item.label}
                  </span>
                </button>
              );
            }
          )}
        </nav>


        <div className="server-status">
          <CheckCircle2
            size={14}
          />

          Render API
        </div>

      </aside>


      <main className="main">

        <header className="topbar">

          <div>
            <div className="eyebrow">
              RESEARCH WORKSPACE
            </div>

            <h1>
              {
                NAVIGATION.find(
                  item =>
                    item.id === page
                )?.label
              }
            </h1>
          </div>


          <div className="status-pill">

            {uploadStatus ===
              "uploading"
              ? (
                <>
                  <Loader2
                    size={13}
                    className="spin"
                  />
                  Processing
                </>
              )
              : (
                <>
                  <span
                    className="status-dot"
                  />
                  Ready
                </>
              )
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
            uploadStatus={
              uploadStatus
            }
            uploadProposal={
              uploadProposal
            }
            setPage={setPage}
          />
        )}


        {page === "document" && (
          <DocumentWorkspace
            dossier={dossier}
            setPage={setPage}
          />
        )}


        {page === "research" && (
          <ResearchWorkspace
            dossier={dossier}
            research={research}
          />
        )}


        {page === "review" && (
          <ReviewWorkspace
            title={title}
          />
        )}

      </main>

    </div>
  );
}


function Overview({
  dossier,
  research,
  uploadStatus,
  uploadProposal,
  setPage,
}) {
  return (
    <section className="workspace">

      <div className="hero">

        <div className="hero-copy">

          <span className="hero-label">
            PROPOSAL INTELLIGENCE
          </span>

          <h2>
            Read the proposal.
            <br />
            Investigate the evidence.
          </h2>

          <p>
            Upload a technical proposal.
            The workspace extracts its
            structure, claims, KPIs and
            research concepts, then starts
            looking for related evidence.
          </p>

        </div>


        <div className="hero-symbol">
          <FlaskConical
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
            dossier
              ?.document
              ?.pages
            ?? "—"
          }
        />

        <Stat
          label="Concepts"
          value={
            dossier
              ?.concepts
              ?.length
            ?? 0
          }
        />

        <Stat
          label="Research"
          value={
            research.status
          }
        />

      </div>


      <div className="section-heading">

        <div>
          <h3>
            Start with a proposal
          </h3>

          <p>
            PDF, DOCX, TXT or Markdown.
          </p>
        </div>

      </div>


      <label className="upload-zone">

        <div className="upload-icon">

          {uploadStatus ===
            "uploading"
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
              uploadStatus ===
                "uploading"
                ? "Reading proposal..."
                : "Choose a proposal"
            }
          </strong>

          <span>
            Native text extraction first.
            Sparse pages are flagged for
            visual processing.
          </span>

        </div>


        <span className="primary-button">
          Choose file
        </span>


        <input
          type="file"
          accept=".pdf,.docx,.txt,.md"
          disabled={
            uploadStatus ===
            "uploading"
          }
          onChange={
            event =>
              uploadProposal(
                event
                  .target
                  .files?.[0]
              )
          }
        />

      </label>


      {dossier && (
        <div className="document-summary">

          <div className="document-summary-main">

            <span className="eyebrow">
              CURRENT PROPOSAL
            </span>

            <h3>
              {
                dossier
                  .document
                  ?.title
              }
            </h3>

            <p>
              {
                dossier
                  .concepts
                  ?.slice(0, 6)
                  .join(" · ")
                || "No technical concepts detected."
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
                size={14}
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
                size={14}
              />
            </button>

          </div>

        </div>
      )}

    </section>
  );
}


function DocumentWorkspace({
  dossier,
  setPage,
}) {
  const [
    selectedPage,
    setSelectedPage,
  ] = useState(1);


  if (!dossier) {
    return (
      <EmptyState
        icon={FileText}
        title="No proposal loaded"
        text={
          "Upload a proposal from Overview first."
        }
      />
    );
  }


  if (
    dossier.status ===
    "needs_visual_processing"
  ) {
    return (
      <section className="workspace">

        <div className="warning-panel">

          <FileSearch
            size={24}
          />

          <div>
            <h3>
              Visual processing required
            </h3>

            <p>
              This document contains too
              little native text to analyse
              reliably. It is probably a
              scanned or image-based PDF.
            </p>
          </div>

        </div>

      </section>
    );
  }


  const pages =
    dossier.page_analysis
    || [];


  const currentPage =
    pages.find(
      page =>
        page.page ===
        selectedPage
    )
    || pages[0];


  return (
    <section className="workspace">

      <div className="document-header">

        <div>
          <span className="eyebrow">
            PROPOSAL
          </span>

          <h2>
            {
              dossier
                .document
                ?.title
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
            size={14}
          />
        </button>

      </div>


      <div className="document-layout">

        <aside className="page-list">

          <div className="pane-title">
            Pages
          </div>

          {pages.map(
            page => (
              <button
                key={page.page}
                className={
                  selectedPage ===
                    page.page
                    ? "page-button active"
                    : "page-button"
                }
                onClick={() =>
                  setSelectedPage(
                    page.page
                  )
                }
              >
                <span>
                  {page.page}
                </span>

                <small>
                  {
                    page.concepts
                      ?.length
                    || 0
                  } concepts
                </small>
              </button>
            )
          )}

        </aside>


        <div className="proposal-pane">

          <div className="pane-title">
            Page {
              currentPage?.page
            }
          </div>


          <div className="proposal-text">
            {
              currentPage
                ?.text_preview
              || "No native text extracted from this page."
            }
          </div>

        </div>


        <aside className="analysis-pane">

          <AnalysisSection
            title="Concepts"
            items={
              currentPage
                ?.concepts
              || []
            }
          />

          <AnalysisSection
            title="Claims"
            items={
              currentPage
                ?.claims
              || []
            }
          />

          <AnalysisSection
            title="KPIs"
            items={
              currentPage
                ?.kpis
              || []
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

      {!items.length && (
        <p className="muted">
          None detected.
        </p>
      )}

      {items.map(
        (item, index) => (
          <div
            className="analysis-item"
            key={index}
          >
            {item}
          </div>
        )
      )}

    </div>
  );
}


function ResearchWorkspace({
  dossier,
  research,
}) {
  const evidence =
    research.evidence
    || [];


  if (!dossier) {
    return (
      <EmptyState
        icon={BookOpen}
        title="No research context"
        text={
          "Upload a proposal first. Research will start automatically."
        }
      />
    );
  }


  return (
    <section className="workspace">

      <div className="research-header">

        <div>
          <span className="eyebrow">
            EVIDENCE
          </span>

          <h2>
            Research generated from
            the proposal
          </h2>

          <p>
            Queries come from the
            technical concepts and claims
            extracted from your document.
          </p>
        </div>


        <ResearchStatus
          status={
            research.status
          }
        />

      </div>


      {research.status ===
        "running" && (
        <div className="progress-panel">

          <Loader2
            className="spin"
            size={18}
          />

          <div>
            <strong>
              Searching literature
            </strong>

            <span>
              The proposal remains usable
              while research runs.
            </span>
          </div>

        </div>
      )}


      {research.status ===
        "error" && (
        <div className="warning-panel">

          <FileSearch
            size={20}
          />

          <div>
            <strong>
              Research provider error
            </strong>

            <p>
              {
                research.error
                || "Research failed."
              }
            </p>
          </div>

        </div>
      )}


      {research.status ===
        "complete"
        && evidence.length === 0
        && (
          <div className="empty-inline">
            No relevant evidence was
            returned.
          </div>
        )
      }


      <div className="evidence-list">

        {evidence.map(
          (
            group,
            groupIndex
          ) => (
            <EvidenceGroup
              key={
                groupIndex
              }
              group={group}
            />
          )
        )}

      </div>

    </section>
  );
}


function EvidenceGroup({
  group,
}) {
  const [
    open,
    setOpen,
  ] = useState(true);


  return (
    <article className="evidence-group">

      <button
        className="evidence-heading"
        onClick={() =>
          setOpen(
            current =>
              !current
          )
        }
      >

        <div>
          <span className="eyebrow">
            SEARCH QUERY
          </span>

          <strong>
            {group.query}
          </strong>
        </div>

        <span>
          {
            group.papers
              ?.length
            || 0
          } results
        </span>

      </button>


      {open && (
        <div className="evidence-body">

          <div className="source-links">

            <ExternalSource
              label="Google Scholar"
              href={
                group.links
                  ?.google_scholar
              }
            />

            <ExternalSource
              label="Google Patents"
              href={
                group.links
                  ?.google_patents
              }
            />

            <ExternalSource
              label="Semantic Scholar"
              href={
                group.links
                  ?.semantic_scholar
              }
            />

            <ExternalSource
              label="WIPO"
              href={
                group.links
                  ?.wipo
              }
            />

          </div>


          {(
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
                    {
                      paper.source
                    }
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
                  {
                    paper.title
                  }
                </strong>


                <ArrowUpRight
                  size={15}
                />

              </a>
            )
          )}

        </div>
      )}

    </article>
  );
}


function ExternalSource({
  label,
  href,
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
        size={12}
      />
    </a>
  );
}


function ResearchStatus({
  status,
}) {
  return (
    <div
      className={
        `research-status ${status}`
      }
    >
      {status === "running" && (
        <Loader2
          size={13}
          className="spin"
        />
      )}

      {status}
    </div>
  );
}


function ReviewWorkspace({
  title,
}) {
  const criteria = [
    "Science & technology",
    "Impact / national benefit",
    "Management & delivery",
    "Budget / value",
  ];


  const initial =
    Object.fromEntries(
      criteria.map(
        criterion => [
          criterion,
          3,
        ]
      )
    );


  const [
    scores,
    setScores,
  ] = useState(
    initial
  );


  const average =
    useMemo(
      () => {
        const values =
          Object.values(
            scores
          );

        return (
          values.reduce(
            (
              sum,
              value
            ) =>
              sum
              + Number(value),
            0,
          )
          / values.length
        );
      },
      [scores],
    );


  return (
    <section className="workspace">

      <div className="review-header">

        <span className="eyebrow">
          HUMAN REVIEW
        </span>

        <h2>
          {title}
        </h2>

        <p>
          Decision-support workspace.
          Final assessment remains with
          the human reviewer.
        </p>

      </div>


      <div className="review-grid">

        {criteria.map(
          criterion => (
            <div
              className="review-item"
              key={criterion}
            >

              <div>
                <strong>
                  {criterion}
                </strong>

                <span>
                  {
                    scores[
                      criterion
                    ]
                  } / 5
                </span>
              </div>


              <input
                type="range"
                min="1"
                max="5"
                step="1"
                value={
                  scores[
                    criterion
                  ]
                }
                onChange={
                  event =>
                    setScores({
                      ...scores,
                      [criterion]:
                        Number(
                          event
                            .target
                            .value
                        ),
                    })
                }
              />

            </div>
          )
        )}

      </div>


      <div className="overall-score">

        <span>
          Preliminary score
        </span>

        <strong>
          {
            average.toFixed(
              2
            )
          }
          <small>
            / 5
          </small>
        </strong>

      </div>

    </section>
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


function EmptyState({
  icon: Icon,
  title,
  text,
}) {
  return (
    <section className="workspace">

      <div className="empty-state">

        <Icon size={28} />

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
