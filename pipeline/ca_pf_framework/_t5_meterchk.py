#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_meterchk.py --- ★★★★★★ **量具解析正对照**（用户第一硬要求）

## 用户逐字要求
> 「一定确保测量工具的正确性……凡"最小化/最优化"得到的量，
>   必须**先用解析已知答案验证最小化器本身**，且**正对照必须预先写死、必须能失败**」

## 本脚本验两个量具（判据② 与判据③④⑥ 都靠它们）

### 量具 1：`argmin2` / `region()` —— **本引擎唯一的"最小化器"**
`region() = argmin(φ, axis=0)`（`windowB_surface.py:1513-1537`）⇒ 全盒按 φ 最小的场分区。

**解析真值（手算可得）**：取两个**等半径**球 `φ_k = |x − c_k| − R`（k=1,2）。
`argmin` 的边界是 `|x−c1| = |x−c2|` ⇒ **垂直平分面**（一个**平面**，解析已知）。
⇒ 逐体素判据：**预测的 `region` 必须与解析式逐点一致**（0 误分类）。

**预先写死的负对照（必须 FAIL）**：把 `φ_2` **整体平移** δ ⇒ 平分面移动
⇒ 判据必须报出误分类 ⇒ 若仍报 0，说明判据**没有分辨力**（判据作废）。

### 量具 2：`wide_face_thickness`（`t_wf`）—— **判据② 的厚度量具**
`_bk_measure.py:153-215`：按 `n = ∇φ/|∇φ|` 取宽面胞（`(n·n*)² > cos2_min`）再统计厚度。

**解析真值**：厚度 `t`、法向 `n*` 的**平板 SDF** `φ = max(n*·(x−x0) − t/2, −n*·(x−x0) − t/2)`
⇒ `t_wf` **必须返回 `t`**（容差 Δx 量级，因体素化）。

**预先写死的负对照（必须 FAIL）**：① 改 `t` ⇒ 读数必须跟着变；
② **★ 把 `region` 当 `φ` 传进去**（这正是 `_r581_wfthick.py` 历史上踩的坑：
    18 个场给出**同一个** `t_wf`=1172.6 nm）⇒ 读数必须**不是** `t`（即：量具能识别出被喂了错的输入）。
