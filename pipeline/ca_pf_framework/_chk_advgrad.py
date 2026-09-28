#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_advgrad.py --- 守卫：**所有驱动脚本的 `--adv` 默认值必须是 `proj2`**

为什么需要（`WINDOWB_ROADMAP_TO_CORRECT.md §9.11`，A3「改一半」陷阱第 3 例）
----------------------------------------------------------------------------
D17（2026-09-28，用户批准）把引擎 `LevelSetMulti.advance` 的默认平流格式
从 `central` 改成 `proj2`，理由是实测（球 + 常数驱动、同一物理半径）：
    central  `R/R_ex−1 = +4.16%`、粗糙度测度 **2.237**（**界面自发粗化**）
    proj2    `−0.54%`、**0.998**     ⇒ ★可用
随后 A3 做了一次"自述平流格式"的审计，结论是"**全仓只有 3 个诊断脚本显式传 central**"。
**但那次审计 grep 的是字面量 `adv_grad='central'`，漏掉了 CLI 默认值**：

    T16_verify_rve.py:242   ap.add_argument('--adv', default='central')
    T16_verify_rve.py:171   g.advance(..., adv_grad=adv)      ← 把引擎默认覆盖掉

⇒ 任何 `argparse` 默认值都可能**静默覆盖引擎默认**，而 `grep` 字面量看不见它。
本守卫把这件事变成**机械可查**的。

判据
----
  G-1 扫描 `ca_pf_framework/*.py` 里所有 `add_argument('--adv'...)` 与
      `add_argument('--adv-grad'...)`，报出 `default=` 的值；
  G-2 **任何不是 `'proj2'` 的默认值 ⇒ FAIL**（要复现 D17 之前的归档读数，必须**显式传参**，
      不得改默认）；
  G-3 **反向测试**（`AGENTS.md §3.4`：守卫必须反向测一次）：
      用 `--inject` 造一条 `default='central'` 的假输入，守卫**必须报 FAIL**。

用法：python3 _chk_advgrad.py [--root .] [--inject]
"""
import os
import re
import sys
import glob
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('--root', default=os.path.dirname(os.path.abspath(__file__)))
ap.add_argument('--inject', action='store_true',
                help='反向测试：注入一条 default=\'central\' 的假记录，守卫必须 FAIL')
a = ap.parse_args()

PAT = re.compile(r"add_argument\(\s*['\"]--adv(?:-grad)?['\"]\s*,\s*[^)]*?default\s*=\s*['\"]([^'\"]+)['\"]",
                 re.S)

rows = []
for f in sorted(glob.glob(os.path.join(a.root, '*.py'))):
    # ★ 排除自己：本文件的 docstring 里**引用**了 `default='central'` 作为反例，
    #   第一版没排除 ⇒ 守卫把自己判成 FAIL（假阳性）。这正说明"扫字面量"这种做法
    #   必须配一条"我知道哪些是引用、哪些是代码"的规则。
    if os.path.basename(f) == os.path.basename(__file__):
        continue
    try:
        t = open(f, encoding='utf-8', errors='replace').read()
    except Exception:
        continue
    for m in PAT.finditer(t):
        line = t[:m.start()].count('\n') + 1
        rows.append((os.path.basename(f), line, m.group(1)))

if a.inject:
    rows.append(('__INJECTED__.py', 1, 'central'))

print('=' * 92)
print('_chk_advgrad —— 守卫：驱动脚本的 `--adv` 默认值必须与 D17 一致（`proj2`）')
print('=' * 92)
print('\n【G-1】扫描到的 `--adv` / `--adv-grad` 默认值（%d 处）' % len(rows))
bad = []
for fn, ln, val in rows:
    tag = 'OK ' if val == 'proj2' else '**BAD**'
    if val != 'proj2':
        bad.append((fn, ln, val))
    print('   %-9s %-28s :%-5d default=%r' % (tag, fn, ln, val))

print('\n【G-2】非 `proj2` 的默认值 ⇒ %s' % ('**FAIL**' if bad else 'PASS（无）'))
for fn, ln, val in bad:
    print('   ⛔ %s:%d default=%r ⇒ 它会**静默覆盖**引擎的 proj2 默认' % (fn, ln, val))

print('\n【G-3】反向测试：%s' % ('（`--inject`）' if a.inject else '（未注入，跳过；用 --inject 跑一次）'))
if a.inject:
    print('   注入 `default=\'central\'` 后 ⇒ %s'
          % ('**FAIL（守卫有效）** ✅' if bad else '**仍然 PASS ⇒ 守卫失效** ⛔'))

print('\n' + '=' * 92)
print('结论：%s' % ('**PASS** —— 全部驱动的默认与 D17 一致' if not bad
                  else '**FAIL** —— %d 处默认值仍指向被 D17 弃用的格式' % len(bad)))
print('=' * 92)
sys.exit(1 if bad else 0)
