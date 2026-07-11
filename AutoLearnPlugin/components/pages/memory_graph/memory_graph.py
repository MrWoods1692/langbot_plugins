from __future__ import annotations

from langbot_plugin.api.definition.components.page import Page, PageRequest, PageResponse


class MemoryGraphPage(Page):

    async def handle_api(self, request: PageRequest) -> PageResponse:
        plugin = self.plugin

        if request.endpoint == '/graph' and request.method == 'GET':
            return PageResponse.ok(plugin.store.get_graph_data())

        if request.endpoint == '/summary' and request.method == 'GET':
            return PageResponse.ok(plugin.store.get_summary())

        if request.endpoint == '/relationships' and request.method == 'GET':
            return PageResponse.ok(plugin.store.data["relationships"])

        if request.endpoint == '/slang' and request.method == 'GET':
            return PageResponse.ok(plugin.store.data["slang"])

        if request.endpoint == '/personality' and request.method == 'GET':
            return PageResponse.ok(plugin.store.data["personality"])

        return PageResponse.fail(f'Unknown: {request.method} {request.endpoint}')
