#!/bin/bash
# _t5_B6.sh --- ★★★★★ 可行替代：`--N 80 --B 6`（块数 3→6 ⇒ 变体数 3→6，体量装得下）
#
# ## 为什么是 B=6
# ★ 盒体积上限（N=80 · 5 µm 盒）：可容 **147 根**（单根 0.2550 µm³ · 30% 分数）
#   ⇒ `B ≤ 147/23 = **6.4**` ⇒ **B = 6**（6×23 = **138 根** ≤ 147 ✓）
# ★ `--B 12` 实测**不可用**：N=80 ⇒ 拒绝循环 · N=100 ⇒ 卡住（0 事件/0 拒绝，CPU 206% 无进展）
#
# ## 能验证什么（**因果判据**）
# A 臂 `--B 3` ⇒ `n_var_sig = **3**`（实测）·
# B 臂 `--B 6` ⇒ 预期 `n_var_sig = **6**`
#   ⇒ **自协调从"3/12"提升到"6/12"** ⇒ **弹性能罚能可抵消一半**
#   ⇒ 判据：**`|Δed|` 中位下降** + **逐场体积流失显著减小** ⇒ **设计级根因确认** ✓
#   （不必到 12；**只要"变体数↑ ⇒ 溶解↓"这个单调关系成立**，根因就确认了）
#
# ## 预登记判据（**六条**）
#  ① `n_var_sig` = 6（A 臂 3）② `|Δed|` 中位下降（A 臂 **−2.955e8**，`<0` 占 100%）
#  ③ 逐场体积流失减小（A 臂孤立种子 **−87%**）④ 瓣数更接近 1（A 臂 1→**22**）
#  ⑤ `blk_laths` 出现 6 个块 ⑥ 长宽比 ≥5（A 臂 **3.37**）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python

# ── 停掉卡住的 t5B12N（按 PID；数据改名保留）──
echo '── 停掉卡住的 t5B12N ──'
for P in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- '--tag t5B12N' | awk '{print $1}'); do
  kill -TERM "$P" 2>/dev/null && echo "  已 TERM pid=$P"
done
sleep 6
for P in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- '--tag t5B12N' | awk '{print $1}'); do
  kill -KILL "$P" 2>/dev/null && echo "  已 KILL pid=$P"
done
D=_exp/_bk_t5/dry_t5B12N
[ -d "$D" ] && mv "$D" "${D}_superseded_$(date +%m%d_%H%M)" && echo "  旧数据已改名保留（未删）"

# ── 起 B=6 ──
TAG=t5B6
LOG=_w2_t5_$TAG.log
{
  echo "════ 可行替代实验：--N 80 --B 6（块数 3→6 ⇒ 变体数 3→6）════"
  echo "  与 A 臂（t5N276F: --B 3）唯一差异：--B 6"
  echo "  体量：6×23 = 138 根 ≤ 盒容量 147 根 ⇒ 装得下 ✓"
  echo "  判据：① n_var_sig=6 ② |Δed| 下降 ③ 体积流失减小 ④ 瓣数→1 ⑤ 6 块 ⑥ 宽比≥5"
  free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"
$PY -m py_compile _t5_short.py || { echo "  ❌ 语法错" >> "$LOG"; exit 1; }
echo "  ✅ 语法 OK" >> "$LOG"

setsid $PY _t5_short.py --tag $TAG --N 80 --nvar 12 --m 23 --B 6 --steps 6000 \
    --cores 0-5 --mem-limit-gb 8.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 --diag-terms \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG" >> "$LOG"
sleep 260
{
  echo "  ── 260 s 后 ──"
  P=$(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- "--tag $TAG" | awk '{print $1}' | head -1)
  if [ -n "$P" ]; then
    ps -o pid,etime,time,stat,%cpu --no-headers -p "$P" | sed 's/^/     进程 /'
    echo "  ★ argv:"
    tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null | grep -oE '\-\-N [0-9]+|\-\-B [0-9]+' | sed 's/^/     /'
    echo "  ★ 构造横幅："
    grep -nE '总根数|体积是瓶颈|可容|块数口径' _w2_t5_short_$TAG.log 2>/dev/null | head -5 | cut -c1-175 | sed 's/^/     /'
  else
    echo "  ⚠ 未找到进程 ⇒ 日志尾部："; tail -6 _w2_t5_short_$TAG.log | cut -c1-155 | sed 's/^/     /'
  fi
  printf '  末步 = %s ｜ 形核事件 = %s ｜ 被拒 = %s\n' \
    "$(tail -1 _exp/_bk_t5/dry_$TAG/series.csv 2>/dev/null | cut -d, -f1)" \
    "$(grep -cE '模式 \*\*' _w2_t5_short_$TAG.log 2>/dev/null)" \
    "$(grep -c '被引擎拒' _w2_t5_short_$TAG.log 2>/dev/null)"
  free -m | sed -n 2p | awk '{printf "  内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"
