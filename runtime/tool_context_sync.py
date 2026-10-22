# ============================================================
# Keep LLM tool-call context in sync without blocking TTS audio.
# LLMAssistantAggregator must not sit in front of TTS — it consumes
# LLMTextFrame / LLMFullResponseEndFrame instead of forwarding them.
# ============================================================

import json

from pipecat.frames.frames import (
    Frame,
    FunctionCallInProgressFrame,
    FunctionCallResultFrame,
    LLMContextFrame,
)
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


class ToolContextSync(FrameProcessor):
    """Update shared LLMContext on tool calls; re-run LLM when needed."""

    def __init__(self, context: LLMContext, **kwargs):
        super().__init__(**kwargs)
        self._context = context

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, FunctionCallInProgressFrame):
            # Context is updated by the LLM service; do not duplicate tool_call rows.
            return

        if isinstance(frame, FunctionCallResultFrame):
            if frame.function_name == "end_call":
                return

            self._context.add_message(
                {
                    "role": "tool",
                    "tool_call_id": frame.tool_call_id,
                    "content": json.dumps(frame.result, ensure_ascii=False)
                    if not isinstance(frame.result, str)
                    else frame.result,
                }
            )
            run_llm = frame.run_llm if frame.run_llm is not None else True
            if run_llm:
                await self.push_frame(
                    LLMContextFrame(context=self._context),
                    FrameDirection.UPSTREAM,
                )
            return

        await self.push_frame(frame, direction)
