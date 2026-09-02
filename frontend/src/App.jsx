import React, { useMemo, useState } from "react";

import {
  Activity,
  ArrowUpRight,
  BookOpen,
  CheckCircle2,
  ChevronRight,
  FileText,
  FolderOpen,
  Gauge,
  Search,
  ShieldCheck,
  Sparkles,
  Upload,
  Loader2,
  ExternalLink,
  SlidersHorizontal,
} from "lucide-react";


const API =
  import.meta.env.VITE_API_BASE ||
  "http://localhost:8000/api";


const NAV_ITEMS = [
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
    id: "awards",
    label: "Awards",
    icon: FolderOpen,
  },
  {
    id: "research",
    label: "Research & IP",
    icon: BookOpen,
  },
  {
    id: "review",
    label: "Reviewer",
    icon: ShieldCheck,
  },
];


export default function App() {

  const [
    page,
    setPage,
  ] = useState("overview");


  const [
    proposal,
    setProposal,
  ] = useState(null);


  const [
    research,
    setResearch,
  ] = useState([]);


  const [
    awards,
    setAwards,
  ] = useState([]);


  const [
    loading,
    setLoading,
  ] = useState(false);


  const [
    status,
    setStatus,
  ] = useState("Ready");


  const [
    message,
    setMessage,
  ] = useState("");


  async function uploadProposal(file) {

    if (!file) {
      return;
    }


    setLoading(true);

    setStatus("Reading proposal...");

    setMessage("");


    try {

      const body =
        new FormData();

      body.append(
        "file",
        file
      );


      const response =
        await fetch(
          `${API}/proposals/analyze`,
          {
            method: "POST",
            body,
          }
        );


      const data =
        await response.json();


      if (!response.ok) {

        throw new Error(
          data.detail ||
          "Proposal upload failed."
        );

      }


      setProposal(
        data
      );
      
      setEvidence(
        data.research?.evidence
        ||
        []
      );
            
      setStatus(
        "Proposal ready"
      );

      setMessage(
        "Proposal loaded successfully."
      );


      setPage(
        "overview"
      );


    } catch (error) {

      setStatus(
        "Error"
      );

      setMessage(
        error.message
      );

    } finally {

      setLoading(false);

    }

  }


  async function searchResearch(
    query
  ) {

    const cleanQuery =
      String(query || "").trim();


    if (!cleanQuery) {

      setMessage(
        "Enter a research question or technical claim."
      );

      return;

    }


    setLoading(true);

    setStatus(
      "Searching literature..."
    );

    setMessage("");


    try {

      const params =
        new URLSearchParams({

          query:
            cleanQuery,

          year:
            "2020",

          limit:
            "15",

        });


      const response =
        await fetch(

          `${API}/research/search?${params}`,

          {
            method:
              "POST",
          }

        );


      const data =
        await response.json();


      if (!response.ok) {

        throw new Error(

          data.detail ||
          "Research search failed."

        );

      }


      setResearch(
        data.results || []
      );


      setStatus(
        "Research ready"
      );


      setMessage(

        `${data.count || 0} research records found.`

      );


    } catch (error) {

      setStatus(
        "Search error"
      );

      setMessage(
        error.message
      );

    } finally {

      setLoading(false);

    }

  }


  async function uploadAward(file) {

    if (!file) {
      return;
    }


    setLoading(true);

    setStatus(
      "Reading award..."
    );


    try {

      const body =
        new FormData();

      body.append(
        "file",
        file
      );


      const response =
        await fetch(

          `${API}/proposals/analyze`,

          {
            method:
              "POST",
            body,
          }

        );


      const data =
        await response.json();


      if (!response.ok) {

        throw new Error(

          data.detail ||
          "Award upload failed."

        );

      }


      setAwards(
        current => [

          ...current,

          {

            filename:
              file.name,

            text:
              data.raw_text ||
              "",

          },

        ]

      );


      setStatus(
        "Award ready"
      );


      setMessage(
        `${file.name} added.`
      );


    } catch (error) {

      setStatus(
        "Error"
      );

      setMessage(
        error.message
      );

    } finally {

      setLoading(false);

    }

  }


  const currentTitle = useMemo(

    () =>

      proposal?.document?.title ||
      proposal?.document?.filename ||
      "No proposal loaded",

    [proposal]

  );


  return (

    <div className="app">

      <aside className="sidebar">

        <div className="brand">

          <div className="brand-logo">

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

          {NAV_ITEMS.map(
            item => (

              <NavItem

                key={
                  item.id
                }

                active={
                  page === item.id
                }

                icon={
                  <item.icon
                    size={17}
                  />
                }

                label={
                  item.label
                }

                onClick={() =>
                  setPage(
                    item.id
                  )
                }

              />

            )
          )}

        </nav>


        <div className="sidebar-status">

          <CheckCircle2
            size={14}
          />

          System ready

        </div>

      </aside>


      <main>

        <header>

          <div>

            <div className="eyebrow">
              RESEARCH WORKSPACE
            </div>

            <h1>

              {

                NAV_ITEMS.find(
                  item =>
                    item.id === page
                )?.label

              }

            </h1>

          </div>


          <div className="online">

            <span />

            {status}

          </div>

        </header>


        {message && (

          <div className="message">

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

            proposal={
              proposal
            }

            awards={
              awards
            }

            research={
              research
            }

            loading={
              loading
            }

            upload={
              uploadProposal
            }

            navigate={
              setPage
            }

          />

        )}


        {page === "document" && (

          <DocumentView
            proposal={
              proposal
            }
          />

        )}


        {page === "awards" && (

          <AwardsView

            awards={
              awards
            }

            upload={
              uploadAward
            }

          />

        )}


        {page === "research" && (

          <ResearchView

            proposal={
              proposal
            }

            research={
              research
            }

            loading={
              loading
            }

            search={
              searchResearch
            }

          />

        )}


        {page === "review" && (

          <ReviewView />

        )}

      </main>

    </div>

  );

}


