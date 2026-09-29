#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_bk_cmp.py —— **同类性对照**：长出来的块 vs 摆出来的块，一张表看完。

用法: python3 _bk_cmp.py <dir> [dir...]        # 每个 dir 是一个臂的输出目录
      python3 _bk_cmp.py --last <dir> ...      # 只用每个臂的**最后一个**快照（默认）

为什么需要它：`_bk_verdict.py` 判的是"这一臂过没过"，而本脚本回答的是
"**长出来的块和摆出来的块，差在哪、差多少**"。这两个问题不能混：
`dry_gs2` 在 V-1g 上是 PASS 的，但它比预摆对照少 35% 的界面面积（V-7 = 0.616），
**只有把两臂并排放才能一眼看出**。

列的含义（全部来自落盘数据，可离线重算）：
  · `nslab`/`nf3col`/`runs` —— 柱剖面里的段数与场序号（`runs` 里**缺号 = 那片没了**）
  · `F3 µm²` —— 同变体界面总面积（Cauchy 无偏估计）
  · `cov` —— V-7 覆盖率 = `F3 / [Σ_k V_k/t_k · (M−1)/M]`（⚠ 分母会被侵蚀污染，见下）
  · `β占比max` —— V-7b：最差那一对的 β 夹层占比
  · `厚度` —— 逐片沿 n\* 的厚度（先剔 <32 体素孤儿再取分位，抗离散噪声）
  · `Vt` —— α′ 总体积
  · `场` —— 末态还在位的场号；**与 M 不等就是"块缺片"**
"""
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _bk_measure as BM                                        # noqa: E402


def last_snap(d):
    s = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
    return s[-1] if s else None


def robust_thickness(reg, dx, n_hab, k):
    """场 k 的厚度：**先剔掉 <32 体素的孤儿分量**，再取投影 0.5%/99.5% 分位之差。

    ★ 为什么不能直接读 `n_k`：`gs2` 的场 1 有 3 个 1–2 体素孤儿散在盒子里，
      把它的 n 向包围尺寸从 251 nm 拉到 **868 nm**（`_bk_measure` 报的 `n_1`）。
      孤儿是零厚度界面模型的离散伪影，不该算进"板条厚度"。
    """
    from scipy import ndimage as ndi
    m = (reg == k)
    if not m.any():
        return 0.0
    st = np.zeros((3, 3, 3), bool)
    for ax in range(3):
        for sh in (1, -1):
            sl = [1, 1, 1]
            sl[ax] = 0 if sh < 0 else 2
            st[tuple(sl)] = True
    st[1, 1, 1] = True
    lab, n = ndi.label(m, structure=st)
    if n > 1:
        sz = np.bincount(lab.ravel())
        sz[0] = 0
        m = (lab == int(np.argmax(sz)))
    idx = np.argwhere(m)
    p = ((idx[:, 0] + 0.5) * n_hab[0] + (idx[:, 1] + 0.5) * n_hab[1]
         + (idx[:, 2] + 0.5) * n_hab[2]) * dx
    q = np.percentile(p, [0.5, 99.5])
    return float(q[1] - q[0])


def main():
    args = [x for x in sys.argv[1:] if not x.startswith('--')]
    print('=' * 118)
    print('_bk_cmp —— 同类性对照（长出来的块 vs 摆出来的块）；全部读数来自落盘快照，可离线重算')
    print('=' * 118)
    # ★ 表头是**字面量**，不要写 `%` 格式串（第一版写成 `'%-12s ...'` 却没给参数
    #   ⇒ `TypeError: not enough arguments for format string`）。
    print('臂            step   M nslab nf3col runs                 F3 µm²     cov'
          '   β占比max 逐片厚度 nm                  Vt µm³ 在位的场')
    print('-' * 118)
    for d in args:
        if not os.path.isabs(d):
            d = os.path.join(HERE, d)
        s = last_snap(d)
        if s is None:
            print('%-12s **无快照**' % os.path.basename(d))
            continue
        z = np.load(s)
        reg = z['region']
        dx = float(z['L']) / reg.shape[0]
        n_hab = np.asarray(z['n_hab'], float)
        vmap = {int(k): int(v) for k, v in zip(z['vmap_keys'], z['vmap_vals'])}
        M = len(vmap)
        r = BM.measure_state(reg, dx, n_hab, z['w_ax'], z['a_ax'], vmap)
        cv = BM.snapshot_coverage(z)
        present = [k for k in sorted(vmap) if r['vol_%d' % k] > 0]
        th = {k: robust_thickness(reg, dx, n_hab, k) for k in present}
        # ★ 合理性断言：**单位错会静默打印成 0**（第一版正是如此：函数返回"米"，
        #   而格式串按"纳米"打印 ⇒ `'%.0f' % 2.757e-07` = `0`，看着像"还没长出来"）。
        #   板条厚度必须在 (20, 2000) nm 之间，否则**直接报错**而不是印一个假数。
        _bad = [k for k in present if not (2e-8 < th[k] < 2e-6)]
        if _bad:
            raise ValueError('robust_thickness 单位可疑：场 %s 给出 %s（应为 20~2000 nm）'
                             % (_bad, [th[k] for k in _bad]))
        vt = sum(r['vol_%d' % k] for k in present)
        bmax = (max(cv['beta_frac'].values()) if cv['beta_frac'] else 0.0)
        print('%-12s %5d %5d %5d %5d %-16s %9.4f %7.3f %8.2f %-28s %9.4f %s'
              % (os.path.basename(d), int(z['step']), M, r['nslab_n'],
                 r['nf3_col'], r['runs'], cv['f3_area'] * 1e12, cv['cov'],
                 bmax,
                 '/'.join('%.0f' % (th[k] * 1e9) for k in present), vt * 1e18,
                 # ★ 完整性要按**柱剖面**判，不能按 `vol > 0` 判：`gs3` 的场 1
                 #   被撕成 18 个碎片散在背景里，`vol_1 > 0` 照样成立，
                 #   但柱剖面 `runs=5,3,2,4,6` 里**没有 1** ⇒ 块里没有那片。
                 #   （第一版这里印 `1,2,3,4,5,6` 却不加缺片标记 ⇒ 自相矛盾。）
                 ','.join(str(k) for k in present)
                 + ('' if set(int(x) for x in r['runs'].split(',') if x) == set(vmap)
                    else '  ← **柱内缺片 %s**'
                         % ','.join(str(k) for k in sorted(vmap)
                                    if str(k) not in r['runs'].split(',')))))
    print('-' * 118)
    print('记账：`cov` 的分母 `Σ_k V_k/t_k` 会被"侵蚀/孤儿"污染 ⇒ 它**只是序数判据**'
          '（干净分开 0.29/0.51/0.62 与 0.88/0.96），不是精确面积比；>1.1 即分母不可用。')
    print('      `β占比max` 不受此影响（同一对界面自己的 F3 与 β 之比）。两者必须一起看。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
