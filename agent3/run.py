# agent3/run.py

import argparse
import json
import sys

from common.file_parser import parse_document

from agent1.agent import Agent1
from agent2.agent import Agent2
from agent3.agent import Agent3


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Run Agent 3: "
            "Indian Central-Law Verifier"
        )
    )

    parser.add_argument(
        "file",
        help=(
            "Path to PDF, DOCX, "
            "or TXT document"
        )
    )

    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Optional path to save "
            "VerifiedAnalysis JSON"
        )
    )

    args = parser.parse_args()

    try:

        # =====================================================
        # STEP 1
        # Parse document
        # =====================================================

        print(
            f"\nProcessing document: {args.file}"
        )

        pages = parse_document(
            args.file
        )

        print(
            f"Extracted {len(pages)} page(s)."
        )

        # =====================================================
        # STEP 2
        # Agent 1
        # =====================================================

        print(
            "\n[1/3] Running Agent 1..."
        )

        agent1 = Agent1()

        document_analysis = agent1.analyze(
            file_path=args.file,
            pages=pages
        )

        print(
            "Agent 1 completed."
        )

        # =====================================================
        # STEP 3
        # Agent 2
        # =====================================================

        print(
            "\n[2/3] Running Agent 2..."
        )

        agent2 = Agent2()

        risk_analysis = agent2.analyze(
            document_analysis=document_analysis
        )

        print(
            "Agent 2 completed."
        )

        # =====================================================
        # STEP 4
        # Agent 3
        # =====================================================

        print(
            "\n[3/3] Running Agent 3..."
        )

        agent3 = Agent3()

        verified_analysis = agent3.verify(
            document_analysis=document_analysis,
            risk_analysis=risk_analysis
        )

        print(
            "Agent 3 completed."
        )

        # =====================================================
        # STEP 5
        # Final result
        # =====================================================

        output_data = {
            "document_analysis": document_analysis,
            "risk_analysis": risk_analysis,
            "verified_analysis": verified_analysis
        }

        output = json.dumps(
            output_data,
            indent=2,
            ensure_ascii=False
        )

        print(
            "\n" + "=" * 70
        )

        print(
            "AGENT 3 - VERIFIED ANALYSIS"
        )

        print(
            "=" * 70
        )

        print(output)

        # =====================================================
        # STEP 6
        # Save result
        # =====================================================

        if args.output:

            with open(
                args.output,
                "w",
                encoding="utf-8"
            ) as f:

                f.write(output)

            print(
                f"\nResult saved to: {args.output}"
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
            f"\nAGENT 3 ERROR: {e}"
        )

        sys.exit(1)


if __name__ == "__main__":
    main()
