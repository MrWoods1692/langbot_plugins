# AutoLearn Plugin

Autonomous learning plugin for LangBot. Learns from real conversations to adapt bot behavior over time.

## Features

- **Conversation Style Learning** — Tracks user expression patterns, common phrases, and sentence length from real chats
- **Group Slang Detection** — Counts high-frequency words in group chats and infers meanings (optional LLM)
- **Social Relationship System** — Records interactions, favorability (0–100), and mood per user
- **Personality Evolution** — Gradually adjusts warmth, humor, formality, empathy, and curiosity traits
- **Memory Graph** — Builds a knowledge/memory network with interactive visualization in WebUI

## Components

| Component | Description |
|-----------|-------------|
| EventListener | Captures messages, responses, and injects learned context into prompts |
| Command `!learn` | View stats, slang, relationships, and trigger slang inference |
| Tool `query_learned_context` | Lets the LLM Agent query learned data during conversations |
| Page `Memory Graph` | Visual dashboard with force-directed graph and personality traits |

## Configuration

| Field | Type | Description |
|-------|------|-------------|
| `llm_model` | llm-model-selector | Optional. Used for slang meaning inference via `!learn infer` |
| `enable_prompt_injection` | boolean | Inject learned context into system prompt (default: true) |

## Commands

```
!learn              — Overview
!learn qfx          — Group analysis chart image (group chat only)
!learn slang        — Top group slang words
!learn relation     — Relationship & favorability for current user
!learn infer        — Infer slang meanings via LLM (requires llm_model config)
!learn graph        — Memory graph statistics
```

## Auto Learning

- Every group message is automatically learned (no command required)
- Per-speaker style, relationship and slang context is injected into LLM prompts
- Use `!learn qfx` in a group to get a visual analysis chart

## Development

```bash
cd AutoLearnPlugin
cp .env.example .env
# Edit DEBUG_RUNTIME_WS_URL to your LangBot Plugin Runtime debug address
python -m langbot_plugin.cli.__init__ run
```

Then enable the plugin in your LangBot pipeline configuration.

## Debug WebSocket

Set in `.env`:

```
DEBUG_RUNTIME_WS_URL=ws://your-host:port/plugin/debug/ws
PLUGIN_DEBUG_KEY=          # if your runtime requires authentication
```
