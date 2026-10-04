#!/bin/bash
# _t10_launch28.sh --- WSL 28 GB 之后重跑：--nthreads 16 · --cores 0-19 · --mem-limit-gb 27
#
# ## 已确认的环境事实
# `.wslconfig` `memory=24GB → 28GB`（备份 `.wslconfig.bak_24GB_1004_2305`）；
# WSL 重启后 `MemTotal = 28064 MB`、`available = 27087 MB`、swap 0 ✓
#
# ## 上一跑的实测（**这是本脚本取值的依据**）
# `--nthreads 8 --mem-limit-gb 23`：**未被杀**，真实峰值 **VmHWM = 22.53 GB**，
#   但 burst 期间 available 只剩 400 MB、swap 用了 5.85 GB ⇒ 走得极慢（18 min 未出 step 1）。
# ⇒ 本次内存 +4 GB ⇒ 峰值应有 ~5.5 GB 余量 ⇒ 同时把线程数提到 16（提速）。
#
# ## 取值
# `--nthreads 16`（原来是 4，实测只用 2.74 核；16 线程已证**逐位一致**，见 `_t10_thrab.sh`）
# `--cores 0-19`（`processors=20`，只此一道作业）
# `--mem-limit-gb 27`（28 GB 留 1 GB + 8 GB swap 作安全阀；看门狗只为"别把机器打死"）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10N160
LOG=_w2_t10_launch28.log
: > "$LOG"
{
  echo "════ 28 GB 重跑：--nthreads 16 · --cores 0-19 · --mem-limit-gb 27  $(date '+%m-%d %H:%M:%S') ════"
  free -m | sed -n '2,3p' | sed 's/^/  /'
} >> "$LOG"

# 清掉可能残留的 exit 文件（**上一跑的陈旧文件曾让我误判过**）
[ -f _w2_t10_exit.txt ] && mv _w2_t10_exit.txt _w2_t10_exit_old_$(date +%m%d_%H%M).txt
echo "  exit 文件已清（存在即代表本跑已结束）" >> "$LOG"

# 语法门
for f in _t5_short.py _bk_exp.py windowB_surface.py; do
  $PY -m py_compile "$f" 2>>"$LOG" || { echo "  ❌ $f 语法错" >> "$LOG"; exit 1; }
done
echo "  ✅ 语法 OK" >> "$LOG"

CMD="$PY _t5_short.py --tag $TAG --N 160 --dx-nm 62.5 --nvar 10 --m 22 --B 3 \
    --steps 20000 --every 20 --snap-every 100 --pair-every 100 \
    --ckpt-every 200 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    --ed-eta 0.375 --burst-km 1 --nuc-block-parallel 1 --diag-terms \
    --nthreads 16 --cores 0-19 --mem-limit-gb 27"
setsid bash -c "$CMD ; echo \"EXIT=\$? at \$(date '+%F %T')\" > _w2_t10_exit.txt" \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起：--nthreads 16 --cores 0-19 --mem-limit-gb 27" >> "$LOG"

# RSS / VmHWM 盯守（90 min），同时记 swap —— burst 尖峰是重点
{
  echo "  ── RSS / VmHWM / Swap 轨迹（每 30 s）──"
  PEAK=0
  for i in $(seq 1 180); do
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
    S=$(awk '/VmSwap/{print $2}' /proc/$P/status 2>/dev/null)
    echo "    [$((i*30))s] RSS=$(( ${R:-0}/1024 )) VmHWM=$(( ${H:-0}/1024 )) Swap=$(( ${S:-0}/1024 )) MB" >> "$LOG"
  done
} >> "$LOG" 2>&1
echo "done $(date '+%H:%M:%S')" >> "$LOG"
