from __future__ import annotations

from typing import AsyncGenerator

from langbot_plugin.api.definition.components.command.command import Command
from langbot_plugin.api.entities.builtin.command.context import ExecuteContext, CommandReturn
from langbot_plugin.api.entities.builtin.platform import message as platform_message

from core.tts import text_to_speech


class TTS(Command):

    async def initialize(self):
        await super().initialize()

        @self.subcommand(
            name="",
            help="Convert text to speech and send as voice message",
            usage="tts <text>",
            aliases=["语音"],
        )
        async def tts(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            session = context.session
            params = context.params

            if not params:
                yield CommandReturn(
                    text="❌ 用法: /tts <要朗读的文本>\n例如: /tts 你好，欢迎使用语音插件"
                )
                return

            text = " ".join(params)
            config = self.plugin.get_config()
            token = config.get("api_token", "")

            if not token:
                yield CommandReturn(text="❌ 未配置 API Token，请在插件设置中填写 token")
                return

            max_length = int(config.get("max_text_length", 500))
            if len(text) > max_length:
                yield CommandReturn(
                    text=f"❌ 文本过长（{len(text)} 字符），最大支持 {max_length} 字符"
                )
                return

            print(f"[VoiceOutput] Command TTS: {text[:80]}...", flush=True)

            try:
                result = await text_to_speech(token, text)
                voice_url = result.get("data", {}).get("voice", "")

                if voice_url:
                    # Send voice message directly via reply
                    chain = platform_message.MessageChain([
                        platform_message.Voice(url=voice_url),
                    ])
                    await context.reply(chain)
                    yield CommandReturn()
                    return
            except Exception as e:
                print(f"[VoiceOutput] Command TTS failed: {e}", flush=True)

            # Fallback: return original text
            yield CommandReturn(text=text)
