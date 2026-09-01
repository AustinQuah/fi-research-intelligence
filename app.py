import os
import re
import tempfile
from pathlib import Path
from urllib.parse import quote

import httpx
from nicegui import ui, run


# ============================================================
# CONFIG
# ============================================================

APP_TITLE = 'FI Research Intelligence'

ui.colors(
    primary='#2457E6',
    secondary='#06A7C8',
    positive='#168F68',
    warning='#F59E0B',
    negative='#D64545',
)


# ============================================================
# DOCUMENT PARSING
# ============================================================

def read_pdf(path: str) -> dict:
    import pymupdf

    document = pymupdf.open(path)

    pages = []
    visual_pages = []

    for page_number, page in enumerate(document, start=1):
        text = page.get_text('text') or ''

        pages.append(
            f'[PAGE {page_number}]\n{text}'
        )

        # Flag pages which may contain figures, scans, or sparse text.
        if (
            len(text.strip()) < 500
            or page.get_images(full=True)
        ):
            visual_pages.append(page_number)

    return {
        'text': '\n\n'.join(pages),
        'pages': len(document),
        'visual_pages': visual_pages,
    }


def read_docx(path: str) -> dict:
    from docx import Document

    document = Document(path)

    parts = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            parts.append(text)

    for table in document.tables:
        for row in table.rows:
            parts.append(
                ' | '.join(
                    cell.text.strip()
                    for cell in row.cells
                )
            )

    return {
        'text': '\n'.join(parts),
        'pages': None,
        'visual_pages': [],
    }


def read_text(path: str) -> dict:
    return {
        'text': Path(path).read_text(
            encoding='utf-8',
            errors='ignore',
        ),
        'pages': None,
        'visual_pages': [],
    }


def read_document(
    path: str,
    filename: str,
) -> dict:

    suffix = Path(filename).suffix.lower()

    if suffix == '.pdf':
        return read_pdf(path)

    if suffix == '.docx':
        return read_docx(path)

    if suffix in {'.txt', '.md'}:
        return read_text(path)

    raise ValueError(
        'Supported formats: PDF, DOCX, TXT and MD.'
    )


# ============================================================
# BROWSER-SAFE PROVISIONAL ANALYSIS
# ============================================================

