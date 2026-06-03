# SuperVoice

SuperVoice is a Python voice-agent prototype for handling business calls. The current demo agent is **Priya**, a concise sales assistant for SuperVoice that listens through the local microphone, transcribes speech with Deepgram, sends conversation context to Gemini, speaks replies with Deepgram TTS, and records a call transcript in memory.

The repository is intentionally small and is organized around three concerns:

- `runtime/`: the executable call pipeline and conversation runtime.
- `agents/`: technical agent configuration such as voice, language, model, and provider choices.
- `prompts/`: prompt configuration and persona/behavior instructions.

## Current Status

This project is a local-audio prototype, not a packaged production service yet.

What works in the current code:

- Local microphone input and speaker output through Pipecat.
- Voice activity detection using Silero VAD.
- Speech-to-text through Deepgram.
- LLM responses through Google Gemini.
- Text-to-speech through Deepgram Aura.
- Conversation history stored per call in `CallSession`.
- Full transcript and call metadata printed after the pipeline ends.
- Agent and prompt separated into reusable config modules.

What is not implemented yet:

- No persistent database storage.
- No API server or telephony integration wired into the current runtime.
- No automated lead extraction, although `LeadData` is already modeled.
- No `requirements.txt`, `pyproject.toml`, or lockfile.
- No automated tests.
- The existing `venv/` appears to be machine/path-specific and should be recreated locally.

## Repository Structure

```text
.
├── agents/
│   ├── __init__.py
│   └── configs/
│       ├── __init__.py
│       └── priya_agent.py
├── prompts/
│   └── supervoice_sales_prompt.py
├── runtime/
│   ├── __init__.py
│   ├── bot.py
│   ├── context_bridge.py
│   └── session.py
├── .env
├── .gitignore
└── README.md
```

There are also local artifacts such as `venv/`, `__pycache__/`, `.DS_Store`, and debug logs. These are not part of the application design.

## Architecture

At runtime, `runtime.bot` creates a single call session, builds a Pipecat pipeline, and runs it until the local audio transport stops.

```text
Microphone
  ↓
LocalAudioTransport.input()
  ↓
Silero VAD
  ↓
Deepgram STT
  ↓
STTToLLMBridge
  ↓
Google Gemini LLM
  ↓
LLMFullResponseAggregator
  ↓
ResponseCapture
  ↓
Deepgram TTS
  ↓
LocalAudioTransport.output()
  ↓
Speakers
```

The custom runtime processors are where most of the project-specific behavior lives:

- `STTToLLMBridge` receives transcription frames, stores user messages in the session, waits briefly to avoid cutting the user off, and emits an `LLMContextFrame`.
- `ResponseCapture` collects streamed LLM text chunks, sends them onward to TTS immediately, and saves the completed agent reply back into the session.
- `CallSession` owns call metadata, ordered conversation messages, placeholder lead data, and summary/transcript printing.

## Key Files

### `runtime/bot.py`

This is the application entry point.

It performs the following steps:

1. Loads environment variables from `.env`.
2. Loads `PRIYA_CONFIG` and `SUPERVOICE_SALES_PROMPT`.
3. Creates a `CallSession` with organization ID, agent ID, and a generated call ID.
4. Configures local audio transport.
5. Configures Deepgram STT.
6. Configures Gemini LLM.
7. Configures Deepgram TTS.
8. Builds the Pipecat pipeline.
9. Runs the pipeline with interruptions enabled.
10. Prints the call summary and transcript when the call ends.

The current pipeline uses:

- STT: `DeepgramSTTService`
- LLM: `GoogleLLMService`
- TTS: `DeepgramTTSService`
- VAD: `SileroVADAnalyzer`
- Transport: `LocalAudioTransport`

Run it from the repository root with:

```bash
python -m runtime.bot
```

Using module execution is important because the code imports packages from the repo root, such as `agents.configs.priya_agent` and `runtime.context_bridge`.

### `runtime/context_bridge.py`

This file contains two custom Pipecat frame processors.

#### `STTToLLMBridge`

Responsibilities:

- Converts final STT transcriptions into LLM context.
- Adds user messages to `CallSession`.
- Maintains a short natural delay before asking the LLM to respond.
- Cancels pending responses when the user continues speaking.
- Pushes an `InterruptionFrame` before a new response so queued TTS can be interrupted.
- Builds an `LLMContext` from the full conversation history.

The delay logic is punctuation-aware:

- Text ending in `.`, `?`, or `!`: waits `1.0` second.
- Text ending in `,`: waits `2.5` seconds.
- Other text: waits `1.8` seconds.

This is meant to make the voice agent feel less eager and reduce interruptions.

#### `ResponseCapture`

Responsibilities:

