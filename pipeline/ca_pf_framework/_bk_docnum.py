#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_docnum.py —— 把闭环文档里**手打的数字**逐条与代码重算对照。

为什么需要：本仓库最贵的一课是"**文档里的数字会悄悄过期**"（kappa_c 只改了一半、
T7 的判读被自己的文档说服……）。闭环文档里凡是能算的数，都必须在交稿前重算一遍。
本脚本把文档 §1/§2/§7 里出现的数字抽出来，与 `windowB_closure` 的当前输出比对，
**不一致就报出来**（不自动改文档 —— 改文档要人看一眼）。
"""
import math
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import windowB_closure as CL                                    # noqa: E402

DOC = os.path.join(_HERE, 'BLOCK_PARAM_CLOSURE.md')
# ★ Round 19：把核对范围扩到**另外两份**结论文档 —— 它们的数字也是手打的，
#   而 `_bk_docnum` 原先只看闭环文档。`(路径, 是否查"过时写法")`。
DOCS = [(DOC, True),
        (os.path.join(_HERE, 'BLOCK_STATUS.md'), False),
        (os.path.join(_HERE, 'BLOCK_RESULT.md'), False)]


def main():
    rec = CL.recommend()
    txt = open(DOC, encoding='utf-8').read()
    all_txt = '\n'.join(open(p, encoding='utf-8').read()
                        for p, _ in DOCS if os.path.exists(p))
    # (文档里期望出现的字符串, 由代码算出的期望值, 说明)
    exp = []

    def add(s, why):
        exp.append((s, why))

    add('%.0f 步' % rec['steps_min'], 'C-3 算力下界')
    add('%.0f 步' % rec['steps'], 'C-3 实际步数')
    # ★ 冷速上界：文档里写的是 `2.98e6`（人不写 `e+06`）⇒ 人写的与机器写的都查一遍。
    #   （`%.3g` 给 `2.98e+06`、手写给 `2.98e6` ⇒ 去掉 `+0` 再比。）
    add(('%.3g' % rec['q_cap']).replace('e+0', 'e').replace('e-0', 'e-') + ' K/s',
        'C-3 冷速上界（%.4e）' % rec['q_cap'])
    add('%.0f nm' % rec['dx_nm'], 'Δx')
    add('%.2f' % rec['t_over_dx'], 't/Δx')
    add('%.2f' % rec['beta_h_use'], 'β_h')
    add('%.2f' % rec['beta_h_floor'], 'β_h 下界')
    add('%.2f' % rec['beta_h_T'], 'β_h(T) 运行均值')
    add('%.1f°' % CL.contact_angle_max(0.25, CL.DG_CRIT_REF, CL.M_S_TI64)[0],
        'C-1b 接触角门槛')
    add('%.4f' % CL.gamma_max_athermal(CL.DG_CRIT_REF, CL.M_S_TI64), 'C-1a γ 上限')
    add('%.4f' % CL.wetting_check(0.25, 5.0)['flip_gamma'], 'C-6 翻转阈值')
    add('%.1f' % CL.fcrit_ratio(0.25, 510e-9, CL.DG_CRIT_REF)[1], 'C-7 ΔG_v/f_crit')
    add('%.0f' % CL.barrier_ratio(0.25, CL.DG_CRIT_REF, CL.M_S_TI64), 'C-1a 势垒比')
    # ★ Round 19：C-1a 的三个数（全矩形上下端 / 倍数 / 数量级）
    _br = CL.barrier_ratio_range()
    add('%.0f' % _br['ratio_max'], 'C-1a ΔG*/kT 上端')
    add('%.1f' % _br['factor_max'], 'C-1a 倍数上端')
    add('%.0f' % _br['decades_max'], 'C-1a 数量级上端')

    print('=' * 100)
    print('文档里手打的数字 vs 代码重算')
    print('  闭环文档 = %s（另外两份只查"数字在不在"，不查过时写法）'
          % os.path.basename(DOC))
    print('=' * 100)
    bad = 0
    for s, why in exp:
        in_doc = s in txt
        in_any = s in all_txt
        if not in_any:
            bad += 1
        print('  %-14s %-22s %s'
              % (s, ('闭环文档' if in_doc else ('其它文档' if in_any
                                                else '**三份里都没有**')), why))

    # 另外几条：文档里的"扫描情景"数字必须与代码一致
    for a in (0.005, 0.011, 0.02):
        n = CL.n_lath_int(298.0, a)
        steps = int(math.ceil(CL.steps_min_ordered(a, 9 * 510e-9, 125e-9, 0.15,
                                                   298.0, CL.T_start_of_clock(a))
                              / 0.8 * 1.05))
        print('  α=%-6g ⇒ n=%2d，steps=%5d（换 α 时场数与步数都由代码定）' % (a, n, steps))

    # ★ 负对照：故意找**过时写法**。
    #   ⚠ 第一版写成"整篇搜 `42 条`" ⇒ **假阳性**：文档里有一句话是在
    #     *描述这次修正*（"它抓到 4 处：`42 条`→43、`7601 步`→6124…"），
    #     那句话里当然含有这些字符串。
    #     ⇒ 与仓库里记过四次的"读数口径"是同一类错：**要查的是"活的用法"，
    #       不是"字符串出现过"**。现在只查**只在数字过期时才会出现的整句**。
    stale_phrases = [
        '（由代码生成，42 条）',        # 更早的条数（两代之前）
        '（由代码生成，43 条）',        # 上一代的条数（加 3 条补登之后应过期）
        '完整 42 条见',                 # 参数条数过期时的引用
        '完整 43 条见',
        '需要 7601 步',                 # n=11 情景的旧步数（正确是 6124）
        'n = 11` 的敏感度情景需要 7601',  # 旧措辞整句
    ]
    for s in stale_phrases:
        if s in txt:
            bad += 1
            print('  ⚠ **发现过时写法**：%r 仍在文档里' % s)
    print('  （过时检查用的是"活的整句"，不是裸子串 —— 见本文件里的口径说明）')
    print('-' * 96)
    print('  不一致/过时项 = %d' % bad)
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
