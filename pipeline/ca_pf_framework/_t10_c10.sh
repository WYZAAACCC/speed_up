#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== t10B9 状态 ==="
EN=""
for P in $(ls /proc 2>/dev/null | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in *bk_exp.py*"--tag t10B9 "*) EN=$P; break ;; esac
done
if [ -n "$EN" ]; then
  ps -o etime,pcpu --no-headers -p "$EN" | sed 's/^/  /'
  awk '/^VmRSS|^VmHWM|^VmSwap/{printf "  %s\n", $0}' /proc/$EN/status
else echo "  ⚠ 引擎不在"; fi
free -m | sed -n '2,3p' | sed 's/^/  /'
echo -n "  形核事件行 = "; grep -ac 'athermal 形核' _w2_t5_short_t10B9.log 2>/dev/null
echo -n "  首档目标行 = "; grep -a 's292 补投轮' _w2_t5_short_t10B9.log 2>/dev/null | tail -2 | tr -d '\r' | sed 's/^/    /'
echo -n "  块数（应 9）= "; grep -ao '共 [0-9]* 块' _w2_t5_short_t10B9.log 2>/dev/null | tail -1
echo "--- swap 盯守尾 ---"; tail -2 _w2_t10_swapfix2.log 2>/dev/null

cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t10_periodic_chk.py
git commit -q -F - <<'MSG'
新增监控项「板条长出盒子时周期边界是否正确」+ 量具自检（_t10_periodic_chk.py）：

★ 量具风险自查：_t10_allfields.py / _t10_seven.py 一直用 ndimage.label(structure=S26) **非周期**连通性；若板条横跨周期面（+x↔−x），其胞物理上是一根却会被**数成两块** ⇒ 会虚增碎片、压低 ⑦。

首测（t10PRT2_b3_1005_1213 @step100，40 个场）：
· P1 同时出现在两个相对面附近的场 = **0** ⇒ 当前**没有板条跨出盒子**，周期 BC 尚未被行使
· P2 因周期连通而被合并的场 = **0**
· P3 ⑦：非周期口径 40/40 = 100%，周期口径 40/40 = 100% ⇒ **两种口径一致** ⇒ 此前 ⑦ 的测量**未受该量具缺陷影响**（正对照成立）
· P4 无跨面容，暂不可测

⇒ 结论：量具缺陷**真实存在但当前未激活**；周期性判据 P1/P2/P3/P4 已建成，须在**后续步（板条长大到触及盒面时）复测**。t10B9 的板条更多（207）且会长更大 ⇒ 更可能触及盒面，是复测的主场。
MSG
git log --oneline -1
