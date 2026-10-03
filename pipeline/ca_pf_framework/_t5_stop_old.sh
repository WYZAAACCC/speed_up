#!/bin/bash
# _t5_stop_old.sh --- ★★★ 停掉"已产出确定结论、再跑无新信息"的臂（**只 kill 进程，数据一概不动**）
#
# ## 判据（**先写清，再动手**）
# | 臂 | 它已经产出的结论 | 还有新信息吗 | 处置 |
# |----|------------------|--------------|------|
# | **t5AB_C** | `facet-proj=1` **有害**（长厚比 1.15；§186+§219+§221 三条独立罪证）| **无** | **停** |
# | **t5AB_D** | `facet+elong7` 被拉平（长厚比 1.09）—— 同上，`facet` 已判死 | **无** | **停** |
# | **t5AB_B** | `eng-elong=3.75` 的剂量点：长宽比 **3.5 上下稳定**（step 40→1120 共 20+ 个步点）| **无**（剂量曲线已由 5/7/10 覆盖）| **停** |
# | **t5AD_500** | `eng-elong=5` 剂量点：**4.75/9.24 稳定**（多步点）| **无** | **停** |
# | **t5AB_A** | 对照：**1.84/3.74 稳定** | **有** —— 它是 `t5AM_ell` 的**同末步对照** | **留** |
# | **t5AD_700** | `eng-elong=7`：**6.55/13.0 稳定** | **有** —— 它是 `t5AM_combo` 的**同末步对照** | **留** |
# | **t5AD_1000** | `eng-elong=10`：7.32/14.47（**仅到 step 120**，稳定性尚未多步点确认）| **有** | **留** |
# | **t5AM_ell / t5AM_combo** | 本目标验证臂 | **有** | **留** |
# | **t5V2** | N=160 长臂；判据④（`nf2>0`）未达成 | **有** | **留** |
#
# ## 安全规则（**严格遵守**）
# * **绝不 `pkill -f`**（会杀到自己的 shell，AGENTS.md §3.10）⇒ **按精确 pid**；
# * **数据一概不动**（不删、不 mv —— 它们本来就该留在 F 盘）；
# * 先 `TERM`（让臂走正常退出路径、打退出摘要），10 s 后仍活着才 `KILL`。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
LOG=_w2_t5_stop_old.log
say() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

STOP="t5AB_C t5AB_D t5AB_B t5AD_500"
say '════ 停掉已定论的臂（判据见脚本头）════'
free -m | sed -n 2p | awk '{printf "  停前内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"

for t in $STOP; do
  PIDS=$(ps -eo pid,args --no-headers 2>/dev/null | grep "dry_$t" | grep '_bk_exp.py' | awk '{print $1}')
  if [ -z "$PIDS" ]; then say "  $t：没有引擎进程（可能已结束）"; continue; fi
  for P in $PIDS; do
    kill -TERM "$P" 2>/dev/null && say "  $t：已 TERM pid=$P"
  done
done
sleep 12
# 仍未死的才 KILL
for t in $STOP; do
  PIDS=$(ps -eo pid,args --no-headers 2>/dev/null | grep "dry_$t" | grep '_bk_exp.py' | awk '{print $1}')
  for P in $PIDS; do
    kill -9 "$P" 2>/dev/null && say "  $t：TERM 未生效 ⇒ 已 KILL pid=$P"
  done
done
sleep 3
say '  ── 停后核对 ──'
for t in $STOP t5AB_A t5AD_700 t5AD_1000 t5AM_ell t5AM_combo t5V2; do
  N=$(ps -eo args --no-headers 2>/dev/null | grep -c "dry_$t")
  S=$(tail -1 _exp/_bk_t5/dry_$t/series.csv 2>/dev/null | cut -d, -f1)
  say "     $(printf '%-12s' "$t") 进程=$N  末步=$S"
done
free -m | sed -n 2p | awk '{printf "  停后内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"
say '  ⚠ 数据一概未动（不删、不 mv）—— 所有快照/ckpt/series 仍在 F 盘原处'
say '=== STOP_OLD DONE ==='
