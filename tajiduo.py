"""
塔吉多（异环）签到适配器

塔吉多 = 完美世界（Perfect World）的官方社区：https://www.tajiduo.com/
包含：**异环**（Neverness to Everness）

凭据获取：
  1. 手机登录塔吉多 App / 网页（老虎账号）
  2. 抓包 https://bbs-api.tajiduo.com/usercenter/api/login 的响应
  3. 复制 `refreshToken`（长期有效，会自动续期）
  4. 填到 config.json 的 tajiduo 账号里

签到两类：
  - 社区签到：POST https://bbs-api.tajiduo.com/apihub/api/signin
  - 游戏签到：POST https://bbs-api.tajiduo.com/apihub/awapi/sign

签名：塔吉多用 header 里的 accessToken，不需要额外签名（比森空岛简单）。
"""

import json
import time
import urllib.request
import urllib.parse

TAJIDUO_BASE = "https://bbs-api.tajiduo.com"

TAJIDUO_UA = (
    "Mozilla/5.0 (Linux; Android 12; SM-G9880) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/99.0.4844.88 Mobile Safari/537.36"
)

TAJIDUO_GAMES = [
    {"key": "nte", "name": "异环", "gameId": "1"},
]


def _post_json(url, payload, headers, timeout=20):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")[:200]
        except Exception:
            body = ""
        return {"code": e.code, "message": "HTTP %d %s" % (e.code, body)}
    except Exception as e:
        return {"code": -1, "message": str(e)}


def _auth_headers(access_token):
    return {
        "User-Agent": TAJIDUO_UA,
        "Accept": "application/json",
        "Authorization": access_token,
        "Origin": "https://www.tajiduo.com",
        "Referer": "https://www.tajiduo.com/",
    }


def tajiduo_refresh(refresh_token):
    """用 refreshToken 换新的 accessToken"""
    url = TAJIDUO_BASE + "/usercenter/api/refreshToken"
    return _post_json(url, {"refreshToken": refresh_token},
                      {"User-Agent": TAJIDUO_UA, "Content-Type": "application/json"})


def tajiduo_sign_community(access_token):
    """社区签到"""
    url = TAJIDUO_BASE + "/apihub/api/signin"
    return _post_json(url, {}, _auth_headers(access_token))


def tajiduo_sign_game(access_token, game_id="1"):
    """游戏签到"""
    url = TAJIDUO_BASE + "/apihub/awapi/sign"
    return _post_json(url, {"gameId": str(game_id)}, _auth_headers(access_token))


def tajiduo_sign_state(access_token, game_id="1"):
    """查询签到状态"""
    url = TAJIDUO_BASE + "/apihub/awapi/signin/state"
    return _post_json(url, {"gameId": str(game_id)}, _auth_headers(access_token))


def run_tajiduo_account(acc, dry_run=False):
    results = []
    rt = acc.get("refreshToken") or acc.get("refresh_token")
    at = acc.get("accessToken") or acc.get("access_token")

    if not rt and not at:
        return [{"game": "-", "ok": False, "msg": "缺少 refreshToken 或 accessToken"}]

    # dry-run：不碰网络
    if dry_run:
        return [
            {"game": "凭据", "ok": True, "msg": "[dry-run] 跳过刷新"},
            {"game": "社区签到", "ok": True, "msg": "[dry-run] 跳过"},
            {"game": "异环", "ok": True, "msg": "[dry-run] 跳过"},
        ]

    # 优先用 refreshToken 换新的
    if rt:
        d = tajiduo_refresh(rt)
        new_at = None
        if isinstance(d, dict):
            data = d.get("data") or {}
            new_at = data.get("accessToken") or data.get("token")
            if not new_at and isinstance(data.get("user"), dict):
                new_at = data["user"].get("accessToken")
        if new_at:
            at = new_at
            results.append({"game": "凭据", "ok": True, "msg": "refreshToken 刷新成功"})
        else:
            results.append({
                "game": "凭据", "ok": False,
                "msg": "refreshToken 刷新失败: %s" % ((d or {}).get("message") or d),
            })
            return results

    if not at:
        return [{"game": "-", "ok": False, "msg": "拿不到 accessToken"}]

    if dry_run:
        results.append({"game": "社区签到", "ok": True, "msg": "[dry-run] 跳过"})
        results.append({"game": "异环", "ok": True, "msg": "[dry-run] 跳过"})
        return results

    # 社区签到
    d = tajiduo_sign_community(at)
    ok = False
    msg = ""
    if isinstance(d, dict):
        code = d.get("code")
        msg = str(d.get("message") or d.get("msg") or "")
        ok = code in (0, 200) or d.get("success") is True
        if not ok and ("已签" in msg or "already" in msg.lower()):
            ok = True
            msg = "今天已经签过了"
    results.append({"game": "社区签到", "ok": ok, "msg": msg or "失败"})
    time.sleep(1.0)

    # 游戏签到
    want = acc.get("games")
    for g in TAJIDUO_GAMES:
        if want and g["key"] not in want:
            continue
        d = tajiduo_sign_game(at, g["gameId"])
        ok = False
        msg = ""
        if isinstance(d, dict):
            code = d.get("code")
            msg = str(d.get("message") or d.get("msg") or "")
            ok = code in (0, 200) or d.get("success") is True
            if not ok and ("已签" in msg or "already" in msg.lower()):
                ok = True
                msg = "今天已经签过了"
        results.append({"game": g["name"], "ok": ok, "msg": msg or "失败"})
        time.sleep(1.0)

    return results
