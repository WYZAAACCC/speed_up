#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r30_mbverdict.py —— R31 **MB-1 多块相遇实验**的判决（判据**跑之前就写好**）。

## 装置（`_r30_mb1.sh`）

| 臂 | 内容 | 用途 |
|---|---|---|
| `mb1`  | 2 块（V1×3 + V3×3），t=0 由**精确判据**确认分离（异变体接触面 = 0） | 被测 |
| `mb1s` | 1 块（V1×3），同盒/同种子/同步数 | **负对照**：没有邻居 |

## 判据（预先登记，不得事后挪动）

* **P-SA-2a（主判据）** `mb1` 的**块 0 沿它自己的长轴 a** 的跨度出现**平台**：
  `rate_late / rate_early < 0.25`，且平台期间 **`box_touch == 0`** 且
  **`Vt/V_box < 0.5`**（母相仍在）⇒ 停止**不是**撞壁造成的。
* **P-SA-2b** `mb1` 的 `nf2` 从 0 **增到 > 0**（两块确实接触上了）。
* **P-SA-2c（负对照）** `mb1s` 在同一步数内**不出现**平台，或其平台与
  `box_touch == 1` 同时发生 ⇒ 判据有分辨力。
* **P-SA-2d** 两臂的 `E_el_J` 轨迹不同（弹性相互作用存在）—— 只报不判（无对照分布）。

## ★ 本脚本同时是 R30 落盘修复的**正面演示**

`mb1` 的 CSV 是在加了 `blk_alen_nm` 列**之前**启动的（进程已加载旧模块），
所以"块 0 的长轴跨度"在**在线列里没有**。
⇒ 本脚本改从**落盘快照**离线重算（`region` + `vmap` + 变体表 ⇒ `blocks(axes_var=…)`）。
这正是用户要求的那条路：「即使测量工具有问题，之后也能用新量具在原始数据上重测」。

