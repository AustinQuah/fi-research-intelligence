import asyncio
import re
from urllib.parse import quote

import httpx


CACHE: dict[str, dict] = {}


def tokenize(
    text: str,
) -> set[str]:

    words = re.findall(
        r"[a-zA-Z0-9]{3,}",
        text.lower(),
    )

    stop_words = {
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
        if word not in stop_words
    }


def similarity(
    left_text: str,
    right_text: str,
) -> float:

    left = tokenize(
        left_text
    )

    right = tokenize(
        right_text
    )

    if not left or not right:
        return 0.0

    union = (
        left
        | right
    )

    intersection = (
        left
        & right
    )

    return (
        len(intersection)
        / len(union)
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
                "FI-Research-Intelligence/6.0"
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
                        1.5
                        * (
                            attempt
                            + 1
                        )
                    )

                    continue

                response.raise_for_status()

            except httpx.HTTPError:

                if attempt == 2:
                    raise

                await asyncio.sleep(
                    0.75
                    * (
                        attempt
                        + 1
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

        queries.append(
            concept
        )

    if len(concepts) >= 2:

        queries.append(
            (
                f"{concepts[0]} "
                f"{concepts[1]}"
            )
        )

    claims = dossier.get(
        "claims",
        [],
    )

    for claim in claims[:3]:

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

    cleaned = []
    seen = set()

    for query in queries:

        query = query.strip()

        normalized = query.lower()

        if (
            query
            and normalized not in seen
        ):

            seen.add(
                normalized
            )

            cleaned.append(
                query
            )

    return cleaned[:8]


def reconstruct_abstract(
    inverted_index,
) -> str:

    if not inverted_index:
        return ""

    positions = []

    for word, indexes in (
        inverted_index.items()
    ):

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

    data = await get_json(
        url
    )

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
                    item.get(
                        "title"
                    )
                    or "Untitled"
                ),
                "year": item.get(
                    "publication_year"
                ),
                "citations": item.get(
                    "cited_by_count",
                    0,
                ),
                "doi": item.get(
                    "doi"
                ),
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

    data = await get_json(
        url
    )

    items = (
        data.get(
            "message",
            {},
        )
        .get(
            "items",
            [],
        )
    )

    results = []

    for item in items:

        titles = (
            item.get(
                "title"
            )
            or ["Untitled"]
        )

        doi = item.get(
            "DOI"
        )

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

        year = None

        if (
            date_parts
            and date_parts[0]
        ):

            year = date_parts[0][0]

        results.append(
            {
                "source": "Crossref",
                "title": titles[0],
                "year": year,
                "citations": item.get(
                    "is-referenced-by-count",
                    0,
                ),
                "doi": doi,
                "url": (
                    item.get(
                        "URL"
                    )
                    or (
                        f"https://doi.org/{doi}"
                        if doi
                        else None
                    )
                ),
                "abstract": (
                    item.get(
                        "abstract"
                    )
                    or ""
                ),
            }
        )

    return results


def make_links(
    query: str,
) -> dict:

    encoded = quote(
        query
    )

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

    openalex_results = []
    crossref_results = []

    try:

        openalex_results = (
            await search_openalex(
                query,
                5,
            )
        )

    except Exception as error:

        errors.append(
            f"OpenAlex: {error}"
        )

    try:

        crossref_results = (
            await search_crossref(
                query,
                5,
            )
        )

    except Exception as error:

        errors.append(
            f"Crossref: {error}"
        )

    combined = (
        openalex_results
        + crossref_results
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

        unique.append(
            item
        )

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
        "links": make_links(
            query
        ),
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

        result = await research_query(
            query
        )

        evidence.append(
            result
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

    proposal_text = (
        " ".join(
            concepts
        )
        or
        dossier.get(
            "document",
            {},
        ).get(
            "title",
            "",
        )
    )

    paper_texts = [
        (
            f"{paper.get('title', '')} "
            f"{paper.get('abstract', '')}"
        )
        for paper in papers
    ]

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
        (
            1
            - max_similarity
        )
        * 100,
        1,
    )

    prior_art_distance = max(
        0.0,
        min(
            100.0,
            prior_art_distance,
        )
    )

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
            (
                1
                - coverage
            )
            * 100
        )

    concept_novelty = round(
        (
            sum(
                concept_scores
            )
            / len(
                concept_scores
            )
        )
        if concept_scores
        else 50.0,
        1,
    )

    claim_scores = []

    for claim in claims[:10]:

        claim_text = claim.get(
            "text",
            "",
        )

        closest = max(
            [
                similarity(
                    claim_text,
                    text,
                )
                for text in paper_texts
            ]
            or [0.0]
        )

        claim_scores.append(
            (
                1
                - closest
            )
            * 100
        )

    claim_novelty = round(
        (
            sum(
                claim_scores
            )
            / len(
                claim_scores
            )
        )
        if claim_scores
        else 50.0,
        1,
    )

    patent_distance = None

    query_count = len(
        evidence
    )

    paper_count = len(
        papers
    )

    successful_queries = sum(
        1
        for group in evidence
        if (
            group.get(
                "papers"
            )
            and not group.get(
                "errors"
            )
        )
    )

    confidence = min(
        100.0,
        (
            min(
                query_count,
                8,
            )
            / 8
            * 45
        )
        + (
            min(
                paper_count,
                40,
            )
            / 40
            * 35
        )
        + (
            successful_queries
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

    components = [
        (
            "Prior-art distance",
            prior_art_distance,
            35,
            True,
        ),
        (
            "Patent distance",
            patent_distance,
            25,
            False,
        ),
        (
            "Concept novelty",
            concept_novelty,
            20,
            True,
        ),
        (
            "Claim novelty",
            claim_novelty,
            15,
            True,
        ),
        (
            "Evidence confidence",
            confidence,
            5,
            True,
        ),
    ]

    measured_weight = sum(
        weight
        for _, score, weight, measured
        in components
        if measured
        and score is not None
    )

    weighted_total = sum(
        score * weight
        for _, score, weight, measured
        in components
        if measured
        and score is not None
    )

    score = round(
        weighted_total
        / measured_weight
        if measured_weight
        else 50.0,
        1,
    )

    if score >= 80:
        classification = "Very High"

    elif score >= 65:
        classification = "High"

    elif score >= 45:
        classification = "Moderate"

    else:
        classification = "Low"

    closest = []

    for paper, sim in sorted(
        zip(
            papers,
            similarities,
        ),
        key=lambda pair:
            pair[1],
        reverse=True,
    )[:5]:

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
                        1
                        - sim
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
                    "Distance from the closest "
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
                    "and retrieved research evidence."
                ),
            },
            "evidence_confidence": {
                "score": confidence,
                "weight": 5,
                "measured": True,
                "description": (
                    "Coverage and success of the "
                    "research retrieval pass."
                ),
            },
        },
        "evidence": {
            "query_count": query_count,
            "paper_count": paper_count,
            "successful_query_groups": (
                successful_queries
            ),
            "closest_prior_work": closest,
        },
        "methodology": (
            "The novelty score is a screening measure based "
            "on retrieved evidence. It is not a legal patent "
            "novelty opinion and is not a funding recommendation."
        ),
    }
