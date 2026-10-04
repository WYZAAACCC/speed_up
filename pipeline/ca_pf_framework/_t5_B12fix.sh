#!/bin/bash
# _t5_B12fix.sh --- ★★★★★★ 修正实验：`--N 100 --B 12`（盒加大到 6.25 µm ⇒ 276 根能放下）
#
# ## 为什么 N=80 + B=12 会空转（本轮实测）
# 横幅自警：「盒体积 125 µm³ / 单根 0.2550 µm³ ⇒ 30% 分数下可容 **147 根**（nv=276）⇒ ❌ 体积是瓶颈」
# 实测：`--B 12` ⇒ n_target=276 > 147 ⇒ **每个事件被拒**（"无可用空场/落位失败"）
#   ⇒ **引擎在 step 1 空转**（CPU 175%、9 分钟无进展）✓
# ## 定量修正
# 要装 276 根：`276 × 0.2550 / 0.30 = 234 µm³` ⇒ 边长 **6.16 µm** ⇒ dx=62.5 nm 下 **N ≈ 99**
#   ⇒ 取 **N = 100（6.25 µm，盒 244 µm³）** ⇒ 可容 **287 根** ⇒ B=12 的 276 根能放下 ✓
# ## 内存（按本仓定律外推）
# N=80/nv=276 ≈ 5.3 GB ⇒ N=100 ⇒ 5.3 × (100/80)³ = **10.4 GB** ⇒ 余 20 GB 可容 ✓
# ## 验收判据（与 s278 相同，**预先写死**）
#  ① `n_var_sig` → 12（A 臂 --B 3 实测 = 3）② `|Δed|` 中位下降 ③ 逐场体积不再流失
#  ④ 瓣数保持 1 ⑤ `blk_laths` 12 个块 ⑥ 长宽比 ≥5
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python

# ── ① 先杀掉空转的 t5B12（**按 PID，不用 pkill -f**；数据改名保留，不删）──
echo '── 停掉空转的 t5B12 ──'
for P in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- '--tag t5B12' | awk '{print $1}'); do
  kill -TERM "$P" 2>/dev/null && echo "  已 TERM pid=$P"
done
sleep 6
for P in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- '--tag t5B12' | awk '{print $1}'); do
  kill -KILL "$P" 2>/dev/null && echo "  已 KILL pid=$P"
done
D=_exp/_bk_t5/dry_t5B12
[ -d "$D" ] && mv "$D" "${D}_superseded_$(date +%m%d_%H%M)" && echo "  旧数据已改名保留（未删）"
# 同时停掉等待作业里的循环（它的目标是已废弃的臂）
for P in $(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]t5_waitB12' | awk '{print $1}'); do
  kill -TERM "$P" 2>/dev/null && echo "  已停等待脚本 pid=$P"
done

# ── ② 起正确的：N=100 · B=12 ──
TAG=t5B12N
LOG=_w2_t5_$TAG.log
{
  echo "════ 修正实验：--N 100 --B 12（盒 6.25 µm ⇒ 276 根能放下 ⇒ 12 块 ⇒ 12 变体）════"
  echo "  与 A 臂（t5N276F: N=80 --B 3）的差异：N 80→100 且 B 3→12"
  echo "  预期：n_var_sig 3→12 ⇒ 自协调成立 ⇒ 罚能抵消 ⇒ 板条站得住"
  free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"
$PY -m py_compile _t5_short.py || { echo "  ❌ 语法错" >> "$LOG"; exit 1; }
echo "  ✅ 语法 OK" >> "$LOG"

setsid $PY _t5_short.py --tag $TAG --N 100 --nvar 12 --m 23 --B 12 --steps 6000 \
    --cores 0-5 --mem-limit-gb 14.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 --diag-terms \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG" >> "$LOG"
sleep 260
{
  echo "  ── 260 s 后 ──"
  P=$(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- "--tag $TAG" | awk '{print $1}' | head -1)
  if [ -n "$P" ]; then
    echo "  ★ argv:"
    tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null \
      | grep -oE '\-\-N [0-9]+|\-\-B [0-9]+|\-\-nvar [0-9]+|\-\-m [0-9]+' | sed 's/^/     /'
    echo "  ★ 构造横幅（体积/根数/块数）："
    grep -nE '总根数|体积是瓶颈|可容|块数口径|❌' _w2_t5_short_$TAG.log 2>/dev/null | head -6 | cut -c1-175 | sed 's/^/     /'
    echo "  ★ 是否出现"被拒"（B=12/N=80 的死循环特征）："
    grep -c '被引擎拒' _w2_t5_short_$TAG.log 2>/dev/null | sed 's/^/     被拒次数 = /'
  else
    echo "  ⚠ 未找到进程 ⇒ 日志尾部："; tail -6 _w2_t5_short_$TAG.log | cut -c1-155 | sed 's/^/     /'
  fi
  free -m | sed -n 2p | awk '{printf "  内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"
