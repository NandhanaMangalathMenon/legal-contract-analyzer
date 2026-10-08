from pathlib import Path

from common.llm_client import LLMClient


PROMPT_PATH = (
    Path(__file__).resolve()
    .parents[1]
    / "prompts"
    / "agent2_prompt.txt"
)


class Agent2:

    def __init__(self):

        self.llm = LLMClient()

        self.prompt = (
            PROMPT_PATH
            .read_text(
                encoding="utf-8"
            )
        )

    def analyze(
        self,
        document_analysis
    ):

        result = self.llm.generate_json(

            self.prompt,

            {
                "document_analysis":
                    document_analysis
            }
        )

        return result
