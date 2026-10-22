# ============================================================
# Half-duplex guards for loudspeaker use (no echo → STT / VAD)
# ============================================================

from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    Frame,
    InputAudioRawFrame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from runtime.playback_state import PlaybackState


class InputMuteGate(FrameProcessor):
    """Drop mic audio to STT only during post-playback echo tail (VAD runs upstream)."""

    def __init__(self, playback: PlaybackState, **kwargs):
        super().__init__(**kwargs)
        self._playback = playback

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, InputAudioRawFrame) and self._playback.is_stt_muted():
            return
        await self.push_frame(frame, direction)


class BotPlaybackObserver(FrameProcessor):
    """Track real speaker output so listen gate matches what the user hears."""

    def __init__(self, playback: PlaybackState, on_bot_stopped=None, **kwargs):
        super().__init__(**kwargs)
        self._playback = playback
        self._on_bot_stopped = on_bot_stopped

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, BotStartedSpeakingFrame):
            self._playback.on_bot_started_speaking()
        elif isinstance(frame, BotStoppedSpeakingFrame):
            self._playback.on_bot_stopped_speaking()
            if self._on_bot_stopped:
                self._on_bot_stopped()
        await self.push_frame(frame, direction)


class EchoTranscriptionFilter(FrameProcessor):
    """Drop transcriptions that are clearly the agent's voice echoed from speakers."""

    def __init__(self, playback: PlaybackState, **kwargs):
        super().__init__(**kwargs)
        self._playback = playback

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, TranscriptionFrame) and frame.text:
            from runtime.playback_state import is_likely_echo

            if self._playback.in_echo_tail():
                return
            if is_likely_echo(frame.text, self._playback.last_agent_text):
                print(f"🔇 Echo filtered: {frame.text.strip()}")
                return
        await self.push_frame(frame, direction)
