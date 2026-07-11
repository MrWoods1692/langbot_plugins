from __future__ import annotations

import re

from langbot_plugin.api.definition.components.common.event_listener import EventListener
from langbot_plugin.api.entities import events, context
from langbot_plugin.api.entities.builtin.platform import message as platform_message

from core.query import query_timezone, format_timezone_result

TZ_CMD_RE = re.compile(r"^[！!/.](?:timezone|tz)\s+(.+?)\s+(UST|CST)", re.IGNORECASE)


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
            if not text:
                return
            match = TZ_CMD_RE.match(text)
            if not match:
                return
            country = match.group(1).strip()
            kind = match.group(2).upper()
            await self._handle_timezone(
                event_context,
                event.launcher_type,
                event.launcher_id,
                event.sender_id,
                country,
                kind,
            )

        @self.handler(events.PersonMessageReceived)
        async def on_person_message(event_context: context.EventContext):
            event = event_context.event
            text = _extract_text(event.message_chain)
            if not text:
                return
            match = TZ_CMD_RE.match(text)
            if not match:
                return
            country = match.group(1).strip()
            kind = match.group(2).upper()
            await self._handle_timezone(
                event_context,
                event.launcher_type,
                event.launcher_id,
                event.sender_id,
                country,
                kind,
            )

    async def _handle_timezone(
        self,
        event_context: context.EventContext,
        launcher_type: str,
        launcher_id: str | int,
        sender_id: str | int,
        country: str,
        kind: str,
    ) -> None:
        kind = kind.upper()
        if kind not in ("UST", "CST"):
            text = f"❌ 无效的时区类型: {kind}，请使用 UST 或 CST"
        else:
            config = self.plugin.get_config()
            token = config.get("api_token", "")

            if not token:
                text = "❌ 未配置 API Token，请在插件设置中填写 token"
            else:
                try:
                    data = await query_timezone(token, country, kind)
                    text = format_timezone_result(data)
                except Exception as e:
                    text = f"❌ 查询时区失败: {e}"

        chain = platform_message.MessageChain([
            platform_message.Plain(text=text),
        ])
        await event_context.reply(chain)
        event_context.prevent_default()