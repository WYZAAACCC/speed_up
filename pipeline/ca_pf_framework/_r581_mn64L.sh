#!/bin/bash
# _r581_mn64L.sh --- ★★★★★★ **臂 L：A39 的长跑判决实验**（R581-R153）
#
# ## 它回答什么（A39 的两个待定数）
# ① **`V` 的饱和值**（能否到 12？）；
# ② **`V` 大时的利用率**（能否从 23–27% 回到 E 的 60%？）
# ⇒ **这两个数决定 C5 的 `m`**（60% ⇒ `m`≈31、15.3 GB ✅；23% ⇒ `m`≈80、38.5 GB ❌）。
#
# ## 设计（**逐条都有依据**）
# | 决定 | 值 | 依据 |
# |---|---|---|
# | 参数 | **与臂 F 逐字相同** | **可比**（F 已给出 `V`=4@200 的曲线） |
# | `--steps` | **600** | **F 的 `V` 增速 3/100 步 ⇒ 要看到饱和需 ~2–3 倍** |
# | **`--snap-every`** | **★ 50** | **P37：`600 % 50 == 0` ⇒ **终态有快照****（F 踩过的坑：250 不是 100 的倍数 ⇒ 没有终态快照）** |
# | `B` | **74** | **与 F 同**（**⚠ 它会被 `B_max`=32 夹紧 ⇒ 实际 `B`=32**） |
# | `m` | **20**（`nv`=240） | **与 F 同** |
# | 核 | **8-11** | **与 F/G 同段**（**⚠ 会与 G 抢核；故本脚本先等 N=64 的臂跑完**） |
# | **内存闸** | **≥ 2500 MB 才起** | **P23：加车道的判据是**内存**不是空闲核** |
# | 墙钟上限 | **12 h** | **R147 实测 40 s/步@`V`=4 ⇒ 600 步 ≈ 6.7 h；留 1.8× 余量** |
#
# ## 判据（**预先写死**）
# | 观察 | 判决 |
# |---|---|
# | **终态 `V` ≥ 10** | **★ `V` 能到 12 量级 ⇒ C5 的路**通**（按利用率定 `m`）** |
# | **终态 `V` ≤ 6** | **★ `V` 饱和在 5–6 ⇒ C5 必须**改口径**（A37-A）** |
# | **利用率回到 ≥ 50%** | **⇒ `m`≈37 够（15–19 GB ✅）** |
# | **利用率仍 ≤ 30%** | **⇒ `m` 要 ~70+（>30 GB ❌）⇒ C5 在当前预算内不可达** |
# | **`nslab_n` 与 3-D 计数** | **★ 两个口径都报（§14）⇒ 再次检验"1-D 低报"** |
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_mn64"
STEPS="${R581MN64L_STEPS:-600}"
SNAP="${R581MN64L_SNAP:-50}"
CAP_H="${R581MN64L_CAP_H:-12}"
LOG=_w2_r581_mn64L.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

_n_mn64() {
  ps -eo args --no-headers 2>/dev/null \
    | grep '_bk_exp\.py' | grep -v grep | grep -c -- '--out _exp/_bk_mn64'
}

say "=== R581-R153：臂 L —— A39 长跑（目标 600 步 / snap 50）==="
say "阶段 1：等 N=64 上的其它臂跑完（F/G 各还需 ~5–30 min）…"
_w=0
while [ "$(_n_mn64)" -gt 0 ]; do
  sleep 30; _w=$((_w + 1))
  if [ "$_w" -ge $((CAP_H * 120)) ]; then say "❌ 等太久 ⇒ 退出"; exit 4; fi
done
say "阶段 1 完成（N=64 上无其它 _bk_exp 进程）"

avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
say "内存闸：MemAvailable = ${avail} MB"
[ "$avail" -lt 2500 ] && { say "❌ 内存不足（需 ≥2500 MB）⇒ 退出"; exit 3; }

BASE="--N 64 --dx-nm 62.5 --steps $STEPS --every 5 --snap-every $SNAP \
  --pair-every 0 --norm-smooth 0 --nthreads 2 --grow-stack \
  --nuc-law athermal --nuc-init 6 --nuc-block-target 74 --nuc-shape ellipsoid \
  --nuc-supercrit 1 --nuc-sites-refill 1 --nuc-overlap-nm 62.5 \
  --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
  --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
  --cool-rate 2.3524e6 --eps0-mode einsum --ed-pair gather --k-loop act \
  --act-mode bincount --argmin2-mode copyto --grad-mode sliced --pf-phi onfly \
  --h-chunk 4 --extend-mode near --argmin2-reuse 1 --bbox-mode axis --nfsv-diag 1"

m="${R581MN64L_M:-20}"
laths=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range($m)))")
say "m=$m ⇒ nv=$((m * 12))；steps=$STEPS；snap-every=$SNAP（600 %% 50 = $((STEPS % SNAP))）"

d="$ROOT/dry_L"
if [ -d "$d" ]; then
  ts=$(date '+%Y%m%d_%H%M%S')
  say "⚠ dry_L 已存在 ⇒ mv 到 dry_L_superseded_$ts（**绝不删除**）"
  mv "$d" "${d}_superseded_$ts" || exit 5
fi

say "起 L（cores 8-11）"
_t0=$(date +%s)
taskset -c 8-11 $PY -u _bk_exp.py $BASE --out "$ROOT" --tag L --laths "$laths" \
    > "_w2_r581_mn64_L.log" 2>&1
_rc=$?
_t1=$(date +%s)
say "L 结束 exit=$_rc；用时 $(( (_t1 - _t0) / 60 )) min；Traceback=$(grep -c '^Traceback' _w2_r581_mn64_L.log || true)"

say "── ★ 判决表（3-D 口径，§14）──"
$PY _r581_mn64read.py "$ROOT" L 2>&1 | tail -20 | tee -a "$LOG"
say "── ★ 两个口径对照（§14）──"
$PY _r581_xchk.py "$ROOT" L 2>&1 | tail -16 | tee -a "$LOG"
say "=== R581 MN64L DONE ==="
