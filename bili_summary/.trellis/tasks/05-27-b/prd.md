# B站直播日报自动推送系统

## Goal

每日自动采集B站已关注UP主的直播信息（标题、弹幕词云、AI总结），通过多种渠道推送给用户，实现"错过了直播也能快速了解今天发生了什么"。

## What I already know

* 用户通过B站扫码或session cookie登录
* 登录后获取关注列表，用户可选择性将UP主加入"监控列表"
* 每天采集监控列表中UP主当天的直播信息
* 直播信息包括：标题、弹幕词云、AI总结
* 定时自动运行，推送日报
* 当前项目为全新初始化，无现有代码，语言/框架待定

## Assumptions (temporary)

* 使用 Python 作为主语言（生态成熟：bilibili-api、APScheduler、jieba/wordcloud）
* 单用户模式（个人使用，非SaaS）
* 推送渠道先做一个（后续扩展）
* 纯 CLI + 配置文件管理，不做 Web UI

## Decision (ADR-lite)

**关注列表管理**: YAML 配置文件为核心，CLI 命令辅助操作，两者都支持。
**AI 总结策略**: 词云统计默认开启，AI 总结作为可配置选项（不配 API key 就跳过）。
**Context**: 平衡功能完整性和使用成本。
**Consequences**: 需要设计可插拔的总结模块，词云和 AI 总结走不同 pipeline。

## Open Questions

（全部已解答）

## Requirements (evolving)

* B站登录（扫码/cookie），会话持久化
* 关注列表管理（白名单筛选，YAML配置文件 + CLI辅助管理，两者都支持）
* 定时采集直播信息（标题、人气、时长等）
* 弹幕采样采集 + 词云生成（默认开启）
* AI 直播内容总结（可选，统一 OpenAI SDK 格式，配置里切换模型/API key 即用）
* 日报推送（PushPlus，推送到微信）

## Acceptance Criteria (evolving)

* [ ] 能够通过扫码或cookie完成B站登录
* [ ] 能够获取并管理关注UP主列表
* [ ] 能够定时采集指定UP主的直播数据
* [ ] 能够生成包含标题、词云、总结的日报
* [ ] 能够通过至少一种渠道推送日报

## Definition of Done

* 代码可本地运行，定时任务正常工作
* 登录会话可持久化，不频繁要求重新登录
* 推送内容格式清晰可读

## Out of Scope (explicit)

* 多用户/SaaS 支持
* Web UI
* 实时开播/下播通知（MVP阶段不做）
* 历史直播回放检测

## Technical Notes

* 全新项目，无现有代码约束
* B站 API：bilibili-api-python 库覆盖了大部分接口
* 详见 research/ 目录下的调研文档

## Research References

* [`research/bilibili-api.md`](research/bilibili-api.md) — bilibili-api-python 支持扫码登录、关注列表、弹幕采集；SESSDATA cookie 约30天有效
* [`research/push-channels.md`](research/push-channels.md) — Telegram Bot 功能最优，企业微信/PushPlus 国内友好
* [`research/llm-summary.md`](research/llm-summary.md) — DeepSeek-V3 推荐（中文最优，月均~6元）；Qwen-Turbo 备选（月均~2元）
