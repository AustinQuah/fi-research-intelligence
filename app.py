import os
import asyncio
import tempfile
from pathlib import Path
from urllib.parse import quote

import httpx
from nicegui import ui, run


APP_TITLE = "FI Research Intelligence"


# ============================================================
# COLOURS
# ============================================================

ui.colors(
    primary="#0EA5E9",
    secondary="#38BDF8",
    accent="#0284C7",
    positive="#10B981",
    warning="#F59E0B",
    negative="#EF4444",
)

ui.query("body").classes(
    "bg-sky-50 text-slate-900"
)


# ============================================================
# DOCUMENT READING
# ============================================================

def read_pdf(path: str) -> dict:
    import pymupdf

    doc = pymupdf.open(path)

    pages = []
    visual_pages = []

    total_pages = len(doc)

    for page_number, page in enumerate(doc, 1):

        # Fast native PDF text extraction.
        text = page.get_text("text") or ""

        pages.append(
            f"[PAGE {page_number}]\n{text}"
        )

        # IMPORTANT:
        # Do NOT inspect every page's embedded images here.
        #
        # page.get_images(full=True) was unnecessary work
        # during the initial upload pass.
        #
        # For now, only flag suspiciously text-light pages.
        if len(text.strip()) < 250:
            visual_pages.append(page_number)

    doc.close()

    return {
        "text": "\n\n".join(pages),
        "pages": total_pages,
        "visual_pages": visual_pages,
    }


def read_docx(path: str) -> dict:
    from docx import Document

    doc = Document(path)

    parts = []

    for paragraph in doc.paragraphs:

        text = paragraph.text.strip()

        if text:
            parts.append(text)

    for table in doc.tables:

        for row in table.rows:

            parts.append(
                " | ".join(
                    cell.text.strip()
                    for cell in row.cells
                )
            )

    return {
        "text": "\n".join(parts),
        "pages": None,
        "visual_pages": [],
    }


def read_text(path: str) -> dict:

    return {
        "text": Path(path).read_text(
            encoding="utf-8",
            errors="ignore",
        ),
        "pages": None,
        "visual_pages": [],
    }


def read_document(
    path: str,
    filename: str,
) -> dict:

    suffix = Path(
        filename
    ).suffix.lower()

    if suffix == ".pdf":

        return read_pdf(path)

    if suffix == ".docx":

        return read_docx(path)

    if suffix in {".txt", ".md"}:

        return read_text(path)

    raise ValueError(
        "Supported formats are PDF, DOCX, TXT and MD."
    )


# ============================================================
# PROVISIONAL DOCUMENT UNDERSTANDING
# ============================================================

