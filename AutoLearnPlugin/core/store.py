from __future__ import annotations

import json
import re
import time
import uuid
from copy import deepcopy
from datetime import datetime
from typing import Any

STORAGE_KEY = "auto_learn_data"

DEFAULT_DATA: dict[str, Any] = {
    "style_profiles": {},
    "slang": {},
    "relationships": {},
    "group_members": {},
    "group_stats": {},
    "personality": {
        "traits": {
            "warmth": 0.5,
            "humor": 0.5,
            "formality": 0.5,
            "empathy": 0.5,
            "curiosity": 0.5,
        },
        "evolution_log": [],
    },
    "memory_graph": {"nodes": [], "edges": []},
    "stats": {"messages_processed": 0, "last_updated": 0},
}

POSITIVE_WORDS = {
    "好", "棒", "赞", "谢谢", "感谢", "喜欢", "开心", "哈哈", "厉害", "牛",
    "爱", "nice", "good", "great", "awesome", "love", "thanks",
}
NEGATIVE_WORDS = {
    "烦", "差", "烂", "讨厌", "无语", "生气", "滚", "傻", "垃圾", "不行",
    "bad", "hate", "stupid", "suck", "angry",
}
COMMON_WORDS = {
    "的", "了", "是", "我", "你", "他", "她", "它", "们", "在", "有", "和",
    "不", "这", "那", "就", "也", "都", "要", "会", "吗", "呢", "吧", "啊",
    "哦", "嗯", "哈", "呀", "么", "什么", "怎么", "可以", "没有", "一个",
    "the", "a", "an", "is", "are", "was", "were", "to", "of", "and", "or",
    "in", "on", "at", "for", "it", "this", "that", "you", "me", "we",
}


def _now() -> float:
    return time.time()


def _user_key(launcher_type: str, sender_id: str | int) -> str:
    return f"{launcher_type}_{sender_id}"


def _group_key(launcher_type: str, launcher_id: str | int) -> str:
    return f"{launcher_type}_{launcher_id}"


def _extract_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for word in re.findall(r"[\u4e00-\u9fff]{2,6}|[a-zA-Z]{3,12}", text.lower()):
        if word not in COMMON_WORDS:
            tokens.append(word)
    for phrase in re.findall(r"[\u4e00-\u9fff]{2,4}", text):
        if phrase not in COMMON_WORDS:
            tokens.append(phrase)
    return tokens


