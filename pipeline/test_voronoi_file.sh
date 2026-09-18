#!/bin/bash
# 最小对照：PolycrystalVoronoi 用 file_name 时能不能正确染色？
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
BIN=/root/moose/modules/phase_field/phase_field-opt
mkdir -p /root/work/tv && cd /root/work/tv || exit 1

# 种子文件：5 个点排成一行
cat > seeds.csv <<'EOF'
x,y
0.1,0.5
0.3,0.5
0.5,0.5
0.7,0.5
0.9,0.5
EOF

mk() {
cat > t.i <<EOF
[Mesh]
  type = GeneratedMesh
  dim = 2
  nx = 40
  ny = 20
  xmin = 0
  xmax = 1
  ymin = 0
  ymax = 1
[]
[GlobalParams]
  op_num = 8
  var_name_base = gr
[]
[Variables]
  [PolycrystalVariables]
  []
[]
[UserObjects]
  [voronoi]
    type = PolycrystalVoronoi
$1
    int_width = 0.02
  []
  [gt]
    type = GrainTracker
  []
[]
[Modules]
  [PhaseField]
    [GrainGrowth]
    []
  []
[]
[ICs]
  [PolycrystalICs]
    [PolycrystalColoringIC]
      polycrystal_ic_uo = voronoi
    []
  []
[]
[AuxVariables]
  [unique_grains]
    order = CONSTANT
    family = MONOMIAL
  []
[]
[AuxKernels]
  [ug]
    type = FeatureFloodCountAux
    variable = unique_grains
    flood_counter = gt
    field_display = UNIQUE_REGION
  []
[]
[Materials]
  [consts]
    type = GenericConstantMaterial
    prop_names  = 'L      mu      gamma_asymm  kappa_op'
    prop_values = '0.2    1.0e6   1.5          1.0e-6'
  []
[]
[Postprocessors]
  [ngr]
    type = FeatureFloodCount
    variable = gr0
    threshold = 0.5
  []
[]
[Executioner]
  type = Transient
  num_steps = 1
  dt = 0.01
[]
[Outputs]
  csv = true
  exodus = true
[]
EOF
    "$BIN" -i t.i > out.log 2>&1
    echo "   退出码 $?  $(grep -c 'ERROR' out.log) 个错误"
    grep -i 'error' out.log | head -2
    if [ -f t_out.csv ]; then
        echo "   末行: $(tail -1 t_out.csv)"
    fi
    if [ -f t_out.e ]; then
        python3 - <<'PY'
import numpy as np
from netCDF4 import Dataset
ds = Dataset('t_out.e','r')
nm=[b''.join(r).decode(errors='replace').replace('\x00','').strip()
    for r in ds.variables['name_elem_var'][:]]
if 'unique_grains' in nm:
    j=nm.index('unique_grains')+1
    for key in (f'vals_elem_var{j}eb1', f'vals_elem_var{j}'):
        if key in ds.variables:
            g=np.rint(np.asarray(ds.variables[key][:])[-1]).astype(int); break
    print(f"   unique_grains 取值: {np.unique(g)}  （应看到多个晶粒 ID）")
else:
    print("   (无 unique_grains 输出)")
PY
    fi
}

echo "=== A. 用 grain_num = 5（对照组，应该正常）==="
mk "    grain_num = 5
    rand_seed = 1"

echo
echo "=== B. 用 file_name = seeds.csv（待测）==="
mk "    file_name = seeds.csv"

echo
echo "=== C. 用 file_name + 显式 coloring_algorithm = bt ==="
mk "    file_name = seeds.csv
    coloring_algorithm = bt"
