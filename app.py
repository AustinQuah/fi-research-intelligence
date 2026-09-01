import asyncio
import os
import tempfile
from pathlib import Path
from urllib.parse import quote

from nicegui import ui, run

from services.documents import (
    parse_uploaded_document,
    quick_understanding,
)
from services.research import research_pass
from services.awards import compare_award_corpus
from services.intelligence import run_ai_understanding


APP_TITLE = "FI Research Intelligence"

ui.colors(
    primary="#0EA5E9",
    secondary="#38BDF8",
    accent="#0284C7",
    positive="#10B981",
    warning="#F59E0B",
    negative="#EF4444",
)

ui.query("body").classes("bg-sky-50")


def main() -> None:

    # ========================================================
    # USER SESSION STATE
    # ========================================================

    state = {
        "proposal": None,
        "awards": [],
        "research": [],
        "ai": None,
        "busy": False,
        "award_result": [],
    }

    # ========================================================
    # OVERVIEW
    # ========================================================

    @ui.refreshable
    def overview_panel() -> None:

        proposal = state["proposal"]

        with ui.column().classes(
            "w-full max-w-6xl mx-auto p-6 gap-6"
        ):

            with ui.card().classes(
                "w-full p-7 "
                "bg-white "
                "border border-sky-100 "
                "shadow-none "
                "rounded-2xl"
            ):

                ui.label(
                    "Research with context."
                ).classes(
                    "text-4xl font-semibold tracking-tight"
                )

                ui.label(
                    "Understand proposals, "
                    "find prior work, and "
                    "surface the evidence that matters."
                ).classes(
                    "text-lg text-slate-500 max-w-3xl"
                )

            with ui.grid(columns=4).classes(
                "w-full gap-4"
            ):

                cards = [
                    (
                        "Proposal",
                        "Loaded" if proposal else "None",
                        "description",
                        "primary",
                    ),
                    (
                        "Awards",
                        len(state["awards"]),
                        "workspace_premium",
                        "warning",
                    ),
                    (
                        "Research",
                        len(state["research"]),
                        "science",
                        "positive",
                    ),
                    (
                        "AI",
                        "Ready" if state["ai"] else "Not run",
                        "auto_awesome",
                        "secondary",
                    ),
                ]

                for label, value, icon, color in cards:

                    with ui.card().classes(
                        "w-full p-5 "
                        "bg-white "
                        "border border-sky-100 "
                        "shadow-none "
                        "rounded-2xl"
                    ):

                        with ui.row().classes(
                            "w-full items-center justify-between"
                        ):

                            ui.label(
                                label
                            ).classes(
                                "text-sm text-slate-500"
                            )

                            ui.icon(
                                icon,
                                color=color,
                            )

                        ui.label(
                            str(value)
                        ).classes(
                            "text-2xl font-semibold text-slate-800"
                        )

            with ui.card().classes(
                "w-full p-6 "
                "bg-white "
                "border border-sky-100 "
                "shadow-none "
                "rounded-2xl"
            ):

                ui.label(
                    "Proposal"
                ).classes(
                    "text-xl font-semibold"
                )

                if not proposal:

                    ui.label(
                        "Upload a proposal from the Document tab."
                    ).classes(
                        "text-slate-500"
                    )

                else:

                    document = proposal.get(
                        "document",
                        {}
                    )

                    understanding = proposal.get(
                        "understanding",
                        {}
                    )

                    ui.label(
                        document.get("title")
                        or "Title not confidently determined"
                    ).classes(
                        "text-2xl font-semibold mt-2"
                    )

                    with ui.row().classes(
                        "gap-2 mt-2"
                    ):

                        ui.chip(
                            document.get(
                                "funding_initiative"
                            )
                            or "FI not determined",
                            color="primary",
                        )

                        ui.chip(
                            document.get(
                                "document_type"
                            )
                            or "Unknown"
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
                                "uppercase "
                                "font-semibold "
                                "text-slate-400"
                            )

                            ui.label(
                                understanding.get(
                                    "problem"
                                )
                                or
                                "Not yet determined"
                            ).classes(
                                "text-slate-700"
                            )

                        with ui.column():

                            ui.label(
                                "Technology"
                            ).classes(
                                "text-xs "
                                "uppercase "
                                "font-semibold "
                                "text-slate-400"
                            )

                            ui.label(
                                understanding.get(
                                    "technology"
                                )
                                or
                                "Not yet determined"
                            ).classes(
                                "text-slate-700"
                            )

            if state["ai"]:

                with ui.card().classes(
                    "w-full p-6 "
                    "bg-sky-50/50 "
                    "border border-sky-100 "
                    "shadow-none "
                    "rounded-2xl"
                ):

                    ui.label(
                        "AI findings"
                    ).classes(
                        "text-xl font-semibold"
                    )

                    render_ai_findings(
                        state["ai"]
                    )

                    ui.button(
                        "Refresh AI analysis",
                        icon="auto_awesome",
                        on_click=lambda:
                            asyncio.create_task(
                                run_deeper_analysis()
                            ),
                    ).props(
                        "color=primary "
                        "unelevated "
                        "no-caps"
                    ).classes(
                        "mt-4"
                    )

            elif proposal:

                with ui.card().classes(
                    "w-full p-6 "
                    "bg-white "
                    "border border-sky-100 "
                    "shadow-none "
                    "rounded-2xl"
                ):

                    ui.label(
                        "Deeper AI analysis"
                    ).classes(
                        "text-xl font-semibold"
                    )

                    ui.label(
                        "The fast pass is complete. "
                        "Run the deeper AI stage when your "
                        "AI provider is configured."
                    ).classes(
                        "text-slate-500"
                    )

                    ui.button(
                        "Run AI understanding",
                        icon="auto_awesome",
                        on_click=lambda:
                            asyncio.create_task(
                                run_deeper_analysis()
                            ),
                    ).props(
                        "color=primary "
                        "unelevated "
                        "no-caps"
                    ).classes(
                        "mt-4"
                    )


    def render_ai_findings(
        ai: dict
    ) -> None:

        fields = [
            (
                "Problem",
                ai.get("problem"),
            ),
            (
                "Technology",
                ai.get("technology"),
            ),
            (
                "Baseline",
                ai.get("baseline"),
            ),
            (
                "Proposed solution",
                ai.get("proposed_solution"),
            ),
            (
                "TRL",
                ai.get("trl"),
            ),
            (
                "Commercialisation",
                ai.get("commercialisation"),
            ),
        ]

        with ui.grid(columns=2).classes(
            "w-full gap-4 mt-3"
        ):

            for label, value in fields:

                with ui.card().classes(
                    "w-full p-4 "
                    "bg-white "
                    "border border-sky-100 "
                    "shadow-none"
                ):

                    ui.label(
                        label
                    ).classes(
                        "text-xs uppercase "
                        "font-semibold text-slate-400"
                    )

                    ui.label(
                        value or "Not determined"
                    ).classes(
                        "text-slate-700 mt-1"
                    )

        flags = ai.get(
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

                with ui.card().classes(
                    "w-full "
                    "p-4 "
                    "bg-amber-50 "
                    "border border-amber-100 "
                    "shadow-none"
                ):

                    ui.label(
                        flag.get(
                            "title",
                            "Review flag",
                        )
                    ).classes(
                        "font-semibold"
                    )

                    ui.label(
                        flag.get(
                            "detail",
                            "",
                        )
                    ).classes(
                        "text-slate-600"
                    )


    # ========================================================
    # DOCUMENT TAB
    # ========================================================

    @ui.refreshable
    def document_panel() -> None:

        proposal = state["proposal"]

        with ui.column().classes(
            "w-full max-w-6xl mx-auto p-6 gap-5"
        ):

            ui.label(
                "Document understanding"
            ).classes(
                "text-3xl font-semibold"
            )

            ui.label(
                "Fast document structure first, deeper AI second."
            ).classes(
                "text-slate-500"
            )

            if not proposal:

                ui.card().classes(
                    "fi-card w-full"
                )

                ui.label(
                    "No proposal loaded."
                ).classes(
                    "text-slate-500"
                )

                return

            document = proposal.get(
                "document",
                {}
            )

            understanding = proposal.get(
                "understanding",
                {}
            )

            with ui.grid(columns=2).classes(
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

                for label, key in fields:

                    with ui.card().classes(
                        "w-full p-5 "
                        "bg-white "
                        "border border-sky-100 "
                        "shadow-none "
                        "rounded-2xl"
                    ):

                        ui.label(
                            label
                        ).classes(
                            "font-semibold"
                        )

                        ui.label(
                            understanding.get(
                                key
                            )
                            or
                            "Not determined"
                        ).classes(
                            "text-slate-600 mt-2"
                        )

                with ui.card().classes(
                    "w-full p-5 "
                    "bg-white "
                    "border border-sky-100 "
                    "shadow-none "
                    "rounded-2xl"
                ):

                    ui.label(
                        "Novelty"
                    ).classes(
                        "font-semibold"
                    )

                    novelty = understanding.get(
                        "novelty_claims",
                        []
                    )

                    if not novelty:

                        ui.label(
                            "No novelty claims "
                            "confidently extracted yet."
                        ).classes(
                            "text-slate-400"
                        )

                    for item in novelty:

                        ui.label(
                            "• " + str(item)
                        ).classes(
                            "text-slate-600"
                        )

                with ui.card().classes(
                    "w-full p-5 "
                    "bg-white "
                    "border border-sky-100 "
                    "shadow-none "
                    "rounded-2xl"
                ):

                    ui.label(
                        "TRL"
                    ).classes(
                        "font-semibold"
                    )

                    start = understanding.get(
                        "trl_start"
                    )

                    target = understanding.get(
                        "trl_target"
                    )

                    ui.label(
                        (
                            f"TRL {start} → {target}"
                        )
                        if start is not None
                        else "Not determined"
                    ).classes(
                        "text-lg "
                        "font-semibold "
                        "text-sky-600"
                    )

            with ui.card().classes(
                "w-full p-5 "
                "bg-white "
                "border border-sky-100 "
                "shadow-none "
                "rounded-2xl"
            ):

                ui.label(
                    "Document map"
                ).classes(
                    "text-xl font-semibold"
                )

                rows = [
                    {
                        "section": item.get("name"),
                        "confidence": (
                            f"{round((item.get('confidence') or 0) * 100)}%"
                        ),
                    }
                    for item in document.get(
                        "sections",
                        []
                    )
                ]

                ui.table(
                    columns=[
                        {
                            "name": "section",
                            "label": "SECTION",
                            "field": "section",
                        },
                        {
                            "name": "confidence",
                            "label": "CONFIDENCE",
                            "field": "confidence",
                        },
                    ],
                    rows=rows,
                ).props(
                    "flat bordered"
                ).classes(
                    "w-full"
                )

            with ui.card().classes(
                "w-full p-5 "
                "bg-white "
                "border border-sky-100 "
                "shadow-none "
                "rounded-2xl"
            ):

                ui.label(
                    "Potential technical claims"
                ).classes(
                    "text-xl font-semibold"
                )

                claims = proposal.get(
                    "claims",
                    []
                )

                if not claims:

                    ui.label(
                        "No claim signals detected."
                    ).classes(
                        "text-slate-400"
                    )

                for claim in claims:

                    ui.label(
                        "• " + str(claim)
                    ).classes(
                        "text-slate-700"
                    )


    # ========================================================
    # AWARDS
    # ========================================================

    @ui.refreshable
    def awards_panel() -> None:

        with ui.column().classes(
            "w-full max-w-6xl mx-auto p-6 gap-5"
        ):

            ui.label(
                "Award landscape"
            ).classes(
                "text-3xl font-semibold"
            )

            ui.label(
                "Load previous projects and compare them "
                "against the current proposal."
            ).classes(
                "text-slate-500"
            )

            ui.upload(
                on_upload=lambda event:
                    asyncio.create_task(
                        handle_award_upload(event)
                    ),
                multiple=True,
                auto_upload=True,
                max_files=100,
                max_file_size=50_000_000,
            ).props(
                "accept=.pdf,.docx,.txt,.md"
            ).classes(
                "w-full"
            )

            if not state["awards"]:

                ui.label(
                    "No award corpus loaded."
                ).classes(
                    "text-slate-400"
                )

            else:

                with ui.card().classes(
                    "w-full "
                    "bg-white "
                    "border border-sky-100 "
                    "shadow-none "
                    "rounded-2xl"
                ):

                    ui.label(
                        f"{len(state['awards'])} award documents loaded"
                    ).classes(
                        "text-lg font-semibold"
                    )

                    for award in state["awards"]:

                        with ui.row().classes(
                            "items-center gap-2"
                        ):

                            ui.icon(
                                "workspace_premium",
                                color="warning",
                            )

                            ui.label(
                                award["filename"]
                            )

                if state["proposal"]:

                    ui.button(
                        "Compare against current proposal",
                        icon="compare_arrows",
                        on_click=lambda:
                            asyncio.create_task(
                                run_award_comparison()
                            ),
                    ).props(
                        "color=primary "
                        "unelevated "
                        "no-caps"
                    )

                if state["award_result"]:

                    with ui.card().classes(
                        "w-full "
                        "bg-white "
                        "border border-sky-100 "
                        "shadow-none "
                        "rounded-2xl"
                    ):

                        ui.label(
                            "Preliminary relationships"
                        ).classes(
                            "text-xl font-semibold"
                        )

                        for item in state[
                            "award_result"
                        ]:

                            with ui.card().classes(
                                "w-full "
                                "p-4 "
                                "bg-slate-50 "
                                "shadow-none"
                            ):

                                with ui.row().classes(
                                    "items-center"
                                ):

                                    ui.label(
                                        item["filename"]
                                    ).classes(
                                        "font-semibold"
                                    )

                                    ui.space()

                                    ui.badge(
                                        item["relationship"],
                                        color="warning",
                                    )

                                ui.label(
                                    item["reason"]
                                ).classes(
                                    "text-slate-600 mt-2"
                                )


    # ========================================================
    # RESEARCH
    # ========================================================

    @ui.refreshable
    def research_panel() -> None:

        with ui.column().classes(
            "w-full max-w-6xl mx-auto p-6 gap-5"
        ):

            ui.label(
                "Research & IP"
            ).classes(
                "text-3xl font-semibold"
            )

            ui.label(
                "Search actual literature records and "
                "open proposal-specific patent routes."
            ).classes(
                "text-slate-500"
            )

            with ui.card().classes(
                "w-full "
                "bg-white "
                "border border-sky-100 "
                "shadow-none "
                "rounded-2xl"
            ):

                with ui.row().classes(
                    "w-full items-end gap-3"
                ):

                    research_query = ui.input(
                        "Research question / technical claim"
                    ).classes(
                        "grow"
                    )

                    from_year = ui.number(
                        "From year",
                        value=2020,
                        min=1900,
                        max=2100,
                    )

                    result_limit = ui.number(
                        "Results",
                        value=10,
                        min=1,
                        max=25,
                    )

                    async def search():

                        if not research_query.value:

                            ui.notify(
                                "Enter a research question.",
                                type="warning",
                            )

                            return

                        note = ui.notification(
                            "Searching research...",
                            spinner=True,
                            timeout=None,
                        )

                        try:

                            state["research"] = (
                                await research_pass(
                                    research_query.value,
                                    int(
                                        from_year.value
                                    ),
                                    int(
                                        result_limit.value
                                    ),
                                )
                            )

                            note.message = (
                                f"Found "
                                f"{len(state['research'])} "
                                f"records."
                            )

                            note.spinner = False
                            note.type = "positive"

                            research_panel.refresh()
                            overview_panel.refresh()

                        except Exception as error:

                            note.message = (
                                f"Research failed: {error}"
                            )

                            note.spinner = False
                            note.type = "negative"

                    ui.button(
                        "Search",
                        icon="search",
                        on_click=search,
                    ).props(
                        "color=primary "
                        "unelevated "
                        "no-caps"
                    )

            with ui.row().classes(
                "gap-4 flex-wrap"
            ):

                if research_query.value:
                    query_for_links = (
                        research_query.value
                    )

                elif state["proposal"]:
                    query_for_links = (
                        state["proposal"]
                        .get("document", {})
                        .get("title")
                        or
                        "technology"
                    )

                else:
                    query_for_links = (
                        "technology"
                    )

                encoded = quote(
                    query_for_links
                )

                for name, url in [

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
                        "USPTO",
                        "https://ppubs.uspto.gov/"
                        "pubwebapp/static/pages/"
                        "landing.html",
                    ),

                ]:

                    ui.link(
                        name,
                        url,
                        new_tab=True,
                    ).classes(
                        "text-sky-600 font-semibold"
                    )

            if not state["research"]:

                ui.card().classes(
                    "w-full"
                )

                ui.label(
                    "No research results yet."
                ).classes(
                    "text-slate-400"
                )

            else:

                for paper in state[
                    "research"
                ]:

                    with ui.card().classes(
                        "w-full "
                        "bg-white "
                        "border border-sky-100 "
                        "shadow-none "
                        "rounded-2xl"
                    ):

                        with ui.row().classes(
                            "items-center w-full"
                        ):

                            ui.badge(
                                paper["source"],
                                color=(
                                    "positive"
                                    if paper["source"]
                                    == "OpenAlex"
                                    else "warning"
                                ),
                            )

                            ui.label(
                                str(
                                    paper.get("year")
                                    or ""
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
                            "text-slate-800 "
                            "mt-1"
                        )

                        if paper.get("url"):

                            ui.link(
                                "Open source ↗",
                                paper["url"],
                                new_tab=True,
                            ).classes(
                                "text-sky-600 "
                                "font-semibold "
                                "mt-2"
                            )


    # ========================================================
    # REVIEWER
    # ========================================================

    @ui.refreshable
    def reviewer_panel() -> None:

        with ui.column().classes(
            "w-full max-w-6xl mx-auto p-6 gap-5"
        ):

            ui.label(
                "Human reviewer"
            ).classes(
                "text-3xl font-semibold"
            )

            ui.label(
                "The system supports the panel. "
                "The panel makes the final decision."
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
                "w-full gap-4"
            ):

                for criterion in criteria:

                    with ui.card().classes(
                        "w-full "
                        "bg-white "
                        "border border-sky-100 "
                        "shadow-none "
                        "rounded-2xl"
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
                                f"Score: {value}/5",
                        )

                        sliders.append(
                            slider
                        )

            score = ui.label(
                "Overall: 4.00 / 5"
            ).classes(
                "text-3xl "
                "font-semibold "
                "text-sky-600"
            )

            def update_score():

                values = [
                    float(
                        slider.value or 0
                    )
                    for slider
                    in sliders
                ]

                average = (
                    sum(values)
                    / len(values)
                    if values
                    else 0
                )

                score.set_text(
                    f"Overall: {average:.2f} / 5"
                )

            for slider in sliders:

                slider.on_value_change(
                    update_score
                )

    # ========================================================
    # HANDLERS
    # ========================================================

    async def handle_proposal_upload(
        event
    ) -> None:

        note = ui.notification(
            "Receiving proposal...",
            spinner=True,
            timeout=None,
        )

        path = None

        try:

            suffix = Path(
                event.name
            ).suffix.lower()

            content = await run.io_bound(
                event.content.read
            )

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
            ) as temp:

                temp.write(content)

                path = temp.name

            note.message = (
                "Extracting document..."
            )

            parsed = await run.io_bound(
                parse_uploaded_document,
                path,
                event.name,
            )

            state[
                "proposal"
            ] = quick_understanding(
                parsed
            )

            state["ai"] = None

            note.message = (
                "Fast pass complete."
            )

            note.spinner = False
            note.type = "positive"

            overview_panel.refresh()
            document_panel.refresh()

        except Exception as error:

            note.message = (
                f"Proposal failed: {error}"
            )

            note.spinner = False
            note.type = "negative"

        finally:

            if path:

                try:
                    os.unlink(path)

                except OSError:
                    pass

    async def handle_award_upload(
        event
    ) -> None:

        note = ui.notification(
            f"Reading {event.name}...",
            spinner=True,
            timeout=None,
        )

        path = None

        try:

            suffix = Path(
                event.name
            ).suffix.lower()

            content = await run.io_bound(
                event.content.read
            )

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
            ) as temp:

                temp.write(content)

                path = temp.name

            parsed = await run.io_bound(
                parse_uploaded_document,
                path,
                event.name,
            )

            state[
                "awards"
            ].append({

                "filename":
                    event.name,

                "text":
                    parsed["text"],

                "pages":
                    parsed.get("pages"),

                "visual_pages":
                    parsed.get(
                        "visual_pages",
                        [],
                    ),

            })

            note.message = (
                f"{event.name} loaded."
            )

            note.spinner = False
            note.type = "positive"

            awards_panel.refresh()
            overview_panel.refresh()

        except Exception as error:

            note.message = (
                f"Award failed: {error}"
            )

            note.spinner = False
            note.type = "negative"

        finally:

            if path:

                try:
                    os.unlink(path)

                except OSError:
                    pass

    async def run_deeper_analysis():

        if not state["proposal"]:

            ui.notify(
                "Upload a proposal first.",
                type="warning",
            )

            return

        note = ui.notification(
            "Running deeper AI analysis...",
            spinner=True,
            timeout=None,
        )

        try:

            state["ai"] = (
                await run_ai_understanding(
                    state["proposal"]
                )
            )

            note.message = (
                "AI understanding complete."
            )

            note.spinner = False
            note.type = "positive"

            overview_panel.refresh()

        except Exception as error:

            note.message = (
                f"AI analysis failed: {error}"
            )

            note.spinner = False
            note.type = "negative"

    async def run_award_comparison():

        if not state["proposal"]:

            ui.notify(
                "Upload a current proposal first.",
                type="warning",
            )

            return

        result = (
            await compare_award_corpus(
                state["proposal"],
                state["awards"],
            )
        )

        state[
            "award_result"
        ] = result

        awards_panel.refresh()

    # ========================================================
    # HEADER
    # ========================================================

    with ui.header().classes(
        "bg-white "
        "text-slate-900 "
        "border-b border-sky-100 "
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
                "flex items-center "
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
                    "text-base font-semibold"
                )

                ui.label(
                    "Proposal research workspace"
                ).classes(
                    "text-xs text-slate-400"
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

        ui.tab(
            "Overview",
            icon="dashboard",
        )

        ui.tab(
            "Document",
            icon="description",
        )

        ui.tab(
            "Awards",
            icon="workspace_premium",
        )

        ui.tab(
            "Research & IP",
            icon="science",
        )

        ui.tab(
            "Reviewer",
            icon="fact_check",
        )

    with ui.tab_panels(
        tabs,
        value="Overview",
    ).classes(
        "w-full "
        "bg-transparent"
    ):

        with ui.tab_panel(
            "Overview"
        ):
            overview_panel()

        with ui.tab_panel(
            "Document"
        ):
            document_panel()

        with ui.tab_panel(
            "Awards"
        ):
            awards_panel()

        with ui.tab_panel(
            "Research & IP"
        ):
            research_panel()

        with ui.tab_panel(
            "Reviewer"
        ):
            reviewer_panel()


if __name__ == "__main__":

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
