import os
import tempfile
from pathlib import Path

from fastapi import (
    FastAPI,
    File,
    UploadFile,
    HTTPException,
)

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from services.documents import (
    parse_document,
    build_document_dossier,
)

from services.research import (
    research_dossier,
)


app = FastAPI(
    title="FI Research Intelligence API",
    version="2.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():

    return {
        "status": "ok",
        "version": "2.0.0",
    }


@app.post("/api/proposals/analyze")
async def analyze_proposal(
    file: UploadFile = File(...),
):

    filename = (
        file.filename
        or
        "proposal"
    )

    suffix = (
        Path(filename)
        .suffix
        .lower()
    )

    if suffix not in {
        ".pdf",
        ".docx",
        ".txt",
        ".md",
    }:

        raise HTTPException(
            status_code=400,
            detail=(
                "Supported formats: "
                "PDF, DOCX, TXT, MD"
            ),
        )

    content = await file.read()

    if not content:

        raise HTTPException(
            status_code=400,
            detail=(
                "Uploaded file is empty."
            ),
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

        dossier = (
            build_document_dossier(
                parsed
            )
        )

        research = (
            await research_dossier(
                dossier
            )
        )

        return {
            **dossier,
            "research": research,
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )

    finally:

        if path:

            try:
                os.unlink(
                    path
                )

            except OSError:
                pass
