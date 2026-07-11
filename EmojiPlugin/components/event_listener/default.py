from __future__ import annotations

import re

from langbot_plugin.api.definition.components.common.event_listener import EventListener
from langbot_plugin.api.entities import events, context
from langbot_plugin.api.entities.builtin.platform import message as platform_message

from core.emoji import emoji_fusion

# Match two emoji characters (consecutive or separated by whitespace/punctuation)
_EMOJI_PAIR_RE = re.compile(
    r"([\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
    r"\U0001F1E0-\U0001F1FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F"
    r"\U0001FA70-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF"
    r"\U00002300-\U000023FF\U00002B50\U00002B55\U00003030\U0000303D"
    r"\U00003297\U00003299\U0001F780-\U0001F7FF\U0001FA00-\U0001FA6F"
    r"\U0001FA70-\U0001FAFF\U0001F004\U0001F0CF\U0001F18E\U0001F191-\U0001F19A"
    r"\U0001F201-\U0001F251\U0001F300-\U0001F320\U0001F32D-\U0001F335"
    r"\U0001F337-\U0001F37C\U0001F37E-\U0001F393\U0001F3A0-\U0001F3CA"
    r"\U0001F3CF-\U0001F3D3\U0001F3E0-\U0001F3F0\U0001F3F4\U0001F3F8-\U0001F43E"
    r"\U0001F440\U0001F442-\U0001F4FC\U0001F4FF-\U0001F53D\U0001F54B-\U0001F54E"
    r"\U0001F550-\U0001F567\U0001F57A\U0001F595-\U0001F596\U0001F5A4"
    r"\U0001F5FB-\U0001F64F\U0001F680-\U0001F6C5\U0001F6CC\U0001F6D0-\U0001F6D2"
    r"\U0001F6D5-\U0001F6D7\U0001F6DD-\U0001F6DF\U0001F6EB-\U0001F6EC"
    r"\U0001F6F4-\U0001F6FC\U0001F7E0-\U0001F7EB\U0001F7F0\U0001F90C-\U0001F93A"
    r"\U0001F93C-\U0001F945\U0001F947-\U0001F9FF\U0001FA70-\U0001FA7C"
    r"\U0001FA80-\U0001FA88\U0001FA90-\U0001FABD\U0001FABF-\U0001FAC5"
    r"\U0001FACE-\U0001FADB\U0001FAE0-\U0001FAE8\U0001FAF0-\U0001FAF8])"
    r".*?"
    r"([\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
    r"\U0001F1E0-\U0001F1FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F"
    r"\U0001FA70-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF"
    r"\U00002300-\U000023FF\U00002B50\U00002B55\U00003030\U0000303D"
    r"\U00003297\U00003299\U0001F780-\U0001F7FF\U0001FA00-\U0001FA6F"
    r"\U0001FA70-\U0001FAFF\U0001F004\U0001F0CF\U0001F18E\U0001F191-\U0001F19A"
    r"\U0001F201-\U0001F251\U0001F300-\U0001F320\U0001F32D-\U0001F335"
    r"\U0001F337-\U0001F37C\U0001F37E-\U0001F393\U0001F3A0-\U0001F3CA"
    r"\U0001F3CF-\U0001F3D3\U0001F3E0-\U0001F3F0\U0001F3F4\U0001F3F8-\U0001F43E"
    r"\U0001F440\U0001F442-\U0001F4FC\U0001F4FF-\U0001F53D\U0001F54B-\U0001F54E"
    r"\U0001F550-\U0001F567\U0001F57A\U0001F595-\U0001F596\U0001F5A4"
    r"\U0001F5FB-\U0001F64F\U0001F680-\U0001F6C5\U0001F6CC\U0001F6D0-\U0001F6D2"
    r"\U0001F6D5-\U0001F6D7\U0001F6DD-\U0001F6DF\U0001F6EB-\U0001F6EC"
    r"\U0001F6F4-\U0001F6FC\U0001F7E0-\U0001F7EB\U0001F7F0\U0001F90C-\U0001F93A"
    r"\U0001F93C-\U0001F945\U0001F947-\U0001F9FF\U0001FA70-\U0001FA7C"
    r"\U0001FA80-\U0001FA88\U0001FA90-\U0001FABD\U0001FABF-\U0001FAC5"
    r"\U0001FACE-\U0001FADB\U0001FAE0-\U0001FAE8\U0001FAF0-\U0001FAF8])",
)


def _extract_text(message_chain: platform_message.MessageChain | None) -> str:
    """Extract plain text from a message chain."""
    if not message_chain:
        return ""
    parts: list[str] = []
    for component in message_chain:
        if isinstance(component, platform_message.Plain) and component.text:
            parts.append(component.text)
    return "".join(parts).strip()


def _extract_emoji_pair(text: str) -> tuple[str, str] | None:
    """Extract the first two emoji characters from text. Returns (go, to) or None."""
    match = _EMOJI_PAIR_RE.search(text)
    if not match:
        return None
    return match.group(1), match.group(2)


class DefaultEventListener(EventListener):

    async def initialize(self):
        await super().initialize()

        @self.handler(events.GroupMessageReceived)
        async def on_group_message(event_context: context.EventContext):
            """Detect two emojis in group messages and fuse them."""
            event = event_context.event
            text = _extract_text(event.message_chain)
            pair = _extract_emoji_pair(text)
            if pair is None:
                return
            print(f"[Emoji] GroupMessageReceived: {pair[0]} + {pair[1]}", flush=True)
            await self._handle_emoji_fusion(event_context, pair[0], pair[1])

        @self.handler(events.PersonMessageReceived)
        async def on_person_message(event_context: context.EventContext):
            """Detect two emojis in private messages and fuse them."""
            event = event_context.event
            text = _extract_text(event.message_chain)
            pair = _extract_emoji_pair(text)
            if pair is None:
                return
            print(f"[Emoji] PersonMessageReceived: {pair[0]} + {pair[1]}", flush=True)
            await self._handle_emoji_fusion(event_context, pair[0], pair[1])

    async def _handle_emoji_fusion(
        self,
        event_context: context.EventContext,
        go: str,
        to: str,
    ):
        """Call the emoji fusion API and send the result image."""
        config = self.plugin.get_config()
        token = config.get("api_token", "")
        show_link = config.get("show_link", False)

        if not token:
            print("[Emoji] API token not configured, skipping", flush=True)
            return

        print(f"[Emoji] Calling API: {go} + {to}", flush=True)

        try:
            result = await emoji_fusion(token, go, to)
            url = result.get("data", {}).get("url", "")

            if url:
                # Send the fusion image
                chain = platform_message.MessageChain([
                    platform_message.Image(url=url),
                ])
                await event_context.reply(chain)

                # Optionally send the link
                if show_link:
                    await event_context.reply(
                        platform_message.MessageChain([
                            platform_message.Plain(text=f"🔗 {url}"),
                        ])
                    )

                event_context.prevent_default()
                print(f"[Emoji] Fusion success: {url}", flush=True)
            else:
                print("[Emoji] Fusion failed: no url in response", flush=True)
        except Exception as e:
            print(f"[Emoji] Fusion error: {e}", flush=True)