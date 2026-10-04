#!/bin/bash
# _t5_burstver.sh --- ★★★★★★ burst 修复验证：`--burst-km 1`（KM 分数律）vs 现状（线性律）
#
# ## 判据（**s282 已预登记，此处复述**）
#  ① **首档核数应占总量 ~63%**（现状 `floor(α·ΔT)=1` ⇒ `1/23 = 4.3%`）
#  ② **每档核数应指数衰减**（现状**恒定**每档 `B·1` 个）
#  ③ 复用引擎已有的 "burst regime" 记账串做正对照（`_bk_exp.py:1174`）
#  ④ 核数序列与 `N_end·Δf(T_k)` 在 **±15%** 内一致
#
# ## 预期（α = 0.041739 /K，ΔT_step = 23.958 K，N_end = 23 每块，B = 3）
#   第 1 档 `f=0.632` ⇒ 每块 ~15 根 ⇒ 全盒 ~44 根（现状 **3** 根）
#   第 2 档 `f=0.865` ⇒ 增量 23.2% ⇒ 每块 ~5 根 ⇒ 全盒 ~16 根
#   第 3 档 ⇒ ~8.5% ⇒ ~6 根 ｜ 第 4 档 ⇒ ~3.1% ⇒ ~2 根 …
#   ⇒ **首档爆发、随后指数衰减** ✓
#
# ## 配置（与 A 臂 `t5N276F` **只多一个 `--burst-km 1`**，且用**无补丁版** `windowB_surface.py`）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t5BK1
LOG=_w2_t5_$TAG.log
{
  echo "════ burst 修复验证：--burst-km 1（KM 分数律；A 臂 = t5N276F 的线性律）════"
  echo "  配置：N=80 · nvar 12 · m 23 · B 3 · 与 t5N276F 只多 --burst-km 1"
  echo "  代码：windowB_surface.py = 无补丁版（与 t5N276F 一致）"
  echo "  判据：① 首档核数 ~63% ② 每档指数衰减 ③ burst regime 记账 ④ 与 N_end·Δf 在 ±15%"
  free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"
$PY -m py_compile _t5_short.py && echo "  ✅ _t5_short.py 语法 OK" >> "$LOG" || { echo "  ❌ 语法错" >> "$LOG"; exit 1; }
$PY -m py_compile _bk_exp.py && echo "  ✅ _bk_exp.py 语法 OK" >> "$LOG" || { echo "  ❌ 语法错" >> "$LOG"; exit 1; }

setsid $PY _t5_short.py --tag $TAG --N 80 --nvar 12 --m 23 --B 3 --steps 3000 \
    --cores 0-5 --mem-limit-gb 8.0 --every 10 --snap-every 80 --pair-every 100 \
    --ckpt-every 100 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    --burst-km 1 \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG" >> "$LOG"
sleep 240
{
  echo "  ── 240 s 后 ──"
  P=$(ps -eo pid,args --no-headers 2>/dev/null | grep 'bk_exp.py' | grep -- "--tag $TAG" | grep -v grep | awk '{print $1}' | head -1)
  if [ -n "$P" ]; then
    ps -o pid,etime,time,pcpu --no-headers -p "$P" | sed 's/^/     进程 /'
    echo "  ★ argv 核对（应有 --burst-km 1）:"
    tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null | grep -oE '\-\-burst-km [0-9]+|\-\-B [0-9]+|\-\-N [0-9]+' | sed 's/^/     /'
  else
    echo "  ⚠ 未找到进程 ⇒ 日志尾部："; tail -6 _w2_t5_short_$TAG.log | cut -c1-160 | sed 's/^/     /'
  fi
  printf '  末步 = %s ｜ 形核事件 = %s ｜ 被拒 = %s\n' \
    "$(tail -1 _exp/_bk_t5/dry_$TAG/series.csv 2>/dev/null | cut -d, -f1)" \
    "$(grep -cE '模式 \*\*' _w2_t5_short_$TAG.log 2>/dev/null)" \
    "$(grep -c '被引擎拒' _w2_t5_short_$TAG.log 2>/dev/null)"
  echo "  ── ★ 判据①②：每档核数分布（按温度档统计事件数）──"
  grep -oE 'T=[0-9.]+ K' _w2_t5_short_$TAG.log 2>/dev/null | sort | uniq -c | head -14 | sed 's/^/     /'
  echo "  ── 对照：A 臂（t5N276F，线性律）的每档核数 ──"
  grep -oE 'T=[0-9.]+ K' _w2_t5_short_t5N276F.log 2>/dev/null | sort | uniq -c | head -10 | sed 's/^/     /'
  free -m | sed -n 2p | awk '{printf "  内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"