跑法：  python3 _r30_mbverdict.py [--root _exp/_bk_mb] [--arms mb1,mb1s]
"""
import os
import sys
import csv
import glob
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import _bk_measure as BM                                        # noqa: E402
import windowB_surface as W                                     # noqa: E402
from T16_verify_rve import C, EPS0, NPF                         # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))


def variant_axes(v):
    n = np.asarray(NPF[v], float); n = n / np.linalg.norm(n)
    nref, _, _ = W.argmin_normal_cached(C, np.asarray(EPS0[v - 1], float))
    R = W.LevelSetMulti._rank1_axes(np.asarray(EPS0[v - 1], float), nref)
    a = np.asarray(R[1], float); a = a / np.linalg.norm(a)
    w = np.asarray(R[2], float); w = w / np.linalg.norm(w)
    return n, a, w


def load_csv(d):
    p = os.path.join(d, 'series.csv')
    if not os.path.exists(p):
        return []
    with open(p, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def fnum(r, k):
    try:
        return float(r.get(k, 'nan'))
    except (TypeError, ValueError):
        return float('nan')


def offline_blocklen(d, sel_variant=1):
    """★ 从**落盘快照**离线重算"**指定变体那一块**沿它自己的长轴 a 的跨度"（nm）。

    ⚠ 必须**按变体选块**，不能按"最大的那块"选：`blocks()` 的输出按体积降序排，
      而 MB-1 两块**体积几乎相等** ⇒ 排序在快照之间会**互换身份**，
      于是"块 0 的长轴跨度"会跳变（这正是"量的身份不稳定"那类错）。

    返回 [(step, alen_nm, nlath, span_nm, nblk_sig, f_var_of_that_block), ...]。
    ⇒ 这是"新量具在原始数据上重测"的正面演示。
    """
    out = []
    for s in sorted(glob.glob(os.path.join(d, 'snap_*.npz'))):
        z = np.load(s)
        reg = z['region']
        dx = float(z['L']) / reg.shape[0]
        vmap = {int(k): int(v) for k, v in zip(z['vmap_keys'], z['vmap_vals'])}
        ax = {v: variant_axes(v) for v in sorted(set(vmap.values()))}
        b = BM.blocks(reg, dx, vmap, eps0_var=EPS0, npf_var=NPF, axes_var=ax)
        al = [float(x) for x in (b.get('blk_alen_nm') or '').split('/') if x]
        nl = [int(x) for x in (b.get('blk_nlath') or '').split('/') if x]
        sp = [float(x) for x in (b.get('blk_span_nm') or '').split('/') if x]
        vs = [int(x) for x in (b.get('blk_vars') or '').split('/') if x]
        idx = vs.index(sel_variant) if sel_variant in vs else None
        out.append((int(z['step']),
                    (al[idx] if idx is not None and idx < len(al) else float('nan')),
                    (nl[idx] if idx is not None and idx < len(nl) else -1),
                    (sp[idx] if idx is not None and idx < len(sp) else float('nan')),
                    int(b['nblk_sig']),
                    (vs[idx] if idx is not None else -1)))
    return out


def rate(xs, ys, lo=None, hi=None):
    """简单最小二乘斜率（单位 nm/步）；样本不足返回 nan。"""
    p = [(x, y) for x, y in zip(xs, ys) if np.isfinite(y)
         and (lo is None or x >= lo) and (hi is None or x <= hi)]
    if len(p) < 3:
        return float('nan')
    x = np.array([t[0] for t in p], float)
    y = np.array([t[1] for t in p], float)
    return float(np.polyfit(x, y, 1)[0])


def selfac_verdict(root, arms, vbox):
    """★★ R31 **MB-2/MB-3 自协调变体选择**的判决（P-SA-1a..c）。

    ## 为什么必须**按已转变分数 f 配对**
    `r_selfac` 与 `E_el_J` **都随 f 增长**（变体越多、转变越多，两者都动）。
    两臂的形核节奏由同一个 `--eng-cadence` 决定，但**长出来的速度不一定一样**
    （变体不同 ⇒ 弹性驱动不同）⇒ **直接比末态会被 f 的差异混杂**。
    ⇒ 正确口径：在一组**目标 f** 上各取最近的一行，**逐点配对**比。

    ## 正对照（先证明配对本身可信）
    两臂 t=0 的种子**完全相同**（同一 `--laths`、同一变体 1）⇒ 在**最早**的那个
    目标 f 上两臂的 `r_selfac` 必须**几乎相同**。若这里就已经差很多 ⇒ 配对口径有问题。

    ## 判据（预先登记，双向）
      P-SA-1a 在**共同 f 区间**上，ed 臂的 `r_selfac` **低于** random 臂（逐点多数成立）
      P-SA-1b 在共同 f 区间上，ed 臂的 `E_el_J` 更低
      P-SA-1c ed 臂的 `n_var_sig`/`n_habit` **不多于** random 臂
    ⚠ 任一条**不成立就如实写"P-SA-1 被否证"**，不得挑区间。
    """
    def load(arm):
        d = os.path.join(_HERE, root, 'eng_%s' % arm)
        rows = load_csv(d)
        return d, rows

    data = {}
    for arm in arms:
        d, rows = load(arm)
        if not rows:
            print('⚠ %s 没有数据' % arm)
            return 1
        data[arm] = [(fnum(r, 'step'), fnum(r, 'Vt') * 1e18 / vbox,
                      fnum(r, 'r_selfac'), fnum(r, 'E_el_J'),
                      fnum(r, 'n_var_sig'), fnum(r, 'n_habit'), r.get('f_var', ''))
                     for r in rows if r.get('r_selfac') not in (None, '')]
        print('%-5s %d 个有效测点，f: %.4f → %.4f，step %g → %g'
              % (arm, len(data[arm]), data[arm][0][1], data[arm][-1][1],
                 data[arm][0][0], data[arm][-1][0]))
    if len(data) < 2:
        return 1
    a1, a2 = arms[0], arms[1]

    def nearest(seq, f):
        return min(seq, key=lambda t: abs(t[1] - f))

    f_lo = max(data[a1][0][1], data[a2][0][1])
    f_hi = min(data[a1][-1][1], data[a2][-1][1])
    print('\n共同 f 区间：[%.4f, %.4f]；在其上取 6 个目标点逐点配对'
          % (f_lo, f_hi))
    print('  %-9s | %-22s | %-22s | %s'
          % ('f', '%s (r / E_el / nvar)' % a1, '%s (r / E_el / nvar)' % a2,
             '判读'))
    grid = [f_lo + (f_hi - f_lo) * k / 5.0 for k in range(6)]
    win_a = win_b = win_c = 0
    n = 0
    for f in grid:
        t1, t2 = nearest(data[a1], f), nearest(data[a2], f)
        n += 1
        ok_a = t1[2] < t2[2]
        ok_b = t1[3] < t2[3]
        ok_c = t1[4] <= t2[4]
        win_a += int(ok_a)
        win_b += int(ok_b)
        win_c += int(ok_c)
        print('  %-9.5f | %-8.4f %-8.3e %-4g | %-8.4f %-8.3e %-4g | %s %s %s'
              % (f, t1[2], t1[3], t1[4], t2[2], t2[3], t2[4],
                 'a' if ok_a else '.', 'b' if ok_b else '.', 'c' if ok_c else '.'))
    # 正对照：最早的目标点上两臂应当几乎相同（种子相同）
    t1, t2 = nearest(data[a1], f_lo), nearest(data[a2], f_lo)
    same0 = abs(t1[2] - t2[2]) < 0.02
    print('\n  [正对照] f=%.4f 处两臂 r_selfac 差 = %.4f（种子相同 ⇒ 应 ≈0）%s'
          % (f_lo, abs(t1[2] - t2[2]), '✅' if same0 else '⚠ 配对口径可疑'))
    print('\n★ 判据 P-SA-1（%d 个配对点）' % n)
    for tag, w, txt in (('P-SA-1a', win_a, 'ed 的 r_selfac 更低'),
                        ('P-SA-1b', win_b, 'ed 的 E_el 更低'),
                        ('P-SA-1c', win_c, 'ed 的变体数不多于 random')):
        if w >= n - 1:
            verdict = '**PASS**（%d/%d）' % (w, n)
        elif w <= 1:
            verdict = '**否证**（%d/%d —— ed 反而更差/相同）' % (w, n)
        else:
            verdict = '**不判定**（%d/%d，两向都出现）' % (w, n)
        print('  %-9s %-30s %s' % (tag, txt, verdict))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='_exp/_bk_mb')
    ap.add_argument('--arms', default='mb1,mb1s')
    ap.add_argument('--mode', default='impinge',
                    choices=['impinge', 'selfac'],
                    help='impinge = MB-1 的两块相遇；selfac = MB-2/MB-3 的变体选择')
    ap.add_argument('--vbox-um3', type=float, default=12.0 ** 3)
    a = ap.parse_args()

    if a.mode == 'selfac':
        return selfac_verdict(a.root, [x.strip() for x in a.arms.split(',') if x.strip()],
                              a.vbox_um3)

    arms = [x.strip() for x in a.arms.split(',') if x.strip()]
    fnum_map = {}
    res = {}

    for arm in arms:
        d = os.path.join(_HERE, a.root, 'dry_%s' % arm)
        print('=' * 96)
        print('臂 %s   目录=%s' % (arm, d))
        print('=' * 96)
        rows = load_csv(d)
        if not rows:
            print('   ⚠ 没有 series.csv（还没产出？）')
            continue
        steps = [fnum(r, 'step') for r in rows]
        vt = [fnum(r, 'Vt') * 1e18 for r in rows]                  # µm³
        nf2 = [fnum(r, 'nf2') for r in rows]
        f2a = [fnum(r, 'f2_area_m2') * 1e12 for r in rows]         # µm²
        bt = [fnum(r, 'box_touch') for r in rows]
        eel = [fnum(r, 'E_el_J') for r in rows]
        print('  在线 CSV：%d 行，step %g→%g' % (len(rows), steps[0], steps[-1]))
        print('  %-6s %-10s %-9s %-9s %-9s %-11s %s'
              % ('step', 'Vt/µm³', 'f=%.4f', 'nf2', 'f2/µm²', 'E_el/J', 'box_touch'))
        for i in range(0, len(rows), max(1, len(rows) // 12)):
            print('  %-6g %-10.3f %-9.4f %-9g %-9.3f %-11.3e %g'
                  % (steps[i], vt[i], vt[i] / a.vbox_um3, nf2[i], f2a[i],
                     eel[i], bt[i]))
        print('  末值：Vt=%.3f µm³ (f=%.4f)  nf2=%g  f2=%.3f µm²  box_touch=%g'
              % (vt[-1], vt[-1] / a.vbox_um3, nf2[-1], f2a[-1], bt[-1]))

        off = offline_blocklen(d)
        if not off:
            print('   ⚠ 没有快照 ⇒ 无法离线重算块长轴跨度')
            continue
        print('\n  ★ **离线重算**（从落盘快照，用 R30 的新块表量具；'
              '在线列里没有这一项）')
        print('  %-8s %-8s %-12s %-10s %-10s %s'
              % ('step', 'nblk_sig', 'V1块 长轴nm', 'V1块 片数', 'V1块 n*跨度',
                 'V1块变体'))
        for st, al, nl, sp, nb, vv in off:
            print('  %-8d %-8d %-12.1f %-10d %-10.1f %d' % (st, nb, al, nl, sp, vv))
        xs = [t[0] for t in off]
        ys = [t[1] for t in off]
        mid = xs[0] + 0.5 * (xs[-1] - xs[0])
        r_e = rate(xs, ys, hi=mid)
        r_l = rate(xs, ys, lo=mid)
        ratio = (r_l / r_e) if (np.isfinite(r_e) and abs(r_e) > 1e-9) else float('nan')
        print('\n  块0 长轴跨度：早期斜率 = %.4f nm/步   晚期斜率 = %.4f nm/步'
              '   ⇒ rate_late/rate_early = **%.3f**' % (r_e, r_l, ratio))
        print('  末态 f = %.4f（母相仍在？%s）；box_touch 出现次数 = %d'
              % (vt[-1] / a.vbox_um3, '是' if vt[-1] / a.vbox_um3 < 0.5 else '否',
                 int(sum(1 for x in bt if x > 0))))
        res[arm] = dict(xs=xs, ys=ys, r_e=r_e, r_l=r_l, ratio=ratio,
                        nf2_0=nf2[0], nf2_end=nf2[-1], f=vt[-1] / a.vbox_um3,
                        ntouch=int(sum(1 for x in bt if x > 0)),
                        eel0=eel[1] if len(eel) > 1 else float('nan'),
                        eel_end=eel[-1])

    # ---------------- 判据 ----------------
    print('\n' + '=' * 96)
    print('★ 预登记判据 P-SA-2a..d')
    print('=' * 96)
    if 'mb1' in res:
        m = res['mb1']
        ok_a = (np.isfinite(m['ratio']) and m['ratio'] < 0.25
                and m['ntouch'] == 0 and m['f'] < 0.5)
        print('  P-SA-2a mb1 块0 长轴出现平台（rate比<0.25）且未撞壁且母相仍在  %s'
              '  rate比=%.3f  撞壁=%d  f=%.4f'
              % ('**PASS**' if ok_a else '**FAIL**', m['ratio'], m['ntouch'], m['f']))
        ok_b = (m['nf2_0'] == 0 and m['nf2_end'] > 0)
        print('  P-SA-2b mb1 的 nf2 从 0 增到 >0（两块接触上了）            %s'
              '  nf2: %g → %g' % ('**PASS**' if ok_b else '**FAIL**',
                                  m['nf2_0'], m['nf2_end']))
    else:
        print('  P-SA-2a/b：mb1 数据缺失 ⇒ 无法判定')
    if 'mb1s' in res:
        s = res['mb1s']
        no_plat = (not np.isfinite(s['ratio'])) or s['ratio'] > 0.5
        plat_at_wall = s['ntouch'] > 0
        ok_c = no_plat or plat_at_wall
        print('  P-SA-2c 负对照 mb1s 不出现平台（或平台与撞壁同时）        %s'
              '  rate比=%.3f  撞壁=%d' % ('**PASS**' if ok_c else '**FAIL**',
                                         s['ratio'], s['ntouch']))
    else:
        print('  P-SA-2c：mb1s 数据缺失 ⇒ 无法判定')
    if 'mb1' in res and 'mb1s' in res:
        d0 = abs(res['mb1']['eel0'] - res['mb1s']['eel0'])
        d1 = abs(res['mb1']['eel_end'] - res['mb1s']['eel_end'])
        print('  P-SA-2d（只报不判）E_el：t≈0 差 %.3e J；末态差 %.3e J'
              % (d0, d1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
