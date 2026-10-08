# agent2/agent.py

from pathlib import Path
from typing import Any, Dict

from common.config import Settings
from common.llm_client import LLMClient
from common.validation import (
    validate_document_analysis,
    validate_risk_analysis
)


class Agent2:
    """
    Agent 2: Contract Risk Analyst

    Input:
        DocumentAnalysis

    Output:
        RiskAnalysis

    Agent 2 identifies potentially problematic
    contractual provisions.

    Agent 2 does NOT:
        - perform legal research
        - verify statutes
        - create legal citations
        - declare something illegal
        - give final legal conclusions
    """

    def __init__(self):

        self.settings = Settings()

        self.llm = LLMClient(
            self.settings
        )

        prompt_path = Path(
            "prompts/agent2_prompt.txt"
        )

        if not prompt_path.exists():

            raise FileNotFoundError(
                f"Agent 2 prompt not found: {prompt_path}"
            )

        self.system_prompt = (
            prompt_path.read_text(
                encoding="utf-8"
            )
        )

    # ---------------------------------------------------------
    # Analyze risks
    # ---------------------------------------------------------

    def analyze(
        self,
        document_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:

        # -----------------------------------------------------
        # Validate Agent 1 input
        # -----------------------------------------------------

        if not isinstance(
            document_analysis,
            dict
        ):

            raise ValueError(
                "Agent 2 received invalid "
                "DocumentAnalysis."
            )

        try:

            validate_document_analysis(
                document_analysis
            )

        except ValueError as e:

            raise ValueError(
                "Agent 2 received DocumentAnalysis "
                "that does not match the schema:\n"
                f"{e}"
            ) from e

        # -----------------------------------------------------
        # Get document ID
        # -----------------------------------------------------

        document_id = document_analysis.get(
            "document_id"
        )

        # -----------------------------------------------------
        # Build LLM input
        # -----------------------------------------------------

        payload = {
            "document_analysis": document_analysis
        }

        # -----------------------------------------------------
        # Call LLM
        # -----------------------------------------------------

        result = self.llm.generate_json(
            system_prompt=self.system_prompt,
            user_payload=payload
        )

        # -----------------------------------------------------
        # Basic output check
        # -----------------------------------------------------

        if not isinstance(result, dict):

            raise ValueError(
                "Agent 2 returned invalid output. "
                "Expected a JSON object."
            )

        # -----------------------------------------------------
        # Validate against risk_schema.json
        # -----------------------------------------------------

        try:

            validate_risk_analysis(
                result
            )

        except ValueError as e:

            raise ValueError(
                "Agent 2 output failed schema validation:\n"
                f"{e}"
            ) from e

        # -----------------------------------------------------
        # Document ID must remain unchanged
        # -----------------------------------------------------

        result_document_id = result.get(
            "document_id"
        )

        if result_document_id != document_id:

            raise ValueError(
                "Agent 2 changed the document_id."
            )

        # -----------------------------------------------------
        # Collect valid clause IDs
        # -----------------------------------------------------

        valid_clause_ids = {
            clause.get("clause_id")
            for clause in document_analysis.get(
                "clauses",
                []
            )
            if clause.get("clause_id")
        }

        # -----------------------------------------------------
        # Validate risk IDs and clause references
        # -----------------------------------------------------

        risk_ids = set()

        for risk in result.get(
            "risks",
            []
        ):

            risk_id = risk.get(
                "risk_id"
            )

            # -------------------------------------------------
            # Risk ID required
            # -------------------------------------------------

            if not risk_id:

                raise ValueError(
                    "Agent 2 returned a risk "
                    "without risk_id."
                )

            # -------------------------------------------------
            # Risk IDs must be unique
            # -------------------------------------------------

            if risk_id in risk_ids:

                raise ValueError(
                    f"Duplicate risk_id detected: "
                    f"{risk_id}"
                )

            risk_ids.add(
                risk_id
            )

            # -------------------------------------------------
            # Check clause references
            # -------------------------------------------------

            referenced_clause_ids = risk.get(
                "clause_ids",
                []
            )

            for clause_id in referenced_clause_ids:

                if clause_id not in valid_clause_ids:

                    raise ValueError(
                        f"Agent 2 risk {risk_id} "
                        f"references unknown clause_id: "
                        f"{clause_id}"
                    )

            # -------------------------------------------------
            # Check evidence
            # -------------------------------------------------

            for evidence in risk.get(
                "evidence",
                []
            ):

                evidence_clause_id = evidence.get(
                    "clause_id"
                )

                if (
                    evidence_clause_id
                    and evidence_clause_id
                    not in valid_clause_ids
                ):

                    raise ValueError(
                        f"Agent 2 risk {risk_id} "
                        f"contains evidence for unknown "
                        f"clause_id: "
                        f"{evidence_clause_id}"
                    )

        return result
