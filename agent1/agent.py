import json
from pathlib import Path

from common.llm_client import LLMClient


PROMPT_PATH = (
    Path(__file__).resolve()
    .parents[1]
    / "prompts"
    / "agent1_prompt.txt"
)


class Agent1:

    def __init__(self):

        self.llm = LLMClient()

        self.prompt = (
            PROMPT_PATH
            .read_text(
                encoding="utf-8"
            )
        )

    def analyze(self, document):

        pages = []

        for page_number, text in enumerate(
            document.pages,
            start=1
        ):

            pages.append({

                "page": page_number,

                "text": text

            })

        input_data = {

            "filename":
                document.filename,

            "file_type":
                document.file_type,

            "page_count":
                document.page_count,

            "pages":
                pages
        }

        result = self.llm.generate_json(
            self.prompt,
            input_data
        )

        return result
