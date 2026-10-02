#!/bin/bash
# _r581_mn64c.sh --- ★★★★★ **臂 D：`--var-rule random`**（直接检验 R76 的推论）
#
# ## R76 的推论（本轮要判的）
# | 臂 | `m` | 用到的**变体数** | 同变体 max |
# |---|---|---|---|
# | A | 4  | **2**（变体 1、5） | 4 |
# | B | 12 | **1**（变体 1）    | 5 |
# **⇒ 推论**：「`ed`（默认）= `np.argmax(drv)` ⇒ **每次形核都挑驱动力最大者**
#   ⇒ **倾向反复挑同一个变体** ⇒ **用到的变体数被压住**」
# **⇒ 而 C5 的总根数 = 「变体数」×「每变体根数」⇒ **两个因子都要动**。
#
# ## 本臂（**单变量**：只差 `--var-rule`）
# | 臂 | `--m` | `--var-rule` | 其余 |
# |---|---|---|---|
# | B（对照） | **12** | **`ed`**（默认，不传） | 逐字相同 |
# | **D（本臂）** | **12** | **`random`** | 逐字相同 |
#
# ## 判据（**预先写死**）
# * **臂 D 用到的变体数明显**多于**臂 B（≥3 vs 1）** ⇒ **R76 的推论成立**
#   ⇒ **C5 的配方 = `m` + S4 + `--var-rule`（三件）**；
# * **臂 D 仍是 1–2 个变体** ⇒ **R76 的推论不成立** ⇒ `ed` 不是限制变体数的原因，另查。
# ⚠ `--var-rule random` 会**消耗 `rng`**（与 `ed` 不同：`ed` 不调 `rng`）
#   ⇒ 本臂与臂 B **不是逐位关系**，只能比**统计量**（变体数 / 根数），不能比逐位。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_mn64"
STEPS="${R581MN64_STEPS:-250}"
LOG=_w2_r581_mn64c.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

# ⚠ 只数**真正的臂**（P27 + "别匹配到脚本自己"）
_n_mn64() {
  ps -eo args --no-headers 2>/dev/null \
    | grep '_bk_exp\.py' | grep -v grep | grep -c -- '--out _exp/_bk_mn64'
}

say "=== R581-R77：臂 D（--var-rule random）—— 直接检验 R76 的推论 ==="
say "阶段 1：等臂 B/C 跑完…"
_w=0
while [ "$(_n_mn64)" -gt 0 ]; do
  sleep 30; _w=$((_w + 1))
  [ "$_w" -ge 480 ] && { say "❌ 等了 4 h ⇒ 退出"; exit 4; }
done
[ -d "$ROOT/dry_C" ] || say "⚠ 臂 C（m=20）的目录不在 —— 可能没跑；臂 D 照跑"
say "阶段 1 完成"

avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
say "内存闸：MemAvailable = ${avail} MB"
[ "$avail" -lt 1500 ] && { say "❌ 内存不足"; exit 3; }

BASE="--N 64 --dx-nm 62.5 --steps $STEPS --every 5 --snap-every 100 \
  --pair-every 0 --norm-smooth 0 --nthreads 2 --grow-stack \
  --nuc-law athermal --nuc-init 6 --nuc-block-target 5 --nuc-shape ellipsoid \
  --nuc-supercrit 1 --nuc-sites-refill 1 --nuc-overlap-nm 62.5 \
  --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
  --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
  --cool-rate 2.3524e6 --eps0-mode einsum --ed-pair gather --k-loop act \
  --act-mode bincount --argmin2-mode copyto --grad-mode sliced --pf-phi onfly \
  --h-chunk 4 --extend-mode near --argmin2-reuse 1 --bbox-mode axis --nfsv-diag 1"

m=12
laths=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range($m)))")
d="$ROOT/dry_D"
[ -d "$d" ] && mv "$d" "${d}_superseded_$(date +%s)"
say "起臂 D：--m 12 --var-rule random（nv=144）cores 8-11"
taskset -c 8-11 $PY -u _bk_exp.py $BASE --out "$ROOT" --tag D --laths "$laths" \
    --var-rule random > _w2_r581_mn64_D.log 2>&1
say "臂 D 结束 exit=$? Traceback=$(grep -c '^Traceback' _w2_r581_mn64_D.log || true)"

say "── 四臂对照表（A/B/C/D）──"
$PY _r581_mn64read.py "$ROOT" A B C D 2>&1 | tee -a "$LOG"
say "=== R581 MN64C DONE ==="
