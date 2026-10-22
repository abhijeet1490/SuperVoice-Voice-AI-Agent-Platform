# ============================================================
# Standard SuperVoice tools (hang-up, transfer, CRM — phased rollout)
# ============================================================

from pipecat.frames.frames import EndTaskFrame, FunctionCallResultProperties
from pipecat.processors.frame_processor import FrameDirection
from pipecat.services.llm_service import FunctionCallParams

from runtime.session import CallSession


async def end_call(params: FunctionCallParams, reason: str) -> None:
    """End the current voice session after saying goodbye to the caller.

    Args:
        reason: Short reason code for analytics (e.g. conversation_complete).
    """
    reason = (reason or "conversation_complete").strip()
    resources = params.app_resources or {}
    session: CallSession | None = resources.get("session")
    if session:
        session.mark_ended(reason)

    print(f"🔚 end_call invoked: {reason}")

    await params.result_callback(
        {"status": "ok", "reason": reason},
        properties=FunctionCallResultProperties(run_llm=False),
    )
    await params.pipeline_worker.queue_frame(
        EndTaskFrame(reason=reason),
        FrameDirection.UPSTREAM,
    )
