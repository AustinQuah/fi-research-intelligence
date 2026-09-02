import asyncio
import re
from urllib.parse import quote

import httpx


CACHE: dict[str, dict] = {}


def tokenize(text: str) -> set[str]:
    words = re.findall(
        r"[a-zA-Z0-9]{3,}",
        text.lower(),
    )

    stop = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "into",
        "using",
        "use",
        "are",
        "was",
        "were",
        "will",
        "can",
        "than",
        "their",
        "there",
        "about",
        "have",
        "has",
        "been",
        "being",
        "but",
        "our",
        "they",
        "them",
        "which",
        "such",
        "more",
        "less",
        "also",
        "through",
        "based",
        "system",
        "process",
        "proposed",
        "study",
    }

    return {
        word
        for word in words
        if word not in stop
    }


def similarity(
    a: str,
    b: str,
) -> float:
    left = tokenize(a)
    right = tokenize(b)

    if not left or not right:
        return 0.0

    return (
        len(left & right)
        / len(left | right)
    )


async def get_json(
    url: str,
) -> dict:
    if url in CACHE:
        return CACHE[url]

    async with httpx.AsyncClient(
        timeout=15,
        follow_redirects=True,
        headers={
            "Accept": "application/json",
            "User-Agent": (
                "FI-Research-Intelligence/1.0"
            ),
        },
    ) as client:
        for attempt in range(3):
            try:
                response = await client.get(
                    url
                )

                if response.status_code == 200:
                    data = response.json()
                    CACHE[url] = data
                    return data

                if response.status_code == 429:
                    await asyncio.sleep(
                        1.5 * (
                            attempt + 1
                        )
                    )
                    continue

                response.raise_for_status()

            except httpx.HTTPError:
                if attempt == 2:
                    raise

                await asyncio.sleep(
                    0.75 * (
                        attempt + 1
                    )
                )

    raise RuntimeError(
        "Research provider unavailable."
    )


def build_queries(
    dossier: dict,
) -> list[str]:
    concepts = dossier.get(
        "concepts",
        [],
    )

    queries = []

    if concepts:
        queries.append(
            " ".join(
                concepts[:3]
            )
        )

    for concept in concepts[:5]:
        queries.append(concept)

    if len(concepts) >= 2:
        queries.append(
            f"{concepts[0]} {concepts[1]}"
        )

    for claim in dossier.get(
        "claims",
        [],
    )[:2]:
        text = claim.get(
            "text",
            "",
        )

        words = text.split()

        if len(words) >= 5:
            queries.append(
                " ".join(
                    words[:14]
                )
            )

    clean = []
    seen = set()

    for query in queries:
        normalized = (
            query
            .strip()
            .lower()
        )

        if (
            normalized
            and normalized not in seen
        ):
            seen.add(normalized)
            clean.append(
                query.strip()
            )

    return clean[:6]


def reconstruct_abstract(
    inverted: dict | None,
) -> str:
    if not inverted:
        return ""

    positions = []

    for word, indexes in inverted.items():
        for index in indexes:
            positions.append(
                (
                    index,
                    word,
                )
            )

    positions.sort()

    return " ".join(
        word
        for _, word in positions
    )


async def search_openalex(
    query: str,
    limit: int = 5,
) -> list[dict]:
    url = (
        "https://api.openalex.org/works"
        f"?search={quote(query)}"
        "&filter=from_publication_date:2018-01-01"
        f"&per-page={limit}"
    )

    data = await get_json(url)
    results = []

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

        results.append(
            {
                "source": "OpenAlex",
                "title": (
                    item.get("title")
                    or "Untitled"
                ),
                "year": item.get(
                    "publication_year"
                ),
                "citations": item.get(
                    "cited_by_count",
                    0,
                ),
                "doi": item.get("doi"),
                "url": (
                    location.get(
                        "landing_page_url"
                    )
                    or item.get("doi")
                    or item.get("id")
                ),
                "abstract": reconstruct_abstract(
                    item.get(
                        "abstract_inverted_index"
                    )
                ),
            }
        )

    return results


