#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== ① --cool-rate 0 时 T(t) 走哪条路径 ==="
grep -nE "cool_rate|linear_cool|_T_of_t|from_cooling_rate" _bk_exp.py | head -24 | cut -c1-150 | sed 's/^/  /'
echo
echo "=== ② --burst-km / nuc_law 是否内部设定 fresh-every ==="
grep -nE "burst_km|nuc_law|nuc_fresh_every" _bk_exp.py | head -30 | cut -c1-150 | sed 's/^/  /'
echo
echo "=== ③ 日志里实际生效的 T 表 / 冷速（从已跑算例的 banner 取）==="
for L in _w2_t5_short_t10PRT2_b3_1005_1213.log _w2_t5_short_t10B9.log _w2_t5_short_t10CL2_ok.log; do
  [ -f "$L" ] || continue
  echo "  --- $L ---"
  grep -aE "冷速|T_start|T_end|时钟|qs|fresh|K =|n\(T" "$L" 2>/dev/null | head -6 | tr -d '\r' | cut -c1-150 | sed 's/^/    /'
done
echo
echo "=== ④ 归档 meta.json 里的实际参数（最能说明"实际用了什么"）==="
for D in dry_t10PRT2_b3_1005_1213 dry_t10B9 dry_t10CL2_ok_1005_0946 dry_t10FIX_p1_1005_0708; do
  F="_exp/_bk_t5/$D/meta.json"
  [ -f "$F" ] || continue
  echo "  --- $D ---"
  /root/miniconda3/envs/ml/bin/python -c "
import json,sys
d=json.load(open('$F'))
ks=['gamma0','beta_h','beta_w','cool_rate','T_end','nuc_fresh_every','nuc_block_target','nuc_init','nuc_sites_refill','nuc_law','burst_km','B','nv','N','dx_nm','ed_eta','nuc_block_parallel','nuc_occ_guard']
for k in ks:
    if k in d: print('    %-22s = %s' % (k, d[k]))
" 2>/dev/null || echo "    （读取失败）"
done
