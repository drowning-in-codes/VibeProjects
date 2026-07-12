"""
知乎人格蒸馏模块
使用 Claude API / 知乎直答 分析知乎内容 → 蒸馏人格 → 生成 SKILL.md
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from loguru import logger
from anthropic import Anthropic

from ..config import config
from ..storage.models import ZhihuContent, Persona
from ..storage.database import Database
from .client import ZhihuAPIClient, ZhihuChatClient
from .scraper import ZhihuScraper


# ═══════════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════════

@dataclass
class DistillerConfig:
    """蒸馏参数配置"""

    # 数据量控制
    content_limit: int = 50          # 爬取内容数量上限
    analyze_limit: int = 30          # 分析内容数量上限（传给 AI）
    min_content_length: int = 50     # 过滤太短的内容

    # AI 配置
    ai_provider: str = "claude"      # claude / zhihu_chat
    zhihu_chat_model: str = "thinking"  # fast / thinking / agent（仅 zhihu_chat）

    # 输出配置
    output_dir: str = "./skills"     # SKILL.md 输出目录
    include_examples: bool = True    # 是否包含原文示例
    max_examples: int = 5            # 最多示例数

    # 分析深度
    deep_analysis: bool = False      # 是否启用深度分析（两轮：一轮特征提取 + 一轮风格精炼）


# ═══════════════════════════════════════════════════════════════
# 蒸馏器
# ═══════════════════════════════════════════════════════════════

class ZhihuPersonaDistiller:
    """知乎人格蒸馏器 — 分析内容 → 提取特征 → 生成 SKILL.md"""

    def __init__(self, db: Database):
        self.db = db

        # Anthropic 客户端（支持代理）
        client_kwargs: dict = {"api_key": config.anthropic_api_key}
        if config.anthropic_base_url:
            client_kwargs["base_url"] = config.anthropic_base_url
            logger.info(f"使用自定义 Anthropic API: {config.anthropic_base_url}")
        http_client = config.get_httpx_client()
        if http_client:
            client_kwargs["http_client"] = http_client
        self.anthropic = Anthropic(**client_kwargs)

        # 知乎直答客户端（备选）
        access_secret = config.zhihu_access_secret
        self._zhihu_chat: Optional[ZhihuChatClient] = None
        if access_secret:
            self._zhihu_chat = ZhihuChatClient(access_secret)

    # ── 主入口：从用户蒸馏并生成 SKILL.md ────────────────────

    async def distill_and_generate(
        self,
        user_id: str,
        cfg: Optional[DistillerConfig] = None,
    ) -> Optional[str]:
        """
        一键蒸馏：搜索用户内容 → 分析特征 → 生成 SKILL.md

        Args:
            user_id: 知乎用户 ID 或名称
            cfg: 蒸馏配置

        Returns:
            SKILL.md 文件路径，失败返回 None
        """
        cfg = cfg or DistillerConfig()

        # Step 1: 收集内容
        contents = await self._collect_content(user_id, cfg)
        if not contents:
            logger.error(f"未找到 '{user_id}' 的内容")
            return None

        logger.info(f"收集到 {len(contents)} 条内容，开始蒸馏...")

        # Step 2: 提取人格
        persona_data = await self._distill(contents, cfg)

        # Step 3: 保存到数据库
        author_name = contents[0].author_name or user_id
        persona = Persona(
            username=f"zhihu_{user_id}",
            tone=persona_data.get("tone", ""),
            vocabulary=persona_data.get("vocabulary", []),
            topics=persona_data.get("topics", []),
            style_metrics=persona_data.get("style_metrics", {}),
            updated_at=datetime.now(),
        )
        await self.db.save_persona(persona)

        # Step 4: 生成 SKILL.md
        skill_path = self._write_skill_md(
            author_name=author_name,
            user_id=user_id,
            persona_data=persona_data,
            examples=[c.content[:300] for c in contents[: cfg.max_examples]] if cfg.include_examples else [],
            cfg=cfg,
        )

        logger.info(f"SKILL.md 已生成: {skill_path}")
        return skill_path

    async def distill_from_search(
        self,
        query: str,
        cfg: Optional[DistillerConfig] = None,
    ) -> List[str]:
        """
        从搜索关键词蒸馏：搜索 → 按作者聚合 → 逐个生成 SKILL.md

        Returns:
            生成的 SKILL.md 文件路径列表
        """
        cfg = cfg or DistillerConfig()

        access_secret = config.zhihu_access_secret
        if not access_secret:
            raise ValueError("未配置知乎 API 凭证")

        zclient = ZhihuAPIClient(access_secret)
        scraper = ZhihuScraper(self.db, zclient)
        contents = await scraper.search_and_collect(query, limit=cfg.content_limit)

        # 按作者分组
        author_map: Dict[str, List[ZhihuContent]] = {}
        for c in contents:
            key = c.author_name or c.author_id or "unknown"
            if key not in author_map:
                author_map[key] = []
            author_map[key].append(c)

        skill_paths = []
        for author_key, author_contents in author_map.items():
            if len(author_contents) < 3:
                continue

            author_id = author_contents[0].author_id or author_key
            persona_data = await self._distill(author_contents, cfg)

            persona = Persona(
                username=f"zhihu_{author_id}",
                tone=persona_data.get("tone", ""),
                vocabulary=persona_data.get("vocabulary", []),
                topics=persona_data.get("topics", []),
                style_metrics=persona_data.get("style_metrics", {}),
                updated_at=datetime.now(),
            )
            await self.db.save_persona(persona)

            skill_path = self._write_skill_md(
                author_name=author_key,
                user_id=author_id,
                persona_data=persona_data,
                examples=[c.content[:300] for c in author_contents[: cfg.max_examples]] if cfg.include_examples else [],
                cfg=cfg,
            )
            skill_paths.append(skill_path)
            logger.info(f"  完成: {author_key} → {skill_path}")

        return skill_paths

    # ── 内容收集 ────────────────────────────────────────────

    async def _collect_content(
        self, user_id: str, cfg: DistillerConfig
    ) -> Optional[List[ZhihuContent]]:
        """收集知乎用户内容"""
        access_secret = config.zhihu_access_secret
        if not access_secret:
            raise ValueError("未配置知乎 API 凭证")

        zclient = ZhihuAPIClient(access_secret)
        scraper = ZhihuScraper(self.db, zclient)
        contents = await scraper.collect_by_author(user_id, limit=cfg.content_limit)
        if contents:
            return contents

        # fallback: 搜索
        logger.info(f"collect_by_author 无结果，改用搜索")
        return await scraper.search_and_collect(user_id, limit=cfg.content_limit)

    # ── AI 蒸馏核心 ─────────────────────────────────────────

    async def _distill(
        self, contents: List[ZhihuContent], cfg: DistillerConfig
    ) -> Dict[str, Any]:
        """核心蒸馏逻辑"""
        # 预处理内容
        texts = self._prepare_texts(contents, cfg)

        # 第一轮：特征提取
        persona_data = await self._extract_features(texts, cfg)

        # 第二轮（可选）：深度精炼
        if cfg.deep_analysis:
            persona_data = await self._refine_style(persona_data, texts, cfg)

        return persona_data

    def _prepare_texts(
        self, contents: List[ZhihuContent], cfg: DistillerConfig
    ) -> List[str]:
        """预处理内容文本"""
        texts = []
        for c in contents[: cfg.analyze_limit]:
            title = c.title or ""
            body = c.content or ""
            full = f"{title}\n{body}"
            if len(full.strip()) >= cfg.min_content_length:
                texts.append(full)
        return texts

    async def _extract_features(
        self, texts: List[str], cfg: DistillerConfig
    ) -> Dict[str, Any]:
        """第一轮：提取写作风格特征"""
        prompt = self._build_extraction_prompt(texts)

        if cfg.ai_provider == "zhihu_chat" and self._zhihu_chat:
            result = self._zhihu_chat.ask(
                prompt,
                system_prompt="你是专业的写作风格分析专家。只返回 JSON，不要其他文本。",
                model=ZhihuChatClient.MODELS.get(cfg.zhihu_chat_model, cfg.zhihu_chat_model),
            )
            if result:
                return self._parse_json_safe(result)
            # fallback to claude

        return await self._call_claude(prompt)

    async def _refine_style(
        self, base: Dict[str, Any], texts: List[str], cfg: DistillerConfig
    ) -> Dict[str, Any]:
        """第二轮：深度精炼风格描述"""
        prompt = f"""
