# agent2/run.py

import argparse
import json
import sys

from common.file_parser import parse_document
from agent1.agent import Agent1
from agent2.agent import Agent2


def main():
    parser = argparse.ArgumentParser(
        description="Run Agent 2: Contract Risk Analyst"
    )

    parser.add_argument(
        "file",
        help="Path to PDF, DOCX, or TXT document"
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to save RiskAnalysis JSON"
    )

    args = parser.parse_args()

    try:
        # ---------------------------------------------------------
        # Step 1: Parse document
        # ---------------------------------------------------------
        print(f"Processing: {args.file}")

        pages = parse_document(args.file)

        print(
            f"Extracted {len(pages)} page(s)."
        )

        # ---------------------------------------------------------
        # Step 2: Run Agent 1
        # Document → DocumentAnalysis
        # ---------------------------------------------------------
        print("Running Agent 1...")

        agent1 = Agent1()

        document_analysis = agent1.analyze(
            file_path=args.file,
            pages=pages
        )

        print("Agent 1 completed.")

        # ---------------------------------------------------------
        # Step 3: Run Agent 2
        # DocumentAnalysis → RiskAnalysis
        # ---------------------------------------------------------
        print("Running Agent 2...")

        agent2 = Agent2()

        risk_analysis = agent2.analyze(
            document_analysis=document_analysis
        )

        print("Agent 2 completed.")

        # ---------------------------------------------------------
        # Step 4: Convert result to JSON
        # ---------------------------------------------------------
        output = json.dumps(
            risk_analysis,
            indent=2,
            ensure_ascii=False
        )

        print("\n" + "=" * 70)
        print("AGENT 2 - RISK ANALYSIS")
        print("=" * 70)

        print(output)

        # ---------------------------------------------------------
        # Step 5: Save output if requested
        # ---------------------------------------------------------
        if args.output:
            with open(
                args.output,
                "w",
                encoding="utf-8"
            ) as f:
                f.write(output)

            print(
                f"\nRisk analysis saved to: {args.output}"
            )

    except FileNotFoundError as e:
        print(
            f"\nERROR: File not found: {e}"
        )
        sys.exit(1)

    except ValueError as e:
        print(
            f"\nERROR: {e}"
        )
        sys.exit(1)

    except Exception as e:
        print(
            f"\nERROR while running Agent 2: {e}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
