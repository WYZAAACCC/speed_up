#!/bin/bash
# _r581_mn64b.sh --- ★★★★ **N=64 上补 `m=20`**（R66 已验证 N=64 代理有效）
#
# ## 为什么（R66 的授权）
# R66 实测：**`m` 上限在 N=64 与 N=160 上表现完全一致**
# （N=160/m=4 ⇒ 同变体 max = 4；N=64/m=4 ⇒ **也是 4**）。
# ⇒ **"同变体 max 是否随 `m` 上升"这个判据，在 N=64 上就有效**，
#    而 **N=64 只要 ~1 h**（`p2_m20` 在 N=160 上要 **11.1 h**，见 R53 的时间账）。
# ⇒ **用 N=64 先把 `m=20` 的信号拿到，再决定要不要花那 11 h。**
#
# ## 链条
# 等 `_r581_mn64.sh`（臂 A/B）跑完 ⇒ 跑 **臂 C（`m=20`，nv=240）**。
# 内存：`9.000 × 240 × 262144 B = 566 MB` ⇒ cores 8-11 足够，不碰 0-3/4-7。
#
# ## 判据（**预先写死**）
# | 臂 | `m` | 预期「同变体 max」 |
# |---|---|---|
# | A（已跑） | 4  | **4**（实测 ✅） |
# | B（在跑） | 12 | **应当 > 4** |
# | **C（本脚本）** | **20** | **应当 > B，趋向 20** |
# 若 C 的 max 明显高于 B ⇒ **`m` 的杠杆作用确认** ⇒ 才值得上 N=160 的 `p2_m20`。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_mn64"
STEPS="${R581MN64_STEPS:-250}"
LOG=_w2_r581_mn64b.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

# ⚠⚠ **两个坑都躲开**：
#   ① P27：`ps | grep` 会匹配到 `grep` 自己 ⇒ 用 `[m]` 打断字面；
#   ② ★ **但 `[m]n64` 仍会匹配到**本脚本自己**（`bash _r581_mn64b.sh` 的命令行里含 "mn64"）
#      ⇒ **会无限等下去**（第一版就是这个错，当场抓到）。
#   ⇒ 改成**只数真正的臂**：命令行里必须同时有 `_bk_exp.py` 与 `--out _exp/_bk_mn64`。
_n_mn64() {
  ps -eo args --no-headers 2>/dev/null \
    | grep '_bk_exp\.py' | grep -v grep \
    | grep -c -- '--out _exp/_bk_mn64'
}

say "=== R581-R67：N=64 上补 m=20（R66 已授权 N=64 代理）==="
say "阶段 1：等 _r581_mn64.sh（臂 A/B）跑完…"
_w=0
while [ "$(_n_mn64)" -gt 0 ]; do
  sleep 30; _w=$((_w + 1))
  [ "$_w" -ge 480 ] && { say "❌ 等了 4 h ⇒ 退出（不硬上）"; exit 4; }
done
say "阶段 1 完成"

avail=$(awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo)
say "内存闸：MemAvailable = ${avail} MB（要求 ≥ 1500）"
[ "$avail" -lt 1500 ] && { say "❌ 内存不足 ⇒ 不起跑"; exit 3; }

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
d="$ROOT/dry_C"
[ -d "$d" ] && mv "$d" "${d}_superseded_$(date +%s)"
say "起臂 C：--m 20（nv=240）cores 8-11"
taskset -c 8-11 $PY -u _bk_exp.py $BASE --out "$ROOT" --tag C --laths "$laths" \
    > _w2_r581_mn64_C.log 2>&1
say "臂 C 结束 exit=$? Traceback=$(grep -c '^Traceback' _w2_r581_mn64_C.log || true)"

say "── 三个臂的判决表 ──"
$PY _r581_mn64read.py "$ROOT" A B C 2>&1 | tee -a "$LOG"
say "=== R581 MN64B DONE ==="
