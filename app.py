"""
app.py
------
Streamlit UI for the AI Job-Tailored Resume Generator.

Flow:
1. User uploads 1-5 resumes (PDF/DOCX).
2. User pastes a job description.
3. On button click, we extract text from every resume, combine it into
   one master context, send it + the job description to the LLM, and
   display the tailored resume plus ATS/match analysis.

This file only orchestrates the UI. It never talks to pdfplumber/docx
or Groq directly - it always goes through resume_parser.py and llm.py.
"""

from __future__ import annotations

import re

import streamlit as st

from config import GROQ_API_KEY, MAX_RESUMES
from llm import LLMGenerationError, generate_tailored_resume
from resume_parser import ResumeExtractionError, build_master_context, extract_resume

# --- Page setup -----------------------------------------------------

st.set_page_config(page_title="AI Job-Tailored Resume Generator", page_icon="📄")

st.title("📄 AI Job-Tailored Resume Generator")
st.write(
    "Upload up to five of your existing resumes and paste a job description. "
    "The app merges everything you've done into one profile and rewrites a "
    "concise, ATS-friendly resume tailored to that specific role - using "
    "only information that's already in your resumes."
)


def parse_llm_response(raw_response: str) -> dict[str, str]:
    """
    Split the model's raw response into its labeled sections.

    Expects sections marked with ===SECTION_NAME=== headers, as defined
    in llm.SYSTEM_INSTRUCTIONS. Falls back gracefully if a section is
    missing so the UI never crashes on an unexpected response shape.
    """
    section_names = ["RESUME", "ATS_SCORE", "MATCH_SCORE", "MISSING_SKILLS", "SUGGESTIONS"]
    pattern = "|".join(f"==={name}===" for name in section_names)
    parts = re.split(pattern, raw_response)

    # re.split with a pattern of alternatives keeps the text between
    # markers; the first chunk (before ===RESUME===) is discarded.
    found_markers = re.findall(pattern, raw_response)

    sections = {name: "" for name in section_names}
    for marker, content in zip(found_markers, parts[1:]):
        clean_marker = marker.strip("=")
        sections[clean_marker] = content.strip()

    return sections


# --- Resume upload -----------------------------------------------------

st.subheader("1. Upload your resumes")
uploaded_files = st.file_uploader(
    f"Upload 1-{MAX_RESUMES} resumes (PDF or DOCX)",
    type=["pdf", "docx"],
    accept_multiple_files=True,
)

if uploaded_files and len(uploaded_files) > MAX_RESUMES:
    st.error(f"Please upload at most {MAX_RESUMES} resumes. You uploaded {len(uploaded_files)}.")

# --- Job description -----------------------------------------------------

st.subheader("2. Paste the job description")
job_description = st.text_area(
    "Job Description",
    height=250,
    placeholder="Paste the full job description here...",
)

# --- Generate button -----------------------------------------------------

st.subheader("3. Generate")
generate_clicked = st.button("Generate Tailored Resume", type="primary")

if generate_clicked:
    # --- Validation -----------------------------------------------------
    if not GROQ_API_KEY:
        st.error(
            "GROQ_API_KEY is not set. Add it to a .env file in the project "
            "root (see .env.example) and restart the app."
        )
    elif not uploaded_files:
        st.error("Please upload at least one resume before generating.")
    elif len(uploaded_files) > MAX_RESUMES:
        st.error(f"Please upload at most {MAX_RESUMES} resumes.")
    elif not job_description or not job_description.strip():
        st.error("Please paste a job description before generating.")
    else:
        # --- Extraction -----------------------------------------------------
        resume_texts: list[tuple[str, str]] = []
        extraction_failed = False

        with st.spinner("Reading your resumes..."):
            for uploaded_file in uploaded_files:
                try:
                    text = extract_resume(uploaded_file, uploaded_file.name)
                    resume_texts.append((uploaded_file.name, text))
                except ResumeExtractionError as exc:
                    st.error(f"'{uploaded_file.name}': {exc}")
                    extraction_failed = True

        if not extraction_failed and resume_texts:
            master_context = build_master_context(resume_texts)

            # --- Generation -----------------------------------------------------
            with st.spinner("Tailoring your resume with AI... this can take a moment."):
                try:
                    raw_response = generate_tailored_resume(master_context, job_description)
                    sections = parse_llm_response(raw_response)

                    # If the SUGGESTIONS section never appeared, the response
                    # was almost certainly cut off by the output token limit
                    # before it finished - flag this instead of silently
                    # showing an incomplete resume.
                    if not sections.get("SUGGESTIONS", "").strip():
                        st.warning(
                            "The AI's response may have been cut short (this can "
                            "happen with a lot of resume content). Try uploading "
                            "fewer resumes, trimming the longest one, or "
                            "shortening the job description, then generate again."
                        )

                    st.session_state["result"] = sections
                except LLMGenerationError as exc:
                    st.error(f"Resume generation failed: {exc}")

# --- Results -----------------------------------------------------

if "result" in st.session_state:
    sections = st.session_state["result"]

    st.subheader("✅ Your Tailored Resume")
    resume_text = sections.get("RESUME", "").strip()
    if resume_text:
        st.text_area("Generated Resume", value=resume_text, height=400)
        st.download_button(
            "Download Resume (.txt)",
            data=resume_text,
            file_name="tailored_resume.txt",
            mime="text/plain",
        )
    else:
        st.warning("No resume text was returned. Try generating again.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 ATS Score")
        st.write(sections.get("ATS_SCORE", "Not available.") or "Not available.")
    with col2:
        st.subheader("🎯 Job Match Score")
        st.write(sections.get("MATCH_SCORE", "Not available.") or "Not available.")

    st.subheader("🧩 Missing Skills")
    st.write(sections.get("MISSING_SKILLS", "Not available.") or "Not available.")

    st.subheader("💡 Suggested Improvements")
    st.write(sections.get("SUGGESTIONS", "Not available.") or "Not available.")