你是一位写作风格精炼专家。以下是对一位作者的初步分析结果和部分原文。

初步分析：
{json.dumps(base, ensure_ascii=False, indent=2)}

原始内容片段：
{chr(10).join([f'[例{i+1}] {t[:400]}' for i, t in enumerate(texts[:3])])}

请基于以上信息，进一步精炼分析，特别关注：
1. 作者在论证问题时偏好什么逻辑结构（归纳？演绎？类比？举例？）？
2. 开头和结尾是否有固定模式？
3. 是否有独特的修辞习惯（反问、设问、排比等）？
4. 对待不同观点时的态度（开放包容、坚决反对、理性分析等）？

请以 JSON 格式返回（合并原分析 + 精炼内容）：

{{
  "tone": "...",
  "vocabulary": ["...", "..."],
  "topics": ["...", "..."],
  "style_metrics": {{ ... }},
  "writing_patterns": {{
    "structure": "论证结构描述",
    "opening_style": "开头风格",
    "closing_style": "结尾风格",
    "rhetoric": ["修辞手法1", "修辞手法2"],
    "attitude": "对待观点的态度"
  }}
}}
"""
        if cfg.ai_provider == "zhihu_chat" and self._zhihu_chat:
            result = self._zhihu_chat.ask(prompt, system_prompt="只返回 JSON。")
            if result:
                return self._parse_json_safe(result)

        return await self._call_claude(prompt)

    # ── AI 调用 ─────────────────────────────────────────────

    async def _call_claude(self, prompt: str) -> Dict[str, Any]:
        """调用 Claude API"""
        message = self.anthropic.messages.create(
            model=config.anthropic_model,
            max_tokens=config.anthropic_max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._parse_json_safe(message.content[0].text)

    @staticmethod
    def _parse_json_safe(text: str) -> Dict[str, Any]:
        """安全的 JSON 解析"""
        text = text.strip()
        # 去掉可能的 ```json 包裹
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试提取 JSON 对象
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                return json.loads(m.group())
            raise

    # ── Prompt 构建 ─────────────────────────────────────────

    def _build_extraction_prompt(self, texts: List[str]) -> str:
        """构建特征提取 prompt"""
        sample = texts[:20]
        joined = "\n\n---\n\n".join(
            [f"[内容 {i+1}]\n{t[:600]}" for i, t in enumerate(sample)]
        )

        return f"""你是专业的写作风格分析专家。请分析以下 {len(sample)} 条知乎内容，提取作者的人格特征和写作风格。

