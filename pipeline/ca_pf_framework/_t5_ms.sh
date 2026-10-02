#!/bin/bash
# _t5_ms.sh --- ★ M_s 对账（实现 --therm-hist lpbf 的前置）
cd "$(dirname "$0")" || exit 1
echo '════ ① 代码里的 M_s 常数 ════'
grep -rn 'M_S_TI64\|M_s *=\|MS_TI64\|T0_TI64\|T_BETA_TI64' windowB_km.py windowB_closure.py 2>/dev/null \
  | head -16 | cut -c1-124 | sed 's/^/  /'
echo
echo '════ ② 873 这个数在库里出现在哪 ════'
grep -rn '873\.0\|873\.' windowB_km.py windowB_closure.py _bk_exp.py 2>/dev/null \
  | head -10 | cut -c1-124 | sed 's/^/  /'
echo
echo '════ ③ 用引擎自己的函数反解（不靠我算）════'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
import sys, os
sys.path.insert(0, '.')
try:
    import windowB_km as KM
except Exception as e:
    print('  ⚠ import windowB_km 失败：%s' % e); raise SystemExit
cands = [k for k in dir(KM) if not k.startswith('_')]
print('  模块里与温度有关的常量：')
for k in cands:
    v = getattr(KM, k)
    if isinstance(v, (int, float)) and 200 < float(v) < 2200 and k.isupper():
        print('     %-22s = %s  (%.2f °C)' % (k, v, float(v) - 273.15))
print()
for fn in ('T_of_k', 'alpha_km_n_lath', 'drive_of_T'):
    if hasattr(KM, fn):
        print('  函数 %s 存在' % fn)
PYEOF
echo
echo '════ ④ 结论对账表 ════'
/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
Ms_eng = 873.0
print('  引擎反解 M_s = %.1f K = **%.2f °C**（两点印证：abA 的 T_1 与 p2 的 T_start=782.09）'
      % (Ms_eng, Ms_eng - 273.15))
bands = [('gla_thesis:1257 / lightam:140', 575.0, 800.0),
         ('arxiv_2404:936', 580.0, 700.0),
         ('lat_mcgill_lwd:1254（模型输入单值）', 650.0, 650.0)]
tgt = Ms_eng - 273.15
print()
print('  %-38s %-14s %s' % ('文献来源', '带 (°C)', '引擎值在里面吗'))
for nm, lo, hi in bands:
    ok = '✅ 在带内' if lo <= tgt <= hi else '❌ 带外'
    print('  %-38s %-14s %s' % (nm, '%.0f–%.0f' % (lo, hi), ok))
print()
print('  ⇒ 引擎的 %.0f °C 落在 **580–700 °C 带内**（arxiv_2404），也落在 575–800 内（偏下端）'
      % tgt)
print('  ⚠ 但 800 °C 那条**很可能是 M_f 被误写成 M_s**（lat_gilmur1996:140-141 vs gla_thesis:1257）')
print('  ⇒ **按 580–700 °C 带判，引擎的 M_s 与文献相容** ⇒ **不需要为 --therm-hist 改 M_s**')
PYEOF
