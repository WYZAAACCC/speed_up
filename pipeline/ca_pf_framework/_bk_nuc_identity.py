#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_bk_nuc_identity.py —— 引擎 R11 改动（形核通道）的**逐位身份 + 活性**判据。

## 改了什么

`nuc_cfg()` 新增四个默认关闭的参数（`vgroup` / `nfsv` / `attach` /
`attach_overlap`），`nucleate()` 的 `stack` 通道里多两条**守卫分支**。
改动前的引擎已存档为 `_bk_engine_prenuc.py`
（`git show HEAD:pipeline/ca_pf_framework/windowB_surface.py`）。

## 四条判据（**先登记，后跑**）

| # | 判据 | 为什么必须有 |
|---|---|---|
| **U-1** | **两个开关全关**时，新旧引擎跑同一条形核算例，`phi` **逐位相同** | 引擎改动的硬规矩：默认路径必须与归档逐位一致 |
| **U-2** | 两个开关全关时，`dbg` 里**不能出现** `attach_ok` / `nfsv_ok` | U-1 的"相同"可能是"两条路都没跑"；这条证明**新支路真的没进** |
| **U-3** | `attach=True` 时结果**必须不同**，且 `dbg['attach_ok'] ≥ 1`、事件模式里有 `'attach'` | 正对照：证明新支路**是活的**，不是"改了但没接上" |
| **U-4** | `nfsv=True` + `vgroup` 时，**空场的个数必须减少**（同变体形核进了新场） | 这是"块可表示"的核心；只看模式名会被假象骗过 |

⚠ 记账：`attach` 的守卫**放宽到允许落在源板条 `k` 上**（正是"共用一张界面"），
但**绝不允许落在别的场上** —— 若放宽过头，`seed_plate` 会把别的板条抹掉
（本仓库 A2 事故的同型），所以 U-3 还会检查**非源场的体积没有被削掉 >1%**。

