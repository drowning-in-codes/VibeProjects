"""直播数据采集模块"""

from bilibili_api import sync, user, live


class LiveCollector:
    def __init__(self, auth):
        self.auth = auth

    def get_followings(self) -> list[dict]:
        """获取所有关注的UP主列表"""
        cred = self.auth.get_credential()
        if not cred:
            raise RuntimeError("未登录，请先执行 login 命令")

        u = user.User(cred.dedeuserid, credential=cred)
        followings = []
        page = 1
        while True:
            result = sync(u.get_followings(page=page, pn=20))
            for f in result.get("list", []):
                followings.append({
                    "uid": f.get("mid"),
                    "uname": f.get("uname"),
                })
            if len(result.get("list", [])) < 20:
                break
            page += 1
        return followings

    def get_live_status(self, uids: list[int]) -> list[dict]:
        """检测监控列表中哪些正在直播"""
        cred = self.auth.get_credential()
        if not cred:
            raise RuntimeError("未登录，请先执行 login 命令")

        lives = []
        for uid in uids:
            try:
                u = user.User(uid, credential=cred)
                info = sync(u.get_live_info())
                if info.get("live_status") == 1:
                    room_id = info.get("room_id")
                    room_info = sync(live.LiveRoom(room_id).get_room_info())
                    room_data = room_info.get("room_info", {})
                    lives.append({
                        "uid": uid,
                        "uname": room_data.get("uname", ""),
                        "room_id": room_id,
                        "title": room_data.get("title", ""),
                        "popularity": room_data.get("online", 0),
                        "start_time": room_data.get("live_start_time", ""),
                    })
            except Exception:
                continue
        return lives

    def collect_live_data(self, uids: list[int]) -> list[dict]:
        """采集直播数据（find live rooms for monitored UIDs）"""
        return self.get_live_status(uids)

    def collect_danmaku(self, room_id: int, max_count: int = 2000) -> list[str]:
        """采集直播间弹幕（通过历史弹幕接口）"""
        import math
        import time
        danmakus = []
        segment = 0
        while len(danmakus) < max_count:
            try:
                resp = sync(live.LiveDanmaku(room_id).get_danmaku_history(
                    page=1, segment=segment
                ))
                msgs = resp.get("admin", []) + resp.get("room", [])
                if not msgs:
                    break
                for m in msgs:
                    text = m.get("text", "").strip()
                    if text and text not in danmakus:
                        danmakus.append(text)
                        if len(danmakus) >= max_count:
                            break
                segment += 1
            except Exception:
                break
            time.sleep(0.5)
        return danmakus[:max_count]