function NavItem({
  active,
  icon,
  label,
  onClick,
}) {

  return (

    <button

      className={
        active
          ? "nav active"
          : "nav"
      }

      onClick={
        onClick
      }

    >

      {icon}

      <span>
        {label}
      </span>


      {active && (

        <ChevronRight
          size={14}
          className="nav-arrow"
        />

      )}

    </button>

  );

}


function Overview({
  proposal,
  awards,
  research,
  loading,
  upload,
  navigate,
}) {

  return (

    <section className="page">

      <div className="hero">

        <div>

          <span className="hero-kicker">
            PROPOSAL INTELLIGENCE
          </span>


          <h2>

            Understand the proposal.
            <br />

            Find what already exists.

          </h2>


          <p>

            Start with the source document,
            then move from claims to evidence,
            research and prior work.

          </p>

        </div>


        <div className="orb">

          <Sparkles
            size={34}
          />

        </div>

      </div>


      <div className="metrics">

        <Metric
          label="Proposal"
          value={
            proposal
              ? "Loaded"
              : "None"
          }
        />

        <Metric
          label="Awards"
          value={
            awards.length
          }
        />

        <Metric
          label="Research"
          value={
            research.length
          }
        />

        <Metric
          label="Status"
          value={
            loading
              ? "Working"
              : "Ready"
          }
        />

      </div>


      <div className="section-title">

        <div>

          <h3>
            Start a research workspace
          </h3>

          <p>
            Upload your source proposal.
          </p>

        </div>

      </div>


      <label className="upload">

        <div className="upload-icon">

          {loading

            ? <Loader2
                size={20}
                className="spin"
              />

            : <Upload
                size={20}
              />

          }

        </div>


        <div>

          <strong>

            {
              loading
                ? "Processing document..."
                : "Drop a proposal here"
            }

          </strong>


          <span>
            PDF, DOCX, TXT or Markdown
          </span>

        </div>


        <span className="upload-button">

          Choose file

        </span>


        <input

          type="file"

          accept=".pdf,.docx,.txt,.md"

          disabled={
            loading
          }

          onChange={
            event =>
              upload(
                event.target.files?.[0]
              )
          }

        />

      </label>


      {proposal && (

        <div className="proposal-card">

          <div className="proposal-head">

            <div>

              <span className="field-label">
                CURRENT PROPOSAL
              </span>

              <h3>
                {
                  proposal.document?.title
                  ||
                  proposal.document?.filename
                  ||
                  "Untitled"
                }
              </h3>

            </div>


            <span className="chip">

              {
                proposal.document
                  ?.funding_initiative
                ||
                "FI not determined"
              }

            </span>

          </div>


          <div className="proposal-body">

            <div>

              <span className="field-label">
                SUMMARY
              </span>

              <p>

                {
                  proposal.summary
                  ||
                  "No summary extracted."
                }

              </p>

            </div>


            <div>

              <span className="field-label">
                SOURCE
              </span>

              <p>

                {
                  proposal.document
                    ?.document_type
                  ||
                  "Unknown"
                }

              </p>

              <small>

                {
                  proposal.document
                    ?.pages
                  ||
                  "?"
                }

                {" pages"}

              </small>

            </div>

          </div>


          <div className="actions">

            <button
              onClick={() =>
                navigate(
                  "document"
                )
              }
            >

              Open document

              <ArrowUpRight
                size={15}
              />

            </button>


            <button
              onClick={() =>
                navigate(
                  "research"
                )
              }
            >

              Investigate

              <Search
                size={15}
              />

            </button>

          </div>

        </div>

      )}

    </section>

  );

}


