import os
import json
import hashlib
import ast
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass
from dotenv import load_dotenv
import ast
import json
import streamlit.components.v1 as components
from pathlib import Path

import pyperclip

# =========================
# LOAD ENV
# =========================

load_dotenv()

# =========================
# HASH
# =========================

def compute_file_hash(content: str) -> str:
    return hashlib.md5(content.encode("utf-8")).hexdigest()

# =========================
# CONFIG
# =========================

@dataclass
class Config:
    root_dir: str = "."
    file_extensions: List[str] = None
    output_file: str = "codebase_summary.txt"

    # LLM
    provider: str = os.getenv("LLM_PROVIDER", "openai")
    api_key: str = os.getenv("LLM_API_KEY")
    model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    base_url: str = os.getenv("LLM_BASE_URL")

    max_words: int = int(os.getenv("MAX_WORDS_DESCRIPTION_PER_FILE", 80))

    def __post_init__(self):
        if self.file_extensions is None:
            self.file_extensions = [".py"]

# =========================
# LLM CLIENT
# =========================

class LLMClient:
    def __init__(self, config: Config):
        self.provider = config.provider
        self.api_key = config.api_key
        self.model = config.model
        self.base_url = config.base_url

        if self.provider in ["openai", "deepseek", "openrouter"]:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url if self.base_url else None
            )
        else:
            raise NotImplementedError(f"Provider {self.provider} não suportado")

    def generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Você é um engenheiro de software especialista em análise de código."
                },
                {
                    "role": "user",
                    "content": prompt
                },
            ],
        )
        return response.choices[0].message.content

# =========================
# FILE SCAN
# =========================

def scan_files(config: Config) -> List[Path]:
    files = []

    ignored_dirs = {
        ".git",
        "hooks",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        "node_modules",
        ".streamlit",
    }

    for root, dirs, filenames in os.walk(config.root_dir):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]

        for f in filenames:
            path = Path(root) / f
            if path.suffix in config.file_extensions:
                files.append(path)

    return files

# =========================
# SUMMARY STORAGE
# =========================

def get_summary_file(file: Path) -> Path:
    return file.with_suffix(file.suffix + ".summary.json")

def read_summary(file: Path):
    summary_file = get_summary_file(file)
    if not summary_file.exists():
        return None, None

    data = json.loads(summary_file.read_text(encoding="utf-8"))
    return data.get("summary"), data.get("hash")

def write_summary(file: Path, summary: str, file_hash: str):
    summary_file = get_summary_file(file)

    data = {
        "hash": file_hash,
        "summary": summary
    }

    summary_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

# =========================
# PROMPT
# =========================

def build_summary_prompt(code: str, filename: str, max_words: int) -> str:
    return f"""
Analise o código abaixo e gere um resumo técnico.

REGRAS:
- Máximo de {max_words} palavras
- Seja extremamente conciso

Formato:

Arquivo: {filename}

Resumo:
- propósito em 1 linha

Funções:
- nome(input) -> output: descrição curta

Classes:
- NomeClasse: descrição

Código:
{code[:8000]}
"""



# =========================
# Função para copiar arquivos listados pelo GPT
# =========================

def clean_gpt_list_input(user_input: str) -> str:
    text = user_input.strip()

    # Remove markdown code fence, caso o GPT retorne:
    # ```python
    # [...]
    # ```
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [
            line for line in lines
            if not line.strip().startswith("```")
        ]
        text = "\n".join(lines).strip()

    # Extrai apenas o conteúdo entre [ e ]
    start = text.find("[")
    end = text.rfind("]")

    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    return text


def parse_file_list(user_input: str):
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
    }

    return mapping.get(suffix, "")


def resolve_project_path(raw_path: str, root_dir: str) -> Path:
    path = Path(raw_path)

    if path.is_absolute():
        return path

    return (Path(root_dir) / path).resolve()


def build_files_content(file_paths, root_dir: str) -> str:
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


