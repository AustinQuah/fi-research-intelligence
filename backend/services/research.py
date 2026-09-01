import asyncio
from urllib.parse import quote

import httpx


CACHE = {}


async def get_json(
    url: str,
    retries: int = 4,
) -> dict:

    if url in CACHE:
        return CACHE[url]

    headers = {
        "Accept": "application/json",
        "User-Agent": (
            "FI-Research-Intelligence/0.1"
        ),
    }

    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=True,
        headers=headers,
    ) as client:

        for attempt in range(retries):

            response = await client.get(
                url
            )

            if response.status_code == 200:

                data = response.json()

                CACHE[url] = data

                return data

            if response.status_code == 429:

                retry_after = (
                    response.headers.get(
                        "Retry-After"
                    )
                )

                try:

                    delay = (
                        float(retry_after)
                        if retry_after
                        else
                        1.5 * (
                            2 ** attempt
                        )
                    )

                except ValueError:

                    delay = (
                        1.5 * (
                            2 ** attempt
                        )
                    )

                await asyncio.sleep(
                    delay
                )

                continue

            response.raise_for_status()

    raise RuntimeError(
        "Research provider unavailable after retries."
    )


async def research_pass(
    query: str,
    year: int = 2020,
    limit: int = 10,
) -> list:

    query = query.strip()

    if not query:
        raise ValueError(
            "Research query cannot be empty."
        )

    # --------------------------------------------------------
    # OpenAlex
    # --------------------------------------------------------

    openalex_url = (

        "https://api.openalex.org/works"

        f"?search={quote(query)}"

        f"&filter="
        f"from_publication_date:{year}-01-01,"
        f"type:article|review"

        f"&per-page={limit}"

    )

    openalex = await get_json(
        openalex_url
    )

    results = []

    for item in openalex.get(
        "results",
        []
    ):

        location = (
            item.get(
                "primary_location"
            )
            or {}
        )

        results.append({

            "source":
                "OpenAlex",

            "title":
                item.get(
                    "title"
                )
                or
                "Untitled",

            "year":
                item.get(
                    "publication_year"
                ),

            "citations":
                item.get(
                    "cited_by_count",
                    0,
                ),

            "doi":
                item.get(
                    "doi"
                ),

            "url":
                location.get(
                    "landing_page_url"
                )
                or
                item.get("doi")
                or
                item.get("id"),

        })

    # Don't immediately hammer another provider.

    await asyncio.sleep(
        0.75
    )

    # --------------------------------------------------------
    # Crossref
    # --------------------------------------------------------

    crossref_url = (

        "https://api.crossref.org/works"

        f"?query.bibliographic="
        f"{quote(query)}"

        f"&filter="
        f"from-pub-date:{year}-01-01"

        f"&rows={limit}"

    )

    crossref = await get_json(
        crossref_url
    )

    for item in (

        crossref
        .get(
            "message",
            {}
        )
        .get(
            "items",
            []
        )

    ):

        doi = item.get(
            "DOI"
        )

        dates = (

            item
            .get(
                "published",
                {}
            )
            .get(
                "date-parts",
                [[None]]
            )

        )

        results.append({

            "source":
                "Crossref",

            "title":
                (
                    item.get(
                        "title"
                    )
                    or
                    ["Untitled"]
                )[0],

            "year":
                (
                    dates[0][0]
                    if dates
                    else None
                ),

            "citations":
                item.get(
                    "is-referenced-by-count",
                    0,
                ),

            "doi":
                doi,

            "url":
                item.get(
                    "URL"
                )
                or
                (
                    f"https://doi.org/{doi}"
                    if doi
                    else None
                ),

        })

    # --------------------------------------------------------
    # Dedup
    # --------------------------------------------------------

    unique = []
    seen = set()

    for item in results:

        key = (

            item.get(
                "doi"
            )

            or

            item.get(
                "url"
            )

            or

            item.get(
                "title"
            )

            or
            ""

        ).lower()

        if (
            not key
            or
            key in seen
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

    return unique
