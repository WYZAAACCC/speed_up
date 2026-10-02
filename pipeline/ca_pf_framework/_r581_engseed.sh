#!/bin/bash
# _r581_engseed.sh --- ★ 形核种子的真实旋钮 `--eng-seed` 的**四道门**。
#
# ## ⚠ 这个脚本的前身叫 `_r581_nucseed.sh`，**测错了开关**（留痕）
#   我断言「`nuc_cfg` 的 `seed` 硬编码 11、CLI 没旋钮」（缺口 A22）⇒ 自己加了
#   `--nuc-seed`。**实测报错** `SyntaxError: keyword argument repeated: seed`
#   —— 因为 `nuc_cfg(...)` 里**本来就有** `seed=a.eng_seed`
#   ⇒ **真正的旋钮是 `--eng-seed`（default=11）**。
#   ⇒ A22 的"没有旋钮"那半句**是错的**，已撤回改动。见 P28。
#
# ## 本轮要证的（用**正确的**开关）
# | # | 判据 | 期望 |
# |---|---|---|
# | **G1** | `--eng-seed 11`（显式 = 默认）的 `series.csv` 与**不传**时**全部共有列逐位相同** | ✅ |
# | **G2** | 两臂的 `nuc_cfg.sites` **逐位相同** | ✅ |
# | **NC** | `--eng-seed 12` 的 `sites` **必须与 11 不同** | ✅ 必须不同 |
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
ROOT="_exp/_bk_ns"
CORES="${R581NS_CORES:-12-15}"
STEPS="${R581NS_STEPS:-10}"
COMMON="--N 64 --dx-nm 62.5 --steps $STEPS --every 1 --snap-every 99999 \
  --pair-every 0 --norm-smooth 0 --nthreads 4 --grow-stack \
  --nuc-law athermal --nuc-init 6 --nuc-block-target 3 --nuc-shape ellipsoid \
  --nuc-supercrit 1 --nuc-sites-refill 1 --nuc-overlap-nm 62.5 \
  --plate-L 1000 --plate-W 500 --plate-T 510 --gamma0 0.25 --beta-h 6.477 \
  --qs-clock 1 --qs-max-relax 100 --alpha-km 0.011 --T-end 350.0 \
  --cool-rate 2.3524e6 --eps0-mode einsum --ed-pair gather --k-loop act \
  --act-mode bincount --argmin2-mode copyto --grad-mode sliced --pf-phi onfly \
  --h-chunk 4 --extend-mode near --argmin2-reuse 1 --bbox-mode axis"

run() {  # run <tag> <额外参数...>
  local tag="$1"; shift
  local d="$ROOT/dry_$tag"
  [ -d "$d" ] && mv "$d" "${d}_superseded_$(date +%s)"
  taskset -c "$CORES" $PY -u _bk_exp.py $COMMON --out "$ROOT" --tag "$tag" "$@" \
      > "_w2_r581_ns_${tag}.log" 2>&1
  echo "   $tag: exit=$? Traceback=$(grep -c '^Traceback' "_w2_r581_ns_${tag}.log" || true)"
}

# P25：文本一律单引号，**绝不**在双引号里写反引号
echo '=== R581 `--eng-seed` 四道门 ==='
echo '── 三个臂：A=不传（默认）  B=--eng-seed 11  C=--eng-seed 12 ──'
run A
run B --eng-seed 11
run C --eng-seed 12

$PY - "$ROOT" <<'PYEOF'
import json, os, sys
import numpy as np
ROOT = sys.argv[1]

def series(tag):
    p = os.path.join(ROOT, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p): return None, None
    with open(p) as fh: h = fh.readline().strip().split(',')
    return h, np.genfromtxt(p, delimiter=',', names=True)

def sites(tag):
    p = os.path.join(ROOT, 'dry_' + tag, 'nuc_dbg.json')
    if not os.path.exists(p): return None
    j = json.load(open(p, encoding='utf-8'))
    return [(int(k), tuple(round(float(z), 15) for z in v))
            for k, v in j.get('nuc_cfg', {}).get('sites', [])]

print()
print('── G1：A（不传）vs B（--nuc-seed 11）的 series.csv **全部共有列逐位** ──')
hA, dA = series('A'); hB, dB = series('B')
if hA is None or hB is None:
    print('   ❌ 缺 series.csv'); G1 = False
else:
    common = [c for c in hA if c in hB and c != 'wall_s']
    bad = []
    for c in common:
        x = np.atleast_1d(dA[c]).astype(float); y = np.atleast_1d(dB[c]).astype(float)
        m = min(len(x), len(y)); x, y = x[:m], y[:m]
        b = np.isfinite(x) & np.isfinite(y)
        nanbad = (np.isnan(x) != np.isnan(y)).any()
        if (b.any() and not np.array_equal(x[b], y[b])) or nanbad:
            bad.append(c)
    G1 = (len(bad) == 0)
    print('   共有列 %d 个（已排除 wall_s）；差异列 %d 个 %s' % (len(common), len(bad), bad[:6]))
    print('   ⇒ %s' % ('✅ **逐位相同 ⇒ 门 1 过**' if G1 else '❌ 有差异'))

print()
print('── G2：A vs B 的 `nuc_cfg.sites`（含 12 位小数）──')
sA, sB, sC = sites('A'), sites('B'), sites('C')
for nm, s in (('A', sA), ('B', sB), ('C', sC)):
    print('   %s: %s' % (nm, '（无 nuc_dbg.json）' if s is None else
                        '共 %d 项，前 4 = %s' % (len(s), [k for k, _ in s[:4]])))
G2 = (sA is not None and sA == sB)
print('   ⇒ %s' % ('✅ 逐位相同' if G2 else '❌ 不同（或取不到）'))

print()
print('── NC（负对照）：C（--nuc-seed 12）**必须与 A 不同** ──')
NCok = (sC is not None and sA is not None and sC != sA)
print('   ⇒ %s' % ('✅ **不同 ⇒ 开关是活的**' if NCok
                  else '❌ **相同 ⇒ 开关是死的**（`--nuc-seed` 没接上）'))
if NCok:
    for i, (x, y) in enumerate(zip(sA, sC)):
        if x != y:
            print('     第 %d 项：seed11 场%-3d (%.6f, %.6f, %.6f) µm' % (i, x[0], *[z*1e6 for z in x[1]]))
            print('             seed12 场%-3d (%.6f, %.6f, %.6f) µm' % (y[0], *[z*1e6 for z in y[1]]))
            break

print()
print('=' * 88)
ok = G1 and G2 and NCok
print('✅ **`--nuc-seed` 四道门全过**：默认逐位不变 + 负对照证明开关是活的' if ok
      else '❌ 未全过：G1=%s G2=%s NC=%s' % (G1, G2, NCok))
sys.exit(0 if ok else 1)
PYEOF
echo "=== R581 NUCSEED DONE $(date '+%F %T') ==="
