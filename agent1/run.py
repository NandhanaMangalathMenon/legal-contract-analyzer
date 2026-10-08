import json
import sys

from common.file_parser import parse_document
from agent1.agent import Agent1


def main():

    if len(sys.argv) != 2:

        print(
            "Usage: python -m agent1.run <document>"
        )

        return

    document = parse_document(
        sys.argv[1]
    )

    agent = Agent1()

    result = agent.analyze(
        document
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()
