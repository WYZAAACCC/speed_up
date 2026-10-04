#!/bin/bash
# _t5_t16vals.sh --- ★★★★★★ 读 `T16_verify_rve.py` 的 `C` 与 `EPS0` 真值，并**用真值重算薄板罚能**
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① 真值定义 ════'
grep -nE '^C *=|^EPS0 *=|^NPF *=|^DF *=|^MOB *=' T16_verify_rve.py 2>/dev/null | cut -c1-160 | sed 's/^/  /'
echo
echo '════ ② C 的定义段 ════'
LC=$(grep -n '^C *=' T16_verify_rve.py | head -1 | cut -d: -f1)
[ -n "$LC" ] && sed -n "${LC},$((LC+12))p" T16_verify_rve.py | nl -ba -v"$LC" | cut -c1-145 | sed 's/^/  /'
echo
echo '════ ③ EPS0 的定义段 ════'
LE=$(grep -n '^EPS0 *=' T16_verify_rve.py | head -1 | cut -d: -f1)
[ -n "$LE" ] && sed -n "${LE},$((LE+22))p" T16_verify_rve.py | nl -ba -v"$LE" | cut -c1-145 | sed 's/^/  /'
echo
echo '════ ④ ★ 用**真值**重算理论罚能（三档）与 Ms 判据 ════'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import sys, numpy as np
sys.path.insert(0, '.')
from T16_verify_rve import C, EPS0
import windowB_km as KM
C = np.asarray(C, float); EPS0 = np.asarray(EPS0, float)
print('  C 形状 = %s ｜ EPS0 形状 = %s（%d 个变体）' % (C.shape, EPS0.shape, len(EPS0)))
print('  C[0:3,0:3] (GPa) =\n%s' % np.array2string(C[:3, :3] / 1e9, precision=1, prefix='    '))
e0 = EPS0[0]
print('  EPS0[0] =\n%s' % np.array2string(e0, precision=4, prefix='    '))


def en(e, Cm):
    return 0.5 * float(np.einsum('ij,ijkl,kl->', e, Cm, e))


print()
print('  ── 真值下的理论罚能 ──')
for name, e in (('变体1', EPS0[0]), ('变体2', EPS0[1] if len(EPS0) > 1 else EPS0[0])):
    E_un = en(e, C)
    tr = np.trace(e); dev = e - np.eye(3) * tr / 3.0
    print('     %s：**完全约束 `½ε⁰:C:ε⁰` = %.4e J/m³** ｜ 膨胀 %.4f ｜ 偏应变范数 %.4f'
          % (name, E_un, tr, np.linalg.norm(dev)))
E_un = en(EPS0[0], C)
# 各向同性等效
C11, C12, C44 = C[0, 0], C[0, 1], C[3, 3] if C.shape[0] > 3 else C[0, 1]
K = (C11 + 2 * C12) / 3.0; G = (C11 - C12 + 3 * C44) / 5.0
nu = (3 * K - 2 * G) / (6 * K + 2 * G)
print('     各向同性等效：K=%.1f GPa G=%.1f GPa ν=%.3f' % (K / 1e9, G / 1e9, nu))
print('     ⇒ 球体（Eshelby）≈ %.3e ｜ **薄板（法向自由）≈ %.3e**'
      % (E_un * 2 * (1 - 2 * nu) / (3 * (1 - nu)), E_un * (1 - 2 * nu) / (1 - nu) * 0.5))
print()
print('  ── 与实测/代码基准对照 ──')
MEAS = 2.96e8
print('     实测（模型薄板）      = **%.3e**' % MEAS)
print('     代码球体基准(R=120nm) = 1.43e8')
print('     ⇒ 实测/完全约束 = **%.2f%%**' % (100 * MEAS / E_un))
print()
print('  ── Ms 判据 ──')
dMs = KM.drive_of_T(KM.M_S_TI64, KM.T0_TI64, KM.DS_REF)
print('     `df(Ms=873K)` = %.4e' % dMs)
print('     ⇒ `df(Ms)/实测` = **%.3f**（应 ≈1）' % (dMs / MEAS))
print('     ⇒ `df(Ms)/完全约束` = %.3f' % (dMs / E_un))
if abs(dMs - MEAS) / MEAS < 0.35:
    print('     ⇒ ✅ 实测罚能与 Ms 处驱动力**相当** ⇒ 标定自洽 ⇒ 问题在别处')
else:
    print('     ⇒ ❌ 实测罚能是 Ms 处驱动力的 **%.2f 倍** ⇒ 板条在 Ms 处站不住'
          % (MEAS / dMs))
    print('        （`df` 要到 %.3e 才够 ⇒ 对应 T ≈ %.0f K）'
          % (MEAS + 1.6e6, 298 + (3.5125e8 - MEAS - 1.6e6) / 4.15e5))
PYEOF
