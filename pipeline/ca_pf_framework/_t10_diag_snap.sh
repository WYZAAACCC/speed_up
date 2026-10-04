#!/bin/bash
# _t10_diag_snap.sh --- ★ 密快照诊断：定位「一场多块」发生在**第几步**
#
# ## 要回答的问题
# 10 µm 生产配置（t10E253）在 step 100 有 45 个场、其中 33 个被切成 ≥2 块。
# 已知：**两跑只差 η，⑦ 计数逐位相同（12/45）** ⇒ 掐断**发生在极早期**（η 起作用之前）。
# 但现有快照只有 step 0（形核前）与 step 100 ⇒ **看不到 1～20 步的窗口**。
#
# ## 做法（**缩减配置以省时间，盒子与网格不变**）
#   `--N 160 --dx-nm 62.5`（10 µm 盒、解析度不变）✓
#   `--B 1 --nvar 2 --m 22` ⇒ nv=44、本档目标 = 1×round(23×0.6327) = **15 个核**
#       （生产是 B=3 ⇒ 45 个核）⇒ burst 时间 ≈ 1/3
#   `--snap-every 1` ⇒ 拿到 step 1..20 **每一帧**
#   `--steps 20`
# ⚠ 记账：本诊断**不是**生产配置（B、nvar 缩小）⇒ 只用于定位"掐断发生在第几步"，
#   不得用它判 ⑦ 的绝对值。
#
# ## 判据
# 逐帧统计「分量数 ≥2 的场占比」。若**第 1 帧（step 1）就已经 ≥2** ⇒ 播种所致；
# 若第 1 帧为 1、随后某帧跳变 ⇒ 动力学掐断，且能读到**确切的步号**。
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10DGN
TS=$(date +%m%d_%H%M)
LOG=_w2_t10_diag.log
: > "$LOG"
{
  echo "════ 密快照诊断 $TS ════"
  free -m | sed -n '2,3p' | sed 's/^/  /'
} >> "$LOG"

# ① 停主算例（数据改名保留）
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in
    *bk_exp.py*|*_t10_swapalert_253.sh*|*_t10_auto_253.sh*)
      kill -9 "$P" 2>/dev/null; echo "  KILL pid=$P" >> "$LOG" ;;
  esac
done
sleep 6
D=_exp/_bk_t5/dry_t10E253
[ -d "$D" ] && mv "$D" "${D}_at100_$TS" && echo "  主算例数据 → $(basename ${D}_at100_$TS)" >> "$LOG"
[ -f _w2_t10_exit.txt ] && mv _w2_t10_exit.txt _w2_t10_exit_253_$TS.txt

# ② 语法门
for f in _t5_short.py _bk_exp.py windowB_surface.py; do
  $PY -m py_compile "$f" 2>>"$LOG" || { echo "❌ $f 语法错" >> "$LOG"; exit 1; }
done
echo "  ✅ 语法 OK" >> "$LOG"

# ③ 起诊断（η 沿用推导值 0.253 ⇒ 与生产一致的那一半参数）
setsid $PY _t5_short.py --tag $TAG --N 160 --dx-nm 62.5 --nvar 2 --m 22 --B 1 \
    --steps 20 --every 1 --snap-every 1 --pair-every 1000 --ckpt-every 0 \
    --overlap-nm 62.5 --eng-elong 7.00 \
    --ed-eta 0.253 --burst-km 1 --nuc-block-parallel 1 --diag-terms \
    --nthreads 16 --cores 0-19 --mem-limit-gb 20 \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG（nv=44、B=1、snap-every 1、steps 20）" >> "$LOG"

# ④ 盯守：每 60 s 记录 完成步数 + 快照数 + swap
{
  echo "  ── 盯守（每 60 s）──"
  for i in $(seq 1 120); do
    sleep 60
    P=""
    for X in $(ls /proc | grep -E '^[0-9]+$'); do
      C=$(tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null)
      case "$C" in *bk_exp.py*"--tag $TAG "*) P=$X; break ;; esac
    done
    NS=$(ls _exp/_bk_t5/dry_$TAG/snap_*.npz 2>/dev/null | wc -l)
    NE=$(grep -ac 'athermal 形核' _w2_t5_short_$TAG.log 2>/dev/null)
    if [ -z "$P" ]; then
      echo "    [$((i*60))s] ⚠ 结束（快照=$NS 核=$NE）" >> "$LOG"
      [ -f _w2_t10_exit.txt ] && cat _w2_t10_exit.txt | sed 's/^/      /' >> "$LOG"
      break
    fi
    R=$(awk '/VmRSS/{print $2}' /proc/$P/status 2>/dev/null)
    S=$(awk '/VmSwap/{print $2}' /proc/$P/status 2>/dev/null)
    echo "    [$((i*60))s] RSS=$(( ${R:-0}/1024 ))MB Swap=$(( ${S:-0}/1024 ))MB 快照=$NS 核=$NE" >> "$LOG"
  done
} >> "$LOG" 2>&1
echo "done $(date '+%H:%M:%S')" >> "$LOG"
