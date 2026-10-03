#!/bin/bash
# _t5_stop_old2.sh --- 按**精确 pid** 停掉已定论的 4 条臂（数据一概不动）
#
# ## 要停的（pid → tag 取自 `_t5_whopid.sh` 的实测映射）
#   pid=27094  t5AB_B    （eng-elong=3.75 剂量点已稳定，且被 5/7/10 覆盖）
#   pid=27101  t5AB_C    （facet-proj=1 已判定有害 —— §186/§219/§221 三条独立罪证）
#   pid=27103  t5AB_D    （facet+elong7 同样被 facet 拉平，同属已判死）
#   pid=28950  t5AD_500  （eng-elong=5 剂量点已稳定，多步点确认）
#
# ## 要留的（**有同末步对照/尚在跟踪**）
#   pid=27090  t5AB_A    （t5AM_ell 的对照）
#   pid=28948  t5AD_700  （t5AM_combo 的对照）
#   pid=29707  t5AD_1000 （最高剂量，稳定性仅到 step 120）
#   pid=33073  t5AM_ell  ·  pid=33075  t5AM_combo  （本目标验证臂）
#   pid=11386  t5V2      （N=160 长臂，判据④ 未达成）
#
# ## 安全
# **按精确 pid**（绝不用 `pkill -f` —— 会杀到自己的 shell，AGENTS.md §3.10）；
# **先 TERM**（走正常退出路径、打退出摘要），12 s 后仍在才 **KILL**；
# **数据一概不动**（不删、不 mv —— 本来就该留在 F 盘）。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
LOG=_w2_t5_stop_old.log
say() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

STOP_PIDS="27094 27101 27103 28950"
say '════ 按精确 pid 停 4 条已定论的臂（第二轮，修正匹配）════'
say '  原因：第一轮用 `grep dry_<tag>` 匹配失败 —— 引擎命令行里是 `--tag <tag>`，不是 `dry_<tag>`'
free -m | sed -n 2p | awk '{printf "  停前内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"

for P in $STOP_PIDS; do
  T=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null | grep -oE '\-\-tag [A-Za-z0-9_]+' | awk '{print $2}')
  if kill -TERM "$P" 2>/dev/null; then say "  已 TERM pid=$P（tag=${T:-?}）"
  else say "  ⚠ pid=$P 不存在或已退出（tag=${T:-?}）"; fi
done
sleep 14
for P in $STOP_PIDS; do
  T=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null | grep -oE '\-\-tag [A-Za-z0-9_]+' | awk '{print $2}')
  if kill -9 "$P" 2>/dev/null; then say "  TERM 未生效 ⇒ 已 KILL pid=$P（tag=${T:-?}）"; fi
done
sleep 4

say '  ── 停后核对（引擎总数 + 各臂）──'
say "  引擎进程总数 = $(ps -eo args --no-headers 2>/dev/null | grep -c '[_]bk_exp.py')"
for P in 11386 27090 27094 27101 27103 28948 28950 29707 33073 33075; do
  T=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null | grep -oE '\-\-tag [A-Za-z0-9_]+' | awk '{print $2}')
  if [ -n "$T" ]; then
    S=$(tail -1 _exp/_bk_t5/dry_$T/series.csv 2>/dev/null | cut -d, -f1)
    say "     pid=$P  tag=$(printf '%-12s' "$T")  **仍在跑**  末步=$S"
  else
    say "     pid=$P  （已停）"
  fi
done
free -m | sed -n 2p | awk '{printf "  停后内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"
say '  ⚠ 数据一概未动（不删、不 mv）'
say '=== STOP_OLD2 DONE ==='
