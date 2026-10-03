#!/bin/bash
# _t5_mschk.sh --- ★★★★★★ 核算 `M_s`、`T0`、`DS_REF` 与 `ΔG(M_s)` 的自检
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① `windowB_km.py` 的常数定义（T0 / Ms / DS_REF）════'
grep -nE '^T0|^M_s|^MS|^DS_REF|^T_G|_REF *=|M_s *=|MS *=|T0 *=' windowB_km.py | head -18 | cut -c1-160 | sed 's/^/  /'
echo
echo '════ ② 自检函数 `selftest` / `T_G_from_calphad`（看它断言什么）════'
L=$(grep -n 'def T_G_from_calphad' windowB_km.py | head -1 | cut -d: -f1)
[ -n "$L" ] && sed -n "${L},$((L+30))p" windowB_km.py | nl -ba -v"$L" | cut -c1-152
echo
echo '════ ③ 实测：模型到底在什么温度放第一个核（从大算例日志）════'
grep -E 'athermal 形核' _w2_t5_short_t5N276F.log 2>/dev/null | head -3 | cut -c1-190 | sed 's/^/  /'
echo
echo '════ ④ 直接算：Ms 处的 df 与 |ed| 比一比 ════'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import sys
sys.path.insert(0, '.')
try:
    import windowB_km as KM
    print('  模块常数：')
    for nm in dir(KM):
        if nm.isupper() and not nm.startswith('_'):
            v = getattr(KM, nm)
            if isinstance(v, (int, float)):
                print('     %-14s = %s' % (nm, v))
    print()
    if hasattr(KM, 'T_G_from_calphad'):
        try:
            T0, Ms, dG = KM.T_G_from_calphad()
            print('  ★ `T_G_from_calphad()` = (T0=%.2f K, Ms=%.2f K, ΔG(Ms)=%.4e J/m³)' % (T0, Ms, dG))
            print()
            print('  ── 三个温度的驱动力 ──')
            for T in (Ms, Ms - 24.0, Ms - 100.0, 298.0):
                d = KM.drive_of_T(T, T0, KM.DS_REF) if hasattr(KM, 'DS_REF') else float('nan')
                print('     T=%-7.1f K  `drive_of_T` = **%+.4e** J/m³' % (T, d))
            print()
            print('  ── 判据（**预先写死**）──')
            dMs = KM.drive_of_T(Ms, T0, KM.DS_REF)
            ed = -2.96e8
            gam = 0.25; t = 312.5e-9
            need = abs(ed) + 2 * gam / t
            print('     `|ed|`（薄板实测）        = %.4e' % abs(ed))
            print('     `2γ/t`（γ=0.25, t=312.5nm）= %.4e' % (2 * gam / t))
            print('     ⇒ **Ms 处所需驱动力**       = %.4e' % need)
            print('     ⇒ **模型 Ms 处实际 df**    = %+.4e' % dMs)
            print('     ⇒ 比值 `df(Ms)/所需` = **%.3f**' % (dMs / need))
            print()
            if dMs / need > 0.8:
                print('     ✅ Ms 处的驱动力与罚能**相当** ⇒ **标定自洽**')
                print('        ⇒ 那么"溶解"的原因不在 Ms 设定，而在**演化门槛/判据缺口**')
            else:
                print('     ❌ Ms 处的驱动力**远小于**罚能（只有 %.0f%%）⇒ **标定不自洽**'
                      % (100 * dMs / need))
                print('        ⇒ **模型的 Ms 被设得过高**（或弹性罚能偏大）—')
                print('          即：**在模型认为"已到 Ms"的温度上，其实还不够冷**')
                print('        ⇒ 核被放下后必然溶解 ✓ 与本轮全部实测吻合')
        except Exception as e:
            print('  ⚠ `T_G_from_calphad()` 调用失败：%s' % e)
    else:
        print('  ⚠ 模块里没有 `T_G_from_calphad`')
except Exception as e:
    print('  ⚠ 导入失败：%s' % e)
PYEOF
