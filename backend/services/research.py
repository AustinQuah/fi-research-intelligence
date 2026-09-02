import asyncio
from urllib.parse import quote

import httpx


CACHE = {}


async def get_json(
    url: str,
) -> dict:

    if url in CACHE:
        return CACHE[url]

    async with httpx.AsyncClient(
        timeout=25,
        follow_redirects=True,
        headers={
            "Accept": "application/json",
            "User-Agent": (
                "FI-Research-Intelligence/2.0"
            ),
        },
    ) as client:

        for attempt in range(4):

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
                        2 ** attempt
                    )
                )

                continue

            response.raise_for_status()

    raise RuntimeError(
        "Research provider unavailable."
    )


def build_queries(
    dossier: dict,
) -> list:

    concepts = dossier.get(
        "concepts",
        [],
    )

    queries = []

    # Individual concepts

    for concept in concepts[:8]:

        queries.append(
            concept
        )

    # Concept combinations are usually
    # more useful than one giant title search.

    if len(concepts) >= 2:

        queries.append(
            " ".join(
                concepts[:2]
            )
        )

    if len(concepts) >= 3:

        queries.append(
            " ".join(
                concepts[:3]
            )
        )

    # Claims can generate targeted
    # literature questions.

    for claim in dossier.get(
        "claims",
        [],
    )[:3]:

        text = claim.get(
            "text",
            "",
        )

        words = text.split()

        if len(words) > 5:

            queries.append(
                " ".join(
                    words[:14]
                )
            )

    clean = []

    for query in queries:

        query = (
            query
            .strip()
            .lower()
        )

        if (
            query
            and query not in clean
        ):

            clean.append(
                query
            )

    return clean[:8]


async def search_openalex(
    query: str,
    limit: int = 5,
) -> list:

    url = (
        "https://api.openalex.org/works"
        f"?search={quote(query)}"
        "&filter=from_publication_date:2018-01-01,"
        "type:article|review"
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
                    or item.get(
                        "doi"
                    )
                    or item.get(
                        "id"
                    )
                ),
                "query": query,
            }
        )

    return results


async def search_crossref(
    query: str,
    limit: int = 5,
) -> list:

    url = (
        "https://api.crossref.org/works"
        f"?query.bibliographic={quote(query)}"
        "&filter=from-pub-date:2018-01-01"
        f"&rows={limit}"
    )

    data = await get_json(
        url
    )

    results = []

    for item in (
        data
        .get(
            "message",
            {},
        )
        .get(
            "items",
            [],
        )
    ):

        title_list = (
            item.get(
                "title"
            )
            or
            ["Untitled"]
        )

        doi = item.get(
            "DOI"
        )

        date_parts = (
            item
            .get(
                "published",
                {},
            )
            .get(
                "date-parts",
                [[None]],
            )
        )

        results.append(
            {
                "source": "Crossref",
                "title": title_list[0],
                "year": (
                    date_parts[0][0]
                    if date_parts
                    else None
                ),
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
                "query": query,
            }
        )

    return results


def direct_links(
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
            f"search?q={encoded}"
        ),
        "wipo": (
            "https://patentscope.wipo.int/"
            "search/en/result.jsf"
            f"?query={encoded}"
        ),
    }


async def research_dossier(
    dossier: dict,
) -> dict:

    queries = build_queries(
        dossier
    )

    evidence = []

    # Keep this deliberately limited.
    # Eight queries x multiple providers can
    # otherwise become painfully slow on free Render.

    for query in queries[:5]:

        try:

            openalex = await search_openalex(
                query,
                4,
            )

        except Exception:

            openalex = []

        try:

            crossref = await search_crossref(
                query,
                4,
            )

        except Exception:

            crossref = []

        evidence.append(
            {
                "query": query,
                "links": direct_links(
                    query
                ),
                "papers": (
                    openalex
                    +
                    crossref
                ),
            }
        )

        await asyncio.sleep(
            0.3
        )

    return {
        "queries": queries,
        "evidence": evidence,
    }