内容：
{joined}

请以 JSON 格式返回（仅返回 JSON）：

{{
  "tone": "语气风格概述（50字以内）",
  "vocabulary": ["高频词1", "高频词2", "...（15-20个）"],
  "topics": ["擅长话题1", "擅长话题2", "...（最多5个）"],
  "style_metrics": {{
    "avg_length": 平均内容长度估算,
    "formality": 正式度评分(0-10),
    "humor_level": 幽默度评分(0-10),
    "technical_depth": 技术深度评分(0-10),
    "narrative_style": "叙事风格标签",
    "sentence_complexity": "句子复杂度：简短/中等/复杂",
    "use_of_analogy": "类比使用频率：很少/有时/经常",
    "emotional_tone": "情感基调：冷静/热情/批判/鼓励/..."
  }},
  "writing_patterns": {{
    "structure": "常用论证结构",
    "opening_style": "开头风格描述",
    "closing_style": "结尾风格描述",
    "rhetoric": ["修辞手法..."],
    "attitude": "对待不同观点的态度"
  }},
  "quintessence": "用一段话（100-150字）精炼概括这位作者的写作精髓和人格特质"
}}

分析要求：
1. 知乎内容通常比推文长，注重深度表达
2. 注意作者的论证逻辑、举例方式、引用习惯
3. 区分专业讨论和日常闲聊的语气差异
4. 关注特殊表达习惯、口头禅、使用频率高的句式
"""

    # ── SKILL.md 生成 ───────────────────────────────────────

    def _write_skill_md(
        self,
        author_name: str,
        user_id: str,
        persona_data: Dict[str, Any],
        examples: List[str],
        cfg: DistillerConfig,
    ) -> str:
        """生成 SKILL.md 文件"""
        output_dir = Path(cfg.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 安全文件名
        safe_name = re.sub(r"[^\w\-]", "_", author_name or user_id)
        file_path = output_dir / f"SKILL_{safe_name}.md"

        md = self._render_skill_md(author_name, user_id, persona_data, examples, cfg)

        file_path.write_text(md, encoding="utf-8")
        return str(file_path)

    def _render_skill_md(
        self,
        author_name: str,
        user_id: str,
        d: Dict[str, Any],
        examples: List[str],
        cfg: DistillerConfig,
    ) -> str:
        """渲染 SKILL.md 内容"""
        metrics = d.get("style_metrics", {})
        patterns = d.get("writing_patterns", {})
        vocab = d.get("vocabulary", [])
        topics = d.get("topics", [])
        quintessence = d.get("quintessence", "")

        # 格式化写作模式
        structure = patterns.get("structure", "无特定模式")
        opening = patterns.get("opening_style", "—")
        closing = patterns.get("closing_style", "—")
        rhetoric = patterns.get("rhetoric", [])
        attitude = patterns.get("attitude", "—")

        # 风格指标
        def m(key, default="—"):
            return metrics.get(key, default)

        lines: List[str] = []

        # 标题和元数据
        lines.append("---")
        lines.append(f"name: zhihu-{user_id}")
        lines.append(f"description: >")
        lines.append(f"  模仿知乎用户「{author_name}」的写作风格。{quintessence}")
        lines.append("metadata:")
        lines.append(f"  type: persona")
        lines.append(f"  source: zhihu")
        lines.append(f"  author: {author_name}")
        lines.append(f"  author_id: {user_id}")
        lines.append(f"  generated_at: {datetime.now().isoformat()}")
        lines.append(f"  distillation_count: {cfg.content_limit}")
        lines.append("---")
        lines.append("")

        # 人格画像
        lines.append(f"# 人格画像 — {author_name}")
        lines.append("")
        if quintessence:
            lines.append(f"> {quintessence}")
            lines.append("")
        lines.append(f"**语气风格**: {d.get('tone', '—')}")
        lines.append("")

        # 风格指标表
        lines.append("## 风格指标")
        lines.append("")
        lines.append("| 维度 | 评分 | 说明 |")
        lines.append("|------|------|------|")
        lines.append(f"| 正式度 | {m('formality')}/10 | — |")
        lines.append(f"| 幽默感 | {m('humor_level')}/10 | — |")
        lines.append(f"| 技术深度 | {m('technical_depth')}/10 | — |")
        lines.append(f"| 句子复杂度 | — | {m('sentence_complexity')} |")
        lines.append(f"| 类比频率 | — | {m('use_of_analogy')} |")
        lines.append(f"| 情感基调 | — | {m('emotional_tone')} |")
        lines.append(f"| 叙事风格 | — | {m('narrative_style')} |")
        lines.append(f"| 平均长度 | — | ~{m('avg_length')} 字 |")
        lines.append("")

        # 写作模式
        lines.append("## 写作模式")
        lines.append("")
        lines.append(f"- **论证结构**: {structure}")
        lines.append(f"- **开头风格**: {opening}")
        lines.append(f"- **结尾风格**: {closing}")
        lines.append(f"- **观点态度**: {attitude}")
        if rhetoric:
            lines.append(f"- **修辞手法**: {', '.join(rhetoric)}")
        lines.append("")

        # 话题
        if topics:
            lines.append("## 擅长话题")
            lines.append("")
            for t in topics:
                lines.append(f"- {t}")
            lines.append("")

        # 高频词汇
        if vocab:
            lines.append("## 高频词汇")
            lines.append("")
            lines.append("、".join(vocab))
            lines.append("")

        # 原文示例
        if examples:
            lines.append("## 原文示例")
            lines.append("")
            for i, ex in enumerate(examples, 1):
                trimmed = ex[:500].replace("\n", "\n> ")
                lines.append(f"### 示例 {i}")
                lines.append("")
                lines.append(f"> {trimmed}")
                lines.append("")

        # 模仿指南
        lines.append("## 模仿指南")
        lines.append("")
        lines.append(f"在模仿「{author_name}」的写作风格时，请注意：")
        lines.append("")
        lines.append(f"1. **语气基调**: {d.get('tone', '保持自然')}")
        if structure != "无特定模式":
            lines.append(f"2. **结构偏好**: {structure}")
        if rhetoric:
            lines.append(f"3. **修辞习惯**: 适当使用 {', '.join(rhetoric[:3])}")
        lines.append(f"4. **词汇选择**: 优先使用上述高频词汇中的表述")
        if topics:
            lines.append(f"5. **话题选择**: 集中在 {', '.join(topics[:3])} 等领域")
        lines.append(f"6. **长度控制**: 平均 ~{m('avg_length', '中等')} 字")
        lines.append("")

        return "\n".join(lines)
