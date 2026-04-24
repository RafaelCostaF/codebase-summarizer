import os
import ast
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from script import *


# =========================
# PAGE CONFIG
# =========================

st.set_page_config(
    page_title="Codebase Summarizer",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================
# STYLE
# =========================

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1400px;
        }

        .app-title {
            font-size: 2.4rem;
            font-weight: 800;
            letter-spacing: -0.04em;
            margin-bottom: 0.2rem;
        }

        .app-subtitle {
            color: #94a3b8;
            font-size: 1rem;
            margin-bottom: 1.5rem;
        }

        .ux-card {
            border: 1px solid rgba(148, 163, 184, 0.25);
            background: rgba(15, 23, 42, 0.18);
            border-radius: 18px;
            padding: 1.1rem 1.2rem;
            margin-bottom: 1rem;
        }

        .step-title {
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }

        .step-desc {
            color: #94a3b8;
            font-size: 0.9rem;
            margin-bottom: 0.2rem;
        }

        .status-ok {
            color: #22c55e;
            font-weight: 700;
        }

        .status-warn {
            color: #eab308;
            font-weight: 700;
        }

        .status-empty {
            color: #94a3b8;
            font-weight: 700;
        }

        .small-muted {
            color: #94a3b8;
            font-size: 0.85rem;
        }

        .file-row {
            padding: 0.45rem 0.55rem;
            border-radius: 10px;
            margin-bottom: 0.25rem;
            background: rgba(148, 163, 184, 0.06);
            font-family: monospace;
            font-size: 0.85rem;
            word-break: break-all;
        }

        div[data-testid="stTextArea"] textarea {
            border-radius: 14px;
        }

        div[data-testid="stButton"] button {
            border-radius: 12px;
            font-weight: 650;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# CONSTANTS
# =========================

IGNORED_DIRS = {
    ".git",
    "objects",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "env",
    ".mypy_cache",
    ".pytest_cache",
    ".streamlit",
}

IGNORED_FILES = {
    "COMMIT_EDITMSG",
    "FETCH_HEAD",
    ".DS_Store",
}


# =========================
# HELPERS
# =========================

def normalize_extensions(raw: str):
    extensions = []

    for item in raw.split(","):
        ext = item.strip()

        if not ext:
            continue

        if not ext.startswith("."):
            ext = f".{ext}"

        extensions.append(ext)

    return extensions or [".py"]


def apply_filters(files):
    filtered = []

    for f in files:
        path_parts = set(f.parts)

        if path_parts & IGNORED_DIRS:
            continue

        if f.name in IGNORED_FILES:
            continue

        filtered.append(f)

    return sorted(filtered, key=lambda p: str(p).lower())


def safe_relative_path(path: Path, base_dir: str) -> str:
    try:
        return str(path.resolve().relative_to(Path(base_dir).resolve()))
    except Exception:
        return str(path)


def filter_tree_text(tree: str) -> str:
    """
    O build_tree_structure do script.py retorna string.
    Então o filtro precisa trabalhar em texto, não em dict.
    """
    lines = []

    for line in tree.splitlines():
        clean = line.strip().rstrip("/")

        if clean in IGNORED_DIRS:
            continue

        if clean in IGNORED_FILES:
            continue

        if any(part in IGNORED_DIRS for part in Path(clean).parts):
            continue

        lines.append(line)

    return "\n".join(lines)


def clean_gpt_list_input(user_input: str) -> str:
    text = user_input.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        lines = [
            line for line in lines
            if not line.strip().startswith("```")
        ]
        text = "\n".join(lines).strip()

    start = text.find("[")
    end = text.rfind("]")

    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    return text


def parse_file_list_from_gpt(user_input: str):
    try:
        cleaned = clean_gpt_list_input(user_input)
        parsed = ast.literal_eval(cleaned)

        if not isinstance(parsed, list):
            return []

        return [
            item.strip()
            for item in parsed
            if isinstance(item, str) and item.strip()
        ]

    except Exception:
        return []


def detect_code_language(path: str) -> str:
    suffix = Path(path).suffix.lower()

    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "jsx",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".html": "html",
        ".css": "css",
        ".json": "json",
        ".md": "markdown",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".sql": "sql",
        ".env": "bash",
        ".toml": "toml",
        ".ini": "ini",
        ".sh": "bash",
    }

    return mapping.get(suffix, "")