function Metric({
  label,
  value,
}) {

  return (

    <div className="metric">

      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>

    </div>

  );

}


function DocumentView({
  proposal
}) {

  if (!proposal) {

    return (

      <Empty

        title="No proposal loaded"

        text="Upload a proposal from the Overview page."

      />

    );

  }


  const understanding =
    proposal.understanding ||
    {};


  return (

    <section className="page">

      <div className="section-title">

        <div>

          <h3>
            Document understanding
          </h3>

          <p>
            Native extraction first.
            Semantic analysis can follow.
          </p>

        </div>

      </div>


      <div className="info-grid">

        {[

          ["Problem", "problem"],

          ["Technology", "technology"],

          ["Baseline", "baseline"],

          [
            "Proposed solution",
            "proposed_solution",
          ],

        ].map(
          ([label, key]) => (

            <div
              className="info-card"
              key={
                label
              }
            >

              <span className="field-label">
                {label}
              </span>

              <p>

                {
                  understanding[key]
                  ||
                  "Not determined"
                }

              </p>

            </div>

          )
        )}

      </div>


      <div className="panel">

        <div className="panel-head">

          <div>

            <h3>
              Document map
            </h3>

            <p>
              Detected structural sections.
            </p>

          </div>


          <span className="chip">

            {
              proposal.document
                ?.sections
                ?.length
              ||
              0
            }

            {" sections"}

          </span>

        </div>


        {(
          proposal.document
            ?.sections
          ||
          []
        ).map(
          section => (

            <div
              className="row-line"
              key={
                section.name
              }
            >

              <span>
                {section.name}
              </span>

              <strong>

                {
                  Math.round(
                    (
                      section.confidence
                      ||
                      0
                    )
                    *
                    100
                  )
                }%

              </strong>

            </div>

          )
        )}

      </div>


      <div className="panel">

        <div className="panel-head">

          <div>

            <h3>
              Potential technical claims
            </h3>

            <p>
              Signals detected from source text.
            </p>

          </div>


          <SlidersHorizontal
            size={17}
            color="#94a3b8"
          />

        </div>


        {(
          proposal.claims
          ||
          []
        ).map(
          (
            claim,
            index
          ) => (

            <div
              className="claim"
              key={
                index
              }
            >

              <span>

                {
                  index + 1
                }

              </span>


              <p>
                {claim}
              </p>

            </div>

          )
        )}

      </div>

    </section>

  );

}


function AwardsView({
  awards,
  upload
}) {

  return (

    <section className="page">

      <div className="section-title">

        <div>

          <h3>
            Award landscape
          </h3>

          <p>
            Build a corpus of previous work.
          </p>

        </div>

      </div>


      <label className="upload">

        <div className="upload-icon">

          <Upload
            size={20}
          />

        </div>


        <div>

          <strong>
            Add previous award
          </strong>

          <span>
            PDF, DOCX, TXT or Markdown
          </span>

        </div>


        <span className="upload-button">
          Choose file
        </span>


        <input

          type="file"

          accept=".pdf,.docx,.txt,.md"

          onChange={
            event =>
              upload(
                event.target.files?.[0]
              )
          }

        />

      </label>


      <div className="panel">

        <div className="panel-head">

          <div>

            <h3>
              Award corpus
            </h3>

            <p>
              Documents currently loaded.
            </p>

          </div>


          <span className="chip">

            {
              awards.length
            }

          </span>

        </div>


        {!awards.length && (

          <div className="empty-row">

            No previous awards loaded.

          </div>

        )}


        {awards.map(
          (
            award,
            index
          ) => (

            <div
              className="file-row"
              key={
                index
              }
            >

              <FileText
                size={16}
              />

              <span>

                {
                  award.filename
                }

              </span>

            </div>

          )
        )}

      </div>

    </section>

  );

}