async def search_crossref(
    query: str,
    limit: int = 5,
) -> list[dict]:
    url = (
        "https://api.crossref.org/works"
        f"?query.bibliographic={quote(query)}"
        "&filter=from-pub-date:2018-01-01"
        f"&rows={limit}"
    )

    data = await get_json(url)
    results = []

    for item in (
        data.get(
            "message",
            {},
        )
        .get(
            "items",
            [],
        )
    ):
        title = (
            item.get("title")
            or ["Untitled"]
        )[0]

        doi = item.get("DOI")

        date_parts = (
            item.get(
                "published",
                {},
            )
            .get(
                "date-parts",
                [[None]],
            )
        )

        year = (
            date_parts[0][0]
            if date_parts
            and date_parts[0]
            else None
        )

        results.append(
            {
                "source": "Crossref",
                "title": title,
                "year": year,
                "citations": item.get(
                    "is-referenced-by-count",
                    0,
                ),
                "doi": doi,
                "url": (
                    item.get("URL")
                    or (
                        f"https://doi.org/{doi}"
                        if doi
                        else None
                    )
                ),
                "abstract": (
                    item.get("abstract")
                    or ""
                ),
            }
        )

    return results


def make_links(
    query: str,
) -> dict:
    encoded = quote(query)

    return {
        "google_scholar": (
            "https://scholar.google.com/"
            f"scholar?q={encoded}"
        ),
        "google_patents": (
            "https://patents.google.com/"
            f"?q={encoded}"
        ),
        "semantic_scholar": (
            "https://www.semanticscholar.org/"
            "search?"
            f"q={encoded}"
        ),
        "wipo": (
            "https://patentscope.wipo.int/"
            "search/en/result.jsf?"
            f"query={encoded}"
        ),
    }


async def research_query(
    query: str,
) -> dict:
    errors = []
    openalex = []
    crossref = []

    try:
        openalex = await search_openalex(
            query,
            5,
        )

    except Exception as error:
        errors.append(
            f"OpenAlex: {error}"
        )

    try:
        crossref = await search_crossref(
            query,
            5,
        )

    except Exception as error:
        errors.append(
            f"Crossref: {error}"
        )

    combined = (
        openalex
        + crossref
    )

    unique = []
    seen = set()

    for item in combined:
        key = (
            item.get("doi")
            or item.get("url")
            or item.get("title")
            or ""
        ).lower()

        if (
            not key
            or key in seen
        ):
            continue

        seen.add(key)
        unique.append(item)

    unique.sort(
        key=lambda item:
            item.get(
                "citations",
                0,
            ),
        reverse=True,
    )

    return {
        "query": query,
        "links": make_links(query),
        "papers": unique[:10],
        "errors": errors,
    }


async def run_research(
    dossier: dict,
) -> dict:
    queries = build_queries(
        dossier
    )

    evidence = []

    for query in queries:
        evidence.append(
            await research_query(
                query
            )
        )

        await asyncio.sleep(
            0.2
        )

    return {
        "status": "complete",
        "queries": queries,
        "evidence": evidence,
    }


