#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
二游自动签到 · 主程序

支持：
  - 米游社系：原神 / 崩坏：星穹铁道 / 绝区零 / 崩坏3 / 崩坏学园2 / 未定事件簿 / 鹿鸣
  - 库街区：鸣潮 / 战双帕弥什

用法：
  python main.py                    # 用 config.json 跑全部账号
  python main.py -c my.json         # 指定配置文件
  python main.py --dry-run          # 只打印，不真签
  python main.py --only 主号        # 只跑某个账号
  python main.py --list             # 列出配置里的账号和游戏

定时（Windows 计划任务）：
  每天 8:00 跑一次：
  schtasks /create /tn "二游签到" /tr "python D:\\path\\main.py" /sc daily /st 08:00
"""

import os
import sys
import io as _io

# Windows 控制台默认 GBK，强制 UTF-8 避免中文/符号乱码
try:
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass
import json
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adapters


HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(HERE, "config.json")


def load_config(path):
    if not os.path.isfile(path):
        print("[!] 配置文件不存在: %s" % path)
        print("    复制 config.example.json 成 config.json 再填")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def print_result(name, results):
    total = len(results)
    okn = sum(1 for r in results if r["ok"])
    print("")
    print("=" * 56)
    print("  账号: %s    (%d/%d 成功)" % (name, okn, total))
    print("=" * 56)
    for r in results:
        flag = "[OK]" if r["ok"] else "[--]"
        print("  %s %-14s %s" % (flag, r["game"], r["msg"]))


def main():
    ap = argparse.ArgumentParser(description="二游社区自动签到")
    ap.add_argument("-c", "--config", default=DEFAULT_CONFIG, help="配置文件路径")
    ap.add_argument("--dry-run", action="store_true", help="只检查不签到")
    ap.add_argument("--only", default="", help="只跑指定账号名")
    ap.add_argument("--list", action="store_true", help="列出账号")
    ap.add_argument("--retry", type=int, default=2, help="失败重试次数（默认 2）")
    ap.add_argument("--json", default="", help="把结果写成 JSON 文件（便于监控）")
    args = ap.parse_args()

    cfg = load_config(args.config)
    accounts = cfg.get("accounts", [])

    if args.list:
        print("配置的账号：")
        for a in accounts:
            t = a.get("type", "?")
            games = a.get("games") or "全部"
            print("  - %-16s [%s]  games=%s" % (a.get("name", "?"), t, games))
        return

    if args.only:
        accounts = [a for a in accounts if a.get("name") == args.only]
        if not accounts:
            print("[!] 找不到账号: %s" % args.only)
            sys.exit(1)

    cfg["accounts"] = accounts

    print("")
    print("二游自动签到 · %s" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("账号数: %d%s" % (len(accounts), "  [DRY-RUN]" if args.dry_run else ""))

    retries = max(0, args.retry)
    all_results = {}
    for acc in accounts:
        name = acc.get("name") or acc.get("type", "unknown")
        attempt = 0
        last = None
        while attempt <= retries:
            try:
                r = adapters.run_all({"accounts": [acc]}, dry_run=args.dry_run)
                last = r.get(name) or []
                # 全部成功就不再重试
                if last and all(x.get("ok") for x in last):
                    break
            except Exception as e:
                last = [{"game": "-", "ok": False, "msg": "异常: %s" % e}]
            attempt += 1
            if attempt <= retries and not args.dry_run:
                import time as _t
                print("    [retry %d/%d] %s" % (attempt, retries, name))
                _t.sleep(3 * attempt)
        all_results[name] = last or []

    total_ok = 0
    total_all = 0
    for name, results in all_results.items():
        print_result(name, results)
        total_ok += sum(1 for r in results if r["ok"])
        total_all += len(results)

    print("")
    print("=" * 56)
    print("  汇总: %d / %d 项成功" % (total_ok, total_all))
    print("=" * 56)

    # 可选：写 JSON（给监控用）
    if args.json:
        try:
            import json as _json
            payload = {
                "time": datetime.now().isoformat(timespec="seconds"),
                "total": total_all,
                "ok": total_ok,
                "accounts": {},
            }
            for name, results in all_results.items():
                payload["accounts"][name] = [
                    {"game": r["game"], "ok": r["ok"], "msg": r["msg"]} for r in results
                ]
            with open(args.json, "w", encoding="utf-8") as f:
                _json.dump(payload, f, ensure_ascii=False, indent=2)
            print("  [json] %s" % args.json)
        except Exception as e:
            print("  [!] 写 JSON 失败: %s" % e)

    # 写日志
    logdir = os.path.join(HERE, "logs")
    os.makedirs(logdir, exist_ok=True)
    logfile = os.path.join(logdir, "sign_%s.log" % datetime.now().strftime("%Y%m%d"))
    try:
        with open(logfile, "a", encoding="utf-8") as f:
            f.write("\n[%s]\n" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            for name, results in all_results.items():
                f.write("  %s:\n" % name)
                for r in results:
                    f.write("    %s %s %s\n" % ("OK" if r["ok"] else "FAIL", r["game"], r["msg"]))
    except Exception as e:
        print("[!] 写日志失败: %s" % e)

    # 有失败就返回非 0（方便计划任务报警）
    sys.exit(0 if total_ok == total_all else 2)


if __name__ == "__main__":
    main()
