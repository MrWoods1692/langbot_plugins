from __future__ import annotations

import json
from typing import Any

from langbot_plugin.api.definition.components.tool.tool import Tool
from langbot_plugin.api.entities.builtin.provider import session as provider_session

from core.store import _user_key, _group_key


class QueryLearnedContext(Tool):

    async def call(
        self,
        params: dict[str, Any],
        session: provider_session.Session,
        query_id: int,
    ) -> str:
        query_type = params.get("query_type", "summary")
        target_id = params.get("target_id", "")

        if target_id:
            user_key = f"person_{target_id}" if not target_id.startswith(("person_", "group_")) else target_id
        else:
            user_key = _user_key(session.launcher_type.value, session.launcher_id)

        group_key = _group_key(session.launcher_type.value, session.launcher_id)
        store = self.plugin.store

        if query_type == "summary":
            return json.dumps(store.get_summary(), ensure_ascii=False)
        if query_type == "style":
            profile = store.get_style_profile(user_key)
            return json.dumps(profile or {}, ensure_ascii=False)
        if query_type == "relation":
            rel = store.get_relationship(user_key)
            return json.dumps(rel or {}, ensure_ascii=False)
        if query_type == "slang":
            items = store.get_top_slang(group_key, 15)
            return json.dumps(items, ensure_ascii=False)
        if query_type == "memory":
            graph = store.get_graph_data()
            return json.dumps(graph, ensure_ascii=False)

        return json.dumps({"error": f"Unknown query_type: {query_type}"}, ensure_ascii=False)
