#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_l10_4.py --- L10-4 判据（三叉线不得被液相项污染）+ 防漏判据。

做法：**直接解析** 生产副本 pipeline/stage1_meltpool_c.i 里
  [solute_hs] 的表达式  -> h_solid
  [solute_mobility] 的 expression / constant_expressions -> D 的合成式
再逐点求值。判据绑定在文件内容上（改文件就会被这条判据看见）。

判据：
  L10-4a 三叉线 D_TJ <= 10*D_GB（修好后应 = D_GB）
  L10-4b 二元晶界 D = D_GB ; 晶粒内 D = D_S ; 液相 D = D_L
  L10-4c 固液界面 h_gb = 0（不被误判成晶界）
  L10-4d D 从晶界中心到晶粒内单调下降
  L10-5  M 的分母与 f_loc 的 c 二阶导**同源**（防"改了 h_solid 忘改 f_cc"）
"""
import io
import re

import numpy as np

src = io.open('/mnt/f/speed_up/pipeline/stage1_meltpool_c.i', encoding='utf-8').read()
hs_expr = re.search(r"\[solute_hs\](.*?)\n\[\]", src, re.S).group(1)
HS_E = re.search(r"expression\s*=\s*'([^']+)'", hs_expr).group(1)
blk = re.search(r"\[solute_mobility\](.*?)\n\[\]", src, re.S).group(1)
cn = re.search(r"constant_names\s*=\s*'([^']+)'", blk).group(1).split()
cv = re.search(r"constant_expressions\s*=\s*'([^']+)'", blk).group(1).split()
MEX = ' '.join(re.search(r"expression\s*=\s*'([^']+)'", blk, re.S).group(1).split())
C = dict(zip(cn, [float(v) for v in cv]))
print('   从 .i 解析: %s' % C)
print('   h_solid : %s' % HS_E)
print('   M       : %s' % MEX)
OK = {}


def rec(tag, good, extra=''):
    OK[tag] = bool(good)
    print('   %-58s %s %s' % (tag, 'PASS' if good else 'FAIL', extra))


def ev(e, gr_subs):
    ee = e.replace('^', '**')
    for k, v in gr_subs.items():
        ee = ee.replace(k, '(%r)' % v)
    return float(eval(ee, {'min': min, 'max': max, 'pow': pow, 'abs': abs}))


def state(eta):
    gr = list(eta) + [0.0] * (8 - len(eta))
    sub = {'gr%d' % i: gr[i] for i in range(8)}
    S = sum(g ** 2 for g in gr)
    Q = sum(g ** 4 for g in gr)
    sub['S_eta1'] = sum(gr)
    sub['S_eta2'] = S
    sub['Q_eta4'] = Q
    h_gb = ev('8*(S_eta2^2 - Q_eta4)', sub)
    sub['h_gb'] = h_gb
    h_s = ev(HS_E, sub)
    sub['h_solid'] = h_s
    # D = M * f_cc，f_cc = k_c + 2*A_part*h_solid（与 f_loc 的 c 二阶导同源）
    f_cc = C['k_c'] + 2 * C['A_part'] * h_s
    sub.update({'D_L': C['D_L'], 'D_S': C['D_S'], 'D_GB': C['D_GB'],
                'k_c': C['k_c'], 'A_part': C['A_part']})
    M = ev(MEX, sub)
    return dict(D=M * f_cc, S=S, Q=Q, h_gb=h_gb, h_s=h_s, S1=sum(gr))


print('   %-26s %8s %8s %8s %13s %9s' % ('状态', 'SumEta', 'S', 'h_gb', 'D (m^2/s)', 'D/D_S'))
cases = [('液相', []), ('晶粒内部', [1.0]), ('固液界面(1 个 eta)', [0.5]),
         ('二元晶界中心', [0.5, 0.5]), ('三叉晶界', [1 / 3] * 3), ('四重点', [0.25] * 4)]
R = {}
for name, eta in cases:
    r = state(eta)
    R[name] = r
    print('   %-26s %8.4f %8.4f %8.4f %13.4e %9.3g'
          % (name, r['S1'], r['S'], r['h_gb'], r['D'], r['D'] / C['D_S']))
DS, DL, DG = C['D_S'], C['D_L'], C['D_GB']
rec('L10-4a 三叉线 D_TJ <= 10*D_GB（修好后应 = D_GB）',
    R['三叉晶界']['D'] <= 10 * DG,
    'D_TJ = %.3e = %.3g x D_GB = %.3g x D_S' % (R['三叉晶界']['D'],
                                                R['三叉晶界']['D'] / DG, R['三叉晶界']['D'] / DS))
rec('L10-4a2 四重点同样不被污染', R['四重点']['D'] <= 10 * DG,
    'D = %.3g x D_GB' % (R['四重点']['D'] / DG))
rec('L10-4b 二元晶界 D = D_GB（<1%）',
    abs(R['二元晶界中心']['D'] / DG - 1) < 0.01, 'D = %.4e' % R['二元晶界中心']['D'])
rec('L10-4b2 晶粒内部 D = D_S（<1%）',
    abs(R['晶粒内部']['D'] / DS - 1) < 0.01, 'D = %.4e' % R['晶粒内部']['D'])
rec('L10-4b3 液相 D = D_L（<1%）', abs(R['液相']['D'] / DL - 1) < 0.01,
    'D = %.4e' % R['液相']['D'])
rec('L10-4c 固液界面 h_gb = 0', R['固液界面(1 个 eta)']['h_gb'] == 0.0,
    'h_gb = %.3g ; h_s = %.4f' % (R['固液界面(1 个 eta)']['h_gb'],
                                  R['固液界面(1 个 eta)']['h_s']))
scan = [(0.5, 0.5), (0.6, 0.4), (0.7, 0.3), (0.8, 0.2), (0.9, 0.1), (1.0, 0.0)]
dv = [state([a, b])['D'] for a, b in scan]
print('   GB -> 晶粒内 的 D/D_S: %s' % ['%.3g' % (d / DS) for d in dv])
rec('L10-4d D 从晶界中心到晶粒内单调下降', bool(np.all(np.diff(dv) <= 1e-12)),
    'max/D_S = %.3g' % (max(dv) / DS))
# L10-5：M 的分母必须含 2*A_part*h_solid（或同源的 min(1,S_eta1)^2）
den_ok = ('2*A_part' in MEX) and (('min(1, S_eta1)^2' in MEX) or ('h_solid' in MEX))
rec('L10-5 M 的分母与 f_loc 的 c 二阶导同源（防漏改 f_cc）', den_ok,
    '分母含 2*A_part 且用同一 h_solid 指示')
# L10-6：h_solid 在固相处处 = 1（含三叉线/四重点）
hs_all = [R[k]['h_s'] for k in ('晶粒内部', '二元晶界中心', '三叉晶界', '四重点')]
rec('L10-6 固相指示在晶内/二元晶界/三叉线/四重点**处处 = 1**',
    bool(np.allclose(hs_all, 1.0, atol=1e-12)), 'h_s = %s' % hs_all)
nP = sum(OK.values())
print()
print('L10-4 汇总: PASS %d / FAIL %d' % (nP, len(OK) - nP))
if nP != len(OK):
    print('FAIL 项: %s' % [k for k, v in OK.items() if not v])
