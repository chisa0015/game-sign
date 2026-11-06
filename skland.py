"""
森空岛（SKLAND）签到适配器 — 明日方舟 / 来自星尘 / 终末地

森空岛是鹰角网络的官方社区：https://www.skland.com/

签到接口：
  POST https://zonai.skland.com/api/v0/game/attendance
  Headers:
    cred:      <登录凭据>
    sign:      <签名 = MD5(timestamp + path + body + salt)>
    timestamp: <unix 秒>
    platform:  1
    User-Agent: 森空岛 App UA
  Body: {"gameId": 1}

gameId:
  1 = 明日方舟
  2 = 来自星尘
  3 = 终末地

凭据怎么拿：
  1. 手机/模拟器登录森空岛 App
  2. 抓包得到 cred（或从 WebView 的 localStorage 里挖）
  3. 有效期约 30 天

签名 salt：森空岛用固定 salt（社区公开），本脚本内置一份，失效时替换即可。
"""

import time
import json
import hashlib
import urllib.request

# 森空岛固定 salt（社区公开值，若失效需重新逆向）
SKLAND_SALT = "6f4a1e7f8c3d9b2a5e0c4f7d1b8a3e6c"

SKLAND_GAMES = [
    {"key": "arknights", "name": "明日方舟", "gameId": 1},
    {"key": "exastris", "name": "来自星尘", "gameId": 2},
    {"key": "endfield", "name": "终末地", "gameId": 3},
]

SKLAND_UA = (
    "SKLand/1.0.1 (com.hypergryph.skland; build:1000014; Android 12; ) "
    "OkHttp/4.11.0"
)


def _skland_sign(path, body_str, timestamp):
    """sign = MD5(timestamp + path + body + salt)"""
    raw = "%s%s%s%s" % (timestamp, path, body_str, SKLAND_SALT)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def skland_headers(cred, path, body_str):
    ts = str(int(time.time()))
    return {
        "cred": cred,
        "sign": _skland_sign(path, body_str, ts),
        "timestamp": ts,
        "platform": "1",
        "User-Agent": SKLAND_UA,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def skland_checkin(cred, game_id):
    """
    签到单个游戏
    返回：{"code":0,"message":"OK","data":{...}}
    """
    path = "/api/v1/game/attendance"
    url = "https://zonai.skland.com" + path
    body_str = json.dumps({"gameId": int(game_id)}, separators=(",", ":"))
    headers = skland_headers(cred, path, body_str)

    req = urllib.request.Request(url, data=body_str.encode("utf-8"), method="POST")
    for k, v in headers.items():
        req.add_header(k, v)

    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")[:200]
        except Exception:
            pass
        return {"code": e.code, "message": "HTTP %d %s" % (e.code, body)}
    except Exception as e:
        return {"code": -1, "message": str(e)}


def skland_player_info(cred):
    """拿绑定的玩家信息（含各个游戏的 uid / 昵称）"""
    path = "/api/v1/game/player/info"
    url = "https://zonai.skland.com" + path
    body_str = ""
    headers = skland_headers(cred, path, body_str)
    req = urllib.request.Request(url, method="GET")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        return {"code": -1, "message": str(e)}


def run_skland_account(acc, dry_run=False):
    """主程序调用的入口"""
    results = []
    cred = acc.get("cred", "")
    if not cred:
        return [{"game": "-", "ok": False, "msg": "缺少 cred（森空岛登录凭据）"}]

    want = acc.get("games")  # None = 全部
    for g in SKLAND_GAMES:
        if want and g["key"] not in want:
            continue
        if dry_run:
            results.append({"game": g["name"], "ok": True, "msg": "[dry-run] 跳过"})
            continue
        d = skland_checkin(cred, g["gameId"])
        code = d.get("code")
        msg = d.get("message", "") or ""
        if code == 0:
            results.append({"game": g["name"], "ok": True, "msg": "签到成功"})
        elif "已签" in str(msg) or "already" in str(msg).lower() or code == 10001:
            results.append({"game": g["name"], "ok": True, "msg": "今天已经签过了"})
        elif code == 401 or "10002" in str(msg) or "未登录" in str(msg) \
                or "cred" in str(msg).lower() or "登录" in str(msg):
            results.append({"game": g["name"], "ok": False, "msg": "cred 失效，需重新抓包"})
        else:
            results.append({"game": g["name"], "ok": False, "msg": "%s (code=%s)" % (msg, code)})
        time.sleep(1.2)
    return results
