from __future__ import annotations

from typing import Any


def clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 100.0,
) -> float:
    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def weighted_average(
    components: list[dict[str, Any]],
) -> float | None:
    measured = [
        item
        for item in components
        if item.get("measured")
        and item.get("score") is not None
    ]

    if not measured:
        return None

    total_weight = sum(
        float(item["weight"])
        for item in measured
    )

    if total_weight <= 0:
        return None

    total = sum(
        float(item["score"])
        * float(item["weight"])
        for item in measured
    )

    return round(
        total / total_weight,
        1,
    )


def score_from_presence(
    present: bool,
    strong: bool = False,
) -> dict[str, Any]:
    if not present:
        return {
            "score": None,
            "measured": False,
        }

    return {
        "score": 85.0 if strong else 65.0,
        "measured": True,
    }


def extract_trl(
    dossier: dict[str, Any],
) -> int | None:
    for claim in dossier.get(
        "claims",
        [],
    ):
        text = claim.get(
            "text",
            "",
        )

        import re

        matches = re.findall(
            r"\bTRL\s*([1-9])\b",
            text,
            re.IGNORECASE,
        )

        if matches:
            return int(
                matches[0]
            )

    for page in dossier.get(
        "page_analysis",
        [],
    ):
        for kpi in page.get(
            "kpis",
            [],
        ):
            matches = re.findall(
                r"\bTRL\s*([1-9])\b",
                kpi,
                re.IGNORECASE,
            )

            if matches:
                return int(
                    matches[0]
                )

    return None


def calculate_translation(
    dossier: dict[str, Any],
) -> dict[str, Any]:
    trl = extract_trl(
        dossier
    )

    page_analysis = dossier.get(
        "page_analysis",
        [],
    )

    all_text = " ".join(
        page.get(
            "text_preview",
            "",
        )
        for page in page_analysis
    ).lower()

    claims = dossier.get(
        "claims",
        [],
    )

    kpis = dossier.get(
        "kpis",
        [],
    )

    # --------------------------------------------------------
    # 1. Technical maturity
    #
    # Explicit TRL is measured.
    # No explicit TRL = not measured.
    # --------------------------------------------------------

    technical_maturity = None

    if trl is not None:
        technical_maturity = round(
            (
                (trl - 1)
                / 8
            )
            * 100,
            1,
        )

    # --------------------------------------------------------
    # 2. Scale-up feasibility
    #
    # We only score this when the proposal contains
    # scale-up / pilot / demonstration evidence.
    # --------------------------------------------------------

    scale_terms = [
        "pilot",
        "demonstration",
        "demonstration-scale",
        "scale-up",
        "scale up",
        "commercial scale",
        "m³/day",
        "m3/day",
        "continuous operation",
    ]

    scale_matches = sum(
        1
        for term in scale_terms
        if term in all_text
    )

    scale_up_score = None

    if scale_matches >= 3:
        scale_up_score = 80.0
    elif scale_matches == 2:
        scale_up_score = 65.0
    elif scale_matches == 1:
        scale_up_score = 50.0

    # --------------------------------------------------------
    # 3. Integration feasibility
    # --------------------------------------------------------

    integration_terms = [
        "existing plant",
        "existing facility",
        "existing infrastructure",
        "integration",
        "retrofit",
        "operational environment",
        "treatment train",
        "process integration",
        "deployment",
    ]

    integration_matches = sum(
        1
        for term in integration_terms
        if term in all_text
    )

    integration_score = None

    if integration_matches >= 4:
        integration_score = 82.0
    elif integration_matches >= 2:
        integration_score = 68.0
    elif integration_matches == 1:
        integration_score = 50.0

    # --------------------------------------------------------
    # 4. Validation quality
    # --------------------------------------------------------

    validation_terms = [
        "validated",
        "validation",
        "pilot test",
        "pilot testing",
        "field test",
        "field testing",
        "real-world",
        "real world",
        "demonstrated",
        "demonstration",
        "experimental results",
        "measured results",
    ]

    validation_matches = sum(
        1
        for term in validation_terms
        if term in all_text
    )

    validation_score = None

    if validation_matches >= 4:
        validation_score = 82.0
    elif validation_matches >= 2:
        validation_score = 67.0
    elif validation_matches == 1:
        validation_score = 50.0

    # --------------------------------------------------------
    # 5. Implementation pathway
    # --------------------------------------------------------

    implementation_terms = [
        "industry partner",
        "industry partners",
        "deployment partner",
        "end user",
        "end-user",
        "customer",
        "operator",
        "commercialisation",
        "commercialization",
        "licensing",
        "market",
        "adopter",
    ]

    implementation_matches = sum(
        1
        for term in implementation_terms
        if term in all_text
    )

    implementation_score = None

    if implementation_matches >= 5:
        implementation_score = 80.0
    elif implementation_matches >= 3:
        implementation_score = 66.0
    elif implementation_matches >= 1:
        implementation_score = 48.0

    # --------------------------------------------------------
    # 6. Execution capability
    #
    # We only infer a modest signal from explicit project
    # planning evidence.
    # --------------------------------------------------------

    execution_terms = [
        "milestone",
        "milestones",
        "work package",
        "work packages",
        "project management",
        "project manager",
        "research team",
        "principal investigator",
        "PI",
        "partner",
        "partners",
    ]

    execution_matches = sum(
        1
        for term in execution_terms
        if term.lower() in all_text
    )

    execution_score = None

    if execution_matches >= 5:
        execution_score = 78.0
    elif execution_matches >= 3:
        execution_score = 65.0
    elif execution_matches >= 1:
        execution_score = 48.0

    components = [
        {
            "key": "technical_maturity",
            "label": "Technical maturity",
            "weight": 20,
            "score": technical_maturity,
            "measured": technical_maturity is not None,
            "basis": (
                "Explicit TRL extracted from the proposal."
            ),
        },
        {
            "key": "scale_up",
            "label": "Scale-up feasibility",
            "weight": 20,
            "score": scale_up_score,
            "measured": scale_up_score is not None,
            "basis": (
                f"{scale_matches} scale-up/pilot indicators "
                "found in extracted proposal text."
            ),
        },
        {
            "key": "integration",
            "label": "Integration feasibility",
            "weight": 15,
            "score": integration_score,
            "measured": integration_score is not None,
            "basis": (
                f"{integration_matches} integration indicators "
                "found in extracted proposal text."
            ),
        },
        {
            "key": "validation",
            "label": "Validation quality",
            "weight": 15,
            "score": validation_score,
            "measured": validation_score is not None,
            "basis": (
                f"{validation_matches} validation indicators "
                "found in extracted proposal text."
            ),
        },
        {
            "key": "implementation",
            "label": "Implementation pathway",
            "weight": 15,
            "score": implementation_score,
            "measured": implementation_score is not None,
            "basis": (
                f"{implementation_matches} implementation/adoption "
                "indicators found."
            ),
        },
        {
            "key": "execution",
            "label": "Execution capability",
            "weight": 15,
            "score": execution_score,
            "measured": execution_score is not None,
            "basis": (
                f"{execution_matches} execution/planning indicators "
                "found."
            ),
        },
    ]

    score = weighted_average(
        components
    )

    measured_count = sum(
        1
        for item in components
        if item["measured"]
    )

    confidence = round(
        (
            measured_count
            / len(components)
        )
        * 100,
        1,
    )

    return {
        "score": score,
        "confidence": confidence,
        "components": components,
        "inputs": {
            "trl": trl,
            "claim_count": len(claims),
            "kpi_count": len(kpis),
            "page_count": len(page_analysis),
        },
        "methodology": (
            "Translation is assessed from explicit technical "
            "maturity and observable translation signals in "
            "the proposal. Missing evidence is not converted "
            "into a negative score; it is marked unmeasured."
        ),
    }


