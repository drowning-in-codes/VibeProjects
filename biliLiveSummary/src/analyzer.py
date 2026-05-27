"""分析模块: 词云生成 + AI总结"""

import os
import re
from datetime import date

import jieba
from wordcloud import WordCloud
from openai import OpenAI

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")

# 中文停用词
STOP_WORDS = set([
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些",
    "吗", "啊", "吧", "呢", "哦", "嗯", "哈", "哈哈", "哈哈哈",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
])


class LiveAnalyzer:
    def __init__(self, config: dict):
        self.config = config
        self.llm_config = config.get("llm", {})
        self._client = None
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    def _get_client(self):
        if self._client is None and self.llm_config.get("api_key"):
            self._client = OpenAI(
                api_key=self.llm_config["api_key"],
                base_url=self.llm_config.get("api_base", "https://api.deepseek.com/v1"),
            )
        return self._client

    def generate_wordcloud(self, live: dict, danmakus: list[str]) -> str | None:
        """生成词云图片，返回图片路径"""
        if not danmakus:
            return None

        text = " ".join(danmakus)
        words = jieba.cut(text)
        filtered = [w for w in words if len(w) > 1 and w not in STOP_WORDS]
        if not filtered:
            return None

        wc_text = " ".join(filtered)
        wc = WordCloud(
            width=800, height=400,
            background_color="white",
            font_path="C:/Windows/Fonts/msyh.ttc",  # 微软雅黑（Windows）
            max_words=100,
            collocations=False,
        )
        wc.generate(wc_text)

        filename = f"{date.today().isoformat()}_{live.get('uname', 'unknown')}_wordcloud.png"
        filepath = os.path.join(OUTPUT_DIR, filename)
        wc.to_file(filepath)
        return filepath

    def generate_summary(self, live: dict, danmakus: list[str]) -> str | None:
        """通过LLM生成直播内容总结"""
        client = self._get_client()
        if not client or not danmakus:
            return None

        sample = danmakus[:500]
        prompt = (
            f"直播标题: {live.get('title', '未知')}\n"
            f"弹幕样本 (共{len(sample)}条):\n" + "\n".join(sample[:200]) +
            "\n\n请用3-5句话总结这场直播的主要内容、观众反应和高光时刻。用中文输出。"
        )

        try:
            resp = client.chat.completions.create(
                model=self.llm_config.get("model", "deepseek-chat"),
                messages=[
                    {"role": "system", "content": "你是B站直播内容分析师，擅长从弹幕中提取关键信息。"},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=400,
                temperature=0.7,
            )
            return resp.choices[0].message.content
        except Exception as e:
            print(f"AI总结失败: {e}")
            return None

    def generate_report(self, lives: list[dict]) -> str:
        """生成日报文本"""
        today = date.today().isoformat()
        lines = [f"📺 B站直播日报 {today}", "━" * 24, ""]

        for i, live in enumerate(lives, 1):
            lines.append(f"{i}. [{live.get('uname', '未知')}] {live.get('title', '无标题')}")
            lines.append(f"   人气: {live.get('popularity', 0):,}")

            if live.get("summary"):
                lines.append(f"   总结: {live['summary']}")

            if live.get("wordcloud_path"):
                lines.append(f"   词云: {live['wordcloud_path']}")

            lines.append("")

        if not lives:
            lines.append("今日无主播开播")

        lines.append("━" * 24)
        return "\n".join(lines)
