import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass
from dotenv import load_dotenv

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
                {"role": "system", "content": "Você é um engenheiro de software especialista em análise de código."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content

# =========================
# FILE SCAN
# =========================

def scan_files(config: Config) -> List[Path]:
    files = []
    for root, _, filenames in os.walk(config.root_dir):
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
# ETAPA 1 (INTELIGENTE)
# =========================

def generate_summaries(files: List[Path], config: Config, llm: LLMClient):
    for file in files:
        print(f"\n📄 {file}")

        try:
            code = file.read_text(encoding="utf-8")
        except:
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
    for root_dir, _, files in os.walk(root):
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
TAREFAS
====================
1. Arquitetura
2. Problemas
3. Melhorias
4. Refatoração
5. Riscos técnicos
"""

def generate_final_txt(files: List[Path], config: Config):
    tree = build_tree_structure(config.root_dir)
    summaries = collect_summaries(files)

    final_prompt = build_final_prompt(tree, summaries)

    Path(config.output_file).write_text(final_prompt, encoding="utf-8")
    print(f"\n✅ Gerado: {config.output_file}")

# =========================
# MAIN
# =========================

def main():
    config = Config()

    llm = LLMClient(config)
    files = scan_files(config)

    print(f"{len(files)} arquivos encontrados")

    generate_summaries(files, config, llm)
    generate_final_txt(files, config)

if __name__ == "__main__":
    main()