- Accumulates streamed `LLMTextFrame` chunks.
- Pushes text frames onward immediately so TTS can speak as the LLM streams.
- On `LLMFullResponseEndFrame`, saves the completed assistant message into the active session.

### `runtime/session.py`

This module defines the in-memory call state.

#### `Message`

Represents one conversation turn:

- `timestamp`
- `speaker`
- `message`

It also includes `to_llm_format()`, which converts internal messages into Pipecat/Gemini-compatible message dictionaries.

User messages become:

```python
{"role": "user", "content": "..."}
```

Agent messages become:

```python
{"role": "model", "content": "..."}
```

#### `LeadData`

Placeholder structure for extracted lead information:

- `name`
- `phone`
- `email`
- `city`
- `company`
- `team_size`
- `use_case`
- `budget`

The comments indicate lead extraction is planned but not implemented yet.

#### `CallSession`

Tracks one call:

- Organization ID.
- Agent ID.
- Call ID.
- Start timestamp.
- Ordered message history.
- Lead data.

It can:

- Add timestamped messages.
- Convert the full conversation into LLM context.
- Print a readable transcript.
- Print a call summary.

### `agents/configs/priya_agent.py`

Defines technical configuration for the demo agent.

Current `PRIYA_CONFIG`:

```python
agent_id = "agt_priya_001"
agent_name = "Priya"
organization_id = "org_supervoice_demo"
voice = "aura-asteria-en"
language = "en-IN"
model = "gemini-2.5-flash"
prompt_id = "pmt_supervoice_sales_001"
stt_provider = "deepgram"
tts_provider = "deepgram"
llm_provider = "gemini"
```

This module intentionally does not contain prompt text. It points to a prompt through `prompt_id`.

### `prompts/supervoice_sales_prompt.py`

Defines the sales prompt used by Priya.

The prompt config includes:

- `prompt_id`
- `prompt_name`
- `organization_id`
- `first_message`
- `system_prompt`

The system prompt instructs Priya to:

- Act as a friendly and professional SuperVoice assistant.
- Keep responses under two sentences.
- Speak naturally on a phone call.
- Avoid repeating "Hello!" after the first greeting.
- Always respond to short complete answers such as "yes", "no", and "okay".
- Understand the caller's business use case.
- Ask for name and phone number.
- Tell the caller the team will follow up after details are collected.

Note: `first_message` exists in the prompt config, but the current runtime does not automatically speak it at call start.

## Environment Variables

The runtime currently reads these variables:

```env
DEEPGRAM_API_KEY=...
GEMINI_API_KEY=...
```

The checked local `.env` also contains keys for Soniox, Exotel, language, and model settings, but the current `runtime/bot.py` does not use them directly.

Currently used by code:

| Variable | Used For | Required |
| --- | --- | --- |
| `DEEPGRAM_API_KEY` | Deepgram STT and TTS | Yes |
| `GEMINI_API_KEY` | Google Gemini LLM | Yes |

Present but not used by the current runtime:

| Variable | Likely Purpose |
| --- | --- |
| `SONIOX_API_KEY` | Future or previous STT provider |
| `EXOTEL_ACCOUNT_SID` | Future telephony integration |
| `EXOTEL_API_KEY` | Future telephony integration |
| `EXOTEL_API_TOKEN` | Future telephony integration |
| `AGENT_LANGUAGE` | Future configurable language |
| `LLM_MODEL` | Previous runtime model override |

## Setup

### 1. Create a fresh virtual environment

The existing `venv/` is not reliable on another machine because its scripts reference an older absolute path. Recreate it instead:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 2. Install dependencies

There is no dependency manifest yet. Based on the current imports and the local environment metadata, the core packages are:

```bash
pip install pipecat-ai python-dotenv deepgram-sdk google-genai onnxruntime pyaudio
```

Depending on your platform and Pipecat extras, you may prefer to install the provider extras from Pipecat's documentation. The project currently imports Pipecat services for Deepgram, Google, local audio, Silero VAD, pipeline processing, and frame processors.

### 3. Add `.env`

Create or update `.env` with:

```env
DEEPGRAM_API_KEY=your_deepgram_key
GEMINI_API_KEY=your_gemini_key
```

### 4. Run the local voice agent

From the repository root:

```bash
python -m runtime.bot
```

The app will print the selected agent, prompt, call ID, and language, then wait for microphone input.

## Runtime Behavior

### Conversation History

Every user transcription is stored in `CallSession.messages`. Every completed LLM response is stored after `ResponseCapture` receives the end-of-response frame.

Before each LLM call, the session produces a message list like this:

```python
[
    {"role": "user", "content": system_prompt},
    {"role": "model", "content": "Understood."},
    {"role": "user", "content": "Customer message"},
    {"role": "model", "content": "Agent reply"},
]
```

