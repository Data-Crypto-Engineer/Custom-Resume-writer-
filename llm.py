"""
llm.py
------
Builds the prompt sent to the LLM and handles the Groq API call.

This file is the only place that talks to Groq. app.py never calls
the Groq SDK directly - it always goes through generate_tailored_resume().
"""

from __future__ import annotations

from groq import Groq

from config import (
    GROQ_API_KEY,
    MAX_INPUT_CHARS,
    MAX_OUTPUT_TOKENS,
    MIN_OUTPUT_TOKENS,
    MODEL_NAME,
    TEMPERATURE,
    TPM_LIMIT,
    TPM_SAFETY_MARGIN,
)


class LLMGenerationError(Exception):
    """Raised when the Groq API call fails or returns something unusable."""


# The instructions that shape how the model behaves. Kept separate from
# the user-specific content (resumes + job description) so it's easy to
# tweak the rules without touching the data-building logic.
SYSTEM_INSTRUCTIONS = """\
You are an expert resume writer and ATS (Applicant Tracking System) specialist.

You will be given:
1. A MASTER RESUME CONTEXT - one or more resumes belonging to the same person.
2. A JOB DESCRIPTION - the role they are applying for.

Your task:
- Read every resume in the master context and merge them into a single,
  accurate profile of the candidate.
- Remove duplicate information. When resumes conflict, prefer the most
  recent or most complete version of the information.
- NEVER invent experience, education, skills, certifications, or
  achievements that are not present in the master resume context.
- Ignore experience that is clearly unrelated to the target role.
- Select only the experiences, skills, and projects relevant to the
  target role.
- Prioritize achievements with measurable, quantifiable impact.
- Rewrite bullet points using strong action verbs and an accomplishment
  focus rather than a responsibility focus.
- Naturally weave in ATS keywords drawn from the job description, but
  only where they are truthfully supported by the candidate's background.
- Produce a concise, one-page-where-possible, professional, ATS-friendly
  resume, using plain text formatting (no markdown tables, no images).
- Only include a section if there is real content for it. Sections to
  consider: Professional Summary, Skills, Technical Skills, Soft Skills,
  Work Experience, Projects, Education, Certifications, Achievements.
- Maintain chronological order within Work Experience and Education
  where appropriate.

After the resume, you MUST also produce an analysis. Format your entire
response EXACTLY as follows, using these literal section headers so the
output can be parsed:

===RESUME===
<the full tailored resume text>

===ATS_SCORE===
<a number from 0-100>
<one or two sentence explanation>

===MATCH_SCORE===
<a number from 0-100>
<one or two sentence explanation>

===MISSING_SKILLS===
<a bullet list of important skills mentioned in the job description that
are missing from the candidate's resumes; write "None identified" if none>

===SUGGESTIONS===
<a bullet list of practical suggestions to improve future applications>

Do not add any text before ===RESUME=== or after the SUGGESTIONS section.
"""


def _build_user_prompt(master_resume_context: str, job_description: str) -> str:
    """
    Combine the resume context and job description into one user message,
    trimming if needed to stay under the rate-limit safety budget.
    """
    # Reserve roughly a third of the character budget for the job
    # description and the rest for the resumes, then trim whichever is
    # too long. This keeps combined input + output tokens under the
    # Groq tokens-per-minute limit.
    jd_budget = MAX_INPUT_CHARS // 3
    resume_budget = MAX_INPUT_CHARS - jd_budget

    trimmed_job_description = job_description[:jd_budget]
    trimmed_resume_context = master_resume_context[:resume_budget]

    return (
        "MASTER RESUME CONTEXT:\n"
        f"{trimmed_resume_context}\n\n"
        "JOB DESCRIPTION:\n"
        f"{trimmed_job_description}\n"
    )


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 characters per token) for budgeting purposes."""
    return max(1, len(text) // 4)


def _calculate_output_budget(prompt_text: str) -> int:
    """
    Work out how many output tokens we can safely request for this
    specific prompt, so short inputs get a larger output budget (enough
    to finish the resume plus the ATS/match analysis) and long inputs
    automatically get a smaller, safer budget instead of hitting a
    tokens-per-minute error.
    """
    estimated_prompt_tokens = _estimate_tokens(prompt_text)
    available = TPM_LIMIT - TPM_SAFETY_MARGIN - estimated_prompt_tokens

    # Clamp between the configured floor and ceiling.
    return max(MIN_OUTPUT_TOKENS, min(available, MAX_OUTPUT_TOKENS))


def generate_tailored_resume(master_resume_context: str, job_description: str) -> str:
    """
    Call the Groq API to generate a tailored resume plus analysis.

    Args:
        master_resume_context: The combined text of all uploaded resumes.
        job_description: The job description pasted by the user.

    Returns:
        The raw text response from the model (still in the ===SECTION===
        format defined in SYSTEM_INSTRUCTIONS - parsing happens in app.py).

    Raises:
        LLMGenerationError: If the API key is missing or the call fails.
    """
    if not GROQ_API_KEY:
        raise LLMGenerationError(
            "GROQ_API_KEY is not set. Add it to your .env file before "
            "generating a resume."
        )

    try:
        client = Groq(api_key=GROQ_API_KEY)

        user_prompt = _build_user_prompt(master_resume_context, job_description)
        output_budget = _calculate_output_budget(SYSTEM_INSTRUCTIONS + user_prompt)

        response = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=TEMPERATURE,
            max_tokens=output_budget,
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content
        if not content or not content.strip():
            raise LLMGenerationError("The model returned an empty response.")

        return content

    except LLMGenerationError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface any Groq/API error clearly
        raise LLMGenerationError(f"Groq API request failed: {exc}") from exc