def analyse_document(
    text: str,
    filename: str,
    pages,
    visual_pages,
) -> dict:

    lower = text.lower()

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    title = None

    patterns = [
        r"(?:title of research project|"
        r"research project title|"
        r"proposal title|"
        r"project title)"
        r"\s*[:\-]?\s*([^\n]{8,180})"
    ]

    for pattern in patterns:

        match = __import__("re").search(
            pattern,
            text,
            __import__("re").IGNORECASE,
        )

        if match:

            title = match.group(1).strip()

            break

    # --------------------------------------------------------
    # FUNDING INITIATIVE
    # --------------------------------------------------------

    if (
        "living lab" in lower
        and "water" in lower
    ):

        funding_initiative = (
            "Living Lab (Water)"
        )

    elif (
        "industrial water solutions"
        in lower
        or "wafer fab" in lower
    ):

        funding_initiative = (
            "Industrial Water Solutions (IWS)"
        )

    elif (
        "municipal water" in lower
        or "mwtd" in lower
    ):

        funding_initiative = (
            "Municipal Water: "
            "Technology Development (MWTD)"
        )

    elif (
        "competitive funding for water research"
        in lower
    ):

        funding_initiative = (
            "Competitive Funding "
            "for Water Research"
        )

    else:

        funding_initiative = None

    # --------------------------------------------------------
    # DOCUMENT TYPE
    # --------------------------------------------------------

    if (
        "funding initiative" in lower
        and "desired outcomes" in lower
    ):

        document_type = (
            "FI / programme paper"
        )

    elif (
        "project proposal" in lower
        or "scientific abstract" in lower
    ):

        document_type = (
            "Individual R&D proposal"
        )

    else:

        document_type = "Unknown"

    # --------------------------------------------------------
    # SECTIONS
    # --------------------------------------------------------

    section_names = [

        "Scientific Abstract",
        "Problem Statement",
        "Research Objectives",
        "Technical KPIs",
        "Methodology",
        "Landscape Scan",
        "Innovativeness",
        "Commercialisation",
        "Milestones",
        "Budget",
        "Impact",
        "TRL",

    ]

    sections = []

    for section in section_names:

        if section.lower() in lower:

            sections.append({

                "name":
                    section,

                "confidence":
                    0.50,

            })

    # --------------------------------------------------------
    # POTENTIAL CLAIMS
    # --------------------------------------------------------

    claims = []

    for line in text.splitlines():

        line = line.strip()

        if len(line) < 40:

            continue

        if __import__("re").search(

            r"novel|innovative|"
            r"improv|increase|"
            r"reduce|demonstrat|"
            r"achiev|target|"
            r"performance",

            line,

            __import__("re").IGNORECASE,

        ):

            claims.append(line)

        if len(claims) >= 10:

            break

    return {

        "document": {

            "filename":
                filename,

            "title":
                title,

            "funding_initiative":
                funding_initiative,

            "document_type":
                document_type,

            "pages":
                pages,

            "visual_pages":
                visual_pages,

            "sections":
                sections,

        },

        "understanding": {

            "problem":
                None,

            "technology":
                None,

            "baseline":
                None,

            "proposed_solution":
                None,

            "novelty_claims":
                [],

            "trl_start":
                None,

            "trl_target":
                None,

            "prior_projects":
                [],

        },

        "claims":
            claims,

        "kpis":
            [],

        "review_flags": [

            {

                "severity":
                    "Review",

                "title":
                    "Provisional interpretation",

                "detail":
                    (
                        "The document is parsed and "
                        "structured, but a full semantic "
                        "AI layer has not yet been connected."
                    ),

            }

        ],

    }


# ============================================================
# OPENALEX
# ============================================================

async def search_openalex(
    query: str,
    year: int,
    limit: int,
) -> list:

    url = (

        "https://api.openalex.org/works"

        f"?search={quote(query)}"

        f"&filter=from_publication_date:"
        f"{year}-01-01"

        "&select="
        "id,title,publication_year,"
        "cited_by_count,doi,primary_location"

        f"&per-page={limit}"

    )

    headers = {

        "Accept":
            "application/json",

        "User-Agent":
            "FI-Research-Intelligence/0.1",

    }

    async with httpx.AsyncClient(

        timeout=30,

        follow_redirects=True,

        headers=headers,

    ) as client:

        for attempt in range(4):

            response = await client.get(
                url
            )

            if response.status_code == 200:

                data = response.json()

                break

            if response.status_code == 429:

                retry_after = (
                    response.headers.get(
                        "Retry-After"
                    )
                )

                try:

                    delay = (
                        float(retry_after)
                        if retry_after
                        else
                        1.5 *
                        (
                            2 ** attempt
                        )
                    )

                except ValueError:

                    delay = (
                        1.5 *
                        (
                            2 ** attempt
                        )
                    )

                await asyncio.sleep(
                    delay
                )

                continue

            response.raise_for_status()

        else:

            return []

    output = []

    for item in data.get(
        "results",
        [],
    ):

        location = (
            item.get(
                "primary_location"
            )
            or {}
        )

        output.append({

            "source":
                "OpenAlex",

            "title":
                item.get(
                    "title"
                )
                or
                "Untitled",

            "year":
                item.get(
                    "publication_year"
                ),

            "citations":
                item.get(
                    "cited_by_count",
                    0,
                ),

            "doi":
                item.get(
                    "doi"
                ),

            "url":
                location.get(
                    "landing_page_url"
                )
                or
                item.get("doi")
                or
                item.get("id"),

        })

    return output