def calculate_market_viability(
    dossier: dict[str, Any],
    research: dict[str, Any],
) -> dict[str, Any]:
    page_analysis = dossier.get(
        "page_analysis",
        []
    )

    all_text = " ".join(
        page.get(
            "text_preview",
            "",
        )
        for page in page_analysis
    ).lower()

    evidence = research.get(
        "evidence",
        []
    )

    papers = []

    for group in evidence:
        papers.extend(
            group.get(
                "papers",
                []
            )
        )

    # --------------------------------------------------------
    # Problem / customer need
    # --------------------------------------------------------

    problem_terms = [
        "problem",
        "challenge",
        "need",
        "demand",
        "shortage",
        "cost",
        "inefficiency",
        "constraint",
        "pain point",
        "operational challenge",
    ]

    problem_matches = sum(
        1
        for term in problem_terms
        if term in all_text
    )

    problem_score = None

    if problem_matches >= 6:
        problem_score = 82.0
    elif problem_matches >= 3:
        problem_score = 68.0
    elif problem_matches >= 1:
        problem_score = 50.0

    # --------------------------------------------------------
    # Economic proposition
    # --------------------------------------------------------

    economic_terms = [
        "cost reduction",
        "operating cost",
        "operating costs",
        "opex",
        "capex",
        "capital cost",
        "energy savings",
        "energy consumption",
        "payback",
        "roi",
        "return on investment",
        "revenue",
        "savings",
        "economic benefit",
        "unit cost",
        "$/m3",
        "$/m³",
    ]

    economic_matches = sum(
        1
        for term in economic_terms
        if term in all_text
    )

    economic_score = None

    if economic_matches >= 5:
        economic_score = 82.0
    elif economic_matches >= 3:
        economic_score = 67.0
    elif economic_matches >= 1:
        economic_score = 48.0

    # --------------------------------------------------------
    # Market/adopter evidence
    # --------------------------------------------------------

    adopter_terms = [
        "customer",
        "customers",
        "end user",
        "end-user",
        "operator",
        "industry partner",
        "commercial partner",
        "adopter",
        "deployment partner",
        "pilot partner",
        "letter of intent",
        "LOI",
        "off-take",
        "offtake",
    ]

    adopter_matches = sum(
        1
        for term in adopter_terms
        if term.lower() in all_text
    )

    adopter_score = None

    if adopter_matches >= 5:
        adopter_score = 80.0
    elif adopter_matches >= 3:
        adopter_score = 65.0
    elif adopter_matches >= 1:
        adopter_score = 45.0

    # --------------------------------------------------------
    # Competitive advantage
    #
    # Uses research result volume as evidence coverage,
    # but does NOT pretend that retrieval volume alone proves
    # competitive superiority.
    # --------------------------------------------------------

    competitive_score = None

    if len(papers) >= 20:
        competitive_score = 70.0
    elif len(papers) >= 10:
        competitive_score = 60.0
    elif len(papers) >= 5:
        competitive_score = 50.0

    # --------------------------------------------------------
    # Regulatory / adoption barrier
    #
    # Only measured when proposal text explicitly discusses
    # regulations, standards, permitting, safety, etc.
    # --------------------------------------------------------

    regulatory_terms = [
        "regulation",
        "regulatory",
        "regulations",
        "permit",
        "permitting",
        "standard",
        "standards",
        "safety",
        "approval",
        "compliance",
        "certification",
    ]

    regulatory_matches = sum(
        1
        for term in regulatory_terms
        if term in all_text
    )

    regulatory_score = None

    if regulatory_matches >= 4:
        regulatory_score = 75.0
    elif regulatory_matches >= 2:
        regulatory_score = 60.0
    elif regulatory_matches == 1:
        regulatory_score = 45.0

    components = [
        {
            "key": "problem_need",
            "label": "Problem / customer need",
            "weight": 15,
            "score": problem_score,
            "measured": problem_score is not None,
            "basis": (
                f"{problem_matches} problem/need indicators "
                "found."
            ),
        },
        {
            "key": "economic_value",
            "label": "Economic value proposition",
            "weight": 20,
            "score": economic_score,
            "measured": economic_score is not None,
            "basis": (
                f"{economic_matches} economic-value indicators "
                "found."
            ),
        },
        {
            "key": "competitive_advantage",
            "label": "Competitive advantage evidence",
            "weight": 20,
            "score": competitive_score,
            "measured": competitive_score is not None,
            "basis": (
                f"{len(papers)} research records retrieved. "
                "This measures evidence coverage, not "
                "proof of superiority."
            ),
        },
        {
            "key": "market_adoption",
            "label": "Market / adopter evidence",
            "weight": 15,
            "score": adopter_score,
            "measured": adopter_score is not None,
            "basis": (
                f"{adopter_matches} adopter/customer indicators "
                "found in proposal text."
            ),
        },
        {
            "key": "commercial_pathway",
            "label": "Commercialisation pathway",
            "weight": 10,
            "score": adopter_score,
            "measured": adopter_score is not None,
            "basis": (
                "Uses explicit customer/adopter/commercial "
                "signals as a provisional pathway indicator."
            ),
        },
        {
            "key": "regulatory",
            "label": "Regulatory / adoption readiness",
            "weight": 10,
            "score": regulatory_score,
            "measured": regulatory_score is not None,
            "basis": (
                f"{regulatory_matches} regulatory/safety "
                "indicators found."
            ),
        },
        {
            "key": "resources",
            "label": "Supply / resource feasibility",
            "weight": 10,
            "score": None,
            "measured": False,
            "basis": (
                "Not measured in the current MVP."
            ),
        },
    ]

    score = weighted_average(
        components
    )

    measured_count = sum(
        1
        for item in components
        if item["measured"]
    )

    confidence = round(
        (
            measured_count
            / len(components)
        )
        * 100,
        1,
    )

    return {
        "score": score,
        "confidence": confidence,
        "components": components,
        "inputs": {
            "research_records": len(papers),
            "query_count": len(evidence),
        },
        "methodology": (
            "Market viability is a provisional decision-support "
            "score. It uses only evidence actually present in the "
            "proposal or retrieved research set. Missing commercial "
            "evidence remains unmeasured."
        ),
    }


def classification(
    score: float | None,
) -> str:
    if score is None:
        return "Insufficient evidence"

    if score >= 80:
        return "Very High"

    if score >= 65:
        return "High"

    if score >= 45:
        return "Moderate"

    return "Low"


def build_assessment(
    dossier: dict[str, Any],
    research: dict[str, Any],
    novelty: dict[str, Any] | None = None,
) -> dict[str, Any]:
    translation = calculate_translation(
        dossier
    )

    market = calculate_market_viability(
        dossier,
        research,
    )

    return {
        "novelty": novelty,
        "translation": {
            **translation,
            "classification": classification(
                translation["score"]
            ),
        },
        "market": {
            **market,
            "classification": classification(
                market["score"]
            ),
        },
    }
