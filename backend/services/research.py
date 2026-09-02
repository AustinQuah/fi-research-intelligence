import asyncio
from urllib.parse import quote

import httpx


CACHE: dict[str, dict] = {}


def build_queries(dossier: dict) -> list[str]:
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

    claims = dossier.get(
        "claims",
        [],
    )

    for claim in claims[:2]:
        text = claim.get(
            "text",
            "",
        )

        words = text.split()

        if len(words) >= 5:
            queries.append(
                " ".join(
                    words[:12]
                )
            )

    clean = []

    for query in queries:
        query = query.strip()

        if (
            query
            and query.lower()
            not in {
                value.lower()
                for value in clean
            }
        ):
            clean.append(query)

    return clean[:6]


async def get_json(url: str) -> dict:
    if url in CACHE:
        return CACHE[url]

    headers = {
        "Accept": "application/json",
        "User-Agent": (
            "FI-Research-Intelligence/3.0"
        ),
    }

    async with httpx.AsyncClient(
        timeout=15,
        follow_redirects=True,
        headers=headers,
    ) as client:

        for attempt in range(3):
            try:
                response = await client.get(url)

                if response.status_code == 200:
                    data = response.json()
                    CACHE[url] = data
                    return data

                if response.status_code == 429:
                    await asyncio.sleep(
                        1.5 * (attempt + 1)
                    )
                    continue

                response.raise_for_status()

            except httpx.HTTPError:
                if attempt == 2:
                    raise

                await asyncio.sleep(
                    0.75 * (attempt + 1)
                )

    raise RuntimeError(
        "Research provider unavailable."
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

    for item in data.get("results", []):
        location = (
            item.get("primary_location")
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

    items = (
        data.get("message", {})
        .get("items", [])
    )

    results = []

    for item in items:
        titles = (
            item.get("title")
            or ["Untitled"]
        )

        doi = item.get("DOI")

        date_parts = (
            item.get("published", {})
            .get(
                "date-parts",
                [[None]],
            )
        )

        year = None

        if date_parts and date_parts[0]:
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
                    item.get("URL")
                    or (
                        f"https://doi.org/{doi}"
                        if doi
                        else None
                    )
                ),
            }
        )

    return results


def make_links(query: str) -> dict:
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
            f"search?q={encoded}"
        ),
        "wipo": (
            "https://patentscope.wipo.int/"
            "search/en/result.jsf"
            f"?query={encoded}"
        ),
    }


async def research_query(
    query: str,
) -> dict:

    openalex_results = []
    crossref_results = []

    errors = []

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

        if not key or key in seen:
            continue

        seen.add(key)
        unique.append(item)

    unique.sort(
        key=lambda item: item.get(
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
        result = await research_query(
            query
        )

        evidence.append(result)

    return {
        "status": "complete",
        "queries": queries,
        "evidence": evidence,
    }