def provisional_analysis(
    text: str,
    filename: str,
    pages: int | None,
    visual_pages: list[int],
) -> dict:

    lower = text.lower()

    title = None

    patterns = [
        r'(?:title of research project|'
        r'research project title|'
        r'project title|'
        r'proposal title)'
        r'\s*[:\-]?\s*([^\n]{8,180})'
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            title = match.group(1).strip()
            break

    if (
        'living lab' in lower
        and 'water' in lower
    ):
        funding_initiative = (
            'Living Lab (Water)'
        )

    elif (
        'industrial water solutions'
        in lower
        or 'wafer fab' in lower
    ):
        funding_initiative = (
            'Industrial Water Solutions (IWS)'
        )

    elif (
        'municipal water' in lower
        or 'mwtd' in lower
    ):
        funding_initiative = (
            'Municipal Water: Technology Development'
        )

    elif (
        'competitive funding for water research'
        in lower
    ):
        funding_initiative = (
            'Competitive Funding for Water Research'
        )

    else:
        funding_initiative = None

    if (
        'funding initiative' in lower
        and 'desired outcomes' in lower
    ):
        document_type = 'FI / programme paper'

    elif (
        'project proposal' in lower
        or 'scientific abstract' in lower
    ):
        document_type = 'Individual R&D proposal'

    else:
        document_type = 'Unknown'

    section_names = [
        'Scientific Abstract',
        'Problem Statement',
        'Research Objectives',
        'Technical KPIs',
        'Methodology',
        'Landscape Scan',
        'Innovativeness',
        'Commercialisation',
        'Milestones',
        'Budget',
        'Impact',
        'TRL',
    ]

    sections = []

    for section in section_names:

        if section.lower() in lower:

            sections.append({
                'name': section,
                'confidence': 0.50,
            })

    claims = []

    for line in text.splitlines():

        line = line.strip()

        if len(line) < 40:
            continue

        if re.search(
            r'novel|innovative|improv|'
            r'increase|reduce|demonstrat|'
            r'achiev|target',
            line,
            re.IGNORECASE,
        ):
            claims.append(line)

        if len(claims) >= 8:
            break

    return {
        'document': {
            'filename': filename,
            'title': title,
            'funding_initiative': funding_initiative,
            'document_type': document_type,
            'pages': pages,
            'visual_pages': visual_pages,
            'sections': sections,
        },
        'understanding': {
            'problem': None,
            'technology': None,
            'baseline': None,
            'proposed_solution': None,
            'novelty_claims': [],
            'trl_start': None,
            'trl_target': None,
            'prior_projects': [],
        },
        'claims': claims,
        'kpis': [],
        'review_flags': [
            {
                'severity': 'Review',
                'title': 'Provisional analysis',
                'detail': (
                    'Browser parsing is not a substitute for '
                    'multimodal semantic analysis.'
                ),
            }
        ],
    }


# ============================================================
# RESEARCH
# ============================================================

async def search_openalex(
    query: str,
    year: int,
    limit: int,
) -> list[dict]:

    url = (
        'https://api.openalex.org/works'
        f'?search={quote(query)}'
        f'&filter=from_publication_date:{year}-01-01'
        f'&per-page={limit}'
    )

    async with httpx.AsyncClient(
        timeout=25,
        follow_redirects=True,
        headers={
            'User-Agent':
                'FI-Research-Intelligence/0.1',
            'Accept':
                'application/json',
        },
    ) as client:

        for attempt in range(4):

            response = await client.get(url)

            if response.status_code == 200:
                data = response.json()
                break

            if response.status_code == 429:

                await __import__(
                    'asyncio'
                ).sleep(
                    1.5 * (2 ** attempt)
                )

                continue

            response.raise_for_status()

        else:
            return []

    output = []

    for item in data.get(
        'results',
        [],
    ):

        location = (
            item.get(
                'primary_location'
            )
            or {}
        )

        output.append({
            'source': 'OpenAlex',
            'title':
                item.get('title')
                or 'Untitled',
            'year':
                item.get('publication_year'),
            'citations':
                item.get(
                    'cited_by_count',
                    0,
                ),
            'url':
                location.get(
                    'landing_page_url'
                )
                or item.get('doi')
                or item.get('id'),
        })

    return output


async def search_crossref(
    query: str,
    year: int,
    limit: int,
) -> list[dict]:

    url = (
        'https://api.crossref.org/works'
        f'?query.bibliographic={quote(query)}'
        f'&filter=from-pub-date:{year}-01-01'
        f'&rows={limit}'
    )

    async with httpx.AsyncClient(
        timeout=25,
        follow_redirects=True,
        headers={
            'User-Agent':
                'FI-Research-Intelligence/0.1',
            'Accept':
                'application/json',
        },
    ) as client:

        response = await client.get(url)

        response.raise_for_status()

        data = response.json()

    output = []

    for item in (
        data
        .get('message', {})
        .get('items', [])
    ):

        doi = item.get('DOI')

        output.append({
            'source': 'Crossref',
            'title': (
                item.get('title')
                or ['Untitled']
            )[0],
            'year': (
                (
                    item.get('published')
                    or {}
                )
                .get(
                    'date-parts',
                    [[None]],
                )[0][0]
            ),
            'citations':
                item.get(
                    'is-referenced-by-count',
                    0,
                ),
            'url':
                item.get('URL')
                or (
                    f'https://doi.org/{doi}'
                    if doi
                    else None
                ),
        })

    return output


# ============================================================
# MAIN PAGE
# ============================================================

def index():

    # Per-user state.
    proposal = {'value': None}
    papers = {'value': []}
    award_names = []

    # --------------------------------------------------------
    # Refreshable sections
    # --------------------------------------------------------

    @ui.refreshable
    def proposal_summary():

        data = proposal['value']

        if data is None:

            with ui.card().classes(
                'w-full p-6'
            ):

                ui.icon(
                    'description',
                    size='3rem',
                    color='grey-5',
                )

                ui.label(
                    'No proposal loaded'
                ).classes(
                    'text-xl font-bold'
                )

                ui.label(
                    'Upload a proposal to begin.'
                ).classes(
                    'text-grey-6'
                )

            return

        document = data['document']
        understanding = data[
            'understanding'
        ]

        with ui.card().classes(
            'w-full p-5'
        ):

            ui.label(
                document.get('title')
                or 'Title not determined'
            ).classes(
                'text-2xl font-bold'
            )

            with ui.row().classes(
                'items-center gap-2'
            ):

                ui.chip(
                    document.get(
                        'funding_initiative'
                    )
                    or 'FI not determined',
                    icon='account_balance',
                    color='primary',
                )

                ui.chip(
                    document.get(
                        'document_type'
                    )
                    or 'Unknown',
                    icon='description',
                )

            ui.separator()

            ui.label(
                understanding.get(
                    'problem'
                )
                or
                'Problem not yet determined.'
            ).classes(
                'text-grey-8'
            )

            ui.label(
                'Technology: '
                + (
                    understanding.get(
                        'technology'
                    )
                    or 'Not determined'
                )
            )

    @ui.refreshable
    def metrics():

        with ui.grid(
            columns=4
        ).classes(
            'w-full gap-4'
        ):

            metric_cards = [
                (
                    'Claims',
                    len(
                        proposal['value'].get(
                            'claims',
                            []
                        )
                    )
                    if proposal['value']
                    else 0,
                    'fact_check',
                    'primary',
                ),
                (
                    'KPIs',
                    len(
                        proposal['value'].get(
                            'kpis',
                            []
                        )
                    )
                    if proposal['value']
                    else 0,
                    'analytics',
                    'secondary',
                ),
                (
                    'Research',
                    len(papers['value']),
                    'science',
                    'positive',
                ),
                (
                    'Awards',
                    len(award_names),
                    'workspace_premium',
                    'warning',
                ),
            ]

            for (
                label,
                value,
                icon,
                color,
            ) in metric_cards:

                with ui.card().classes(
                    'p-4 w-full'
                ):

                    with ui.row().classes(
                        'items-center '
                        'justify-between '
                        'w-full'
                    ):

                        ui.label(
                            label
                        ).classes(
                            'text-grey-7'
                        )

                        ui.icon(
                            icon,
                            color=color,
                        )

                    ui.label(
                        str(value)
                    ).classes(
                        'text-3xl font-bold'
                    )

    @ui.refreshable
    def document_details():

        data = proposal['value']

        if data is None:
            ui.label(
                'Upload a proposal first.'
            ).classes(
                'text-grey-6'
            )
            return

        understanding = data[
            'understanding'
        ]

        with ui.grid(
            columns=2
        ).classes(
            'w-full gap-4'
        ):

            fields = [
                (
                    'Problem',
                    'problem',
                ),
                (
                    'Technology',
                    'technology',
                ),
                (
                    'Baseline',
                    'baseline',
                ),
                (
                    'Proposed solution',
                    'proposed_solution',
                ),
                (
                    'Commercialisation',
                    'commercialisation',
                ),
            ]

            for label, key in fields:

                with ui.card().classes(
                    'w-full'
                ):

                    ui.label(
                        label
                    ).classes(
                        'font-bold text-lg'
                    )

                    ui.label(
                        understanding.get(
                            key
                        )
                        or 'Not determined'
                    ).classes(
                        'text-grey-8'
                    )

            with ui.card().classes(
                'w-full'
            ):

                ui.label(
                    'Novelty claims'
                ).classes(
                    'font-bold text-lg'
                )

                novelty = understanding.get(
                    'novelty_claims',
                    []
                )

                if not novelty:
                    ui.label(
                        'None confidently identified.'
                    ).classes(
                        'text-grey-6'
                    )

                for item in novelty:
                    ui.label(
                        '• ' + item
                    )

    @ui.refreshable
    def award_list():

        if not award_names:

            ui.label(
                'No awards loaded.'
            ).classes(
                'text-grey-6'
            )

            return

        for name in award_names:

            with ui.card().classes(
                'w-full'
            ):

                with ui.row().classes(
                    'items-center'
                ):

                    ui.icon(
                        'workspace_premium',
                        color='warning',
                    )

                    ui.label(
                        name
                    ).classes(
                        'font-bold'
                    )

    @ui.refreshable
    def research_results():

        if not papers['value']:

            ui.label(
                'No research results yet.'
            ).classes(
                'text-grey-6'
            )

            return

        for paper in papers['value']:

            with ui.card().classes(
                'w-full'
            ):

                with ui.row().classes(
                    'items-center'
                ):

                    ui.badge(
                        paper['source'],
                        color=(
                            'positive'
                            if paper['source']
                            == 'OpenAlex'
                            else 'warning'
                        ),
                    )

                    ui.label(
                        str(
                            paper.get(
                                'year'
                            )
                            or ''
                        )
                    ).classes(
                        'text-grey-6'
                    )

                    ui.space()

                    ui.label(
                        f"{paper.get('citations', 0)} citations"
                    ).classes(
                        'text-grey-6'
                    )

                ui.label(
                    paper['title']
                ).classes(
                    'text-base font-bold'
                )

                if paper.get('url'):

                    ui.button(
                        'Open source',
                        icon='open_in_new',
                        on_click=lambda
                        url=paper['url']:
                            ui.navigate.to(
                                url,
                                new_tab=True,
                            ),
                    ).props(
                        'flat color=primary'
                    )

    # --------------------------------------------------------
    # Upload handlers
    # --------------------------------------------------------

    async def handle_proposal_upload(event):

        notification = ui.notification(
            'Reading proposal...',
            spinner=True,
            timeout=None,
        )

        suffix = Path(
            event.name
        ).suffix.lower()

        try:

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
            ) as temp:

                content = await run.io_bound(
                    event.content.read
                )

                temp.write(content)

                path = temp.name

            parsed = await run.io_bound(
                parse_document,
                path,
                event.name,
            )

            proposal['value'] = (
                provisional_analysis(
                    parsed['text'],
                    event.name,
                    parsed['pages'],
                    parsed['visual_pages'],
                )
            )

            # Seed research with title if useful.
            document = proposal[
                'value'
            ]['document']

            query.value = (
                document.get('title')
                or ''
            )

            proposal_summary.refresh()
            metrics.refresh()
            document_details.refresh()

            notification.message = (
                'Proposal loaded'
            )

            notification.spinner = False
            notification.type = (
                'positive'
            )

        except Exception as error:

            notification.message = (
                f'Upload failed: {error}'
            )

            notification.spinner = False
            notification.type = (
                'negative'
            )

    async def handle_award_upload(event):

        award_names.append(
            event.name
        )

        metrics.refresh()
        award_list.refresh()

        ui.notify(
            f'Loaded {event.name}',
            type='positive',
        )

    # --------------------------------------------------------
    # Research handler
    # --------------------------------------------------------

    async def run_research():

        search_query = (
            query.value or ''
        ).strip()

        if not search_query:

            ui.notify(
                'Enter a research question.',
                type='warning',
            )

            return

        notification = ui.notification(
            'Searching OpenAlex and Crossref...',
            spinner=True,
            timeout=None,
        )

        try:

            openalex = (
                await search_openalex(
                    search_query,
                    int(year.value),
                    int(limit.value),
                )
            )

            # Courtesy delay between providers.
            import asyncio

            await asyncio.sleep(0.75)

            crossref = (
                await search_crossref(
                    search_query,
                    int(year.value),
                    int(limit.value),
                )
            )

            combined = (
                openalex
                + crossref
            )

            unique = []
            seen = set()

            for paper in combined:

                key = (
                    paper.get('doi')
                    or paper.get('url')
                    or paper.get('title')
                    or ''
                ).lower()

                if not key or key in seen:
                    continue

                seen.add(key)
                unique.append(paper)

            unique.sort(
                key=lambda x:
                    x.get(
                        'citations',
                        0,
                    ),
                reverse=True,
            )

            papers['value'] = unique

            metrics.refresh()
            research_results.refresh()

            notification.message = (
                f'Found {len(unique)} '
                'research records.'
            )

            notification.spinner = False
            notification.type = (
                'positive'
            )

        except Exception as error:

            notification.message = (
                f'Research failed: {error}'
            )

            notification.spinner = False
            notification.type = (
                'negative'
            )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    with ui.header().classes(
        'bg-primary px-6 py-3'
    ):

        ui.icon(
            'hub',
            size='2rem',
        )

        with ui.column().classes(
            'gap-0'
        ):

            ui.label(
                APP_TITLE
            ).classes(
                'text-xl font-bold'
            )

            ui.label(
                'Proposal • Awards • '
                'Research • Review'
            ).classes(
                'text-xs text-blue-100'
            )

        ui.space()

        ui.badge(
            'MVP',
            color='secondary',
        )

    # --------------------------------------------------------
    # Main navigation
    # --------------------------------------------------------

    with ui.tabs() as tabs:

        overview = ui.tab(
            'Overview',
            icon='dashboard',
        )

        documents = ui.tab(
            'Document',
            icon='description',
        )

        awards = ui.tab(
            'Awards',
            icon='workspace_premium',
        )

        research = ui.tab(
            'Research & IP',
            icon='science',
        )

        review = ui.tab(
            'Reviewer',
            icon='fact_check',
        )

    with ui.tab_panels(
        tabs,
        value=overview,
    ).classes(
        'w-full max-w-7xl mx-auto'
    ):

        # ----------------------------------------------------
        # Overview
        # ----------------------------------------------------

        with ui.tab_panel(
            overview
        ):

            ui.label(
                'Proposal workspace'
            ).classes(
                'text-3xl font-bold'
            )

            ui.label(
                'Upload a proposal and '
                'build an evidence-led '
                'review workspace.'
            ).classes(
                'text-grey-7'
            )

            ui.upload(
                on_upload=handle_proposal_upload,
                auto_upload=True,
                max_file_size=30_000_000,
            ).props(
                'accept=.pdf,.docx,.txt,.md'
            ).classes(
                'w-full mt-4'
            )

            metrics()

            proposal_summary()

        # ----------------------------------------------------
        # Document
        # ----------------------------------------------------

        with ui.tab_panel(
            documents
        ):

            ui.label(
                'Document understanding'
            ).classes(
                'text-3xl font-bold'
            )

            ui.label(
                'What does the proposal '
                'actually contain?'
            ).classes(
                'text-grey-7'
            )

            document_details()

        # ----------------------------------------------------
        # Awards
        # ----------------------------------------------------

        with ui.tab_panel(
            awards
        ):

            ui.label(
                'Award landscape'
            ).classes(
                'text-3xl font-bold'
            )

            ui.label(
                'Upload previous awards '
                'or proposals.'
            ).classes(
                'text-grey-7'
            )

            ui.upload(
                on_upload=handle_award_upload,
                multiple=True,
                auto_upload=True,
                max_files=50,
            ).props(
                'accept=.pdf,.docx,.txt,.md'
            ).classes(
                'w-full mt-4'
            )

            award_list()

        # ----------------------------------------------------
        # Research
        # ----------------------------------------------------

        with ui.tab_panel(
            research
        ):

            ui.label(
                'Research intelligence'
            ).classes(
                'text-3xl font-bold'
            )

            ui.label(
                'Search literature and '
                'open direct patent '
                'research routes.'
            ).classes(
                'text-grey-7'
            )

            with ui.card().classes(
                'w-full mt-4'
            ):

                query = ui.input(
                    'Technology, claim or '
                    'research question'
                ).classes(
                    'w-full'
                )

                with ui.row().classes(
                    'items-end gap-3'
                ):

                    year = ui.number(
                        'From year',
                        value=2020,
                    )

                    limit = ui.number(
                        'Results',
                        value=10,
                    )

                    ui.button(
                        'Search',
                        icon='search',
                        on_click=run_research,
                    ).props(
                        'color=primary'
                    )

            with ui.row().classes(
                'gap-2 mt-3'
            ):

                ui.button(
                    'Google Scholar',
                    on_click=lambda:
                        ui.navigate.to(
                            'https://scholar.google.com/',
                            new_tab=True,
                        ),
                ).props('outline')

                ui.button(
                    'Google Patents',
                    on_click=lambda:
                        ui.navigate.to(
                            'https://patents.google.com/',
                            new_tab=True,
                        ),
                ).props('outline')

                ui.button(
                    'WIPO',
                    on_click=lambda:
                        ui.navigate.to(
                            'https://patentscope.wipo.int/',
                            new_tab=True,
                        ),
                ).props('outline')

            research_results()

        # ----------------------------------------------------
        # Reviewer
        # ----------------------------------------------------

        with ui.tab_panel(
            review
        ):

            ui.label(
                'Human reviewer'
            ).classes(
                'text-3xl font-bold'
            )

            ui.label(
                'The AI provides evidence; '
                'the human makes the decision.'
            ).classes(
                'text-grey-7'
            )

            criteria = [
                'Science & technology',
                'Impact / national benefit',
                'Management & delivery',
                'Budget / value',
            ]

            scores = []

            for criterion in criteria:

                with ui.card().classes(
                    'w-full'
                ):

                    ui.label(
                        criterion
                    ).classes(
                        'font-bold'
                    )

                    score = ui.slider(
                        min=1,
                        max=5,
                        step=1,
                        value=4,
                    ).classes(
                        'w-full'
                    )

                    scores.append(score)

            overall = ui.label(
                'Overall: 4.00 / 5'
            ).classes(
                'text-2xl font-bold '
                'text-primary'
            )

            def update_score():

                values = [
                    float(x.value or 0)
                    for x in scores
                ]

                average = (
                    sum(values)
                    / len(values)
                    if values
                    else 0
                )

                overall.set_text(
                    f'Overall: {average:.2f} / 5'
                )

            for score in scores:
                score.on_value_change(
                    update_score
                )


# IMPORTANT:
# Render needs the server to bind to 0.0.0.0
# and to use Render's supplied PORT.
ui.run(
    root=index,
    host='0.0.0.0',
    port=int(
        os.environ.get(
            'PORT',
            '8000',
        )
    ),
    title=APP_TITLE,
    favicon='🔬',
    reload=False,
)
