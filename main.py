# main.py

import argparse
import json
import sys

from common.file_parser import parse_document
from agent1.agent import Agent1
from agent2.agent import Agent2
from agent3.agent import Agent3


def run_pipeline(file_path: str) -> dict:
    """
    Full pipeline:

    Document
       ↓
    Agent 1: Document Analysis
       ↓
    Agent 2: Contract Risk Analysis
       ↓
    Agent 3: Indian Central-Law Verification
       ↓
    Final result
    """

    print(f"Processing document: {file_path}")

    # ---------------------------------------------------------
    # Step 1: Parse the uploaded document
    # ---------------------------------------------------------
    print("[1/4] Parsing document...")

    pages = parse_document(file_path)

    print(f"      Extracted {len(pages)} page(s).")

    # ---------------------------------------------------------
    # Step 2: Agent 1
    # Document → DocumentAnalysis
    # ---------------------------------------------------------
    print("[2/4] Running Agent 1: Document Analyst...")

    agent1 = Agent1()

    document_analysis = agent1.analyze(
        file_path=file_path,
        pages=pages
    )

    print("      Agent 1 completed.")

    # ---------------------------------------------------------
    # Step 3: Agent 2
    # DocumentAnalysis → RiskAnalysis
    # ---------------------------------------------------------
    print("[3/4] Running Agent 2: Contract Risk Analyst...")

    agent2 = Agent2()

    risk_analysis = agent2.analyze(
        document_analysis=document_analysis
    )

    print("      Agent 2 completed.")

    # ---------------------------------------------------------
    # Step 4: Agent 3
    # DocumentAnalysis + RiskAnalysis + RAG
    # → VerifiedAnalysis
    # ---------------------------------------------------------
    print("[4/4] Running Agent 3: Indian Central-Law Verifier...")

    agent3 = Agent3()

    verified_analysis = agent3.verify(
        document_analysis=document_analysis,
        risk_analysis=risk_analysis
    )

    print("      Agent 3 completed.")

    # ---------------------------------------------------------
    # Final output
    # ---------------------------------------------------------
    return {
        "document_analysis": document_analysis,
        "risk_analysis": risk_analysis,
        "verified_analysis": verified_analysis
    }


def main():
    parser = argparse.ArgumentParser(
        description="AI Legal Contract Risk Analysis Pipeline"
    )

    parser.add_argument(
        "file",
        help="Path to PDF, DOCX, or TXT document"
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to save the final JSON output"
    )

    args = parser.parse_args()

    try:
        result = run_pipeline(args.file)

        # Convert to JSON
        output = json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        )

        # Print result
        print("\n" + "=" * 70)
        print("FINAL ANALYSIS")
        print("=" * 70)
        print(output)

        # Save if requested
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
        print(f"\nERROR: File not found: {e}")
        sys.exit(1)

    except ValueError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"\nPIPELINE ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