# ============================================================
# CROSSREF
# ============================================================

async def search_crossref(
    query: str,
    year: int,
    limit: int,
) -> list:

    url = (

        "https://api.crossref.org/works"

        f"?query.bibliographic="
        f"{quote(query)}"

        f"&filter="
        f"from-pub-date:{year}-01-01"

        "&select="
        "title,published,"
        "is-referenced-by-count,"
        "DOI,URL"

        f"&rows={limit}"

    )

    headers = {

        "Accept":
            "application/json",

        "User-Agent":
            "FI-Research-Intelligence/0.1",

    }

    async with httpx.AsyncClient(

        timeout=30,

        follow_redirects=True,

        headers=headers,

    ) as client:

        response = await client.get(
            url
        )

        response.raise_for_status()

        data = response.json()

    results = []

    for item in (

        data

        .get(
            "message",
            {}
        )

        .get(
            "items",
            []
        )

    ):

        doi = item.get(
            "DOI"
        )

        dates = (

            item

            .get(
                "published",
                {}
            )

            .get(
                "date-parts",
                [[None]]
            )

        )

        results.append({

            "source":
                "Crossref",

            "title":
                (
                    item.get(
                        "title"
                    )
                    or
                    ["Untitled"]
                )[0],

            "year":
                (
                    dates[0][0]
                    if dates
                    else None
                ),

            "citations":
                item.get(
                    "is-referenced-by-count",
                    0,
                ),

            "doi":
                doi,

            "url":
                item.get("URL")
                or
                (
                    f"https://doi.org/{doi}"
                    if doi
                    else None
                ),

        })

    return results


# ============================================================
# DIRECT RESEARCH SOURCES
# ============================================================

def research_links(
    query: str,
) -> list:

    encoded = quote(
        query
    )

    return [

        (
            "Google Scholar",
            (
                "https://scholar.google.com/"
                f"scholar?q={encoded}"
            ),
        ),

        (
            "Google Patents",
            (
                "https://patents.google.com/"
                f"?q={encoded}"
            ),
        ),

        (
            "Semantic Scholar",
            (
                "https://www.semanticscholar.org/"
                f"search?q={encoded}"
            ),
        ),

        (
            "WIPO PATENTSCOPE",
            (
                "https://patentscope.wipo.int/"
                "search/en/result.jsf"
                f"?query={encoded}"
            ),
        ),

        (
            "USPTO Patent Search",
            (
                "https://ppubs.uspto.gov/"
                "pubwebapp/static/pages/"
                "landing.html"
            ),
        ),

    ]


# ============================================================
# APPLICATION
# ============================================================

