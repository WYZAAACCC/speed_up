#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_fix_nucmode.py —— R28：`--nuc-mode`（默认 auto）+ 引擎推荐默认值。

约束（**必须成立**）：
  * 所有**归档命令行**都带 `--nuc-every 30`（>0）⇒ `auto` 下走**驱动层** ⇒ **逐位不变**。
  * `--arm eng` ⇒ 仍走引擎（兼容）。
  * `--grow-stack` 且 `--nuc-every 0` ⇒ `auto` 下走**引擎**（= 新的默认行为）。
"""
import io

P = '/mnt/f/speed_up/pipeline/ca_pf_framework/_bk_exp.py'
t = io.open(P, encoding='utf-8').read()


def rep(a, b, n=1):
    global t
    assert t.count(a) == n, (t.count(a), a[:70])
    t = t.replace(a, b)


# 1) grow 的定义：把 use_engine 也纳入（use_engine 在下面定义，故这里只加一项）
rep("    grow = bool(a.grow_stack) or (a.arm == 'eng')",
    "    # ★ R28：**默认走引擎形核**（见下面的 `use_engine`）。\n"
    "    use_engine = (a.arm == 'eng') or (a.nuc_mode == 'engine') or (\n"
    "        a.nuc_mode == 'auto' and bool(a.grow_stack) and a.nuc_every <= 0)\n"
    "    grow = bool(a.grow_stack) or (a.arm == 'eng') or use_engine")

# 2) nuc_cfg 的触发条件
rep("    if a.arm == 'eng':\n        g.nuc_cfg(", "    if use_engine:\n        g.nuc_cfg(")

# 3) 引擎推荐默认值：elong / 末片减薄
rep("                  elong=(a.eng_elong if a.eng_elong > 1.0 else 1.0),\n"
    "                  along=(a_ax if a.eng_elong > 1.0 else None),",
    "                  elong=((a.eng_elong if a.eng_elong > 1.0\n"
    "                          else (a.plate_L / a.plate_W if use_engine else 1.0))),\n"
    "                  along=(a_ax if (a.eng_elong > 1.0 or use_engine) else None),")
rep("                  t_last_reduce=a.eng_t_last_reduce_nm * 1e-9)",
    "                  t_last_reduce=((a.eng_t_last_reduce_nm if a.eng_t_last_reduce_nm > 0\n"
    "                                  else (a.nuc_overlap_nm * 0.5 if use_engine else 0.0))\n"
    "                                 * 1e-9))")

# 4) 步进循环里的引擎形核调用
rep("        if (a.arm == 'eng') and it > 0 and a.eng_cadence >= 0:",
    "        if use_engine and it > 0 and a.eng_cadence >= 0:")

# 5) 诊断落盘
rep("    if a.arm == 'eng' and getattr(g, '_nuc', None) is not None:",
    "    if use_engine and getattr(g, '_nuc', None) is not None:")

# 6) n_eng_ev / _ed_dummy 的初始化注释里已说明；补 argparse
rep("    ap.add_argument('--eng-seed', type=int, default=11)",
    "    # ★★★ R28：**形核通道选择**。\n"
    "    #   `auto`（默认）：`--grow-stack` 且 `--nuc-every <= 0` ⇒ **引擎**；\n"
    "    #                     给了 `--nuc-every > 0` ⇒ **驱动层**。\n"
    "    #   ⇒ **所有归档命令行都带 `--nuc-every 30` ⇒ 逐位不变**；\n"
    "    #     而「只给 `--grow-stack`」这一新写法自动拿到**已验的引擎路径**。\n"
    "    ap.add_argument('--nuc-mode', default='auto',\n"
    "                    choices=['auto', 'driver', 'engine'])\n"
    "    ap.add_argument('--eng-seed', type=int, default=11)")

io.open(P, 'w', encoding='utf-8').write(t)
print('OK')
for i, ln in enumerate(t.split('\n'), 1):
    if 'use_engine' in ln or 'nuc-mode' in ln:
        print(i, ln.strip()[:96])
