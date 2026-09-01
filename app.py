import os
import re
import tempfile
from pathlib import Path
from urllib.parse import quote

import httpx
from nicegui import ui

try:
    import fitz
except ImportError:
    fitz = None

try:
    from docx import Document
except ImportError:
    Document = None


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

ui.query('body').classes('bg-slate-50')


# ============================================================
# DOCUMENT PARSING
# ============================================================

def parse_pdf(path: str) -> dict:
    if fitz is None:
        raise RuntimeError('PyMuPDF is not installed.')

    document = fitz.open(path)

    pages = []
    visual_pages = []

    for number, page in enumerate(document, start=1):
        text = page.get_text('text') or ''

        pages.append(
            f'[PAGE {number}]\n{text}'
        )

        if (
            len(text.strip()) < 500
            or page.get_images(full=True)
        ):
            visual_pages.append(number)

    return {
        'text': '\n\n'.join(pages),
        'pages': len(document),
        'visual_pages': visual_pages,
    }


def parse_docx(path: str) -> dict:
    if Document is None:
        raise RuntimeError('python-docx is not installed.')

    document = Document(path)

    parts = []

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            parts.append(paragraph.text)

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


def parse_document(
    path: str,
    filename: str,
) -> dict:

    extension = (
        Path(filename)
        .suffix
        .lower()
    )

    if extension == '.pdf':
        return parse_pdf(path)

    if extension == '.docx':
        return parse_docx(path)

    if extension in {'.txt', '.md'}:
        return {
            'text': Path(path).read_text(
                errors='ignore'
            ),
            'pages': None,
            'visual_pages': [],
        }

    raise RuntimeError(
        'Supported files: PDF, DOCX, TXT, MD'
    )


# ============================================================
# SIMPLE LOCAL UNDERSTANDING
# ============================================================

def local_analysis(
    text: str,
    filename: str,
    pages,
) -> dict:

    lower = text.lower()

    title = None

    title_patterns = [
        r'(?:title of research project|'
        r'research project title|'
        r'proposal title|'
        r'project title)'
        r'\s*[:\-]?\s*([^\n]{8,180})'
    ]

    for pattern in title_patterns:
        match = re.search(
            pattern,
            text,
            re.I,
        )

        if match:
            title = (
                match.group(1)
                .strip()
            )
            break

    if (
        'living lab' in lower
        and 'water' in lower
    ):
        fi = 'Living Lab (Water)'

    elif (
        'industrial water solutions'
        in lower
        or 'wafer fab' in lower
    ):
        fi = (
            'Industrial Water '
            'Solutions (IWS)'
        )

    elif (
        'municipal water' in lower
        or 'mwtd' in lower
    ):
        fi = (
            'Municipal Water: '
            'Technology Development'
        )

    elif (
        'competitive funding '
        'for water research'
        in lower
    ):
        fi = (
            'Competitive Funding '
            'for Water Research'
        )

    else:
        fi = None

    if (
        'funding initiative' in lower
        and 'desired outcomes' in lower
    ):
        document_type = (
            'FI / programme paper'
        )

    elif (
        'project proposal' in lower
        or 'scientific abstract' in lower
    ):
        document_type = (
            'Individual R&D proposal'
        )

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
                'section': section,
                'status': 'Detected',
            })

    lines = [
        line.strip()
        for line in text.splitlines()
        if len(line.strip()) > 35
    ]

    claims = []

    for line in lines:
        if re.search(
            r'novel|innovative|'
            r'improve|increase|'
            r'reduce|demonstrate|'
            r'achieve|target',
            line,
            re.I,
        ):
            claims.append(line)

        if len(claims) >= 8:
            break

    return {
        'filename': filename,
        'title': title,
        'fi': fi,
        'document_type': document_type,
        'pages': pages,
        'sections': sections,
        'claims': claims,
        'text': text,
    }


# ============================================================
# RESEARCH APIS
# ============================================================

