import React, {
  Component,
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


class AppErrorBoundary extends Component {

  constructor(props) {
    super(props);

    this.state = {
      hasError: false,
      error: null
    };
  }


  static getDerivedStateFromError(
    error
  ) {

    return {
      hasError: true,
      error
    };

  }


  componentDidCatch(
    error,
    errorInfo
  ) {

    console.error(
      "FI Research UI crashed:",
      error
    );

    console.error(
      "Component stack:",
      errorInfo?.componentStack
    );

  }


  render() {

    if (
      this.state.hasError
    ) {

      return (

        <div className="fatal-error">

          <div className="fatal-error-card">

            <div className="eyebrow">
              APPLICATION ERROR
            </div>

            <h2>
              The page hit a frontend error.
            </h2>

            <p>
              The application caught the error
              instead of leaving the page blank.
            </p>


            <div className="fatal-error-code">

              {
                this.state.error?.message
                ||
                "Unknown JavaScript error."
              }

            </div>


            <button
              onClick={() =>
                window.location.reload()
              }
            >
              Reload application
            </button>

          </div>

        </div>

      );

    }


    return this.props.children;

  }

}


export default function App() {

  return (

    <AppErrorBoundary>

      <ResearchApp />

    </AppErrorBoundary>

  );

}


function ResearchApp() {

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

    } catch (
      error
    ) {

      console.error(
        "Network error:",
        error
      );

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

    setResearch({
      status:
        "not_started",
      queries: [],
      evidence: []
    });

    setPatents(
      null
    );

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


      if (
        !result?.id
      ) {

        throw new Error(
          "The server did not return a document ID."
        );

      }


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
        "Proposal loaded. Research is running in the background."
      );


      setPage(
        "document"
      );


    } catch (
      error
    ) {

      console.error(
        "Upload error:",
        error
      );


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


      let stopped =
        false;

      let timer =
        null;


      async function poll() {

        try {

          const result =
            await api(
              `${API}/proposals/${documentId}`
            );


          if (
            stopped
          ) {
            return;
          }


          setDossier(
            result?.dossier
            || null
          );


          setResearch(
            result?.research
            || {
              status:
                "not_started",
              queries: [],
              evidence: []
            }
          );


          setNovelty(
            result?.novelty
            || null
          );


          setAssessment(
            result?.assessment
            || null
          );


          setPatents(
            result?.patents
            || null
          );


          if (
            result?.status
            ===
            "error"
          ) {

            setMessage(
              result?.error
              ||
              "Document processing failed."
            );

            return;

          }


          if (
            result?.research?.status
            ===
            "running"
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

          console.error(
            "Polling error:",
            error
          );


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


          if (
            !stopped
          ) {

            setMessage(
              error.message
            );

          }

        }

      }


      poll();


      return () => {

        stopped =
          true;


        if (
          timer
        ) {

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

          {
            NAV.map(
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

                  onClick={() =>
                    setPage(
                      id
                    )
                  }

                >

                  <Icon
                    size={16}
                  />

                  <span>
                    {
                      label
                    }
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
            )
          }

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
                (
                  NAV.find(
                    item =>
                      item[0]
                      ===
                      page
                  )
                  || []
                )[1]
                ||
                "Workspace"
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
                : research.status ===
                    "running"
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
          page === "overview"
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
          page === "document"
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
          page === "research"
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
          page === "patents"
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
          page === "assessment"
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
            ??
            "—"
          }
        />

        <Stat
          label="Patent searches"
          value={
            patents?.total_queries
            ??
            0
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

          onClick={
            () =>
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
                ===
                "running"
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
              Generating targeted searches
              from the technical concepts.
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
            Focused searches are generated
            separately for core technology,
            applications, performance and
            competing approaches.
          </p>

        </div>


        <div className="patent-count">

          {
            patents.total_queries
            ??
            0
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
            Core technology searches find
            direct prior art. Application
            searches investigate use cases.
            Performance searches target
            technical claims. Competitive
            searches look for alternatives.
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

                  {
                    card.query
                  }

                </div>


                <p>
                  {
                    card.group_description
                  }
                </p>


                <div className="query-actions">

                  <ExternalLink
                    href={
                      card.sources?.google_patents
                    }
                    label="Google Patents"
                  />

                  <ExternalLink
                    href={
                      card.sources?.wipo
                    }
                    label="WIPO PATENTSCOPE"
                  />

                  <ExternalLink
                    href={
                      card.sources?.espacenet
                    }
                    label="EPO Espacenet"
                  />

                  <ExternalLink
                    href={
                      card.sources?.uspto
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
          MVP methodology
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


  const safeAssessment =
    (
      assessment
      && typeof assessment === "object"
    )
      ? assessment
      : null;


  if (!safeAssessment) {

    return (

      <section className="workspace">

        <div className="progress-panel">

          {
            assessment === null
              ? (
                <Loader2
                  size={17}
                  className="spin"
                />
              )
              : (
                <BarChart3
                  size={17}
                />
              )
          }


          <div>

            <strong>
              Building assessment.
            </strong>

            <span>
              Novelty, translation and market
              viability appear after research.
            </span>

          </div>

        </div>


        <div className="assessment-debug">

          <div className="eyebrow">
            DEBUG STATE
          </div>

          <p>

            Document loaded successfully.

            {" "}

            Research status:

            {" "}

            <strong>
              {
                (
                  dossier
                  && dossier.research_status
                )
                ||
                "background"
              }
            </strong>

          </p>

        </div>

      </section>

    );

  }


  const safeNovelty =
    isObject(
      safeAssessment.novelty
    )
      ? safeAssessment.novelty
      : null;


  const safeTranslation =
    isObject(
      safeAssessment.translation
    )
      ? safeAssessment.translation
      : null;


  const safeMarket =
    isObject(
      safeAssessment.market
    )
      ? safeAssessment.market
      : null;


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
            safeNovelty
          }
        />


        <ScoreCard
          label="Translation"
          data={
            safeTranslation
          }
        />


        <ScoreCard
          label="Market viability"
          data={
            safeMarket
          }
        />

      </div>


      <div className="assessment-note">

        <strong>
          These are screening signals, not decisions.
        </strong>

        <p>
          Missing evidence is not turned into
          an invented score. Components that
          cannot be measured remain explicitly
          marked as unmeasured.
        </p>

      </div>


      <AssessmentSection
        title="Novelty"
        data={
          safeNovelty
        }
      />


      <AssessmentSection
        title="Translation"
        data={
          safeTranslation
        }
      />


      <AssessmentSection
        title="Market viability"
        data={
          safeMarket
        }
      />

    </section>

  );

}


function ScoreCard({
  label,
  data
}) {

  if (!data) {

    return (

      <div className="score-card">

        <span className="eyebrow">
          {label}
        </span>

        <strong>
          —
        </strong>

        <span className="score-class">
          Insufficient evidence
        </span>

        <div className="score-card-meta">
          No assessment data returned.
        </div>

      </div>

    );

  }


  return (

    <div className="score-card">

      <span className="eyebrow">
        {label}
      </span>


      <strong>

        {
          data.score
          != null
            ? data.score
            : "—"
        }


        <small>

          {
            data.score
            != null
              ? "/100"
              : ""
          }

        </small>

      </strong>


      <span className="score-class">

        {
          data.classification
          ||
          "Insufficient evidence"
        }

      </span>


      <div className="score-card-meta">

        Confidence:

        {" "}

        {
          data.confidence
          != null
            ? `${data.confidence}/100`
            : "—"
        }

      </div>

    </div>

  );

}


function AssessmentSection({
  title,
  data
}) {

  if (!data) {

    return (

      <section className="assessment-section">

        <div className="assessment-section-header">

          <div>

            <h3>
              {title}
            </h3>

            <p>
              No assessment data was returned
              for this category.
            </p>

          </div>


          <div className="formula-score">
            —
          </div>

        </div>

      </section>

    );

  }


  const components =
    Array.isArray(
      data.components
    )
      ? data.components
      : [];


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
              ||
              "Assessment methodology not supplied."
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


      {
        components.length === 0

          ? (

            <div className="empty-inline">
              No component data was returned.
            </div>

          )

          : (

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
                components.map(
                  (
                    item,
                    index
                  ) => {

                    const safeItem =
                      item
                      && typeof item === "object"
                        ? item
                        : {};


                    return (

                      <div
                        className="component-row"
                        key={
                          index
                        }
                      >

                        <span>

                          <strong>
                            {
                              safeItem.label
                              ||
                              `Component ${index + 1}`
                            }
                          </strong>

                          <small>
                            {
                              safeItem.basis
                              ||
                              "No calculation basis supplied."
                            }
                          </small>

                        </span>


                        <span>

                          {
                            safeItem.weight
                            != null
                              ? `${safeItem.weight}%`
                              : "—"
                          }

                        </span>


                        <span>

                          {
                            safeItem.measured
                            && safeItem.score
                              != null

                              ? safeItem.score

                              : "—"
                          }

                        </span>


                        <span>

                          {
                            safeItem.measured
                              ? "Measured"
                              : "Not measured"
                          }

                        </span>

                      </div>

                    );

                  }
                )
              }

            </div>

          )
      }

    </section>

  );

}


function EvidenceGroup({
  group
}) {

  if (
    !group
    || typeof group !== "object"
  ) {

    return null;

  }


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
              ||
              "Unnamed query"
            }
          </strong>

        </div>


        <span>

          {
            Array.isArray(
              group.papers
            )
              ? group.papers.length
              : 0
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
            Array.isArray(
              group.papers
            )
              ? group.papers
              : []
          ).map(
            (
              paper,
              index
            ) => (

              <a
                className="paper"
                href={
                  paper?.url
                  || "#"
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
                      paper?.source
                      ||
                      "Source"
                    }
                  </span>

                  <span>
                    {
                      paper?.year
                      ||
                      "—"
                    }
                  </span>

                  <span>
                    {
                      paper?.citations
                      ||
                      0
                    }
                    {" citations"}
                  </span>

                </div>


                <strong>
                  {
                    paper?.title
                    ||
                    "Untitled result"
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

  const safeItems =
    Array.isArray(
      items
    )
      ? items
      : [];


  return (

    <div className="analysis-section">

      <div className="pane-title">
        {title}
      </div>


      {
        safeItems.length

          ? safeItems
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
                  {
                    item
                  }
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

      {
        label
      }

      <ArrowUpRight
        size={11}
      />

    </a>

  );

}


function formatGroup(
  group
) {

  const labels = {

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
    labels[group]
    ||
    group
    ||
    "Patent search"
  );

}


function isObject(
  value
) {

  return (
    value !== null
    &&
    typeof value === "object"
    &&
    !Array.isArray(value)
  );

}


function Stat({
  label,
  value
}) {

  return (

    <div className="stat">

      <span>
        {
          label
        }
      </span>

      <strong>
        {
          value
        }
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
          {
            title
          }
        </h3>

        <p>
          {
            text
          }
        </p>

      </div>

    </section>

  );

}