function ResearchView({
  proposal,
  research,
  loading,
  search
}) {

  const defaultQuery =
    proposal
      ?.document
      ?.title
    ||
    "";


  const [
    query,
    setQuery
  ] = useState(
    defaultQuery
  );


  const encodedQuery =
    encodeURIComponent(
      query ||
      "water technology"
    );


  return (

    <section className="page">

      <div className="section-title">

        <div>

          <h3>
            Research & IP
          </h3>

          <p>
            Search literature and jump
            directly into patent sources.
          </p>

        </div>

      </div>


      <div className="search">

        <Search
          size={18}
        />


        <input

          value={
            query
          }

          onChange={
            event =>
              setQuery(
                event.target.value
              )
          }

          onKeyDown={
            event => {

              if (
                event.key === "Enter"
              ) {

                search(
                  query
                );

              }

            }
          }

          placeholder={
            "Technology, claim or research question"
          }

        />


        <button

          onClick={() =>
            search(
              query
            )
          }

          disabled={
            loading
          }

        >

          {loading
            ? <Loader2
                size={16}
                className="spin"
              />
            : <Search
                size={16}
              />
          }

          Search

        </button>

      </div>


      <div className="source-links">

        <SourceLink

          name="Google Scholar"

          url={
            `https://scholar.google.com/scholar?q=${encodedQuery}`
          }

        />


        <SourceLink

          name="Google Patents"

          url={
            `https://patents.google.com/?q=${encodedQuery}`
          }

        />


        <SourceLink

          name="Semantic Scholar"

          url={
            `https://www.semanticscholar.org/search?q=${encodedQuery}`
          }

        />


        <SourceLink

          name="WIPO PATENTSCOPE"

          url={
            `https://patentscope.wipo.int/search/en/result.jsf?query=${encodedQuery}`
          }

        />

      </div>


      <div className="panel">

        <div className="panel-head">

          <div>

            <h3>
              Literature
            </h3>

            <p>
              OpenAlex + Crossref
            </p>

          </div>


          <span className="chip">

            {
              research.length
            }

          </span>

        </div>


        {!research.length && (

          <div className="empty-row">

            Run a search to populate the evidence set.

          </div>

        )}


        {research.map(
          (
            item,
            index
          ) => (

            <div
              className="research-item"
              key={
                index
              }
            >

              <div>

                <span className="research-source">
                  {item.source}
                </span>

                <span className="muted">

                  {" "}
                  {item.year || ""}
                  {" · "}
                  {item.citations || 0}
                  {" citations"}

                </span>

              </div>


              <a

                href={
                  item.url
                  ||
                  "#"
                }

                target="_blank"

                rel="noreferrer"

              >

                {item.title}

                <ExternalLink
                  size={13}
                />

              </a>

            </div>

          )
        )}

      </div>

    </section>

  );

}


function SourceLink({
  name,
  url
}) {

  return (

    <a

      href={
        url
      }

      target="_blank"

      rel="noreferrer"

    >

      {name}

      <ArrowUpRight
        size={13}
      />

    </a>

  );

}


function ReviewView() {

  const criteria = [

    "Science & technology",

    "Impact / national benefit",

    "Management & delivery",

    "Budget / value",

  ];


  const [
    scores,
    setScores
  ] = useState(

    Object.fromEntries(

      criteria.map(
        criterion => [
          criterion,
          4
        ]
      )

    )

  );


  const average =

    Object.values(
      scores
    ).reduce(

      (
        total,
        value
      ) =>

        total +
        Number(
          value
        ),

      0

    )

    /

    criteria.length;


  return (

    <section className="page">

      <div className="section-title">

        <div>

          <h3>
            Human reviewer
          </h3>

          <p>
            Structured scoring workspace.
          </p>

        </div>

      </div>


      <div className="review-grid">

        {criteria.map(
          criterion => (

            <div
              className="review-card"
              key={
                criterion
              }
            >

              <span className="field-label">
                {criterion}
              </span>


              <div className="slider">

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
                          event.target.value,

                      })

                  }

                />


                <strong>

                  {
                    scores[
                      criterion
                    ]
                  }

                  /5

                </strong>

              </div>

            </div>

          )
        )}

      </div>


      <div className="score">

        <span className="field-label">
          PRELIMINARY SCORE
        </span>


        <strong>

          {
            average.toFixed(
              2
            )
          }

          <small>
            /5
          </small>

        </strong>


        <div className="score-bar">

          <span
            style={{
              width:
                `${(average / 5) * 100}%`
            }}
          />

        </div>

      </div>

    </section>

  );

}


function Empty({
  title,
  text
}) {

  return (

    <section className="page">

      <div className="empty">

        <FileText
          size={30}
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
