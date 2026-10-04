#!/bin/bash
# _t10_restart_thr.sh --- 提线程数重启主算例（用户 2026-10-04 指示：允许多核并行，取合适核数，需重启就重启）
#
# ## 核数选择
# 宿主 **20 逻辑核**；当前只有这一道作业。取 **`--nthreads 16` + `--cores 0-17`**：
# 留 **2 个逻辑核（18,19）** 给内核/IO/盯守脚本，避免把机器占满（AGENTS.md §1.3 用户约束）。
# 依据（实测）：上一跑 `--nthreads 4` 时 `%CPU=274` ⇒ **2.74 核**，而亲和性允许 16 核 ⇒ 5.8× 闲置。
#
# ## 记账
# · `--nthreads` 只影响**空间切片分工**（`workers=` 传给 `LevelSetMulti`），不是物理参数；
# · 同配置的 `--nthreads 2 vs 8` 逐位 A/B 结果一并记入本日志（若已完成）；
# · 数据一律**改名保留**，不删。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10N160
TS=$(date +%m%d_%H%M)
LOG=_w2_t10_restart_thr.log
: > "$LOG"

{
  echo "════ 提线程数重启（--nthreads 4 → 16；--cores 0-17） $TS ════"
  free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"

# ── ① A/B 结果（若已完成）──
{
  echo "── `--nthreads` 逐位 A/B 结果 ──"
  if [ -f _w2_t10_thrab.log ]; then tail -14 _w2_t10_thrab.log; else echo "  （A/B 未产出日志）"; fi
} >> "$LOG"

# ── ② 停 A/B（若还在跑）与主算例 ──
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in
    *bk_exp.py*"--tag thrab"*|*_t10_thrab.sh*)
      echo "  KILL A/B pid=$P" >> "$LOG"; kill -9 "$P" 2>/dev/null ;;
    *bk_exp.py*"--tag $TAG "*)
      echo "  KILL 主算例 pid=$P" >> "$LOG"; kill -9 "$P" 2>/dev/null ;;
    *"_t5_short.py --tag $TAG "*)
      echo "  KILL 包装层 pid=$P" >> "$LOG"; kill -9 "$P" 2>/dev/null ;;
  esac
done
sleep 8
{
  echo "  ── 停后内存 ──"; free -m | sed -n 2p | awk '{printf "    用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"

# ── ③ 数据改名保留 ──
D=_exp/_bk_t5/dry_$TAG
[ -d "$D" ] && mv "$D" "${D}_thr4_$TS" && echo "  旧数据（nthreads=4）→ $(basename ${D}_thr4_$TS)" >> "$LOG"

# ── ④ 语法门 ──
for f in _t5_short.py _bk_exp.py windowB_surface.py; do
  $PY -m py_compile "$f" 2>>"$LOG" && echo "  ✅ $f 语法 OK" >> "$LOG" \
    || { echo "  ❌ $f 语法错 ⇒ 中止" >> "$LOG"; exit 1; }
done

# ── ⑤ 起算例：**--nthreads 16 / --cores 0-17**（其余 argv 与上一跑逐字相同）──
CMD="$PY _t5_short.py --tag $TAG --N 160 --dx-nm 62.5 --nvar 10 --m 22 --B 3 \
    --steps 20000 --every 20 --snap-every 100 --pair-every 100 \
    --ckpt-every 200 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    --ed-eta 0.375 --burst-km 1 --nuc-block-parallel 1 --diag-terms \
    --nthreads 16 --cores 0-17 --mem-limit-gb 20"
setsid bash -c "$CMD ; echo \"EXIT=\$? at \$(date '+%F %T')\" > _w2_t10_exit.txt" \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起：**--nthreads 16 --cores 0-17**" >> "$LOG"

# ── ⑥ 复验 argv + 亲和性 + 实测核数 ──
sleep 90
{
  echo "  ── 复验（90 s 后）──"
  P=""
  for X in $(ls /proc | grep -E '^[0-9]+$'); do
    C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
    case "$C" in *bk_exp.py*"--tag $TAG "*) P=$X; break ;; esac
  done
  if [ -n "$P" ]; then
    echo "    pid=$P"
    tr '\0' ' ' < /proc/$P/cmdline | grep -oE '\-\-nthreads [0-9]+' | sed 's/^/    argv /'
    echo "    亲和性: $(taskset -pc $P 2>/dev/null | sed 's/.*list: //')"
    ps -o etime,time,pcpu,rss --no-headers -p "$P" | sed 's/^/    /'
  else
    echo "    ⚠ 未找到"
  fi
  echo "    OMP/OPENBLAS 线程环境（包装层设置）:"
  tr '\0' '\n' < /proc/$P/environ 2>/dev/null | grep -E 'OMP_NUM_THREADS|OPENBLAS_NUM_THREADS|MKL_NUM_THREADS' | sed 's/^/      /'
} >> "$LOG" 2>&1
echo "done $(date '+%H:%M:%S')" >> "$LOG"
