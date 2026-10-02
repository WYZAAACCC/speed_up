#!/bin/bash
# _r581_mn64d.sh --- ★★★★★ **臂 E：C5 的**完整配方**（`m=20` + S4 + `--var-rule random`）**
#
# ## 为什么这是最关键的一臂
# R74 证实 **`m` 抬高"每变体根数上限"**（`m=4`⇒4，`m=12`⇒5）；
# R76 指出**总根数 = 「用到的变体数」×「每变体根数」**，而 `m` 只抬高第二个因子
# ⇒ **`ed`（`argmax(drv)`）可能把"变体数"压在 1–2 个**（臂 B 实测：`{1: 5}`）。
# **⇒ C5 要 220–450 根 ⇒ **两个因子都要拉满** ⇒ 这一臂把三个旋钮一起拧到底：**
#   * `--m 20`（R53 的甜点：11.9 GB / 11.1 h @N=160；N=64 上只要几百 MB）
#   * `--nuc-overlap-nm 62.5`（S4：打开 `stack` 通道，R64/R69）
#   * `--var-rule random`（铺开变体，R76 的推论）
#
# ## 四臂矩阵（**（N=64，全部 S4 开**）
# | 臂 | `--m` | `--var-rule` | 测的是 |
# |---|---|---|---|
# | A | 4  | `ed`     | 基准（已完：max 4，2 个变体） |
# | B | 12 | `ed`     | **`m` 单独**（step 100：max 5，**1 个变体**） |
# | C | 20 | `ed`     | **`m` 再抬高** |
# | D | 12 | `random` | **`--var-rule` 单独**（判 R76 的推论） |
# | **E** | **20** | **`random`** | **★ 完整配方 ⇒ C5 能到多少根** |
#
# ## 判据（**预先写死**）
# * **臂 E 的「用到的变体数」× 「每变体根数」应当是四臂里**最大**的**；
# * **若臂 E 的总根数 ≪ 220** ⇒ **当前模型（即使三旋钮全开）到不了 C5** ⇒ 要另找机制；
# * **若臂 E 的总根数进入几十根的量级** ⇒ **C5 的路是"三旋钮 + 更大的 `m`"**，
#   按 R53 的账外推到 N=160。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_mn64"
STEPS="${R581MN64_STEPS:-250}"
LOG=_w2_r581_mn64d.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }
_n_mn64() {
  ps -eo args --no-headers 2>/dev/null \
    | grep '_bk_exp\.py' | grep -v grep | grep -c -- '--out _exp/_bk_mn64'
}

say "=== R581-R78：臂 E（完整配方 m=20 + S4 + var-rule random）==="
say "阶段 1：等臂 B/C/D 跑完…"
_w=0
while [ "$(_n_mn64)" -gt 0 ]; do
  sleep 30; _w=$((_w + 1))
  [ "$_w" -ge 600 ] && { say "❌ 等了 5 h ⇒ 退出"; exit 4; }
done
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

m=20
laths=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range($m)))")
d="$ROOT/dry_E"
[ -d "$d" ] && mv "$d" "${d}_superseded_$(date +%s)"
say "起臂 E：--m 20 --var-rule random（nv=240，~570 MB）cores 8-11"
taskset -c 8-11 $PY -u _bk_exp.py $BASE --out "$ROOT" --tag E --laths "$laths" \
    --var-rule random > _w2_r581_mn64_E.log 2>&1
say "臂 E 结束 exit=$? Traceback=$(grep -c '^Traceback' _w2_r581_mn64_E.log || true)"

say "── 五臂对照（A/B/C/D/E）──"
$PY _r581_mn64read.py "$ROOT" A B C D E 2>&1 | tee -a "$LOG"
say "=== R581 MN64D DONE ==="
