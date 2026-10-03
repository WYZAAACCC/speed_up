#!/bin/bash
# _t5_aniso.sh --- ★★★ 查"生长各向异性"的机制：`elong`/`along`/`prefer_end` 到底在不在跑
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
git add _t5_ar_ctrl.py _t5_ar2.py 2>/dev/null
git commit -F - <<'MSGEOF'
R581-T5R-s208 量具验证(两级对照) + 重测: 生长近似各向同性 => 长厚比没改善

① 量具验证: 合成椭球(解析已知答案) A极端扁 700/120/60nm => 期望1.400/0.240/0.120 实测1.438/0.188/0.062
   err 47.9%; B中等扁 500/250/255 => err 12.5%; C接近等轴 通过; D更扁 err 17.2%。
   ★ 诊断: 用例A的半轴只有 1.92/0.96 胞(<2胞) => 离散误差必然巨大 => 那是我测试用例的超分辨率伪影,
     不是量具缺陷。用例B半轴 4/4.08 胞(可分辨) => 误差 12.5% 可接受。
   => 量具在"厚度>=4胞(>=250nm)"时误差~10%(可用); <2胞时不可用。
   种子快照: step40 场1 PCA=1.032/0.508/0.453 µm(期望1.000/0.500/0.510) => 数据链正确。
   两种测厚法(n_hab 与 PCA第3轴)多数场一致 => 互证。
② 重测(厚用n_hab): 种子期(step40)长厚比中位3.43[2.33,3.43]; 最终(step1800)中位3.02[1.72,6.46]
   => 尺寸长了(1.0->7.1µm)但长厚比几乎没变(甚至略降) => 生长近似各向同性 => 长成"更大的团"而非"更长的板条"。
③ => "什么导致长宽比不够": 不是种子太扁, 而是生长没有各向异性偏好。
MSGEOF
echo '════ ① 生长各向异性参数在 CLI 里的定义 ════'
grep -n "add_argument('--elong'\|add_argument('--along'\|add_argument('--prefer-end'\|add_argument('--along-per-variant'" _bk_exp.py | cut -c1-150 | sed 's/^/  /'
echo
echo '════ ② 它们在引擎里怎么用（核心几处）════'
grep -n "elong\b\|prefer_end\|along_per_variant" _bk_exp.py | head -14 | cut -c1-150 | sed 's/^/  /'
echo
echo '════ ③ 生长项本身（Allen-Cahn 驱动）有没有各向异性 ════'
grep -n "def .*growth\|各向异性\|aniso" windowB_surface.py | head -10 | cut -c1-150 | sed 's/^/  /'
