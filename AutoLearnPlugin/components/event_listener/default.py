from __future__ import annotations

import re

from langbot_plugin.api.definition.components.common.event_listener import EventListener
from langbot_plugin.api.entities import events, context
from langbot_plugin.api.entities.builtin.provider import message as provider_message
from langbot_plugin.api.entities.builtin.platform import message as platform_message

LEARN_CMD_RE = re.compile(
    r"^[!.／/、]?learn(?:\s+(.+))?$",
    re.IGNORECASE,
)


def _extract_text(message_chain: platform_message.MessageChain | None) -> str:
    if not message_chain:
        return ""
    parts: list[str] = []
    for component in message_chain:
        if isinstance(component, platform_message.Plain) and component.text:
            parts.append(component.text)
    return "".join(parts).strip()


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
        text = await self.plugin.handle_learn_command(
            launcher_type, launcher_id, sender_id, params
        )
        print(f"[AutoLearn] Command reply: {text[:80]}...", flush=True)
        await event_context.reply(
            platform_message.MessageChain([platform_message.Plain(text=text)])
        )
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
            if event.text_message:
                await self.plugin.record_user_message(
                    event.launcher_type, event.launcher_id, event.sender_id, event.text_message
                )

        @self.handler(events.PersonNormalMessageReceived)
        async def on_person_normal(event_context: context.EventContext):
            event = event_context.event
            if event.text_message:
                await self.plugin.record_user_message(
                    event.launcher_type, event.launcher_id, event.sender_id, event.text_message
                )

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
            ctx_text = self.plugin.build_prompt_context(event.session_name)
            if not ctx_text:
                return

            injection = provider_message.Message(role="system", content=ctx_text)
            event.default_prompt.append(injection)
