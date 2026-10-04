#!/bin/bash
# _t5_B12.sh --- ★★★★★★ 决定性实验：**`--B 12`**（块数 3→12 ⇒ 变体数 3→12 ⇒ 自协调成立）
#
# ## 设计级根因（本轮由"引擎拒绝"反推得到）
# 引擎硬校验（日志逐字）：「`--nuc-fresh-every` **必须 = n(T_end) = 23**」
#   （依据 `R525_TASK5_PARAM_FINDINGS.md §5`，**用户 2026-10-04 拍板"自动推导+硬校验"**）
# ⇒ **`K = n(T_end)` ⇒ 块数 = `ceil(B·n/K) = B`**
# ⇒ **我们用的 `--B 3` ⇒ 整个盒子只建 **3 个 block** ⇒ 只有 **3 个变体**
#    （与实测 `n_var_sig = **3**` **逐数吻合**）
# ⇒ **而自协调需要 **12** 个变体**（`ε⁰` 模块判据 **C4**：12 个 dev(ε⁰) 之和 = 0）
# ⇒ **自协调原理上不可能** ⇒ **弹性能罚能永远满值（~3e8）> `df(Ms)=1.128e8`**
# ⇒ **板条永远站不住 ⇒ 必然溶解 ⇒ 被啃成多块** ✓
#
# ## 而 `nv = nvar × m = 12 × 23 = 276` ⇒ **正对应 `B·n = 12 × 23 = 276`**
# ⇒ **盒子设计容量本是 `B = 12`** ⇒ 修法 = **`--B 12`**（零代码改动）
# ## 引擎自证：`T1_verify_edsign.py` D1c ⇒ **自协调构型 `E_el/vol` = 机器零**
#
# ## 验收判据（**预先写死**）
#  ① `n_var_sig` → **12**（现状 3）② `|Δed|` 中位显著下降 ③ 逐场体积不再流失
#  ④ 瓣数保持 1 ⑤ `blk_laths` 显示 12 个块 ⑥ 长宽比 ≥5
#  ★ **②③④可在**早期**读出**（不必跑完 276 条）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t5B12
LOG=_w2_t5_$TAG.log
{
  echo "════ 决定性实验：--B 12（块数 3→12 ⇒ 变体数 3→12 ⇒ 自协调）════"
  echo "  与 A 臂（t5N276F, --B 3）唯一差异：--B 12"
  echo "  nv = 12×23 = 276 ⇒ 与 B·n = 12×23 = 276 满配匹配"
  echo "  判据：① n_var_sig →12 ② |Δed| 下降 ③ 体积不流失 ④ 瓣数=1 ⑤ 12 块 ⑥ 宽比≥5"
  free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"
$PY -m py_compile _t5_short.py || { echo "  ❌ 语法错" >> "$LOG"; exit 1; }
echo "  ✅ 语法 OK" >> "$LOG"

setsid $PY _t5_short.py --tag $TAG --N 80 --nvar 12 --m 23 --B 12 --steps 6000 \
    --cores 0-5 --mem-limit-gb 8.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 --diag-terms \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG" >> "$LOG"
sleep 220
{
  echo "  ── 220 s 后 ──"
  P=$(ps -eo pid,args --no-headers 2>/dev/null | grep '[_]bk_exp.py' | grep -- "--tag $TAG" | awk '{print $1}' | head -1)
  if [ -n "$P" ]; then
    echo "  ★ argv 核对："
    tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null \
      | grep -oE '\-\-B [0-9]+|\-\-nvar [0-9]+|\-\-m [0-9]+|\-\-N [0-9]+|\-\-laths [0-9]+' | sed 's/^/     /'
    echo "  ★ 构造横幅（总根数 / N8 自洽 / 有无 ❌）："
    grep -nE '总根数|N8|自洽|nv=|❌|块数' _w2_t5_short_$TAG.log 2>/dev/null | head -8 | cut -c1-170 | sed 's/^/     /'
  else
    echo "  ⚠ 未找到进程 ⇒ 日志尾部："; tail -8 _w2_t5_short_$TAG.log | cut -c1-155 | sed 's/^/     /'
  fi
  free -m | sed -n 2p | awk '{printf "  内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"
