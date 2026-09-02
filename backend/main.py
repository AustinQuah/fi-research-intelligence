import asyncio
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import (
    FastAPI,
    File,
    HTTPException,
    UploadFile,
)

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from services.documents import (
    build_document_dossier,
    parse_document,
)

from services.research import (
    run_research,
)


app = FastAPI(
    title="FI Research Intelligence API",
    version="3.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------
# Temporary in-memory store.
#
# Fine for MVP.
# Render restart = data disappears.
# We'll add persistence later.
# ------------------------------------------------------------

DOCUMENTS: dict[str, dict[str, Any]] = {}


@app.get("/")
async def root():
    return {
        "service": "FI Research Intelligence API",
        "status": "online",
        "version": "3.0.0",
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "3.0.0",
    }


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
        "status": "processing",
        "filename": filename,
        "dossier": None,
        "research": {
            "status": "not_started",
            "queries": [],
            "evidence": [],
        },
        "error": None,
    }

    await process_document(
        document_id=document_id,
        filename=filename,
        suffix=suffix,
        content=content,
    )

    return {
        "id": document_id,
        "status": DOCUMENTS[
            document_id
        ]["status"],
        "document": DOCUMENTS[
            document_id
        ]["dossier"],
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

        DOCUMENTS[
            document_id
        ]["dossier"] = dossier

        DOCUMENTS[
            document_id
        ]["status"] = "ready"

    except Exception as error:
        DOCUMENTS[
            document_id
        ]["status"] = "error"

        DOCUMENTS[
            document_id
        ]["error"] = str(error)

        raise HTTPException(
            status_code=500,
            detail=(
                "Document processing failed: "
                f"{error}"
            ),
        )

    finally:
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass


@app.get("/api/proposals/{document_id}")
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


@app.post(
    "/api/proposals/{document_id}/research"
)
async def start_research(
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

    if not item.get("dossier"):
        raise HTTPException(
            status_code=409,
            detail=(
                "Document analysis is "
                "not ready."
            ),
        )

    if (
        item["research"]["status"]
        == "running"
    ):
        return {
            "status": "running",
        }

    item["research"] = {
        "status": "running",
        "queries": [],
        "evidence": [],
    }

    asyncio.create_task(
        research_background(
            document_id
        )
    )

    return {
        "status": "running",
    }


async def research_background(
    document_id: str,
):
    item = DOCUMENTS.get(
        document_id
    )

    if not item:
        return

    try:
        result = await run_research(
            item["dossier"]
        )

        item["research"] = result

    except Exception as error:
        item["research"] = {
            "status": "error",
            "queries": [],
            "evidence": [],
            "error": str(error),
        }


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
# Compatibility endpoint.
#
# Keep this temporarily so old frontend requests
# don't instantly explode during deployment.
# ------------------------------------------------------------

@app.post("/api/proposals/analyze")
async def analyze_compatibility(
    file: UploadFile = File(...),
):
    return await upload_proposal(file)
