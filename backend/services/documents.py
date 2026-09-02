from pathlib import Path
import re


# ============================================================
# CONFIGURATION
# ============================================================

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
    r"\bpfas\b",
    r"\bsludge\b",
    r"\bbiogas\b",
]


CLAIM_PATTERN = re.compile(
    r"\b("
    r"novel|"
    r"innovative|"
    r"improve|"
    r"improved|"
    r"improvement|"
    r"increase|"
    r"increased|"
    r"reduce|"
    r"reduced|"
    r"reduction|"
    r"achieve|"
    r"achieved|"
    r"target|"
    r"demonstrate|"
    r"demonstrated|"
    r"performance|"
    r"efficiency|"
    r"higher|"
    r"lower|"
    r"enhance|"
    r"enhanced"
    r")\b",
    re.IGNORECASE,
)


KPI_PATTERN = re.compile(
    r"("
    r"\d+(?:\.\d+)?\s*%|"
    r"\d+(?:\.\d+)?\s*"
    r"(?:"
    r"mg\/l|"
    r"g\/l|"
    r"kg\/m3|"
    r"m3\/day|"
    r"m³\/day|"
    r"bar|"
    r"kwh|"
    r"kw|"
    r"mw|"
    r"ppm|"
    r"ppb"
    r")|"
    r"trl\s*\d+"
    r")",
    re.IGNORECASE,
)


# ============================================================
# DOCUMENT ROUTER
# ============================================================

def parse_document(
    path: str,
    filename: str,
) -> dict:

    suffix = Path(
        filename
    ).suffix.lower()

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
        return parse_text(
            path,
            filename,
        )

    raise ValueError(
        "Supported formats: PDF, DOCX, TXT, MD"
    )


# ============================================================
# PDF
# ============================================================