def calculate_novelty(
    dossier: dict,
    research: dict,
) -> dict:
    evidence = research.get(
        "evidence",
        [],
    )

    papers = []

    for group in evidence:
        papers.extend(
            group.get(
                "papers",
                [],
            )
        )

    concepts = dossier.get(
        "concepts",
        [],
    )

    claims = dossier.get(
        "claims",
        [],
    )

    paper_texts = [
        (
            f"{item.get('title', '')} "
            f"{item.get('abstract', '')}"
        )
        for item in papers
    ]

    # Prior-art distance
    proposal_text = " ".join(
        concepts
    )

    if not proposal_text:
        proposal_text = (
            dossier.get(
                "document",
                {},
            )
            .get(
                "title",
                "",
            )
        )

    similarities = [
        similarity(
            proposal_text,
            text,
        )
        for text in paper_texts
    ]

    max_similarity = max(
        similarities,
        default=0.0,
    )

    prior_art_distance = round(
        max(
            0.0,
            min(
                100.0,
                (
                    1.0
                    - max_similarity
                )
                * 100,
            ),
        ),
        1,
    )

    # Concept novelty
    concept_scores = []

    for concept in concepts:
        count = sum(
            1
            for text in paper_texts
            if concept.lower()
            in text.lower()
        )

        coverage = (
            count
            / max(
                1,
                len(paper_texts),
            )
        )

        concept_scores.append(
            max(
                0.0,
                min(
                    100.0,
                    (
                        1.0
                        - coverage
                    )
                    * 100,
                ),
            )
        )

    concept_novelty = round(
        (
            sum(concept_scores)
            / len(concept_scores)
        )
        if concept_scores
        else 50.0,
        1,
    )

    # Claim novelty
    claim_distances = []

    for claim in claims[:10]:
        claim_text = claim.get(
            "text",
            "",
        )

        claim_similarity = max(
            [
                similarity(
                    claim_text,
                    text,
                )
                for text in paper_texts
            ]
            or [0.0]
        )

        claim_distances.append(
            max(
                0.0,
                min(
                    100.0,
                    (
                        1.0
                        - claim_similarity
                    )
                    * 100,
                ),
            )
        )

    claim_novelty = round(
        (
            sum(claim_distances)
            / len(claim_distances)
        )
        if claim_distances
        else 50.0,
        1,
    )

    # Patent similarity isn't implemented yet.
    patent_distance = None

    # Evidence confidence
    query_count = len(evidence)
    paper_count = len(papers)

    successful_groups = sum(
        1
        for group in evidence
        if (
            not group.get("errors")
            and group.get("papers")
        )
    )

    confidence = min(
        100.0,
        (
            query_count
            / 6
            * 45
        )
        + (
            min(
                paper_count,
                30,
            )
            / 30
            * 35
        )
        + (
            successful_groups
            / max(
                1,
                query_count,
            )
            * 20
        ),
    )

    confidence = round(
        confidence,
        1,
    )

    # Reweight only measured components.
    weighted_components = [
        (
            prior_art_distance,
            35,
        ),
        (
            concept_novelty,
            20,
        ),
        (
            claim_novelty,
            15,
        ),
        (
            confidence,
            5,
        ),
    ]

    total_weight = sum(
        weight
        for _, weight
        in weighted_components
    )

    score = round(
        (
            sum(
                value * weight
                for value, weight
                in weighted_components
            )
            / total_weight
        ),
        1,
    )

    if score >= 80:
        classification = (
            "Very High"
        )

    elif score >= 65:
        classification = "High"

    elif score >= 45:
        classification = (
            "Moderate"
        )

    else:
        classification = "Low"

    closest = []
    scored = []

    for paper, sim in zip(
        papers,
        similarities,
    ):
        scored.append(
            (
                sim,
                paper,
            )
        )

    scored.sort(
        key=lambda pair:
            pair[0],
        reverse=True,
    )

    for sim, paper in scored[:5]:
        closest.append(
            {
                "title": paper.get(
                    "title"
                ),
                "source": paper.get(
                    "source"
                ),
                "year": paper.get(
                    "year"
                ),
                "similarity": round(
                    sim * 100,
                    1,
                ),
                "distance": round(
                    (
                        1 - sim
                    )
                    * 100,
                    1,
                ),
                "url": paper.get(
                    "url"
                ),
            }
        )

    return {
        "score": score,
        "confidence": confidence,
        "classification": classification,
        "components": {
            "prior_art_distance": {
                "score": prior_art_distance,
                "weight": 35,
                "measured": True,
                "description": (
                    "Lexical distance from the closest "
                    "retrieved research evidence."
                ),
            },
            "patent_distance": {
                "score": patent_distance,
                "weight": 25,
                "measured": False,
                "description": (
                    "Patent similarity is not yet "
                    "measured in this MVP."
                ),
            },
            "concept_novelty": {
                "score": concept_novelty,
                "weight": 20,
                "measured": True,
                "description": (
                    "Rarity of extracted technical "
                    "concepts within retrieved evidence."
                ),
            },
            "claim_novelty": {
                "score": claim_novelty,
                "weight": 15,
                "measured": True,
                "description": (
                    "Distance between extracted claims "
                    "and retrieved evidence."
                ),
            },
            "evidence_confidence": {
                "score": confidence,
                "weight": 5,
                "measured": True,
                "description": (
                    "Coverage and success of the "
                    "retrieval pass."
                ),
            },
        },
        "evidence": {
            "query_count": query_count,
            "paper_count": paper_count,
            "successful_query_groups": (
                successful_groups
            ),
            "closest_prior_work": closest,
        },
        "methodology": (
            "This is an evidence-based screening score, "
            "not a funding recommendation. Patent distance "
            "is excluded from the numerical calculation "
            "until patent similarity is implemented. "
            "Measured components are renormalised over "
            "their available weights."
        ),
    }
