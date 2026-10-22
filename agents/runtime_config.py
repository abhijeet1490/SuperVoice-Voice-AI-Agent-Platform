# ============================================================
# Runtime config — loaded from config/agent_runtime.json (Studio UI)
# ============================================================

import json
from dataclasses import asdict, fields
from pathlib import Path

from agents.configs.priya_agent import PRIYA_CONFIG, AgentConfig

DEFAULT_RUNTIME_PATH = Path(__file__).resolve().parent.parent / "config" / "agent_runtime.json"


def _config_field_names() -> set[str]:
    return {f.name for f in fields(AgentConfig)}


def _read_runtime_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_tools_config(path: Path | None = None) -> dict:
    """Tools section from agent_runtime.json (standard + customer)."""
    path = path or DEFAULT_RUNTIME_PATH
    data = _read_runtime_json(path)
    tools = data.get("tools", {})
    standard = tools.get("standard", {})
    return {
        "standard": {
            "end_call": standard.get("end_call", True),
            "transfer_to_human": standard.get("transfer_to_human", False),
            "crm_push_lead": standard.get("crm_push_lead", False),
        },
        "customer": tools.get("customer", []),
    }


def load_agent_config(path: Path | None = None) -> AgentConfig:
    """Merge saved JSON overrides onto PRIYA_CONFIG defaults."""
    path = path or DEFAULT_RUNTIME_PATH
    base = asdict(PRIYA_CONFIG)
    data = _read_runtime_json(path)
    if data:
        agent = data.get("agent", data)
        for key, value in agent.items():
            if key in _config_field_names():
                base[key] = value
        tools = load_tools_config(path)
        base["tools_end_call_enabled"] = tools["standard"].get("end_call", True)
    return AgentConfig(**base)


def load_prompt_override(path: Path | None = None) -> str | None:
    path = path or DEFAULT_RUNTIME_PATH
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    prompt = data.get("prompt", {})
    text = prompt.get("system_prompt", "").strip()
    return text or None


def save_runtime(
    agent: dict,
    system_prompt: str | None = None,
    tools: dict | None = None,
    path: Path | None = None,
) -> None:
    path = path or DEFAULT_RUNTIME_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_runtime_json(path)
    payload = {"agent": agent}
    if system_prompt is not None:
        payload["prompt"] = {"system_prompt": system_prompt}
    elif "prompt" in existing:
        payload["prompt"] = existing["prompt"]
    if tools is not None:
        payload["tools"] = tools
    elif "tools" in existing:
        payload["tools"] = existing["tools"]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def agent_config_to_dict(config: AgentConfig) -> dict:
    return asdict(config)
