import React, {
  useState
} from "react";

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
  Loader2

} from "lucide-react";


const API = "/api";


function App() {

  const [
    tab,
    setTab
  ] = useState(
    "overview"
  );

  const [
    proposal,
    setProposal
  ] = useState(
    null
  );

  const [
    awards,
    setAwards
  ] = useState(
    []
  );

  const [
    research,
    setResearch
  ] = useState(
    []
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


  async function uploadProposal(
    file
  ) {

    if (!file) {
      return;
    }

    setBusy(true);

    setMessage(
      "Reading proposal..."
    );

    const form =
      new FormData();

    form.append(
      "file",
      file
    );


    try {

      const response =
        await fetch(

          `${API}/proposals/analyze`,

          {

            method:
              "POST",

            body:
              form,

          }

        );


      const data =
        await response.json();


      if (!response.ok) {

        throw new Error(

          data.detail
          ||
          "Upload failed."

        );

      }


      setProposal(
        data
      );


      setMessage(
        "Proposal loaded."
      );


      setTab(
        "overview"
      );


    } catch (error) {

      setMessage(
        error.message
      );

    } finally {

      setBusy(
        false
      );

    }

  }


  async function searchResearch(
    query
  ) {

    if (!query.trim()) {

      setMessage(
        "Enter a research question."
      );

      return;

    }


    setBusy(true);

    setMessage(
      "Searching research..."
    );


    try {

      const params =
        new URLSearchParams({

          query,

          year:
            "2020",

          limit:
            "10",

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

          data.detail
          ||
          "Research search failed."

        );

      }


      setResearch(
        data.results
        ||
        []
      );


      setMessage(

        `Found ${data.count || 0} records.`

      );


    } catch (error) {

      setMessage(
        error.message
      );

    } finally {

      setBusy(
        false
      );

    }

  }


  async function uploadAward(
    file
  ) {

    if (!file) {
      return;
    }

    setBusy(true);

    setMessage(
      "Reading award..."
    );


    const form =
      new FormData();

    form.append(
      "file",
      file
    );


    try {

      const response =
        await fetch(

          `${API}/proposals/analyze`,

          {

            method:
              "POST",

            body:
              form,

          }

        );


      const data =
        await response.json();


      if (!response.ok) {

        throw new Error(

          data.detail
          ||
          "Award upload failed."

        );

      }


      setAwards(
        previous => [

          ...previous,

          {

            filename:
              file.name,

            text:
              data.raw_text
              ||
              "",

          },

        ]

      );


      setMessage(
        `${file.name} added.`
      );


    } catch (error) {

      setMessage(
        error.message
      );

    } finally {

      setBusy(
        false
      );

    }

  }


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

          <Nav
            active={
              tab === "overview"
            }
            icon={
              <Gauge size={17} />
            }
            label="Overview"
            onClick={() =>
              setTab("overview")
            }
          />


          <Nav
            active={
              tab === "document"
            }
            icon={
              <FileText size={17} />
            }
            label="Document"
            onClick={() =>
              setTab("document")
            }
          />


          <Nav
            active={
              tab === "awards"
            }
            icon={
              <FolderOpen size={17} />
            }
            label="Awards"
            onClick={() =>
              setTab("awards")
            }
          />


          <Nav
            active={
              tab === "research"
            }
            icon={
              <BookOpen size={17} />
            }
            label="Research & IP"
            onClick={() =>
              setTab("research")
            }
          />


          <Nav
            active={
              tab === "review"
            }
            icon={
              <ShieldCheck size={17} />
            }
            label="Reviewer"
            onClick={() =>
              setTab("review")
            }
          />

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
                {

                  overview:
                    "Research with context.",

                  document:
                    "Document understanding",

                  awards:
                    "Award landscape",

                  research:
                    "Research & IP",

                  review:
                    "Human reviewer",

                }[tab]
              }

            </h1>

          </div>


          <div className="online">

            <span />

            Online

          </div>

        </header>


        {message && (

          <div className="message">

            {message}

            <button
              onClick={() =>
                setMessage("")
              }
            >
              ×
            </button>

          </div>

        )}


        {tab === "overview" && (

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

            busy={
              busy
            }

            upload={
              uploadProposal
            }

            goTo={
              setTab
            }

          />

        )}


        {tab === "document" && (

          <DocumentView
            proposal={
              proposal
            }
          />

        )}


        {tab === "awards" && (

          <AwardsView
            awards={
              awards
            }

            upload={
              uploadAward
            }

          />

        )}


        {tab === "research" && (

          <ResearchView
            proposal={
              proposal
            }

            research={
              research
            }

            busy={
              busy
            }

            search={
              searchResearch
            }

          />

        )}


        {tab === "review" && (

          <ReviewView />

        )}

      </main>

    </div>

  );

}


function Nav({
  active,
  icon,
  label,
  onClick
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
        />

      )}

    </button>

  );

}


