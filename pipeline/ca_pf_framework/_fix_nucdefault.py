#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_fix_nucdefault.py —— R28：把 `--nuc-every` 的默认从 30 改成 0。

效果：**「只给 `--grow-stack`」= 引擎形核的块（新默认）**；
要复现归档的驱动层行为，显式传 `--nuc-every 30`。
**所有归档命令行都显式传了 30** ⇒ 不受影响（可逐条核对 `_exp/*/meta.json` 的 `exp_args`）。
"""
import io

P = '/mnt/f/speed_up/pipeline/ca_pf_framework/_bk_exp.py'
t = io.open(P, encoding='utf-8').read()

a = "    ap.add_argument('--nuc-every', type=int, default=30)"
b = ("    # ★★★ R28：**默认 0 = 形核交给引擎**（新默认）。\n"
     "    #   要复现归档的**驱动层**行为，显式传 `--nuc-every 30`。\n"
     "    #   **归档命令行全部显式传了 30**（见各臂 `meta.json` 的 `exp_args`）\n"
     "    #   ⇒ 它们的行为**逐位不变**。\n"
     "    ap.add_argument('--nuc-every', type=int, default=0)")
assert t.count(a) == 1
t = t.replace(a, b)
io.open(P, 'w', encoding='utf-8').write(t)
print('OK')
for i, ln in enumerate(t.split('\n'), 1):
    if 'nuc-every' in ln and 'add_argument' in ln:
        print(i, ln.strip()[:96])
