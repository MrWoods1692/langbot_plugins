from __future__ import annotations

from langbot_plugin.api.definition.components.common.event_listener import EventListener
from langbot_plugin.api.entities import events, context
from langbot_plugin.api.entities.builtin.provider import message as provider_message
from langbot_plugin.api.entities.builtin.platform import message as platform_message


def _extract_text(message_chain: platform_message.MessageChain | None) -> str:
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

        @self.handler(events.GroupMessageReceived)
        async def on_group_message(event_context: context.EventContext):
            event = event_context.event
            text = _extract_text(event.message_chain)
            if text:
                await self.plugin.record_user_message(
                    event.launcher_type, event.launcher_id, event.sender_id, text
                )

        @self.handler(events.PersonMessageReceived)
        async def on_person_message(event_context: context.EventContext):
            event = event_context.event
            text = _extract_text(event.message_chain)
            if text:
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
