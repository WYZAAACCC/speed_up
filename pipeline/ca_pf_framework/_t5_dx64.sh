#!/bin/bash
# _t5_dx64.sh --- ★★★★★★ 更快的 dx 对照：`--N 64 --dx-nm 31.25`（与 t5B4D 同胞数 ⇒ 同速）
#
# ## 为什么这样设计
# * 原对照 `t5DX32`（`--N 160 --dx-nm 31.25`）**网格细 8 倍** ⇒ ~60 s/步 ⇒ 到首个诊断要 ~20 分钟;
# * A 臂（对照）`t5B4D` = **`--N 64 --dx-nm 62.5`** ⇒ 盒 4 µm、**胞数 64³ = 2.6e5**、薄板 **5 胞厚**;
# * B 臂（本臂）= **`--N 64 --dx-nm 31.25`** ⇒ 盒 **2 µm**、**同胞数**、薄板 **10 胞厚**
#   ⇒ **速度相同**（数分钟出诊断）;
# * ⚠ **盒尺寸不同**（4 µm vs 2 µm）⇒ **不是严格单变量**;
#   但对"测**单根孤立板条**的 `ed`"而言，**周期性镜像的贡献在两臂都很小**
#   （板条 ~1 µm，远小于两个盒子）⇒ **该比较近似单变量**，且**方向性结论可靠**。
#
# ## 判据（**预先写死**）
#   * `dx` 减半后 `|Δed|` **显著下降** ⇒ **欠解析**（修法 = 加密网格）;
#   * **基本不变** ⇒ 罚能是**物理量** ⇒ 查 `ε⁰`/`C`/`Ms` 标定。
#   ★ 严格版仍由 `t5DX32`（`--N 160 --dx-nm 31.25`，盒保持 5 µm）继续跑作为复核。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t5DX64
LOG=_w2_t5_$TAG.log
{
  echo "════ 快速 dx 对照：--N 64 --dx-nm 31.25（薄板 10 胞厚；A 臂 t5B4D = 5 胞厚）════"
  echo "  ⚠ 盒 2 µm（A 臂 4 µm）⇒ 近似单变量；严格版见 t5DX32"
  echo "  判据：|Δed| 显著下降 ⇒ 欠解析（加密网格）；不变 ⇒ 物理量（查 ε⁰/C/Ms）"
  free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"
$PY -m py_compile _t5_short.py && echo "  ✅ 语法 OK" >> "$LOG" || { echo "  ❌ 语法错" >> "$LOG"; exit 1; }

setsid $PY _t5_short.py --tag $TAG --N 64 --dx-nm 31.25 --nvar 1 --m 23 --B 1 --steps 300 \
    --cores 0-5 --mem-limit-gb 6.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    --no-nucleation --diag-terms \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG" >> "$LOG"
sleep 270
{
  echo "  ── 270 s 后 ──"
  P=$(ps -eo pid,args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -- "--tag $TAG" | grep -v grep | awk '{print $1}' | head -1)
  if [ -n "$P" ]; then
    ps -o pid,etime,time,pcpu --no-headers -p "$P" | sed 's/^/     进程 /'
    echo "  ★ argv："
    tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null | grep -oE '\-\-N [0-9]+|\-\-dx-nm [0-9.]+' | sed 's/^/     /'
  else
    echo "  ⚠ 未找到进程 ⇒ 日志尾部："; tail -5 _w2_t5_short_$TAG.log | cut -c1-150 | sed 's/^/     /'
  fi
  printf '  末步 = %s ｜ 诊断块 = %s\n' \
    "$(tail -1 _exp/_bk_t5/dry_$TAG/series.csv 2>/dev/null | cut -d, -f1)" \
    "$(grep -c '三项量级' _w2_t5_short_$TAG.log 2>/dev/null)"
  echo "  ── ★ B 臂 |Δed|（dx=31.25，10 胞厚）──"
  grep -E 'F1 含母相|Δed 带符号' _w2_t5_short_$TAG.log 2>/dev/null | tail -4 | cut -c1-205 | sed 's/^/     /'
  echo "  ── ★ A 臂 |Δed|（dx=62.5，5 胞厚；t5B4D）──"
  grep -E 'F1 含母相|Δed 带符号' _w2_t5_short_t5B4D.log 2>/dev/null | tail -3 | cut -c1-205 | sed 's/^/     /'
  free -m | sed -n 2p | awk '{printf "  内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"