def render_gpt_file_copy_box(root_dir: str):
    st.markdown("---")
    st.subheader("📥 Colar lista do GPT e copiar arquivos")

    st.caption(
        "Cole aqui a lista de arquivos que o GPT retornou. "
        "Depois gere o conteúdo e copie para enviar novamente ao GPT."
    )

    example = """[
  "models.py",
  "services/conversation_service.py",
  "routes/calendar.py",
  "services/calendar_service.py"
]"""

    files_list_input = st.text_area(
        "Lista de arquivos retornada pelo GPT",
        height=180,
        placeholder=example,
        key="files_list_input",
    )

    col_generate, col_clear = st.columns([1, 1])

    with col_generate:
        generate_files_content = st.button(
            "📦 Gerar conteúdo dos arquivos",
            use_container_width=True,
            type="primary",
            key="generate_files_content_btn",
        )

    with col_clear:
        clear_files_content = st.button(
            "🧹 Limpar arquivos gerados",
            use_container_width=True,
            key="clear_files_content_btn",
        )

    if clear_files_content:
        st.session_state.pop("files_content_to_copy", None)
        st.session_state.pop("parsed_files_to_copy", None)
        st.rerun()

    if generate_files_content:
        file_list = parse_file_list(files_list_input)

        if not file_list:
            st.error('Lista inválida. Use o formato: ["models.py", "services/arquivo.py"]')
        else:
            files_content = build_files_content(file_list, root_dir)

            st.session_state["files_content_to_copy"] = files_content
            st.session_state["parsed_files_to_copy"] = file_list

            st.success(f"✅ {len(file_list)} arquivo(s) processado(s).")

    if "parsed_files_to_copy" in st.session_state:
        st.markdown("#### Arquivos detectados")

        for file in st.session_state["parsed_files_to_copy"]:
            resolved = resolve_project_path(file, root_dir)

            if resolved.exists() and resolved.is_file():
                st.markdown(f"✅ `{file}`")
            elif resolved.exists() and resolved.is_dir():
                st.markdown(f"⚠️ `{file}` — é um diretório")
            else:
                st.markdown(f"❌ `{file}` — não encontrado")

    if "files_content_to_copy" in st.session_state:
        st.markdown("#### 📋 Conteúdo pronto para colar no GPT")

        browser_copy_button(
            st.session_state["files_content_to_copy"],
            "📋 Copiar conteúdo dos arquivos"
        )

        with st.expander("Preview do conteúdo", expanded=False):
            st.code(
                st.session_state["files_content_to_copy"],
                language="markdown"
            )
            