def resolve_project_path(raw_path: str, root_dir: str) -> Path:
    path = Path(raw_path)

    if path.is_absolute():
        return path

    return (Path(root_dir) / path).resolve()


def build_selected_files_content(file_paths, root_dir: str) -> str:
    output = []

    for raw_path in file_paths:
        path = resolve_project_path(raw_path, root_dir)

        if not path.exists():
            output.append(
                f"### FILE: {raw_path}\n"
                f"[ERRO: arquivo não encontrado]\n"
            )
            continue

        if path.is_dir():
            output.append(
                f"### FILE: {raw_path}\n"
                f"[ERRO: caminho é um diretório]\n"
            )
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            language = detect_code_language(raw_path)

            formatted = (
                f"### FILE: {raw_path}\n"
                f"```{language}\n"
                f"{content.strip()}\n"
                f"```\n"
            )

            output.append(formatted)

        except Exception as e:
            output.append(
                f"### FILE: {raw_path}\n"
                f"[ERRO: {str(e)}]\n"
            )

    return "\n\n".join(output)


def browser_copy_button(text: str, label: str = "📋 Copiar"):
    safe_text = json.dumps(text)

    components.html(
        f"""
        <div style="width:100%; margin: 0.25rem 0 1rem 0;">
            <button
                id="copy-btn"
                style="
                    width: 100%;
                    background: linear-gradient(135deg, #2563eb, #1d4ed8);
                    color: white;
                    border: none;
                    padding: 13px 18px;
                    border-radius: 14px;
                    font-size: 15px;
                    font-weight: 700;
                    cursor: pointer;
                    box-shadow: 0 10px 26px rgba(37, 99, 235, 0.25);
                "
            >
                {label}
            </button>

            <div
                id="copy-feedback"
                style="
                    margin-top: 10px;
                    color: #22c55e;
                    font-family: sans-serif;
                    font-size: 14px;
                    display: none;
                    text-align: center;
                "
            >
                ✅ Copiado! Agora cole no GPT.
            </div>
        </div>

        <script>
            const btn = document.getElementById("copy-btn");
            const feedback = document.getElementById("copy-feedback");
            const content = {safe_text};

            btn.addEventListener("click", async () => {{
                try {{
                    await navigator.clipboard.writeText(content);
                    feedback.style.display = "block";
                    feedback.style.color = "#22c55e";
                    feedback.innerText = "✅ Copiado! Agora cole no GPT.";
                    btn.innerText = "✅ Copiado!";

                    setTimeout(() => {{
                        btn.innerText = "{label}";
                        feedback.style.display = "none";
                    }}, 1800);
                }} catch (err) {{
                    feedback.style.display = "block";
                    feedback.style.color = "#ef4444";
                    feedback.innerText = "❌ Não foi possível copiar automaticamente. Use o preview abaixo.";
                }}
            }});
        </script>
        """,
        height=95,
    )


def get_file_status(file: Path):
    try:
        code = file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return "error"

    current_hash = compute_file_hash(code)
    summary, saved_hash = read_summary(file)

    if summary is None:
        return "empty"

    if saved_hash != current_hash:
        return "changed"

    return "ok"


def render_file_status(status: str):
    if status == "ok":
        return "🟢"
    if status == "changed":
        return "🟡"
    if status == "error":
        return "🔴"
    return "⚪"


