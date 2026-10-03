#!/bin/bash
# _t5_B3low.sh --- ★★★★★ 问题 B 判别实验 **B3：低密度**（盒加倍 ⇒ 密度 1/8）
#
# ## 为什么要做（**B2 的判据被修正后的结论**）
# B2（1 变体 · B=1 · N=80 ⇒ 5 µm 盒）实测（**按场数对齐**）：
#   场数 11 → 宽比 **7.07** ；场数 16 → 宽比 **5.64**  ⇒ **−20%**
# 而 t5N276（12 变体 · B=3）：
#   场数  9 → 宽比  6.59 ；场数 16 → 宽比 **5.34**  ⇒ **−19%**
# **⇒ 两者的下降率几乎相同（−20% vs −19%）**
# **⇒ 结论：「同变体密集堆叠/多块」**不是**原因**（我原先的判据"是否 ≥5"太粗，
#    漏掉了"自身随场数的下降率"——**判据缺陷，已记账**）。**
# **⇒ 退化与"**场数（密度）**"相关，而与变体数/块数无关。**
#
# ## 本实验（**分离"密度"与"场数"**）
# 同样的 `nvar 1 --m 23 --B 1`（nv=23 · 最多 23 根），但**盒子加倍**：
#   `--N 160` + `--dx-nm 62.5` ⇒ 盒 = **10.00 µm**（体积 = N=80 的 **8 倍**）
#   ⇒ **板条数相同、密度降到 1/8**
# **判据（预先写死）**：
#   * 若宽比的**下降率显著变小**（如 16 场时 ≥6.5）⇒ **确证是密度效应**;
#   * 若下降率**不变**（16 场时仍 ~5.6）⇒ **与密度无关** ⇒ 指向单根自身的时间演化。
#
# ## 内存
# N=160/nv=72 约 11 GB（先前实测）⇒ nv=23 约 **3.5 GB** ⇒ 可行（当前余 ~15 GB）。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t5B3L
LOG=_w2_t5_$TAG.log
say() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

{
  echo "════ 问题 B 判别 B3：**低密度**（N=160 ⇒ 10 µm 盒 · nvar 1 · m 23 · B 1 ⇒ nv=23）════"
  echo "  依据：B2（N=80）实测宽比 7.07(11场) → 5.64(16场) = −20%，"
  echo "        而 t5N276（12变体）9场 6.59 → 16场 5.34 = −19% ⇒ **下降率相同**"
  echo "  ⇒ 「同变体堆叠/多块」被否证 ⇒ 改测「**密度**」"
  echo "  判据：若本臂下降率显著变小 ⇒ **确证密度效应**；不变 ⇒ 与密度无关"
  free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"

setsid $PY _t5_short.py --tag $TAG --N 160 --nvar 1 --m 23 --B 1 --steps 6000 \
    --cores 0-3 --mem-limit-gb 6.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
say "  已起 tag=$TAG"

sleep 150
say '  ── 150 s 后：构造横幅（**关键：盒是否 10 µm、nv 是否 23、有无 ❌**）──'
grep -nE '盒|nv=|N8|自洽|总根数|❌|Traceback|约束|体积' _w2_t5_short_$TAG.log 2>/dev/null \
  | head -10 | cut -c1-165 >> "$LOG"
P=$(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- "--tag $TAG" | awk '{print $1}' | head -1)
if [ -n "$P" ]; then
  say '  ★ 命令行核对：'
  tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null \
    | grep -oE '\-\-N [0-9]+|\-\-nvar [0-9]+|\-\-m [0-9]+|\-\-B [0-9]+|\-\-eng-elong [0-9.]+' \
    | sed 's/^/     /' >> "$LOG"
else
  say '  ⚠ 未找到进程 ⇒ 查日志'
fi
free -m | sed -n 2p | awk '{printf "  起后内存：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"