async def search_openalex(
    query: str,
    year: int,
    limit: int,
) -> list:

    url = (
        'https://api.openalex.org/works'
        f'?search={quote(query)}'
        f'&filter=from_publication_date:'
        f'{year}-01-01'
        f'&per-page={limit}'
    )

    async with httpx.AsyncClient(
        timeout=25,
        follow_redirects=True,
    ) as client:

        response = await client.get(url)

        if response.status_code == 429:
            return []

        response.raise_for_status()

        data = response.json()

    output = []

    for item in data.get(
        'results',
        [],
    ):

        location = (
            item.get('primary_location')
            or {}
        )

        output.append({
            'source': 'OpenAlex',
            'title': (
                item.get('title')
                or 'Untitled'
            ),
            'year': item.get(
                'publication_year'
            ),
            'citations': item.get(
                'cited_by_count',
                0,
            ),
            'url': (
                location.get(
                    'landing_page_url'
                )
                or item.get('doi')
                or item.get('id')
            ),
        })

    return output


async def search_crossref(
    query: str,
    year: int,
    limit: int,
) -> list:

    url = (
        'https://api.crossref.org/works'
        f'?query.bibliographic='
        f'{quote(query)}'
        f'&filter=from-pub-date:'
        f'{year}-01-01'
        f'&rows={limit}'
    )

    async with httpx.AsyncClient(
        timeout=25,
        follow_redirects=True,
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

        title = (
            item.get('title')
            or ['Untitled']
        )[0]

        doi = item.get('DOI')

        date_parts = (
            item.get('published', {})
            .get(
                'date-parts',
                [[None]],
            )
        )

        output.append({
            'source': 'Crossref',
            'title': title,
            'year': (
                date_parts[0][0]
                if date_parts
                else None
            ),
            'citations': item.get(
                'is-referenced-by-count',
                0,
            ),
            'url': (
                item.get('URL')
                or (
                    f'https://doi.org/{doi}'
                    if doi
                    else None
                )
            ),
        })

    return output


# ============================================================
# PAGE
# ============================================================

@ui.page('/')
def index():

    # --------------------------------------------
    # Per-user state
    # --------------------------------------------

    state = {
        'proposal': None,
        'papers': [],
        'award_files': [],
    }

    # --------------------------------------------
    # Dynamic UI sections
    # --------------------------------------------

    @ui.refreshable
    def proposal_summary():

        proposal = state['proposal']

        if proposal is None:

            with ui.card() \
                    .classes(
                        'w-full p-6 '
                        'bg-white'
                    ):

                ui.icon(
                    'description',
                    size='2.5rem',
                    color='grey-5',
                )

                ui.label(
                    'No proposal analysed yet'
                ).classes(
                    'text-lg font-bold'
                )

                ui.label(
                    'Upload a proposal to '
                    'start the review.'
                ).classes(
                    'text-grey-6'
                )

            return

        with ui.card() \
                .classes(
                    'w-full p-5 '
                    'bg-white shadow-sm'
                ):

            ui.label(
                proposal.get('title')
                or 'Title not determined'
            ).classes(
                'text-2xl font-bold'
            )

            with ui.row() \
                    .classes(
                        'gap-2 items-center'
                    ):

                ui.chip(
                    proposal.get('fi')
                    or 'FI not determined',
                    icon='account_balance',
                    color='primary',
                )

                ui.chip(
                    proposal.get(
                        'document_type'
                    ),
                    icon='description',
                )

            ui.separator()

            ui.label(
                f"File: "
                f"{proposal['filename']}"
            ).classes(
                'text-grey-7'
            )

            if proposal.get('pages'):
                ui.label(
                    f"Pages: "
                    f"{proposal['pages']}"
                ).classes(
                    'text-grey-7'
                )

    @ui.refreshable
    def metrics():

        proposal = state['proposal']

        cards = [
            (
                'Claims',
                len(
                    proposal.get(
                        'claims',
                        [],
                    )
                )
                if proposal
                else 0,
                'fact_check',
                'primary',
            ),
            (
                'Sections',
                len(
                    proposal.get(
                        'sections',
                        [],
                    )
                )
                if proposal
                else 0,
                'view_list',
                'secondary',
            ),
            (
                'Papers',
                len(state['papers']),
                'science',
                'positive',
            ),
            (
                'Awards',
                len(
                    state[
                        'award_files'
                    ]
                ),
                'workspace_premium',
                'warning',
            ),
        ]

        with ui.grid(columns=4) \
                .classes(
                    'w-full gap-4'
                ):

            for (
                label,
                value,
                icon,
                color,
            ) in cards:

                with ui.card() \
                        .classes(
                            'p-4 '
                            'bg-white '
                            'shadow-sm'
                        ):

                    with ui.row() \
                            .classes(
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
                        'text-3xl '
                        'font-bold'
                    )

    @ui.refreshable
    def document_view():

        proposal = state['proposal']

        if not proposal:
            ui.label(
                'Upload a proposal first.'
            ).classes(
                'text-grey-6'
            )
            return

        with ui.grid(columns=2) \
                .classes(
                    'w-full gap-4'
                ):

            with ui.card() \
                    .classes(
                        'w-full p-5'
                    ):

                ui.label(
                    'Detected sections'
                ).classes(
                    'text-lg font-bold'
                )

                for section in (
                    proposal.get(
                        'sections',
                        [],
                    )
                ):

                    with ui.row() \
                            .classes(
                                'items-center'
                            ):

                        ui.icon(
                            'check_circle',
                            color='positive',
                        )

                        ui.label(
                            section[
                                'section'
                            ]
                        )

            with ui.card() \
                    .classes(
                        'w-full p-5'
                    ):

                ui.label(
                    'Potential claims'
                ).classes(
                    'text-lg font-bold'
                )

                claims = (
                    proposal.get(
                        'claims',
                        [],
                    )
                )

                if not claims:

                    ui.label(
                        'No claims '
                        'identified.'
                    ).classes(
                        'text-grey-6'
                    )

                for claim in claims:

                    with ui.card() \
                            .classes(
                                'w-full '
                                'bg-grey-1'
                            ):

                        ui.label(
                            claim
                        ).classes(
                            'text-sm'
                        )

    @ui.refreshable
    def research_results():

        if not state['papers']:

            ui.label(
                'No research results yet.'
            ).classes(
                'text-grey-6'
            )

            return

        for paper in state['papers']:

            with ui.card() \
                    .classes(
                        'w-full p-4 '
                        'hover:shadow-md'
                    ):

                with ui.row() \
                        .classes(
                            'items-center '
                            'w-full'
                        ):

                    ui.badge(
                        paper['source'],
                        color=(
                            'positive'
                            if paper[
                                'source'
                            ]
                            == 'OpenAlex'
                            else 'warning'
                        ),
                    )

                    ui.label(
                        str(
                            paper.get(
                                'year',
                                '',
                            )
                            or ''
                        )
                    ).classes(
                        'text-grey-6'
                    )

                    ui.space()

                    ui.label(
                        f"{paper.get('citations', 0)} "
                        f"citations"
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

    # --------------------------------------------
    # Events
    # --------------------------------------------

    async def upload_proposal(event):

        notification = ui.notification(
            'Reading document...',
            spinner=True,
            timeout=None,
        )

        suffix = (
            Path(event.name)
            .suffix
            .lower()
        )

        try:

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
            ) as temporary:

                temporary.write(
                    event.content.read()
                )

                path = temporary.name

            parsed = parse_document(
                path,
                event.name,
            )

            state['proposal'] = (
                local_analysis(
                    parsed['text'],
                    event.name,
                    parsed['pages'],
                )
            )

            proposal_summary.refresh()
            metrics.refresh()
            document_view.refresh()

            query.value = (
                state['proposal']
                .get('title')
                or ''
            )

            notification.message = (
                'Proposal loaded'
            )

            notification.spinner = False
            notification.type = 'positive'

        except Exception as error:

            notification.message = (
                f'Could not read file: '
                f'{error}'
            )

            notification.spinner = False
            notification.type = (
                'negative'
            )

    async def run_research():

        search_query = (
            query.value
            or ''
        ).strip()

        if not search_query:

            ui.notify(
                'Enter a research question.',
                type='warning',
            )

            return

        notification = ui.notification(
            'Searching research...',
            spinner=True,
            timeout=None,
        )

        try:

            # Sequential on purpose:
            # kinder to public APIs.

            openalex = (
                await search_openalex(
                    search_query,
                    int(year.value),
                    int(limit.value),
                )
            )

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

            seen = set()
            unique = []

            for paper in combined:

                key = (
                    paper.get('url')
                    or paper.get('title')
                    or ''
                ).lower()

                if (
                    not key
                    or key in seen
                ):
                    continue

                seen.add(key)
                unique.append(paper)

            unique.sort(
                key=lambda item:
                    item.get(
                        'citations',
                        0,
                    ),
                reverse=True,
            )

            state['papers'] = unique

            metrics.refresh()
            research_results.refresh()

            notification.message = (
                f'Found '
                f'{len(unique)} '
                f'research records'
            )

            notification.spinner = False
            notification.type = (
                'positive'
            )

        except Exception as error:

            notification.message = (
                f'Research failed: '
                f'{error}'
            )

            notification.spinner = False
            notification.type = (
                'negative'
            )

    async def upload_award(event):

        state[
            'award_files'
        ].append(
            event.name
        )

        metrics.refresh()
        award_list.refresh()

    @ui.refreshable
    def award_list():

        if not state['award_files']:

            ui.label(
                'No previous awards '
                'uploaded.'
            ).classes(
                'text-grey-6'
            )

            return

        for filename in (
            state['award_files']
        ):

            with ui.card() \
                    .classes(
                        'w-full'
                    ):

                with ui.row() \
                        .classes(
                            'items-center'
                        ):

                    ui.icon(
                        'workspace_premium',
                        color='warning',
                    )

                    ui.label(
                        filename
                    ).classes(
                        'font-bold'
                    )

                    ui.space()

                    ui.badge(
                        'Loaded',
                        color='positive',
                    )

    # --------------------------------------------
    # Header
    # --------------------------------------------

    with ui.header() \
            .classes(
                'bg-primary '
                'items-center '
                'px-6 py-3'
            ):

        ui.icon(
            'hub',
            size='2rem',
        )

        with ui.column() \
                .classes('gap-0'):

            ui.label(
                APP_TITLE
            ).classes(
                'text-xl '
                'font-bold'
            )

            ui.label(
                'Research • Awards • '
                'Evidence • Review'
            ).classes(
                'text-xs '
                'text-blue-100'
            )

        ui.space()

        ui.badge(
            'MVP',
            color='secondary',
        )

    # --------------------------------------------
    # Navigation
    # --------------------------------------------

    with ui.tabs() as tabs:

        overview_tab = ui.tab(
            'Overview',
            icon='dashboard',
        )

        document_tab = ui.tab(
            'Document',
            icon='description',
        )

        awards_tab = ui.tab(
            'Awards',
            icon='workspace_premium',
        )

        research_tab = ui.tab(
            'Research & IP',
            icon='science',
        )

        review_tab = ui.tab(
            'Reviewer',
            icon='fact_check',
        )

    # --------------------------------------------
    # Panels
    # --------------------------------------------

    with ui.tab_panels(
        tabs,
        value=overview_tab,
    ).classes(
        'w-full '
        'max-w-7xl '
        'mx-auto '
        'bg-transparent'
    ):

        # OVERVIEW

        with ui.tab_panel(
            overview_tab
        ):

            ui.label(
                'Proposal workspace'
            ).classes(
                'text-3xl '
                'font-bold'
            )

            ui.label(
                'Upload a proposal and '
                'build an evidence-led '
                'review workspace.'
            ).classes(
                'text-grey-7'
            )

            ui.upload(
                on_upload=upload_proposal,
                auto_upload=True,
                max_file_size=30_000_000,
            ).props(
                'accept=.pdf,.docx,.txt,.md'
            ).classes(
                'w-full mt-4'
            )

            metrics()

            proposal_summary()

        # DOCUMENT

        with ui.tab_panel(
            document_tab
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

            document_view()

        # AWARDS

        with ui.tab_panel(
            awards_tab
        ):

            ui.label(
                'Award landscape'
            ).classes(
                'text-3xl font-bold'
            )

            ui.label(
                'Add previous awards '
                'for comparison.'
            ).classes(
                'text-grey-7'
            )

            ui.upload(
                on_upload=upload_award,
                multiple=True,
                auto_upload=True,
                max_files=50,
            ).props(
                'accept=.pdf,.docx,.txt,.md'
            ).classes(
                'w-full mt-4'
            )

            award_list()

        # RESEARCH

        with ui.tab_panel(
            research_tab
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

            with ui.card() \
                    .classes(
                        'w-full mt-4'
                    ):

                query = ui.input(
                    'Technology, claim, '
                    'or research question'
                ).classes(
                    'w-full'
                )

                with ui.row() \
                        .classes(
                            'w-full '
                            'items-end'
                        ):

                    year = ui.number(
                        'From year',
                        value=2020,
                        min=1900,
                        max=2100,
                    )

                    limit = ui.number(
                        'Results per source',
                        value=10,
                        min=1,
                        max=25,
                    )

                    ui.button(
                        'Search research',
                        icon='search',
                        on_click=run_research,
                    )

            with ui.row() \
                    .classes(
                        'w-full '
                        'gap-2 mt-2'
                    ):

                ui.button(
                    'Google Scholar',
                    icon='school',
                    on_click=lambda:
                        ui.navigate.to(
                            'https://scholar.'
                            'google.com/',
                            new_tab=True,
                        ),
                ).props(
                    'outline'
                )

                ui.button(
                    'Google Patents',
                    icon='lightbulb',
                    on_click=lambda:
                        ui.navigate.to(
                            'https://patents.'
                            'google.com/',
                            new_tab=True,
                        ),
                ).props(
                    'outline'
                )

                ui.button(
                    'WIPO',
                    icon='public',
                    on_click=lambda:
                        ui.navigate.to(
                            'https://patentscope.'
                            'wipo.int/',
                            new_tab=True,
                        ),
                ).props(
                    'outline'
                )

            with ui.column() \
                    .classes(
                        'w-full mt-4'
                    ):

                research_results()

        # REVIEWER

        with ui.tab_panel(
            review_tab
        ):

            ui.label(
                'Human reviewer'
            ).classes(
                'text-3xl font-bold'
            )

            ui.label(
                'AI and research evidence '
                'support the reviewer; '
                'they do not make the '
                'funding decision.'
            ).classes(
                'text-grey-7'
            )

            criteria = [
                (
                    'Science & technology',
                    25,
                ),
                (
                    'Impact / '
                    'national benefit',
                    25,
                ),
                (
                    'Management & delivery',
                    25,
                ),
                (
                    'Budget / value',
                    25,
                ),
            ]

            review_inputs = []

            with ui.grid(
                columns=2
            ).classes(
                'w-full gap-4 mt-4'
            ):

                for (
                    criterion,
                    default_weight,
                ) in criteria:

                    with ui.card() \
                            .classes(
                                'w-full'
                            ):

                        ui.label(
                            criterion
                        ).classes(
                            'font-bold'
                        )

                        weight = ui.number(
                            'Weight (%)',
                            value=(
                                default_weight
                            ),
                            min=0,
                            max=100,
                        )

                        score = ui.slider(
                            min=1,
                            max=5,
                            step=1,
                            value=4,
                        )

                        score_label = (
                            ui.label()
                        )

                        score_label.bind_text_from(
                            score,
                            'value',
                            backward=lambda value:
                                f'Score: '
                                f'{value}/5',
                        )

                        review_inputs.append(
                            (
                                weight,
                                score,
                            )
                        )

            total_label = ui.label(
                'Weighted score: 4.00 / 5'
            ).classes(
                'text-2xl '
                'font-bold '
                'text-primary'
            )

            def calculate_score():

                total = 0
                weights = 0

                for (
                    weight,
                    score,
                ) in review_inputs:

                    w = (
                        float(
                            weight.value
                            or 0
                        )
                    )

                    s = (
                        float(
                            score.value
                            or 0
                        )
                    )

                    total += w * s
                    weights += w

                result = (
                    total / weights
                    if weights
                    else 0
                )

                total_label.set_text(
                    'Weighted score: '
                    f'{result:.2f} / 5'
                )

            for (
                weight,
                score,
            ) in review_inputs:

                weight.on_value_change(
                    calculate_score
                )

                score.on_value_change(
                    calculate_score
                )

            ui.textarea(
                'Reviewer notes'
            ).props(
                'outlined autogrow'
            ).classes(
                'w-full mt-4'
            )


# ============================================================
# START SERVER
# ============================================================

ui.run(
    host='0.0.0.0',
    port=int(
        os.environ.get(
            'PORT',
            8000,
        )
    ),
    title=APP_TITLE,
    favicon='🔬',
    reload=False,
)
