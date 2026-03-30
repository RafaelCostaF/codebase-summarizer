import streamlit as st
import os

from script import *

st.set_page_config(layout="wide")

st.title("🧠 Codebase Summarizer")

# =========================
# SIDEBAR (CONFIG)
# =========================

st.sidebar.header("⚙️ Configuration")

provider = st.sidebar.text_input("Provider", os.getenv("LLM_PROVIDER", "openai"))
api_key = st.sidebar.text_input("API Key", os.getenv("LLM_API_KEY", ""), type="password")
model = st.sidebar.text_input("Model", os.getenv("LLM_MODEL", "gpt-4o-mini"))
base_url = st.sidebar.text_input("Base URL", os.getenv("LLM_BASE_URL", ""))

max_words = st.sidebar.number_input("Max words per file", value=80)

extensions_input = st.sidebar.text_input("File types (.py,.js)", ".py")
extensions = [e.strip() for e in extensions_input.split(",")]

# =========================
# STATE INIT
# =========================

if "base_dir" not in st.session_state:
    st.session_state.base_dir = "."

if "prompt" not in st.session_state:
    st.session_state.prompt = ""

# =========================
# LAYOUT
# =========================

col_left, col_main = st.columns([1, 3])

# =========================
# LEFT PANEL
# =========================

with col_left:
    st.subheader("📂 Project")

    # Suggestion
    home = os.path.expanduser("~")
    st.markdown("**Quick examples:**")
    st.code(f"{home}/projects/my-repo\n{home}/Desktop\n.")

    # Input
    new_path = st.text_input(
        "Project path",
        st.session_state.base_dir
    )

    # Set folder button
    if st.button("Set Folder"):
        if os.path.exists(new_path):
            st.session_state.base_dir = new_path
            st.success("Folder set successfully")
        else:
            st.error("Invalid path")

    st.caption(f"📁 Current: {st.session_state.base_dir}")

    # =========================
    # FILE LIST
    # =========================

    if not os.path.exists(st.session_state.base_dir):
        st.warning("Invalid folder path")
    else:
        config = Config(
            root_dir=st.session_state.base_dir,
            file_extensions=extensions
        )

        files = scan_files(config)

        st.subheader("📄 Files")

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
    st.subheader("🚀 Actions")

    col_btn1, col_btn2 = st.columns(2)

    # Generate summaries
    with col_btn1:
        if st.button("♻️ Generate / Update Summaries", use_container_width=True):
            if not os.path.exists(st.session_state.base_dir):
                st.error("Invalid folder")
            else:
                config = Config(
                    root_dir=st.session_state.base_dir,
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
                st.success("Summaries updated!")

    # Generate prompt
    with col_btn2:
        if st.button("📄 Generate Prompt", use_container_width=True):
            if not os.path.exists(st.session_state.base_dir):
                st.error("Invalid folder")
            else:
                config = Config(
                    root_dir=st.session_state.base_dir,
                    file_extensions=extensions
                )

                files = scan_files(config)

                tree = build_tree_structure(config.root_dir)
                summaries = collect_summaries(files)

                st.session_state.prompt = build_final_prompt(tree, summaries)

    # =========================
    # PROMPT SECTION
    # =========================

    st.subheader("📋 Prompt")

    prompt = st.text_area(
        "Generated prompt",
        value=st.session_state.prompt,
        height=400
    )

    col_copy, col_clear = st.columns(2)

    with col_copy:
        if st.button("📋 Show for Copy", use_container_width=True):
            st.code(prompt)

    with col_clear:
        if st.button("🧹 Clear", use_container_width=True):
            st.session_state.prompt = ""
            st.rerun()