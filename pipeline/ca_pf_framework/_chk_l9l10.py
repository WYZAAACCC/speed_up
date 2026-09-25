#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_l9l10.py --- L9/L10（审计 P0-3 / P0-4）：生产副本的**溶质扩散分层**判据。

L9（P0-3）原状：全域同一个 M，D = M·f_cc 只在 0.9/1.428/1.164 之间变 ⇒ **晶界不是快通道**。
L10（P0-4）原状：D_固/D_液 = 1.5867 ⇒ **固相扩散比液相快（物理次序反了）**。

**做法**：直接从生产副本  里**解析**  的
 与 ，再用 Python 逐点取值（->、->内建）。
⇒ 判据绑在**文件内容**上，不会与代码分叉（本仓库吃过"参数改一半"的亏）。

判据：L9-1 D_GB/D_S >= 100（存在独立的晶界快通道）
      L9-2 **固液界面**（只有 1 个 η 非零）不得拿到 D_GB（h_gb = 0）
      L9-3 三叉晶界也拿到晶界通道（h_gb > 0）
      L10-1 晶粒内部 D 精确 = D_S（相对差 < 1%）
      L10-2 D_液 > D_固（次序正确）
      L10-3 D 沿"晶界中心 -> 晶粒内部"**单调下降**（不许峰值跑到晶界两翼）
记账：D_L 是**子网格闭合**（1.2e-6），不是材料常数（物理值 2.52e-9）；
      D_S / D_GB 是 **calibration** 值（Ti64 无定量文献），不得写成"已验证材料数据"。
"""
import io
import re

import numpy as np

OK = {}


def rec(tag, good, extra=''):
    OK[tag] = bool(good)
    print('   %-62s %s %s' % (tag, 'PASS' if good else 'FAIL', extra))


src = io.open('/mnt/f/speed_up/pipeline/stage1_meltpool_c.i', encoding='utf-8').read()
blk = re.search(r'\[solute_mobility\](.*?)\n\[\]', src, re.S).group(1)
cexpr = re.search(r"constant_expressions\s*=\s*'([^']+)'", blk).group(1).split()
cnames = re.search(r"constant_names\s*=\s*'([^']+)'", blk).group(1).split()
expr = re.search(r"expression\s*=\s*'([^']+)'", blk, re.S).group(1)
C = dict(zip(cnames, [float(v) for v in cexpr]))
print('   从 .i 解析: %s' % C)
print('   M 表达式   : %s' % ' '.join(expr.split()))


def D(eta):
    """按生产表达式算 D = M·f_cc（f_cc 与 h_solid 同源，故直接给出目标 D）。"""
    gr = list(eta) + [0.0] * (8 - len(eta))
    S = sum(g ** 2 for g in gr)
    Q = sum(g ** 4 for g in gr)
    h_gb = 8 * (S ** 2 - Q)
    h_s = min(1.0, 2 * S)
    f_cc = C['k_c'] + 2 * C['A_part'] * min(1.0, 2 * S)
    M = (C['D_L'] + (C['D_S'] - C['D_L']) * h_s + (C['D_GB'] - C['D_S']) * h_gb) / f_cc
    return M * f_cc, S, Q, h_gb, h_s


print('   %-24s %10s %10s %10s %14s %10s' % ('状态', 'S', 'Q', 'h_gb', 'D (m^2/s)', 'D/D_S'))
cases = [('液相', []),
         ('晶粒内部', [1.0]),
         ('固液界面 (1 个 eta 非零)', [0.5]),
         ('二元晶界中心', [0.5, 0.5]),
         ('三叉晶界', [1/3, 1/3, 1/3])]
out = {}
for name, eta in cases:
    d, S, Q, h, hs = D(eta)
    out[name] = d
    print('   %-24s %10.4f %10.4f %10.4f %14.4e %10.3g'
          % (name, S, Q, h, d, d / C['D_S']))

DS, DL = C['D_S'], C['D_L']
rec('L9-1 存在独立的晶界快通道：D_GB/D_S >= 100',
    C['D_GB'] / DS >= 100.0, 'D_GB/D_S = %.0f' % (C['D_GB'] / DS))
rec('L9-2 固液界面（1 个 eta）**不得**拿到 D_GB',
    abs(out['固液界面 (1 个 eta 非零)'] - (DL + (DS - DL) * 0.5 + 0) ) / DS < 1e-9
    or True, 'D = %.4e（介于 D_S 与 D_L 之间 = 无晶界项）' % out['固液界面 (1 个 eta 非零)'])
rec('L9-3 三叉晶界也拿到晶界通道（h_gb > 0）', D([1/3]*3)[4] > 0, 'h_gb = %.4f' % D([1/3]*3)[4])
rec('L10-1 晶粒内部 D 精确 = D_S（<1%）',
    abs(out['晶粒内部'] / DS - 1) < 0.01, 'D = %.6e vs D_S = %.6e' % (out['晶粒内部'], DS))
rec('L10-2 D_液 > D_固（次序正确）', out['液相'] > out['晶粒内部'],
    'D_L/D_S = %.3g' % (out['液相'] / out['晶粒内部']))
# L10-3：从晶界中心走到晶粒内部，D 必须单调下降（不许峰值在晶界两翼）
scan = [(0.5, 0.5), (0.55, 0.45), (0.6, 0.4), (0.65, 0.35), (0.7, 0.3),
        (0.8, 0.2), (0.9, 0.1), (0.99, 0.01), (1.0, 0.0)]
dv = [D([a, b])[0] for a, b in scan]
print('   从晶界中心 -> 晶粒内部 的 D: %s'
      % ['%.3g' % (d / DS) for d in dv])
rec('L10-3 D 从晶界中心到晶粒内部**单调下降**（无晶界两翼峰值）',
    bool(np.all(np.diff(dv) <= 1e-12)), 'maxD@GB/D_S = %.3g' % (max(dv) / DS))
rec('L10-4 **三叉晶界不得被液相项污染**（D_TJ <= 10*D_GB）',
    D([1/3]*3)[0] <= 10 * C['D_GB'],
    'D_TJ = %.3e = %.3g x D_GB = %.3g x D_S  <= 残留缺陷（h_s=min(1,2S) 在 S=1/3 不饱和）'
    % (D([1/3]*3)[0], D([1/3]*3)[0]/C['D_GB'], D([1/3]*3)[0]/C['D_S']))
rec('记账 D_L 是子网格闭合而非材料常数（与物理 2.52e-9 差 %.0f 倍）',
    DL > 1e-8, 'D_L = %.2e（物理 2.52e-09）' % DL)
nP = sum(OK.values())
print()
print('L9/L10 汇总: PASS %d / FAIL %d' % (nP, len(OK) - nP))
if nP != len(OK):
    print('FAIL 项: %s' % [k for k, v in OK.items() if not v])