This pattern is used because the code comments target Pipecat 1.3.0 and Gemini-compatible roles.

### Interruption Handling

`PipelineParams(allow_interruptions=True)` enables interruption behavior at the task level.

`STTToLLMBridge` also:

- Cancels a pending delayed LLM response if the user speaks again.
- Pushes an `InterruptionFrame` before sending a new LLM context.

Together, these choices are designed to make the agent more usable in a real conversation where the caller may pause, resume, or interrupt.

### Buffering While the LLM Is Busy

If a user transcription arrives while a response is already pending, the bridge appends it to `_buffered_text`. After the assistant response is saved, stale buffer text is cleared.

This prevents partial speech fragments from being immediately sent to the LLM while another response is in progress. The current behavior favors avoiding noisy context over preserving every overlapping fragment.

### Transcript and Summary

When the pipeline ends, `session.print_summary()` prints:

- Call ID.
- Organization.
- Agent.
- Start time.
- Message count.
- Current `LeadData`.
- Full timestamped transcript.

## Development Notes

### Adding a New Agent

Create a new config module under `agents/configs/`, following the structure in `priya_agent.py`.

Recommended fields:

- `agent_id`
- `agent_name`
- `organization_id`
- `voice`
- `language`
- `model`
- `stt_provider`
- `tts_provider`
- `llm_provider`
- `prompt_id`

Then update `runtime/bot.py` to load the new config.

### Adding a New Prompt

Create a new prompt module under `prompts/`, following `supervoice_sales_prompt.py`.

Keep prompt text separate from agent configuration so multiple agents can reuse prompts or multiple prompts can be tested with the same agent.

### Adding Lead Extraction

`LeadData` already defines the intended shape for structured lead information. A future implementation could add a processor after `ResponseCapture` or a separate extraction pass that updates:

- Name.
- Phone.
- Email.
- City.
- Company.
- Team size.
- Use case.
- Budget.

For production use, lead extraction should be validated and persisted outside of the in-memory session.

### Adding Persistence

`CallSession` currently lives only in memory. A future persistence layer would likely store:

- Call metadata.
- Message transcript.
- Extracted lead fields.
- Agent ID and prompt ID.
- Provider metadata.
- Timestamps and call outcome.

The comments in `runtime/bot.py` indicate that config is expected to come from a database later.

### Adding Telephony

The current transport is `LocalAudioTransport`, so the app runs through local microphone and speakers. The `.env` contains Exotel variables, which suggests a future telephony integration, but there is no active Exotel runtime code in the current repo.

To add phone-call support, replace or supplement the local audio transport with a telephony transport supported by the chosen voice stack, then preserve the same STT -> LLM -> TTS processor chain.

## Git/Refactor Notes

The current working tree appears to be in the middle of a refactor:

- Old top-level files such as `bot.py`, `context_bridge.py`, and `prompts.py` are deleted.
- New package-based files now live under `runtime/`, `agents/`, and `prompts/`.

The new structure is cleaner because configuration, prompt content, session state, and runtime pipeline are separated.

## Troubleshooting

### `ModuleNotFoundError: No module named 'agents'`

Run the app from the repository root using module mode:

```bash
python -m runtime.bot
```

Avoid running `python runtime/bot.py` from another working directory.

### Microphone or speaker errors

Check that:

- Your terminal has microphone permission.
- Your OS input/output devices are available.
- `pyaudio` installed successfully.
- No other process has exclusive access to the microphone.

### Deepgram authentication errors

Verify:

- `DEEPGRAM_API_KEY` exists in `.env`.
- The key is valid.
- The account has access to STT and TTS.

### Gemini authentication or model errors

Verify:

- `GEMINI_API_KEY` exists in `.env`.
- The key is valid.
- The configured model in `PRIYA_CONFIG.model` is available to your account.

### Broken virtual environment

If commands inside `venv/bin/` fail with a path pointing to another user or machine, delete/recreate the environment locally:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Then reinstall dependencies.

## Suggested Next Steps

1. Add a dependency manifest (`requirements.txt` or `pyproject.toml`).
2. Add startup validation for missing `DEEPGRAM_API_KEY` and `GEMINI_API_KEY`.
3. Decide whether `first_message` should be spoken automatically at call start.
4. Add tests for `CallSession`, message formatting, and bridge buffering behavior.
5. Implement lead extraction into `LeadData`.
6. Add persistent storage for calls and transcripts.
7. Wire a telephony transport when moving beyond local audio.
8. Remove committed/runtime artifacts such as caches, logs, and machine-specific virtualenvs.

## License

No license file is currently present in this repository.
