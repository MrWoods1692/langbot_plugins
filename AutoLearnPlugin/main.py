from __future__ import annotations

from langbot_plugin.api.definition.plugin import BasePlugin
from langbot_plugin.api.entities.builtin.provider import message as provider_message

from core.store import LearnStore, STORAGE_KEY
from core.commands import run_learn_command


class AutoLearnPlugin(BasePlugin):
    """Autonomous learning plugin — style, slang, relationships, personality, memory graph."""

    store: LearnStore
    _dirty: bool

    def __init__(self) -> None:
        super().__init__()
        self.store = LearnStore()
        self._dirty = False

    async def initialize(self) -> None:
        try:
            raw = await self.get_plugin_storage(STORAGE_KEY)
            self.store.load(raw)
            print(
                f"[AutoLearn] Loaded data: {self.store.get_summary()['messages_processed']} messages",
                flush=True,
            )
        except Exception as e:
            print(f"[AutoLearn] Fresh start: {e}", flush=True)
            self.store.load(None)

    async def persist(self) -> None:
        await self.set_plugin_storage(STORAGE_KEY, self.store.dump())
        self._dirty = False

    async def maybe_persist(self) -> None:
        if self._dirty:
            await self.persist()

    def mark_dirty(self) -> None:
        self._dirty = True

    async def record_user_message(
        self,
        launcher_type: str,
        launcher_id: str | int,
        sender_id: str | int,
        text: str,
    ) -> None:
        self.store.record_message(launcher_type, launcher_id, sender_id, text, is_bot=False)
        self.mark_dirty()
        if self.store.data["stats"]["messages_processed"] % 20 == 0:
            await self.persist()

    async def record_bot_response(self, session_name: str, response_text: str) -> None:
        parts = session_name.split("_", 1)
        if len(parts) != 2:
            return
        launcher_type, launcher_id = parts[0], parts[1]
        self.store.record_message(launcher_type, launcher_id, launcher_id, response_text, is_bot=True)
        self.mark_dirty()

    async def infer_slang_with_llm(self, group_key: str, limit: int = 5) -> list[dict[str, str]]:
        config = self.get_config()
        model_uuid = config.get("llm_model", "")
        if not model_uuid:
            return []

        candidates = self.store.get_top_slang(group_key, limit)
        results: list[dict[str, str]] = []
        for item in candidates:
            if item.get("meaning"):
                continue
            samples = item.get("samples", [])
            prompt = (
                f"这是一个群聊中的高频词「{item['word']}」，出现了{item['count']}次。\n"
                f"上下文示例：\n" + "\n".join(f"- {s}" for s in samples[:3]) + "\n"
                "请用一句话推断这个词在群聊中可能的含义（网络用语/黑话）。只输出含义，不要解释。"
            )
            try:
                resp = await self.invoke_llm(
                    model_uuid,
                    [provider_message.Message(role="user", content=prompt)],
                    timeout=30,
                )
                meaning = ""
                if isinstance(resp.content, str):
                    meaning = resp.content.strip()
                elif isinstance(resp.content, list):
                    for ce in resp.content:
                        if hasattr(ce, "text") and ce.text:
                            meaning = ce.text.strip()
                            break
                if meaning:
                    self.store.set_slang_meaning(group_key, item["word"], meaning)
                    results.append({"word": item["word"], "meaning": meaning})
            except Exception as e:
                print(f"[AutoLearn] LLM infer failed for {item['word']}: {e}", flush=True)
        if results:
            self.mark_dirty()
            await self.persist()
        return results

    def build_prompt_context(self, session_name: str) -> str:
        return self.store.build_prompt_context(session_name)

    async def handle_learn_command(
        self,
        launcher_type: str,
        launcher_id: str | int,
        sender_id: str | int,
        params: list[str],
    ) -> str:
        return await run_learn_command(
            self.store, self, launcher_type, launcher_id, sender_id, params
        )
