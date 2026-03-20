# 🧠 Codebase Summarizer

```{=html}
<p align="center">
```
`<img src="https://img.shields.io/badge/LLM-Ready-blue" />`{=html}
`<img src="https://img.shields.io/badge/Simple-Fast-green" />`{=html}
`<img src="https://img.shields.io/badge/Multi--Provider-Supported-purple" />`{=html}
```{=html}
</p>
```
Turn any codebase into a **ready-to-use prompt for LLMs** in seconds.

------------------------------------------------------------------------

## 🚀 What it does

1.  Scans your project\
2.  Summarizes each file using an LLM\
3.  Generates a single `.txt` with:
    -   folder structure\
    -   file summaries\
    -   prompt ready to paste

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

Run CLI:

``` bash
python script.py
```

Run UI (recommended):

``` bash
streamlit run app.py
```

------------------------------------------------------------------------

## 🧠 How to use

Open `codebase_summary.txt` and paste into any LLM.

Ask: - Explain the architecture\
- Suggest improvements\
- Find problems

------------------------------------------------------------------------

## 💡 Why use it

-   Understand large projects fast\
-   Reduce onboarding time\
-   Improve AI-assisted coding

------------------------------------------------------------------------

## 🔄 Flow

``` mermaid
graph TD
A[Scan Files] --> B[LLM Summaries]
B --> C[Hash Check (skip unchanged)]
C --> D[Aggregate Summaries]
D --> E[Generate Prompt]
E --> F[Paste into LLM]
```

------------------------------------------------------------------------

## ⭐ If this helped you, give it a star!
