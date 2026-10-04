#!/bin/bash
# _t10_launch.sh --- ★ 10 µm 盒（N=160）· nv=220 主算例
#
# ## 用户指令（2026-10-04）
#   「将计算盒子设置为 10 微米，nv 设置为 220，N=160，其他初始条件与 5 微米时的盒子类似，
#     可以复用的就复用，不可以复用的就适配到 10 微米盒子中。如果有其他实验抢占内存就杀掉」
#
# ## 复用清单（**与 5 µm 盒逐字相同**）
#   `--plate-L 1000 --plate-W 500 --plate-T 510`（板条物理尺寸，与盒子无关）
#   `--eng-elong 7.00` · `--overlap-nm 62.5` · `--B 3`（块数）
#   冷却曲线（`--cool-rate 2.3524e6`、`--T-end 298.0`、`--qs-clock 1`）· `Ms`/`α_KM`/`C`/`ε⁰` 全未动
#   三个已批准的修复：`--ed-eta 0.375`（含**形核闸门**，s296）· `--burst-km 1` · `--nuc-block-parallel 1`
#
# ## 适配清单（**因为盒子变了**）
#   `--dx-nm 62.5` ⇒ L = 160 × 62.5 nm = **10.0 µm** ✓
#   `--nvar 10 --m 22` ⇒ **nv = 220**（用户指定）。`m=22`（原 23）是**唯一被迫的改动**：
#       220 = 10×22 是整数分解里 `m` 最接近 23 的一组（`nv=220` 不是 23 的倍数）。
#       ⚠ 记账：`m` 从 23 降到 22 ⇒ 单个变体最多容纳 22 根而非 `n(T_end)=23` 根。
#   `--steps 20000`（8× 体积 ⇒ 需要更多步走完同一降温曲线；停止由 `T_end` 的准静态钟决定）
#   `--snap-every 100`（N=160 的快照大得多，控制磁盘）
#
# ## 内存（实测定律 R598：RSS ≈ 3.64 GB + 69.8 MB × nv）
#   nv=220 ⇒ **≈ 19.0 GB**（预算 22 GB）⇒ 必须**独占**，故先杀掉三臂
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
TAG=t10N160
LOG=_w2_t10_launch.log
TS=$(date +%m%d_%H%M)
: > "$LOG"

{
  echo "════ 10 µm 盒（N=160）· nv=220 启动  $TS ════"
  free -m | sed -n 2p | awk '{printf "  起前内存：用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"

# ── ① 杀掉所有抢占内存的算例（用户已授权）+ 旧守望器 ──
for P in $(ls /proc | grep -E '^[0-9]+$'); do
  C=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)
  case "$C" in
    *bk_exp.py*|*_t5_wait*.sh*|*_t5_nvprobe*.sh*)
      echo "  KILL pid=$P  $(echo "$C" | grep -oE '\-\-tag [A-Za-z0-9_]+' | head -1)" >> "$LOG"
      kill -9 "$P" 2>/dev/null ;;
  esac
done
sleep 6
{
  echo "  ── 杀后内存 ──"
  free -m | sed -n 2p | awk '{printf "    用 %s MB / 余 %s MB\n", $3, $7}'
} >> "$LOG"

# ── ② 数据改名保留（**绝不删除**）──
for T in t5FIX t5BKMo t5ETAo; do
  D=_exp/_bk_t5/dry_$T
  [ -d "$D" ] && mv "$D" "${D}_superseded_10um_$TS" && echo "  $T → $(basename ${D}_superseded_10um_$TS)" >> "$LOG"
done

# ── ③ 语法/补丁硬门 ──
for f in _t5_short.py _bk_exp.py windowB_surface.py; do
  $PY -m py_compile "$f" 2>>"$LOG" && echo "  ✅ $f 语法 OK" >> "$LOG" \
    || { echo "  ❌ $f 语法错 ⇒ 中止" >> "$LOG"; exit 1; }
done
echo -n "  补丁在位性（各应 = 1）：s291记账 " >> "$LOG"
awk '/^ *if _ev or not _burst_on:$/{n++} END{printf "%d ", n+0}' _bk_exp.py >> "$LOG"
echo -n "s292代价闸 " >> "$LOG"
awk '/while _do_try and n_ath_tgt < _tgt/{n++} END{printf "%d ", n+0}' _bk_exp.py >> "$LOG"
echo -n "s293平行建块 " >> "$LOG"
awk '/_fresh_now = \(n_fresh_ok < int\(_Bt\)\)/{n++} END{printf "%d ", n+0}' _bk_exp.py >> "$LOG"
echo -n "s295分诊量具 " >> "$LOG"
awk '/s295 形核分诊/{n++} END{printf "%d ", n+0}' _bk_exp.py >> "$LOG"
echo -n "s296形核闸门η " >> "$LOG"
awk '/_eta_sc \* med > fcrit/{n++} END{printf "%d\n", n+0}' windowB_surface.py >> "$LOG"

# ── ④ 起主算例 ──
setsid $PY _t5_short.py --tag $TAG --N 160 --dx-nm 62.5 --nvar 10 --m 22 --B 3 \
    --steps 20000 --every 20 --snap-every 100 --pair-every 100 \
    --ckpt-every 200 --ckpt-keep 2 --overlap-nm 62.5 --eng-elong 7.00 \
    --ed-eta 0.375 --burst-km 1 --nuc-block-parallel 1 --diag-terms \
    --nthreads 4 --cores 0-15 --mem-limit-gb 21 \
    < /dev/null > _w2_t5_short_$TAG.log 2>&1 &
echo "  已起 tag=$TAG（N=160 · nv=10×22=220 · 10 µm 盒）" >> "$LOG"

# ── ⑤ 构造期内存盯守（每 30 s 记一次 RSS，共 ~14 min = 构造约 8–10 min + 前几步）──
{
  echo "  ── RSS 轨迹（构造期，判据：峰值应 ≲ 20 GB）──"
  for i in $(seq 1 28); do
    sleep 30
    P=$(ls /proc | grep -E '^[0-9]+$' | while read -r X; do
          tr '\0' ' ' < /proc/$X/cmdline 2>/dev/null | grep -q -- "--tag $TAG " && echo "$X"; done | head -1)
    if [ -z "$P" ]; then echo "    [$((i*30))s] ⚠ 进程已不在"; break; fi
    RSS=$(awk '/VmRSS/{print $2}' /proc/$P/status 2>/dev/null)
    echo "    [$((i*30))s] pid=$P RSS=$(( ${RSS:-0} / 1024 )) MB" >> "$LOG"
  done
} >> "$LOG" 2>&1
echo "done $(date '+%H:%M:%S')" >> "$LOG"
