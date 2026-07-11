from __future__ import annotations

from core.store import LearnStore, _user_key, _group_key


async def run_learn_command(
    store: LearnStore,
    plugin,
    launcher_type: str,
    launcher_id: str | int,
    sender_id: str | int,
    params: list[str],
) -> str:
    subcmd = params[0].lower() if params else ""

    if subcmd in ("", "l"):
        summary = store.get_summary()
        traits = summary["personality"]
        return (
            "📚 自主学习概览\n"
            f"已处理消息: {summary['messages_processed']}\n"
            f"追踪用户: {summary['users_tracked']}\n"
            f"关系记录: {summary['relationships']}\n"
            f"黑话群组: {summary['slang_groups']}\n"
            f"记忆节点: {summary['graph_nodes']} / 边: {summary['graph_edges']}\n"
            f"人格: 温暖{traits['warmth']:.2f} 幽默{traits['humor']:.2f} "
            f"正式{traits['formality']:.2f} 共情{traits['empathy']:.2f} 好奇{traits['curiosity']:.2f}\n"
            "子命令: status | slang | relation | infer | graph"
        )

    if subcmd == "status":
        return str(store.get_summary())

    if subcmd == "slang":
        group_key = _group_key(launcher_type, launcher_id)
        items = store.get_top_slang(group_key, 10)
        if not items:
            return "暂无足够数据推断群黑话（需要至少3次出现）"
        lines = [f"🔤 群 {launcher_id} 高频词 TOP{len(items)}:"]
        for i, item in enumerate(items, 1):
            meaning = item.get("meaning") or "待推断"
            lines.append(f"{i}. {item['word']} ×{item['count']} — {meaning}")
        return "\n".join(lines)

    if subcmd == "relation":
        user_key = _user_key(launcher_type, sender_id)
        rel = store.get_relationship(user_key)
        if not rel:
            return "暂无关系数据，多聊几句就有了~"
        style = store.get_style_profile(user_key)
        text = (
            f"💝 关系档案 ({user_key})\n"
            f"好感度: {rel['favorability']:.0f}/100\n"
            f"心情: {rel['mood']}\n"
            f"互动次数: {rel['interaction_count']}\n"
            f"正向/负向: {rel['positive_hits']}/{rel['negative_hits']}"
        )
        if style:
            text += f"\n平均句长: {style['avg_length']:.0f}字"
        return text

    if subcmd == "infer":
        group_key = _group_key(launcher_type, launcher_id)
        results = await plugin.infer_slang_with_llm(group_key)
        if not results:
            return "未推断出新黑话。请确认已配置 LLM 模型，且有足够高频词数据。"
        lines = ["🧠 黑话推断结果:"]
        for r in results:
            lines.append(f"• {r['word']} → {r['meaning']}")
        return "\n".join(lines)

    if subcmd == "graph":
        data = store.get_graph_data()
        type_counts: dict[str, int] = {}
        for node in data["nodes"]:
            t = node.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
        lines = [f"🕸️ 记忆图谱: {len(data['nodes'])} 节点, {len(data['edges'])} 边"]
        for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {t}: {c}")
        lines.append("完整可视化请打开 WebUI 侧边栏「记忆图谱」页面")
        return "\n".join(lines)

    return f"未知子命令: {subcmd}\n可用: status | slang | relation | infer | graph"