def parse_pdf(
    path: str,
    filename: str,
) -> dict:

    import pymupdf

    document = pymupdf.open(
        path
    )

    pages = []

    try:

        for page_number, page in enumerate(
            document,
            start=1,
        ):

            text = (
                page
                .get_text("text")
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

    finally:

        document.close()

    return {
        "filename": filename,
        "text": "\n\n".join(
            page["text"]
            for page in pages
        ),
        "pages": pages,
        "page_count": len(
            pages
        ),
    }


# ============================================================
# DOCX
# ============================================================

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

        text = (
            paragraph
            .text
            .strip()
        )

        if text:
            blocks.append(
                text
            )

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


# ============================================================
# TXT / MARKDOWN
# ============================================================

def parse_text(
    path: str,
    filename: str,
) -> dict:

    text = Path(
        path
    ).read_text(
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


# ============================================================
# TITLE EXTRACTION
# ============================================================

def extract_title(
    text: str,
    filename: str,
) -> str:

    title_patterns = [
        (
            r"(?:"
            r"title of research project|"
            r"research project title|"
            r"proposal title|"
            r"project title"
            r")"
            r"\s*[:\-]?\s*"
            r"([^\n]{8,200})"
        ),
    ]

    for pattern in title_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:

            candidate = (
                match
                .group(1)
                .strip()
            )

            if candidate:
                return candidate

    # --------------------------------------------------------
    # Fallback:
    # use the first substantial line.
    # --------------------------------------------------------

    for line in text.splitlines():

        clean = (
            line
            .strip()
        )

        if (
            15 <= len(clean) <= 180
            and not clean.startswith("[")
        ):
            return clean

    return Path(
        filename
    ).stem


# ============================================================
# TECHNICAL CONCEPT EXTRACTION
# ============================================================

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

            if isinstance(
                match,
                tuple,
            ):

                concept = (
                    match[0]
                    if match
                    else ""
                )

            else:

                concept = match

            concept = (
                str(concept)
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

    return concepts[:15]


# ============================================================
# PAGE ANALYSIS
# ============================================================

def analyze_page(
    page: dict,
) -> dict:

    text = page.get(
        "text",
        "",
    )

    lower = text.lower()

    # --------------------------------------------------------
    # Sections
    # --------------------------------------------------------

    sections = []

    for section in SECTION_NAMES:

        if section in lower:

            display_name = (
                section
                .title()
            )

            if (
                display_name
                not in sections
            ):

                sections.append(
                    display_name
                )

    # --------------------------------------------------------
    # Technical concepts
    # --------------------------------------------------------

    concepts = extract_concepts(
        text
    )

    # --------------------------------------------------------
    # Claims
    # --------------------------------------------------------

    claims = []

    # --------------------------------------------------------
    # KPIs
    # --------------------------------------------------------

    kpis = []

    for line in text.splitlines():

        clean = (
            line
            .strip()
        )

        if len(clean) < 30:
            continue

        # ----------------------------------------------------
        # Claim signal
        # ----------------------------------------------------

        if CLAIM_PATTERN.search(
            clean
        ):

            if clean not in claims:

                claims.append(
                    clean
                )

        # ----------------------------------------------------
        # KPI signal
        # ----------------------------------------------------

        if KPI_PATTERN.search(
            clean
        ):

            if clean not in kpis:

                kpis.append(
                    clean
                )

        if (
            len(claims) >= 8
            and len(kpis) >= 8
        ):
            break

    return {
        "page": page.get(
            "page"
        ),
        "sections": sections[:8],
        "concepts": concepts[:12],
        "claims": claims[:8],
        "kpis": kpis[:8],
        "needs_visual_review": page.get(
            "needs_visual_review",
            False,
        ),
        "text_preview": (
            text[:1200]
            if text
            else ""
        ),
    }


# ============================================================
# FULL DOCUMENT DOSSIER
# ============================================================

def build_document_dossier(
    parsed: dict,
) -> dict:

    text = parsed.get(
        "text",
        "",
    )

    filename = parsed.get(
        "filename",
        "proposal",
    )

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    title = extract_title(
        text,
        filename,
    )

    # --------------------------------------------------------
    # Analyse every page
    # --------------------------------------------------------

    page_analysis = [
        analyze_page(
            page
        )
        for page in parsed.get(
            "pages",
            []
        )
    ]

    # --------------------------------------------------------
    # Aggregate document-level information
    # --------------------------------------------------------

    concepts = []

    claims = []

    kpis = []

    sections = []

    visual_review_pages = []

    # --------------------------------------------------------
    # Page aggregation
    # --------------------------------------------------------

    for page in page_analysis:

        page_number = page.get(
            "page"
        )

        # ----------------------------------------------------
        # Concepts
        # ----------------------------------------------------

        for concept in page.get(
            "concepts",
            [],
        ):

            if concept not in concepts:

                concepts.append(
                    concept
                )

        # ----------------------------------------------------
        # Claims
        # ----------------------------------------------------

        for claim in page.get(
            "claims",
            [],
        ):

            claims.append(
                {
                    "page": page_number,
                    "text": claim,
                }
            )

        # ----------------------------------------------------
        # KPIs
        # ----------------------------------------------------

        for kpi in page.get(
            "kpis",
            [],
        ):

            kpis.append(
                {
                    "page": page_number,
                    "text": kpi,
                }
            )

        # ----------------------------------------------------
        # Sections
        # ----------------------------------------------------

        for section in page.get(
            "sections",
            [],
        ):

            sections.append(
                {
                    "page": page_number,
                    "name": section,
                }
            )

        # ----------------------------------------------------
        # Visual review
        # ----------------------------------------------------

        if page.get(
            "needs_visual_review",
            False,
        ):

            visual_review_pages.append(
                page_number
            )

    # --------------------------------------------------------
    # Remove duplicate claims
    # --------------------------------------------------------

    unique_claims = []

    seen_claims = set()

    for claim in claims:

        key = (
            claim.get(
                "text",
                "",
            )
            .strip()
            .lower()
        )

        if (
            not key
            or key in seen_claims
        ):
            continue

        seen_claims.add(
            key
        )

        unique_claims.append(
            claim
        )

    # --------------------------------------------------------
    # Remove duplicate KPIs
    # --------------------------------------------------------

    unique_kpis = []

    seen_kpis = set()

    for kpi in kpis:

        key = (
            kpi.get(
                "text",
                "",
            )
            .strip()
            .lower()
        )

        if (
            not key
            or key in seen_kpis
        ):
            continue

        seen_kpis.add(
            key
        )

        unique_kpis.append(
            kpi
        )

    # --------------------------------------------------------
    # Remove duplicate section/page combinations
    # --------------------------------------------------------

    unique_sections = []

    seen_sections = set()

    for section in sections:

        key = (
            section.get(
                "page"
            ),
            section.get(
                "name"
            ),
        )

        if key in seen_sections:
            continue

        seen_sections.add(
            key
        )

        unique_sections.append(
            section
        )

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    return {

        "document": {

            "filename":
                filename,

            "title":
                title,

            "pages":
                parsed.get(
                    "page_count"
                ),

            "visual_review_pages":
                visual_review_pages,

        },

        "concepts":
            concepts[:15],

        "claims":
            unique_claims[:30],

        "kpis":
            unique_kpis[:30],

        "sections":
            unique_sections,

        "page_analysis":
            page_analysis,

        "raw_text":
            text,

    }
