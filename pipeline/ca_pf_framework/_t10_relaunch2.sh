#!/bin/bash
# _t10_relaunch2.sh --- 修「看门狗杀自己」：--nthreads 8 + --mem-limit-gb 23
#
# ## 根因（实测，不是猜）
# `_w2_t5_short_t10N160.log` 的收尾摘要写着：
#     ⚠⚠⚠ 内存看门狗触发：VmHWM=20.65 GB > 20.00 GB ⇒ 杀
#     峰值 RSS（VmHWM，看门狗实测）= **20.65 GB**  ⚠ 被看门狗杀
# ⇒ 是**我自己设的 `--mem-limit-gb 20`** 杀的（`_t5_short.py:155-168`），
#   包装层随后**正常返回 0** ⇒ 所以退出码是 0、也没有 traceback。**两次死亡同一原因。**
#
# ## 账目（为什么 20 GB 不够）
# · R598 定律 `3.64 GB + 69.8 MB×nv` = **19.0 GB** 只覆盖**构造**（那是只跑构造的探针测的）；
# · **step 1 的 burst 在构造之上再加 ~5 GB**：每个候选核的 `supercrit` 探针要
#   `seed_plate` + `elastic_driving()` + 回滚，而 `elastic_driving()` 临时分配
#   多张 `(nv, N³)` 数组 + FFT 工作区；
# · 实测：构造期采样峰值 ~15 GB，而 step 1 的 `VmHWM` 到 **20.65 GB**；
# · 16 线程比 4 线程**更费内存**（每线程自己的切片缓冲）。
#
# ## 本次取值
# · `--nthreads 8`：仍比原来的 4 线程快（实测 4 线程只用 2.74 核），但比 16 线程省内存；
# · `--mem-limit-gb 23`：WSL 总 24 GB + 8 GB swap ⇒ 留 1 GB + swap 作安全阀；
#   看门狗的本意是"别把机器打死"，而不是"卡在引擎真实的峰值下面"。
# · **停掉所有额外监控**（只留一个轻量 RSS 记录），把内存让给引擎。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10N160
TS=$(date +%m%d_%H%M)
LOG=_w2_t10_relaunch2.log
: > "$LOG"
{
  echo "════ 修看门狗：--nthreads 8 · --mem-limit-gb 23  $TS ════"
  free -m | sed -n 2p | awk '{printf "  起前：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"

# ① 停掉一切非必要进程（监控/盯守/守望），把内存让出来
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in
    *bk_exp.py*|*_t10_mon.sh*|*_t10_wait.sh*|*ca_pf_framework*_t5_armon*|\
    *ca_pf_framework*_t5_blkmon*|*ca_pf_framework*_t5_milewatch*|*ca_pf_framework*_t5_lathmon*|\
    *ca_pf_framework*_t5_mon_keeper*|*ca_pf_framework*_t5_keeper_all*)
      kill -9 "$P" 2>/dev/null; echo "  KILL pid=$P" >> "$LOG" ;;
  esac
done
sleep 5
free -m | sed -n 2p | awk '{printf "  停后：用 %s MB / 余 %s MB\n", $3, $7}' >> "$LOG"

# ② 数据改名保留
D=_exp/_bk_t5/dry_$TAG
[ -d "$D" ] && mv "$D" "${D}_wd20_$TS" && echo "  旧数据 → $(basename ${D}_wd20_$TS)" >> "$LOG"

# ③ 语法门
for f in _t5_short.py _bk_exp.py windowB_surface.py; do
  $PY -m py_compile "$f" 2>>"$LOG" || { echo "  ❌ $f 语法错" >> "$LOG"; exit 1; }
done
echo "  ✅ 语法 OK" >> "$LOG"

# ④ 起算例
CMD="$PY _t5_short.py --tag $TAG --N 160 --dx-nm 62.5 --nvar 10 --m 22 --B 3 \
    --steps 20000 --every 20 --snap-every 100 --pair-every 100 \
    --ckpt-every 200 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    --ed-eta 0.375 --burst-km 1 --nuc-block-parallel 1 --diag-terms \
    --nthreads 8 --cores 0-15 --mem-limit-gb 23"
setsid bash -c "$CMD ; echo \"EXIT=\$? at \$(date '+%F %T')\" > _w2_t10_exit.txt" \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起：--nthreads 8 --mem-limit-gb 23" >> "$LOG"

# ⑤ 轻量 RSS/VmHWM 盯守（**同时记 VmHWM，这样即使被杀也知道真实峰值**）
{
  echo "  ── RSS / VmHWM 轨迹 ──"
  for i in $(seq 1 60); do
    sleep 30
    P=""
    for X in $(ls /proc | grep -E '^[0-9]+$'); do
      C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
      case "$C" in *bk_exp.py*"--tag $TAG "*) P=$X; break ;; esac
    done
    if [ -z "$P" ]; then
      echo "    [$((i*30))s] ⚠ 引擎不在" >> "$LOG"
      [ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt | sed 's/^/      /' >> "$LOG"
      grep -a '看门狗\|峰值 RSS' _w2_t5_short_$TAG.log | tail -3 | sed 's/^/      /' >> "$LOG"
      break
    fi
    R=$(awk '/VmRSS/{print $2}' /proc/$P/status 2>/dev/null)
    H=$(awk '/VmHWM/{print $2}' /proc/$P/status 2>/dev/null)
    echo "    [$((i*30))s] RSS=$(( ${R:-0} / 1024 )) MB  VmHWM=$(( ${H:-0} / 1024 )) MB" >> "$LOG"
  done
} >> "$LOG" 2>&1
echo "done $(date '+%H:%M:%S')" >> "$LOG"
