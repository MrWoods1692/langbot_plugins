from __future__ import annotations

from typing import AsyncGenerator

from langbot_plugin.api.definition.components.command.command import Command
from langbot_plugin.api.entities.builtin.command.context import ExecuteContext, CommandReturn

from core.query import query_timezone, format_timezone_result


class Timezone(Command):

    async def initialize(self):
        await super().initialize()

        @self.subcommand(name="", help="Query global timezone info", usage="timezone <country> <UST|CST>", aliases=["tz"])
        async def query(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            async for ret in self._dispatch(context):
                yield ret

    async def _dispatch(
        self, context: ExecuteContext
    ) -> AsyncGenerator[CommandReturn, None]:
        session = context.session
        params = context.params

        if len(params) < 2:
            yield CommandReturn(text=(
                "🌍 全球时区查询\n"
                "用法: !timezone <国家名称> <UST|CST>\n"
                "示例: !timezone 美国 UST\n"
                "      !timezone 中国 CST\n"
                "      !tz 日本 UST\n\n"
                "时区类型:\n"
                "  UST — 美国时区 (US Time)\n"
                "  CST — 中国标准时间 (China Standard Time)"
            ))
            return

        country = params[0]
        kind = params[1].upper()

        if kind not in ("UST", "CST"):
            yield CommandReturn(text=f"❌ 无效的时区类型: {kind}，请使用 UST 或 CST")
            return

        config = self.plugin.get_config()
        token = config.get("api_token", "")

        if not token:
            yield CommandReturn(text="❌ 未配置 API Token，请在插件设置中填写 token")
            return

        try:
            data = await query_timezone(token, country, kind)
            result = format_timezone_result(data)
            yield CommandReturn(text=result)
        except Exception as e:
            yield CommandReturn(text=f"❌ 查询时区失败: {e}")