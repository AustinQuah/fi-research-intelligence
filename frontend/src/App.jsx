import React, {
  useEffect,
  useState
} from "react";

import {
  Activity,
  ArrowUpRight,
  BarChart3,
  BookOpen,
  CheckCircle2,
  ChevronRight,
  FileText,
  Gauge,
  Loader2,
  Search,
  ShieldCheck,
  Upload
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
    "Research",
    BookOpen
  ],
  [
    "patents",
    "Patents",
    ShieldCheck
  ],
  [
    "assessment",
    "Assessment",
    BarChart3
  ]
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
    () =>
      localStorage.getItem(
        "fi_document_id"
      )
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
    status:
      "not_started",
    queries: [],
    evidence: []
  });


  const [
    patents,
    setPatents
  ] = useState(
    null
  );


  const [
    assessment,
    setAssessment
  ] = useState(
    null
  );


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


  async function api(
    url,
    options = {}
  ) {

    let response;

    try {

      response =
        await fetch(
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

      data =
        await response.json();

    } catch {

      data = null;

    }


    if (!response.ok) {

      throw new Error(
        data?.detail
        ||
        `Server returned HTTP ${response.status}.`
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


    setBusy(
      true
    );

    setMessage(
      "Uploading and reading proposal..."
    );


    setDossier(
      null
    );

    setPatents(
      null
    );

    setResearch({
      status:
        "not_started",
      queries: [],
      evidence: []
    });

    setAssessment(
      null
    );

    setNovelty(
      null
    );


    const form =
      new FormData();


    form.append(
      "file",
      file
    );


    try {

      const result =
        await api(
          `${API}/proposals/upload`,
          {
            method:
              "POST",
            body:
              form
          }
        );


      localStorage.setItem(
        "fi_document_id",
        result.id
      );


      setDocumentId(
        result.id
      );


      setDossier(
        result.document
      );


      setMessage(
        "Proposal loaded. Research and patent-search analysis are running."
      );


      setPage(
        "document"
      );


    } catch (
      error
    ) {

      setMessage(
        error.message
      );

    } finally {

      setBusy(
        false
      );

    }

  }


  useEffect(
    () => {

      if (!documentId) {
        return;
      }


      let stopped = false;

      let timer = null;


      async function poll() {

        try {

          const result =
            await api(
              `${API}/proposals/${documentId}`
            );


          if (stopped) {
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

          setAssessment(
            result.assessment
          );

          setPatents(
            result.patents
          );


          if (
            result.status
            === "error"
          ) {

            setMessage(
              result.error
              ||
              "Document processing failed."
            );

            return;

          }


          if (
            result.research?.status
            === "running"
          ) {

            timer =
              window.setTimeout(
                poll,
                2000
              );

          }

        } catch (
          error
        ) {

          if (
            error.message
              .toLowerCase()
              .includes(
                "document not found"
              )
          ) {

            localStorage.removeItem(
              "fi_document_id"
            );

            setDocumentId(
              null
            );

            setDossier(
              null
            );

            setPatents(
              null
            );

            setResearch({
              status:
                "not_started",
              queries: [],
              evidence: []
            });

            setAssessment(
              null
            );

            setNovelty(
              null
            );

            setMessage(
              "The previous proposal expired because Render restarted. Please upload it again."
            );

            return;

          }


          if (!stopped) {

            setMessage(
              error.message
            );

          }

        }

      }


      poll();


      return () => {

        stopped = true;

        if (timer) {

          window.clearTimeout(
            timer
          );

        }

      };

    },
    [
      documentId
    ]
  );


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

                key={
                  id
                }

                className={
                  page === id
                    ? "nav active"
                    : "nav"
                }

                onClick={
                  () =>
                    setPage(
                      id
                    )
                }

              >

                <Icon
                  size={16}
                />

                <span>
                  {label}
                </span>


                {
                  page === id
                  && (
                    <ChevronRight
                      size={13}
                      className="nav-arrow"
                    />
                  )
                }

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
                  item =>
                    item[0]
                    ===
                    page
                )?.[1]
              }

            </h1>

          </div>


          <div className="status-pill">

            <span
              className="status-dot"
            />

            {
              busy
                ? "Processing"
                : research.status
                  === "running"
                  ? "Researching"
                  : "Ready"
            }

          </div>

        </header>


        {
          message
          && (

            <div className="toast">

              <span>
                {
                  message
                }
              </span>


              <button
                onClick={() =>
                  setMessage("")
                }
              >
                ×
              </button>

            </div>

          )
        }


        {
          page
          === "overview"
          && (

            <Overview
              dossier={
                dossier
              }

              assessment={
                assessment
              }

              patents={
                patents
              }

              busy={
                busy
              }

              uploadProposal={
                uploadProposal
              }

              setPage={
                setPage
              }

            />

          )
        }


        {
          page
          === "document"
          && (

            <DocumentPage
              dossier={
                dossier
              }

              setPage={
                setPage
              }

            />

          )
        }


        {
          page
          === "research"
          && (

            <ResearchPage
              dossier={
                dossier
              }

              research={
                research
              }

            />

          )
        }


        {
          page
          === "patents"
          && (

            <PatentPage
              dossier={
                dossier
              }

              patents={
                patents
              }

            />

          )
        }


        {
          page
          === "assessment"
          && (

            <AssessmentPage
              dossier={
                dossier
              }

              assessment={
                assessment
              }

            />

          )
        }

      </main>

    </div>

  );

}


