#!/bin/bash
# =============================================================================
# Phase 3 第一增量的验收：独立偏析项能否让 Γ_GB 与 wGB 无关（修 T11）
# =============================================================================
# 背景：实测 `Γ_GB ∝ w_gb`（T11，+101.9% / +103.9%），而同一仓库里晶界能 σ
#   在 wGB 下**逐位不变** ⇒ 晶界能那半套有配套重标定、偏析这半套没有。
#
# 本脚本扫 wGB × {不带偏析项, 带偏析项}，看 Γ_GB 的变化：
#   * 不带：应该复现 ~+100%（正比）
#   * 带（Ω = Ω0/wGB）：应该**基本不变**
#
# ⚠ Ω0 是 **calibration 参数**，不是 Ti64 材料常数（审计禁止事项 5）。
# ⚠ 域长必须跟着放大（T11 的教训）：wGB=0.8 µm 时 tanh 尾巴会伸到边界、污染结果。
#
# 用法：bash run_phase3_seg.sh
#   OMEGA0=-4.6e-9 WGB_LIST="0.4e-6 0.8e-6" bash run_phase3_seg.sh
# =============================================================================
set -eo pipefail

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${ROOT:-/mnt/f/speedup_work/p3seg}"
MOOSE="${MOOSE:-/root/projects/gb_jac/gb_jac-opt}"
DX="${DX:-2.5e-8}"            # 0.025 µm，固定不动（Γ 随 wGB 的对照必须在同一 dx 上）
LDOM="${LDOM:-1.2e-5}"        # 12 µm，放大域避免边界污染
WGB_LIST="${WGB_LIST:-0.4e-6 0.8e-6}"
OMEGA0="${OMEGA0:--4.6e-9}"
# ⚠ t_end 必须是 **30 s** 量级（照抄已验证的 run_t11.sh 的 T_END=30）。
#   第一版我写成 1e-5 s，结果溶质只够扩散 √(Dt) ≈ 2 nm、Γ_GB 全程恒等于 0，
#   与 T11 实测的 1.8e-9 差得离谱 —— 白跑一轮。
#   **慢扩散过程的时间尺度别凭感觉设，照抄已验证的算例。**
T_END="${T_END:-30.0}"

rm -rf "$ROOT"; mkdir -p "$ROOT"; cd "$ROOT"

echo "wGB 扫描：dx=$DX m，域长=$LDOM m，Ω0=$OMEGA0"
echo

for WGB in $WGB_LIST; do
  for TAG in noseg seg; do
    D="$ROOT/${TAG}_${WGB}"; mkdir -p "$D"; cd "$D"
    EXTRA=""
    [ "$TAG" = "seg" ] && EXTRA="--f-seg $OMEGA0"
    # shellcheck disable=SC2086
    python3 "$HERE/make_1d_gb.py" --out gb.i --dx "$DX" --ldom "$LDOM" \
        --wgb "$WGB" --t-end "$T_END" $EXTRA > gen.log 2>&1 \
      || { echo "  生成失败 $TAG $WGB"; tail -3 gen.log; continue; }
    timeout 1800 "$MOOSE" -i gb.i > run.log 2>&1 || true
    cd "$ROOT"
  done
done

echo "=== 结果：Γ_GB（由算例自带的 Gamma_GB 后处理给出）==="
python3 - "$ROOT" <<'PY'
import csv, os, re, sys
root = sys.argv[1]
res = {}
for d in sorted(os.listdir(root)):
    m = re.match(r"(noseg|seg)_([\d.eE+-]+)$", d)
    if not m:
        continue
    f = os.path.join(root, d, "gb_out.csv")
    if not os.path.exists(f):
        continue
    rows = list(csv.DictReader(open(f)))
    key = [k for k in rows[0] if "amma" in k or "GB" in k]
    if not key:
        print("  %-22s 找不到 Γ_GB 后处理（列：%s）" % (d, list(rows[0])))
        continue
    res[d] = float(rows[-1][key[0]])

print("  %-22s %-18s %s" % ("算例", "Γ_GB", "相对 wGB=0.4µm"))
print("  " + "-" * 60)
for tag in ("noseg", "seg"):
    base = None
    for d in sorted(res, key=lambda s: (s.split("_")[1], s)):
        if not d.startswith(tag + "_"):
            continue
        if base is None:
            base = res[d]
        rel = (res[d] - base) / abs(base) * 100 if base else 0
        print("  %-22s %-18.6g %+.2f%%" % (d, res[d], rel))
    print()
print("判读：")
print("  noseg 档应复现 ~+100%（Γ ∝ wGB，T11 的病灶）")
print("  seg   档应接近 0% （1/wGB 重标定生效 ⇒ Γ 与 wGB 无关）")
PY
