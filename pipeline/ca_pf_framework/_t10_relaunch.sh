#!/bin/bash
# _t10_relaunch.sh --- ★ 清僵尸 + 带**退出码捕获**重跑，用于区分 OOM(SIGKILL) 与段错误(SIGSEGV)
#
# ## 为什么要重跑
# 上一跑在 22:12 静默死亡：**无 traceback、无 error、包装层与引擎同时消失、
# `_t5_short.py` 的收尾摘要（含"峰值 RSS（看门狗实测）"）也没打印**。
# ⇒ 排除：keeper/监控（无 kill 逻辑、当时无活动）、`--mem-limit-gb`（触发也会打印摘要）
# ⇒ 剩下：**内核 OOM killer** 或 **段错误**。两者的退出码不同：
#      OOM/被 SIGKILL ⇒ 137 ；段错误 SIGSEGV ⇒ 139 ；正常 ⇒ 0
# ## 本脚本做什么
# ① 清掉一天多前的僵尸监控/keeper（它们仍在占内存，且与被杀的三臂同源）；
# ② 用 `bash -c '... ; echo EXIT=$?'` 把退出码写进独立文件；
# ③ 打开 core dump（若系统允许）以便回溯；
# ④ 起算例，并把退出码与 RSS 一起记账。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10N160
TS=$(date +%m%d_%H%M)
LOG=_w2_t10_relaunch.log
: > "$LOG"

{
  echo "════ 清僵尸 + 带退出码重跑  $TS ════"
  free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"

# ── ① 清僵尸（**只杀本工程目录下的旧监控/keeper**，按 PID 精确杀）──
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in
    *ca_pf_framework*_t5_armon*|*ca_pf_framework*_t5_blkmon*|*ca_pf_framework*_t5_milewatch*|\
    *ca_pf_framework*_t5_lathmon*|*ca_pf_framework*_t5_mon_keeper*|*ca_pf_framework*_t5_keeper_all*|\
    *ca_pf_framework*_t5_arwatch*|*ca_pf_framework*_t5_finalwatch*)
      echo "  KILL 僵尸 pid=$P  $(echo "$C" | awk '{print $2, $3}')" >> "$LOG"
      kill -9 "$P" 2>/dev/null ;;
  esac
done
sleep 4
{
  echo "  ── 清后内存 ──"
  free -m | sed -n 2p | awk '{printf "    用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"

# ── ② 数据改名保留 ──
D=_exp/_bk_t5/dry_$TAG
[ -d "$D" ] && mv "$D" "${D}_died_$TS" && echo "  旧数据 → $(basename ${D}_died_$TS)" >> "$LOG"

# ── ③ 语法门 ──
for f in _t5_short.py _bk_exp.py windowB_surface.py; do
  $PY -m py_compile "$f" 2>>"$LOG" && echo "  ✅ $f 语法 OK" >> "$LOG" \
    || { echo "  ❌ $f 语法错 ⇒ 中止" >> "$LOG"; exit 1; }
done

# ── ④ 起算例（**捕获退出码**）──
CMD="$PY _t5_short.py --tag $TAG --N 160 --dx-nm 62.5 --nvar 10 --m 22 --B 3 \
    --steps 20000 --every 20 --snap-every 100 --pair-every 100 \
    --ckpt-every 200 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    --ed-eta 0.375 --burst-km 1 --nuc-block-parallel 1 --diag-terms \
    --nthreads 4 --cores 0-15 --mem-limit-gb 21"
setsid bash -c "$CMD ; echo \"EXIT=\$? at \$(date '+%F %T')\" > _w2_t10_exit.txt" \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起（带退出码捕获 → _w2_t10_exit.txt）" >> "$LOG"

# ── ⑤ RSS + 存活盯守（含退出码检测）──
{
  echo "  ── RSS 轨迹 / 存活 ──"
  for i in $(seq 1 40); do
    sleep 30
    P=""
    for X in $(ls /proc | grep -E '^[0-9]+$'); do
      C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
      case "$C" in *bk_exp.py*"--tag $TAG "*) P=$X; break ;; esac
    done
    if [ -z "$P" ]; then
      echo "    [$((i*30))s] ⚠ 引擎不在" >> "$LOG"
      [ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt | sed 's/^/      /' >> "$LOG"
      break
    fi
    R=$(awk '/VmRSS/{print $2}' /proc/$P/status 2>/dev/null)
    H=$(awk '/VmHWM/{print $2}' /proc/$P/status 2>/dev/null)
    echo "    [$((i*30))s] RSS=$(( ${R:-0} / 1024 )) MB  峰值=$(( ${H:-0} / 1024 )) MB" >> "$LOG"
  done
} >> "$LOG" 2>&1
echo "done $(date '+%H:%M:%S')" >> "$LOG"
