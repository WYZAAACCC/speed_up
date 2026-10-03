#!/bin/bash
# _t5_relaunch_mob2.sh --- ★★★★★ 用 `setsid` 重启两臂（**上次的教训：脚本退出 ⇒ SIGHUP 杀子进程**）
#
# ## 上次的错（**记账**）
# `_t5_relaunch_mob.sh` 用 `&` 起了两臂，**然后脚本自己退出** ⇒ 子进程收 **SIGHUP** ⇒
# **两臂静默死掉**（日志既无 traceback 也无退出摘要 ⇒ 一开始我误以为是修复引入的崩溃）。
# **⇒ 正确做法：`setsid <cmd> < /dev/null >> log 2>&1 &`，并**在脚本里 wait**（或让脚本常驻）。**
#
# ## 本脚本做两件事
# 1. **重启两臂**（参数逐字不变，引擎 BUG 已修）；
# 2. **脚本自己 `wait`** ⇒ 与 `_t5_ab_mob.sh` 同构 ⇒ **子进程不会因脚本退出而死**。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TS=$(date '+%Y%m%d_%H%M%S')
LOG=_w2_t5_ab_mob.log
say() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

say '════════ setsid 重启两臂（修上次 SIGHUP 的错）════════'
for t in t5AM_ell t5AM_combo; do
  D=_exp/_bk_t5/dry_$t
  [ -d "$D" ] && mv "$D" "${D}_superseded_${TS}" && say "  已归档 $D"
  for L in _w2_t5_am_$t.log _w2_t5_short_$t.log; do
    [ -f "$L" ] && mv "$L" "${L}.sighup_${TS}" && say "  已归档 $L"
  done
done

free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"

# ★ 关键：setsid 让子进程**脱离本 shell 的会话** ⇒ 本脚本退出也不影响它们
setsid $PY _t5_short.py --tag t5AM_ell --N 80 --nvar 3 --m 24 --B 3 --steps 1400 \
    --cores 0-3 --mem-limit-gb 3.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 1 --overlap-nm 62.5 --mob-iform ellipse --mob-ratio 9.0 \
    < /dev/null > _w2_t5_am_t5AM_ell.log 2>&1 &
P1=$!
setsid $PY _t5_short.py --tag t5AM_combo --N 80 --nvar 3 --m 24 --B 3 --steps 1400 \
    --cores 0-3 --mem-limit-gb 3.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 1 --overlap-nm 62.5 \
    --eng-elong 7.00 --mob-iform ellipse --mob-ratio 9.0 \
    < /dev/null > _w2_t5_am_t5AM_combo.log 2>&1 &
P2=$!
say "  起 t5AM_ell(p=$P1) · t5AM_combo(p=$P2) —— setsid 已脱离本 shell"

# ★ 本脚本**保持存活**（等两臂），这样即使 setsid 失效也有兜底
sleep 300
say '  ── 5 分钟后核对（上次死在这里）──'
for t in t5AM_ell t5AM_combo; do
  say "     $t 末步=$(tail -1 _exp/_bk_t5/dry_$t/series.csv 2>/dev/null | cut -d, -f1)  进程数=$(ps -eo args --no-headers 2>/dev/null | grep -c "dry_$t")  日志最后写=$(stat -c%y _w2_t5_short_$t.log 2>/dev/null | cut -d. -f1)"
done
say '  ⇒ 末步 ≥20 且进程在 ⇒ 存活 ✓'
wait               # ★ 关键：保持存活
say '════ 两臂结束 ════'
