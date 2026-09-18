#!/bin/bash
# 两个高区分度变体，与雅可比自检并行跑
#
#  W1 —— 只删掉 grad_align 这个**纯输出**的 AuxKernel（MaterialRealAux）
#        2b 的物理完全不变。若 W1 收敛，说明问题出在"读材料属性做输出"
#        这条路径扰动了材料求值顺序 —— 那会是个很隐蔽的坑。
#
#  W3 —— 把 2b 因子从 L 挪到 mu。
#        ACGrGrPoly **只用 mu 的值、不取任何导数**（源码已核），
#        所以 mu 依赖 eta 不会引入"被求导的错项"。
#        若 W3 收敛 -> 问题确实在 dL/dop 这条导数链上，而不是 2b 的物理。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

SRC=/mnt/f/speed_up/pipeline
D=/root/work/s1d_w13
MOOSE=/root/moose/modules/phase_field/phase_field-opt
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1

sed 's/\r$//' "$SRC/stage1_meltpool_d.i" > base.i
cp "$SRC/columnar_seeds.csv" .

python3 - <<'PY'
import re
base = open("base.i", encoding="utf-8").read()

def shrink(s, tag):
    s = re.sub(r"^  end_time = .*$", "  end_time = 6e-6", s, flags=re.M)
    s = s.replace("file_base = stage1d", f"file_base = {tag}")
    return s

# ---- W1: 删掉 [AuxKernels] 里的 [grad_align]（纯输出）----
w1 = re.sub(r"\n  # 对齐度从材料里取出[\s\S]*?\n  \[grad_align\]\n[\s\S]*?\n  \[\]\n",
            "\n", base, count=1)
if "[grad_align]" not in w1:
    raise SystemExit("W1: grad_align AuxKernel 没删掉")
open("W1.i", "w", encoding="utf-8").write(shrink(w1, "W1"))

# ---- W3: 2b 因子挪到 mu 上，L 的 2b 关掉 ----
w3 = re.sub(r"(\[L2b\][\s\S]*?expression = ')[^']*(')",
            r"\g<1>1\g<2>", base, count=1)
assert "expression = '1'" in w3
# barrier_mu 同时引用 align4
w3 = re.sub(r"(\[barrier_mu\][\s\S]*?)property_name = mu\n",
            r"\1property_name = mu\n    material_property_names = 'align4'\n",
            w3, count=1)
w3 = re.sub(r"(\[barrier_mu\][\s\S]*?expression = ')[^']*(')",
            r"\g<1>(mu0 * (1 - (1+boost)*0.5*(1+tanh((T-T_mid)/dT))))"
            r"*(1+0.7*(2*align4-1))\g<2>", w3, count=1)
assert "material_property_names = 'align4'" in w3
assert "2*align4-1" in w3
open("W3.i", "w", encoding="utf-8").write(shrink(w3, "W3"))
print("W1/W3 已生成")
PY

for t in W1 W3; do
  ( setsid --wait "$MOOSE" -i "$t.i" > "$t.log" 2>&1 ) &
done
wait
echo "W1/W3 结束"
