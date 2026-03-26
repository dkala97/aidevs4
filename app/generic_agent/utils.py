from pathlib import Path
from .config import AgentConfig

def resolve_workspace_path(shared_config: AgentConfig, relative_path: str) -> Path:
    candidate = (shared_config.PROJECT_ROOT / "workspace" / relative_path).resolve()
    try:
        candidate.relative_to(shared_config.PROJECT_ROOT / "workspace")
    except ValueError as error:
        raise RuntimeError("image_path must stay inside the project root") from error
    return candidate
