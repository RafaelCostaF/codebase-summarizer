import streamlit as st
import os

from script import *

st.set_page_config(layout="wide")

st.title("🧠 Codebase Summarizer")

# =========================
# SIDEBAR
# =========================

st.sidebar.header("⚙️ Config")

provider = st.sidebar.text_input("Provider", os.getenv("LLM_PROVIDER", "openai"))
api_key = st.sidebar.text_input("API Key", os.getenv("LLM_API_KEY", ""), type="password")
model = st.sidebar.text_input("Model", os.getenv("LLM_MODEL", "gpt-4o-mini"))
base_url = st.sidebar.text_input("Base URL", os.getenv("LLM_BASE_URL", ""))

max_words = st.sidebar.number_input("Max words", value=80)

extensions = st.sidebar.text_input("Extensões (.py,.js)", ".py")
extensions = [e.strip() for e in extensions.split(",")]

# =========================
# MAIN LAYOUT
# =========================

col_left, col_main = st.columns([1, 3])

# =========================
# LEFT PANEL
# =========================

with col_left:
    st.subheader("📂 Arquivos")

    base_dir = st.text_input("Pasta base", ".")

    if base_dir:
        config = Config(root_dir=base_dir, file_extensions=extensions)
        files = scan_files(config)

        for f in files:
            try:
                code = f.read_text(encoding="utf-8")
            except:
                continue

            current_hash = compute_file_hash(code)
            summary, saved_hash = read_summary(f)

            if summary is None:
                status = "⚪"
            elif saved_hash != current_hash:
                status = "🟡"
            else:
                status = "🟢"

            st.text(f"{status} {f}")

# =========================
# MAIN PANEL
# =========================

with col_main:
    st.subheader("🚀 Ações")

    if st.button("♻️ Gerar / Atualizar comentários"):
        config = Config(
            root_dir=base_dir,
            file_extensions=extensions,
            provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
            max_words=max_words
        )

        llm = LLMClient(config)
        files = scan_files(config)

        generate_summaries(files, config, llm)
        st.success("Comentários atualizados!")

    if st.button("📄 Gerar prompt"):
        config = Config(root_dir=base_dir, file_extensions=extensions)
        files = scan_files(config)

        tree = build_tree_structure(config.root_dir)
        summaries = collect_summaries(files)

        prompt = build_final_prompt(tree, summaries)

        st.session_state["prompt"] = prompt

    st.subheader("📋 Prompt")

    prompt = st.text_area(
        "Preview",
        value=st.session_state.get("prompt", ""),
        height=400
    )

    if st.button("📋 Copiar"):
        st.code(prompt)