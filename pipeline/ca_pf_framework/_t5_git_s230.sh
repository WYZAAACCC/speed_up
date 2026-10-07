#!/bin/bash
# _t5_git_s230.sh --- ★★★★★ 起"迁移率各向异性"验证（2×2，只新起 2 臂）
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/_t5_patch_mob.py pipeline/ca_pf_framework/_t5_ab_mob.sh \
        pipeline/ca_pf_framework/_t5_mobcli.sh pipeline/ca_pf_framework/_t5_mobratio.sh \
        pipeline/ca_pf_framework/_t5_mobchk.sh pipeline/ca_pf_framework/_t5_growthmech.sh \
        pipeline/ca_pf_framework/_t5_mobaniso.sh pipeline/ca_pf_framework/_t5_armon.py \
        pipeline/ca_pf_framework/_t5_short.py pipeline/ca_pf_framework/R581_T5_RESTART.md 2>/dev/null
git commit -F - <<'MSGEOF'
R581-T5R-s230 ★★★★★ 验"迁移率各向异性"公式 + 与 eng-elong 叠加(2x2, 只新起 2 臂)

## 关键发现（更正 §212 的 framing）
框架**有**伸长机制，且是已实现、有实测量的 —— 只是**默认没打开**:
 * windowB_surface.py:4668  elif mob_beta > 0.0 and nd_ref_ is not None and **mob_iform == 'ellipse'**:
 * **mob_beta = a.beta_h**（= --beta-h, abA 基线 6.477 > 0）=> **闸门本来就开**;
 * **只差 mob_iform == 'ellipse'**（默认 'exp2' => 走不到那段）;
 * 代码注释逐字: "极集本身凸 => 凸化恒等 => h(a)/h(w) 恰等于 --mob-ratio（实测 ratio=9 给 8.93）";
 * 而"解析 9.90 vs 引擎实际 1.24"那个老问题是 exp2 形式的 —— ellipse 正是 R64/§52 为修它而实现的;
 * 另有 --mob-wulff（Wulff 凸化/刻面, 默认关）与 --mob-dip（45° 凹陷, c=4 时 h(a)/h(w)=9.73）。
 * 仓库实测支持: BLOCK_SELFAC.md:28 "板条长轴 a 从 4.58 µm 单调长到 10.02 µm"(2853 步),
   且 :27 "α′/β 界面(F1)沿板条长轴 M(n) = M₀（无钉扎）"。

## 做了什么
1. 自验证补丁给 _t5_short.py 加 4 个透传(--mob-iform/--mob-ratio/--mob-wulff/--mob-dip),
   备份 -> 内存改 -> compile 通过才写盘 -> 六条复核全过; 四个都带"默认档不传"守卫
   => 归档路径与在跑的臂逐字不变。
2. 起 2x2（**复用两条已跑的臂 ⇒ 只新起 2 条**）:
   |                | mob-iform=exp2      | mob-iform=ellipse      |
   | eng-elong=0    | t5AB_A(已跑)        | **t5AM_ell**(新起)     | <= 验公式
   | eng-elong=7    | t5AD_700(已跑)      | **t5AM_combo**(新起)   | <= 验叠加
   参数与 t5AB_*/t5AD_* 逐项一致 => 唯一变量 = 这两个开关。
3. ★ 先验检查(必须): 查进程命令行确认参数真的进去了 ——
   pid=31837 --mob-iform ellipse --mob-ratio 9.0; pid=31836 + --eng-elong 7.0 => **通过** ✓
   ⚠ 记账: 引擎**横幅不打印迁移率形式** => 唯一可靠的先验方式是查进程命令行(这是引擎诊断的缺口)。
4. 监控扩到 11 臂(加入 t5AM_ell/t5AM_combo); 内存起后用 13689 / 余 10343 MB => 安全。

## 判据(预先写死)
1) 【公式是否起作用】t5AM_ell(ellipse, elong=0) 的长宽比应显著 > t5AB_A(1.85);
   若 ellipse 也上不去(仍 ~2) => 公式未真正起作用 => 记账且**不进入叠加**;
2) 【叠加是否更好】t5AM_combo 应 >= max(t5AD_700=6.55, t5AM_ell); 若 ≈6.55 => 两机制不叠加;
3) 时序闸(第28条): 只认同一末步 + >=3 个步点的趋势;
4) 副作用闸: 同时刻场数应与对照一致(eng-elong 已验无副作用; 本开关未验)。
MSGEOF
git log --oneline -1
