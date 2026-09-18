#!/bin/bash
# 坐实"bt 染色只用 5 色、gr5/6/7 恒为零、11 个晶粒只有 5 个不同取向"这个判断。
#
# 依据（间接）：C 版与 D 版的逐变量初始残差都显示 gr5/gr6/gr7 ~ 1e-33..1e-45
#   （即恒等于零），而 grain_tracker = 11。
# 本次直接量：每个 gr 的 max/min + 11 个晶粒的取向分布。
source /root/miniconda3/etc/profile.d/conda.sh
conda activate moose
MOOSE=/root/moose/modules/phase_field/phase_field-opt
D=/root/work/s1d_ops
rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 1
cp /root/work/s1d_w/stage1_meltpool_d.i ./O.i
cp /root/work/s1d_w/columnar_seeds.csv .

python3 - <<'PY'
import re
s = open("O.i", encoding="utf-8").read()
s = re.sub(r"^  end_time = .*$", "  end_time = 0", s, flags=re.M)
s = re.sub(r"^  nl_max_its = .*$", "  nl_max_its = 1", s, flags=re.M)
s = s.replace("file_base = stage1d", "file_base = O")
diag = []
for i in range(8):
    for vt in ("min", "max"):
        diag.append(f"""  [gr{i}_{vt}]
    type = ElementExtremeValue
    variable = gr{i}
    value_type = {vt}
    execute_on = 'initial'
  []
""")
i = s.index("\n[Postprocessors]\n") + len("\n[Postprocessors]\n")
s = s[:i] + "".join(diag) + s[i:]
open("O.i", "w", encoding="utf-8").write(s)
print("O.i 写好（end_time=0，量 8 个序参量的极值）")
PY

setsid --wait "$MOOSE" -i O.i > run.log 2>&1
echo "退出码 $?"
echo
echo "======== 各序参量的 min/max（恒为零 = 该序参量没承载晶粒）========"
head -1 O_out.csv | tr ',' '\n' > /tmp/h.txt
sed -n 2p O_out.csv | tr ',' '\n' > /tmp/v.txt
paste -d' ' /tmp/h.txt /tmp/v.txt | grep -E "^gr[0-7]_" | sed 's/^/  /'
echo
echo "======== grain_tracker（应=11）========"
paste -d' ' /tmp/h.txt /tmp/v.txt | grep -E "grain_tracker|oc_mean|os_mean" | sed 's/^/  /'
echo
echo "======== 判读 ========"
python3 - <<'PY'
import re
h = open("/tmp/h.txt").read().split()
v = open("/tmp/v.txt").read().split()
d = dict(zip(h, v))
active = []
for i in range(8):
    mx = float(d.get(f"gr{i}_max", "0") or 0)
    if mx > 1e-6:
        active.append(i)
print(f"  实际承载晶粒的序参量: {active}  共 {len(active)} 个")
print(f"  grain_tracker = {d.get('grain_tracker')}")
print()
if len(active) < 8:
    print(f"  ==> **坐实**：op_num=8 但只有 {len(active)} 个序参量在用，"
          f"其余恒为零。")
    print(f"      11 个晶粒压在 {len(active)} 个序参量上 -> 取向必然重复。")
else:
    print("  ==> 8 个序参量都在用，与"只有 5 色"的判断不符，需重新分析。")
PY