def _count_emojis(text: str) -> int:
    return len(re.findall(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", text))


def _hour_key() -> str:
    return str(datetime.now().hour)


def _sentiment_score(text: str) -> float:
    score = 0.0
    lower = text.lower()
    for word in POSITIVE_WORDS:
        if word in lower:
            score += 1.0
    for word in NEGATIVE_WORDS:
        if word in lower:
            score -= 1.5
    return score


class LearnStore:
    def __init__(self) -> None:
        self.data: dict[str, Any] = deepcopy(DEFAULT_DATA)

    def load(self, raw: bytes | None) -> None:
        if not raw:
            self.data = deepcopy(DEFAULT_DATA)
            return
        try:
            loaded = json.loads(raw.decode("utf-8"))
            merged = deepcopy(DEFAULT_DATA)
            for key in DEFAULT_DATA:
                if key in loaded:
                    merged[key] = loaded[key]
            self.data = merged
        except Exception:
            self.data = deepcopy(DEFAULT_DATA)

    def dump(self) -> bytes:
        self.data["stats"]["last_updated"] = _now()
        return json.dumps(self.data, ensure_ascii=False).encode("utf-8")

    def record_message(
        self,
        launcher_type: str,
        launcher_id: str | int,
        sender_id: str | int,
        text: str,
        is_bot: bool = False,
        image_count: int = 0,
    ) -> None:
        text = (text or "").strip()
        if not text and image_count == 0:
            return

        user_key = _user_key("person", sender_id)
        group_key = _group_key(launcher_type, launcher_id)
        char_count = len(text)
        emoji_count = _count_emojis(text)
        self.data["stats"]["messages_processed"] += 1

        if not is_bot:
            if text:
                self._update_style(user_key, text)
                self._update_slang(group_key, text)
                self._update_relationship(user_key, text)
                self._update_memory_graph(user_key, group_key, text, sender_id, launcher_id)
            if launcher_type == "group":
                self._update_group_member(
                    group_key, user_key, sender_id, text,
                    char_count, image_count, emoji_count,
                )
                self._update_group_stats(
                    group_key, sender_id, text, char_count, image_count, emoji_count,
                )
        elif text:
            self._evolve_personality(text)

    def _update_group_stats(
        self,
        group_key: str,
        sender_id: str | int,
        text: str,
        char_count: int,
        image_count: int,
        emoji_count: int,
    ) -> None:
        stats = self.data["group_stats"].setdefault(
            group_key,
            {
                "total_messages": 0,
                "total_chars": 0,
                "total_images": 0,
                "total_emojis": 0,
                "hourly": {},
                "message_log": [],
            },
        )
        stats["total_messages"] += 1
        stats["total_chars"] += char_count
        stats["total_images"] += image_count
        stats["total_emojis"] += emoji_count
        hour = _hour_key()
        stats["hourly"][hour] = stats["hourly"].get(hour, 0) + 1

        if text:
            log: list[dict[str, Any]] = stats["message_log"]
            log.append({
                "user_id": str(sender_id),
                "text": text[:200],
                "ts": _now(),
            })
            if len(log) > 200:
                stats["message_log"] = log[-150:]

    def _update_group_member(
        self,
        group_key: str,
        user_key: str,
        sender_id: str | int,
        text: str,
        char_count: int,
        image_count: int,
        emoji_count: int,
    ) -> None:
        members = self.data["group_members"].setdefault(group_key, {})
        entry = members.setdefault(
            user_key,
            {
                "user_id": str(sender_id),
                "message_count": 0,
                "char_count": 0,
                "image_count": 0,
                "emoji_count": 0,
                "last_active": 0,
                "samples": [],
            },
        )
        entry["message_count"] += 1
        entry["char_count"] += char_count
        entry["image_count"] += image_count
        entry["emoji_count"] += emoji_count
        entry["last_active"] = _now()
        entry["user_id"] = str(sender_id)
        if text:
            samples: list[str] = entry["samples"]
            if len(samples) < 20:
                samples.append(text[:120])
            elif entry["message_count"] % 3 == 0:
                samples[entry["message_count"] % 20] = text[:120]

    def _update_style(self, user_key: str, text: str) -> None:
        profiles = self.data["style_profiles"]
        profile = profiles.setdefault(
            user_key,
            {
                "message_count": 0,
                "avg_length": 0.0,
                "emoji_ratio": 0.0,
                "common_phrases": {},
                "samples": [],
            },
        )
        count = profile["message_count"] + 1
        profile["avg_length"] = (
            profile["avg_length"] * profile["message_count"] + len(text)
        ) / count
        profile["message_count"] = count

        emoji_count = len(re.findall(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", text))
        profile["emoji_ratio"] = (
            profile["emoji_ratio"] * (count - 1) + (emoji_count / max(len(text), 1))
        ) / count

        for token in _extract_tokens(text)[:8]:
            phrases = profile["common_phrases"]
            phrases[token] = phrases.get(token, 0) + 1

        samples: list[str] = profile["samples"]
        if len(samples) < 10:
            samples.append(text[:80])
        elif count % 5 == 0:
            samples[count % 10] = text[:80]

    def _update_slang(self, group_key: str, text: str) -> None:
        slang_map = self.data["slang"].setdefault(group_key, {})
        for token in _extract_tokens(text):
            if len(token) < 2:
                continue
            entry = slang_map.setdefault(
                token,
                {
                    "count": 0,
                    "meaning": "",
                    "confidence": 0.0,
                    "samples": [],
                },
            )
            entry["count"] += 1
            samples: list[str] = entry["samples"]
            if len(samples) < 5:
                samples.append(text[:60])
            elif entry["count"] % 10 == 0:
                samples[entry["count"] % 5] = text[:60]

    def _update_relationship(self, user_key: str, text: str) -> None:
        rel = self.data["relationships"].setdefault(
            user_key,
            {
                "favorability": 50.0,
                "mood": "neutral",
                "interaction_count": 0,
                "positive_hits": 0,
                "negative_hits": 0,
                "last_interaction": 0,
            },
        )
        rel["interaction_count"] += 1
        rel["last_interaction"] = _now()

        sentiment = _sentiment_score(text)
        if sentiment > 0:
            rel["positive_hits"] += 1
            rel["favorability"] = min(100.0, rel["favorability"] + sentiment * 0.8)
            rel["mood"] = "happy"
        elif sentiment < 0:
            rel["negative_hits"] += 1
            rel["favorability"] = max(0.0, rel["favorability"] + sentiment * 1.2)
            rel["mood"] = "annoyed"
        else:
            rel["favorability"] = min(100.0, rel["favorability"] + 0.2)
            if rel["mood"] == "annoyed":
                rel["mood"] = "neutral"

    def _update_memory_graph(
        self,
        user_key: str,
        group_key: str,
        text: str,
        sender_id: str | int,
        launcher_id: str | int,
    ) -> None:
        graph = self.data["memory_graph"]
        nodes: list[dict[str, Any]] = graph["nodes"]
        edges: list[dict[str, Any]] = graph["edges"]

        user_node_id = f"user:{user_key}"
        group_node_id = f"group:{group_key}"
        self._ensure_node(nodes, user_node_id, "person", str(sender_id), 1.0)
        self._ensure_node(nodes, group_node_id, "group", str(launcher_id), 0.8)
        self._ensure_edge(edges, user_node_id, group_node_id, "member_of")

        for token in _extract_tokens(text)[:3]:
            topic_id = f"topic:{token}"
            self._ensure_node(nodes, topic_id, "topic", token, 0.5)
            self._ensure_edge(edges, user_node_id, topic_id, "mentioned")

        if len(text) > 20:
            memory_id = f"memory:{uuid.uuid4().hex[:8]}"
            nodes.append(
                {
                    "id": memory_id,
                    "type": "memory",
                    "label": text[:30] + ("..." if len(text) > 30 else ""),
                    "weight": 0.3,
                    "content": text[:200],
                    "timestamp": _now(),
                }
            )
            self._ensure_edge(edges, user_node_id, memory_id, "said")

        if len(nodes) > 500:
            graph["nodes"] = nodes[-400:]
            valid_ids = {n["id"] for n in graph["nodes"]}
            graph["edges"] = [e for e in edges if e["source"] in valid_ids and e["target"] in valid_ids]

    def _ensure_node(
        self,
        nodes: list[dict[str, Any]],
        node_id: str,
        node_type: str,
        label: str,
        weight: float,
    ) -> None:
        for node in nodes:
            if node["id"] == node_id:
                node["weight"] = min(1.0, node.get("weight", 0.5) + 0.05)
                return
        nodes.append(
            {"id": node_id, "type": node_type, "label": label, "weight": weight}
        )

    def _ensure_edge(
        self,
        edges: list[dict[str, Any]],
        source: str,
        target: str,
        relation: str,
    ) -> None:
        for edge in edges:
            if edge["source"] == source and edge["target"] == target:
                edge["weight"] = edge.get("weight", 1) + 1
                return
        edges.append({"source": source, "target": target, "relation": relation, "weight": 1})

    def _evolve_personality(self, response_text: str) -> None:
        traits = self.data["personality"]["traits"]
        lower = response_text.lower()
        if any(w in lower for w in ("哈哈", "笑", "有趣", "好玩", "lol", "haha")):
            traits["humor"] = min(1.0, traits["humor"] + 0.002)
        if any(w in lower for w in ("理解", "感受", "陪伴", "没关系", "别担心")):
            traits["empathy"] = min(1.0, traits["empathy"] + 0.002)
        if any(w in lower for w in ("为什么", "怎么", "好奇", "想知道")):
            traits["curiosity"] = min(1.0, traits["curiosity"] + 0.002)
        if len(response_text) > 120:
            traits["formality"] = min(1.0, traits["formality"] + 0.001)
        else:
            traits["warmth"] = min(1.0, traits["warmth"] + 0.001)

    def get_top_slang(self, group_key: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        groups = [group_key] if group_key else list(self.data["slang"].keys())
        for gk in groups:
            for word, info in self.data["slang"].get(gk, {}).items():
                if info["count"] >= 3:
                    results.append({"group": gk, "word": word, **info})
        results.sort(key=lambda x: x["count"], reverse=True)
        return results[:limit]

    def get_relationship(self, user_key: str) -> dict[str, Any] | None:
        return self.data["relationships"].get(user_key)

    def get_style_profile(self, user_key: str) -> dict[str, Any] | None:
        return self.data["style_profiles"].get(user_key)

    def build_prompt_context(
        self,
        session_name: str,
        sender_id: str | int | None = None,
    ) -> str:
        parts: list[str] = []
        traits = self.data["personality"]["traits"]
        parts.append(
            "[自主学习上下文] 当前人格特质: "
            f"温暖={traits['warmth']:.2f}, 幽默={traits['humor']:.2f}, "
            f"正式={traits['formality']:.2f}, 共情={traits['empathy']:.2f}, "
            f"好奇={traits['curiosity']:.2f}"
        )

        is_group = session_name.startswith("group_")
        user_key: str | None = None
        if sender_id is not None:
            user_key = _user_key("person", sender_id)
        elif not is_group:
            user_key = session_name

        if user_key:
            rel = self.data["relationships"].get(user_key)
            if rel:
                parts.append(
                    f"当前发言者({user_key}): 好感度={rel['favorability']:.0f}/100, "
                    f"心情={rel['mood']}, 互动{rel['interaction_count']}次"
                )
            style = self.data["style_profiles"].get(user_key)
            if style:
                top_phrases = sorted(
                    style["common_phrases"].items(), key=lambda x: x[1], reverse=True
                )[:5]
                if top_phrases:
                    phrase_str = ", ".join(f"{p}({c})" for p, c in top_phrases)
                    parts.append(
                        f"发言风格: 均句长{style['avg_length']:.0f}字, "
                        f"常用[{phrase_str}]"
                    )
                    if style["samples"]:
                        parts.append(f"说话示例: 「{style['samples'][-1]}」")

        if is_group:
            group_key = session_name
            members = self.data["group_members"].get(group_key, {})
            if members:
                top = sorted(
                    members.values(), key=lambda m: m["message_count"], reverse=True
                )[:5]
                member_str = ", ".join(
                    f"{m['user_id']}({m['message_count']}条)" for m in top
                )
                parts.append(f"本群活跃成员: {member_str}")

            slang = self.get_top_slang(group_key, 5)
            if slang:
                slang_str = "; ".join(
                    f"{s['word']}({s['count']}次"
                    + (f":{s['meaning']}" if s.get("meaning") else "")
                    + ")"
                    for s in slang
                )
                parts.append(f"群黑话/高频词: {slang_str}")

        return "\n".join(parts)

    def get_group_analysis(self, group_key: str) -> dict[str, Any]:
        group_id = group_key.split("_", 1)[-1] if "_" in group_key else group_key
        members_raw = self.data["group_members"].get(group_key, {})
        top_members: list[dict[str, Any]] = []
        total_messages = 0
        for user_key, info in members_raw.items():
            total_messages += info["message_count"]
            rel = self.data["relationships"].get(user_key, {})
            top_members.append({
                "user_key": user_key,
                "user_id": info["user_id"],
                "message_count": info["message_count"],
                "favorability": rel.get("favorability", 50),
                "mood": rel.get("mood", "neutral"),
            })
        top_members.sort(key=lambda m: m["message_count"], reverse=True)

        slang = self.get_top_slang(group_key, 10)
        graph = self.data["memory_graph"]
        type_counts: dict[str, int] = {}
        for node in graph["nodes"]:
            if node.get("id", "").startswith(f"group:{group_key}"):
                continue
            t = node.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        graph_summary = [
            f"节点 {len(graph['nodes'])} · 边 {len(graph['edges'])}",
        ]
        for t, c in sorted(type_counts.items(), key=lambda x: -x[1])[:5]:
            graph_summary.append(f"  {t}: {c}")

        return {
            "group_id": group_id,
            "group_key": group_key,
            "total_messages": total_messages,
            "member_count": len(members_raw),
            "slang_count": len(self.data["slang"].get(group_key, {})),
            "graph_nodes": len(graph["nodes"]),
            "top_members": top_members,
            "top_slang": slang,
            "personality": self.data["personality"]["traits"],
            "graph_summary": graph_summary,
        }

    def set_slang_meaning(self, group_key: str, word: str, meaning: str, confidence: float = 0.8) -> bool:
        entry = self.data["slang"].get(group_key, {}).get(word)
        if not entry:
            return False
        entry["meaning"] = meaning
        entry["confidence"] = confidence
        slang_node_id = f"slang:{group_key}:{word}"
        self._ensure_node(
            self.data["memory_graph"]["nodes"],
            slang_node_id,
            "slang",
            f"{word}={meaning}",
            0.7,
        )
        return True

    def get_graph_data(self) -> dict[str, Any]:
        return self.data["memory_graph"]

    def get_summary(self) -> dict[str, Any]:
        return {
            "messages_processed": self.data["stats"]["messages_processed"],
            "users_tracked": len(self.data["style_profiles"]),
            "relationships": len(self.data["relationships"]),
            "slang_groups": len(self.data["slang"]),
            "graph_nodes": len(self.data["memory_graph"]["nodes"]),
            "graph_edges": len(self.data["memory_graph"]["edges"]),
            "personality": self.data["personality"]["traits"],
        }
