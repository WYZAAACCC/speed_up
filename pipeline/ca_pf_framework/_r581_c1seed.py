#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_c1seed.py --- ★ C1 的**另一半**：位点**可复现**吗？

## 探针发现（读代码，`windowB_surface.py:1542`）
`def nuc_cfg(self, R_nuc, t_nuc, ..., seed=11, ...)` —— **`seed` 的默认值是硬编码的 11**，
而 `_bk_exp.py` **从头到尾没有传 `seed`** ⇒
**所有算例的形核 RNG 种子都是 11** ⇒
**初始位点序列应当是"确定性"的（不只是可复现）。**

## 但有一个陷阱（`windowB_surface.py:1980/2002/2218`）
`c['sites']` 在运行中会被 **`sites_refill` / `attach`** 追加/改写
⇒ **落盘的 `sites` = 初始 6 个 + 运行中补给/消费的结果** ⇒
**不能整表比**，只能比**前 `--nuc-init` 个**（那一段是纯 `_nuc_place_initial` 的产物）。

## 判据（**预先写死**）
* **R1**：两个臂的 `sites` **前 `n_init` 项**必须**逐位相同**（同一个坐标、同一个场号）。
* **R2**（**负对照，必须能失败**）：把其中一个臂的 `sites` 人为**打乱一项** ⇒ R1 必须判"不同"。
* **R3**：`nuc_cfg` 里**没有** `seed` 键 ⇒ 说明 CLI 没传 ⇒ 用的是硬编码 11
  （**这是"确定性"的直接证据，也说明"由 CLI 记录的 seed 复现"这句话目前的实现是"更死"的版本**）。
"""
import json
import os
import sys

R = '_exp/_bk_p2'


def load(tag):
    d = os.path.join(R, 'dry_' + tag)
    p = os.path.join(d, 'nuc_dbg.json')
    if not os.path.exists(p):
        return None, None
    return json.load(open(p, encoding='utf-8')), json.load(
        open(os.path.join(d, 'meta.json'), encoding='utf-8'))


def sites_of(j):
    return [(int(k), tuple(round(float(z), 15) for z in v))
            for k, v in j.get('nuc_cfg', {}).get('sites', [])]


def main():
    tags = sys.argv[1:] or ['p2_b5', 'p2_b3']
    L = ['=' * 96, 'R581 —— C1 的另一半：位点**可复现**吗？', '=' * 96]
    data = {}
    for t in tags:
        j, m = load(t)
        if j is None:
            L.append('★ %s：（没有 nuc_dbg.json）' % t); continue
        cfg = j.get('nuc_cfg', {})
        st = sites_of(j)
        data[t] = (cfg, st)
        L.append('★ %s' % t)
        L.append('   `nuc_cfg` 里有 `seed` 键吗？ **%s**'
                 % ('有 = %s' % cfg.get('seed') if 'seed' in cfg
                    else '**没有** ⇒ CLI 未传 ⇒ 用的是 `nuc_cfg(seed=11)` 的硬编码默认值'))
        L.append('   `--nuc-init` = %s（决定初始位点个数）'
                 % (m.get('exp_args', {}).get('nuc_init')))
        L.append('   落盘的 `sites` 共 **%d** 项（= 初始 + 运行中 refill/attach 的结果）' % len(st))
        L.append('   前 6 项：')
        for k, v in st[:6]:
            L.append('     场 %-4d (%.12f, %.12f, %.12f) µm' % (k, v[0] * 1e6, v[1] * 1e6, v[2] * 1e6))
    L.append('')
    L.append('=' * 96)
    if len(data) < 2:
        L.append('⚠ 少于两个臂 ⇒ 无法做复现判据（**如实登记，不硬给结论**）')
        print('\n'.join(L)); return 2
    (c1, s1), (c2, s2) = list(data.values())[0], list(data.values())[1]
    t1, t2 = list(data.keys())[0], list(data.keys())[1]
    # ★★★ **第一版判据错了（留痕）**：我写 `s1[:6] == s2[:6]`，而两个臂落盘的
    #   `sites` **长度不同**（b5 4 项、b3 5 项 —— 因为运行中 refill/attach 消费的个数不同）
    #   ⇒ **切片长度不同 ⇒ 列表恒不相等 ⇒ 判据恒判"不同"**，
    #   而实际**前 4 项逐位相同**（场 24/29/39/15 连同 12 位小数的坐标）。
    # ⇒ 正确的判据是**公共前缀**：`s[:m] == s2[:m]`，`m = min(len1, len2)`。
    #   （`_nuc_place_initial` 一次撒 `n_init` 个；落盘的是"初始 + 运行中补给"的总表，
    #     所以只能比**公共前缀**，不能比全表、也不能比固定长度。）
    m = min(len(s1), len(s2))
    a, b = s1[:m], s2[:m]
    L.append('── R1：`sites` 的**公共前缀**（%d 项）必须逐位相同 ──' % m)
    L.append('   %s：共 %d 项；%s：共 %d 项' % (t1, len(s1), t2, len(s2)))
    L.append('   ⚠ 记账：落盘的 `sites` = **初始 `n_init` 个 + 运行中 refill/attach 的结果**')
    L.append('     ⇒ 两个臂的**总长可以不同**（消费个数不同）⇒ **只能比公共前缀**。')
    L.append('   %s 前 %d 项场号 = %s' % (t1, m, [k for k, _ in a]))
    L.append('   %s 前 %d 项场号 = %s' % (t2, m, [k for k, _ in b]))
    same = (m > 0 and a == b)
    L.append('   ⇒ %s' % ('✅ **逐位相同（含 12 位小数的坐标）⇒ 初始位点是确定性的**' if same
                         else '❌ 不同 ⇒ 需要查（可能有别的随机源）'))
    if not same:
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                L.append('     第 %d 项不同：%s vs %s' % (i, x, y))
    L.append('')
    L.append('── R2：负对照（把 b 的第 0 项换掉 ⇒ R1 必须判"不同"）──')
    bb = list(b)
    if bb:
        bb[0] = (bb[0][0] + 1, bb[0][1])
    nc = (a == bb)
    L.append('   ⇒ %s' % ('❌ **判据恒真**（换了还判相同）' if nc
                         else '✅ 判据**失败**了（有分辨力）'))
    L.append('')
    L.append('── R3：`seed` 键的存在性 ──')
    has1, has2 = ('seed' in c1), ('seed' in c2)
    L.append('   %s: %s ；%s: %s' % (t1, has1, t2, has2))
    if not has1 and not has2:
        L.append('   ⇒ **两个臂都没传 seed** ⇒ 都走 `nuc_cfg(seed=11)` 的硬编码默认')
        L.append('   ⇒ ★ 记账：goal 对 C1 的表述是「位点由 **CLI 记录的 seed** 复现」。')
        L.append('     **当前实现比这更强**（完全确定性、与 CLI 无关），但也意味着')
        L.append('     **CLI 上没有旋钮去改它** ⇒ 若要做"不同 seed"的对照，要新加参数。')
    L.append('')
    L.append('=' * 96)
    ok = same and (not nc)
    L.append('✅ **C1 的"可复现"这一半成立**（初始位点跨臂逐位相同 + 负对照有分辨力）'
             if ok else '❌ 判据未全过')
    out = '\n'.join(L)
    print(out)
    open('_w2_r581_c1seed.log', 'w').write(out + '\n')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
