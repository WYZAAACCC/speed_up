#!/bin/bash
# 把 GBSoluteSink 每一步"实际扣掉的量"加起来，与面上 Gamma 的增量做守恒对账。
set +u
D=${1:-/root/work/g3d_sinkG}
echo "== 每步 dM [mol] =="
grep -o 'dM = [-0-9.e+]*' "$D/run.log" | awk '{print $3}'
echo "== 合计（体相应共失去这么多） =="
grep -o 'dM = [-0-9.e+]*' "$D/run.log" | awk '{s+=$3} END {printf "%.6e\n", s}'
echo "== c_int_pp（第 12 列）：首页 / 初值行 / 末行 =="
head -1 "$D/case_out.csv" | cut -d, -f12
sed -n 2p "$D/case_out.csv" | cut -d, -f12
tail -1 "$D/case_out.csv" | cut -d, -f12
