#!/usr/bin/env bash
# R464 —— **S2/reinit 的受控判决实验**：`reinit` 到底该不该跑、多久跑一次？
#
# ## 为什么要跑它（承接 R461/R463 的取证）
#
# R463 从归档 CSV 已证实两条（**不重跑**）：
#   · `reinit_dt=1e-4` 的**定时**路径在 800 步里**一次都没触发**（`t_s(末)=3.16e-5 < 1e-4`）；
#   · 但 `abB` 有 **11 次形核事件**，而 `windowB_surface.py:4050-4054` 的
#     **强制**路径（`reinitialize(force=True)`）**绕过 `skip_tol`**（`:4380` 的 `(not force)`）
#     ⇒ **11 次真跑的 reinit**；而 `dry_saSet2`（**预摆**臂）**0 次**。
#
# ⇒ 所以 S2 的原话「reinit 形同虚设」**对两类臂结论相反**，必须分开说。
#   而"后果是 φ 不再是距离函数"这半句**从来没被直接量过** —— 因为
#   `snap_*.npz` **不存 φ**（只存 `region` + 稀疏带，见 `_r462_snapkeys.py`）。
#   ⇒ 本轮用 `--phi-every` 把**整场 φ** 落盘，然后直接量 `|∇φ|`。
#
# ## 单变量对照（**只差一个因素**）
#
#   两条臂**逐字相同**，只差 `--reinit-dt`：
#     A（生产口径）: `--reinit-dt 1e-4`  ⇒ 定时路径 ≈ 永不触发（只靠形核强制）
#     B（频繁口径）: `--reinit-dt 1e-6`  ⇒ 每 ~37 步触发一次定时路径
#   ⚠ 两者的**形核序列必须相同**（同一 `--seed` 路径、同一 `--alpha-km`、同一冷速）
#     ⇒ 否则就不是单变量了。两条臂用同一 `--laths` / `--nuc-*` / `--cool-rate`。
#
# ## 预登记的判据（**先写死**）
#
#   P1 【对照有效性】两条臂的 `nreg_used(末)` 必须**相同**（形核事件数一致）。
#      不一致 ⇒ **本次对照作废**（说明 reinit 反馈到了形核，那是另一回事，得单独查）。
#   P2 【退化存在性】A 臂 `median|∇φ|@6Δx` 从 t=0 到末步**必须下降**
#      且 `med(末) ≤ 0.95` ⇒ 否则「φ 不再是距离函数」这条**在本配置下不成立**，
#      S2 的"后果"必须按**未复现**记账。
#   P3 【reinit 有效性】若 P2 成立，则 B 臂的 `med(末) − med(0)` 必须**显著小于** A 臂的
#      （判据：`|Δ_B| ≤ 0.5·|Δ_A|`）⇒ 否则"多跑 reinit 能救"**不成立**。
#   P4 【成本】B 臂的总墙钟 / A 臂的总墙钟 = 真实代价比（**实测**，不推算）。
#
#   ⚠ **P2/P3 都可能 FAIL**，那就照实报。**不得**为了让它过而改判据。
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
export PYTHONDONTWRITEBYTECODE=1

OUT=_exp/_bk_mb
NT=${NT:-4}
STEPS=${STEPS:-600}
N=${N:-64}
DX=${DX:-62.5}
PHIEVERY=${PHIEVERY:-50}

# ---- 公共臂参数（**除了 --reinit-dt 之外一个字都不许变**）----
COMMON="--N $N --dx-nm $DX --pair-every 50 --every 50 --norm-smooth 0 \
 --nthreads $NT --laths 1,2,3,4,5,6,7,8 --plate-L 1000 --plate-W 500 --plate-T 510 \
 --gamma0 0.25 --beta-h 6.477 --grow-stack --nuc-law athermal --nuc-init 4 \
 --nuc-fresh-every 4 --alpha-km 0.041739 --T-end 298.0 --cool-rate 2.3524e6 \
 --facet-proj 0 --facet-excl 0 --steps $STEPS --snap-every $PHIEVERY \
 --phi-every $PHIEVERY --reinit-band 6.0 --out $OUT"

run_arm () {
  local TAG="$1" RDT="$2"
  echo "=============================================================="
  echo "== 臂 $TAG  (--reinit-dt $RDT)   $(date '+%F %T')"
  echo "=============================================================="
  $PY -u _bk_exp.py $COMMON --reinit-dt "$RDT" --tag "$TAG" \
      > "_w2_r464_${TAG}.log" 2>&1
  echo "臂 $TAG 退出码=$?  $(date '+%F %T')"
}

# C-5 硬闸（沿用 _r445_abfix.sh 的纪律：不满足就不许起跑）
echo "---- C-5 硬闸预检 ----"
$PY -u - <<'PYEOF'
import sys
sys.path.insert(0, '.')
import windowB_closure as CL
for N, dxnm in ((64, 62.5), (112, 62.5)):
    dx = dxnm * 1e-9
    for steps, t_nm in ((600, 510.0), (800, 510.0)):
        need = CL.beta_h_min(steps, dx, t_nm * 1e-9)
        print('  N=%-4d dx=%.1f nm steps=%-5d t=%.0f nm ⇒ β_h ≥ %.3f  (实配 6.477)  %s'
              % (N, dxnm, steps, t_nm, need, 'OK' if need <= 6.477 else '❌ 不满足'))
PYEOF

# ★ 并行走（用户要求：前后没有依赖的工作并行完成）
run_arm r464A 1e-4 &
PA=$!
run_arm r464B 1e-6 &
PB=$!
wait $PA; RA=$?
wait $PB; RB=$?
echo "=============================================================="
echo "两臂结束：A 退出码=$RA  B 退出码=$RB   $(date '+%F %T')"
echo "=============================================================="
