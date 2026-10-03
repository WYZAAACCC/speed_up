#!/bin/bash
# _t5_relaunch_mob.sh --- ★★★★★ 修好 BUG 后重启两臂（**先 mv 归档崩溃目录，绝不删除**）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TS=$(date '+%Y%m%d_%H%M%S')
LOG=_w2_t5_ab_mob.log
say() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

say '════════ 修 BUG 后重启（归档崩溃目录）════════'
say "  BUG：windowB_surface.py:4678 `sorted(npref.values())` 对三维数组排序 ⇒ ValueError"
say "  修：按键排序取第一键（保持作者意图）；已核实实际代码行已改（非注释 grep 为空）"

# ① 归档崩溃的目录（**mv 改名，绝不删除** —— 用户硬要求）
for t in t5AM_ell t5AM_combo; do
  D=_exp/_bk_t5/dry_$t
  if [ -d "$D" ]; then
    mv "$D" "${D}_superseded_${TS}" && say "  已归档 $D ⇒ ${D}_superseded_${TS}"
  fi
  # 日志也归档改名（同样不删）
  for L in _w2_t5_am_$t.log _w2_t5_short_$t.log; do
    [ -f "$L" ] && mv "$L" "${L}.crash_${TS}" && say "  已归档 $L ⇒ ${L}.crash_${TS}"
  done
done

# ② 停掉旧的编排脚本（若还在等）
for P in $(ps -eo pid,args --no-headers | grep '[b]ash _t5_ab_mob.sh' | awk '{print $1}'); do
  kill -TERM "$P" 2>/dev/null && say "  已停旧编排 pid=$P"
done

# ③ 重启两臂（**参数逐字不变**，只是引擎 BUG 已修）
free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"
$PY _t5_short.py --tag t5AM_ell --N 80 --nvar 3 --m 24 --B 3 --steps 1400 \
    --cores 0-3 --mem-limit-gb 3.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 1 --overlap-nm 62.5 --mob-iform ellipse --mob-ratio 9.0 \
    > _w2_t5_am_t5AM_ell.log 2>&1 &
say "  起 t5AM_ell  pid=$!"
$PY _t5_short.py --tag t5AM_combo --N 80 --nvar 3 --m 24 --B 3 --steps 1400 \
    --cores 0-3 --mem-limit-gb 3.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 1 --overlap-nm 62.5 \
    --eng-elong 7.00 --mob-iform ellipse --mob-ratio 9.0 \
    > _w2_t5_am_t5AM_combo.log 2>&1 &
say "  起 t5AM_combo  pid=$!"

# ④ ★ 关键：等 4 分钟看它们是否**过了 step 0**（上次是 156-160 s 崩在 step 0）
sleep 260
say '  ── 4.3 分钟后：是否过了 step 0（上次崩在这里）──'
for t in t5AM_ell t5AM_combo; do
  S=$(tail -1 _exp/_bk_t5/dry_$t/series.csv 2>/dev/null | cut -d, -f1)
  A=$(ps -eo args --no-headers 2>/dev/null | grep -c "dry_$t" || true)
  say "     $t  末步=${S:-（无）}  进程数=$A"
done
say '  ⇒ 若末步 ≥ 40 且进程在 ⇒ **BUG 修好、公式跑起来了** ✓'
free -m | sed -n 2p | awk '{printf "  内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"
