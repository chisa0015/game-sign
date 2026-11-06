"""
真实接口连通性验证（用无效凭据测，验证 API 地址与错误处理）

预期结果：
  - 接口存在（不是 404）
  - 返回结构化 JSON（带 retcode / code）
  - 错误被正确识别为「凭据无效」
"""

import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, r"D:\DSK\richang\game-sign-repo")
import adapters
import skland
import tajiduo

FAKE_COOKIE = "ltuid_v2=100000000; ltoken_v2=deadbeefdeadbeefdeadbeefdeadbeef"
FAKE_UID = "100000000"
FAKE_CRED = "deadbeefdeadbeefdeadbeefdeadbeef"
FAKE_USERID = "100000000"
FAKE_TOKEN = "deadbeefdeadbeefdeadbeefdeadbeef"


def show(title, d):
    print("  %-12s" % title, end="")
    if not isinstance(d, dict):
        print("非 JSON:", str(d)[:100])
        return
    keys = [k for k in ("retcode", "code", "message", "msg") if k in d]
    if keys:
        parts = []
        for k in keys:
            v = d[k]
            if isinstance(v, str) and len(v) > 60:
                v = v[:60] + "…"
            parts.append("%s=%s" % (k, v))
        print(" | ".join(parts))
    else:
        print("keys:", list(d.keys())[:6])


print("=" * 70)
print("  真实接口连通性验证（无效凭据）")
print("=" * 70)

# ---------- 1. 米游社 ----------
print("\n[1] 米游社 — 原神签到接口")
try:
    d = adapters.mihoyo_sign(FAKE_COOKIE, "e202311201442471", FAKE_UID, "cn_gf01")
    show("原神 sign", d)
    if isinstance(d, dict):
        rc = d.get("retcode")
        if rc is None:
            print("    [!] 返回里没有 retcode，可能是接口变了")
        elif rc == 0:
            print("    [!] 假 cookie 居然返回成功？不可能")
        else:
            print("    [OK] 接口活着，凭据被拒（retcode=%s）" % rc)
except Exception as e:
    print("    [FAIL] 异常:", e)

print("\n[2] 米游社 — 崩铁签到接口")
try:
    d = adapters.mihoyo_sign(FAKE_COOKIE, "e202304121516551", FAKE_UID, "prod_gf_cn")
    show("崩铁 sign", d)
except Exception as e:
    print("    [FAIL] 异常:", e)

print("\n[3] 米游社 — 绝区零签到接口")
try:
    d = adapters.mihoyo_sign(FAKE_COOKIE, "e202406242138391", FAKE_UID, "prod_gf_cn")
    show("绝区零 sign", d)
except Exception as e:
    print("    [FAIL] 异常:", e)

# ---------- 2. 库街区 ----------
print("\n[4] 库街区 — 鸣潮签到接口")
try:
    d = adapters.kuro_sign(FAKE_USERID, FAKE_TOKEN, "3")
    show("鸣潮 sign", d)
    if isinstance(d, dict):
        c = d.get("code")
        print("    [OK] 接口活着，返回 code=%s" % c if c is not None else "    [!] 无 code 字段")
except Exception as e:
    print("    [FAIL] 异常:", e)

# ---------- 3. 森空岛 ----------
print("\n[5] 森空岛 — 明日方舟签到接口")
try:
    d = skland.skland_checkin(FAKE_CRED, 1)
    show("方舟 sign", d)
    if isinstance(d, dict):
        c = d.get("code")
        print("    [OK] 接口活着，返回 code=%s" % c if c is not None else "    [!] 无 code 字段")
except Exception as e:
    print("    [FAIL] 异常:", e)

print("\n[6] 森空岛 — 签名自检")
try:
    sig = skland._skland_sign("/api/v0/game/attendance", '{"gameId":1}', "1730000000")
    print("    sign =", sig)
    print("    [OK] 签名函数可执行" if len(sig) == 32 else "    [!] 签名长度异常")
except Exception as e:
    print("    [FAIL]", e)

# ---------- 4. 塔吉多 ----------
print("\n[7] 塔吉多 — refreshToken 接口")
try:
    d = tajiduo.tajiduo_refresh("deadbeef")
    show("refresh", d)
except Exception as e:
    print("    [FAIL] 异常:", e)

print("\n[8] 塔吉多 — 社区签到接口")
try:
    d = tajiduo.tajiduo_sign_community(FAKE_TOKEN)
    show("社区 sign", d)
except Exception as e:
    print("    [FAIL] 异常:", e)

print("\n" + "=" * 70)
print("  结论：能返回结构化 JSON = 接口地址正确，只是凭据无效")
print("=" * 70)
