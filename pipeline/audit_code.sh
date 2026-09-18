#!/bin/bash
# 系统性核对代码事实，供撰写给专家审核的报告使用。
# 所有数字都从这里取，不凭记忆。
F=/mnt/f/speed_up/pipeline
S=$F/stage1_meltpool_c.i
echo "############ 1. 网格与几何 ############"
grep -nE "^ +(nx|ny|xmin|xmax|ymin|ymax|elem_type|int_width) =" $S | sed 's/^/  /'
grep -n "liquid_pool" -A6 $S | grep -E "combinatorial_geometry|block_name" | sed 's/^/  /'
echo
echo "############ 2. 变量 ############"
grep -n "op_num\|var_name_base" $S | grep -v "^.*#" | head -5 | sed 's/^/  /'
sed -n '/^\[Variables\]/,/^\[\]/p' $S | grep -E "^  \[|type =" | sed 's/^/  /'
echo
echo "############ 3. 温度场 ############"
sed -n '/\[laser_T\]/,/^  \[\]/p' $S | head -8 | sed 's/^/  /'
echo
echo "############ 4. 材料（物理参数） ############"
grep -nE "property_name|constant_names|constant_expressions|prop_names|prop_values|type =" $S | sed -n '/Materials/,$p' | head -0
awk '/^\[Materials\]/,/^\[Postprocessors\]/' $S | grep -E "^  \[|property_name|constant_names|constant_expressions|prop_names|prop_values|type =|expression" | head -60 | sed 's/^/  /'
echo
echo "############ 5. 核 ############"
awk '/^\[Kernels\]/,/^\[Modules\]/' $S | grep -E "^  \[|type =|variable =|mob_name|kappa_name|f_name" | sed 's/^/  /'
awk '/^\[Modules\]/,/^\[Materials\]/' $S | grep -E "^  \[|type =|variable_mobility|mobility|kappa" | sed 's/^/  /'
echo
echo "############ 6. 求解器 ############"
awk '/^\[Executioner\]/,/^\[Outputs\]/' $S | grep -E "type =|scheme|solve_type|petsc_options|l_max_its|l_tol|nl_max_its|nl_rel_tol|nl_abs_tol|end_time|dtmax|^ +dt =|cutback|growth|optimal" | sed 's/^/  /'
echo
echo "############ 7. 后处理（诊断量） ############"
awk '/^\[Postprocessors\]/,/^\[Preconditioning\]/' $S | grep -E "^  \[|type =" | sed 's/^/  /'
