#!/bin/bash
# _r581_gate23.sh --- ★★★★★★ **门 2（计数回归）+ 门 3（真实路径冒烟）**
#
# ## 门 2 的两条（**都要**）
# | # | 判据 | 为什么需要 |
# |---|---|---|
# | **2a** | 现成量具 `_r581_countgate.sh`（`el.sigma_tensor`/`el.eps0_fields`/`fe.ed.soft_phi`/`argmin2` == 1/步 + 两个负对照） | 抓"每步多跑一遍"那类**性能回归**（P2） |
# | **★2b** | **同配置下「带 `--ckpt-every`」vs「不带」⇒ `series.csv` **逐位相同**** | ★ **比调用计数更硬**：它直接证明**检查点机制完全不扰动仿真** |
#
# ## 门 3：真实路径冒烟
# | # | 判据 |
# |---|---|
# | **3a** | `_bk_exp.py` 真实算例 + `--resume` ⇒ **共有列全逐位一致 + 无 `Traceback`** |
# | **3b** | 顺带：`--ckpt-every` 开与不开的**产物目录**对比（快照应逐位相同） |
#
# ⚠ 记账：**`--ckpt-every` 会额外写 `ckpt/`** ⇒ 那是**预期的**；本脚本比的是
#   **`series.csv` 与 `snap_*.npz`**（那些不该受任何影响）。
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT=_exp/_bk_g23
LOG=_w2_r581_g23.log
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

CFG="--N 64 --dx-nm 62.5 --every 5 --snap-every 10 --pair-every 50 \
 --nthreads 4 --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
 --grow-stack --nuc-law athermal --nuc-init 6 --nuc-block-target 5 \
 --nuc-shape ellipsoid --nuc-supercrit 1 --nuc-sites-refill 1 \
 --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
 --cool-rate 2.3524e6 --reinit-dt 1e-4 --reinit-band 6.0 \
 --nuc-overlap-nm 62.5 --pf-phi onfly --h-chunk 4 --steps 20"
LATHS=$("$PY" -c "print(','.join(str(v) for v in range(1,13) for _ in range(20)))")

run() {
  local tag="$1" extra="$2"
  [ -d "$ROOT/dry_$tag" ] && mv "$ROOT/dry_$tag" "$ROOT/dry_${tag}_superseded_$(date '+%Y%m%d_%H%M%S')"
  timeout 2400 env -u MALLOC_MMAP_THRESHOLD_ -u MALLOC_TRIM_THRESHOLD_ -u MALLOC_ARENA_MAX \
    taskset -c 0-7 $PY -u _bk_exp.py $CFG $extra \
    --out "$ROOT" --tag "$tag" --laths "$LATHS" > "_w2_r581_g23_${tag}.log" 2>&1
  printf '    %-9s exit=%d  Traceback=%s  末步=%s\n' "$tag" "$?" \
    "$(grep -c '^Traceback' "_w2_r581_g23_${tag}.log" 2>/dev/null | head -1)" \
    "$(tail -1 "$ROOT/dry_$tag/series.csv" 2>/dev/null | cut -d, -f1)"
}

say '════════ 门 2a：现成的计数回归量具 ════════'
if [ -f _r581_countgate.sh ]; then
  timeout 1800 bash _r581_countgate.sh > _w2_r581_g23_cgate.log 2>&1
  say "  countgate exit=$?"
  grep -E '✅|❌|PASS|FAIL|NC-A|NC-B' _w2_r581_g23_cgate.log 2>/dev/null \
    | tail -12 | sed 's/^/    /'
else
  say '  ⚠ 没有 `_r581_countgate.sh`'
fi

say '════════ 门 2b：**带 vs 不带 `--ckpt-every`** ⇒ `series.csv` 必须逐位相同 ════════'
say '  ① 不带（关）'
run g23_off ""
say '  ② 带（--ckpt-every 2 --ckpt-keep 2）'
run g23_on "--ckpt-every 2 --ckpt-keep 2"
say '  ── 逐位比较（**这是比调用计数更硬的判据**）──'
taskset -c 16-19 $PY _r581_ckpt_cmp.py \
  "$ROOT/dry_g23_off/series.csv" "$ROOT/dry_g23_on/series.csv" step 2>&1 \
  | grep -E '差异字段数|共有列逐位一致|Vt |f_var|nslab_n1|nf3 |nf2 |有差异的列' \
  | sed 's/^/    /'
say '  ── 顺带：快照是否也逐位相同 ──'
SAME=0; DIFF=0
for f in "$ROOT/dry_g23_off"/snap_*.npz; do
  b=$(basename "$f")
  if [ -f "$ROOT/dry_g23_on/$b" ]; then
    if cmp -s "$f" "$ROOT/dry_g23_on/$b"; then SAME=$((SAME+1)); else DIFF=$((DIFF+1)); fi
  fi
done
say "    快照：逐位相同 $SAME 个 / 不同 $DIFF 个"
say '    （⚠ `snap_*.npz` 是压缩包 ⇒ 同样的数据也可能因时间戳/顺序不同而字节不同；'
say '      所以这一条只作**参考**，硬判据是上面的 `series.csv`）'

say '════════ 门 3：真实路径 `--resume` 冒烟 ════════'
# 从 g23_on 的 step 10 检查点续跑到 20
say '  ① 找 step 10 的帧'
CK=$($PY - <<'PYEOF'
import os, numpy as np
d = '_exp/_bk_g23/dry_g23_on/ckpt'
best = None
for f in sorted(os.listdir(d)):
    if f.startswith('ckpt') and f.endswith('.npz'):
        with np.load(os.path.join(d, f), allow_pickle=False) as z:
            s = int(np.asarray(z['step']).item())
        if s == 10:
            best = os.path.join(d, f)
print(best or '')
PYEOF
)
say "     $CK"
if [ -z "$CK" ]; then
  say '  ⚠ 没找到 step 10 的帧（检查点间隔是 2 ⇒ 应有 @10）⇒ 改用目录自动挑'
  CK="$ROOT/dry_g23_on/ckpt"
fi
say '  ② 续跑到 20'
run g23_rs "--resume $CK"
grep -E '自动选|检查点 step=|驱动层已回填|P0 已回填' "_w2_r581_g23_g23_rs.log" 2>/dev/null \
  | sed 's/^/    /'
say '  ③ **共有列逐位**（g23_rs vs g23_on —— 后者是"一次跑完"的真值）'
taskset -c 16-19 $PY _r581_ckpt_cmp.py \
  "$ROOT/dry_g23_rs/series.csv" "$ROOT/dry_g23_on/series.csv" step 2>&1 \
  | grep -E '差异字段数|共有列逐位一致|共有 step|Vt |f_var|nslab_n1|nf3 |nf2 |有差异的列' \
  | sed 's/^/    /'

say '════════ 汇总 ════════'
say '  门2a（计数回归）= 见上 countgate 的 ✅/❌'
say '  门2b（带/不带 --ckpt-every 的 series.csv 逐位）= 见上"差异字段数"'
say '  门3（--resume 真实路径逐位）= 见上"差异字段数"'
say '=== GATE23 DONE ==='
