#!/bin/bash
# _t5_etaver.sh --- ★★★★★★ 修法 A 验证：**`--ed-eta 0.375`**（塑性弛豫折减）vs η=1.0（对照）
#
# ## 判据（**预先写死**）
# 单根算例（`--no-nucleation`，N=64，与 `t5B4D` 逐项相同，只多 `--ed-eta 0.375`）：
#   A 臂（对照，`t5B4D`，η=1.0）：孤立种子 **1022 → 128 胞（−87%）**（已实测，双量具一致）
#   B 臂（本臂，η=0.375）：预期 ——
#     · **净驱动力转正**（`df + η·ed ≈ 1.43e8 − 0.375×2.96e8 ≈ +3.2e7 > 0`）
#     · ⇒ **种子体积不再单调流失（或转为长大）**
#   ⇒ 判读：**体积流失显著减轻/转为增长** ⇒ **修法 A 有效** ✓
#            若**仍 −87% 左右** ⇒ 无效（需查接线或 η 标定）
# ## 理论核算
#   `df(801 K) = 1.426e8` ｜ `|ed| = 2.955e8` ｜ `η = 0.375`
#   ⇒ 净驱动力 `= 1.426e8 − 0.375 × 2.955e8 = 1.426e8 − 1.108e8 = **+3.18e7 > 0**` ✓
#   ⇒ 预期**界面转为前进**（种子保住、甚至长大）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t5ETA
LOG=_w2_t5_$TAG.log
{
  echo "════ 修法 A 验证：--ed-eta 0.375（塑性弛豫折减）vs η=1.0（t5B4D 对照）════"
  echo "  配置：N=64 · nvar 1 · m 23 · B 1 · --no-nucleation · --diag-terms（与 t5B4D 逐项相同）"
  echo "  理论：净驱动力 = 1.426e8 − 0.375×2.955e8 = **+3.18e7 > 0** ⇒ 预期界面转前进"
  echo "  判据：体积流失显著减轻或转为增长 ⇒ 修法 A 有效；仍 ~−87% ⇒ 无效"
  free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"
$PY -m py_compile _t5_short.py && echo "  ✅ _t5_short.py OK" >> "$LOG" || { echo "  ❌ 语法错" >> "$LOG"; exit 1; }
$PY -m py_compile _bk_exp.py && echo "  ✅ _bk_exp.py OK" >> "$LOG" || { echo "  ❌ 语法错" >> "$LOG"; exit 1; }
$PY -m py_compile windowB_surface.py && echo "  ✅ windowB_surface.py OK" >> "$LOG" || { echo "  ❌ 语法错" >> "$LOG"; exit 1; }

setsid $PY _t5_short.py --tag $TAG --N 64 --nvar 1 --m 23 --B 1 --steps 300 \
    --cores 0-5 --mem-limit-gb 6.0 --every 20 --snap-every 40 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    --no-nucleation --diag-terms --ed-eta 0.375 \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG" >> "$LOG"
sleep 280
{
  echo "  ── 280 s 后 ──"
  P=$(ps -eo pid,args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -- "--tag $TAG" | grep -v grep | awk '{print $1}' | head -1)
  if [ -n "$P" ]; then
    ps -o pid,etime,time,pcpu --no-headers -p "$P" | sed 's/^/     进程 /'
    echo "  ★ argv（关键：--ed-eta 0.375）:"
    tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null | grep -oE '\-\-ed-eta [0-9.]+|\-\-N [0-9]+' | sed 's/^/     /'
  else
    echo "  ⚠ 未找到进程 ⇒ 日志尾部："; tail -5 _w2_t5_short_$TAG.log | cut -c1-150 | sed 's/^/     /'
  fi
  printf '  末步 = %s ｜ 诊断块 = %s ｜ 快照 = %s\n' \
    "$(tail -1 _exp/_bk_t5/dry_$TAG/series.csv 2>/dev/null | cut -d, -f1)" \
    "$(grep -c '三项量级' _w2_t5_short_$TAG.log 2>/dev/null)" \
    "$(ls -1 _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | wc -l)"
  echo "  ── ★ B 臂（η=0.375）Vt 轨迹 ──"
  grep -E '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_$TAG.log 2>/dev/null | tail -6 | cut -c1-115 | sed 's/^/     /'
  echo "  ── ★ A 臂（η=1.0，t5B4D）Vt 轨迹（对照：单调降 −87%）──"
  grep -E '^ *\[ *[0-9]+\] Vt=' _w2_t5_short_t5B4D.log 2>/dev/null | tail -6 | cut -c1-115 | sed 's/^/     /'
  echo "  ── ★ B 臂 |Δed|（η 是否生效）──"
  grep -E 'F1 含母相' _w2_t5_short_$TAG.log 2>/dev/null | tail -2 | cut -c1-200 | sed 's/^/     /'
  free -m | sed -n 2p | awk '{printf "  内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"
