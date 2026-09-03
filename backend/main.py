import asyncio
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from services.assessment import build_assessment
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
    version="6.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------
# MVP storage
# ------------------------------------------------------------

DOCUMENTS: dict[str, dict[str, Any]] = {}


# ------------------------------------------------------------
# Basic endpoints
# ------------------------------------------------------------

@app.get("/")
async def root():
    return {
        "service": "FI Research Intelligence API",
        "status": "online",
        "version": "6.0.0",
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "6.0.0",
    }


# ------------------------------------------------------------
# Upload
# ------------------------------------------------------------

@app.post("/api/proposals/upload")
async def upload_proposal(
    file: UploadFile = File(...),
):
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
                "Supported formats are "
                "PDF, DOCX, TXT and MD."
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
        "filename": filename,
        "status": "processing",
        "dossier": None,
        "research": {
            "status": "not_started",
            "queries": [],
            "evidence": [],
            "error": None,
        },
        "novelty": None,
        "assessment": None,
        "error": None,
    }

    await process_document(
        document_id=document_id,
        filename=filename,
        suffix=suffix,
        content=content,
    )

    item = DOCUMENTS[
        document_id
    ]

    if item["status"] == "error":
        raise HTTPException(
            status_code=500,
            detail=item["error"]
            or "Document processing failed.",
        )

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

        DOCUMENTS[
            document_id
        ]["status"] = "error"

        DOCUMENTS[
            document_id
        ]["error"] = str(
            error
        )

    finally:

        if path:

            try:
                os.unlink(path)

            except OSError:
                pass


# ------------------------------------------------------------
# Background research
# ------------------------------------------------------------

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
                dossier=dossier,
                research=research,
                novelty=novelty,
            )
        )

    except Exception as error:

        # Research failure MUST NOT destroy
        # an otherwise valid document.

        item["research"] = {
            "status": "error",
            "queries": [],
            "evidence": [],
            "error": str(error),
        }

        item["novelty"] = None

        item["assessment"] = None


# ------------------------------------------------------------
# Proposal retrieval
# ------------------------------------------------------------

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
            detail=(
                "Document not found. "
                "The Render service may have restarted "
                "and cleared the temporary MVP memory."
            ),
        )

    return item


# ------------------------------------------------------------
# Research
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# Novelty
# ------------------------------------------------------------

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
        "novelty": item[
            "novelty"
        ],
    }


# ------------------------------------------------------------
# Full assessment
# ------------------------------------------------------------

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
# Backward compatibility
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
