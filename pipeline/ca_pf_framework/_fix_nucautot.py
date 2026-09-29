#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_fix_nucautot.py —— R28：引擎路径下**自动补厚度**（`t = t_nuc + overlap`）。

为什么：`eng12`（推荐配置）用的是 `--eng-t-nm 312.5`（= 250 + o），
而 `--eng-t-nm` 的默认是 250。若不做成自动，**最简命令行跑不出 `eng12`** ——
这正是"默认路径"必须自洽的地方。
判据：只在 `use_engine` 且 `--nuc-overlap-nm > 0` 时自动加上 `o`；
`--eng-t-nm` 显式给了 `> 250` 就用给的（向后兼容 `eng12` 的命令行）。
"""
import io

P = '/mnt/f/speed_up/pipeline/ca_pf_framework/_bk_exp.py'
t = io.open(P, encoding='utf-8').read()

a = "        g.nuc_cfg(a.eng_r_nm * 1e-9, a.eng_t_nm * 1e-9, gamma=0.15, n_init=0,"
b = ("        # ★ R28：**自动补厚度** —— 界面落在重叠区中面 ⇒ 每片被吃 `o/2`\n"
     "        #   （两侧被吃的片吃 `o`）⇒ 引擎路径下把 `o` 加回 `t_nuc`。\n"
     "        #   这样「只给 `--grow-stack`」的最简命令行也能复现 `eng12`。\n"
     "        _t_nuc = a.eng_t_nm * 1e-9\n"
     "        if use_engine and a.eng_t_nm <= 250.0 and a.nuc_overlap_nm > 0:\n"
     "            _t_nuc = (250.0 + a.nuc_overlap_nm) * 1e-9\n"
     "        g.nuc_cfg(a.eng_r_nm * 1e-9, _t_nuc, gamma=0.15, n_init=0,")
assert t.count(a) == 1
t = t.replace(a, b)

# 打印里也带上实际的 t，便于事后核对
c = "'；R=%.0f nm t=%.0f nm，咬入 %.1f nm，节奏 %s，seed=%d'"
d = "'；R=%.0f nm t=%.1f nm（**含自动补厚**），咬入 %.1f nm，节奏 %s，seed=%d'"
assert t.count(c) == 1
t = t.replace(c, d)
e = "          % (a.eng_r_nm, a.eng_t_nm, a.nuc_overlap_nm,"
f = "          % (a.eng_r_nm, _t_nuc * 1e9, a.nuc_overlap_nm,"
assert t.count(e) == 1
t = t.replace(e, f)

io.open(P, 'w', encoding='utf-8').write(t)
print('OK')
for i, ln in enumerate(t.split('\n'), 1):
    if '_t_nuc' in ln:
        print(i, ln.strip()[:96])
