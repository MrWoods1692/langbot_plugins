from __future__ import annotations

from typing import AsyncGenerator

from langbot_plugin.api.definition.components.command.command import Command
from langbot_plugin.api.entities.builtin.command.context import ExecuteContext, CommandReturn

from core.commands import run_learn_command


class Learn(Command):

    async def initialize(self):
        await super().initialize()

        @self.subcommand(name="", help="Show learning overview", usage="learn", aliases=["l"])
        async def overview(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            async for ret in self._dispatch(context, []):
                yield ret

        @self.subcommand(name="qfx", help="Group analysis chart image", usage="learn qfx")
        async def qfx(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            async for ret in self._dispatch(context, ["qfx"]):
                yield ret

        @self.subcommand(name="status", help="Show detailed status", usage="learn status")
        async def status(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            async for ret in self._dispatch(context, ["status"]):
                yield ret

        @self.subcommand(name="slang", help="Show top group slang", usage="learn slang")
        async def slang(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            async for ret in self._dispatch(context, ["slang"]):
                yield ret

        @self.subcommand(name="relation", help="Show relationship info", usage="learn relation")
        async def relation(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            async for ret in self._dispatch(context, ["relation"]):
                yield ret

        @self.subcommand(name="infer", help="Infer slang meanings via LLM", usage="learn infer")
        async def infer(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            async for ret in self._dispatch(context, ["infer"]):
                yield ret

        @self.subcommand(name="graph", help="Show memory graph stats", usage="learn graph")
        async def graph(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            async for ret in self._dispatch(context, ["graph"]):
                yield ret

    async def _dispatch(
        self, context: ExecuteContext, params: list[str]
    ) -> AsyncGenerator[CommandReturn, None]:
        session = context.session
        sender_id = session.sender_id or session.launcher_id
        result = await run_learn_command(
            self.plugin.store,
            self.plugin,
            session.launcher_type.value,
            session.launcher_id,
            sender_id,
            params,
        )
        if result.image_base64:
            yield CommandReturn(image_base64=result.image_base64)
        else:
            yield CommandReturn(text=result.text or "")