def browser_copy_button(text: str, label: str = "📋 Copy"):
    safe_text = json.dumps(text)

    components.html(
        f"""
        <button
            id="copy-btn"
            style="
                width: 100%;
                background: #2563eb;
                color: white;
                border: none;
                padding: 12px 16px;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 600;
                cursor: pointer;
            "
        >
            {label}
        </button>

        <div
            id="copy-feedback"
            style="
                margin-top: 8px;
                color: #22c55e;
                font-family: sans-serif;
                font-size: 14px;
                display: none;
            "
        >
            ✅ Copiado! Agora cole no GPT.
        </div>

        <script>
            const btn = document.getElementById("copy-btn");
            const feedback = document.getElementById("copy-feedback");
            const content = {safe_text};

            btn.addEventListener("click", async () => {{
                try {{
                    await navigator.clipboard.writeText(content);
                    feedback.style.display = "block";
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
        height=85,
    )
# =========================
# ETAPA 1 (INTELIGENTE)
# =========================

def generate_summaries(files: List[Path], config: Config, llm: LLMClient):
    for file in files:
        print(f"\n📄 {file}")

        try:
            code = file.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            print(f"❌ Erro lendo arquivo: {e}")
            continue

        current_hash = compute_file_hash(code)
        summary, saved_hash = read_summary(file)

        if saved_hash == current_hash:
            print("🟢 Sem mudanças")
            continue

        print("🟡 Gerando resumo...")

        prompt = build_summary_prompt(code, str(file), config.max_words)
        summary = llm.generate(prompt)

        write_summary(file, summary, current_hash)

# =========================
# ETAPA 2
# =========================

def build_tree_structure(root: str) -> str:
    tree = []

    ignored_dirs = {
        ".git",
        "hooks",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        "node_modules",
        ".streamlit",
    }

    for root_dir, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]

        level = root_dir.replace(root, "").count(os.sep)
        indent = "  " * level
        tree.append(f"{indent}{os.path.basename(root_dir)}/")

        for f in files:
            tree.append(f"{indent}  {f}")

    return "\n".join(tree)

def collect_summaries(files: List[Path]) -> Dict[str, str]:
    summaries = {}

    for file in files:
        summary, _ = read_summary(file)
        if summary:
            summaries[str(file)] = summary

    return summaries

def build_final_prompt(tree: str, summaries: Dict[str, str]) -> str:
    summaries_text = "\n\n".join(
        f"{file}:\n{summary}" for file, summary in summaries.items()
    )

    return f"""
Você é um engenheiro de software sênior.

====================
ESTRUTURA
====================
{tree}

====================
RESUMOS
====================
{summaries_text}

====================
CONSIDERE
====================
1. SEJA DIRETO.
2. Se precisar de arquivos, solicite.
3. Retorne apenas lista de arquivos:
Ex: ["models.py","services/..."]
"""

def generate_final_txt(files: List[Path], config: Config):
    tree = build_tree_structure(config.root_dir)
    summaries = collect_summaries(files)

    final_prompt = build_final_prompt(tree, summaries)

    Path(config.output_file).write_text(final_prompt, encoding="utf-8")
    print(f"\n✅ Gerado: {config.output_file}")

    return final_prompt

# =========================
# NOVA ETAPA (COPIAR ARQUIVOS)
# =========================

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

def parse_file_list(user_input: str) -> List[str]:
    try:
        cleaned = clean_gpt_list_input(user_input)
        parsed = ast.literal_eval(cleaned)

        if not isinstance(parsed, list):
            print("❌ O conteúdo não é uma lista")
            return []

        files = []

        for item in parsed:
            if isinstance(item, str) and item.strip():
                files.append(item.strip())

        return files

    except Exception as e:
        print(f"❌ Lista inválida: {e}")
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
    }

    return mapping.get(suffix, "")

def resolve_project_path(raw_path: str, root_dir: str = ".") -> Path:
    path = Path(raw_path)

    if path.is_absolute():
        return path

    return (Path(root_dir) / path).resolve()

def build_files_content(file_paths: List[str], root_dir: str = ".") -> str:
    output = []

    for raw_path in file_paths:
        path = resolve_project_path(raw_path, root_dir)

        print(f"📄 Lendo: {raw_path}")

        if not path.exists():
            output.append(f"### FILE: {raw_path}\n[ERRO: arquivo não encontrado]\n")
            print("❌ Não encontrado")
            continue

        if path.is_dir():
            output.append(f"### FILE: {raw_path}\n[ERRO: caminho é um diretório]\n")
            print("❌ É diretório")
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
            print("✅ OK")

        except Exception as e:
            output.append(f"### FILE: {raw_path}\n[ERRO: {str(e)}]\n")
            print(f"❌ Erro: {e}")

    return "\n\n".join(output)

def interactive_copy_flow():
    print("\n📥 Cole a lista de arquivos gerada pelo GPT:")
    print('Ex: ["models.py","services/..."]\n')

    user_input = input(">>> ")

    file_list = parse_file_list(user_input)

    if not file_list:
        print("⚠️ Nenhum arquivo válido")
        return

    final_text = build_files_content(file_list)

    pyperclip.copy(final_text)

    print("\n📋 Conteúdo copiado para o clipboard!")
    print("🚀 Cole agora no GPT")

# =========================
# STREAMLIT HELPERS
# =========================

def is_running_streamlit() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return False

def browser_copy_button(text: str, label: str = "📋 Copiar para clipboard"):
    import streamlit.components.v1 as components

    safe_text = json.dumps(text)

    components.html(
        f"""
        <div style="margin: 12px 0;">
            <button
                id="copy-btn"
                style="
                    width: 100%;
                    background: linear-gradient(135deg, #2563eb, #1d4ed8);
                    color: white;
                    border: none;
                    padding: 12px 16px;
                    border-radius: 12px;
                    font-size: 15px;
                    font-weight: 600;
                    cursor: pointer;
                    box-shadow: 0 8px 20px rgba(37, 99, 235, 0.25);
                "
            >
                {label}
            </button>

            <div
                id="copy-feedback"
                style="
                    margin-top: 8px;
                    color: #16a34a;
                    font-family: sans-serif;
                    font-size: 14px;
                    display: none;
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
                    btn.innerText = "✅ Copiado!";
                    setTimeout(() => {{
                        btn.innerText = "{label}";
                        feedback.style.display = "none";
                    }}, 1800);
                }} catch (err) {{
                    feedback.style.display = "block";
                    feedback.style.color = "#dc2626";
                    feedback.innerText = "❌ Não foi possível copiar automaticamente. Use o preview abaixo.";
                }}
            }});
        </script>
        """,
        height=90,
    )

def run_streamlit():
    import streamlit as st

    st.set_page_config(
        page_title="Codebase Helper",
        page_icon="🧠",
        layout="wide"
    )

    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 2rem;
                padding-bottom: 3rem;
                max-width: 1100px;
            }

            .soft-card {
                padding: 1.25rem;
                border-radius: 18px;
                border: 1px solid rgba(148, 163, 184, 0.25);
                background: rgba(248, 250, 252, 0.65);
                margin-bottom: 1rem;
            }

            .step-badge {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 26px;
                height: 26px;
                border-radius: 999px;
                background: #2563eb;
                color: white;
                font-size: 13px;
                font-weight: 700;
                margin-right: 8px;
            }

            .muted {
                color: #64748b;
                font-size: 14px;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.title("🧠 Codebase Helper")
    st.caption("Gere o sumário, envie ao GPT, cole a lista de arquivos retornada e copie o conteúdo completo dos arquivos.")

    config = Config()

    with st.sidebar:
        st.header("⚙️ Configurações")

        root_dir = st.text_input(
            "Diretório raiz",
            value=config.root_dir,
            help="Pasta base onde o script vai procurar os arquivos."
        )

        extensions_input = st.text_input(
            "Extensões",
            value=", ".join(config.file_extensions),
            help="Exemplo: .py, .tsx, .js"
        )

        output_file = st.text_input(
            "Arquivo de saída do sumário",
            value=config.output_file
        )

        max_words = st.number_input(
            "Máximo de palavras por resumo",
            min_value=20,
            max_value=300,
            value=config.max_words,
            step=10
        )

        selected_extensions = [
            ext.strip()
            for ext in extensions_input.split(",")
            if ext.strip()
        ]

        config.root_dir = root_dir
        config.file_extensions = selected_extensions
        config.output_file = output_file
        config.max_words = int(max_words)

    tab_summary, tab_copy = st.tabs([
        "1️⃣ Gerar sumário para o GPT",
        "2️⃣ Colar lista e copiar arquivos"
    ])

    with tab_summary:
        st.markdown(
            """
            <div class="soft-card">
                <span class="step-badge">1</span>
                <strong>Gere o sumário da codebase.</strong>
                <div class="muted">
                    Depois copie o conteúdo gerado e envie manualmente ao GPT.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        col1, col2, col3 = st.columns(3)

        files = scan_files(config)

        col1.metric("Arquivos encontrados", len(files))
        col2.metric("Extensões", ", ".join(config.file_extensions))
        col3.metric("Saída", config.output_file)

        generate_col, read_col = st.columns([1, 1])

        with generate_col:
            if st.button("🚀 Gerar / atualizar sumário", use_container_width=True):
                try:
                    with st.spinner("Gerando resumos e arquivo final..."):
                        llm = LLMClient(config)
                        files = scan_files(config)
                        final_prompt = generate_final_txt(files, config)

                        generate_summaries(files, config, llm)
                        final_prompt = generate_final_txt(files, config)

                    st.session_state["final_prompt"] = final_prompt
                    st.success(f"✅ Sumário gerado em: {config.output_file}")

                except Exception as e:
                    st.error(f"❌ Erro ao gerar sumário: {e}")

        with read_col:
            if st.button("📄 Carregar sumário existente", use_container_width=True):
                path = Path(config.output_file)

                if not path.exists():
                    st.warning("Arquivo de sumário ainda não existe.")
                else:
                    st.session_state["final_prompt"] = path.read_text(encoding="utf-8", errors="ignore")
                    st.success("✅ Sumário carregado.")

        if "final_prompt" in st.session_state:
            st.subheader("📋 Sumário para enviar ao GPT")
            browser_copy_button(st.session_state["final_prompt"], "📋 Copiar sumário para enviar ao GPT")

            with st.expander("Ver preview do sumário"):
                st.code(st.session_state["final_prompt"], language="markdown")

    with tab_copy:
        st.markdown(
            """
            <div class="soft-card">
                <span class="step-badge">2</span>
                <strong>Cole a lista de arquivos retornada pelo GPT.</strong>
                <div class="muted">
                    Exemplo: ["models.py", "services/conversation_service.py", "routes/calendar.py"]
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        example = """[
  "models.py",
  "services/conversation_service.py",
  "routes/calendar.py",
  "services/calendar_service.py"
]"""

        user_input = st.text_area(
            "Lista de arquivos",
            height=180,
            placeholder=example,
            help="Cole aqui exatamente a lista que o GPT retornar."
        )

        col_a, col_b = st.columns([1, 1])

        with col_a:
            generate_files = st.button(
                "📦 Gerar conteúdo dos arquivos",
                use_container_width=True,
                type="primary"
            )

        with col_b:
            clear_state = st.button(
                "🧹 Limpar resultado",
                use_container_width=True
            )

        if clear_state:
            st.session_state.pop("files_content", None)
            st.session_state.pop("parsed_files", None)
            st.rerun()

        if generate_files:
            file_list = parse_file_list(user_input)

            if not file_list:
                st.error("❌ Lista inválida. Cole no formato: [\"models.py\", \"services/arquivo.py\"]")
            else:
                with st.spinner("Lendo arquivos..."):
                    result = build_files_content(file_list, config.root_dir)

                st.session_state["files_content"] = result
                st.session_state["parsed_files"] = file_list

                st.success(f"✅ {len(file_list)} arquivo(s) processado(s).")

        if "parsed_files" in st.session_state:
            st.subheader("Arquivos detectados")

            for file in st.session_state["parsed_files"]:
                resolved = resolve_project_path(file, config.root_dir)

                if resolved.exists() and resolved.is_file():
                    st.markdown(f"✅ `{file}`")
                elif resolved.exists() and resolved.is_dir():
                    st.markdown(f"⚠️ `{file}` — é um diretório")
                else:
                    st.markdown(f"❌ `{file}` — não encontrado")

        if "files_content" in st.session_state:
            st.subheader("📋 Conteúdo pronto para colar no GPT")

            browser_copy_button(
                st.session_state["files_content"],
                "📋 Copiar conteúdo dos arquivos"
            )

            with st.expander("Ver preview do conteúdo copiado", expanded=True):
                st.code(st.session_state["files_content"], language="markdown")

# =========================
# MAIN CLI
# =========================

def main():
    config = Config()

    llm = LLMClient(config)
    files = scan_files(config)

    print(f"{len(files)} arquivos encontrados")

    generate_summaries(files, config, llm)
    generate_final_txt(files, config)

    # NOVO: etapa interativa
    interactive_copy_flow()

# =========================
# ENTRYPOINT
# =========================

if __name__ == "__main__":
    if is_running_streamlit():
        run_streamlit()
    else:
        main()