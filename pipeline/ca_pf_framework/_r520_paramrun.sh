#!/usr/bin/env bash
# R520 —— **任务(5) 的"短跑定参数"**：按 `R507_SHAPE_CLOSURE.md §5` 的**五约束自洽配置**跑一次。
#
# ## 为什么这一步不需要等拍板
#   goal 明确写着「**在起大算例之前先短跑定参数，再长跑**」——
#   本跑就是那一步"短跑定参数"。它**不是生产大算例**，目的是**用实测检验我推的参数闭环**：
#   * 椭球核 + `α_KM = 0.011` + 给足场数 ⇒ `nfsv_nofield` 是否真的降下来？
#   * 块数 × 每块根数 ⇒ C3（块内多根堆叠）是否真的出现？
#   * `nf2` ⇒ C4（块间接触）是否出现？
#
# ## 与归档双臂的关键差别（**逐条记账**）
#   | 项 | 归档 abA/abB | **本跑** | 为什么 |
#   |---|---|---|---|
#   | `α_KM` | 0.041739 | **0.011** | 框架参考值；0.0417 使块厚 12.2 µm **超文献带 2 倍** |
#   | `--laths` | 24 项 / 12 变体 | **108 项 / 12 变体（每变体 9 场）** | abA 的 `nfsv_nofield=9` 就是**每变体只有 2 场**造成的 |
#   | 核形状 | `disc`（尖边圆柱） | **`ellipsoid`** | 五约束下 `disc` 的交集是**空集** |
#   | 块数 | 未指定（受 `n(T)` 全盒上限约束） | **`--nuc-block-target 8`** | 正确口径是 `B·n` |
#   | 时钟 | 旧路径（CFL 当时间） | **`--qs-clock 1`** | 1B |
#   | 超临界 | 关 | **`--nuc-supercrit 1`** | 消除"播一片溶一片" |
#   | 位点 | 用尽即止 | **`--nuc-sites-refill 1`** | 位点物理上不应"用尽" |
#   | `--multi-block` | abA **没开** | **开** | 否则 `blk_nprof`/`nblk_sig` 是空列（R-3 的教训） |
#
# ## 预登记判据（**先写死**）
#   P1【不崩】无 `Traceback`；CSV 行数 > 0。
#   P2【变体饱和被解开】**`nfsv_nofield` 必须显著小于 abA 的 9**（判据：≤ 3）。
#   P3【事件数接近目标】`n_athermal_ev / n_target_final ≥ 0.7`（abA 是 13/23 = 0.57）。
#   P4【C3】末态 `blk_nprof` 必须**同时**有 >1 的值**和**多个块（≥2 个条目）。
#   P5【C4】末态 `nf2 > 0`。
#   P6【负对照】本跑的 `blk_nprof` 必须与 abA 的**不同**（abA 是空列）——
#      否则说明 `--multi-block` 没生效、P4 是空的。
#
# ⚠ 规模：`N=64`（4 µm）、`B_max = 32`、`B = 8`、`n(T_end≈350) = 5.75` ⇒ 目标 ≈ 46 根。
#   用时预算：~21 个温度档 × `--qs-max-relax 100` ≈ 2100+ 步。
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1

OUT=_exp/_bk_mb
# 12 变体 × 9 场 = 108 项
LATHS=$(/root/miniconda3/envs/ml/bin/python - <<'PYEOF'
print(','.join(str(v) for v in range(1, 13) for _ in range(9)))
PYEOF
)

$PY -u _bk_exp.py \
  --N 64 --dx-nm 62.5 --every 20 --snap-every 200 --phi-band-every 200 \
  --pair-every 0 --norm-smooth 0 --nthreads 16 --laths "$LATHS" \
  --plate-L 1000 --plate-W 500 --plate-T 510 \
  --gamma0 0.25 --beta-h 6.477 --grow-stack \
  --nuc-law athermal --nuc-init 6 --nuc-fresh-every 6 \
  --nuc-block-target 8 --nuc-shape ellipsoid \
  --nuc-supercrit 1 --nuc-sites-refill 1 \
  --qs-clock 1 --qs-max-relax 100 \
  --alpha-km 0.011 --T-end 350.0 --cool-rate 2.3524e6 \
  --facet-proj 0 --facet-excl 0 --reinit-dt 1e-4 --reinit-band 6.0 \
  --multi-block --steps 4000 --tag r520param --out $OUT \
  > _w2_r520_param.log 2>&1
echo "退出码=$?  $(date '+%F %T')"
echo
echo "== 判据求值 =="
$PY -u _r520_paramverdict.py
