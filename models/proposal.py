from dataclasses import dataclass
from typing import Optional


@dataclass
class Proposal:

    title: Optional[str] = None

    funding_initiative: Optional[str] = None

    document_type: Optional[str] = None

    problem: Optional[str] = None

    technology: Optional[str] = None

    baseline: Optional[str] = None

    proposed_solution: Optional[str] = None

    trl_start: Optional[int] = None

    trl_target: Optional[int] = None
