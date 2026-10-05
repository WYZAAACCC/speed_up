#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
echo "=== 三维视觉验证（t10PRT2 @ step100）==="
for K in 14 111 119; do
  $PY _t5_split3d2.py t10PRT2 $K 100 2>&1 | tail -1
done
echo
echo "=== 当前状态 ==="
EN=""
for P in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10PRT2 "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then
  ps -o etime,pcpu --no-headers -p "$EN" | sed 's/^/  /'
  awk '/^VmHWM|^VmSwap/{printf "  %s\n", $0}' /proc/$EN/status
else echo "  引擎不在"; fi
free -m | sed -n '2,3p' | sed 's/^/  /'
grep -aE '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t10PRT2.log 2>/dev/null | tail -2 | cut -c1-115
echo
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t10_p2.sh pipeline/ca_pf_framework/_t10_p2verdict2.sh \
        pipeline/ca_pf_framework/_t10_deadseed.py pipeline/ca_pf_framework/_t10_ev70.py
git commit -q -m '★★★ 七项监控全部达标（t10PRT2 @step100，含 s304b 核保护）：死核率 21%→**0%**（39 个形核事件/39 个互不相同场/唯一性1.000/快照 40 个变体场=39事件场+初始籽晶/无任何 <30 胞的场）；⑦ 一场一板条 40/40=100%（分量数均值1.00）；② 长/厚 11.34≥10；③ 长/宽 5.95；④⑤⑥ nblk=16 n_var_sig=4 blk_laths=10/4/4/3/3/3/2/2/2/1/1/1（最大块10根）；[SEEDCARVED] 42 行且 protected 含 0 的行数=0；swap 全程 0。★ 读数澄清：deadseed 输出里 124-126/162 被判死核是我的 WATCH 列表过时（那是 t10CL2 的死核号，t10PRT2 本就未在这些场形核）⇒ 判据必须以「事件场号 vs 快照场号」集合差为准'
git log --oneline -1
