# agent3/agent.py

from pathlib import Path
from typing import Any, Dict, List

from common.config import Settings
from common.llm_client import LLMClient

from common.validation import (
    validate_document_analysis,
    validate_risk_analysis,
    validate_verified_analysis
)

from agent3.retriever import LegalRetriever


class Agent3:
    """
    Agent 3: Indian Central-Law Verifier

    Input:

        DocumentAnalysis
        +
        RiskAnalysis

    Retrieval:

        Indian Central-Law knowledge base

    Output:

        VerifiedAnalysis

    Agent 3 does NOT:
        - create new contractual risks
        - invent legal sources
        - invent sections
        - invent case citations
        - provide unsupported legal claims
    """

    def __init__(self):

        self.settings = Settings()

        self.llm = LLMClient(
            self.settings
        )

        # -----------------------------------------------------
        # Load Agent 3 prompt
        # -----------------------------------------------------

        prompt_path = Path(
            "prompts/agent3_prompt.txt"
        )

        if not prompt_path.exists():

            raise FileNotFoundError(
                f"Agent 3 prompt not found: {prompt_path}"
            )

        self.system_prompt = (
            prompt_path.read_text(
                encoding="utf-8"
            )
        )

        # -----------------------------------------------------
        # Initialize legal retriever
        # -----------------------------------------------------

        self.retriever = LegalRetriever(
            self.settings.legal_data_dir
        )

    # =========================================================
    # Retrieve legal sources
    # =========================================================

    def _retrieve_sources(
        self,
        risk_analysis: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:

        retrieved_sources = {}

        risks = risk_analysis.get(
            "risks",
            []
        )

        for risk in risks:

            risk_id = risk.get(
                "risk_id"
            )

            title = risk.get(
                "title",
                ""
            )

            explanation = risk.get(
                "explanation",
                ""
            )

            category = risk.get(
                "category",
                ""
            )

            # -------------------------------------------------
            # Build retrieval query
            # -------------------------------------------------

            query_parts = [
                str(title),
                str(explanation),
                str(category)
            ]

            query = " ".join(
                query_parts
            )

            # -------------------------------------------------
            # Search legal knowledge base
            # -------------------------------------------------

            results = self.retriever.search(
                query=query,
                top_k=5
            )

            retrieved_sources[
                risk_id
            ] = results

        return retrieved_sources

    # =========================================================
    # Verify risks
    # =========================================================

    def verify(
        self,
        document_analysis: Dict[str, Any],
        risk_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:

        # =====================================================
        # STEP 1
        # Validate DocumentAnalysis
        # =====================================================

        if not isinstance(
            document_analysis,
            dict
        ):

            raise ValueError(
                "Agent 3 received invalid "
                "DocumentAnalysis."
            )

        try:

            validate_document_analysis(
                document_analysis
            )

        except ValueError as e:

            raise ValueError(
                "Agent 3 received invalid "
                "DocumentAnalysis:\n"
                f"{e}"
            ) from e

        # =====================================================
        # STEP 2
        # Validate RiskAnalysis
        # =====================================================

        if not isinstance(
            risk_analysis,
            dict
        ):

            raise ValueError(
                "Agent 3 received invalid "
                "RiskAnalysis."
            )

        try:

            validate_risk_analysis(
                risk_analysis
            )

        except ValueError as e:

            raise ValueError(
                "Agent 3 received invalid "
                "RiskAnalysis:\n"
                f"{e}"
            ) from e

        # =====================================================
        # STEP 3
        # Check document IDs
        # =====================================================

        document_id = document_analysis.get(
            "document_id"
        )

        risk_document_id = risk_analysis.get(
            "document_id"
        )

        if document_id != risk_document_id:

            raise ValueError(
                "Document ID mismatch between "
                "DocumentAnalysis and RiskAnalysis."
            )

        # =====================================================
        # STEP 4
        # Retrieve legal sources
        # =====================================================

        print(
            f"Loaded {self.retriever.count()} "
            "legal knowledge record(s)."
        )

        retrieved_sources = (
            self._retrieve_sources(
                risk_analysis
            )
        )

        # =====================================================
        # STEP 5
        # Build LLM payload
        # =====================================================

        payload = {
            "document_analysis": document_analysis,

            "risk_analysis": risk_analysis,

            "retrieved_legal_sources": (
                retrieved_sources
            )
        }

        # =====================================================
        # STEP 6
        # Call LLM
        # =====================================================

        result = self.llm.generate_json(
            system_prompt=self.system_prompt,
            user_payload=payload
        )

        # =====================================================
        # STEP 7
        # Basic output check
        # =====================================================

        if not isinstance(
            result,
            dict
        ):

            raise ValueError(
                "Agent 3 returned invalid output. "
                "Expected a JSON object."
            )

        # =====================================================
        # STEP 8
        # Validate against verification schema
        # =====================================================

        try:

            validate_verified_analysis(
                result
            )

        except ValueError as e:

            raise ValueError(
                "Agent 3 output failed schema validation:\n"
                f"{e}"
            ) from e

        # =====================================================
        # STEP 9
        # Document ID must remain unchanged
        # =====================================================

        result_document_id = result.get(
            "document_id"
        )

        if result_document_id != document_id:

            raise ValueError(
                "Agent 3 changed the document_id."
            )

        # =====================================================
        # STEP 10
        # Collect original risk IDs
        # =====================================================

        input_risk_ids = {
            risk.get("risk_id")
            for risk in risk_analysis.get(
                "risks",
                []
            )
            if risk.get("risk_id")
        }

        # =====================================================
        # STEP 11
        # Collect original clause IDs
        # =====================================================

        valid_clause_ids = {
            clause.get("clause_id")
            for clause in document_analysis.get(
                "clauses",
                []
            )
            if clause.get("clause_id")
        }

        # =====================================================
        # STEP 12
        # Validate every verified risk
        # =====================================================

        verified_risk_ids = set()

        for verified_risk in result.get(
            "verified_risks",
            []
        ):

            risk_id = verified_risk.get(
                "risk_id"
            )

            # -------------------------------------------------
            # Risk must exist in Agent 2
            # -------------------------------------------------

            if risk_id not in input_risk_ids:

                raise ValueError(
                    "Agent 3 returned unknown "
                    f"risk_id: {risk_id}"
                )

            # -------------------------------------------------
            # Risk IDs must be unique
            # -------------------------------------------------

            if risk_id in verified_risk_ids:

                raise ValueError(
                    "Agent 3 returned duplicate "
                    f"risk_id: {risk_id}"
                )

            verified_risk_ids.add(
                risk_id
            )

            # -------------------------------------------------
            # Validate contract evidence
            # -------------------------------------------------

            for evidence in verified_risk.get(
                "contract_evidence",
                []
            ):

                clause_id = evidence.get(
                    "clause_id"
                )

                if clause_id not in valid_clause_ids:

                    raise ValueError(
                        f"Agent 3 risk {risk_id} "
                        f"references unknown "
                        f"clause_id: {clause_id}"
                    )

        return result
