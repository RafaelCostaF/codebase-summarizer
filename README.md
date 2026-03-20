# 🧠 Codebase Summarizer

<p align="center">

<img src="https://img.shields.io/badge/LLM-Ready-blue" />
<img src="https://img.shields.io/badge/Simple-Fast-green" />
<img src="https://img.shields.io/badge/Multi--Provider-Supported-purple" />

</p>

> Turn any codebase into a **ready-to-use prompt for LLMs in seconds**

------------------------------------------------------------------------

## 🚀 What it does

-   📂 Scans your project\
-   🧠 Generates summaries per file (LLM)\
-   ⚡ Skips unchanged files (hash-based)\
-   📄 Builds a single prompt ready to paste into any LLM

------------------------------------------------------------------------

## ⚡ Setup (1 minute)

``` bash
pip install -r requirements.txt
```

Create `.env`:

``` env
LLM_PROVIDER=openai
LLM_API_KEY=your-key
LLM_MODEL=gpt-4o-mini

MAX_WORDS_DESCRIPTION_PER_FILE=80
```

------------------------------------------------------------------------

## ▶️ Usage

### CLI

``` bash
python script.py
```

### UI (recommended)

``` bash
streamlit run app.py
```

------------------------------------------------------------------------

## 🧠 How to use

Open `codebase_summary.txt` and paste into ChatGPT / Claude / DeepSeek.

Ask: - Explain architecture\
- Suggest improvements\
- Find issues

------------------------------------------------------------------------

## 💡 Why this is useful

-   ⚡ Understand large codebases instantly\
-   🚀 Faster onboarding\
-   🧠 Better AI-assisted development

------------------------------------------------------------------------

## 🔄 How it works

``` mermaid
graph TD
A[Scan Files] --> B[Generate Summaries]
B --> C{File Changed?}
C -->|Yes| D[Regenerate Summary]
C -->|No| E[Reuse Summary]
D --> F[Aggregate]
E --> F
F --> G[Generate Prompt]
G --> H[Paste into LLM]
```

------------------------------------------------------------------------

## ⭐ Star this repo if it helped you!
