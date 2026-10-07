#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r579_mem160.py --- goal §(5)：**在 N=160 上直接重测内存定律与 `a` 的逐项构成**。

## 为什么必须重测（不许拿旧数推）

现有的"10 µm 盒内存墙"结论来自两处**推算**：

1. `R550_MEMORY_ENVELOPE.md`：内存定律 `MB = 9.01·nv·N³/2²⁰ + 311.8·N³/2²⁰`（在 **N=64** 上拟合），
   ⇒ 外推 `N=160` 得 `nv_max ≈ 605`、转变分数上限 **15.4%**。
2. `_r560_softmem.py` 发现 **生产实际走 `elastic_soft=True`**（类属性，`_bk_exp.py` 不覆盖），
   而 `soft` 会把 `pf.phi` 从 **bool（1 B/胞）** 升成 **float64（8 B/胞）**
   ⇒ `a` 从 9.01 变成 ≈16.0 ⇒ `nv_max` 应 ≈341，**R550 §6 的结论按旧 `a` 算的**。
3. 但 `_r560` 的量具也只跑 **N=64**，然后用公式外推 `N=160`；`_r553` 同。
4. `_r574` 又用 `a=16, c=311.8` 反推出"隐含预算 23.1 GiB"（与 22 GB 口径不同）。

⇒ 本轮按 goal 要求：**在 N=160 上直接构造、直接量、直接算**，并把 `a` **拆到每一项**。

## 判据（先写死，必须能失败）

* **M1 量具自证**：soft 触发前后 `pf.phi.dtype` 必须由 `bool` 变 `float64`
  （否则量到的是"非生产路径"，与 `_r560` 的 S1 同一条）。
* **M2 一点性检查**：`nv=4` 与 `nv=8` 两次**独立**构造测出的总字节，
  与"逐项清单求和"**必须逐位一致**（清单就是从同一次构造里遍历出来的 ⇒ 差 = 0）。
* **M3 线性性**：`a = ΔM/(Δnv·N³)` 必须落在 **[15.5, 16.5]**（f64）；若明显偏离
  16 B/胞 ⇒ 说明**还有别的随 nv 增长的项**（那就是本轮要抓的东西）。
* **M4 负对照（量具必须有分辨力）**：`phi_prec='f32'` 必须让 `a` **减少 4.000 B/胞**
  （`g.phi` 由 8→4；`pf.phi` 不受影响）。若差不是 4.0 ⇒ 清单口径有问题。
