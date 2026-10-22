# ============================================================
# Tool schemas exposed to the LLM (Gemini via Pipecat)
# ============================================================

from pipecat.adapters.schemas.function_schema import FunctionSchema

END_CALL_TOOL = FunctionSchema(
    name="end_call",
    description=(
        "End the current voice call or local test session. "
        "Only call this after you have spoken a brief goodbye to the caller."
    ),
    properties={
        "reason": {
            "type": "string",
            "description": (
                "Short reason code, e.g. conversation_complete, "
                "customer_not_interested, callback_scheduled, wrong_number."
            ),
        },
    },
    required=["reason"],
)

# Reserved for upcoming standard tools (transfer, CRM).
TRANSFER_TO_HUMAN_TOOL = FunctionSchema(
    name="transfer_to_human",
    description="Transfer the caller to a live human agent (not yet wired in local demo).",
    properties={
        "department": {
            "type": "string",
            "description": "Team or queue name, e.g. sales, support.",
        },
        "summary": {
            "type": "string",
            "description": "One-line summary for the human agent.",
        },
    },
    required=["summary"],
)

CRM_PUSH_LEAD_TOOL = FunctionSchema(
    name="crm_push_lead",
    description="Push lead fields and call notes to CRM (not yet wired in local demo).",
    properties={
        "name": {"type": "string", "description": "Lead full name if known."},
        "phone": {"type": "string", "description": "Phone number if known."},
        "email": {"type": "string", "description": "Email if known."},
        "notes": {"type": "string", "description": "Structured notes from the conversation."},
    },
    required=["notes"],
)
