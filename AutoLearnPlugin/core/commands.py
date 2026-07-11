from __future__ import annotations

from dataclasses import dataclass

from core.store import LearnStore, _user_key, _group_key
from core.chart import generate_group_chart
from core.group_analyzer import analyze_group_with_llm


@dataclass
class LearnResult:
    text: str | None = None
    image_base64: str | None = None


async def run_learn_command(
    store: LearnStore,
    plugin,
    launcher_type: str,
    launcher_id: str | int,
    sender_id: str | int,
    params: list[str],
) -> LearnResult:
    subcmd = params[0].lower() if params else ""

    if subcmd in ("", "l"):
        summary = store.get_summary()
        traits = summary["personality"]
        return LearnResult(text=(
            "📚 自主学习概览\n"
            f"已处理消息: {summary['messages_processed']}\n"
            f"追踪用户: {summary['users_tracked']}\n"
            f"关系记录: {summary['relationships']}\n"
            f"黑话群组: {summary['slang_groups']}\n"
            f"记忆节点: {summary['graph_nodes']} / 边: {summary['graph_edges']}\n"
            f"人格: 温暖{traits['warmth']:.2f} 幽默{traits['humor']:.2f} "
            f"正式{traits['formality']:.2f} 共情{traits['empathy']:.2f} 好奇{traits['curiosity']:.2f}\n"
            "子命令: qfx | slang | relation | infer | graph"
        ))

    if subcmd == "qfx":
        if launcher_type != "group":
            return LearnResult(text="群分析图仅在群聊中可用，请在群里发送 !learn qfx")
        group_key = _group_key(launcher_type, launcher_id)
        analysis = await analyze_group_with_llm(plugin, group_key)
        if analysis.get("error"):
            return LearnResult(text=analysis["error"])
        try:
            image_b64 = generate_group_chart(analysis)
            return LearnResult(image_base64=image_b64)
        except Exception as e:
            return LearnResult(text=f"生成分析图失败: {e}")

    if subcmd == "status":
        return LearnResult(text=str(store.get_summary()))

    if subcmd == "slang":
        group_key = _group_key(launcher_type, launcher_id)
        items = store.get_top_slang(group_key, 10)
        if not items:
            return LearnResult(text="暂无足够数据推断群黑话（需要至少3次出现）")
        lines = [f"🔤 群 {launcher_id} 高频词 TOP{len(items)}:"]
        for i, item in enumerate(items, 1):
            meaning = item.get("meaning") or "待推断"
            lines.append(f"{i}. {item['word']} ×{item['count']} — {meaning}")
        return LearnResult(text="\n".join(lines))

    if subcmd == "relation":
        user_key = _user_key("person", sender_id)
        rel = store.get_relationship(user_key)
        if not rel:
            return LearnResult(text="暂无关系数据，多聊几句就有了~")
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
        return LearnResult(text=text)

    if subcmd == "infer":
        group_key = _group_key(launcher_type, launcher_id)
        results = await plugin.infer_slang_with_llm(group_key)
        if not results:
            return LearnResult(text="未推断出新黑话。请确认已配置 LLM 模型，且有足够高频词数据。")
        lines = ["🧠 黑话推断结果:"]
        for r in results:
            lines.append(f"• {r['word']} → {r['meaning']}")
        return LearnResult(text="\n".join(lines))

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
        return LearnResult(text="\n".join(lines))

    return LearnResult(text=f"未知子命令: {subcmd}\n可用: qfx | slang | relation | infer | graph")
