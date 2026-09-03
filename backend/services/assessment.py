from __future__ import annotations

from typing import Any
import re


def weighted_average(
    components: list[dict[str, Any]],
) -> float | None:

    measured = [
        item
        for item in components
        if (
            item.get("measured")
            and item.get("score") is not None
        )
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


def all_text(
    dossier: dict[str, Any],
) -> str:

    pages = dossier.get(
        "page_analysis",
        [],
    )

    return " ".join(
        page.get(
            "text_preview",
            "",
        )
        for page in pages
    ).lower()


def extract_trl(
    dossier: dict[str, Any],
) -> int | None:

    text = all_text(
        dossier
    )

    patterns = [
        r"\bTRL\s*([1-9])\b",
        r"\btechnology readiness level\s*([1-9])\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            return int(
                match.group(1)
            )

    return None


def count_terms(
    text: str,
    terms: list[str],
) -> int:

    return sum(
        1
        for term in terms
        if term.lower()
        in text
    )


def tier_score(
    matches: int,
    thresholds: tuple[int, int, int] = (
        1,
        3,
        5,
    ),
) -> float | None:

    low, medium, high = thresholds

    if matches >= high:
        return 82.0

    if matches >= medium:
        return 68.0

    if matches >= low:
        return 50.0

    return None


def calculate_translation(
    dossier: dict[str, Any],
) -> dict[str, Any]:

    text = all_text(
        dossier
    )

    claims = dossier.get(
        "claims",
        [],
    )

    kpis = dossier.get(
        "kpis",
        [],
    )

    page_count = len(
        dossier.get(
            "page_analysis",
            [],
        )
    )

    trl = extract_trl(
        dossier
    )

    technical_maturity = None

    if trl is not None:

        technical_maturity = round(
            (
                (
                    trl
                    - 1
                )
                / 8
            )
            * 100,
            1,
        )

    scale_terms = [
        "pilot",
        "demonstration",
        "demonstration-scale",
        "scale-up",
        "scale up",
        "commercial scale",
        "continuous operation",
        "m3/day",
        "m³/day",
    ]

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
        "adopter",
        "pilot partner",
    ]

    execution_terms = [
        "milestone",
        "milestones",
        "work package",
        "work packages",
        "project management",
        "project manager",
        "research team",
        "principal investigator",
        "partner",
        "partners",
    ]

    scale_matches = count_terms(
        text,
        scale_terms,
    )

    integration_matches = count_terms(
        text,
        integration_terms,
    )

    validation_matches = count_terms(
        text,
        validation_terms,
    )

    implementation_matches = count_terms(
        text,
        implementation_terms,
    )

    execution_matches = count_terms(
        text,
        execution_terms,
    )

    components = [
        {
            "key": "technical_maturity",
            "label": "Technical maturity",
            "weight": 20,
            "score": technical_maturity,
            "measured": (
                technical_maturity is not None
            ),
            "basis": (
                "Explicit TRL extracted from "
                "the proposal."
            ),
        },
        {
            "key": "scale_up",
            "label": "Scale-up feasibility",
            "weight": 20,
            "score": tier_score(
                scale_matches
            ),
            "measured": (
                tier_score(
                    scale_matches
                )
                is not None
            ),
            "basis": (
                f"{scale_matches} scale-up/pilot "
                "indicators found."
            ),
        },
        {
            "key": "integration",
            "label": "Integration feasibility",
            "weight": 15,
            "score": tier_score(
                integration_matches
            ),
            "measured": (
                tier_score(
                    integration_matches
                )
                is not None
            ),
            "basis": (
                f"{integration_matches} integration "
                "indicators found."
            ),
        },
        {
            "key": "validation",
            "label": "Validation quality",
            "weight": 15,
            "score": tier_score(
                validation_matches
            ),
            "measured": (
                tier_score(
                    validation_matches
                )
                is not None
            ),
            "basis": (
                f"{validation_matches} validation "
                "indicators found."
            ),
        },
        {
            "key": "implementation",
            "label": "Implementation pathway",
            "weight": 15,
            "score": tier_score(
                implementation_matches
            ),
            "measured": (
                tier_score(
                    implementation_matches
                )
                is not None
            ),
            "basis": (
                f"{implementation_matches} implementation "
                "or adoption indicators found."
            ),
        },
        {
            "key": "execution",
            "label": "Execution capability",
            "weight": 15,
            "score": tier_score(
                execution_matches
            ),
            "measured": (
                tier_score(
                    execution_matches
                )
                is not None
            ),
            "basis": (
                f"{execution_matches} execution/planning "
                "indicators found."
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
        "classification": classification(
            score
        ),
        "components": components,
        "inputs": {
            "trl": trl,
            "claim_count": len(
                claims
            ),
            "kpi_count": len(
                kpis
            ),
            "page_count": page_count,
        },
        "methodology": (
            "Translation assesses technical maturity, "
            "scale-up, integration, validation, implementation "
            "and execution evidence found in the proposal. "
            "Missing evidence remains unmeasured."
        ),
    }


def calculate_market_viability(
    dossier: dict[str, Any],
    research: dict[str, Any],
) -> dict[str, Any]:

    text = all_text(
        dossier
    )

    evidence = research.get(
        "evidence",
        [],
    )

    papers = []

    for group in evidence:

        papers.extend(
            group.get(
                "papers",
                [],
            )
        )

    problem_terms = [
        "problem",
        "challenge",
        "need",
        "demand",
        "shortage",
        "cost",
        "inefficiency",
        "constraint",
        "operational challenge",
    ]

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
        "loi",
        "off-take",
        "offtake",
    ]

    regulatory_terms = [
        "regulation",
        "regulatory",
        "permit",
        "permitting",
        "standard",
        "standards",
        "safety",
        "approval",
        "compliance",
        "certification",
    ]

    problem_matches = count_terms(
        text,
        problem_terms,
    )

    economic_matches = count_terms(
        text,
        economic_terms,
    )

    adopter_matches = count_terms(
        text,
        adopter_terms,
    )

    regulatory_matches = count_terms(
        text,
        regulatory_terms,
    )

    problem_score = tier_score(
        problem_matches,
        (
            1,
            3,
            6,
        ),
    )

    economic_score = tier_score(
        economic_matches,
        (
            1,
            3,
            5,
        ),
    )

    adopter_score = tier_score(
        adopter_matches,
        (
            1,
            3,
            5,
        ),
    )

    regulatory_score = tier_score(
        regulatory_matches,
        (
            1,
            2,
            4,
        ),
    )

    competitive_score = None

    if len(papers) >= 20:
        competitive_score = 70.0

    elif len(papers) >= 10:
        competitive_score = 60.0

    elif len(papers) >= 5:
        competitive_score = 50.0

    components = [
        {
            "key": "problem_need",
            "label": "Problem / customer need",
            "weight": 15,
            "score": problem_score,
            "measured": problem_score is not None,
            "basis": (
                f"{problem_matches} problem/need "
                "indicators found."
            ),
        },
        {
            "key": "economic_value",
            "label": "Economic value proposition",
            "weight": 20,
            "score": economic_score,
            "measured": economic_score is not None,
            "basis": (
                f"{economic_matches} economic-value "
                "indicators found."
            ),
        },
        {
            "key": "competitive_advantage",
            "label": "Competitive evidence",
            "weight": 20,
            "score": competitive_score,
            "measured": competitive_score is not None,
            "basis": (
                f"{len(papers)} research records retrieved. "
                "This is evidence coverage, not proof "
                "of competitive superiority."
            ),
        },
        {
            "key": "market_adoption",
            "label": "Market / adopter evidence",
            "weight": 15,
            "score": adopter_score,
            "measured": adopter_score is not None,
            "basis": (
                f"{adopter_matches} customer/adopter "
                "indicators found."
            ),
        },
        {
            "key": "commercial_pathway",
            "label": "Commercialisation pathway",
            "weight": 10,
            "score": adopter_score,
            "measured": adopter_score is not None,
            "basis": (
                "Uses explicit adopter/customer/"
                "commercial signals."
            ),
        },
        {
            "key": "regulatory",
            "label": "Regulatory / adoption readiness",
            "weight": 10,
            "score": regulatory_score,
            "measured": regulatory_score is not None,
            "basis": (
                f"{regulatory_matches} regulatory/"
                "safety indicators found."
            ),
        },
        {
            "key": "resources",
            "label": "Supply / resource feasibility",
            "weight": 10,
            "score": None,
            "measured": False,
            "basis": (
                "Not measured in this MVP."
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
        "classification": classification(
            score
        ),
        "components": components,
        "inputs": {
            "research_records": len(
                papers
            ),
            "query_count": len(
                evidence
            ),
        },
        "methodology": (
            "Market viability is a provisional decision-support "
            "measure. It uses only evidence present in the proposal "
            "or retrieved research set. Missing commercial evidence "
            "remains unmeasured."
        ),
    }


def build_assessment(
    dossier: dict[str, Any],
    research: dict[str, Any],
    novelty: dict[str, Any] | None,
) -> dict[str, Any]:

    translation = (
        calculate_translation(
            dossier
        )
    )

    market = (
        calculate_market_viability(
            dossier,
            research,
        )
    )

    return {
        "novelty": novelty,
        "translation": translation,
        "market": market,
    }
