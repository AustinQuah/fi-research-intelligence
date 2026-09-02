from pathlib import Path
import re


CLAIM_WORDS = re.compile(
    r"\b(?:novel|innovative|improve|improved|improvement|"
    r"increase|increased|reduce|reduced|reduction|enhance|"
    r"enhanced|higher|lower|target|achieve|achieved|"
    r"demonstrate|demonstrated|performance|efficiency|"
    r"efficient|optimise|optimize)\b",
    re.IGNORECASE,
)

KPI_PATTERN = re.compile(
    r"(?:\d+(?:\.\d+)?\s*%|"
    r"\$\s*\d+(?:\.\d+)?\s*[mkb]?|"
    r"\d+(?:\.\d+)?\s*(?:mg/l|g/l|kg/m3|m3/day|m³/day|"
    r"kwh|kw|mw|ppm|ppb|bar)|trl\s*\d+|"
    r"target\s*:\s*[^\n]+)",
    re.IGNORECASE,
)

CONCEPT_PATTERNS = [
    r"\bceramic membranes?\b",
    r"\breverse osmosis\b",
    r"\bmembrane bioreactor\b",
    r"\bmembranes?\b",
    r"\bdesalination\b",
    r"\bwastewater treatment\b",
    r"\bwastewater\b",
    r"\bwater treatment\b",
    r"\bwater reuse\b",
    r"\bultrafiltration\b",
    r"\bmicrofiltration\b",
    r"\bnanofiltration\b",
    r"\belectrocoagulation\b",
    r"\belectrowinning\b",
    r"\belectrochemical\b",
    r"\belectrolysis\b",
    r"\banaerobic digestion\b",
    r"\banaerobic\b",
    r"\badsorption\b",
    r"\badvanced oxidation\b",
    r"\boxidation\b",
    r"\bresource recovery\b",
    r"\bcarbon removal\b",
    r"\bcarbon capture\b",
    r"\bpfas\b",
    r"\bsludge\b",
    r"\bbiogas\b",
    r"\bdata centres?\b",
    r"\bsemiconductors?\b",
    r"\bwafer fabs?\b",
]

SECTION_NAMES = [
    "executive summary",
    "scientific abstract",
    "abstract",
    "background",
    "problem statement",
    "research objectives",
    "objectives",
    "methodology",
    "approach",
    "competitive analysis",
    "landscape scan",
    "literature review",
    "innovativeness",
    "innovation",
    "commercialisation",
    "commercialization",
    "milestones",
    "budget",
    "impact",
    "key performance indicators",
    "technical kpis",
    "kpis",
    "trl",
]


def parse_document(path: str, filename: str) -> dict:
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        return parse_pdf(path, filename)

    if suffix == ".docx":
        return parse_docx(path, filename)

    if suffix in {".txt", ".md"}:
        return parse_text(path, filename)

    raise ValueError(
        "Supported formats are PDF, DOCX, TXT and MD."
    )


def parse_pdf(path: str, filename: str) -> dict:
    import pymupdf

    document = pymupdf.open(path)
    pages = []

    try:
        for page_number, page in enumerate(
            document,
            start=1,
        ):
            text = (
                page.get_text(
                    "text",
                    sort=True,
                )
                or ""
            ).strip()

            images = page.get_images(
                full=True
            )

            pages.append(
                {
                    "page": page_number,
                    "text": text,
                    "text_length": len(text),
                    "has_images": bool(images),
                    "image_count": len(images),
                    "needs_visual_review": len(text) < 150,
                }
            )

    finally:
        document.close()

    full_text = "\n\n".join(
        page["text"]
        for page in pages
        if page["text"]
    )

    scanned_pages = [
        page["page"]
        for page in pages
        if page["needs_visual_review"]
    ]

    scanned_document = (
        len(full_text.strip())
        < max(
            300,
            len(pages) * 80,
        )
    )

    return {
        "filename": filename,
        "pages": pages,
        "page_count": len(pages),
        "text": full_text,
        "scanned_document": scanned_document,
        "scanned_pages": scanned_pages,
    }


def parse_docx(path: str, filename: str) -> dict:
    from docx import Document

    document = Document(path)
    parts = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            parts.append(text)

    for table in document.tables:
        for row in table.rows:
            row_text = " | ".join(
                cell.text.strip()
                for cell in row.cells
            )

            if row_text.strip():
                parts.append(row_text)

    text = "\n".join(parts)

    return {
        "filename": filename,
        "pages": [
            {
                "page": 1,
                "text": text,
                "text_length": len(text),
                "has_images": False,
                "image_count": 0,
                "needs_visual_review": False,
            }
        ],
        "page_count": 1,
        "text": text,
        "scanned_document": False,
        "scanned_pages": [],
    }


