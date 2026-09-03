"""
config.py
---------
Central place for configuration values used across the app.

Keeping configuration in one file means that if we ever want to
change the model, file limits, or supported formats, we only need
to edit this one place.
"""

import os
from dotenv import load_dotenv

# Load variables from a .env file into the environment (if present).
load_dotenv()

# --- Groq API settings -----------------------------------------------------

# The Groq API key is read from the environment, never hardcoded.
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

# The model used for resume generation. Change this single value to
# switch to another Groq-supported model.
# Note: llama-3.3-70b-versatile was moved to Groq's Enterprise tier and
# is no longer reachable with a standard developer API key, so we use
# openai/gpt-oss-120b (Groq's current recommended general-purpose model).
MODEL_NAME: str = "openai/gpt-oss-120b"

# --- Upload limits -----------------------------------------------------

# Maximum number of resumes a user may upload at once.
MAX_RESUMES: int = 5

# File extensions we know how to extract text from.
SUPPORTED_EXTENSIONS: tuple[str, ...] = (".pdf", ".docx")

# --- LLM generation settings -----------------------------------------------------

# Groq's tokens-per-minute (TPM) ceiling for the free/on-demand tier.
# Every request's (prompt tokens + max output tokens) must fit under this.
# Raise this only if you've confirmed a higher TPM limit on your Groq tier.
TPM_LIMIT: int = 8000

# Tokens held back as a safety margin below TPM_LIMIT, to account for the
# rough chars-per-token estimate not being exact.
TPM_SAFETY_MARGIN: int = 300

# The floor and ceiling for the model's response length. The actual value
# used per-request is calculated dynamically (TPM_LIMIT minus the
# estimated prompt size) so that short inputs (2-3 resumes) get a larger
# output budget - enough to finish the resume AND the ATS/match analysis -
# while long inputs (4-5 resumes) automatically get a smaller, safer
# output budget instead of failing outright.
MIN_OUTPUT_TOKENS: int = 900
MAX_OUTPUT_TOKENS: int = 3000

# Sampling temperature. Lower value keeps the output focused and factual,
# which matters since we never want the model to invent information.
TEMPERATURE: float = 0.3

# Rough safety cap on the combined size (in characters) of the master
# resume context + job description sent to the model. This is a coarse
# ~4-chars-per-token estimate, used to stay under the tokens-per-minute
# rate limit alongside MAX_OUTPUT_TOKENS above. Increase this only if
# you've confirmed your Groq tier's TPM limit can support it.
MAX_INPUT_CHARS: int = 18000
