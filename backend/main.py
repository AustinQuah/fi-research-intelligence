import asyncio
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from services.assessment import (
    build_assessment,
)

from services.documents import (
    build_document_dossier,
    parse_document,
)

from services.research import (
    calculate_novelty,
    run_research,
)


app = FastAPI(
    title="FI Research Intelligence API",
    version="5.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


DOCUMENTS: dict[str, dict[str, Any]] = {}


@app.get("/")
async def root():
    return {
        "service": "FI Research Intelligence API",
        "status": "online",
        "version": "5.0.0",
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "5.0.0",
    }


@app.post("/api/proposals/upload")
async def upload_proposal(
    file: UploadFile = File(...),
):
    filename = file.filename or "proposal"
    suffix = Path(filename).suffix.lower()

    if suffix not in {
        ".pdf",
        ".docx",
        ".txt",
        ".md",
    }:
        raise HTTPException(
            status_code=400,
            detail=(
                "Supported formats are PDF, DOCX, TXT and MD."
            ),
        )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )

    document_id = str(
        uuid.uuid4()
    )

    DOCUMENTS[document_id] = {
        "id": document_id,
        "status": "processing",
        "filename": filename,
        "dossier": None,
        "research": {
            "status": "not_started",
            "queries": [],
            "evidence": [],
        },
        "novelty": None,
        "assessment": None,
        "error": None,
    }

    await process_document(
        document_id,
        filename,
        suffix,
        content,
    )

    item = DOCUMENTS[
        document_id
    ]

    return {
        "id": document_id,
        "status": item["status"],
        "document": item["dossier"],
    }


async def process_document(
    document_id: str,
    filename: str,
    suffix: str,
    content: bytes,
):
    path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp:
            temp.write(content)
            path = temp.name

        parsed = await asyncio.to_thread(
            parse_document,
            path,
            filename,
        )

        dossier = await asyncio.to_thread(
            build_document_dossier,
            parsed,
        )

        item = DOCUMENTS[
            document_id
        ]

        item["dossier"] = dossier

        if dossier.get(
            "status"
        ) == "needs_visual_processing":

            item["status"] = (
                "needs_visual_processing"
            )

            return

        item["status"] = "ready"

        item["research"][
            "status"
        ] = "running"

        asyncio.create_task(
            run_research_pipeline(
                document_id
            )
        )

    except Exception as error:

        item = DOCUMENTS[
            document_id
        ]

        item["status"] = "error"

        item["error"] = str(
            error
        )

    finally:
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass


async def run_research_pipeline(
    document_id: str,
):
    item = DOCUMENTS.get(
        document_id
    )

    if not item:
        return

    dossier = item.get(
        "dossier"
    )

    if not dossier:
        return

    try:

        research = await run_research(
            dossier
        )

        item["research"] = research

        novelty = calculate_novelty(
            dossier,
            research,
        )

        item["novelty"] = novelty

        item["assessment"] = (
            build_assessment(
                dossier,
                research,
                novelty,
            )
        )

    except Exception as error:

        item["research"] = {
            "status": "error",
            "queries": [],
            "evidence": [],
            "error": str(error),
        }

        # We deliberately do not fabricate
        # assessment numbers when research failed.

        item["novelty"] = None

        item["assessment"] = None


@app.get(
    "/api/proposals/{document_id}"
)
async def get_proposal(
    document_id: str,
):
    item = DOCUMENTS.get(
        document_id
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    return item


@app.get(
    "/api/proposals/{document_id}/research"
)
async def get_research(
    document_id: str,
):
    item = DOCUMENTS.get(
        document_id
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    return item["research"]


@app.get(
    "/api/proposals/{document_id}/novelty"
)
async def get_novelty(
    document_id: str,
):
    item = DOCUMENTS.get(
        document_id
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    return {
        "status": (
            "complete"
            if item["novelty"]
            else item["research"].get(
                "status",
                "not_ready",
            )
        ),
        "novelty": item["novelty"],
    }


@app.get(
    "/api/proposals/{document_id}/assessment"
)
async def get_assessment(
    document_id: str,
):
    item = DOCUMENTS.get(
        document_id
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    return {
        "status": (
            "complete"
            if item["assessment"]
            else item["research"].get(
                "status",
                "not_ready",
            )
        ),
        "assessment": item[
            "assessment"
        ],
    }


# ------------------------------------------------------------
# Backward-compatible endpoint
# ------------------------------------------------------------

@app.post(
    "/api/proposals/analyze"
)
async def analyze_compatibility(
    file: UploadFile = File(...),
):
    return await upload_proposal(
        file
    )
