#!/usr/bin/env bash
# _r389_box.sh -- 当前算例的盒子/分辨率事实（从 meta.json 与 run.log 直接读，不凭记忆）
R=/mnt/f/speed_up/pipeline/ca_pf_framework
cd "$R" || exit 1
echo "=== meta.json 关键项（dry_goodA_400，正在跑的臂）==="
M=_exp/_bk_mb/dry_goodA_400/meta.json
if [ -f "$M" ]; then
  /root/miniconda3/envs/ml/bin/python - "$M" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
for k in ('N', 'dx_nm', 'L', 'plate_L', 'plate_W', 'plate_T',
          'plate_t_physical', 'block_gap_nm', 'gap_nm', 'laths',
          'nthreads', 'steps', 'facet_proj', 'reinit_band', 'every',
          'snap_every', 'band_cells', 'omega_max_deg', 'omega_mode',
          'beta_h', 'beta_w', 'mob_ratio', 'aniso', 'gamma0', 'T_end',
          'alpha_km'):
    if k in d:
        print('  %-20s %s' % (k, d[k]))
print('  --- 全部键 ---')
print('  ' + ', '.join(sorted(d.keys())))
PY
else
  echo "  (还没有 meta.json)"
fi
echo
echo "=== run.log 的播种与格子事实 ==="
f=_w2_r386_run.log
[ -f "$f" ] || f=_w2_r361_run.log
grep -E 'Δx=|L=.*µm|播种|dt=|块心' "$f" 2>/dev/null | head -8
echo
echo "=== 内存/步时（正在跑的进程）==="
ps -eo pid,etimes,times,pcpu,rss,args --sort=-rss | grep '_bk_exp[.]py' \
  | sed 's/--out.*//' | head -3
echo
echo "=== 分辨率判据所需：在位场的厚度（取自最近一条进度行）==="
grep -oE '厚度\(在位的场\).*' "$f" 2>/dev/null | tail -1
