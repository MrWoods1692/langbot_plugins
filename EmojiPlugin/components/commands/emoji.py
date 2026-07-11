from __future__ import annotations

from typing import AsyncGenerator

from langbot_plugin.api.definition.components.command.command import Command
from langbot_plugin.api.entities.builtin.command.context import ExecuteContext, CommandReturn
from langbot_plugin.api.entities.builtin.platform import message as platform_message

from core.emoji import emoji_fusion


class Emoji(Command):

    async def initialize(self):
        await super().initialize()

        @self.subcommand(
            name="",
            help="Fuse two emojis into one",
            usage="emoji <表情1> <表情2>",
            aliases=["表情", "融合"],
        )
        async def emoji(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            session = context.session
            params = context.params

            if len(params) < 2:
                yield CommandReturn(
                    text="❌ 用法: /emoji <表情1> <表情2>\n例如: /emoji 😀 😂"
                )
                return

            go = params[0]
            to = params[1]
            config = self.plugin.get_config()
            token = config.get("api_token", "")
            show_link = config.get("show_link", False)

            if not token:
                yield CommandReturn(text="❌ 未配置 API Token，请在插件设置中填写 token")
                return

            print(f"[Emoji] Command: {go} + {to}", flush=True)

            try:
                result = await emoji_fusion(token, go, to)
                url = result.get("data", {}).get("url", "")

                if url:
                    # Send the fusion image
                    chain = platform_message.MessageChain([
                        platform_message.Image(url=url),
                    ])
                    await context.reply(chain)

                    # Optionally send the link
                    if show_link:
                        yield CommandReturn(text=f"🔗 {url}")
                    else:
                        yield CommandReturn()
                    return
                else:
                    yield CommandReturn(text="❌ 表情融合失败: 未获取到结果链接")
                    return
            except Exception as e:
                print(f"[Emoji] Command failed: {e}", flush=True)
                yield CommandReturn(text=f"❌ 表情融合失败: {e}")