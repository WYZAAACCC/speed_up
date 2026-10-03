#!/bin/bash
# _t5_fillnum.sh --- ★★★ 填满盒子需要多少根板条（核实引擎口径 + 算两种尺度）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo '════ ① 引擎横幅里的"盒体积 / 单根板条体积"（官方口径）════'
grep -rhoE '几何上界[^|]*|1000\.0 µm³[^|]*|µm³ / [0-9.]+ µm³[^|]*|总根数 = [^|]*|导出板条数 n = [^|]*' \
  _w2_t5_short_t5AD_700.log _w2_t5_short_t5AB_A.log 2>/dev/null | sort -u | head -10 | sed 's/^/  /'
echo
echo '════ ② 直接从日志抓"板条体积"与"盒体积"两个数 ════'
grep -rhoE '[0-9.]+ µm³ / [0-9.]+ µm³' _w2_t5_short_*.log 2>/dev/null | sort -u | head -4 | sed 's/^/  /'
grep -rhoE '盒 *= *[0-9.]+ *µm|L_box *= *[0-9.]+' _w2_t5_short_t5AD_700.log 2>/dev/null | sort -u | head -4 | sed 's/^/  /'
echo
echo '════ ③ 离线算（两种尺度 × 两种板条体积）════'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
DX = 62.5e-3   # µm
seed = 1000*500*510 * 1e-9   # nm³ -> µm³
grown = 3223 * (62.5**3) * 1e-9   # 实测最大场：3223 体素
print('  单根**种子**体积 = %.4f µm³（= plate_L×W×T = 1000×500×510 nm³）' % seed)
print('  单根**长大**体积 = %.4f µm³（实测 t5H3 最大场 3223 体素 × (62.5 nm)³）' % grown)
print()
print('  %-22s %-14s %-16s %-16s' % ('计算盒', '体积(µm³)', '需板条(种子)', '需板条(长大)'))
print('  ' + '-' * 74)
for N in (80, 160):
    L = N * DX
    V = L ** 3
    print('  %-22s %-14.1f %-16.0f %-16.0f'
          % ('N=%d（%.2f µm）' % (N, L), V, V / seed, V / grown))
print()
print('  ── 与**场预算**对照（这才是硬约束）──')
n_tend = 23
for N in (80, 160):
    for nv in (72, 138, 276, 490, 600):
        nvar_max = nv // n_tend
        # 每场内存：N³ × 40 B
        gb = (N ** 3) * 40 * nv / 1073741824.0
        if nv in (72, 276, 490):
            print('    N=%-4d nv=%-4d ⇒ nvar 上限 %-3d ｜ 内存 ~%5.1f GB ｜ 可容板条 %d 根'
                  % (N, nv, nvar_max, gb, nv))
    print()
PYEOF
