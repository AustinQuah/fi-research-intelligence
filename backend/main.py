import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import (
    FastAPI,
    File,
    UploadFile,
    HTTPException,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from services.documents import (
    parse_document,
    quick_understanding,
)
from services.research import (
    research_pass,
)
from services.awards import (
    compare_awards,
)


app = FastAPI(
    title="FI Research Intelligence",
    version="1.0.0",
)


# ------------------------------------------------------------
# CORS
# ------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------
# HEALTH CHECK
# ------------------------------------------------------------

@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok"
    }


# ------------------------------------------------------------
# PROPOSAL ANALYSIS
# ------------------------------------------------------------

@app.post("/api/proposals/analyze")
async def analyze_proposal(
    file: UploadFile = File(...),
) -> dict[str, Any]:

    filename = (
        file.filename
        or "proposal"
    )

    suffix = (
        Path(filename)
        .suffix
        .lower()
    )

    allowed = {
        ".pdf",
        ".docx",
        ".txt",
        ".md",
    }

    if suffix not in allowed:

        raise HTTPException(
            status_code=400,
            detail=(
                "Supported formats: "
                "PDF, DOCX, TXT and MD."
            ),
        )

    content = await file.read()

    if not content:

        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )

    path = None

    try:

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp:

            temp.write(
                content
            )

            path = temp.name

        parsed = parse_document(
            path,
            filename,
        )

        result = quick_understanding(
            parsed
        )

        return result

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Document processing failed: "
                f"{error}"
            ),
        )

    finally:

        if path:

            try:
                os.unlink(path)
            except OSError:
                pass


# ------------------------------------------------------------
# RESEARCH
# ------------------------------------------------------------

@app.post("/api/research/search")
async def search_research(
    query: str,
    year: int = 2020,
    limit: int = 10,
) -> dict:

    if not query.strip():

        raise HTTPException(
            status_code=400,
            detail=(
                "Research query cannot be empty."
            ),
        )

    try:

        results = await research_pass(
            query=query,
            year=year,
            limit=limit,
        )

        return {
            "query": query,
            "count": len(results),
            "results": results,
        }

    except Exception as error:

        raise HTTPException(
            status_code=502,
            detail=(
                f"Research provider failed: "
                f"{error}"
            ),
        )


# ------------------------------------------------------------
# AWARD COMPARISON
# ------------------------------------------------------------

@app.post("/api/awards/compare")
async def award_compare(
    payload: dict,
) -> dict:

    proposal = payload.get(
        "proposal",
        {},
    )

    awards = payload.get(
        "awards",
        [],
    )

    results = await compare_awards(
        proposal,
        awards,
    )

    return {
        "count": len(results),
        "results": results,
    }


# ------------------------------------------------------------
# FRONTEND
# ------------------------------------------------------------

frontend_dist = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    / "frontend"
    / "dist"
)


if frontend_dist.exists():

    app.mount(
        "/",
        StaticFiles(
            directory=frontend_dist,
            html=True,
        ),
        name="frontend",
    )