function Overview({

  proposal,

  awards,

  research,

  busy,

  upload,

  goTo,

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

            Then find what already exists.

          </h2>

          <p>

            Turn a technical proposal
            into structured evidence,
            research leads and
            reviewer questions.

          </p>

        </div>


        <div className="orb">

          <Sparkles />

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
            busy
              ? "Processing"
              : "Ready"
          }
        />

      </div>


      <div className="section-title">

        <div>

          <h3>
            Start with your proposal
          </h3>

          <p>
            Upload the source document.
          </p>

        </div>

      </div>


      <label className="upload">

        <div className="upload-icon">

          {busy

            ? <Loader2
                className="spin"
                size={20}
              />

            : <Upload
                size={20}
              />

          }

        </div>


        <div>

          <strong>

            {busy

              ? "Reading document..."

              : "Drop a proposal here"

            }

          </strong>

          <span>
            PDF, DOCX, TXT or Markdown
          </span>

        </div>


        <span className="upload-button">

          {busy
            ? "Processing"
            : "Choose file"}

        </span>


        <input

          type="file"

          accept=".pdf,.docx,.txt,.md"

          disabled={
            busy
          }

          onChange={
            e =>
              upload(
                e.target.files?.[0]
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

                {proposal.document?.title
                  ||
                  proposal.document?.filename
                  ||
                  "Untitled"}

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
                  "No fast-pass summary extracted."
                }

              </p>

            </div>


            <div>

              <span className="field-label">
                DOCUMENT
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
                goTo("document")
              }
            >

              Open document

              <ArrowUpRight
                size={15}
              />

            </button>


            <button
              onClick={() =>
                goTo("research")
              }
            >

              Search research

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
  value
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
        text="Upload a proposal from Overview first."
      />

    );

  }


  const u =
    proposal.understanding
    ||
    {};


  return (

    <section className="page">

      <div className="section-title">

        <div>

          <h3>
            Document understanding
          </h3>

          <p>
            Native extraction and structural signals.
          </p>

        </div>

      </div>


      <div className="info-grid">

        {[
          ["Problem", "problem"],
          ["Technology", "technology"],
          ["Baseline", "baseline"],
          ["Proposed solution", "proposed_solution"],
        ].map(
          ([label, key]) => (

            <div
              className="info-card"
              key={label}
            >

              <span className="field-label">
                {label}
              </span>

              <p>

                {u[key]
                  ||
                  "Not determined"}

              </p>

            </div>

          )
        )}

      </div>


      <div className="panel">

        <div className="section-title">

          <div>

            <h3>
              Document map
            </h3>

            <p>
              Sections detected in the first pass.
            </p>

          </div>

        </div>


        {(
          proposal
            .document
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

                }

                %

              </strong>

            </div>

          )
        )}

      </div>


      <div className="panel">

        <h3>
          Potential technical claims
        </h3>


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
                {index + 1}
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
  upload,
}) {

  return (

    <section className="page">

      <div className="section-title">

        <div>

          <h3>
            Award landscape
          </h3>

          <p>
            Build a corpus of previous projects.
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
            e =>
              upload(
                e.target.files?.[0]
              )
          }

        />

      </label>


      <div className="panel">

        <h3>
          Loaded corpus
        </h3>


        {!awards.length && (

          <p className="muted">
            No award documents loaded.
          </p>

        )}


        {awards.map(
          (
            award,
            index
          ) => (

            <div
              className="file-row"
              key={
                `${award.filename}-${index}`
              }
            >

              <FileText
                size={16}
              />

              <span>
                {award.filename}
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

  busy,

  search,

}) {

  const [

    query,
    setQuery

  ] = useState(

    proposal
      ?.document
      ?.title

    ||

    ""

  );


  return (

    <section className="page">

      <div className="section-title">

        <div>

          <h3>
            Research & IP
          </h3>

          <p>
            Search papers and patent databases.
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
            e =>
              setQuery(
                e.target.value
              )
          }

          onKeyDown={
            e => {

              if (
                e.key === "Enter"
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
            search(query)
          }

          disabled={
            busy
          }

        >

          {busy

            ? <Loader2
                className="spin"
                size={16}
              />

            : <Search
                size={16}
              />

          }

          Search

        </button>

      </div>


      <div className="source-links">

        {[
          [
            "Google Scholar",
            `https://scholar.google.com/scholar?q=${encodeURIComponent(query || "water technology")}`
          ],

          [
            "Google Patents",
            `https://patents.google.com/?q=${encodeURIComponent(query || "water technology")}`
          ],

          [
            "Semantic Scholar",
            `https://www.semanticscholar.org/search?q=${encodeURIComponent(query || "water technology")}`
          ],

          [
            "WIPO PATENTSCOPE",
            `https://patentscope.wipo.int/search/en/result.jsf?query=${encodeURIComponent(query || "water technology")}`
          ],

          [
            "USPTO",
            "https://ppubs.uspto.gov/pubwebapp/static/pages/landing.html"
          ],

        ].map(
          ([name, url]) => (

            <a
              key={name}
              href={url}
              target="_blank"
              rel="noreferrer"
            >

              {name}

              <ArrowUpRight
                size={13}
              />

            </a>

          )
        )}

      </div>


      <div className="panel">

        <div className="section-title">

          <div>

            <h3>
              Literature
            </h3>

            <p>
              OpenAlex + Crossref
            </p>

          </div>

          <span className="chip">
            {research.length}
          </span>

        </div>


        {!research.length && (

          <p className="muted">
            No results yet.
          </p>

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

                <ArrowUpRight
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
        item => [
          item,
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
        sum,
        value
      ) =>

        sum +
        Number(value),

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
            Preliminary scoring only.
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

          {average.toFixed(2)}

          <small>
            / 5
          </small>

        </strong>


        <div className="score-bar">

          <span
            style={{
              width:
                `${average / 5 * 100}%`
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


export default App;
