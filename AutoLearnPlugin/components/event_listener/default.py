from __future__ import annotations

import re

from langbot_plugin.api.definition.components.common.event_listener import EventListener
from langbot_plugin.api.entities import events, context
from langbot_plugin.api.entities.builtin.provider import message as provider_message
from langbot_plugin.api.entities.builtin.platform import message as platform_message

from core.commands import LearnResult

LEARN_CMD_RE = re.compile(
    r"^[!.／/、]?learn(?:\s+(.+))?$",
    re.IGNORECASE,
)


def _analyze_message(message_chain: platform_message.MessageChain | None) -> tuple[str, int, int]:
    if not message_chain:
        return "", 0, 0
    parts: list[str] = []
    image_count = 0
    for component in message_chain:
        if isinstance(component, platform_message.Plain) and component.text:
            parts.append(component.text)
        elif isinstance(component, platform_message.Image):
            image_count += 1
    text = "".join(parts).strip()
    return text, image_count, 0


def _extract_text(message_chain: platform_message.MessageChain | None) -> str:
    text, _, _ = _analyze_message(message_chain)
    return text


def _parse_learn_command(text: str) -> list[str] | None:
    match = LEARN_CMD_RE.match(text.strip())
    if not match:
        return None
    rest = (match.group(1) or "").strip()
    return rest.split() if rest else []


class DefaultEventListener(EventListener):

    async def _reply_learn(
        self,
        event_context: context.EventContext,
        launcher_type: str,
        launcher_id: str | int,
        sender_id: str | int,
        params: list[str],
    ) -> None:
        result: LearnResult = await self.plugin.handle_learn_command(
            launcher_type, launcher_id, sender_id, params
        )
        if result.image_base64:
            print("[AutoLearn] Command reply: group analysis image", flush=True)
            chain = platform_message.MessageChain([
                platform_message.Image(base64=result.image_base64),
            ])
        else:
            print(f"[AutoLearn] Command reply: {(result.text or '')[:80]}...", flush=True)
            chain = platform_message.MessageChain([
                platform_message.Plain(text=result.text or ""),
            ])
        await event_context.reply(chain)
        event_context.prevent_default()

    async def initialize(self):
        await super().initialize()

        @self.handler(events.GroupCommandSent)
        async def on_group_command(event_context: context.EventContext):
            event = event_context.event
            if event.command != "learn":
                return
            await self._reply_learn(
                event_context,
                event.launcher_type,
                event.launcher_id,
                event.sender_id,
                event.params,
            )

        @self.handler(events.PersonCommandSent)
        async def on_person_command(event_context: context.EventContext):
            event = event_context.event
            if event.command != "learn":
                return
            await self._reply_learn(
                event_context,
                event.launcher_type,
                event.launcher_id,
                event.sender_id,
                event.params,
            )

        @self.handler(events.GroupMessageReceived)
        async def on_group_message(event_context: context.EventContext):
            event = event_context.event
            text, image_count, _ = _analyze_message(event.message_chain)
            if not text and image_count == 0:
                return

            if text:
                params = _parse_learn_command(text)
                if params is not None:
                    await self._reply_learn(
                        event_context,
                        event.launcher_type,
                        event.launcher_id,
                        event.sender_id,
                        params,
                    )
                    return

            await self.plugin.record_user_message(
                event.launcher_type, event.launcher_id, event.sender_id,
                text, image_count=image_count,
            )

        @self.handler(events.PersonMessageReceived)
        async def on_person_message(event_context: context.EventContext):
            event = event_context.event
            text = _extract_text(event.message_chain)
            if not text:
                return

            params = _parse_learn_command(text)
            if params is not None:
                await self._reply_learn(
                    event_context,
                    event.launcher_type,
                    event.launcher_id,
                    event.sender_id,
                    params,
                )
                return

            await self.plugin.record_user_message(
                event.launcher_type, event.launcher_id, event.sender_id, text
            )

        @self.handler(events.GroupNormalMessageReceived)
        async def on_group_normal(event_context: context.EventContext):
            event = event_context.event
            session_name = f"{event.launcher_type}_{event.launcher_id}"
            self.plugin.set_pending_sender(session_name, event.sender_id)

        @self.handler(events.PersonNormalMessageReceived)
        async def on_person_normal(event_context: context.EventContext):
            event = event_context.event
            session_name = f"{event.launcher_type}_{event.launcher_id}"
            self.plugin.set_pending_sender(session_name, event.sender_id)

        @self.handler(events.NormalMessageResponded)
        async def on_responded(event_context: context.EventContext):
            event = event_context.event
            session_name = f"{event.session.launcher_type.value}_{event.session.launcher_id}"
            if event.response_text:
                await self.plugin.record_bot_response(session_name, event.response_text)

        @self.handler(events.PromptPreProcessing)
        async def on_prompt(event_context: context.EventContext):
            config = self.plugin.get_config()
            if not config.get("enable_prompt_injection", True):
                return

            event = event_context.event
            sender_id = self.plugin.get_pending_sender(event.session_name)
            ctx_text = self.plugin.build_prompt_context(event.session_name, sender_id)
            if not ctx_text:
                return

            injection = provider_message.Message(role="system", content=ctx_text)
            event.default_prompt.append(injection)
