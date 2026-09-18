#!/bin/bash
# 定论实验：在**缩小网格**的真实算例上，用 PETSc 的 -snes_test_jacobian
# 把装配出的雅可比与有限差分雅可比对比。
#
#   ||J - Jfd||_F / ||J||_F   —— 这个比值大就说明雅可比装配错了，
#   牛顿残差出现非零地板就是它的直接后果。
#
# 对比两组：
#   D2b   新版 align4（逐晶粒加权平均）+ 2b 开启
#   no2b  同一份输入，但 L2b 恒为 1（= v1，已知能收敛）
# 若 D2b 的比值远大于 no2b，就坐实了问题在 2b 进入 L 这条路径上。
#
# 网格缩到 20x8，让有限差分可行（全尺寸 129k dof 做不了）。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose

SRC=/mnt/f/speed_up/pipeline
D=/root/work/s1d_jac
MOOSE=/root/moose/modules/phase_field/phase_field-opt

pkill -9 -f phase_field-opt 2>/dev/null
sleep 1
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1

for f in stage1_meltpool_d.i; do sed 's/\r$//' "$SRC/$f" > "$f"; done
cp "$SRC/columnar_seeds.csv" .

# 缩网格 + 打开雅可比自检
shrink() {
  sed -i 's/^    nx = .*/    nx = 20/; s/^    ny = .*/    ny = 8/' "$1"
  sed -i 's/^  end_time = .*/  end_time = 1e-6/' "$1"
  sed -i "s|petsc_options_iname = '\(.*\)'|petsc_options_iname = '\1 -snes_test_jacobian'|" "$1"
  sed -i "s|petsc_options_value = '\(.*\)'|petsc_options_value = '\1 1'|" "$1"
  sed -i "s/^  nl_max_its = .*/  nl_max_its = 6/" "$1"
}

cp stage1_meltpool_d.i D2b.i
shrink D2b.i
sed -i 's/file_base = stage1d/file_base = j_D2b/' D2b.i

cp stage1_meltpool_d.i no2b.i
shrink no2b.i
# L2b 恒为 1（关掉 2b）
python3 - <<'PY'
import re
s = open("no2b.i", encoding="utf-8").read()
s = re.sub(r"(\[L2b\][\s\S]*?expression = ')[^']*(')",
           r"\g<1>1\g<2>", s, count=1)
assert "expression = '1'" in s, "L2b 没被改掉"
open("no2b.i", "w", encoding="utf-8").write(s)
print("no2b: L2b -> 1")
PY
sed -i 's/file_base = stage1d/file_base = j_no2b/' no2b.i

echo "网格: $(grep -m1 'nx = ' D2b.i) $(grep -m1 'ny = ' D2b.i)"
grep -m1 petsc_options_iname D2b.i
echo

for t in no2b D2b; do
  echo "=============== $t ==============="
  timeout 900 setsid --wait "$MOOSE" -i "$t.i" > "$t.log" 2>&1
  echo "退出码 $?"
  grep -a "J - Jfd" "$t.log" | head -4
  grep -a -m2 -E '\*\*\* ERROR|NANORINF' "$t.log" || true
  echo
done
