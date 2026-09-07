from __future__ import annotations

from urllib.parse import quote
import re


def clean_phrase(value: str) -> str:
    value = re.sub(
        r"\s+",
        " ",
        value.strip(),
    )

    return value


def quote_phrase(value: str) -> str:
    return f'"{clean_phrase(value)}"'


def unique_queries(
    queries: list[str],
    limit: int = 12,
) -> list[str]:

    result = []
    seen = set()

    for query in queries:

        query = clean_phrase(
            query
        )

        normalized = query.lower()

        if (
            not query
            or normalized in seen
        ):
            continue

        seen.add(normalized)
        result.append(query)

        if len(result) >= limit:
            break

    return result


def extract_terms(
    dossier: dict,
) -> tuple[list[str], list[str]]:
    concepts = [
        clean_phrase(str(value))
        for value in dossier.get(
            "concepts",
            [],
        )
    ]

    claims = []

    for item in dossier.get(
        "claims",
        [],
    ):

        text = clean_phrase(
            item.get(
                "text",
                "",
            )
        )

        if text:
            claims.append(
                text
            )

    return concepts, claims


def build_core_queries(
    concepts: list[str],
) -> list[str]:

    queries = []

    for concept in concepts[:6]:

        queries.append(
            quote_phrase(
                concept
            )
        )

    if len(concepts) >= 2:

        queries.append(
            (
                quote_phrase(
                    concepts[0]
                )
                + " AND "
                + quote_phrase(
                    concepts[1]
                )
            )
        )

    if len(concepts) >= 3:

        queries.append(
            (
                quote_phrase(
                    concepts[0]
                )
                + " AND "
                + quote_phrase(
                    concepts[1]
                )
                + " AND "
                + quote_phrase(
                    concepts[2]
                )
            )
        )

    return queries


def build_application_queries(
    concepts: list[str],
) -> list[str]:

    if not concepts:
        return []

    base = concepts[0]

    templates = [
        f"{quote_phrase(base)} AND system",
        f"{quote_phrase(base)} AND method",
        f"{quote_phrase(base)} AND process",
        f"{quote_phrase(base)} AND apparatus",
        f"{quote_phrase(base)} AND treatment",
        f"{quote_phrase(base)} AND industrial",
        f"{quote_phrase(base)} AND commercial",
        f"{quote_phrase(base)} AND deployment",
    ]

    if len(concepts) >= 2:

        templates.extend(
            [
                (
                    f"{quote_phrase(base)} AND "
                    f"{quote_phrase(concepts[1])}"
                ),
                (
                    f"{quote_phrase(base)} AND "
                    f"{quote_phrase(concepts[1])} AND system"
                ),
            ]
        )

    return templates


def build_performance_queries(
    concepts: list[str],
    claims: list[str],
) -> list[str]:

    queries = []

    performance_terms = [
        "efficiency",
        "energy consumption",
        "energy reduction",
        "performance",
        "fouling",
        "recovery",
        "throughput",
        "durability",
        "selectivity",
        "cost reduction",
    ]

    base = (
        concepts[0]
        if concepts
        else ""
    )

    if base:

        for term in performance_terms:

            queries.append(
                (
                    f"{quote_phrase(base)} AND "
                    f"{quote_phrase(term)}"
                )
            )

    for claim in claims[:3]:

        words = claim.split()

        important = [
            word
            for word in words
            if len(word) > 4
        ]

        if important:

            queries.append(
                " AND ".join(
                    quote_phrase(word)
                    for word in important[:5]
                )
            )

    return queries


def build_competitor_queries(
    concepts: list[str],
) -> list[str]:

    if not concepts:
        return []

    base = concepts[0]

    alternative_terms = [
        "alternative",
        "conventional",
        "existing technology",
        "competing technology",
        "prior art",
        "replacement",
        "substitute",
        "incumbent",
    ]

    return [
        (
            f"{quote_phrase(base)} AND "
            f"{quote_phrase(term)}"
        )
        for term in alternative_terms
    ]


def build_patent_queries(
    dossier: dict,
) -> dict:

    concepts, claims = extract_terms(
        dossier
    )

    core = build_core_queries(
        concepts
    )

    application = build_application_queries(
        concepts
    )

    performance = build_performance_queries(
        concepts,
        claims,
    )

    competitor = build_competitor_queries(
        concepts
    )

    return {
        "core": unique_queries(
            core,
            8,
        ),
        "application": unique_queries(
            application,
            10,
        ),
        "performance": unique_queries(
            performance,
            10,
        ),
        "competitor": unique_queries(
            competitor,
            8,
        ),
    }


def google_patents_url(
    query: str,
) -> str:

    return (
        "https://patents.google.com/"
        f"?q={quote(query)}"
    )


def wipo_url(
    query: str,
) -> str:

    return (
        "https://patentscope.wipo.int/"
        "search/en/result.jsf?"
        f"query={quote(query)}"
    )


def espacenet_url(
    query: str,
) -> str:

    return (
        "https://worldwide.espacenet.com/"
        "patent/search?"
        f"q={quote(query)}"
    )


def uspto_url(
    query: str,
) -> str:

    return (
        "https://ppubs.uspto.gov/"
        f"pubwebapp/static/pages/search.html"
        f"?query={quote(query)}"
    )


def build_patent_workspace(
    dossier: dict,
) -> dict:

    query_groups = build_patent_queries(
        dossier
    )

    sources = [
        {
            "id": "google_patents",
            "name": "Google Patents",
            "description": (
                "Broad global patent search with "
                "fast full-text discovery."
            ),
        },
        {
            "id": "wipo",
            "name": "WIPO PATENTSCOPE",
            "description": (
                "International/PCT-focused search "
                "with advanced patent query operators."
            ),
        },
        {
            "id": "espacenet",
            "name": "EPO Espacenet",
            "description": (
                "Worldwide patent collection with "
                "classification and family information."
            ),
        },
        {
            "id": "uspto",
            "name": "USPTO",
            "description": (
                "US patent publication search."
            ),
        },
    ]

    query_cards = []

    descriptions = {
        "core": (
            "Core technology searches. Start here "
            "to find direct technical prior art."
        ),
        "application": (
            "Searches the technology in concrete "
            "systems, processes and deployments."
        ),
        "performance": (
            "Searches the technical performance "
            "claims and mechanisms behind them."
        ),
        "competitor": (
            "Searches alternatives, incumbent "
            "approaches and competing solutions."
        ),
    }

    for group, queries in (
        query_groups.items()
    ):

        for query in queries:

            query_cards.append(
                {
                    "group": group,
                    "group_description": descriptions.get(
                        group,
                        "",
                    ),
                    "query": query,
                    "sources": {
                        "google_patents":
                            google_patents_url(
                                query
                            ),
                        "wipo":
                            wipo_url(
                                query
                            ),
                        "espacenet":
                            espacenet_url(
                                query
                            ),
                        "uspto":
                            uspto_url(
                                query
                            ),
                    },
                }
            )

    return {
        "sources": sources,
        "queries": query_groups,
        "query_cards": query_cards,
        "total_queries": len(
            query_cards
        ),
        "methodology": (
            "Patent searches are generated from "
            "technical concepts, claims, performance "
            "terms and competing approaches extracted "
            "from the proposal. The MVP provides "
            "targeted search queries rather than "
            "automated scraping of patent websites."
        ),
    }