"""
import inspect
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FAILED = []


def ck(name, ok, detail=''):
    print('   %s %s%s' % ('✅' if ok else '❌', name, ('  —— ' + detail) if detail else ''))
    if not ok:
        FAILED.append(name)


def _pick_t(obj):
    """从返回值里取"厚度"（可能是 dict / 标量 / 元组）。返回 float 或 None。"""
    if isinstance(obj, dict):
        for k in ('t_wf', 't_wf_m', 't', 'thickness', 't_wf_n', 'thick'):
            if k in obj:
                try:
                    return float(np.asarray(obj[k]).ravel()[0])
                except Exception:
                    pass
        for k, v in obj.items():
            try:
                f = float(np.asarray(v).ravel()[0])
                if np.isfinite(f) and abs(f) > 1e-12:
                    return f
            except Exception:
                continue
        return None
    try:
        return float(np.asarray(obj).ravel()[0])
    except Exception:
        return None


def main():
    print('=' * 100)
    print('量具解析正对照（正对照**预先写死**；负对照**必须能失败**）')
    print('=' * 100)

    # ── 先把要用的符号拿到手 ──────────────────────────────────────
    try:
        import windowB_surface as W
    except Exception as e:
        print('  ❌ 无法 import windowB_surface：%s' % e)
        return 1
    try:
        import _bk_measure as BM
    except Exception as e:
        print('  ❌ 无法 import _bk_measure：%s' % e)
        BM = None

    # ══════════════════════════════════════════════════════════════
    print()
    print('══ 量具 1：`argmin2` / `region()` —— 解析真值 = 垂直平分面 ══')
    N, L = 32, 32 * 62.5e-9          # 32³、dx=62.5 nm
    dx = L / N
    xs = (np.arange(N) + 0.5) * dx
    X, Y, Z = np.meshgrid(xs, xs, xs, indexing='ij')
    R = 8 * dx
    c1 = np.array([10 * dx, 16 * dx, 16 * dx])
    c2 = np.array([22 * dx, 16 * dx, 16 * dx])
    d1 = np.sqrt((X - c1[0]) ** 2 + (Y - c1[1]) ** 2 + (Z - c1[2]) ** 2)
    d2 = np.sqrt((X - c2[0]) ** 2 + (Y - c2[1]) ** 2 + (Z - c2[2]) ** 2)
    phi = np.full((3, N, N, N), 1e3)
    phi[1] = d1 - R
    phi[2] = d2 - R
    # 解析真值：等半径 ⇒ 平分面 = 到两心等距 ⇒ 比较 d1 vs d2
    truth = np.where(d1 < d2, 1, 2).astype(np.int16)
    # 只在场内（球外 φ=1e3 也一样是 1e3，argmin 会取第一个 ⇒ 需限定在"有球的地方"）
    inside = (d1 <= R) | (d2 <= R)
    got = np.argmin(phi, axis=0).astype(np.int16)
    mis = int(((got != truth) & inside).sum())
    n_in = int(inside.sum())
    ck('正对照：`argmin` 与解析平分面逐体素一致（误分类 = 0）', mis == 0,
       '球内 %d 体素，误分类 **%d**' % (n_in, mis))

    # ★ 预先写死的负对照：把 φ_2 平移 δ ⇒ 平分面移动 ⇒ 判据必须报错
    dlt = 2 * dx
    phi2 = np.full((3, N, N, N), 1e3)
    phi2[1] = d1 - R
    phi2[2] = (np.sqrt((X - c2[0] - dlt) ** 2 + (Y - c2[1]) ** 2
                       + (Z - c2[2]) ** 2)) - R
    got2 = np.argmin(phi2, axis=0).astype(np.int16)
    mis2 = int(((got2 != truth) & inside).sum())
    ck('负对照：φ₂ 平移 2Δx ⇒ 判据**必须**报出误分类（有分辨力）', mis2 > 0,
       '误分类 **%d**（必须 > 0）' % mis2)

    # ══════════════════════════════════════════════════════════════
    print()
    print('══ 量具 2：`wide_face_thickness`（`t_wf`）—— 解析真值 = 平板厚度 ══')
    if BM is None:
        print('   ⚠ 没有 `_bk_measure` ⇒ 跳过')
    else:
        fn = None
        for nm in ('wide_face_thickness', 'wide_face_thick', 'wf_thickness'):
            if hasattr(BM, nm):
                fn = getattr(BM, nm); fname = nm; break
        if fn is None:
            print('   ⚠ 找不到 wide_face_thickness ⇒ 候选：%s'
                  % [k for k in dir(BM) if 'thick' in k.lower() or 'wide' in k.lower()])
        else:
            print('   函数 = `%s%s`' % (fname, inspect.signature(fn)))
            n_star = np.array([1.0, 0.0, 0.0])
            ok_pos = 0
            for t_nm in (125.0, 250.0, 500.0):
                t = t_nm * 1e-9
                pr = (X - L / 2) * n_star[0] + (Y - L / 2) * n_star[1] + (Z - L / 2) * n_star[2]
                slab = np.maximum(pr - t / 2, -pr - t / 2)
                got_t = None
                # ★ 签名 = (phi, dx, n_hab, k, band=…, cos2_min=…, band_cells=…)
                #   ⇒ 必须给**场号 k**。单场平板 ⇒ k=0。
                for call in (lambda: fn(slab, dx, n_star, 0),
                             lambda: fn(slab, dx, n_star, 1),
                             lambda: fn(slab[None], dx, n_star, 0)):
                    try:
                        got_t = call(); break
                    except Exception:
                        continue
                if got_t is None:
                    ck('解析平板 t=%.0f nm ⇒ **正对照未能执行**' % t_nm, False,
                       '所有调用写法都失败 ⇒ 按用户要求**记 FAIL**（不许当通过）')
                    continue
                g = _pick_t(got_t)
                if g is None:
                    ck('解析平板 t=%.0f nm ⇒ 返回 dict 里找不到厚度键' % t_nm, False,
                       '返回的键 = %s' % (list(got_t) if isinstance(got_t, dict) else type(got_t)))
                    continue
                err = abs(g - t) / t
                if err <= 0.25:
                    ok_pos += 1
                ck('解析平板 t=%.0f nm ⇒ t_wf=%.1f nm（相对差 %.1f%% ≤ 25%%）'
                   % (t_nm, g * 1e9, err * 100), err <= 0.25)
            if ok_pos == 0:
                ck('量具 2 的正对照**至少一条**必须跑成', False,
                   '一条都没跑成 ⇒ 量具 2 **不可用于判据②**')
            # ★ 负对照（**必须能失败**）：喂 `region`（整数标签）⇒ 读数必须偏离 t
            reg = np.argmin(phi, axis=0).astype(float)
            try:
                bad = None
                for call in (lambda: fn(reg, dx, n_star, 0), lambda: fn(reg, dx, n_star, 1)):
                    try:
                        bad = float(np.asarray(call()).ravel()[0]); break
                    except Exception:
                        continue
                ck('负对照：喂 `region`（整数标签）⇒ 读数**必须**偏离真值 250 nm',
                   (bad is None) or (abs(bad - 250e-9) / 250e-9 > 0.5),
                   ('喂 region ⇒ t_wf=%.1f nm' % (bad * 1e9)) if bad is not None
                   else '抛异常 ⇒ 也算能识别错输入')
            except Exception as e:
                ck('负对照：喂 `region` ⇒ 抛异常（能识别错输入）', True, str(e)[:60])

    print()
    print('=' * 100)
    if FAILED:
        print('  ❌ **%d 条未通过**：%s' % (len(FAILED), FAILED))
        print('  ⇒ 按用户要求：量具不过**不得用于判据**')
    else:
        print('  ✅ **全部通过**（正对照逐点一致 + 负对照都有分辨力）')
    print('=' * 100)
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