def main():

    # Per-user state.

    state = {

        "proposal":
            None,

        "papers":
            [],

        "awards":
            [],

    }


    # ========================================================
    # REFRESHABLE METRICS
    # ========================================================

    @ui.refreshable
    def metric_cards():

        proposal = state[
            "proposal"
        ]

        values = [

            (
                "Claims",

                len(
                    proposal.get(
                        "claims",
                        [],
                    )
                )
                if proposal
                else 0,

                "fact_check",

            ),

            (
                "Sections",

                len(
                    proposal
                    .get(
                        "document",
                        {}
                    )
                    .get(
                        "sections",
                        []
                    )
                )
                if proposal
                else 0,

                "view_list",

            ),

            (
                "Research",

                len(
                    state[
                        "papers"
                    ]
                ),

                "science",

            ),

            (
                "Awards",

                len(
                    state[
                        "awards"
                    ]
                ),

                "workspace_premium",

            ),

        ]


        with ui.grid(
            columns=4
        ).classes(
            "w-full gap-4"
        ):

            for (

                label,
                value,
                icon,

            ) in values:

                with ui.card().classes(

                    "w-full "
                    "p-5 "
                    "bg-white "
                    "border "
                    "border-sky-100 "
                    "shadow-none "
                    "rounded-2xl"

                ):

                    with ui.row().classes(

                        "w-full "
                        "items-center "
                        "justify-between"

                    ):

                        ui.label(
                            label
                        ).classes(
                            "text-sm "
                            "text-slate-500"
                        )

                        ui.icon(
                            icon,
                            color="sky-500",
                        )

                    ui.label(
                        str(value)
                    ).classes(

                        "text-3xl "
                        "font-semibold "
                        "text-slate-800"

                    )


    # ========================================================
    # OVERVIEW
    # ========================================================

    @ui.refreshable
    def proposal_summary():

        proposal = state[
            "proposal"
        ]

        if proposal is None:

            with ui.card().classes(

                "w-full "
                "p-6 "
                "bg-white "
                "border "
                "border-sky-100 "
                "shadow-none "
                "rounded-2xl"

            ):

                ui.icon(
                    "description",
                    size="2.5rem",
                    color="sky-300",
                )

                ui.label(
                    "No proposal loaded"
                ).classes(
                    "text-lg font-semibold"
                )

                ui.label(
                    "Upload a proposal to start."
                ).classes(
                    "text-slate-500"
                )

            return

        d = proposal[
            "document"
        ]

        u = proposal[
            "understanding"
        ]

        with ui.card().classes(

            "w-full "
            "p-6 "
            "bg-white "
            "border "
            "border-sky-100 "
            "shadow-none "
            "rounded-2xl"

        ):

            ui.label(

                d.get(
                    "title"
                )

                or

                "Title not confidently determined"

            ).classes(

                "text-2xl "
                "font-semibold"

            )

            with ui.row().classes(
                "gap-2 mt-2"
            ):

                ui.chip(

                    d.get(
                        "funding_initiative"
                    )

                    or

                    "FI not determined",

                    icon="account_balance",

                    color="primary",

                )

                ui.chip(

                    d.get(
                        "document_type"
                    )

                    or
                    "Unknown",

                    icon="description",

                )

            ui.separator().classes(
                "my-4"
            )

            with ui.grid(
                columns=2
            ).classes(
                "w-full gap-6"
            ):

                with ui.column():

                    ui.label(
                        "Problem"
                    ).classes(

                        "text-xs "
                        "font-semibold "
                        "uppercase "
                        "text-slate-400"

                    )

                    ui.label(

                        u.get(
                            "problem"
                        )

                        or

                        "Not determined"

                    ).classes(
                        "text-slate-700"
                    )

                with ui.column():

                    ui.label(
                        "Technology"
                    ).classes(

                        "text-xs "
                        "font-semibold "
                        "uppercase "
                        "text-slate-400"

                    )

                    ui.label(

                        u.get(
                            "technology"
                        )

                        or

                        "Not determined"

                    ).classes(
                        "text-slate-700"
                    )

            flags = proposal.get(
                "review_flags",
                []
            )

            if flags:

                ui.separator().classes(
                    "my-4"
                )

                ui.label(
                    "Review attention"
                ).classes(
                    "font-semibold"
                )

                for flag in flags:

                    with ui.row().classes(
                        "items-start gap-2"
                    ):

                        ui.badge(
                            flag.get(
                                "severity",
                                "Review"
                            ),
                            color="warning",
                        )

                        ui.label(
                            flag.get(
                                "title",
                                "Review flag"
                            )
                        ).classes(
                            "font-medium"
                        )

                        ui.label(
                            flag.get(
                                "detail",
                                ""
                            )
                        ).classes(
                            "text-slate-500"
                        )


    # ========================================================
    # DOCUMENT
    # ========================================================

    @ui.refreshable
    def document_details():

        proposal = state[
            "proposal"
        ]

        if proposal is None:

            ui.label(
                "Upload a proposal first."
            ).classes(
                "text-slate-400"
            )

            return

        u = proposal[
            "understanding"
        ]

        with ui.grid(
            columns=2
        ).classes(
            "w-full gap-4"
        ):

            fields = [

                (
                    "Problem",
                    "problem",
                ),

                (
                    "Technology",
                    "technology",
                ),

                (
                    "Baseline",
                    "baseline",
                ),

                (
                    "Proposed solution",
                    "proposed_solution",
                ),

            ]

            for (
                label,
                key,
            ) in fields:

                with ui.card().classes(

                    "w-full "
                    "border "
                    "border-sky-100 "
                    "shadow-none "
                    "rounded-2xl"

                ):

                    ui.label(
                        label
                    ).classes(
                        "font-semibold"
                    )

                    ui.label(

                        u.get(
                            key
                        )

                        or

                        "Not determined"

                    ).classes(
                        "text-slate-600"
                    )


            with ui.card().classes(

                "w-full "
                "border "
                "border-sky-100 "
                "shadow-none "
                "rounded-2xl"

            ):

                ui.label(
                    "Novelty claims"
                ).classes(
                    "font-semibold"
                )

                novelty = u.get(
                    "novelty_claims",
                    []
                )

                if not novelty:

                    ui.label(
                        "None confidently identified."
                    ).classes(
                        "text-slate-400"
                    )

                for item in novelty:

                    ui.label(
                        "• " + str(item)
                    )


            with ui.card().classes(

                "w-full "
                "border "
                "border-sky-100 "
                "shadow-none "
                "rounded-2xl"

            ):

                ui.label(
                    "Technology readiness"
                ).classes(
                    "font-semibold"
                )

                start = u.get(
                    "trl_start"
                )

                target = u.get(
                    "trl_target"
                )

                if start is None:

                    ui.label(
                        "Not determined"
                    ).classes(
                        "text-slate-400"
                    )

                else:

                    ui.label(
                        f"TRL {start} → {target}"
                    ).classes(

                        "text-lg "
                        "font-semibold "
                        "text-sky-600"

                    )

        ui.separator().classes(
            "my-6"
        )

        ui.label(
            "Document map"
        ).classes(
            "text-xl font-semibold"
        )

        rows = [

            {
                "name":
                    x.get(
                        "name"
                    ),

                "confidence":
                    f"{round((x.get('confidence') or 0) * 100)}%",

            }

            for x in proposal[
                "document"
            ].get(
                "sections",
                []
            )

        ]

        ui.table(

            columns=[
                {
                    "name":
                        "name",

                    "label":
                        "SECTION",

                    "field":
                        "name",
                },

                {
                    "name":
                        "confidence",

                    "label":
                        "CONFIDENCE",

                    "field":
                        "confidence",
                },
            ],

            rows=rows,

        ).props(
            "flat bordered"
        ).classes(
            "w-full"
        )

        ui.separator().classes(
            "my-6"
        )

        ui.label(
            "Potential claims"
        ).classes(
            "text-xl font-semibold"
        )

        for claim in proposal.get(
            "claims",
            []
        ):

            with ui.card().classes(

                "w-full "
                "border "
                "border-sky-100 "
                "shadow-none"

            ):

                ui.label(
                    str(claim)
                ).classes(
                    "text-slate-700"
                )


    # ========================================================
    # AWARDS
    # ========================================================

    @ui.refreshable
    def awards_panel():

        if not state[
            "awards"
        ]:

            ui.label(
                "No previous awards loaded."
            ).classes(
                "text-slate-400"
            )

            return

        for award in state[
            "awards"
        ]:

            with ui.card().classes(

                "w-full "
                "border "
                "border-sky-100 "
                "shadow-none"

            ):

                with ui.row().classes(
                    "items-center"
                ):

                    ui.icon(
                        "workspace_premium",
                        color="warning",
                    )

                    ui.label(
                        award
                    ).classes(
                        "font-semibold"
                    )


    # ========================================================
    # RESEARCH
    # ========================================================

    @ui.refreshable
    def research_panel():

        if not state[
            "papers"
        ]:

            with ui.card().classes(

                "w-full "
                "border "
                "border-sky-100 "
                "shadow-none "
                "rounded-2xl "
                "p-6"

            ):

                ui.icon(
                    "travel_explore",
                    size="2.5rem",
                    color="sky-300",
                )

                ui.label(
                    "No research results yet"
                ).classes(
                    "text-lg font-semibold"
                )

                ui.label(
                    "Enter a technical question "
                    "to search current literature."
                ).classes(
                    "text-slate-500"
                )

            return

        for paper in state[
            "papers"
        ]:

            with ui.card().classes(

                "w-full "
                "border "
                "border-sky-100 "
                "shadow-none "
                "rounded-2xl"

            ):

                with ui.row().classes(
                    "items-center w-full"
                ):

                    ui.badge(

                        paper[
                            "source"
                        ],

                        color=(

                            "positive"

                            if paper[
                                "source"
                            ]
                            ==
                            "OpenAlex"

                            else

                            "warning"

                        ),

                    )

                    ui.label(

                        str(
                            paper.get(
                                "year"
                            )
                            or
                            ""
                        )

                    ).classes(
                        "text-slate-400"
                    )

                    ui.space()

                    ui.label(

                        f"{paper.get('citations', 0)} citations"

                    ).classes(
                        "text-slate-400"
                    )

                ui.label(

                    paper.get(
                        "title"
                    )
                    or
                    "Untitled"

                ).classes(

                    "font-semibold "
                    "text-slate-800"

                )

                if paper.get(
                    "url"
                ):

                    ui.link(

                        "Open source ↗",

                        paper[
                            "url"
                        ],

                    ).classes(

                        "text-sky-600 "
                        "font-semibold"

                    )


    # ========================================================
    # PROPOSAL UPLOAD
    # ========================================================

    async def upload_proposal(
        event
    ):

        note = ui.notification(
            "Reading proposal...",
            spinner=True,
            timeout=None,
        )

        suffix = Path(
            event.name
        ).suffix.lower()

        try:

            content = await run.io_bound(
                event.content.read
            )

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
            ) as temp:

                temp.write(
                    content
                )

                path = temp.name

            parsed = await run.io_bound(

                read_document,

                path,

                event.name,

            )

            state[
                "proposal"
            ] = analyse_document(

                parsed[
                    "text"
                ],

                event.name,

                parsed[
                    "pages"
                ],

                parsed[
                    "visual_pages"
                ],

            )

            metric_cards.refresh()

            proposal_summary.refresh()

            document_details.refresh()

            note.message = (
                f"{event.name} loaded"
            )

            note.spinner = False

            note.type = (
                "positive"
            )

        except Exception as error:

            note.message = (
                f"Upload failed: {error}"
            )

            note.spinner = False

            note.type = (
                "negative"
            )


    # ========================================================
    # AWARD UPLOAD
    # ========================================================

    async def upload_award(
        event
    ):

        state[
            "awards"
        ].append(
            event.name
        )

        metric_cards.refresh()

        awards_panel.refresh()

        ui.notify(

            f"{event.name} added",

            type="positive",

        )


    # ========================================================
    # RESEARCH SEARCH
    # ========================================================

    async def perform_search():

        search_query = (
            query.value
            or
            ""
        ).strip()

        if not search_query:

            ui.notify(

                "Enter a research question.",

                type="warning",

            )

            return

        note = ui.notification(

            "Searching OpenAlex and Crossref...",

            spinner=True,

            timeout=None,

        )

        try:

            openalex = await search_openalex(

                search_query,

                int(
                    year.value
                ),

                int(
                    limit.value
                ),

            )

            # Avoid hammering APIs.

            await asyncio.sleep(
                0.75
            )

            crossref = await search_crossref(

                search_query,

                int(
                    year.value
                ),

                int(
                    limit.value
                ),

            )

            combined = (

                openalex

                + crossref

            )

            seen = set()

            unique = []

            for paper in combined:

                key = (

                    paper.get(
                        "doi"
                    )

                    or

                    paper.get(
                        "url"
                    )

                    or

                    paper.get(
                        "title"
                    )

                    or
                    ""

                ).lower()

                if (
                    not key
                    or
                    key in seen
                ):

                    continue

                seen.add(
                    key
                )

                unique.append(
                    paper
                )

            unique.sort(

                key=lambda item:

                    item.get(
                        "citations",
                        0,
                    ),

                reverse=True,

            )

            state[
                "papers"
            ] = unique

            metric_cards.refresh()

            research_panel.refresh()

            source_links.clear()

            with source_links:

                for name, url in research_links(
                    search_query
                ):

                    ui.link(

                        name,

                        url,

                        new_tab=True,

                    ).classes(

                        "text-sky-600 "
                        "font-semibold"

                    )

            note.message = (

                f"Found {len(unique)} "
                "research records"

            )

            note.spinner = False

            note.type = (
                "positive"
            )

        except Exception as error:

            note.message = (

                f"Research search failed: "
                f"{error}"

            )

            note.spinner = False

            note.type = (
                "negative"
            )


    # ========================================================
    # HEADER
    # ========================================================

    with ui.header().classes(

        "bg-white "
        "text-slate-900 "
        "border-b "
        "border-sky-100 "
        "px-6 py-3"

    ):

        with ui.row().classes(
            "items-center gap-3"
        ):

            with ui.element(
                "div"
            ).classes(

                "w-9 h-9 "
                "rounded-xl "
                "bg-sky-500 "
                "flex "
                "items-center "
                "justify-center"

            ):

                ui.icon(
                    "water",
                    color="white",
                )

            with ui.column().classes(
                "gap-0"
            ):

                ui.label(
                    APP_TITLE
                ).classes(
                    "text-base "
                    "font-semibold"
                )

                ui.label(
                    "Proposal research workspace"
                ).classes(
                    "text-xs "
                    "text-slate-400"
                )

        ui.space()

        ui.badge(
            "BETA",
            color="primary",
        )


    # ========================================================
    # NAVIGATION
    # ========================================================

    with ui.tabs() as tabs:

        overview = ui.tab(
            "Overview",
            icon="dashboard",
        )

        documents = ui.tab(
            "Document",
            icon="description",
        )

        awards_tab = ui.tab(
            "Awards",
            icon="workspace_premium",
        )

        research_tab = ui.tab(
            "Research & IP",
            icon="science",
        )

        review_tab = ui.tab(
            "Reviewer",
            icon="fact_check",
        )


    with ui.tab_panels(

        tabs,

        value=overview,

    ).classes(

        "w-full "
        "max-w-6xl "
        "mx-auto "
        "bg-transparent "
        "py-6"

    ):

        # ====================================================
        # OVERVIEW
        # ====================================================

        with ui.tab_panel(
            overview
        ):

            ui.label(
                "Research with context."
            ).classes(

                "text-4xl "
                "font-semibold "
                "tracking-tight"

            )

            ui.label(
                "Understand proposals, "
                "find prior work, and "
                "surface the evidence "
                "that matters."
            ).classes(

                "text-lg "
                "text-slate-500 "
                "max-w-2xl"

            )

            ui.upload(

                on_upload=
                    upload_proposal,

                auto_upload=
                    True,

                max_file_size=
                    30_000_000,

            ).props(

                "accept=.pdf,.docx,.txt,.md"

            ).classes(

                "w-full mt-6"

            )

            metric_cards()

            proposal_summary()


        # ====================================================
        # DOCUMENT
        # ====================================================

        with ui.tab_panel(
            documents
        ):

            ui.label(
                "Document understanding"
            ).classes(

                "text-3xl "
                "font-semibold"

            )

            ui.label(
                "A structured view of "
                "the proposal."
            ).classes(
                "text-slate-500"
            )

            document_details()


        # ====================================================
        # AWARDS
        # ====================================================

        with ui.tab_panel(
            awards_tab
        ):

            ui.label(
                "Award landscape"
            ).classes(

                "text-3xl "
                "font-semibold"

            )

            ui.label(
                "Load previous awards "
                "or proposals."
            ).classes(
                "text-slate-500"
            )

            ui.upload(

                on_upload=
                    upload_award,

                multiple=
                    True,

                auto_upload=
                    True,

                max_files=
                    50,

            ).props(

                "accept=.pdf,.docx,.txt,.md"

            ).classes(

                "w-full mt-6"

            )

            awards_panel()


        # ====================================================
        # RESEARCH
        # ====================================================

        with ui.tab_panel(
            research_tab
        ):

            ui.label(
                "Research intelligence"
            ).classes(

                "text-3xl "
                "font-semibold"

            )

            ui.label(
                "Search actual literature "
                "records and jump directly "
                "to patent sources."
            ).classes(
                "text-slate-500"
            )

            with ui.card().classes(

                "w-full "
                "mt-6 "
                "border "
                "border-sky-100 "
                "shadow-none"

            ):

                query = ui.input(
                    "Technology, claim "
                    "or research question"
                ).classes(
                    "w-full"
                )

                with ui.row().classes(
                    "items-end gap-3"
                ):

                    year = ui.number(
                        "From year",
                        value=2020,
                        min=1900,
                        max=2100,
                    )

                    limit = ui.number(
                        "Results",
                        value=10,
                        min=1,
                        max=25,
                    )

                    ui.button(

                        "Search",

                        icon="search",

                        on_click=
                            perform_search,

                    ).props(

                        "color=primary "
                        "unelevated "
                        "no-caps"

                    )

            source_links = ui.row().classes(

                "gap-5 "
                "mt-3 "
                "flex-wrap"

            )

            research_panel()


        # ====================================================
        # REVIEWER
        # ====================================================

        with ui.tab_panel(
            review_tab
        ):

            ui.label(
                "Human reviewer"
            ).classes(

                "text-3xl "
                "font-semibold"

            )

            ui.label(
                "AI supplies evidence; "
                "the reviewer makes "
                "the decision."
            ).classes(
                "text-slate-500"
            )

            criteria = [

                "Science & technology",

                "Impact / national benefit",

                "Management & delivery",

                "Budget / value",

            ]

            sliders = []

            with ui.grid(
                columns=2
            ).classes(

                "w-full "
                "gap-4 "
                "mt-6"

            ):

                for criterion in criteria:

                    with ui.card().classes(

                        "w-full "
                        "border "
                        "border-sky-100 "
                        "shadow-none"

                    ):

                        ui.label(
                            criterion
                        ).classes(
                            "font-semibold"
                        )

                        slider = ui.slider(

                            min=1,

                            max=5,

                            step=1,

                            value=4,

                        ).classes(
                            "w-full"
                        )

                        ui.label().bind_text_from(

                            slider,

                            "value",

                            backward=lambda value:

                                f"Score: "
                                f"{value}/5",

                        )

                        sliders.append(
                            slider
                        )

            overall = ui.label(
                "Overall: 4.00 / 5"
            ).classes(

                "text-3xl "
                "font-semibold "
                "text-sky-600 "
                "mt-4"

            )

            def update_score():

                values = [

                    float(
                        slider.value
                        or 0
                    )

                    for slider
                    in sliders

                ]

                score = (

                    sum(values)
                    / len(values)

                    if values
                    else 0

                )

                overall.set_text(

                    f"Overall: "
                    f"{score:.2f} / 5"

                )

            for slider in sliders:

                slider.on_value_change(
                    update_score
                )


if __name__ == "__main__":

    main()


# ============================================================
# RENDER
# ============================================================

ui.run(

    host="0.0.0.0",

    port=int(

        os.environ.get(

            "PORT",

            "10000",

        )

    ),

    title=APP_TITLE,

    favicon="🔬",

    reload=False,

    show=False,

)
