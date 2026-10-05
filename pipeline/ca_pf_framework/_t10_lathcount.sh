#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
L=_w2_t5_short_t10PRT2.log
echo "=== 板条数上限的诊断 ==="
echo "--- s292 补投轮（每档目标）---"
grep -a 's292 补投轮' "$L" 2>/dev/null | sed 's/^/  /'
echo "--- 形核事件的步分布与温度（看有几档、每档投多少）---"
grep -a 'athermal 形核' "$L" 2>/dev/null | grep -oE '@ step [0-9]+：T=[0-9.]+ K' | sort | uniq -c | sed 's/^/  /'
echo "--- 每块根数 / 目标（从日志抓 n(T) 与 _tgt）---"
grep -a 'n(T' "$L" 2>/dev/null | tail -6 | sed 's/^/  /'
grep -aE 'n_law|每块根数|本档目标' "$L" 2>/dev/null | tail -8 | sed 's/^/  /'
echo "--- 引擎侧的 nvar/m/nuc-block-target ---"
EN=""
for P in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10PRT2 "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then
  tr '\0' ' ' < /proc/$EN/cmdline | grep -oE '\-\-nvar [0-9]+|\-\-m [0-9]+|\-\-nuc-block-target [0-9]+|\-\-nuc-init [0-9]+' | tr '\n' ' ' | sed 's/^/  /'
  echo
fi
echo "--- 当前场数（step100 快照）---"
/root/miniconda3/envs/ml/bin/python - <<'PY'
import numpy as np
with np.load("_exp/_bk_t5/dry_t10PRT2/snap_00100.npz", allow_pickle=False) as z:
    bv = np.asarray(z["band_val"]).ravel(); bf = np.asarray(z["band_fld"]).ravel()
ks = [int(k) for k in np.unique(bf[bv < 0]) if int(k) != 0]
big = [k for k in ks if int(((bf == k) & (bv < 0)).sum()) >= 30]
print("  有带内胞的变体场 = %d（其中 >=30 胞 = %d）" % (len(ks), len(big)))
PY
echo "--- 状态 ---"
free -m | sed -n '2,3p' | sed 's/^/  /'
grep -aE '^ *\[ *[0-9]+\] Vt=' "$L" 2>/dev/null | tail -2 | cut -c1-90