function Overview({
  dossier,
  assessment,
  patents,
  busy,
  uploadProposal,
  setPage
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
            Test the path to impact.
          </h2>

          <p>
            Extract the science, investigate
            existing research and patents,
            then assess novelty, translation
            and market viability.
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
          label="Patent searches"
          value={
            patents?.total_queries
            ?? 0
          }
        />

        <Stat
          label="Novelty"
          value={
            assessment?.novelty?.score
              != null
              ? `${assessment.novelty.score}/100`
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

          {
            busy
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
            Research and patent queries
            are generated automatically.
          </span>

        </div>


        <span className="primary-button">
          Choose file
        </span>


        <input

          type="file"

          accept=".pdf,.docx,.txt,.md"

          disabled={
            busy
          }

          onChange={
            event =>
              uploadProposal(
                event.target.files?.[0]
              )
          }

        />

      </label>


      {
        dossier
        && (

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
                    8
                  )
                  .join(
                    " · "
                  )
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
              </button>


              <button
                onClick={() =>
                  setPage(
                    "research"
                  )
                }
              >
                Research
              </button>


              <button
                onClick={() =>
                  setPage(
                    "patents"
                  )
                }
              >
                Patents
              </button>


              <button
                onClick={() =>
                  setPage(
                    "assessment"
                  )
                }
              >
                Assessment
              </button>

            </div>

          </div>

        )
      }

    </section>

  );

}


function DocumentPage({
  dossier,
  setPage
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
    ===
    "needs_visual_processing"
  ) {

    return (

      <section className="workspace">

        <div className="warning-panel">

          <FileText
            size={22}
          />

          <div>

            <strong>
              Visual processing required.
            </strong>

            <p>
              No usable native text layer
              was found in this document.
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
              "assessment"
            )
          }
        >

          View assessment

          <ArrowUpRight
            size={13}
          />

        </button>

      </div>


      <div className="document-layout">

        <div className="proposal-pane">

          <div className="pane-title">
            Proposal text
          </div>


          {
            (
              dossier.page_analysis
              || []
            ).map(
              page => (

                <article
                  className="page-block"
                  key={
                    page.page
                  }
                >

                  <div className="page-number">

                    PAGE {
                      page.page
                    }

                  </div>


                  <p>

                    {
                      page.text_preview
                      ||
                      "No text extracted."
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


function ResearchPage({
  dossier,
  research
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
            ACADEMIC LANDSCAPE
          </div>

          <h2>
            Literature and research evidence
          </h2>

          <p>
            Research results generated from
            concepts and technical claims.
          </p>

        </div>


        <div
          className={
            `research-status ${research.status}`
          }
        >
          {
            research.status
          }
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
                key={
                  index
                }
                group={
                  group
                }
              />

            )
          )
        }


        {
          !research.evidence?.length
          && (

            <div className="empty-inline">

              {
                research.status
                === "running"
                  ? "Research is running..."
                  : "No research results yet."
              }

            </div>

          )
        }

      </div>

    </section>

  );

}


function PatentPage({
  dossier,
  patents
}) {

  if (!dossier) {

    return (
      <Empty
        title="No patent context"
        text="Upload a proposal first."
      />
    );

  }


  if (!patents) {

    return (

      <section className="workspace">

        <div className="progress-panel">

          <Loader2
            size={17}
            className="spin"
          />

          <div>

            <strong>
              Building patent searches.
            </strong>

            <span>
              Generating targeted queries from
              the proposal's technical concepts.
            </span>

          </div>

        </div>

      </section>

    );

  }


  return (

    <section className="workspace">

      <div className="research-header">

        <div>

          <div className="eyebrow">
            PATENT LANDSCAPE
          </div>

          <h2>
            Targeted patent research
          </h2>

          <p>
            The application generates focused
            patent queries from the proposal
            rather than making you search
            each database manually.
          </p>

        </div>


        <div className="patent-count">

          {
            patents.total_queries
          }

          {" searches"}

        </div>

      </div>


      <div className="patent-source-grid">

        {
          (
            patents.sources
            || []
          ).map(
            source => (

              <div
                className="patent-source"
                key={
                  source.id
                }
              >

                <div className="eyebrow">
                  PATENT SOURCE
                </div>

                <h3>
                  {
                    source.name
                  }
                </h3>

                <p>
                  {
                    source.description
                  }
                </p>

              </div>

            )
          )
        }

      </div>


      <div className="patent-note">

        <ShieldCheck
          size={17}
        />

        <div>

          <strong>
            Search strategy
          </strong>

          <p>
            Start with Core Technology,
            then inspect Application,
            Performance and Competitor
            searches. Each search can be
            opened directly in the selected
            patent database.
          </p>

        </div>

      </div>


      <div className="patent-query-list">

        {
          (
            patents.query_cards
            || []
          ).map(
            (
              card,
              index
            ) => (

              <article
                className="patent-query"
                key={
                  index
                }
              >

                <div className="query-meta">

                  <span>
                    {
                      formatGroup(
                        card.group
                      )
                    }
                  </span>

                </div>


                <div className="query-string">

                  {card.query}

                </div>


                <p>
                  {
                    card.group_description
                  }
                </p>


                <div className="query-actions">

                  <ExternalLink
                    href={
                      card.sources
                        .google_patents
                    }
                    label="Google Patents"
                  />

                  <ExternalLink
                    href={
                      card.sources
                        .wipo
                    }
                    label="WIPO PATENTSCOPE"
                  />

                  <ExternalLink
                    href={
                      card.sources
                        .espacenet
                    }
                    label="EPO Espacenet"
                  />

                  <ExternalLink
                    href={
                      card.sources
                        .uspto
                    }
                    label="USPTO"
                  />

                </div>

              </article>

            )
          )
        }

      </div>


      <div className="methodology">

        <strong>
          What this MVP does
        </strong>

        <p>
          {
            patents.methodology
          }
        </p>

      </div>

    </section>

  );

}


function AssessmentPage({
  dossier,
  assessment
}) {

  if (!dossier) {

    return (
      <Empty
        title="No assessment"
        text="Upload a proposal first."
      />
    );

  }


  if (!assessment) {

    return (

      <section className="workspace">

        <div className="progress-panel">

          <Loader2
            size={17}
            className="spin"
          />

          <div>

            <strong>
              Building assessment.
            </strong>

            <span>
              Scores appear after research
              completes.
            </span>

          </div>

        </div>

      </section>

    );

  }


  return (

    <section className="workspace">

      <div className="research-header">

        <div>

          <div className="eyebrow">
            DECISION SUPPORT
          </div>

          <h2>
            Proposal assessment
          </h2>

          <p>
            Every score exposes its component
            inputs and measurement basis.
          </p>

        </div>

      </div>


      <div className="score-overview">

        <ScoreCard
          label="Novelty"
          data={
            assessment.novelty
          }
        />

        <ScoreCard
          label="Translation"
          data={
            assessment.translation
          }
        />

        <ScoreCard
          label="Market viability"
          data={
            assessment.market
          }
        />

      </div>


      <div className="assessment-note">

        <strong>
          These numbers are screening signals.
        </strong>

        <p>
          They do not replace technical review,
          patent advice or commercial due diligence.
          Missing evidence remains unmeasured.
        </p>

      </div>


      <AssessmentSection
        title="Novelty"
        data={
          assessment.novelty
        }
      />


      <AssessmentSection
        title="Translation"
        data={
          assessment.translation
        }
      />


      <AssessmentSection
        title="Market viability"
        data={
          assessment.market
        }
      />

    </section>

  );

}


function AssessmentSection({
  title,
  data
}) {

  if (!data) {
    return null;
  }


  return (

    <section className="assessment-section">

      <div className="assessment-section-header">

        <div>

          <h3>
            {title}
          </h3>

          <p>
            {
              data.methodology
            }
          </p>

        </div>


        <div className="formula-score">

          {
            data.score
              != null
              ? `${data.score}/100`
              : "Insufficient evidence"
          }

        </div>

      </div>


      <div className="component-table">

        <div className="component-row component-head">

          <span>
            Component
          </span>

          <span>
            Weight
          </span>

          <span>
            Score
          </span>

          <span>
            Status
          </span>

        </div>


        {
          (
            data.components
            || []
          ).map(
            (
              item,
              index
            ) => (

              <div
                className="component-row"
                key={
                  index
                }
              >

                <span>

                  <strong>
                    {
                      item.label
                    }
                  </strong>

                  <small>
                    {
                      item.basis
                    }
                  </small>

                </span>


                <span>
                  {
                    item.weight
                  }%
                </span>


                <span>

                  {
                    item.measured
                      ? item.score
                      : "—"
                  }

                </span>


                <span>

                  {
                    item.measured
                      ? "Measured"
                      : "Not measured"
                  }

                </span>

              </div>

            )
          )
        }

      </div>

    </section>

  );

}


function ScoreCard({
  label,
  data
}) {

  const score =
    data?.score;


  return (

    <div className="score-card">

      <span className="eyebrow">
        {label}
      </span>


      <strong>

        {
          score != null
            ? score
            : "—"
        }

        <small>

          {
            score != null
              ? "/100"
              : ""
          }

        </small>

      </strong>


      <span className="score-class">

        {
          data?.classification
          ||
          "Insufficient evidence"
        }

      </span>


      <div className="score-card-meta">

        Confidence:

        {" "}

        {
          data?.confidence
          != null
            ? `${data.confidence}/100`
            : "—"
        }

      </div>

    </div>

  );

}


function EvidenceGroup({
  group
}) {

  return (

    <article className="evidence-group">

      <div className="evidence-heading">

        <div>

          <div className="eyebrow">
            SEARCH QUERY
          </div>

          <strong>
            {
              group.query
            }
          </strong>

        </div>


        <span>

          {
            group.papers?.length
            || 0
          }

          {" results"}

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
                  ||
                  "#"
                }
                target="_blank"
                rel="noreferrer"
                key={
                  index
                }
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
                    }
                    {" citations"}
                  </span>

                </div>


                <strong>
                  {
                    paper.title
                  }
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


function AnalysisSection({
  title,
  items
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
                  key={
                    index
                  }
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


function ExternalLink({
  href,
  label
}) {

  if (!href) {
    return null;
  }


  return (

    <a
      href={
        href
      }
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


function formatGroup(
  group
) {

  const map = {

    core:
      "Core technology",

    application:
      "Application",

    performance:
      "Performance",

    competitor:
      "Competitive landscape"

  };


  return (
    map[group]
    || group
  );

}


function Stat({
  label,
  value
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
  text
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