def build_config(provider, api_key, model, base_url, max_words, extensions):
    return Config(
        root_dir=st.session_state.base_dir,
        file_extensions=extensions,
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url if base_url else None,
        max_words=int(max_words),
    )


# =========================
# STATE INIT
# =========================

if "base_dir" not in st.session_state:
    st.session_state.base_dir = "."

if "prompt" not in st.session_state:
    st.session_state.prompt = ""

if "files_content_to_copy" not in st.session_state:
    st.session_state.files_content_to_copy = ""

if "parsed_files_to_copy" not in st.session_state:
    st.session_state.parsed_files_to_copy = []


# =========================
# SIDEBAR CONFIG
# =========================

st.sidebar.header("⚙️ Configuração")

provider = st.sidebar.text_input(
    "Provider",
    os.getenv("LLM_PROVIDER", "openai"),
)

api_key = st.sidebar.text_input(
    "API Key",
    os.getenv("LLM_API_KEY", ""),
    type="password",
)

model = st.sidebar.text_input(
    "Model",
    os.getenv("LLM_MODEL", "gpt-4o-mini"),
)

base_url = st.sidebar.text_input(
    "Base URL",
    os.getenv("LLM_BASE_URL", ""),
)

max_words = st.sidebar.number_input(
    "Máximo de palavras por arquivo",
    min_value=20,
    max_value=500,
    value=80,
    step=10,
)

extensions_input = st.sidebar.text_input(
    "Tipos de arquivo",
    ".py",
    help="Separe por vírgula. Exemplo: .py,.js,.ts,.tsx",
)

extensions = normalize_extensions(extensions_input)

st.sidebar.markdown("---")
st.sidebar.caption("Status dos arquivos")
st.sidebar.markdown("🟢 Resumo atualizado")
st.sidebar.markdown("🟡 Arquivo mudou")
st.sidebar.markdown("⚪ Sem resumo")
st.sidebar.markdown("🔴 Erro ao ler")


# =========================
# HEADER
# =========================

st.markdown('<div class="app-title">🧠 Codebase Summarizer</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-subtitle">Fluxo guiado: gerar contexto → enviar ao GPT → colar lista → copiar arquivos.</div>',
    unsafe_allow_html=True,
)


# =========================
# PROJECT BAR
# =========================

project_card, metrics_card = st.columns([2.2, 1])

