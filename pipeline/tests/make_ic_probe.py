#!/usr/bin/env python3
# =============================================================================
# 探测：初始条件本身有没有 η > 1？（把 gr*_max 的 execute_on 加上 initial）
# =============================================================================
# 【为什么要查这个】
#   粗网格烟测里 gr1..gr4_max 在**第一个时间步**就冲到 1.03~1.28。
#   在判读"越界是模型病还是离散病"之前，必须先排除**初值本身就越界**。
#   [ICs][PolycrystalColoringIC] 的 int_width=4 µm 在粗网格上是阶跃，
#   跨过晶界处可能给出 Ση ≠ 1。
#
#   源码里 gr*_max 只写了 execute_on = timestep_end（Gate 0 的已知坑：
#   t=0 那行全是 0，看起来像灾难性 bug）。这里只改这一项。
#
# 用法: python3 make_ic_probe.py <输入.i> <输出.i>
# =============================================================================
import io
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
s = io.open(src, encoding="utf-8").read()

n = 0
for i in range(8):
    name = "gr%d_max" % i
    # 定位该后处理器块，只改它自己那一行
    m = re.search(r"\[%s\]\n(.*?\n)\s*\[\]" % re.escape(name), s, re.S)
    if not m:
        sys.exit("找不到后处理器块 [%s]" % name)
    body = m.group(1)
    # ⚠ 源文件写的是 `execute_on = timestep_end`（**不带引号**）—— 不要假设有引号。
    new_body, k = re.subn(r"(execute_on = )'?timestep_end'?",
                          lambda mo: mo.group(1) + "'initial timestep_end'", body, count=1)
    if k != 1:
        sys.exit("[%s] 里没找到 execute_on = timestep_end" % name)
    s = s[:m.start(1)] + new_body + s[m.end(1):]
    n += 1

assert n == 8, n
io.open(dst, "w", encoding="utf-8", newline="").write(s)
print("已写 %s（改了 %d 个 gr*_max 的 execute_on）" % (dst, n))
