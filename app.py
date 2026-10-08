import streamlit as st
import tempfile
import os
import json
from pathlib import Path
from pipeline.orchestrator import run_pipeline
from core.exceptions import PipelineError, SchemaBoundaryError

st.set_page_config(page_title="AI Contract Counsel", layout="wide")

st.title("⚖️ Contract Graph Counsel")
st.markdown("Upload a contract to analyze its structure, identify risks, and verify against Indian Central-Law knowledge.")

# Settings Sidebar
st.sidebar.header("Settings")
st.sidebar.markdown("**Ollama Integration Active**")
st.sidebar.markdown("LLM Provider: `ollama`")
st.sidebar.markdown("Model: `gemma4:e4b`")

uploaded_file = st.file_uploader("Upload your contract (TXT, PDF, DOCX)", type=["txt", "pdf", "docx"])
custom_prompt = st.text_input("Ask a custom question about this contract (Optional)", "")

if uploaded_file is not None:
    if st.button("Analyze Contract"):
        with st.spinner("Processing document through Agents (Document -> Risk -> Verifier)..."):
            # Save file temporarily
            suffix = Path(uploaded_file.name).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            try:
                # Run the backend pipeline
                report = run_pipeline(tmp_path, None)
                
                # Cleanup temp file
                os.unlink(tmp_path)
                
                st.success("Analysis Complete!")
                
                # Display Summary
                st.header("Executive Summary")
                st.info(report.executive_summary)
                
                # Layout
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("🚨 High Risks")
                    if report.high_risks:
                        for risk in report.high_risks:
                            with st.expander(f"{risk.title} (Score: {risk.priority_score})"):
                                st.write("**Explanation:**", risk.explanation)
                                st.write("**Why it matters:**", risk.why_it_matters)
                                st.write("**Law Verification:**", risk.verification.what_the_law_says)
                    else:
                        st.success("No high risks found.")
                        
                with col2:
                    st.subheader("⚠️ Medium Risks")
                    if report.medium_risks:
                        for risk in report.medium_risks:
                            with st.expander(f"{risk.title} (Score: {risk.priority_score})"):
                                st.write("**Explanation:**", risk.explanation)
                                st.write("**Why it matters:**", risk.why_it_matters)
                    else:
                        st.success("No medium risks found.")
                
                st.subheader("💬 Questions for your Lawyer")
                for q in report.questions_for_lawyer:
                    st.markdown(f"- {q}")
                
                if custom_prompt:
                    st.subheader("Custom Question")
                    # Note: Since the backend doesn't have a direct 'chat' endpoint, 
                    # we would route this to the Ollama API directly as a separate feature,
                    # but for this demo we'll just indicate it's received.
                    st.info(f"You asked: {custom_prompt}\n\n*In a full implementation, this would query the extracted JSON context.*")
                    
                st.subheader("Raw JSON Output")
                with st.expander("View full pipeline JSON output"):
                    st.json(report.model_dump_json(indent=2))
                    
            except Exception as e:
                st.error(f"Pipeline failed: {str(e)}")
