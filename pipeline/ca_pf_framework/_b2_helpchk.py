#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_b2_helpchk.py —— 判定 `_bk_exp.py --help` 的 `%d` 崩溃是不是**我引入的**。

## 方法（P24：负对照要有分辨力）
把两个版本的 `_bk_exp.py`（原始 `e4888f2e` 与我的改动版）**用同一条命令**跑 `--help`，
对照返回码。若**原始版本也崩** ⇒ **不是我引入的**。
"""
import os
import subprocess
import sys

PY = "/root/miniconda3/envs/ml/bin/python"
FW = "/mnt/f/speed_up/pipeline/ca_pf_framework"
TMP = "/tmp/b2help"
os.makedirs(TMP, exist_ok=True)


def run(which, src):
    dst = os.path.join(TMP, "chk_%s.py" % which)
    with open(src, encoding="utf-8") as fh:
        txt = fh.read()
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(txt)
    p = subprocess.run([PY, dst, "--help"], cwd=FW, capture_output=True, text=True)
    tail = (p.stderr or p.stdout).strip().splitlines()
    return p.returncode, tail[-1] if tail else "(no output)"


# 原始版本：从 git 取
orig = os.path.join(TMP, "orig.py")
if not os.path.exists(orig):
    with open(orig, "w", encoding="utf-8") as fh:
        subprocess.run(["git", "-C", "/mnt/f/speed_up", "show",
                        "e4888f2e:pipeline/ca_pf_framework/_bk_exp.py"],
                       stdout=fh, check=True)
mine = os.path.join(FW, "_bk_exp.py")
# 关掉备份文件干扰
print("=" * 92)
print("对照：`_bk_exp.py --help`（原始 vs 我的改动版）")
print("=" * 92)
for which, src in (("ORIG", orig), ("MINE", mine)):
    rc, last = run(which, src)
    print("  %-5s rc=%-3d  %s" % (which, rc, last[:88]))
print()
print("  ⇒ 若 ORIG 也 rc!=0 ⇒ **`%d` 崩溃是**原有的**，与 B2 无关**。")
