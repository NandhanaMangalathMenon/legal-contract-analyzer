# common/config.py

import os
from dataclasses import dataclass

from dotenv import load_dotenv


# Load variables from .env
load_dotenv()


@dataclass
class Settings:
    """
    Shared configuration for the entire project.
    """

    # ---------------------------------------------------------
    # LLM configuration
    # ---------------------------------------------------------

    llm_base_url: str = os.getenv(
        "LLM_BASE_URL",
        "http://localhost:11434/v1"
    )

    llm_api_key: str = os.getenv(
        "LLM_API_KEY",
        "ollama"
    )

    llm_model: str = os.getenv(
        "LLM_MODEL",
        "gemma3:4b"
    )

    # ---------------------------------------------------------
    # Model parameters
    # ---------------------------------------------------------

    temperature: float = float(
        os.getenv(
            "MODEL_TEMPERATURE",
            "0.2"
        )
    )

    frequency_penalty: float = float(
        os.getenv(
            "MODEL_FREQUENCY_PENALTY",
            "0.0"
        )
    )

    presence_penalty: float = float(
        os.getenv(
            "MODEL_PRESENCE_PENALTY",
            "0.0"
        )
    )

    # ---------------------------------------------------------
    # Legal RAG configuration
    # ---------------------------------------------------------

    legal_data_dir: str = os.getenv(
        "LEGAL_DATA_DIR",
        "./data/legal_knowledge"
    )

    vector_db_dir: str = os.getenv(
        "VECTOR_DB_DIR",
        "./data/vector_db"
    )

    # ---------------------------------------------------------
    # LLM request configuration
    # ---------------------------------------------------------

    request_timeout: int = int(
        os.getenv(
            "LLM_REQUEST_TIMEOUT",
            "120"
        )
    )
