from __future__ import annotations

from langbot_plugin.api.definition.components.common.event_listener import EventListener
from langbot_plugin.api.entities import events, context
from langbot_plugin.api.entities.builtin.platform import message as platform_message

from core.tts import text_to_speech, format_voice_result


def _extract_text(message_chain: platform_message.MessageChain | None) -> str:
    """Extract plain text from a message chain."""
    if not message_chain:
        return ""
    parts: list[str] = []
    for component in message_chain:
        if isinstance(component, platform_message.Plain) and component.text:
            parts.append(component.text)
    return "".join(parts).strip()


class DefaultEventListener(EventListener):

    async def initialize(self):
        await super().initialize()

        @self.handler(events.NormalMessageResponded)
        async def on_responded(event_context: context.EventContext):
            """Intercept LLM responses and convert to speech."""
            event = event_context.event
            config = self.plugin.get_config()

            # Check if auto voice is enabled
            if not config.get("auto_voice", True):
                return

            response_text = event.response_text
            if not response_text:
                return

            # Check text length limit
            max_length = int(config.get("max_text_length", 500))
            if len(response_text) > max_length:
                print(
                    f"[VoiceOutput] Text too long ({len(response_text)} chars, max {max_length}), skipping TTS",
                    flush=True,
                )
                return

            # Get API token
            token = config.get("api_token", "")
            if not token:
                print("[VoiceOutput] API token not configured, skipping TTS", flush=True)
                return

            print(
                f"[VoiceOutput] Converting to speech: {response_text[:80]}...",
                flush=True,
            )

            try:
                result = await text_to_speech(token, response_text)
                voice_url = result.get("data", {}).get("voice", "")

                if voice_url:
                    # Send voice message using the Voice component
                    chain = platform_message.MessageChain([
                        platform_message.Voice(url=voice_url),
                    ])
                    await event_context.reply(chain)
                    event_context.prevent_default()
                    print(f"[VoiceOutput] Voice message sent: {voice_url}", flush=True)
                    return
            except Exception as e:
                print(f"[VoiceOutput] TTS conversion failed: {e}", flush=True)

            # Fallback: send original text as plain message
            print("[VoiceOutput] TTS failed, falling back to plain text", flush=True)
            chain = platform_message.MessageChain([
                platform_message.Plain(text=response_text),
            ])
            await event_context.reply(chain)

        @self.handler(events.GroupCommandSent)
        async def on_group_command(event_context: context.EventContext):
            """Handle voice command in groups."""
            event = event_context.event
            if event.command != "voice":
                return
            await self._handle_voice_command(
                event_context,
                event.launcher_type,
                event.launcher_id,
                event.sender_id,
                event.params,
            )

        @self.handler(events.PersonCommandSent)
        async def on_person_command(event_context: context.EventContext):
            """Handle voice command in private chats."""
            event = event_context.event
            if event.command != "voice":
                return
            await self._handle_voice_command(
                event_context,
                event.launcher_type,
                event.launcher_id,
                event.sender_id,
                event.params,
            )

        @self.handler(events.GroupMessageReceived)
        async def on_group_message(event_context: context.EventContext):
            """Handle voice command via message in groups."""
            event = event_context.event
            text = _extract_text(event.message_chain)
            if not text:
                return
            await self._try_voice_command(
                event_context,
                event.launcher_type,
                event.launcher_id,
                event.sender_id,
                text,
            )

        @self.handler(events.PersonMessageReceived)
        async def on_person_message(event_context: context.EventContext):
            """Handle voice command via message in private chats."""
            event = event_context.event
            text = _extract_text(event.message_chain)
            if not text:
                return
            await self._try_voice_command(
                event_context,
                event.launcher_type,
                event.launcher_id,
                event.sender_id,
                text,
            )

    async def _try_voice_command(
        self,
        event_context: context.EventContext,
        launcher_type: str,
        launcher_id: str | int,
        sender_id: str | int,
        text: str,
    ) -> None:
        """Check if the message is a voice command and handle it."""
        import re
        match = re.match(r"^[！!/.](?:voice|语音)\s+(.+)$", text, re.IGNORECASE)
        if not match:
            return
        text_to_speak = match.group(1).strip()
        await self._do_tts(
            event_context, launcher_type, launcher_id, sender_id, text_to_speak,
        )

    async def _handle_voice_command(
        self,
        event_context: context.EventContext,
        launcher_type: str,
        launcher_id: str | int,
        sender_id: str | int,
        params: list[str],
    ) -> None:
        """Handle the /voice command with parameters."""
        if not params:
            chain = platform_message.MessageChain([
                platform_message.Plain(
                    text="❌ 用法: /voice <要朗读的文本>\n"
                         "例如: /voice 你好，欢迎使用语音插件"
                ),
            ])
            await event_context.reply(chain)
            event_context.prevent_default()
            return

        text_to_speak = " ".join(params)
        await self._do_tts(
            event_context, launcher_type, launcher_id, sender_id, text_to_speak,
        )

    async def _do_tts(
        self,
        event_context: context.EventContext,
        launcher_type: str,
        launcher_id: str | int,
        sender_id: str | int,
        text: str,
    ) -> None:
        """Execute TTS conversion and reply with the result."""
        config = self.plugin.get_config()
        token = config.get("api_token", "")

        if not token:
            chain = platform_message.MessageChain([
                platform_message.Plain(text="❌ 未配置 API Token，请在插件设置中填写 token"),
            ])
            await event_context.reply(chain)
            event_context.prevent_default()
            return

        # Check text length
        max_length = int(config.get("max_text_length", 500))
        if len(text) > max_length:
            chain = platform_message.MessageChain([
                platform_message.Plain(
                    text=f"❌ 文本过长（{len(text)} 字符），最大支持 {max_length} 字符"
                ),
            ])
            await event_context.reply(chain)
            event_context.prevent_default()
            return

        print(f"[VoiceOutput] Manual TTS: {text[:80]}...", flush=True)

        try:
            result = await text_to_speech(token, text)
            voice_url = result.get("data", {}).get("voice", "")

            if voice_url:
                # Send voice message using the Voice component
                chain = platform_message.MessageChain([
                    platform_message.Voice(url=voice_url),
                ])
                await event_context.reply(chain)
                print(f"[VoiceOutput] Voice message sent: {voice_url}", flush=True)
                event_context.prevent_default()
                return
        except Exception as e:
            print(f"[VoiceOutput] TTS conversion failed: {e}", flush=True)

        # Fallback: send original text as plain message
        print("[VoiceOutput] TTS failed, falling back to plain text", flush=True)
        chain = platform_message.MessageChain([
            platform_message.Plain(text=text),
        ])
        await event_context.reply(chain)

        event_context.prevent_default()