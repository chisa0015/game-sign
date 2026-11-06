"""
米游社 / 库街区 自动签到适配器

支持的账号类型：
  - mihoyo   : 米游社（原神 / 崩坏：星穹铁道 / 绝区零 / 崩坏3 / 崩坏学园2 / 未定事件簿 / 鹿鸣）
  - kuro     : 库街区（鸣潮 / 战双帕弥什）

凭据来源：
  mihoyo : 浏览器登录 https://www.mihoyo.com/ → F12 → Application → Cookies
           需要 ltuid / ltoken（新版叫 ltuid_v2 / ltoken_v2 也行）
  kuro   : 浏览器登录 https://www.kurobbs.com/ → F12 → Application → Cookies
           需要 userId / token
"""

import json
import time
import random
import hashlib
import urllib.request
import urllib.parse
from datetime import datetime

UA_MOBILE = (
    "Mozilla/5.0 (Linux; Android 12; SM-G9880) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/99.0.4844.88 Mobile Safari/537.36 miHoYoBBS/2.60.1"
)

# ============================================================
# 米游社
# ============================================================

# 各游戏的签到活动 ID（act_id）与默认分区
MIHOYO_GAMES = [
    {
        "key": "genshin",
        "name": "原神",
        "act_id": "e202311201442471",
        "default_region": "cn_gf01",
    },
    {
        "key": "starrail",
        "name": "崩坏：星穹铁道",
        "act_id": "e202304121516551",
        "default_region": "prod_gf_cn",
    },
    {
        "key": "zzz",
        "name": "绝区零",
        "act_id": "e202406242138391",
        "default_region": "prod_gf_cn",
    },
    {
        "key": "honkai3",
        "name": "崩坏3",
        "act_id": "e202207181446311",
        "default_region": "cn_qd01",
    },
    {
        "key": "honkai2",
        "name": "崩坏学园2",
        "act_id": "e202203291431091",
        "default_region": "cn_qd01",
    },
    {
        "key": "tears",
        "name": "未定事件簿",
        "act_id": "e202202251749321",
        "default_region": "cn_gf01",
    },
    {
        "key": "lumi",
        "name": "鹿鸣",
        "act_id": "e202205251409031",
        "default_region": "cn_gf01",
    },
]

MIHOYO_HEADERS_BASE = {
    "User-Agent": UA_MOBILE,
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://webstatic.mihoyo.com",
    "Referer": "https://webstatic.mihoyo.com/",
    "x-rpc-app_version": "2.60.1",
    "x-rpc-client_type": "5",
    "x-rpc-language": "zh-cn",
}

# 国际服的 salt（仅当用 os.hoyolab.com 时需要，这里留空）
SALT_CN = "t0qEgfub6cvMn8u2zKefZQ=="


def _mihoyo_headers(cookie, ds_token=None):
    h = dict(MIHOYO_HEADERS_BASE)
    h["Cookie"] = cookie
    if ds_token:
        h["DS"] = ds_token
    return h


def _http_post_json(url, payload, headers, timeout=20):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return {"retcode": -1, "message": "HTTP %d" % e.code}
    except Exception as e:
        return {"retcode": -1, "message": str(e)}


def _http_get_json(url, headers, timeout=20):
    req = urllib.request.Request(url, method="GET")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return {"retcode": -1, "message": "HTTP %d" % e.code}
    except Exception as e:
        return {"retcode": -1, "message": str(e)}


def mihoyo_list_roles(cookie):
    """列出这个 cookie 下绑定的所有米哈游账号（游戏角色）"""
    url = "https://api-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie?game_biz=hk4e_cn"
    # 用通用接口拿全部绑定
    url = "https://api-takumi-record.mihoyo.com/game_record/app/genshin/api/role/list"
    # 实际上更稳的是这个（返回所有游戏的绑定角色）
    url = "https://api-takumi.mihoyo.com/binding/api/getAllGameRoles"
    d = _http_get_json(url, _mihoyo_headers(cookie))
    if d.get("retcode") != 0:
        # 回退：老接口
        url2 = "https://api-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie?game_biz=hk4e_cn"
        d = _http_get_json(url2, _mihoyo_headers(cookie))
    return d


def mihoyo_sign(cookie, act_id, uid, region):
    """
    单个游戏签到
    POST /event/luna/sign
    返回：{"retcode":0,"message":"OK","data":{...}}
    """
    url = "https://api-takumi.mihoyo.com/event/luna/sign"
    payload = {
        "act_id": act_id,
        "region": region,
        "uid": str(uid),
        "lang": "zh-cn",
    }
    return _http_post_json(url, payload, _mihoyo_headers(cookie))


def mihoyo_sign_home(cookie, act_id, uid, region):
    """备用接口（home 版，部分活动只在这个上面）"""
    url = "https://api-takumi.mihoyo.com/event/luna/home"
    payload = {
        "act_id": act_id,
        "region": region,
        "uid": str(uid),
    }
    return _http_post_json(url, payload, _mihoyo_headers(cookie))


def mihoyo_day_state(cookie, act_id, uid, region):
    """查询今日是否已签到"""
    url = "https://api-takumi.mihoyo.com/event/luna/info"
    payload = {
        "act_id": act_id,
        "region": region,
        "uid": str(uid),
    }
    return _http_post_json(url, payload, _mihoyo_headers(cookie))


