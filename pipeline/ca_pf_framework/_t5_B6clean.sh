#!/bin/bash
# _t5_B6clean.sh --- ★★★★★★ 最干净的因果对照：无补丁版 · `--B 6` vs `t5N276F`（无补丁 · `--B 3`）
#
# ## 为什么用**无补丁版**
# `t5N276F`（A 臂，`--B 3`）是在我加 `supercrit` 补丁**之前**起的 ⇒ **无补丁**。
# ⇒ 用**无补丁版**跑 `--B 6` ⇒ **两臂只差 `B`**（3 → 6），
#   且都无补丁 ⇒ **排除补丁代价的干扰**，是**最干净的因果对照** ✓
#
# ## 判据（**预先写死，六条**）
#  ① `n_var_sig` = 6（A 臂 **3**）② `|Δed|` 中位下降（A 臂 **−2.955e8**，`<0` 占 100%）
#  ③ 逐场体积流失减轻（A 臂孤立种子 **−87%**）④ 瓣数趋近 1（A 臂 1→**22**）
#  ⑤ `blk_laths` 出现 6 个块 ⑥ 长宽比 ≥5（A 臂 **3.37**）
#  ★ 核心：**只要"变体数↑ ⇒ 溶解↓"成立，设计级根因即确认**
#
# ## 代码状态（**显式记账**）
# * 本脚本运行期间，`windowB_surface.py` = **无补丁版**（`.bak_stacksc`，405015 B）
# * 含补丁版已备份为 `.bak_bothpatches`（410079 B）
# * 跑完**不自动还原**（本轮需要它长期运行以便取判据）⇒ **下一轮注意此状态**
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
S=windowB_surface.py
TAG=t5B6np
LOG=_w2_t5_$TAG.log

{
  echo "════ 最干净的因果对照：无补丁版 · --N 80 --B 6（A 臂 = t5N276F · --B 3 · 同无补丁）════"
  echo "  ⚠ **代码状态**：本臂运行期间 windowB_surface.py = **无补丁版**（.bak_stacksc）"
  echo "     （含补丁版已备份为 .bak_bothpatches；跑完不自动还原 ⇒ 下一个会话注意）"
  echo "  判据：① n_var_sig=6 ② |Δed|↓ ③ 体积流失减轻 ④ 瓣数→1 ⑤ 6 块 ⑥ 宽比≥5"
  free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"

# ① 备份现状（两处补丁）→ 还原无补丁版
cp -f "$S" "$S.bak_bothpatches" 2>/dev/null
cp -f "$S.bak_stacksc" "$S" && echo "  已切到**无补丁版**" >> "$LOG"
$PY -c "
s=open('$S',encoding='utf-8').read()
print('  sc_stack_pass=%d sc_att_pass=%d 大小=%d' % (s.count('sc_stack_pass'), s.count('sc_att_pass'), len(s)))" >> "$LOG" 2>&1
$PY -m py_compile "$S" && echo "  ✅ 语法 OK" >> "$LOG" || { echo "  ❌ 语法错 ⇒ 中止" >> "$LOG"; exit 1; }

# ② 起臂
setsid $PY _t5_short.py --tag $TAG --N 80 --nvar 12 --m 23 --B 6 --steps 6000 \
    --cores 0-5 --mem-limit-gb 8.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 --diag-terms \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG" >> "$LOG"

sleep 300
{
  echo "  ── 300 s 后 ──"
  ps -eo pid,etime,time,%cpu --no-headers 2>/dev/null | grep -E "^ *$(ps -eo pid,args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -- "--tag $TAG" | awk '{print $1}' | head -1) " | sed 's/^/  进程 /'
  printf '  末步 = %s ｜ 事件 = %s ｜ 快照 = %s ｜ 被拒 = %s\n' \
    "$(tail -1 _exp/_bk_t5/dry_$TAG/series.csv 2>/dev/null | cut -d, -f1)" \
    "$(grep -cE '模式 \*\*' _w2_t5_short_$TAG.log 2>/dev/null)" \
    "$(ls -1 _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | wc -l)" \
    "$(grep -c '被引擎拒' _w2_t5_short_$TAG.log 2>/dev/null)"
  echo "  ── 构造横幅 ──"
  grep -nE '总根数|可容|块数口径' _w2_t5_short_$TAG.log 2>/dev/null | head -4 | cut -c1-170 | sed 's/^/     /'
  echo "  ── 日志尾部 ──"
  tail -3 _w2_t5_short_$TAG.log 2>/dev/null | cut -c1-160 | sed 's/^/     /'
  free -m | sed -n 2p | awk '{printf "  内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"
