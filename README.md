# VibeProjects

个人项目集合。

## 项目列表

| 项目 | 说明 | 技术栈 |
|---|---|---|
| [biliLiveSummary](./biliLiveSummary/) | B站直播日报自动推送系统 | Python, bilibili-api, SQLite |

### biliLiveSummary

每日自动采集B站关注UP主的直播信息（标题、弹幕词云、AI总结），通过 PushPlus 推送到微信。

```
biliLiveSummary/
├── main.py              # CLI 入口 (login/watch/run/schedule)
├── config.yaml          # 用户配置
├── src/
│   ├── auth.py          # 扫码/cookie登录
│   ├── collector.py     # 直播+弹幕采集
│   ├── analyzer.py      # 词云+AI总结
│   ├── notifier.py      # PushPlus推送
│   └── storage.py       # YAML+SQLite存储
└── requirements.txt
```
