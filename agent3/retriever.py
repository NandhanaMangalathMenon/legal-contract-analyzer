# agent3/retriever.py

import json
import re
from pathlib import Path
from typing import Any, Dict, List


class LegalRetriever:
    """
    Simple legal knowledge-base retriever.

    It searches JSON files inside the legal knowledge directory
    and returns the most relevant legal sources for a query.

    Later this can be upgraded to:
        TF-IDF
        +
        Embeddings
        +
        Vector database
    """

    def __init__(self, knowledge_dir: str):
        self.knowledge_dir = Path(knowledge_dir)
        self.documents: List[Dict[str, Any]] = []

        self._load_documents()

    # ---------------------------------------------------------
    # Load legal documents
    # ---------------------------------------------------------

    def _load_documents(self):
        if not self.knowledge_dir.exists():
            print(
                f"Warning: legal knowledge directory does not exist: "
                f"{self.knowledge_dir}"
            )
            return

        for file_path in self.knowledge_dir.rglob("*.json"):

            try:
                with open(
                    file_path,
                    "r",
                    encoding="utf-8"
                ) as f:

                    data = json.load(f)

                # Support one JSON object
                if isinstance(data, dict):
                    self.documents.append(data)

                # Support a JSON array of documents
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            self.documents.append(item)

            except json.JSONDecodeError:
                print(
                    f"Warning: Invalid JSON file skipped: "
                    f"{file_path}"
                )

            except Exception as e:
                print(
                    f"Warning: Could not load {file_path}: {e}"
                )

    # ---------------------------------------------------------
    # Tokenization
    # ---------------------------------------------------------

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """
        Basic tokenizer.

        Example:

        "termination notice of 90 days"

        becomes approximately:

        ["termination", "notice", "90", "days"]
        """

        text = text.lower()

        return re.findall(
            r"\b[a-zA-Z0-9]+\b",
            text
        )

    # ---------------------------------------------------------
    # Score document
    # ---------------------------------------------------------

    def _score(
        self,
        query: str,
        document: Dict[str, Any]
    ) -> float:

        query_tokens = set(
            self._tokenize(query)
        )

        if not query_tokens:
            return 0.0

        # Combine searchable fields
        searchable_parts = [
            str(document.get("name", "")),
            str(document.get("title", "")),
            str(document.get("section", "")),
            str(document.get("text", "")),
            str(document.get("legal_topics", "")),
            str(document.get("case_name", "")),
            str(document.get("citation", ""))
        ]

        searchable_text = " ".join(
            searchable_parts
        )

        document_tokens = set(
            self._tokenize(searchable_text)
        )

        if not document_tokens:
            return 0.0

        # Basic overlap score
        intersection = (
            query_tokens.intersection(
                document_tokens
            )
        )

        return len(intersection) / len(query_tokens)

    # ---------------------------------------------------------
    # Search
    # ---------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:

        scored_documents = []

        for document in self.documents:

            score = self._score(
                query,
                document
            )

            if score > 0:
                scored_documents.append(
                    (score, document)
                )

        # Highest score first
        scored_documents.sort(
            key=lambda item: item[0],
            reverse=True
        )

        results = []

        for score, document in scored_documents[:top_k]:

            result = dict(document)

            # Keep retrieval score for debugging
            result["_retrieval_score"] = round(
                score,
                4
            )

            results.append(result)

        return results

    # ---------------------------------------------------------
    # Number of loaded documents
    # ---------------------------------------------------------

    def count(self) -> int:
        return len(self.documents)