* **M5 C5 判定**：用**实测**的 `a`/`c` 算 `nv_max`，并与 §几何 算出的"填 30% 所需的 nv"比。
"""
import gc
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_surface as W                                    # noqa: E402
from T16_verify_rve import C, EPS0                             # noqa: E402

N = int(os.environ.get('R579_N', '160'))
DX_UM = float(os.environ.get('R579_DX', '0.0625'))
BUDGET_MB = float(os.environ.get('R579_BUDGET_MB', str(22 * 1024)))
# ★ `_bk_exp.py` 的**当前默认几何**（`--plate-L/-W/-T`，单位 nm）
PLATE_L_NM = float(os.environ.get('R579_PLATE_L', '2400'))
PLATE_W_NM = float(os.environ.get('R579_PLATE_W', '640'))
PLATE_T_NM = float(os.environ.get('R579_PLATE_T', '250'))
FILL = float(os.environ.get('R579_FILL', '0.30'))
BOX_UM = float(os.environ.get('R579_BOX_UM', '10'))

OUT = os.environ.get('R579_OUT', '_w2_r579_mem160.log')


def walk(o, seen=None, path='g', depth=0):
    """遍历对象图，产出 `(path, array)`。**按 id 去重**（否则共享数组会被重复计）。"""
    if seen is None:
        seen = set()
    if depth > 6 or id(o) in seen:
        return
    seen.add(id(o))
    if isinstance(o, np.ndarray):
        yield path, o
        return
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, seen, '%s[%r]' % (path, k), depth + 1)
        return
    if isinstance(o, (list, tuple)):
        for i, v in enumerate(o):
            yield from walk(v, seen, '%s[%d]' % (path, i), depth + 1)
        return
    d = getattr(o, '__dict__', None)
    if isinstance(d, dict):
        for k, v in d.items():
            yield from walk(v, seen, '%s.%s' % (path, k), depth + 1)


def build(nv, prec, pf_phi='materialized', h_chunk=4):
    eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(nv)]
    g = W.LevelSetMulti(N, N * DX_UM, C=C, eps0=eps, gamma=0.25, Mob=1e-9,
                        df=[0.0] * (nv + 1), nv=nv, phi_prec=prec,
                        pf_phi_mode=pf_phi, h_chunk=h_chunk)
    g.init_parent()
    rng = np.random.default_rng(3)
    nrm = np.array([0.0, 0.0, 1.0])
    Lc = N * DX_UM
    g.seed_plate(1, rng.random(3) * Lc * 0.5 + Lc * 0.25, nrm, 120e-9, 300e-9)
    g.advance(dt=1e-9)
    dt_before = str(g.pf.phi.dtype)
    g.elastic_driving()          # ★ 触发 soft 分支（materialized 下会把 pf.phi 升 float64）
    dt_after = str(g.pf.phi.dtype)
    return g, dt_before, dt_after


def inventory(g):
    seen = set()
    rows = []
    tot = 0
    for p, a in walk(g, seen):
        rows.append((p, tuple(a.shape), str(a.dtype), int(a.nbytes)))
        tot += int(a.nbytes)
    rows.sort(key=lambda r: -r[3])
    return tot, rows


def main():
    # ★★ R579 并行编排：`R579_ONE='<prec>,<nv>'` 时**只跑一个构型**并把清单落成 JSON
    #   ⇒ 4 个构型可以在 **4 个独立进程**里并行（每个 ~3 GB、λ 建表互不干扰）。
    #   为什么值得：`lambda_packed` 在 N=160 是 **O(N³) 且与 nv/prec 无关** ⇒
    #   串行跑 4 次会把同一张表**算 4 遍**（4 × ~4 min = 16 min 纯浪费）。
    one = os.environ.get('R579_ONE', '')
    if one:
        parts = one.split(',')
        prec, nvs = parts[0], parts[1]
        pf_phi = parts[2] if len(parts) > 2 else 'materialized'
        chunk = int(parts[3]) if len(parts) > 3 else 4
        nv = int(nvs)
        g, d0, d1 = build(nv, prec, pf_phi, chunk)
        tot, rows = inventory(g)
        tag = '%s_nv%d_%s' % (prec, nv, pf_phi)
        with open(os.path.join(HERE, '_w2_r579_one_%s.json' % tag), 'w',
                  encoding='utf-8') as fh:
            json.dump({'prec': prec, 'nv': nv, 'pf_phi': pf_phi, 'h_chunk': chunk,
                       'total': tot, 'd0': d0, 'd1': d1,
                       'rows': [list(r) for r in rows]}, fh, ensure_ascii=False)
        print('ONE %s total=%d bytes (%.1f MB) d0=%s d1=%s rows=%d'
              % (tag, tot, tot / 2**20, d0, d1, len(rows)))
        return 0

    L = []
    A = L.append
    A('=' * 104)
    A('R579 — N=%d 的**实测**内存定律 + a 的逐项构成   (dx=%.4f µm, 预算 %.0f MB)'
      % (N, DX_UM, BUDGET_MB))
    A('=' * 104)
    A('  宿主：python %s  numpy %s' % (sys.version.split()[0], np.__version__))
    N3 = N ** 3
    CELL = N3 / 2.0 ** 20

    res = {}
    for prec in ('f64', 'f32'):
        for nv in (4, 8):
            g, d0, d1 = build(nv, prec)
            tot, rows = inventory(g)
            res[(prec, nv)] = (tot, rows, d0, d1)
            A('')
            A('  ── prec=%-3s nv=%d ──' % (prec, nv))
            A('    `pf.phi.dtype`：soft 前 **%s** → soft 后 **%s**   %s'
              % (d0, d1, '✅ M1 PASS' if d1 == 'float64' else '❌ M1 FAIL'))
            A('    数组总计 = **%.1f MB**（= %.3f B/胞 全盒摊）' % (tot / 2**20, tot / N3))
            A('    逐项清单（前 12）：')
            for p, sh, dt_, nb in rows[:12]:
                A('      %-34s %-22s %-9s %9.2f MB'
                  % (p[:34], str(sh)[:22], dt_, nb / 2**20))
            del g
            gc.collect()

    # ---- M2 清单与总计一致（同一次构造内部自洽）----
    A('')
    A('  ── M2 清单自洽（清单求和 vs 总计，同一次构造）──')
    ok2 = True
    for k, (tot, rows, _, _) in res.items():
        s = sum(r[3] for r in rows)
        ok2 = ok2 and (s == tot)
        A('    %-10s 求和 %d vs 总计 %d ⇒ %s'
          % (str(k), s, tot, '✅' if s == tot else '❌'))

    # ---- M3/M4 线性性与 f32 差 ----
    A('')
    A('  ── M3/M4：a 与 f32 差 ──')
    aa = {}
    for prec in ('f64', 'f32'):
        m4 = res[(prec, 4)][0]
        m8 = res[(prec, 8)][0]
        a = (m8 - m4) / (4.0 * N3)
        c = (m4 - 4.0 * a * N3) / CELL      # 每胞固定项（B/胞）
        aa[prec] = (a, c, (m8 - m4) / 2**20)
        A('    %-3s：ΔM(nv 4→8) = %.1f MB ⇒ **a = %.4f B/胞**   c = %.1f B/胞'
          % (prec, (m8 - m4) / 2**20, a, c))
    ok3 = 15.5 <= aa['f64'][0] <= 16.5
    A('    M3（a_f64 ∈ [15.5, 16.5]）：%s' % ('✅ PASS' if ok3 else '❌ FAIL ⇒ 还有随 nv 增长的项'))
    d32 = aa['f64'][0] - aa['f32'][0]
    ok4 = abs(d32 - 4.0) < 1e-6
    A('    M4（f32 让 a 减少 **恰好 4.000**）：实测 %.6f ⇒ %s'
      % (d32, '✅ PASS' if ok4 else '❌ FAIL ⇒ 清单口径有问题'))

    # ---- M5 C5 判定（用实测 a/c，不做任何外推）----
    A('')
    A('  ── M5：N=%d 在 %.0f MB 预算下的 nv_max（**实测 a/c，无外推**）──'
      % (N, BUDGET_MB))
    V_LATH = (PLATE_L_NM * 1e-3) * (PLATE_W_NM * 1e-3) * (PLATE_T_NM * 1e-3)   # µm³
    need = FILL * BOX_UM ** 3 / V_LATH
    A('    几何（`_bk_exp.py` 当前默认）：板条 %.0f×%.0f×%.0f nm ⇒ V_lath = **%.4f µm³**'
      % (PLATE_L_NM, PLATE_W_NM, PLATE_T_NM, V_LATH))
    A('    填满 %.0f%% 的 %.0f µm 盒 = %.1f µm³ ⇒ **需要 nv ≈ %.0f 根**'
      % (100 * FILL, BOX_UM, FILL * BOX_UM ** 3, need))
    A('')
    A('    %-6s %-10s %-12s %-10s %-12s %s'
      % ('prec', 'a(B/胞)', '每nv(MB)', '固定(MB)', 'nv_max', '可达转变分数'))
    for prec in ('f64', 'f32'):
        a, c, _ = aa[prec]
        per = a * CELL
        fix = c * CELL
        nv_max = max(int((BUDGET_MB - fix) / per), 0)
        pct = 100.0 * nv_max * V_LATH / BOX_UM ** 3
        flag = '✅ 够' if nv_max >= need else '❌ 不够（差 %.1f×）' % (need / max(nv_max, 1))
        A('    %-6s %-10.4f %-12.2f %-10.1f %-12d %.1f%%   %s'
          % (prec, a, per, fix, nv_max, pct, flag))
    A('')
    A('  ── 与归档结论对账（**这里是本轮要复核的东西**）──')
    _a_assumed = 9.009
    _nv_old = max(int((BUDGET_MB - 311.8 * CELL) / (_a_assumed * CELL)), 0)
    A('    R550 用 a=9.009（**未触发 soft**）⇒ nv_max ≈ %d，转变分数 %.1f%%'
      % (_nv_old, 100.0 * _nv_old * V_LATH / BOX_UM ** 3))
    A('    R553 用 a=5.009（f32 + 未触发 soft）⇒ nv_max ≈ %d，转变分数 %.1f%%'
      % (max(int((BUDGET_MB - 311.8 * CELL) / (5.009 * CELL)), 0),
         100.0 * max(int((BUDGET_MB - 311.8 * CELL) / (5.009 * CELL)), 0)
         * V_LATH / BOX_UM ** 3))
    A('    ⚠ 上面两行**都是外推**（N=64 拟合 → N=160）；本文件上面那两行是 **N=160 实测**。')

    A('')
    A('  ── a 的逐项构成（f64 / nv=8 的清单里，按"是否随 nv 增长"分组）──')
    rows = res[('f64', 8)][1]
    A('    随 nv 增长的（shape[0] == nreg == 9）：')
    for p, sh, dt_, nb in rows:
        if sh and sh[0] == 9:
            A('      %-40s %-20s %-9s %9.2f MB  ⇒ %.3f B/胞/nv'
              % (p[:40], str(sh)[:20], dt_, nb / 2**20, nb / N3 / 8.0))
    A('    固定项里最大的 6 个（**这些进 c，不进 a**）：')
    _cnt = 0
    for p, sh, dt_, nb in rows:
        if sh and (not sh[0] == 9):
            A('      %-40s %-20s %-9s %9.2f MB'
              % (p[:40], str(sh)[:20], dt_, nb / 2**20))
            _cnt += 1
            if _cnt >= 6:
                break

    npass = sum([ok2, ok3, ok4])
    A('')
    A('  ★ 汇总：M2=%s  M3=%s  M4=%s  （%d/3）'
      % ('PASS' if ok2 else 'FAIL', 'PASS' if ok3 else 'FAIL',
         'PASS' if ok4 else 'FAIL', npass))
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, OUT), 'w', encoding='utf-8') as fh:
        fh.write(out + '\n')
    with open(os.path.join(HERE, OUT + '.json'), 'w', encoding='utf-8') as fh:
        json.dump({str(k): {'total': v[0], 'd0': v[2], 'd1': v[3],
                            'rows': v[1][:60]} for k, v in res.items()}, fh,
                  ensure_ascii=False, indent=1)
    return 0 if npass == 3 else 1


if __name__ == '__main__':
    sys.exit(main())
