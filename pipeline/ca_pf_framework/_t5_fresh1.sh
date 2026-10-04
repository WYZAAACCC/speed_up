#!/bin/bash
# _t5_fresh1.sh --- ★★★★★★ 决定性实验：`--nuc-fresh-every 1`（让 fresh 频繁尝试 ⇒ 多变体 ⇒ 自协调）
#
# ## 假说（本轮全部调查的收口）
# `fresh` 通道拥有全部物理机制（`supercrit` 判据 + `var-rule` 变体选择）;
# 而它**只在每 K 个事件尝试一次**（`K = --nuc-fresh-every`，`_t5_short.py` 默认不传 ⇒ `K = n(T_end) = 23`）
# ⇒ 实测 **fresh 2 / attach 16 / stack 10** ⇒ **变体数 n_var_sig 只有 3**（自协调需 12）
# ⇒ **弹性能罚能无法抵消**（满值 ~3e8）> `df(Ms) = 1.128e8`
# ⇒ **板条出生即溶解** ⇒ 被啃成多块（"一个场里有多根板条"）。
# **引擎自证**（`T1_verify_edsign.py` D1c）：**自协调构型 ⇒ `E_el/vol` 与 `ed` 都是机器零**
# ⇒ 只要变体数上去，罚能消失 ⇒ 板条站得住。
#
# ## 与 A 臂的唯一差异
# A 臂 = `t5N276F`（**已完成**，`--nuc-fresh-every` 未传 ⇒ K=23）
# B 臂 = **本臂**：**只多传 `--nuc-fresh-every 1`**，其余逐项相同。
#
# ## 验收判据（**预先写死，六条**）
#  ① `n_var_sig` 显著上升（A 臂末值 **3** ⇒ 目标 ≥6，理想 →12）
#  ② `|Δed|` 中位下降（`--diag-terms`）
#  ③ **逐场体积不再单调流失**
#  ④ **瓣数保持 1**（一场一根）
#  ⑤ **`blk_laths` 仍显示多块结构**（成块未被破坏）
#  ⑥ 长宽比 ≥5（最终目标）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t5NF1
LOG=_w2_t5_$TAG.log
{
  echo "════ 决定性实验 B 臂：`--nuc-fresh-every 1`（促发多变体 ⇒ 自协调）════"
  echo "  与 A 臂（t5N276F）唯一差异：多传 `--nuc-fresh-every 1`"
  echo "  预登记判据：① n_var_sig ≥6（A=3）② |Δed| 下降 ③ 体积不再流失"
  echo "              ④ 瓣数=1 ⑤ blk_laths 仍多块 ⑥ 长宽比 ≥5"
  free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"

$PY -m py_compile _t5_short.py || { echo "  ❌ 语法错" >> "$LOG"; exit 1; }
echo "  ✅ 语法 OK" >> "$LOG"

setsid $PY _t5_short.py --tag $TAG --N 80 --nvar 12 --m 23 --B 3 --steps 6000 \
    --cores 0-5 --mem-limit-gb 8.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    --nuc-fresh-every 1 \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG" >> "$LOG"
sleep 200
{
  echo "  ── 200 s 后 ──"
  P=$(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- "--tag $TAG" | awk '{print $1}' | head -1)
  if [ -n "$P" ]; then
    echo "  ★ argv 核对（关键：应有 --nuc-fresh-every 1）:"
    tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null \
      | grep -oE '\-\-nuc-fresh-every [0-9]+|\-\-nvar [0-9]+|\-\-m [0-9]+|\-\-B [0-9]+|\-\-N [0-9]+' | sed 's/^/     /'
    echo "  ★ 构造横幅："
    grep -nE '总根数|N8|自洽|nv=|❌' _w2_t5_short_$TAG.log 2>/dev/null | head -5 | cut -c1-165 | sed 's/^/     /'
  else
    echo "  ⚠ 未找到进程 ⇒ 日志尾部："; tail -6 _w2_t5_short_$TAG.log | cut -c1-150 | sed 's/^/     /'
  fi
  free -m | sed -n 2p | awk '{printf "  内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"
