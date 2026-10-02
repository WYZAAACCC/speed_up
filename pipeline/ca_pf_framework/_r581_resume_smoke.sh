#!/bin/bash
# _r581_resume_smoke.sh --- ★★★★★ `--resume` **冒烟**：先证明它"能跑"，再谈"逐位"
#
# ## 设计（三段）
# | 段 | 做什么 | 产物 |
# |---|---|---|
# | **S1** | 跑 `--steps 20`、`--ckpt-every 10` ⇒ 在 step 10/20 各存一帧 | `_exp/_bk_rsmoke/dry_rs1/` |
# | **S2** | 从 **step 10** 的检查点 **续跑**到 `--steps 16` | `_exp/_bk_rsmoke/dry_rs2/` |
# | **S3** | （对照）**一次跑完** `--steps 16` | `_exp/_bk_rsmoke/dry_rs3/` |
# ⇒ **S2 与 S3 在 step 10–16 上应逐位相同**（那是门 1 的雏形）
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT=_exp/_bk_rsmoke
LOG=_w2_r581_rsmoke.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

COMMON="--N 64 --dx-nm 62.5 --every 1 --snap-every 100 --pair-every 50 \
 --nthreads 4 --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
 --grow-stack --nuc-law athermal --nuc-init 6 --nuc-block-target 5 \
 --nuc-shape ellipsoid --nuc-supercrit 1 --nuc-sites-refill 1 \
 --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
 --cool-rate 2.3524e6 --reinit-dt 1e-4 --reinit-band 6.0 \
 --nuc-overlap-nm 62.5 --pf-phi onfly --h-chunk 4"
LATHS=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range(20)))")

for t in rs1 rs2 rs3; do
  [ -d "$ROOT/dry_$t" ] && mv "$ROOT/dry_$t" "$ROOT/dry_${t}_superseded_$(date '+%Y%m%d_%H%M%S')"
done

say '=== ① S1：跑 10 步（⇒ 检查点最大帧 = step 10），每 10 步存 ==='
# ★ 为什么只跑 10 步：S2 要**从 step 10 续跑**；若 S1 跑到 20，目录里最大帧就是 20，
#   `--resume <目录>` 会自动挑 20 ⇒ 再想"从 10 续"就选不到了（冒烟第二版踩过）。
timeout 1800 env -u MALLOC_MMAP_THRESHOLD_ -u MALLOC_TRIM_THRESHOLD_ -u MALLOC_ARENA_MAX \
  taskset -c 0-7 $PY -u _bk_exp.py $COMMON \
  --steps 10 --ckpt-every 10 --ckpt-keep 2 \
  --out "$ROOT" --tag rs1 --laths "$LATHS" > "_w2_r581_rsmoke_rs1.log" 2>&1
say "  S1 exit=$?  Traceback=$(grep -c '^Traceback' _w2_r581_rsmoke_rs1.log || echo 0)"
ls -la "$ROOT/dry_rs1/ckpt/" 2>/dev/null | sed 's/^/    /'
grep '\[ckpt' _w2_r581_rsmoke_rs1.log 2>/dev/null | tail -4 | sed 's/^/    /'

# ★ 给**目录** ⇒ 让 `--resume` 自动挑 `step` 最大的那一帧
#   （教训：A/B 交替命名下 `ckpt_A.npz` 会被 step 0/20/40… 反复覆盖，
#    手写文件名**会拿到错的那一帧** —— 冒烟第一版就是这么错的）
CK="$ROOT/dry_rs1/ckpt"
if [ ! -d "$CK" ]; then
  say '  ❌ 没有检查点目录 ⇒ 冒烟无法继续'
  exit 1
fi
say "  用检查点目录（自动挑最新）：$CK"
ls -la "$CK" | sed 's/^/    /'

say '=== ② S2：**从检查点续跑**到 step 16 ==='
timeout 1800 env -u MALLOC_MMAP_THRESHOLD_ -u MALLOC_TRIM_THRESHOLD_ -u MALLOC_ARENA_MAX \
  taskset -c 4-7 $PY -u _bk_exp.py $COMMON \
  --steps 16 --resume "$CK" \
  --out "$ROOT" --tag rs2 --laths "$LATHS" > "_w2_r581_rsmoke_rs2.log" 2>&1
say "  S2 exit=$?  Traceback=$(grep -c '^Traceback' _w2_r581_rsmoke_rs2.log || echo 0)"
grep -E '从检查点续跑|自动选|检查点 step=|驱动层已回填|版本哈希' _w2_r581_rsmoke_rs2.log 2>/dev/null | sed 's/^/    /'
echo '  ── S2 日志尾 6 行 ──'
tail -6 _w2_r581_rsmoke_rs2.log 2>/dev/null | cut -c1-120 | sed 's/^/    /'

say '=== ③ S3：对照——一次跑完 16 步 ==='
timeout 1800 env -u MALLOC_MMAP_THRESHOLD_ -u MALLOC_TRIM_THRESHOLD_ -u MALLOC_ARENA_MAX \
  taskset -c 0-3 $PY -u _bk_exp.py $COMMON \
  --steps 16 \
  --out "$ROOT" --tag rs3 --laths "$LATHS" > "_w2_r581_rsmoke_rs3.log" 2>&1
say "  S3 exit=$?  Traceback=$(grep -c '^Traceback' _w2_r581_rsmoke_rs3.log || echo 0)"

say '=== ④ 结果表 ==='
for t in rs1 rs2 rs3; do
  printf '  %-4s series 行数=%-4s 末步=%s\n' "$t" \
    "$(wc -l < "$ROOT/dry_$t/series.csv" 2>/dev/null)" \
    "$(tail -1 "$ROOT/dry_$t/series.csv" 2>/dev/null | cut -d, -f1)"
done
say '  （下一步用 Python 逐位比 S2 vs S3 的 step 10–16）'
say '=== SMOKE DONE ==='
