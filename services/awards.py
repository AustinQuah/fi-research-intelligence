import re


TOPIC_TERMS = [

    "membrane",
    "sludge",
    "wastewater",
    "desalination",
    "pfas",
    "carbon",
    "resource recovery",
    "anaerobic",
    "electrolysis",
    "biogas",
    "water reclamation",
    "reuse",

]


async def compare_award_corpus(
    proposal: dict,
    awards: list,
) -> list:

    proposal_text = (

        str(
            proposal.get(
                "summary",
                ""
            )
        )

        + " "

        + str(
            proposal.get(
                "understanding",
                {}
            )
        )

        + " "

        + str(
            proposal.get(
                "claims",
                []
            )
        )

    ).lower()

    results = []

    for award in awards:

        award_text = str(
            award.get(
                "text",
                ""
            )
        ).lower()

        shared = [

            term

            for term in TOPIC_TERMS

            if term in proposal_text
            and term in award_text

        ]

        if len(shared) >= 4:

            relationship = (
                "Potential overlap"
            )

        elif len(shared) >= 2:

            relationship = (
                "Related / complementary"
            )

        elif len(shared) == 1:

            relationship = (
                "Weakly related"
            )

        else:

            relationship = (
                "No strong relationship found"
            )

        results.append({

            "filename":
                award.get(
                    "filename",
                    "Unknown",
                ),

            "relationship":
                relationship,

            "reason":
                (
                    "Shared signals: "
                    + (
                        ", ".join(shared)
                        if shared
                        else "none"
                    )
                ),

            "shared_terms":
                shared,

        })

    return results
