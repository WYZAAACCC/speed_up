#!/bin/bash
# _t5_dxtest.sh --- ★★★★★★ 单变量对照：**只改 `dx`**（判"薄板罚能高"是否因**欠解析**）
#
# ## 假设（本轮新提出）
# 薄板厚度 `t = 312.5 nm` 在 `dx = 62.5 nm` 下只有 **5 个胞**
# ⇒ **界面欠解析** ⇒ `ed` 可能被**人工抬高**（与本仓"界面欠解析"的既有教训同族）。
# ★ 而球体基准（`T1_verify_edsign.py`）用的是 `dx = 20/10 nm`（**收敛到 ~2.0e8**）
#   ⇒ **两者分辨率差 3–6 倍** ⇒ **不可直接比** ⚠
#
# ## 判据（**预先写死**）
# 同一盒子（5 µm）、同一 `ε⁰`/`C`、同一形状（薄板）、**只改 `dx`**：
#   * `dx = 62.5 nm`（5 胞厚）⇒ `|Δed|` = **2.955e8**（已实测，来自 `t5B4D`）
#   * `dx = 31.25 nm`（**10 胞厚**）⇒ 若 `|Δed|` **显著下降**（如 → 2.0e8 或更低）
#     ⇒ **罚能高是欠解析造成的** ⇒ 修法是**加密网格**（而不是改物理参数）✓
#   * 若 `|Δed|` **基本不变** ⇒ 与分辨率无关 ⇒ 罚能是**物理量** ⇒ 需查 `ε⁰`/`C`/Ms 标定
#
# ## 内存（按本仓定律外推）
# N=160/nv=276 ≈ 42 GB（先前实测）⇒ 本臂 **nv = 23**（`--nvar 1 --m 23`）
#   ⇒ ≈ 42 × (23/276) ≈ **3.5 GB** ✓（且有 nv 的常数项，留 8 GB 限额）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t5DX32
LOG=_w2_t5_$TAG.log
{
  echo "════ 单变量对照：只改 dx（62.5 → 31.25 nm）⇒ 判薄板罚能是否因欠解析偏高 ════"
  echo "  配置：--N 160 --dx-nm 31.25（盒 5.00 µm，与 t5B4D 同盒）· nvar 1 · m 23 · B 1 ⇒ nv=23"
  echo "        --no-nucleation（单根）· --diag-terms（读 |Δed|）"
  echo "  判据：|Δed| 显著下降 ⇒ **欠解析**（修法=加密网格）；不变 ⇒ 罚能是物理量"
  free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"
$PY -m py_compile _t5_short.py && echo "  ✅ 语法 OK" >> "$LOG" || { echo "  ❌ 语法错" >> "$LOG"; exit 1; }

setsid $PY _t5_short.py --tag $TAG --N 160 --dx-nm 31.25 --nvar 1 --m 23 --B 1 --steps 400 \
    --cores 0-5 --mem-limit-gb 9.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    --no-nucleation --diag-terms \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG" >> "$LOG"
sleep 260
{
  echo "  ── 260 s 后 ──"
  P=$(ps -eo pid,args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -- "--tag $TAG" | grep -v grep | awk '{print $1}' | head -1)
  if [ -n "$P" ]; then
    ps -o pid,etime,time,pcpu --no-headers -p "$P" | sed 's/^/     进程 /'
    echo "  ★ argv（关键：--dx-nm 31.25 与 --N 160）:"
    tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null | grep -oE '\-\-N [0-9]+|\-\-dx-nm [0-9.]+|\-\-nvar [0-9]+|\-\-m [0-9]+' | sed 's/^/     /'
    echo "  ★ 构造横幅（盒尺寸 / ❌ 与否）:"
    grep -nE '盒|dx|❌|体积' _w2_t5_short_$TAG.log 2>/dev/null | head -5 | cut -c1-165 | sed 's/^/     /'
  else
    echo "  ⚠ 未找到进程 ⇒ 日志尾部："; tail -6 _w2_t5_short_$TAG.log | cut -c1-155 | sed 's/^/     /'
  fi
  printf '  末步 = %s ｜ 诊断块 = %s\n' \
    "$(tail -1 _exp/_bk_t5/dry_$TAG/series.csv 2>/dev/null | cut -d, -f1)" \
    "$(grep -c '三项量级' _w2_t5_short_$TAG.log 2>/dev/null)"
  echo "  ── ★ |Δed| 与带符号读数 ──"
  grep -E 'F1 含母相|Δed 带符号' _w2_t5_short_$TAG.log 2>/dev/null | tail -4 | cut -c1-200 | sed 's/^/     /'
  echo "  ── 对照（dx=62.5 的 t5B4D）──"
  grep -E 'F1 含母相' _w2_t5_short_t5B4D.log 2>/dev/null | tail -2 | cut -c1-200 | sed 's/^/     /'
  free -m | sed -n 2p | awk '{printf "  内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"
