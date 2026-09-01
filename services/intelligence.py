import json
import os


SYSTEM_PROMPT = """
You are an expert R&D funding proposal analyst.

Read the proposal as a complete document.

Your job is to distinguish:

1. What the applicant actually proposes.
2. What the applicant claims is novel.
3. What technology already exists.
4. What is merely asserted without enough evidence.
5. What questions a reviewer should research.
6. What previous projects may be relevant.

Do not invent facts.

Use null when something is not supported.

Return valid JSON only.

Schema:

{
  "confidence": 0,
  "problem": null,
  "technology": null,
  "baseline": null,
  "proposed_solution": null,
  "trl": null,
  "commercialisation": null,
  "novelty_claims": [],
  "prior_projects": [],
  "research_questions": [],
  "review_flags": [
    {
      "title": null,
      "detail": null,
      "severity": "High|Medium|Low"
    }
  ]
}
"""


async def run_ai_understanding(
    proposal: dict,
) -> dict:

    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    if not api_key:

        raise RuntimeError(
            "OPENAI_API_KEY is not configured."
        )

    from openai import OpenAI

    client = OpenAI(
        api_key=api_key
    )

    payload = {

        "document":
            proposal.get(
                "document",
                {}
            ),

        "understanding":
            proposal.get(
                "understanding",
                {}
            ),

        "claims":
            proposal.get(
                "claims",
                []
            ),

        "summary":
            proposal.get(
                "summary"
            ),

        "source_text":
            proposal.get(
                "raw_text",
                ""
            )[:200000],

    }

    response = client.responses.create(

        model=os.getenv(
            "OPENAI_MODEL",
            "gpt-5",
        ),

        input=[

            {
                "role":
                    "system",

                "content": [

                    {
                        "type":
                            "input_text",

                        "text":
                            SYSTEM_PROMPT,

                    }

                ],

            },

            {

                "role":
                    "user",

                "content": [

                    {

                        "type":
                            "input_text",

                        "text":
                            json.dumps(
                                payload,
                                ensure_ascii=False,
                            ),

                    }

                ],

            },

        ],

        text={

            "format": {

                "type":
                    "json_object",

            }

        },

    )

    return json.loads(
        response.output_text
    )