# ============================================================
# 库街区（鸣潮 / 战双）
# ============================================================

KURO_GAMES = [
    {"key": "wuthering", "name": "鸣潮", "gameId": "3"},
    {"key": "pgr", "name": "战双帕弥什", "gameId": "2"},
]

KURO_BASE = "https://api.kurobbs.com"


def kuro_headers(user_id, token):
    return {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 12; SM-G9880) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/99.0.4844.88 Mobile Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://web-static.kurobbs.com",
        "Referer": "https://web-static.kurobbs.com/",
        "Content-Type": "application/x-www-form-urlencoded",
        "source": "h5",
        "devCode": "",          # 新接口可能要，留空
        "Ip": "",
        "userId": str(user_id),
        "token": str(token),
    }


def kuro_sign(user_id, token, game_id):
    """库街区签到"""
    url = KURO_BASE + "/encourage/signIn/v2"
    payload = urllib.parse.urlencode({
        "gameId": str(game_id),
        "reqMonth": "%02d" % datetime.now().month,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    for k, v in kuro_headers(user_id, token).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return {"code": -1, "message": "HTTP %d" % e.code}
    except Exception as e:
        return {"code": -1, "message": str(e)}


def kuro_role_list(user_id, token):
    """库街区绑定的角色列表"""
    url = KURO_BASE + "/user/role/findRoleList"
    payload = urllib.parse.urlencode({"userId": str(user_id)}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    for k, v in kuro_headers(user_id, token).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        return {"code": -1, "message": str(e)}


# ============================================================
# 统一调度
# ============================================================

def run_mihoyo_account(acc, dry_run=False):
    """
    acc: {"type":"mihoyo","name":"主号","cookie":"ltuid=...; ltoken=...",
          "games":["genshin","starrail",...], "uid":..., "region":...}
    返回结果列表
    """
    results = []
    cookie = acc.get("cookie", "")
    if not cookie:
        return [{"game": "-", "ok": False, "msg": "缺少 cookie"}]

    want = acc.get("games")  # None = 全部
    fixed_uid = acc.get("uid")
    fixed_region = acc.get("region")

    for g in MIHOYO_GAMES:
        if want and g["key"] not in want:
            continue
        uid = fixed_uid or acc.get("uid_" + g["key"])
        region = fixed_region or acc.get("region_" + g["key"]) or g["default_region"]
        if not uid:
            results.append({
                "game": g["name"], "ok": False,
                "msg": "未配置 uid（在 config 里加 uid 或 uid_%s）" % g["key"],
            })
            continue
        if dry_run:
            results.append({"game": g["name"], "ok": True, "msg": "[dry-run] 跳过"})
            continue
        d = mihoyo_sign(cookie, g["act_id"], uid, region)
        rc = d.get("retcode", -99)
        msg = d.get("message", "")
        if rc == 0:
            results.append({"game": g["name"], "ok": True, "msg": "签到成功"})
        elif rc == -5003:
            results.append({"game": g["name"], "ok": True, "msg": "今天已经签过了"})
        else:
            results.append({"game": g["name"], "ok": False, "msg": "%s (%d)" % (msg, rc)})
        time.sleep(random.uniform(0.8, 2.0))
    return results


def run_kuro_account(acc, dry_run=False):
    results = []
    user_id = acc.get("userId") or acc.get("user_id")
    token = acc.get("token")
    if not user_id or not token:
        return [{"game": "-", "ok": False, "msg": "缺少 userId / token"}]

    want = acc.get("games")
    for g in KURO_GAMES:
        if want and g["key"] not in want:
            continue
        if dry_run:
            results.append({"game": g["name"], "ok": True, "msg": "[dry-run] 跳过"})
            continue
        d = kuro_sign(user_id, token, g["gameId"])
        ok = d.get("code") == 200 or d.get("success") is True
        msg = d.get("msg") or d.get("message") or ""
        if ok:
            results.append({"game": g["name"], "ok": True, "msg": "签到成功"})
        elif "已签" in str(msg) or "already" in str(msg).lower():
            results.append({"game": g["name"], "ok": True, "msg": "今天已经签过了"})
        else:
            results.append({"game": g["name"], "ok": False, "msg": "%s (%s)" % (msg, d.get("code"))})
        time.sleep(random.uniform(0.8, 2.0))
    return results


def run_all(config, dry_run=False):
    """跑所有账号，返回 {账号名: [结果]}"""
    out = {}
    for acc in config.get("accounts", []):
        name = acc.get("name") or acc.get("type", "unknown")
        t = acc.get("type", "")
        if t == "mihoyo":
            out[name] = run_mihoyo_account(acc, dry_run)
        elif t == "kuro":
            out[name] = run_kuro_account(acc, dry_run)
        elif t == "skland":
            try:
                import skland
                out[name] = skland.run_skland_account(acc, dry_run)
            except Exception as e:
                out[name] = [{"game": "-", "ok": False, "msg": "skland 适配器出错: %s" % e}]
        elif t == "tajiduo":
            try:
                import tajiduo
                out[name] = tajiduo.run_tajiduo_account(acc, dry_run)
            except Exception as e:
                out[name] = [{"game": "-", "ok": False, "msg": "tajiduo 适配器出错: %s" % e}]
        else:
            out[name] = [{"game": "-", "ok": False, "msg": "未知类型: %s" % t}]
    return out
