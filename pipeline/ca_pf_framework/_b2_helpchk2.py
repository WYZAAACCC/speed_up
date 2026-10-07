#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_b2_helpchk2.py —— 在**正确目录**里对照 `--help`（P24：负对照要有分辨力）。

## 为什么第一版无效
把 `_bk_exp.py` 拷到 `/tmp` 跑 ⇒ `ModuleNotFoundError: windowB_surface`
（模块按**脚本所在目录**找）⇒ 两个版本都在 import 阶段就死 ⇒ **测不到 `%d`**。
⇒ 本版**在原目录**里跑：先备份我的版本，换入原始版本，跑，再换回。
**任何一步失败都会换回我的版本**（不留下半改状态）。
"""
import os
import shutil
import subprocess
import sys

PY = "/root/miniconda3/envs/ml/bin/python"
FW = "/mnt/f/speed_up/pipeline/ca_pf_framework"
LIVE = os.path.join(FW, "_bk_exp.py")
MINE_BAK = "/tmp/b2_mine_bk_exp.py"
ORIG = "/tmp/b2_orig_bk_exp.py"

# 取原始版本
with open(ORIG, "w", encoding="utf-8") as fh:
    subprocess.run(["git", "-C", "/mnt/f/speed_up", "show",
                    "e4888f2e:pipeline/ca_pf_framework/_bk_exp.py"],
                   stdout=fh, check=True)
shutil.copy2(LIVE, MINE_BAK)          # 备份我的版本（含 B2 改动）


def run(label):
    p = subprocess.run([PY, "_bk_exp.py", "--help"], cwd=FW,
                       capture_output=True, text=True)
    err = (p.stderr or "").strip().splitlines()
    out = (p.stdout or "")
    return p.returncode, (err[-1] if err else "(无 stderr)"), len(out)


print("=" * 100)
print("对照：`_bk_exp.py --help`，**在正确目录**（%s）" % FW)
print("=" * 100)
try:
    # --- 原始 ---
    shutil.copy2(ORIG, LIVE)
    rc_o, e_o, n_o = run("ORIG")
    print("  ORIG rc=%-3d stdout=%-7d  %s" % (rc_o, n_o, e_o[:80]))
    # --- 我的 ---
    shutil.copy2(MINE_BAK, LIVE)
    rc_m, e_m, n_m = run("MINE")
    print("  MINE rc=%-3d stdout=%-7d  %s" % (rc_m, n_m, e_m[:80]))
finally:
    shutil.copy2(MINE_BAK, LIVE)      # ★ 无论如何换回我的版本
    print("\n  （已换回带 B2 改动的版本）")
print()
print("  ⇒ 判定：")
if rc_o != 0 and rc_m != 0:
    print("     两版**都** rc!=0 ⇒ `%d` 崩溃是**原有的**，**与 B2 无关**。")
elif rc_o != 0:
    print("     只有 ORIG 崩 ⇒ ⚠ 我的改动**修好了**它？需复查。")
elif rc_m != 0:
    print("     ⛔ 只有 MINE 崩 ⇒ **是我引入的**，必须修。")
else:
    print("     ✅ 两版都正常。")
