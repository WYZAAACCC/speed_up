#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_check_cmd.py —— 程序化检查生成的命令里 `--out/--tag` 在不在。"""
import _t11_prod_cmd as P

cmd, nv, nl = P.build({"tag": "t10PROD1", "out": "_exp/_bk_t5",
                       "pf_phi": "onfly"})
print(f"nv={nv}  laths={nl}  命令长度={len(cmd)}")
for key in ("--out", "--tag", "--pf-phi", "--burst-km", "--steps"):
    idx = [i for i, x in enumerate(cmd) if x == key]
    print(f"  {key:12} 出现 {len(idx)} 次", end="")
    if idx:
        print(f"  值 = {cmd[idx[0]+1]!r}")
    else:
        print("   ← **缺失**")
print("\n命令尾部 6 项：", cmd[-6:])
