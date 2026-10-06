#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_freeze.py [--thaw] —— **冻结/解冻**所有与本次实验相关的进程（SIGSTOP / SIGCONT）。

## 为什么用 SIGSTOP 而不是杀
`SIGSTOP` 把进程**挂起**（状态 T），**不释放内存、不丢进度**；
`SIGCONT` 从**原处**继续。算例的 checkpoint/snapshot 全在盘上，但**进程内状态也保留**。

## 冻结哪些（白名单，不用 `pkill -f`，见 `AGENTS.md §3.10`）
  · `_bk_exp.py`  → 仿真引擎（重进程）
  · `_t11_cube2b.py` / `_t11_run_one.py` → 实验主控（会 fork 子进程；**先冻结父再冻结子**）
  · `_t11_watch.py` → 监控脚本（它只是采样，冻不冻无所谓，一并冻）
**不冻**系统 python（`networkd-dispatcher` / `unattended-upgrades` 等）。

## 记录
把 PID + 命令行 + 冻结时刻写到 `_w2_frozen.json` ⇒ 解冻时按它来。
"""
import json
import os
import signal
import sys
import time

REC = "/mnt/f/speed_up/_w2_frozen.json"
THAW = "--thaw" in sys.argv
PAT = ("_bk_exp.py", "_t11_cube2b.py", "_t11_run_one.py", "_t11_watch.py")
L = []


def live():
    out = []
    for pid in os.listdir('/proc'):
        if not pid.isdigit():
            continue
        try:
            raw = open('/proc/%s/cmdline' % pid, 'rb').read()
            st = open('/proc/%s/stat' % pid).read()
        except OSError:
            continue
        argv = [x.decode('utf-8', 'replace') for x in raw.split(b'\0') if x]
        line = ' '.join(argv)
        if not any(p in line for p in PAT):
            continue
        # stat 的第 3 个字段是状态（用 rfind(')') 避开括号里的空格）
        state = st[st.rfind(')') + 2]
        out.append((int(pid), line, state))
    return sorted(out)


if THAW:
    if not os.path.exists(REC):
        sys.exit("找不到 %s ⇒ 无法解冻" % REC)
    rec = json.load(open(REC))
    L.append("★ 解冻（SIGCONT），冻结时刻 = %s" % rec.get('time'))
    for it in rec['procs']:
        pid = it['pid']
        try:
            os.kill(pid, signal.SIGCONT)
            L.append("  → SIGCONT PID %d  %s" % (pid, it['cmd'][:80]))
        except OSError as e:
            L.append("  ✗ PID %d 已不存在（%s）—— 它可能已跑完或被杀" % (pid, e))
    time.sleep(3)
    L.append("\n  解冻后状态：")
    for pid, line, state in live():
        L.append("    PID %-7d 状态=%-2s  %s" % (pid, state, line[:80]))
    if not live():
        L.append("    （没有匹配进程 —— 请检查是否已跑完）")
else:
    procs = live()
    L.append("★ 冻结（SIGSTOP），时刻 = %s" % time.strftime('%F %T'))
    # **先冻结主控（父），再冻结引擎（子）**：避免父在冻结前又 fork 出新子
    order = sorted(procs, key=lambda t: (0 if ('_t11_' in t[1]) else 1))
    for pid, line, state in order:
        try:
            os.kill(pid, signal.SIGSTOP)
            L.append("  → SIGSTOP PID %-7d  %s" % (pid, line[:80]))
        except OSError as e:
            L.append("  ✗ PID %d 失败：%s" % (pid, e))
    time.sleep(2)
    L.append("\n  冻结后状态（`T` = 已暂停）：")
    for pid, line, state in live():
        L.append("    PID %-7d 状态=%-2s %s  %s"
                 % (pid, state, "✅已冻结" if state == 'T' else "⚠**未冻结**",
                    line[:74]))
    json.dump(dict(time=time.strftime('%F %T'),
                   procs=[dict(pid=p, cmd=c) for p, c, _ in procs]),
              open(REC, 'w'), ensure_ascii=False, indent=1)
    L.append("\n  冻结清单已写入 %s（解冻：`_t11_freeze.py --thaw`）" % REC)

print("\n".join(L))
