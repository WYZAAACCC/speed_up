#!/bin/bash
# 量 AD 版的材料值，与已知的非 AD 值对比，定位 4.6% 的首步残差差异。
#
# 已知（非 AD 版 t=0，来自 try3_out.csv）：
#   kappa_op  1.7999171949286e-06 / 1.2474965935325e-06
#   gamma_asymm 1.4998896049988 / 1.0274456153675
#   L         1785931.7243125 / 5.2672580365761e-40
# 若 AD 版这三个值逐位相同 -> 差异在别处（align4 或核求值）
# 若不同 -> 直接定位到是哪个材料
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/s1d_mat
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
cp /root/work/s1d_w/stage1_meltpool_d.i ./M.i
cp /root/work/s1d_w/columnar_seeds.csv .

python3 - <<'PY'
import re
s = open("M.i", encoding="utf-8").read()
s = re.sub(r"^  end_time = .*$", "  end_time = 0", s, flags=re.M)
s = re.sub(r"^  nl_max_its = .*$", "  nl_max_its = 1", s, flags=re.M)
s = s.replace("file_base = stage1d", "file_base = M")
# 用 ADElementExtremeMaterialProperty（非 AD 的读不了 AD 属性）
diag = []
for prop in ("kappa_op", "gamma_asymm", "L", "align4"):
    for vt in ("min", "max"):
        diag.append(f"""  [{prop}_{vt}]
    type = ADElementExtremeMaterialProperty
    mat_prop = {prop}
    value_type = {vt}
    execute_on = 'initial timestep_end'
  []
""")
i = s.index("\n[Postprocessors]\n") + len("\n[Postprocessors]\n")
s = s[:i] + "".join(diag) + s[i:]
assert s.count("type = ADDerivativeParsedMaterial") == 4
assert s.count("type = ADGrainGrowth") == 8
open("M.i", "w", encoding="utf-8").write(s)
print("M.i 写好（end_time=0，只做 initial 求值）")
PY

setsid --wait "$MOOSE" -i M.i > run.log 2>&1
echo "退出码 $?"
echo
echo "======== AD 版材料值（t=0）========"
head -1 M_out.csv | tr ',' '\n' | paste -d' ' - <(sed -n 2p M_out.csv | tr ',' '\n') 2>/dev/null | grep -E "kappa_op|gamma_asymm|^L_|align4" | sed 's/^/  /'
echo
echo "======== 与非 AD 对照 ========"
cat <<'EOF'
  非 AD: kappa_op  max=1.7999171949286e-06  min=1.2474965935325e-06
  非 AD: gamma_asymm max=1.4998896049988    min=1.0274456153675
  非 AD: L          max=1785931.7243125     min=5.2672580365761e-40
EOF
grep -a -m3 -E '\*\*\* ERROR' run.log | sed 's/^/  /'
