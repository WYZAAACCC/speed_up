#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r580_p1check.py --- R580/P1 的**单元判据**：`onfly` 的诊断口径是否已与归档对齐。

## 判据（先写死，必须能失败）
* **Q1 step-0 口径**：刚建好、还没跑过弹性求解时，`onfly` 的 `E_el()` 必须
  **与 materialized 逐位相同**（归档那时 `pf.phi` 是全零 bool ⇒ ε⁰ ≡ 0）。
  ⚠ 这是最容易漏的一条：修之前 `onfly` 在这里会给出**非零**的 ε⁰。
* **Q2 稳态口径**：跑若干步（含一次 `elastic_driving`）后，两档的 `E_el()`
  **逐位相同**。
* **Q3 滞后语义**：跑一步后**手动改 `g.phi`**（模拟 advance 里的推进），
  两档的 `E_el()` 仍必须**逐位相同** —— 即**都不跟着 `g.phi` 走**
  （物化档读 `pf.phi`、onfly 档读 `_eps0_lag`）。
* **Q4 负对照（必须失败）**：人为把 `_eps0_lag` 改成全零 ⇒ `E_el()` **必须变**。
  若不变，说明 `E_el` 根本没在读 stash ⇒ Q1–Q3 是假通过。
* **Q5 负对照（必须失败）**：清掉 `_eps0_lag`（=None）而 `_h_src` 仍在 ⇒
  `E_el()` **必须变成 0**（"还没有过弹性求解"的语义）。
* **Q6 缓存清理**：切回 materialized 后 `_eps0_lag` 必须是 `None`。
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_surface as W                                    # noqa: E402
from T16_verify_rve import C, EPS0                             # noqa: E402

N = int(os.environ.get('R580P_N', '40'))
NV = int(os.environ.get('R580P_NV', '8'))
DX = float(os.environ.get('R580P_DX', '0.0625'))
WORK = int(os.environ.get('R580P_WORKERS', '4'))
OUT = os.environ.get('R580P_OUT', '_w2_r580_p1check.log')
L = []
A = L.append


def build(mode):
    eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(NV)]
    g = W.LevelSetMulti(N, N * DX, C=C, eps0=eps, gamma=0.25, Mob=1e-9,
                        df=[0.0] + [3.0e8] * NV, workers=WORK,
                        reinit_every=20, reinit_dt=1e-4, reinit_band_cells=6.0,
                        phi_prec='f64', pf_phi_mode=mode, h_chunk=4)
    g.init_parent()
    rng = np.random.default_rng(7)
    nrm = np.array([0.0, 0.0, 1.0])
    Lc = N * DX
    for k in range(1, max(3, NV // 8) + 1):
        g.seed_plate(k, rng.random(3) * (Lc * 0.6) + Lc * 0.2, nrm, 120e-9, 300e-9)
    return g


def rel(x, y):
    m = max(abs(x), abs(y))
    return 0.0 if m == 0.0 else abs(x - y) / m


def main():
    A('=' * 92)
    A('R580-P1 —— `onfly` 诊断口径是否已与归档对齐（N=%d nv=%d）' % (N, NV))
    A('=' * 92)
    ok = True

    gmat = build('materialized')
    gon = build('onfly')

    # ---------- Q1：step-0（还没有过弹性求解）----------
    e_mat = float(gmat.pf.E_el())
    e_on = float(gon.pf.E_el())
    A('')
    A('  Q1 首次弹性求解**之前**的 `E_el()`：')
    A('     materialized = %.17e' % e_mat)
    A('     onfly        = %.17e' % e_on)
    A('     `_eps0_lag` = %s（应为 None）' % (None if gon.pf._eps0_lag is None
                                             else 'array'))
    q1 = (e_mat == e_on) and (gon.pf._eps0_lag is None)
    A('     ⇒ %s' % ('✅ 逐位相同（都是 0）' if q1 else '❌ 不等'))
    ok = ok and q1

    # ---------- Q2：跑一步后 ----------
    for g in (gmat, gon):
        g.elastic_driving()
    e_mat = float(gmat.pf.E_el())
    e_on = float(gon.pf.E_el())
    A('')
    A('  Q2 一次 `elastic_driving()` **之后**：')
    A('     materialized = %.17e' % e_mat)
    A('     onfly        = %.17e' % e_on)
    A('     `_eps0_lag` 已填：%s' % (gon.pf._eps0_lag is not None))
    q2 = (e_mat == e_on and e_mat != 0.0
          and gon.pf._eps0_lag is not None
          and gon.pf._eps0_lag.shape == (6, N, N, N))
    A('     ⇒ %s（相对差 %.3e）'
      % ('✅ 逐位相同' if q2 else '❌ 不等', rel(e_mat, e_on)))
    ok = ok and q2

    # ---------- Q3：手动推进 g.phi 后，两档仍须一致（都不跟着走）----------
    rng = np.random.default_rng(11)
    pert = rng.standard_normal(gon.phi.shape) * 1e-4
    gmat.phi += pert
    gon.phi += pert
    e_mat2 = float(gmat.pf.E_el())
    e_on2 = float(gon.pf.E_el())
    A('')
    A('  Q3 手动扰动 `g.phi`（模拟 advance 里的推进）**之后**：')
    A('     materialized = %.17e  （与 Q2 相同？%s）' % (e_mat2, e_mat2 == e_mat))
    A('     onfly        = %.17e  （与 Q2 相同？%s）' % (e_on2, e_on2 == e_on))
    q3 = (e_mat2 == e_mat) and (e_on2 == e_on) and (e_mat2 == e_on2)
    A('     ⇒ %s' % ('✅ 两档都不跟着 `g.phi` 走，且逐位相同' if q3 else '❌ 有档跟着走了'))
    ok = ok and q3

    # ---------- Q4 负对照：改 stash 必须改变结果 ----------
    saved = gon.pf._eps0_lag.copy()
    gon.pf._eps0_lag = np.zeros_like(saved)
    e_bad = float(gon.pf.E_el())
    q4 = (e_bad != e_on2)
    A('')
    A('  Q4 负对照（把 `_eps0_lag` 置零）：E_el = %.6e（原 %.6e）⇒ %s'
      % (e_bad, e_on2, '✅ 有分辨力' if q4 else '❌ **无分辨力**：E_el 根本没读 stash'))
    ok = ok and q4
    gon.pf._eps0_lag = saved

    # ---------- Q5 负对照：清空 stash 必须回到"全零"语义 ----------
    gon.pf._eps0_lag = None
    e_non = float(gon.pf.E_el())
    q5 = (e_non == 0.0)
    A('  Q5 负对照（清空 `_eps0_lag`）：E_el = %.6e ⇒ %s'
      % (e_non, '✅ 回到 0（"还没有过弹性求解"）' if q5 else '❌ 不是 0'))
    ok = ok and q5

    # ---------- Q6 切回 materialized 必须清缓存 ----------
    gon._pf_phi_mode = 'materialized'
    gon._soft_sigma()
    q6 = (gon.pf._eps0_lag is None) and (gon.pf._h_src is None)
    A('  Q6 切回 materialized 后 `_eps0_lag is None`：%s ⇒ %s'
      % (gon.pf._eps0_lag is None, '✅' if q6 else '❌ 缓存没清（会读到过期值）'))
    ok = ok and q6

    A('')
    A('  === RESULT: %s ===' % ('ALL PASS' if ok else 'FAIL'))
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, OUT), 'w', encoding='utf-8') as fh:
        fh.write(out + '\n')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
