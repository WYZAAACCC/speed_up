#!/usr/bin/env python3
"""把 ctrl/front1d.i 转成「eta 冻结」的控制算例 ctrl2/front1d.i。

目的：判别 k_eff 偏离平衡值 0.6303 是不是**变分耦合**造成的
      （eta 真变量时 A*c^2*eta^2 同时进 c 与 eta 两个方程 ⇒ 互相反馈；
        冻结 eta 后就是 verify_partition 那种单向耦合）。

做法：删掉 eta 的三个核，把 eta 从 Variables 挪到 AuxVariables，用 FunctionAux 钉住。
"""
import io
import re
import sys

SRC = "/root/work/g1/ctrl/front1d.i"
DST = "/root/work/g1/ctrl2/front1d.i"

s = io.open(SRC, encoding="utf-8").read()

# --- (a) 删掉 eta 的三个核 ---
lines = s.split("\n")
out, skip, removed = [], False, 0
for L in lines:
    t = L.strip()
    if t.startswith("[") and t.strip("[]") in ("eta_dot", "eta_bulk", "eta_iface"):
        skip = True
    if skip:
        removed += 1
        if t == "[]":
            skip = False
        continue
    out.append(L)
s = "\n".join(out)
assert removed > 0, "没找到 eta 的核"

# --- (b) eta 从 Variables 挪到 AuxVariables ---
before = s
s = s.replace("\n[Variables]\n  [eta]\n  []\n  [c]", "\n[Variables]\n  [c]", 1)
assert s != before, "Variables 里的 eta 没删掉"

AUX = (
    "\n[AuxVariables]\n"
    "  [eta]\n"
    "  []\n"
    "[]\n"
    "\n"
    "[AuxKernels]\n"
    "  [eta_fix]\n"
    "    type = FunctionAux\n"
    "    variable = eta\n"
    "    function = eta_ic\n"
    "    execute_on = 'initial timestep_end'\n"
    "  []\n"
    "[]\n"
    "\n"
)

# 只在**行首**的 [Functions] 块头前插入（避免匹配到注释里的 "[Functions]"）
new_s, n = re.subn(r"^\[Functions\]", AUX + "[Functions]", s, count=1, flags=re.M)
assert n == 1, "插入 AuxVariables 失败"
s = new_s

# --- (c) 删掉 eta 的 FunctionIC ---
old_ic = (
    "  [eta_ic]\n"
    "    type = FunctionIC\n"
    "    variable = eta\n"
    "    function = eta_ic\n"
    "  []\n"
)
assert old_ic in s, "找不到 eta 的 FunctionIC"
s = s.replace(old_ic, "", 1)

io.open(DST, "w", encoding="utf-8", newline="").write(s)
print("已写 %s" % DST)
print("  删除 eta 核：%d 行" % removed)

# --- 自检 ---
chk = io.open(DST, encoding="utf-8").read()
assert "type = AllenCahn" not in chk, "AllenCahn 还在"
assert "[Variables]\n  [c]" in chk, "Variables 结构不对"
assert "[AuxVariables]\n  [eta]" in chk, "AuxVariables 没插好"
assert "type = FunctionIC\n    variable = eta" not in chk, "FunctionIC 还在"
print("  自检通过：eta 已冻结，无核引用它")
