#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_fix_engtlast.py —— 驱动层加 `--eng-t-last-reduce-nm` 并传给 `nuc_cfg`。"""
import io

P = '/mnt/f/speed_up/pipeline/ca_pf_framework/_bk_exp.py'
t = io.open(P, encoding='utf-8').read()

a = "    ap.add_argument('--eng-force-reinit', action='store_true',"
b = ("    # ★ R23：末片减薄（对齐驱动层 `_seed_next` 的 `T+o/2`）。默认 0 = 不减薄。\n"
     "    ap.add_argument('--eng-t-last-reduce-nm', type=float, default=0.0)\n"
     + a)
assert t.count(a) == 1
t = t.replace(a, b)

c = "                  force_reinit_after_event=(True if a.eng_force_reinit else None))"
d = ("                  force_reinit_after_event=(True if a.eng_force_reinit else None),\n"
     "                  t_last_reduce=a.eng_t_last_reduce_nm * 1e-9)")
assert t.count(c) == 1, t.count(c)
t = t.replace(c, d)

io.open(P, 'w', encoding='utf-8').write(t)
print('OK')
for i, ln in enumerate(t.split('\n'), 1):
    if 't_last_reduce' in ln:
        print(i, ln.strip()[:100])
