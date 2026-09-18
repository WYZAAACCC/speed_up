#!/bin/bash
# 展示分配系数验证结果。
# 【坑】内联 for 循环里的 $T 会被 Git Bash->WSL 吞掉，必须写脚本。
printf "  %-4s %-10s %-10s %-12s %-12s %-10s %s\n" "变体" "A_part" "公式k" "c_solid" "c_liquid" "实测k" "偏差"
echo "  ------------------------------------------------------------------------"
show() {
  T=$1; AP=$2; KC=$3
  L=/root/work/verify_k/$T/v_out.csv
  if [ ! -f "$L" ]; then echo "  $T  无 CSV"; return; fi
  tail -1 "$L" | awk -F, -v t="$T" -v ap="$AP" -v kc="$KC" '{
    # 列序: time,c_liquid,c_solid,gr0_liquid,gr0_solid
    cl=$2; cs=$3;
    kf = 1.0/(1.0 + 2.0*ap/kc);
    km = (cl!=0) ? cs/cl : 0;
    dev = (kf!=0) ? (km-kf)/kf*100 : 0;
    if (dev<0) dev=-dev;
    printf "  %-4s %-10.5g %-10.4f %-12.6f %-12.6f %-10.4f %.3f%%%s\n", t, ap, kf, cs, cl, km, dev, (dev<1.0 ? "  OK" : "  **不符**");
  }'
}
show A 0.45    0.9
show B 0.264   0.9
show C 0.00918 0.9
echo
echo "  判据：偏差 < 1% 则 k = 1/(1 + 2*A_part/k_c) 确认。"
echo
echo "  --- 稳定性检查：剖面前后是否漂移（应驻定）---"
for T in A B C; do
  L=/root/work/verify_k/$T/v_out.csv
  [ -f "$L" ] || continue
  echo "  $T: $(tail -1 "$L" | cut -d, -f1) 时刻  c_solid=$(tail -1 "$L" | cut -d, -f3)"
done
