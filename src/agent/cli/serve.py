from __future__ import annotations

import os
import sys

from agent.bootstrap import ensure_agent_importable, install_instructions, project_root


def main() -> int:
    try:
        ensure_agent_importable()
    except ModuleNotFoundError:
        print(install_instructions(), file=sys.stderr)
        return 1

    src = project_root() / "src"
    src_str = str(src)
    existing = os.environ.get("PYTHONPATH", "")
    if src_str not in {part for part in existing.split(os.pathsep) if part}:
        os.environ["PYTHONPATH"] = src_str if not existing else f"{src_str}{os.pathsep}{existing}"

    import uvicorn

    from agent.config import settings

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    reload = os.environ.get("RELOAD", "1").strip().lower() not in {"0", "false", "no", "off"}

    if "LLM_MOCK" not in os.environ:
        os.environ["LLM_MOCK"] = "1" if settings.llm_mock else "0"
    if "CHROMA_EPHEMERAL" not in os.environ:
        os.environ["CHROMA_EPHEMERAL"] = "1" if settings.chroma_ephemeral else "0"

    mode = "mock" if settings.llm_mock else "azure"
    print(f"Catalogsmith → http://{host}:{port}/app  ({mode} LLM)")
    uvicorn.run(
        "agent.main:app",
        host=host,
        port=port,
        reload=reload,
        reload_dirs=[src_str],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
