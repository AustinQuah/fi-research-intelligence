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

from services.patents import (
    build_patent_workspace,
)

from services.research import (
    calculate_novelty,
    run_research,
)


app = FastAPI(
    title="FI Research Intelligence API",
    version="7.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


DOCUMENTS: dict[
    str,
    dict[str, Any]
] = {}


@app.get("/")
async def root():

    return {
        "service":
            "FI Research Intelligence API",
        "status":
            "online",
        "version":
            "7.0.0",
    }


@app.get("/api/health")
async def health():

    return {
        "status":
            "ok",
        "version":
            "7.0.0",
    }


@app.post(
    "/api/proposals/upload"
)
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

    DOCUMENTS[
        document_id
    ] = {

        "id":
            document_id,

        "filename":
            filename,

        "status":
            "processing",

        "dossier":
            None,

        "research": {
            "status":
                "not_started",

            "queries":
                [],

            "evidence":
                [],

            "error":
                None,
        },

        "novelty":
            None,

        "assessment":
            None,

        "patents":
            None,

        "error":
            None,
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


    if item["status"] == "error":

        raise HTTPException(
            status_code=500,
            detail=(
                item["error"]
                or
                "Document processing failed."
            ),
        )


    return {
        "id":
            document_id,

        "status":
            item["status"],

        "document":
            item["dossier"],
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

            temp.write(
                content
            )

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


        item[
            "dossier"
        ] = dossier


        if (
            dossier.get(
                "status"
            )
            ==
            "needs_visual_processing"
        ):

            item[
                "status"
            ] = (
                "needs_visual_processing"
            )

            return


        item[
            "status"
        ] = "ready"


        item[
            "patents"
        ] = build_patent_workspace(
            dossier
        )


        item[
            "research"
        ][
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
        ][
            "status"
        ] = "error"

        DOCUMENTS[
            document_id
        ][
            "error"
        ] = str(
            error
        )


    finally:

        if path:

            try:

                os.unlink(
                    path
                )

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

        research = (
            await run_research(
                dossier
            )
        )


        item[
            "research"
        ] = research


        novelty = (
            calculate_novelty(
                dossier,
                research,
            )
        )


        item[
            "novelty"
        ] = novelty


        item[
            "assessment"
        ] = build_assessment(

            dossier=dossier,

            research=research,

            novelty=novelty,

        )


    except Exception as error:

        item[
            "research"
        ] = {

            "status":
                "error",

            "queries":
                [],

            "evidence":
                [],

            "error":
                str(error),

        }

        item[
            "novelty"
        ] = None

        item[
            "assessment"
        ] = None


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
                "The Render service may "
                "have restarted and cleared "
                "the temporary MVP memory."
            ),
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

    return item[
        "research"
    ]


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
            if item[
                "novelty"
            ]

            else item[
                "research"
            ].get(
                "status",
                "not_ready",
            )
        ),

        "novelty":
            item["novelty"],

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
            if item[
                "assessment"
            ]

            else item[
                "research"
            ].get(
                "status",
                "not_ready",
            )
        ),

        "assessment":
            item["assessment"],

    }


@app.get(
    "/api/proposals/{document_id}/patents"
)
async def get_patents(
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


    patents = item.get(
        "patents"
    )


    if patents is None:

        if not item.get(
            "dossier"
        ):

            return {
                "status":
                    "not_ready",

                "patents":
                    None,
            }


        patents = (
            build_patent_workspace(
                item[
                    "dossier"
                ]
            )
        )

        item[
            "patents"
        ] = patents


    return {

        "status":
            "complete",

        "patents":
            patents,

    }


@app.post(
    "/api/proposals/analyze"
)
async def analyze_compatibility(
    file: UploadFile = File(...),
):

    return await upload_proposal(
        file
    )
