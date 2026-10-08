from __future__ import annotations

from schemas.common import Severity
from schemas.risk import RiskFinding

_SEVERITY_WEIGHT = {
    Severity.CRITICAL: 40,
    Severity.HIGH: 30,
    Severity.MEDIUM: 18,
    Severity.LOW: 8,
    Severity.INFO: 2,
}


def explainable_priority_score(finding: RiskFinding, dependency_complexity: int = 0) -> tuple[int, dict[str, int]]:
    """Deterministic, inspectable score. Not a neural risk score and not 0-100 from Agent 2."""
    factors = finding.risk_factors
    parts = {
        "severity": _SEVERITY_WEIGHT[finding.severity],
        "financial_exposure": factors.financial_exposure * 4,
        "termination_difficulty": factors.termination_difficulty * 4,
        "asymmetry": factors.asymmetry * 3,
        "ambiguity": factors.ambiguity * 3,
        "obligation_strength": factors.obligation_strength * 2,
        "dependency_complexity": min(dependency_complexity, 8) * 2,
    }
    return sum(parts.values()), parts
