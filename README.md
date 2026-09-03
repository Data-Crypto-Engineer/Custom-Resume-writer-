# AI Job-Tailored Resume Generator

A simple Streamlit app that turns your existing resumes into a resume
tailored for a specific job description, using the Groq API.

Upload 1-5 resumes (PDF/DOCX), paste a job description, and the app:

- Merges all your resumes into one master profile (no duplicate info,
  most recent/complete version wins on conflicts).
- Generates a concise, ATS-friendly resume tailored to the role, using
  **only** information already present in your resumes.
- Estimates an ATS score and a job-match score.
- Lists skills the job wants that your resumes don't show.
- Suggests improvements for future applications.

## Project structure

```
app.py              Streamlit UI - orchestrates everything
resume_parser.py    Extracts text from PDF / DOCX resumes
llm.py               Builds the prompt and calls the Groq API
config.py            Configuration (model name, limits, API key)
requirements.txt     Python dependencies
.env.example          Template for your API key
```

Dependency flow is one-way: `app.py` → `resume_parser.py` / `llm.py` → `config.py`.

## 1. Get a Groq API key

Sign up at [console.groq.com](https://console.groq.com) and create an API key.

## 2. Run locally

```bash
# Clone or copy the project files into a folder, then:
cd resume-generator

# Install dependencies
pip install -r requirements.txt

# Add your API key
cp .env.example .env
# then edit .env and paste your real GROQ_API_KEY

# Run the app
streamlit run app.py
```

Streamlit will open the app at `http://localhost:8501`.

## 3. Run in Google Colab (via Cloudflare Tunnel)

Colab doesn't let you open `localhost` directly, so we use a free
Cloudflare Tunnel to get a public URL that points at the Streamlit app
running inside the Colab VM.

Paste the following into Colab cells, one block per cell:

**Cell 1 - upload your project files**

Upload `app.py`, `resume_parser.py`, `llm.py`, `config.py`, and
`requirements.txt` into the Colab file browser (or `git clone` your repo).

**Cell 2 - install dependencies**

```python
!pip install -r requirements.txt -q
```

**Cell 3 - set your API key**

```python
import os
os.environ["GROQ_API_KEY"] = "your_real_groq_api_key_here"
```

**Cell 4 - download cloudflared**

```python
!wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
!chmod +x cloudflared-linux-amd64
```

**Cell 5 - start Streamlit in the background**

```python
!nohup streamlit run app.py --server.port 8501 &> streamlit_log.txt &
```

**Cell 6 - start the Cloudflare Tunnel and get your public URL**

```python
!nohup ./cloudflared-linux-amd64 tunnel --url http://localhost:8501 &> cloudflared_log.txt &
import time
time.sleep(6)
!grep -o 'https://[a-zA-Z0-9.-]*\.trycloudflare\.com' cloudflared_log.txt | head -n 1
```

**Cell 7 - open the app**

Copy the `https://....trycloudflare.com` URL printed above and open it
in your browser. That's your live app, running from the Colab VM.

> Tip: if the URL doesn't print right away, wait a few seconds and
> re-run Cell 6's last line, or check `cloudflared_log.txt` directly.

## Notes

- Resumes are processed in memory only; nothing is saved to disk.
- The app never invents experience, skills, or education - it only
  reorganizes and rewrites what's already in your uploaded resumes.
- To use a different Groq model, change `MODEL_NAME` in `config.py`.
