from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = REPO_ROOT / ".env"
EXAMPLE_ENV_PATH = REPO_ROOT / ".env.example"
SEED_DOCS_PATH = REPO_ROOT / "data" / "docs"


def command_available(command: str) -> bool:
    return shutil.which(command) is not None


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def check_command(command: str, pretty_name: str) -> tuple[bool, str]:
    if not command_available(command):
        return False, f"{pretty_name} is not installed."
    try:
        result = subprocess.run([command, "--version"], check=False, capture_output=True, text=True)
        output = (result.stdout or result.stderr).strip().splitlines()
        version_line = output[0] if output else "available"
        return True, f"{pretty_name} available: {version_line}"
    except Exception as exc:
        return False, f"{pretty_name} check failed: {exc}"


def main() -> int:
    env_values = load_env_file(ENV_PATH) or load_env_file(EXAMPLE_ENV_PATH)
    seed_doc_count = len(list(SEED_DOCS_PATH.glob("*.md"))) if SEED_DOCS_PATH.exists() else 0

    checks: list[tuple[str, bool, str, bool]] = [
        ("python3.11", sys.version_info >= (3, 11), f"Running Python {sys.version.split()[0]}", True),
        ("uv", *check_command("uv", "uv"), True),
        ("node", *check_command("node", "Node.js"), True),
        ("npm", *check_command("npm", "npm"), True),
        ("docker", *check_command("docker", "Docker"), False),
        (".env", ENV_PATH.exists(), ".env file present" if ENV_PATH.exists() else "Create `.env` from `.env.example`.", True),
        ("openai_api_key", bool(env_values.get("OPENAI_API_KEY")), "OPENAI_API_KEY configured" if env_values.get("OPENAI_API_KEY") else "OPENAI_API_KEY is missing.", False),
        ("seed_docs", seed_doc_count > 0, f"Found {seed_doc_count} seed docs." if seed_doc_count > 0 else "Seed docs directory is missing or empty.", True),
    ]

    blocking_failures = 0
    print("Enterprise RAG Chatbot preflight\n")
    for name, ok, detail, required in checks:
        status = "OK" if ok else "FAIL" if required else "WARN"
        print(f"[{status}] {name}: {detail}")
        if required and not ok:
            blocking_failures += 1

    print("\nSuggested next steps:")
    print("- make infra-up")
    print("- make backend-install")
    print("- make frontend-install")
    print("- make migrate")
    print("- make seed")
    print("- make backend-dev")
    print("- make frontend-dev")

    return 1 if blocking_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
