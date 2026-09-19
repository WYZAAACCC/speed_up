#!/usr/bin/env python3
"""
量 `op_num` 提上去的**离线代价**（不跑 MOOSE，不占 CPU）。

## 为什么要量

缺口 #2（形核→等轴晶）的**主要代价就在这里**：
`GrainTracker` 的 `reserve_op` 是**永久槽位**（B0a 实测），
⇒ `op_num ≥ 基体晶粒数 + 期望形核次数`。
而等轴晶区需要**很多**形核事件 ⇒ `op_num` 必须显著提高。

## 量什么

用**生产用的冻结非 AD 生成器**（`frozen/gen_aniso_nonad.py`）生成各 `op_num` 的
`aniso_block.i`，看：
  * 块大小、最长行（**L2a 的取向差对是 O(n²)**，会爆）
  * L2a / L2b 表达式的长度
  * 以及**拼进生产输入后的总规模**

⚠ 注意：`op_num > 13` 会越过 AD 的 `MOOSE_AD_MAX_DOFS_PER_ELEM=64` 上限 ——
**但生产是非 AD，不受这条限制**。AD 版才受限。
"""

import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

REPO = "/mnt/f/speed_up/pipeline"
WORK = "/root/work/opcost2"
PROBES = (8, 11, 14, 18, 22, 26, 30)

os.makedirs(WORK, exist_ok=True)
os.chdir(WORK)
subprocess.run(["cp", f"{REPO}/frozen/gen_aniso_nonad.py", "."], check=True)

print("  %-7s %-10s %-9s %-11s %-11s %-9s %s" %
      ("op_num", "块大小", "最长行", "L2a 长度", "L2b 长度", "变量数", "备注"))
print("  " + "-" * 74)
for n in PROBES:
    out = f"blk_{n}.i"
    r = subprocess.run(["python3", "gen_aniso_nonad.py", "--op-num", str(n), "--out", out],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(out):
        print("  %-7d 生成失败：%s" % (n, (r.stderr or "")[:40]))
        continue
    t = open(out, encoding="utf-8", errors="replace").read()
    size = len(t)
    maxl = max((len(x) for x in t.splitlines()), default=0)

    def expr_len(prop):
        m = re.search(rf"property_name = {prop}\b(.*?)\n\s*\[\]", t, re.S)
        if not m:
            return 0
        e = re.search(r"expression\s*=\s*'(.*?)'", m.group(1), re.S)
        return len(e.group(1)) if e else 0

    nvar = n + 3          # gr0..grN-1, c, w（T 是 AuxVariable，不入解向量）
    note = ""
    if nvar * 4 > 64:
        note = "AD 会超上限（生产非 AD，不受限）"
    print("  %-7d %-10d %-9d %-11d %-11d %-9d %s" %
          (n, size, maxl, expr_len("L2a"), expr_len("L2b"), nvar, note))

print()
print("  判读要点：")
print("    * **L2a 长度随 op_num 超线性增长**（取向差对是 O(n²)）——")
print("      这是形核路径的**主要代价**，不是自由度。")
print("    * 生产输入里 `[Kernels]` 与 `[Materials]` 的块数也随 op_num 线性增长。")
