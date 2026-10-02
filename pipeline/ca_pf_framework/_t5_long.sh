#!/bin/bash
# _t5_long.sh --- ★★★★★★ 实验(5) **长跑**：两臂并行，各 6000 步（用户要求"最后长跑"）
#
# ## 配置（每一处的理由都写在这里，便于复核）
# * **盒**：N=160、dx=62.5 nm ⇒ **10.00 µm**（用户：≥10 µm）
# * **物理基线 = abA**（用户："参照 abA"）：`--alpha-km 0.041739 --T-end 298.0`
#   ⇒ 形核数 `n = floor(0.041739×(873−298)) = 23`
# * **算子**：13 项逐位优化（复用 `_r581_p2.SWITCHES`，单一真源）
# * **断点续跑**：`--ckpt-every 20 --ckpt-keep 2 --ckpt-milestone-every 500`
#   ⇒ 被杀最多丢 20 步；里程碑给"往回退一大截"留路
# * **两臂**（S4 简化的长跑级 A/B）：
#   A `--nuc-overlap-nm 62.5`（1Δx，代码自带剂量–响应的最优 = **修复值**）
#   B `--nuc-overlap-nm 0`   （旧默认 = **被审计的简化**）
# * **绑核**：A=0-7、B=8-15（不相交，P10）
# * **内存**：每臂看门狗 9.5 GB（实测单臂 7.8 GB）
# * **落盘**：`--snap-every 40`（供日后用新量具离线重测）+ series 每 20 步
# * **步数**：6000（abA 是 5922 步才成熟；实测 10.3 s/步 ⇒ 约 17 h）
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
LG=_w2_t5_long.log
STEPS=${T5_STEPS:-6000}
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LG"; }

say '════════════════════════════════════════════════════════════════════'
say '  实验(5) 长跑：两臂并行 / N=160（10 µm）/ abA 物理 / 13 项优化算子 / 断点续跑'
say '════════════════════════════════════════════════════════════════════'
free -m | sed -n 2p | sed 's/^/  /'
say "  每臂 $STEPS 步；预计约 $((STEPS*10/3600)) h"

$PY _t5_short.py --tag t5L62 --overlap-nm 62.5 --steps "$STEPS" --cores 0-7 \
   --mem-limit-gb 9.5 --every 20 --snap-every 40 --pair-every 50 \
   --ckpt-every 20 --ckpt-keep 2 --archive-old > _w2_t5_long_A.log 2>&1 &
PA=$!
say "  ★ A（overlap=62.5）pid=$PA  核 0-7"
sleep 25
$PY _t5_short.py --tag t5L0 --overlap-nm 0 --steps "$STEPS" --cores 8-15 \
   --mem-limit-gb 9.5 --every 20 --snap-every 40 --pair-every 50 \
   --ckpt-every 20 --ckpt-keep 2 --archive-old > _w2_t5_long_B.log 2>&1 &
PB=$!
say "  ★ B（overlap=0）  pid=$PB  核 8-15"
say '  （两臂独立进程 ⇒ 任一被杀/中断都能用 `--resume <ckpt 目录>` 续跑）'
wait $PA; RA=$?
wait $PB; RB=$?
say "  收官：A exit=$RA  B exit=$RB"
for t in t5L62 t5L0; do
  say "════ $t 末态 ════"
  $PY - "_exp/_bk_t5/dry_$t/series.csv" "$t" <<'PYEOF' 2>&1 | tee -a "$LG"
import csv, sys
try:
    rows = list(csv.DictReader(open(sys.argv[1], encoding='utf-8', errors='replace')))
except Exception as e:
    print('  读不到：%s' % e); raise SystemExit
print('  %s：%d 行，末步 %s' % (sys.argv[2], len(rows), rows[-1]['step']))
for c in ('Vt','f_var','nslab_n','nslab_n1','nf3','nf3_col','nf2','nblk_sig',
          'r_selfac','n_var_sig','n_habit','box_touch','box_touch_core',
          'n_lath','w_lath','a_lath','f1_area_m2','f2_area_m2','f3_area_m2'):
    if c in rows[-1]:
        print('     %-14s = %s' % (c, (rows[-1][c] or '')[:50]))
PYEOF
done
say '=== T5 LONG DONE ==='
