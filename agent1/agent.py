# agent1/agent.py

from pathlib import Path
from typing import Any, Dict, List

from common.config import Settings
from common.llm_client import LLMClient
from common.validation import validate_document_analysis


class Agent1:
    """
    Agent 1: Document Analyst

    Responsibility:

        PDF/DOCX/TXT
             ↓
        extracted text
             ↓
        document structure
             ↓
        clauses
             ↓
        entities
             ↓
        DocumentAnalysis

    Agent 1 does NOT:
        - identify legal risks
        - perform legal research
        - verify laws
        - give legal advice
    """

    def __init__(self):

        self.settings = Settings()

        self.llm = LLMClient(
            self.settings
        )

        prompt_path = Path(
            "prompts/agent1_prompt.txt"
        )

        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Agent 1 prompt not found: {prompt_path}"
            )

        self.system_prompt = (
            prompt_path.read_text(
                encoding="utf-8"
            )
        )

    # ---------------------------------------------------------
    # Analyze document
    # ---------------------------------------------------------

    def analyze(
        self,
        file_path: str,
        pages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:

        # -----------------------------------------------------
        # Prepare input for LLM
        # -----------------------------------------------------

        payload = {
            "filename": Path(file_path).name,

            "file_type": Path(
                file_path
            ).suffix.lower().replace(
                ".",
                ""
            ),

            "page_count": len(pages),

            "pages": pages
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
                "Agent 1 returned invalid output. "
                "Expected a JSON object."
            )

        # -----------------------------------------------------
        # Validate against document_schema.json
        # -----------------------------------------------------

        try:

            validate_document_analysis(
                result
            )

        except ValueError as e:

            raise ValueError(
                "Agent 1 output failed schema validation:\n"
                f"{e}"
            ) from e

        # -----------------------------------------------------
        # Verify document_id exists
        # -----------------------------------------------------

        document_id = result.get(
            "document_id"
        )

        if not document_id:

            raise ValueError(
                "Agent 1 did not generate a document_id."
            )

        # -----------------------------------------------------
        # Verify clauses have IDs
        # -----------------------------------------------------

        clauses = result.get(
            "clauses",
            []
        )

        clause_ids = set()

        for clause in clauses:

            clause_id = clause.get(
                "clause_id"
            )

            if not clause_id:

                raise ValueError(
                    "Agent 1 returned a clause "
                    "without clause_id."
                )

            if clause_id in clause_ids:

                raise ValueError(
                    f"Duplicate clause_id detected: "
                    f"{clause_id}"
                )

            clause_ids.add(
                clause_id
            )

        return result
