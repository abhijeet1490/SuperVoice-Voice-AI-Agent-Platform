# ============================================================
# Register tools on the LLM and build ToolsSchema for context
# ============================================================

from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.google.llm import GoogleLLMService

from agents.configs.priya_agent import AgentConfig
from runtime.tools.schemas import END_CALL_TOOL
from runtime.tools.standard import end_call


def build_tools_schema(config: AgentConfig) -> ToolsSchema | None:
    """Return tools advertised to the LLM for this agent config."""
    standard = []
    if getattr(config, "tools_end_call_enabled", True):
        standard.append(END_CALL_TOOL)
    if not standard:
        return None
    return ToolsSchema(standard_tools=standard)


def register_standard_tools(llm: GoogleLLMService, config: AgentConfig) -> None:
    """Attach handlers for enabled standard tools."""
    if getattr(config, "tools_end_call_enabled", True):
        llm.register_direct_function(
            end_call,
            cancel_on_interruption=False,
        )


def tools_system_prompt_suffix(config: AgentConfig) -> str:
    """Extra system instructions so the model knows when to use tools."""
    lines = []
    if getattr(config, "tools_end_call_enabled", True):
        lines.append(
            "- When the conversation is finished, say a short goodbye, then call the "
            "`end_call` tool with a clear `reason`."
        )
    if not lines:
        return ""
    return "\n\n## Tools\n" + "\n".join(lines)