def parse_text(path: str, filename: str) -> dict:
    text = Path(path).read_text(
        encoding="utf-8",
        errors="ignore",
    )

    return {
        "filename": filename,
        "pages": [
            {
                "page": 1,
                "text": text,
                "text_length": len(text),
                "has_images": False,
                "image_count": 0,
                "needs_visual_review": False,
            }
        ],
        "page_count": 1,
        "text": text,
        "scanned_document": False,
        "scanned_pages": [],
    }


def extract_title(
    text: str,
    filename: str,
) -> str:
    pattern = (
        r"(?:proposal title|project title|research project title|"
        r"title of research project)\s*[:\-]?\s*([^\n]{8,200})"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE,
    )

    if match:
        return match.group(1).strip()

    for line in text.splitlines():
        line = line.strip()

        if 15 <= len(line) <= 180:
            return line

    return Path(filename).stem


def extract_concepts(
    text: str,
) -> list[str]:
    found = []

    for pattern in CONCEPT_PATTERNS:
        for match in re.findall(
            pattern,
            text,
            re.IGNORECASE,
        ):
            value = (
                str(match)
                .strip()
                .lower()
            )

            if (
                value
                and value not in found
            ):
                found.append(value)

    return found[:20]


def analyse_page(
    page: dict,
) -> dict:
    text = page.get(
        "text",
        "",
    )

    lower = text.lower()
    sections = []

    for name in SECTION_NAMES:
        if name in lower:
            display = name.title()

            if display not in sections:
                sections.append(display)

    concepts = extract_concepts(text)
    claims = []
    kpis = []

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if len(line) < 20:
            continue

        if (
            CLAIM_WORDS.search(line)
            and line not in claims
        ):
            claims.append(line)

        if (
            KPI_PATTERN.search(line)
            and line not in kpis
        ):
            kpis.append(line)

        if (
            len(claims) >= 10
            and len(kpis) >= 10
        ):
            break

    return {
        "page": page["page"],
        "text_length": page["text_length"],
        "has_images": page["has_images"],
        "image_count": page["image_count"],
        "needs_visual_review": page[
            "needs_visual_review"
        ],
        "sections": sections[:10],
        "concepts": concepts[:15],
        "claims": claims[:10],
        "kpis": kpis[:10],
        "text_preview": text[:1800],
    }


def deduplicate_items(
    items: list[dict],
) -> list[dict]:
    result = []
    seen = set()

    for item in items:
        text = (
            item.get(
                "text",
                "",
            )
            .strip()
            .lower()
        )

        if (
            not text
            or text in seen
        ):
            continue

        seen.add(text)
        result.append(item)

    return result


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

    if not text.strip():
        return {
            "status": "needs_visual_processing",
            "document": {
                "filename": filename,
                "title": Path(filename).stem,
                "pages": parsed.get(
                    "page_count"
                ),
                "scanned_document": True,
                "scanned_pages": parsed.get(
                    "scanned_pages",
                    [],
                ),
            },
            "concepts": [],
            "claims": [],
            "kpis": [],
            "sections": [],
            "page_analysis": [],
        }

    page_analysis = [
        analyse_page(page)
        for page in parsed.get(
            "pages",
            [],
        )
    ]

    concepts = []
    claims = []
    kpis = []
    sections = []

    for page in page_analysis:
        page_number = page["page"]

        for concept in page["concepts"]:
            if concept not in concepts:
                concepts.append(concept)

        for claim in page["claims"]:
            claims.append(
                {
                    "page": page_number,
                    "text": claim,
                }
            )

        for kpi in page["kpis"]:
            kpis.append(
                {
                    "page": page_number,
                    "text": kpi,
                }
            )

        for section in page["sections"]:
            sections.append(
                {
                    "page": page_number,
                    "name": section,
                }
            )

    return {
        "status": "ready",
        "document": {
            "filename": filename,
            "title": extract_title(
                text,
                filename,
            ),
            "pages": parsed.get(
                "page_count"
            ),
            "scanned_document": parsed.get(
                "scanned_document",
                False,
            ),
            "scanned_pages": parsed.get(
                "scanned_pages",
                [],
            ),
        },
        "concepts": concepts[:20],
        "claims": deduplicate_items(
            claims
        )[:40],
        "kpis": deduplicate_items(
            kpis
        )[:40],
        "sections": sections,
        "page_analysis": page_analysis,
    }
