#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T7_verify_dGsens.py --- T7 判据：**形貌对 ΔG 的敏感度**（决策点 D7）。

问题（`WINDOWB_EXECUTION_PLAN.md` §2 T7 / `RESEARCH_INTENT.md` §4.2 D1′）：
  **CALPHAD 目前没有数据**（`CALPHAD_REQUEST.md` 未交付）。它到底**阻不阻塞形貌**？
  若形貌对 `ΔG` 不敏感（<10%）⇒ CALPHAD 只影响"钟的快慢"，不阻塞 A2（组织正确）。
  若敏感 ⇒ CALPHAD 升级为**阻塞项**。

设计（**同一无量纲时间 τ**，单变量）：
  * 扫 3 档 `DS`（= `windowB_km.DS_BAND` 的两端与中值：1.5e5 / 3.0e5 / 6.0e5 J·m⁻³K⁻¹），
    在 `T = M_s` 处取驱动力 ⇒ `df = |drive(M_s)| = 0.5e8 / 1.0e8 / 2.0e8`
  * **同一 τ**：总位移 `Σ dt·M·df` 固定 ⇒ `nstep ∝ 1/df`（速度 ∝ df）
  * 量：三向主尺度 + **长/厚** + 长/宽 + 变体体积分数 + 界面面积
  * 判据：三个形貌量的**相对散布 < 10%** ⇒ 形貌对 ΔG 不敏感

记账：本判据**只测形貌**；`ΔG` 的绝对值仍带 4 倍不确定度（`DS_BAND`），
      **不得**据此声称"预测了 f(T)"。