with project_card:
    st.markdown(
        """
        <div class="ux-card">
            <div class="step-title">📂 Projeto</div>
            <div class="step-desc">Escolha a pasta raiz da aplicação que será analisada.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    home = os.path.expanduser("~")

    with st.expander("Exemplos rápidos de caminho", expanded=False):
        st.code(f"{home}/projects/my-repo\n{home}/Desktop\n.", language="bash")

    new_path = st.text_input(
        "Caminho do projeto",
        value=st.session_state.base_dir,
        placeholder=f"{home}/projects/my-repo",
        label_visibility="collapsed",
    )

    col_set, col_current = st.columns([0.35, 1])

    with col_set:
        if st.button("Definir pasta", use_container_width=True):
            if os.path.exists(new_path):
                st.session_state.base_dir = new_path
                st.success("Pasta definida.")
                st.rerun()
            else:
                st.error("Caminho inválido.")

    with col_current:
        st.caption(f"📁 Atual: `{st.session_state.base_dir}`")


# =========================
# LOAD FILES
# =========================

folder_is_valid = os.path.exists(st.session_state.base_dir)

files = []

if folder_is_valid:
    config_preview = Config(
        root_dir=st.session_state.base_dir,
        file_extensions=extensions,
    )

    files = apply_filters(scan_files(config_preview))

with metrics_card:
    st.markdown(
        """
        <div class="ux-card">
            <div class="step-title">📊 Visão geral</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.metric("Arquivos", len(files))
    st.metric("Extensões", ", ".join(extensions))
    st.metric("Pasta válida", "Sim" if folder_is_valid else "Não")


if not folder_is_valid:
    st.warning("Defina uma pasta válida para continuar.")
    st.stop()


# =========================
# MAIN TABS
# =========================

tab_files, tab_prompt, tab_gpt_copy = st.tabs(
    [
        "📄 Arquivos",
        "🧠 Gerar prompt",
        "📥 Colar lista do GPT",
    ]
)


# =========================
# TAB FILES
# =========================

with tab_files:
    st.markdown(
        """
        <div class="ux-card">
            <div class="step-title">📄 Arquivos encontrados</div>
            <div class="step-desc">Veja o que será considerado no resumo da codebase.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    search = st.text_input(
        "Buscar arquivo",
        placeholder="Ex: calendar_service.py, routes/, models...",
    )

    visible_files = files

    if search.strip():
        visible_files = [
            f for f in files
            if search.lower().strip() in safe_relative_path(f, st.session_state.base_dir).lower()
        ]

    st.caption(f"Mostrando {len(visible_files)} de {len(files)} arquivo(s).")

    if not visible_files:
        st.info("Nenhum arquivo encontrado com esse filtro.")
    else:
        max_to_show = st.slider(
            "Quantidade exibida",
            min_value=10,
            max_value=max(10, min(len(visible_files), 300)),
            value=min(80, max(10, len(visible_files))),
            step=10,
        )

        for f in visible_files[:max_to_show]:
            status = get_file_status(f)
            icon = render_file_status(status)
            rel = safe_relative_path(f, st.session_state.base_dir)
            st.markdown(
                f'<div class="file-row">{icon} {rel}</div>',
                unsafe_allow_html=True,
            )

        if len(visible_files) > max_to_show:
            st.caption(f"+ {len(visible_files) - max_to_show} arquivo(s) ocultos.")


# =========================
# TAB PROMPT
# =========================

with tab_prompt:
    st.markdown(
        """
        <div class="ux-card">
            <div class="step-title">1️⃣ Gerar contexto para o GPT</div>
            <div class="step-desc">
                Primeiro atualize os resumos. Depois gere o prompt e copie para enviar ao GPT manualmente.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_action_1, col_action_2 = st.columns(2)

    with col_action_1:
        if st.button("♻️ Gerar / atualizar resumos", use_container_width=True, type="primary"):
            try:
                config = build_config(
                    provider=provider,
                    api_key=api_key,
                    model=model,
                    base_url=base_url,
                    max_words=max_words,
                    extensions=extensions,
                )

                llm = LLMClient(config)

                with st.spinner("Analisando arquivos e atualizando resumos..."):
                    current_files = apply_filters(scan_files(config))
                    generate_summaries(current_files, config, llm)

                st.success("Resumos atualizados.")
            except Exception as e:
                st.error(f"Erro ao gerar resumos: {e}")

    with col_action_2:
        if st.button("📄 Gerar prompt final", use_container_width=True):
            try:
                config = Config(
                    root_dir=st.session_state.base_dir,
                    file_extensions=extensions,
                )

                current_files = apply_filters(scan_files(config))

                tree = build_tree_structure(config.root_dir)
                tree = filter_tree_text(tree)

                summaries = collect_summaries(current_files)

                st.session_state.prompt = build_final_prompt(tree, summaries)

                st.success("Prompt gerado.")
            except Exception as e:
                st.error(f"Erro ao gerar prompt: {e}")

    st.markdown("### 📋 Prompt gerado")

    prompt = st.text_area(
        "Prompt para enviar ao GPT",
        value=st.session_state.prompt,
        height=420,
        placeholder="Clique em “Gerar prompt final” para preencher esta área.",
        label_visibility="collapsed",
    )

    st.session_state.prompt = prompt

    col_copy_prompt, col_clear_prompt = st.columns([1, 1])

    with col_copy_prompt:
        if st.session_state.prompt.strip():
            browser_copy_button(
                st.session_state.prompt,
                "📋 Copiar prompt para enviar ao GPT",
            )
        else:
            st.button(
                "📋 Copiar prompt para enviar ao GPT",
                use_container_width=True,
                disabled=True,
            )

    with col_clear_prompt:
        if st.button("🧹 Limpar prompt", use_container_width=True):
            st.session_state.prompt = ""
            st.rerun()

    with st.expander("Preview em bloco de código", expanded=False):
        st.code(st.session_state.prompt, language="markdown")


# =========================
# TAB GPT COPY
# =========================

with tab_gpt_copy:
    st.markdown(
        """
        <div class="ux-card">
            <div class="step-title">2️⃣ Colar lista do GPT e copiar arquivos</div>
            <div class="step-desc">
                Cole a lista de arquivos que o GPT pediu. O app lê os arquivos da pasta do projeto e monta um único bloco pronto para colar de volta no GPT.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    example = """[
  "models.py",
  "services/conversation_service.py",
  "routes/calendar.py",
  "services/calendar_service.py"
]"""

    files_list_input = st.text_area(
        "Lista de arquivos retornada pelo GPT",
        height=210,
        placeholder=example,
        help='Aceita lista Python/JSON. Ex: ["models.py", "services/arquivo.py"]',
    )

    col_generate_files, col_clear_files = st.columns([1, 1])

    with col_generate_files:
        generate_files_content = st.button(
            "📦 Gerar conteúdo dos arquivos",
            use_container_width=True,
            type="primary",
        )

    with col_clear_files:
        clear_files_content = st.button(
            "🧹 Limpar conteúdo gerado",
            use_container_width=True,
        )

    if clear_files_content:
        st.session_state.files_content_to_copy = ""
        st.session_state.parsed_files_to_copy = []
        st.rerun()

    if generate_files_content:
        file_list = parse_file_list_from_gpt(files_list_input)

        if not file_list:
            st.error('Lista inválida. Use o formato: ["models.py", "services/arquivo.py"]')
        else:
            with st.spinner("Lendo arquivos solicitados..."):
                files_content = build_selected_files_content(
                    file_list,
                    st.session_state.base_dir,
                )

            st.session_state.files_content_to_copy = files_content
            st.session_state.parsed_files_to_copy = file_list

            st.success(f"{len(file_list)} arquivo(s) processado(s).")

    if st.session_state.parsed_files_to_copy:
        st.markdown("### Arquivos detectados")

        ok_count = 0
        missing_count = 0

        for file in st.session_state.parsed_files_to_copy:
            resolved = resolve_project_path(file, st.session_state.base_dir)

            if resolved.exists() and resolved.is_file():
                ok_count += 1
            else:
                missing_count += 1

        col_ok, col_missing = st.columns(2)
        col_ok.metric("Encontrados", ok_count)
        col_missing.metric("Com problema", missing_count)

        with st.expander("Ver validação dos arquivos", expanded=True):
            for file in st.session_state.parsed_files_to_copy:
                resolved = resolve_project_path(file, st.session_state.base_dir)

                if resolved.exists() and resolved.is_file():
                    st.markdown(f"✅ `{file}`")
                elif resolved.exists() and resolved.is_dir():
                    st.markdown(f"⚠️ `{file}` — é um diretório")
                else:
                    st.markdown(f"❌ `{file}` — não encontrado")

    if st.session_state.files_content_to_copy:
        st.markdown("### 📋 Conteúdo pronto para colar no GPT")

        browser_copy_button(
            st.session_state.files_content_to_copy,
            "📋 Copiar conteúdo dos arquivos",
        )

        st.download_button(
            "⬇️ Baixar conteúdo como TXT",
            data=st.session_state.files_content_to_copy,
            file_name="arquivos_para_gpt.txt",
            mime="text/plain",
            use_container_width=True,
        )

        with st.expander("Preview do conteúdo", expanded=False):
            st.code(
                st.session_state.files_content_to_copy,
                language="markdown",
            )