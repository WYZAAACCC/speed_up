#!/bin/bash
# 通用跑算例的壳：把 Windows 侧的 .i 转成 LF 拷进 /root/work/<case>，跑，再把结果拉回 F 盘。
#   用法： bash _run_case.sh <case名> <F盘上的 .i 路径> [额外的 CLI 覆盖...]
set +u
set -o pipefail
CASE="${1:?需要 case 名}"
SRC="${2:?需要 .i 路径}"
shift 2
EXTRA=("$@")

source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
R="/root/work/${CASE}"
rm -rf "$R"
mkdir -p "$R"
cd "$R" || exit 1
sed 's/\r$//' "$SRC" > "$R/case.i"

# 生产输入要读 columnar_seeds.csv（PolycrystalVoronoi 的 file_name）——
# 它是相对工作目录的，所以必须拷到算例目录里。
REPO_F=/mnt/f/speed_up
if grep -q 'columnar_seeds.csv' "$R/case.i"; then
  cp -f "$REPO_F/pipeline/columnar_seeds.csv" "$R/" || echo "警告：种子文件没拷进来"
fi

mkdir -p .jitcache
cp -rn /root/work/jitcache_seed/. .jitcache/ 2>/dev/null

echo "== 算例目录 $R =="
echo "== 行数 $(wc -l < case.i) =="
SUBMIT="${SUBMIT:-/root/projects/gibbs/gibbs-opt}"
echo "== 二进制 $SUBMIT =="
START=$(date +%s)
timeout "${WALL:-3600}" "$SUBMIT" -i case.i "${EXTRA[@]}" > run.log 2>&1
RC=$?
END=$(date +%s)
echo "rc=$RC  墙钟 $((END-START)) s"
echo "JIT 失败 = $(grep -c 'JIT compile failed' run.log)"
echo "未收敛   = $(grep -c 'Solve Did NOT Converge' run.log)"
echo "发散     = $(grep -c 'DIVERGED' run.log)"
sed "s/\x1b\[[0-9;]*m//g" run.log | grep -A12 -m1 '\*\*\* ERROR' | head -16
echo "--- 末 12 行 ---"
tail -12 run.log
echo "--- CSV ---"
head -1 case_out.csv 2>/dev/null
sed -n 2p case_out.csv 2>/dev/null
tail -1 case_out.csv 2>/dev/null

DEST="/mnt/f/speed_up/pipeline/gibbs/prod3d/results_${CASE}"
mkdir -p "$DEST"
cp -f run.log case.i "$DEST"/ 2>/dev/null
cp -f case_out.csv "$DEST"/ 2>/dev/null
# 跨晶界剖面的 CSV 是**每个时间步一个文件**（AGENTS.md 教训 25）—— 一起拉回来
cp -f case_out_profile_*.csv "$DEST"/ 2>/dev/null
cp -f /tmp/gibbs_build.log "$DEST"/ 2>/dev/null
echo "== 结果已复制到 $DEST =="
