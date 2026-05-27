# B站 API 能力调研

## bilibili-api-python 库能力

- **仓库**: https://github.com/Nemo2011/bilibili-api
- **扫码登录**: 支持。`Credential` 类可生成二维码，用户扫码后获取 credential
- **Cookie 登录**: 支持。直接传入 `SESSDATA` 等关键 cookie 字段构造 `Credential`
- **获取关注列表**: `user.get_followings()` — 分页获取所有关注的UP主信息（UID、昵称）
- **获取直播间信息**: `live.LiveRoom(room_id).get_room_info()` — 标题、封面、人气、分区、开播状态
- **获取弹幕**: `live.LiveDanmaku(room_id)` 支持 WebSocket 实时连接获取弹幕流

## B站直播相关 API 端点

| 接口 | 说明 |
|---|---|
| `api.live.bilibili.com/room/v1/Room/get_info` | 直播间信息 |
| `api.live.bilibili.com/xlive/web-ucenter/user/following` | 关注的主播列表（含开播状态） |
| `api.live.bilibili.com/xlive/web-room/v1/dM/gethistory` | 历史弹幕（按时间戳） |
| `passport.bilibili.com/x/passport-login/web/qrcode/generate` | 生成登录二维码 |

## 弹幕采集方案

1. **WebSocket 实时采集** (推荐): `bilibili-api` 内置 `LiveDanmaku` 支持异步接收弹幕流，适合监控中的主播正在直播时实时抓取
2. **HTTP 采样轮询**: 对未实时监听的直播间，通过历史弹幕接口按时间范围分段拉取
3. **采集策略**: 每 5 分钟采样一批弹幕，足够做词云。每场直播采集 500-2000 条弹幕代表性即足够

## 登录态持久化

- **关键 Cookie**: `SESSDATA` (核心会话), `bili_jct` (CSRF token), `DedeUserID` (用户ID)
- **有效期**: `SESSDATA` 通常 30 天有效
- **持久化方案**:
  - 首次扫码登录后，将 credential 序列化到本地文件（如 `~/.blive/config.json`）
  - 启动时尝试从文件加载，验证是否过期
  - 过期后提示用户重新扫码
  - `bilibili-api` 的 `Credential` 对象支持 `from_cookies()` / `check_valid()` 方法

## 关键约束

- B站 API 有频率限制，单IP建议 QPS < 5
- 弹幕 WebSocket 连接需要房间号（room_id），而非 UID
- 关注列表接口需要登录态，需先完成认证
