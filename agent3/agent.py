# agent3/agent.py

import json
from pathlib import Path
from typing import Any, Dict, List

from common.config import Settings
from common.llm_client import LLMClient

from agent3.retriever import LegalRetriever


class Agent3:
    """
    Agent 3: Indian Central-Law Verifier

    Input:
        DocumentAnalysis
        RiskAnalysis

    Retrieval:
        Indian Central-Law knowledge base

    Output:
        VerifiedAnalysis
    """

    def __init__(self):

        self.settings = Settings()

        self.llm = LLMClient(
            self.settings
        )

        self.retriever = LegalRetriever(
            self.settings.legal_data_dir
        )

        prompt_path = Path(
            "prompts/agent3_prompt.txt"
        )

        if not prompt_path.exists():
            raise FileNotFoundError(
                "Agent 3 prompt not found: "
                f"{prompt_path}"
            )

        self.system_prompt = (
            prompt_path.read_text(
                encoding="utf-8"
            )
        )

    # ---------------------------------------------------------
    # Retrieve legal sources
    # ---------------------------------------------------------

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

            query = " ".join(
                [
                    str(title),
                    str(explanation),
                    str(category)
                ]
            )

            results = self.retriever.search(
                query=query,
                top_k=5
            )

            retrieved_sources[risk_id] = results

        return retrieved_sources

    # ---------------------------------------------------------
    # Verify
    # ---------------------------------------------------------

    def verify(
        self,
        document_analysis: Dict[str, Any],
        risk_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:

        document_id = document_analysis.get(
            "document_id"
        )

        risk_document_id = risk_analysis.get(
            "document_id"
        )

        # -----------------------------------------------------
        # Make sure Agent 1 and Agent 2 refer to same document
        # -----------------------------------------------------

        if document_id != risk_document_id:

            raise ValueError(
                "Document ID mismatch between "
                "DocumentAnalysis and RiskAnalysis."
            )

        # -----------------------------------------------------
        # Retrieve legal sources
        # -----------------------------------------------------

        print(
            f"Loaded {self.retriever.count()} "
            f"legal knowledge record(s)."
        )

        retrieved_sources = (
            self._retrieve_sources(
                risk_analysis
            )
        )

        # -----------------------------------------------------
        # Build LLM input
        # -----------------------------------------------------

        payload = {
            "document_analysis": document_analysis,
            "risk_analysis": risk_analysis,
            "retrieved_legal_sources": retrieved_sources
        }

        # -----------------------------------------------------
        # Call LLM
        # -----------------------------------------------------

        result = self.llm.generate_json(
            system_prompt=self.system_prompt,
            user_payload=payload
        )

        # -----------------------------------------------------
        # Basic validation
        # -----------------------------------------------------

        if not isinstance(result, dict):
            raise ValueError(
                "Agent 3 returned invalid JSON object."
            )

        # -----------------------------------------------------
        # Document ID must remain unchanged
        # -----------------------------------------------------

        result_document_id = result.get(
            "document_id"
        )

        if result_document_id != document_id:

            raise ValueError(
                "Agent 3 changed the document_id."
            )

        # -----------------------------------------------------
        # Check risk IDs
        # -----------------------------------------------------

        input_risk_ids = {
            risk.get("risk_id")
            for risk in risk_analysis.get(
                "risks",
                []
            )
            if risk.get("risk_id")
        }

        verified_risks = result.get(
            "verified_risks",
            []
        )

        for verified_risk in verified_risks:

            risk_id = verified_risk.get(
                "risk_id"
            )

            if risk_id not in input_risk_ids:

                raise ValueError(
                    "Agent 3 returned an unknown "
                    f"risk_id: {risk_id}"
                )

        return result