用法：python3 T7_verify_dGsens.py [--N 64] [--steps-ref 300]
退出码：0 = 不敏感（CALPHAD 不阻塞形貌）
"""
import os
import sys
import json
import time
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
import windowB_km as K                                          # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
_rng = np.random.default_rng(0)
NPF = {}
for v in range(NV):
    best, bn = None, None
    for n in _rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', EPS0[v], _lam_full(C, n), EPS0[v]))
        if best is None or val < best:
            best, bn = val, n
    NPF[v + 1] = bn

MS = K.M_S_TI64


def one(df, N, dx, steps):
    """单变体板条生长到给定步数；返回形貌量与产物记录。"""
    L = N * dx
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=1e-9,
                        df=[0.0] + [float(df)] * NV, workers=4, reinit_every=25)
    R = 0.10 * L
    g.seed_plate(1, [L / 2] * 3, NPF[1], R, 4 * dx)
    g.init_parent()
    dt = 0.15 * dx / abs(1e-9 * df)
    for _ in range(steps):
        g.elastic_driving()
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.3)
    reg = g.region()
    idx = np.argwhere(reg == 1)
    if idx.size == 0:
        return None
    p = idx.astype(float) * dx
    p = p - p.mean(0)
    Cv = np.cov(p.T) if len(p) > 3 else np.eye(3)
    ev, evec = np.linalg.eigh(Cv)
    o = np.argsort(ev)[::-1]
    evec = evec[:, o]
    ext = np.array([(p @ evec[:, j]).max() - (p @ evec[:, j]).min() for j in range(3)])
    area = 0.0
    for ax in range(3):
        area += int((reg != np.roll(reg, -1, axis=ax)).sum())
    return dict(ext=ext.tolist(), V=int((reg == 1).sum()),
                area=int(area),
                AR1=float(ext[0] / max(ext[1], 1e-30)),
                AR2=float(ext[0] / max(ext[2], 1e-30)),
                AR3=float(ext[1] / max(ext[2], 1e-30)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=64)
    ap.add_argument('--dx-nm', type=float, default=25.0)
    ap.add_argument('--steps-ref', type=int, default=300)
    a = ap.parse_args()
    N, dx = a.N, a.dx_nm * 1e-9
    print('=' * 100)
    print('T7 —— 形貌对 ΔG 的敏感度（决策点 D7）   N=%d dx=%.0f nm' % (N, a.dx_nm))
    print('=' * 100)
    print('★ 记账（首版是同义反复，已修）：首版用 `T0 = T0_from_Ms(MS, DG_CRIT, DS)` 再造')
    print('  `drive_of_T(MS, T0, DS)` ⇒ 恒等于 `DG_CRIT`、**与 DS 无关** ⇒ 三档是同一个算例')
    print('  （散布 0.000 是恒等式，不是证据）。现在**直接扫驱动带**，并加宽程对照。')
    print()
    print('  驱动带（CALPHAD 的 4 倍 DS 不确定度在 ΔT 固定下映射成 4 倍 df 带）:')
    print('    df = dg_crit × {0.5, 1.0, 2.0}；宽程对照 df = dg_crit × 8（离带外）')
    rows = []
    band = [('0.5×dg_crit', 0.5 * K.DG_CRIT_REF), ('1.0×dg_crit', 1.0 * K.DG_CRIT_REF),
            ('2.0×dg_crit', 2.0 * K.DG_CRIT_REF)]
    for lab, df in band:
        steps = max(20, int(round(a.steps_ref * (1.0e8 / df))))
        t0 = time.time()
        r = one(df, N, dx, steps)
        el = time.time() - t0
        if r is None:
            print('  %-12s df=%.3e  steps=%d  ⇒ **变体消失**（无法比较形貌）'
                  % (lab, df, steps))
            rows.append(dict(lab=lab, df=df, steps=steps, ok=False))
            continue
        r.update(lab=lab, df=df, steps=steps, ok=True)
        rows.append(r)
        print('  %-12s df=%+.4e  steps=%-4d  V=%-7d  长/厚=%.3f  长/宽=%.3f  '
              '宽/厚=%.3f  界面=%d  (%.0f s)'
              % (lab, df, steps, r['V'], r['AR1'], r['AR2'], r['AR3'], r['area'], el),
              flush=True
              )
    # 宽程对照：离带 4 倍。若它的形貌也"一样" ⇒ 本方法没有分辨力 ⇒ "不敏感"无信息量
    print()
    print('  --- 宽程对照（检验**方法本身有没有分辨力**）---')
    ctl = None
    df_c = 8.0 * K.DG_CRIT_REF
    steps_c = max(20, int(round(a.steps_ref * (1.0e8 / df_c))))
    rc = one(df_c, N, dx, steps_c)
    if rc is not None:
        ctl = dict(lab='8.0×dg_crit', df=df_c, steps=steps_c, ok=True, **rc)
        print('  %-12s df=%+.4e  steps=%-4d  V=%-7d  长/厚=%.3f  长/宽=%.3f  宽/厚=%.3f'
              % ('8.0×dg_crit', df_c, steps_c, rc['V'], rc['AR1'], rc['AR2'], rc['AR3']))
    else:
        print('  %-12s df=%+.4e  ⇒ 变体消失' % ('8.0×dg_crit', df_c))

    good = [r for r in rows if r.get('ok')]
    print()
    if len(good) < 3:
        print('  ⚠ 有档次变体消失 ⇒ **本判据失效**（不是"不敏感"）。'
              '需要改用更大的初始种子或更少的步数后重测。')
        print('  ⇒ T7 判定：**未定**（算例退化，不能下结论）')
        return 2

    def spread(key):
        v = np.array([r[key] for r in good], float)
        return float((v.max() - v.min()) / max(abs(v.mean()), 1e-30)), v
    print('  %-10s %-28s %-10s' % ('量', '三档值', '相对散布'))
    worst = 0.0
    for key in ('AR1', 'AR2', 'AR3'):
        s, v = spread(key)
        worst = max(worst, s)
        print('  %-10s %-28s %.3f' % (key, ' '.join('%.3f' % x for x in v), s))
    for key, lab in (('V', '变体体积'), ('area', '界面键数')):
        s, v = spread(key)
        print('  %-10s %-28s %.3f' % (lab, ' '.join('%.0f' % x for x in v), s))
    print()
    print('  判据：三个形貌比（长/厚、长/宽、宽/厚）的相对散布都要 **< 0.10**')
    if ctl is not None:
        vc = np.array([ctl['AR1'], ctl['AR2'], ctl['AR3']])
        vm = np.array([np.mean([r[k] for r in good]) for k in ('AR1', 'AR2', 'AR3')])
        dev = float(np.max(np.abs(vc - vm) / np.maximum(np.abs(vm), 1e-30)))
        print('  方法分辨力检验：带外档（8×）与带内均值的最大偏差 = %.4f ⇒ %s'
              % (dev, '**有分辨力**' if dev > 0.10 else '**无分辨力**（"不敏感"无信息量）'))
        has_power = dev > 0.10
    else:
        has_power = True
        print('  方法分辨力检验：带外档变体消失 ⇒ 视为有分辨力（它在极端驱动下行为不同）')
    print('  最大散布 = %.3f  ⇒ 形貌对 ΔG %s'
          % (worst, '**不敏感**（<10%）⇒ **CALPHAD 不阻塞形貌** ✓'
             if worst < 0.10 else '**敏感**（≥10%）⇒ CALPHAD 升级为阻塞项 ⚠'))
    if worst < 0.10 and not has_power:
        print('  ⚠⚠ 但方法**无分辨力** ⇒ 上面的"不敏感"**不能**作为决策依据；')
        print('      必须先让判据能看见差异（例如换更宽的驱动范围或更长的 τ）。')
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           '_t7_result.json'), 'w') as f:
        json.dump(dict(N=N, dx_nm=a.dx_nm, steps_ref=a.steps_ref,
                       rows=rows, control=ctl, worst_spread=worst,
                       method_has_power=bool(has_power),
                       verdict=('insensitive' if (worst < 0.10 and has_power)
                                else ('sensitive' if worst >= 0.10 else 'no_power'))),
                  f, ensure_ascii=False, indent=1)
    ok = (worst < 0.10) and has_power
    print('  ⇒ T7: %s' % ('PASS（不敏感且方法有分辨力）' if ok else 'FAIL'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
