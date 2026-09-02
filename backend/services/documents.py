from pathlib import Path
import re


SECTION_NAMES = [
    "scientific abstract",
    "abstract",
    "executive summary",
    "problem statement",
    "background",
    "research objectives",
    "objectives",
    "technical kpis",
    "key performance indicators",
    "methodology",
    "approach",
    "landscape scan",
    "literature review",
    "innovativeness",
    "innovation",
    "commercialisation",
    "commercialization",
    "milestones",
    "budget",
    "impact",
    "trl",
]


TECHNICAL_PATTERNS = [
    r"\bmembrane(?:s)?\b",
    r"\bdesalination\b",
    r"\bwastewater\b",
    r"\bwater treatment\b",
    r"\bwater reuse\b",
    r"\breverse osmosis\b",
    r"\bultrafiltration\b",
    r"\bmicrofiltration\b",
    r"\bnanofiltration\b",
    r"\bceramic membrane(?:s)?\b",
    r"\banaerobic\b",
    r"\belectrolysis\b",
    r"\belectrochemical\b",
    r"\badsorption\b",
    r"\boxidation\b",
    r"\bfiltration\b",
    r"\bresource recovery\b",
    r"\bcarbon capture\b",
    r"\bPFAS\b",
    r"\bsludge\b",
    r"\bbiogas\b",
]


CLAIM_PATTERN = re.compile(
    r"\b("
    r"novel|innovative|improve|improved|improvement|"
    r"increase|increased|reduce|reduced|reduction|"
    r"achieve|achieved|target|demonstrate|demonstrated|"
    r"performance|efficiency|higher|lower|enhance|enhanced"
    r")\b",
    re.IGNORECASE,
)


KPI_PATTERN = re.compile(
    r"("
    r"\d+(?:\.\d+)?\s*%|"
    r"\d+(?:\.\d+)?\s*(?:mg\/l|g\/l|kg\/m3|"
    r"m3\/day|m³\/day|bar|kwh|kw|mw|ppm|ppb)|"
    r"trl\s*\d+"
    r")",
    re.IGNORECASE,
)


def parse_document(
    path: str,
    filename: str,
) -> dict:

    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        return parse_pdf(
            path,
            filename,
        )

    if suffix == ".docx":
        return parse_docx(
            path,
            filename,
        )

    if suffix in {
        ".txt",
        ".md",
    }:

        text = Path(path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

        return {
            "filename": filename,
            "text": text,
            "pages": [
                {
                    "page": 1,
                    "text": text,
                    "needs_visual_review": False,
                }
            ],
            "page_count": 1,
        }

    raise ValueError(
        "Supported formats: PDF, DOCX, TXT, MD"
    )


def parse_pdf(
    path: str,
    filename: str,
) -> dict:

    import pymupdf

    document = pymupdf.open(
        path
    )

    pages = []

    for page_number, page in enumerate(
        document,
        start=1,
    ):

        text = (
            page.get_text("text")
            or ""
        ).strip()

        pages.append(
            {
                "page": page_number,
                "text": text,
                "needs_visual_review": (
                    len(text) < 200
                ),
            }
        )

    document.close()

    return {
        "filename": filename,
        "text": "\n\n".join(
            item["text"]
            for item in pages
        ),
        "pages": pages,
        "page_count": len(pages),
    }


def parse_docx(
    path: str,
    filename: str,
) -> dict:

    from docx import Document

    document = Document(
        path
    )

    blocks = []

    for paragraph in document.paragraphs:

        text = paragraph.text.strip()

        if text:
            blocks.append(text)

    for table in document.tables:

        for row in table.rows:

            row_text = " | ".join(
                cell.text.strip()
                for cell in row.cells
            )

            if row_text.strip():
                blocks.append(
                    row_text
                )

    text = "\n".join(
        blocks
    )

    return {
        "filename": filename,
        "text": text,
        "pages": [
            {
                "page": 1,
                "text": text,
                "needs_visual_review": False,
            }
        ],
        "page_count": None,
    }


def extract_title(
    text: str,
    filename: str,
) -> str:

    patterns = [
        (
            r"(?:title of research project|"
            r"research project title|"
            r"proposal title|project title)"
            r"\s*[:\-]?\s*([^\n]{8,200})"
        ),
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:

            candidate = (
                match.group(1)
                .strip()
            )

            if candidate:
                return candidate

    # Fallback:
    # first substantial line rather than
    # making up a document title.

    for line in text.splitlines():

        clean = line.strip()

        if (
            15 <= len(clean) <= 180
            and not clean.startswith("[")
        ):

            return clean

    return Path(filename).stem


def extract_concepts(
    text: str,
) -> list:

    concepts = []

    for pattern in TECHNICAL_PATTERNS:

        matches = re.findall(
            pattern,
            text,
            re.IGNORECASE,
        )

        for match in matches:

            concept = (
                match
                if isinstance(match, str)
                else match[0]
            )

            concept = (
                concept
                .strip()
                .lower()
            )

            if (
                concept
                and concept not in concepts
            ):
                concepts.append(
                    concept
                )

    return concepts[:12]


def analyze_page(
    page: dict,
) -> dict:

    text = page.get(
        "text",
        "",
    )

    lower = text.lower()

    sections = []

    for section in SECTION_NAMES:

        if section in lower:

            sections.append(
                section.title()
            )

    concepts = extract_concepts(
        text
    )

    claims = []

    kpis = []

    for line in text.splitlines():

        clean = line.strip()

        if len(clean) < 30:
            continue

        if CLAIM_PATTERN.search(
            clean
        ):

            claims.append(
                clean
            )

        if KPI_PATTERN.search(
            clean
        ):

            kpis.append(
                clean
            )

    return {
        "page": page.get(
            "page"
        ),
        "sections": sections[:8],
        "concepts": concepts,
        "claims": claims[:8],
        "kpis": kpis[:8],
        "needs_visual_review": (
            page.get(
                "needs_visual_review",
                False,
            )
        ),
        "text_preview": (
            text[:1200]
            if text
            else ""
        ),
    }


def build_document_dossier(
    parsed: dict,
) -> dict:

    text = parsed.get(
        "text",
        "",
    )

    title = extract_title(
        text,
        parsed.get(
            "filename",
            "proposal",
        ),
    )

    page_analysis = [
        analyze_page(page)
        for page in parsed.get(
            "pages",
            []
        )
    ]

    concepts = []

    claims = []

    kpis = []

    sections = []

    for page in page_analysis:

        for concept in page[
            "concepts"
        ]:

            if concept not in concepts:
                concepts.append(
                    concept
                )

        for claim in page[
            "claims"
        ]:

            claims.append(
                {
                    "page": page["page"],
                    "text": claim,
                }
            )

        for kpi in page[
            "kpis"
        ]:

            kpis.append(
                {
                    "page": page["page"],
                    "text": kpi,
                }
            )

        for section in page[
            "sections"
        ]:

            sections.append(
                {
                    "page": page["page"],
                    "name": section,
                }
            )

    return {
        "document": {
            "filename": parsed.get(
                "filename"
            ),
            "title": title,
            "pages": parsed.get(
                "page_count"
            ),
            "visual_review_pages": [
                page["page"]
                for page in page_analysis
                if page[
                    "needs_visual_review"
                ]
            ],
        },
        "concepts": concepts[:15],
        "claims": claims[:30],
        "kpis": kpis[:30],
        "sections": sections,
        "page_analysis": page_analysis,
        "raw_text": text,
    }