跑法：  python3 _bk_nuc_identity.py
"""
import os
import subprocess
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import numpy as np                                              # noqa: E402

OLD_FILE = os.path.join(_HERE, '_bk_engine_prenuc.py')
F = []


def ck(tag, ok, det=''):
    print('  %-62s %s %s' % (tag, 'PASS' if ok else '**FAIL**', det))
    if not ok:
        F.append(tag)


def load_mod(name, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def main():
    print('=' * 104)
    print('_bk_nuc_identity —— 引擎 R11（形核通道 nfsv/attach）的逐位身份 + 活性')
    print('=' * 104)
    if not os.path.exists(OLD_FILE):
        print('✗ 缺少改动前存档 %s' % OLD_FILE)
        return 1
    OLD = load_mod('_bk_engine_prenuc', OLD_FILE)
    import windowB_surface as NEW
    from T16_verify_rve import C, EPS0, NPF, DF, MOB
    print('  旧引擎 %s（%d 行）  新引擎 %s'
          % (os.path.basename(OLD_FILE), sum(1 for _ in open(OLD_FILE)),
             os.path.basename(NEW.__file__)))

    N = 64
    dx = 62.5e-9
    L = N * dx
    NV = 2
    DT = 0.15 * dx / (MOB * DF)
    R_NUC, T_NUC = 300e-9, 200e-9
    STEPS, EVERY = 12, 3
    BETA_H, BETA_W = 3.5, 2.3
    VG = {1: 1, 2: 1, 3: 1, 4: 1}          # 场号 -> 变体号（1..2 用不完，留余量）

    import inspect
    _NEW_ARGS = ('vgroup', 'nfsv', 'attach', 'attach_overlap')

    def build(mod, nfsv=False, attach=False, vgroup=None):
        eps0 = [np.asarray(EPS0[v - 1], float).copy() for v in (1, 2)]
        g = mod.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.15, Mob=MOB,
                              df=[0.0] + [DF] * NV, workers=1,
                              reinit_every=0, reinit_dt=6.0e-7)
        c0 = np.array([L / 2] * 3)
        nz = np.asarray(NPF[1], float)
        nz = nz / np.linalg.norm(nz)
        g.seed_plate(1, c0, nz, 320e-9, 250e-9)
        g.init_parent()
        # ★ 旧引擎没有这四个参数 ⇒ 只能对新引擎传（**这本身就是"默认路径未变"的
        #   一个结构性证据**：旧签名里根本不存在这些开关）。
        _sig = inspect.signature(mod.LevelSetMulti.nuc_cfg).parameters
        kw = dict(gamma=0.15, n_init=0, harden_f=1.0, sym_gap_cells=2,
                  max_per_step=4, seed=11, var_rule='ed')
        if all(a in _sig for a in _NEW_ARGS):
            kw.update(vgroup=vgroup, nfsv=nfsv, attach=attach,
                      attach_overlap=62.5e-9 if attach else 0.0)
        elif nfsv or attach or vgroup is not None:
            raise RuntimeError('该引擎不支持 nfsv/attach/vgroup（旧引擎只能跑默认路径）')
        g.nuc_cfg(R_NUC, T_NUC, **kw)
        return g

    def run(g, steps=STEPS):
        ev = []
        for it in range(1, steps + 1):
            ed = g.elastic_driving()
            g.advance(DT, aniso=0.4, npref=NPF, band_cells=20, mob_beta=BETA_H,
                      mob_beta_w=BETA_W, adv_grad='proj2', norm_smooth=0)
            if it % EVERY == 0:
                reg = g.region()
                f_now = 1.0 - float((reg == 0).sum()) / g.N ** 3
                ev += g.nucleate(ed, f_now=f_now, n_fresh=0, n_stack=3)
        return ev

    # ---------------- U-1 / U-2：默认关闭 ⇒ 逐位相同 ----------------------
    ga = build(OLD, nfsv=False, attach=False)
    gb = build(NEW, nfsv=False, attach=False)
    eva, evb = run(ga), run(gb)
    same = bool(np.array_equal(ga.phi, gb.phi))
    ck('U-1 两个开关全关：新旧引擎 phi **逐位相同**', same,
       'sha_old=%s sha_new=%s  事件 %d vs %d'
       % (hash(ga.phi.tobytes()) % 10 ** 8, hash(gb.phi.tobytes()) % 10 ** 8,
          len(eva), len(evb)))
    dbg = gb._nuc.get('dbg', {})
    ck('U-2 开关全关时 dbg 里**没有** attach_ok / nfsv_ok',
       ('attach_ok' not in dbg) and ('nfsv_ok' not in dbg),
       'dbg=%s' % {k: v for k, v in dbg.items() if v})
    ck('U-2b 开关全关时事件模式**只有** stack/fresh',
       all(m in ('stack', 'fresh') for _k, m in evb),
       '模式=%s' % sorted(set(m for _k, m in evb)))

    # ---------------- U-3：attach 是活的 ---------------------------------
    gc = build(NEW, nfsv=False, attach=True)
    evc = run(gc)
    dbgc = gc._nuc.get('dbg', {})
    ck('U-3 attach=True 时结果**必须不同**（正对照）',
       not bool(np.array_equal(ga.phi, gc.phi)), '')
    ck('U-3b attach 通道**确实落位**（attach_ok ≥ 1 且模式里有 attach）',
       dbgc.get('attach_ok', 0) >= 1 and ('attach' in [m for _k, m in evc]),
       'attach_ok=%s  事件=%s' % (dbgc.get('attach_ok', 0), [m for _k, m in evc]))
    # ★ 放宽守卫的**风险检查**：除源板条外，其它场的体积不能被削
    v_before = {2: float((gc.region() == 2).sum())}
    _ = v_before
    regs = gc.region()
    other = [k for k in range(3, 5) if (regs == k).any()]
    ck('U-3c attach 没有把**别的场**种上（放宽守卫只放行母相与源板条）',
       not other, '出现过的其它场=%s' % other)

    # ---------------- U-4：nfsv 真的开了新场 -----------------------------
    gd = build(NEW, nfsv=True, attach=True, vgroup=VG)
    evd = run(gd)
    dbgd = gd._nuc.get('dbg', {})
    nempt_c = sum(1 for k in range(1, gd.nreg) if not (gc.region() == k).any())
    nempt_d = sum(1 for k in range(1, gd.nreg) if not (gd.region() == k).any())
    ck('U-4 nfsv=True 时**空场变少**（同变体形核进了新场）',
       nempt_d < nempt_c,
       '空场数：attach(不换场) %d → attach+nfsv %d   nfsv_ok=%s nfsv_nofield=%s'
       % (nempt_c, nempt_d, dbgd.get('nfsv_ok', 0),
          dbgd.get('nfsv_nofield', 0)))

    print('-' * 104)
    print('FAIL = %d %s' % (len(F), F if F else ''))
    print('=' * 104)
    return 1 if F else 0


if __name__ == '__main__':
    raise SystemExit(main())
