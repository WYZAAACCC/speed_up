#!/bin/bash
# _t5_append_s190.sh --- 第 190 轮：★ 硬要求验证（全部数据在 F 盘）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
cat >> R581_T5_RESTART.md <<'EOF'

---

## §190 ★★★★ 第 190 轮：**硬要求验证** —— 「全部仿真数据存 F 盘」**已验证满足**

### §190.1 用户逐字要求
> **「全部仿真数据存 F 盘以便日后用新量具重测（重跑前一律 mv 归档改名，绝不删除）」**

### §190.2 实测（`_t5_fcheck.sh`）
```
① 所有臂的数据都在 /mnt/f/speed_up/pipeline/ca_pf_framework/_exp/ 下 ✓
   例：dry_t5H3 1.5G(ckpt=2 snap=31) · dry_t5V2 991M(ckpt=2 snap=13)
       dry_abA 496M(snap=150) · dry_t5L62/t5L0 各 341M · dry_t5G3 460M
   ★ 且含两个归档目录：
       dry_t5G3_superseded_1790967923
       dry_t5V2_superseded_1790986242
     ⇒ **符合"绝不删除、一律 mv 归档改名"** ✓
② `_exp` 合计 = **19 GB**
③ ★ **WSL 侧全盘搜 `series.csv`（产物指纹）⇒ **空****
   ⇒ **没有产物只留在 WSL** ✓
   （`/root/work` 存在，但那是 MOOSE 项目的工作目录，**不含本 goal 的仿真产物**）
```

### §190.3 ★ 判定
| 要求 | 状态 |
|---|---|
| **全部数据在 F 盘** | ✅ **满足** |
| **重跑前一律 `mv` 归档改名、绝不删除** | ✅ **满足**（两个 `_superseded_` 目录在场）|
| **便于日后用新量具重测** | ✅ **满足**（`series.csv` + `snap_*.npz` + `ckpt/*.npz` 齐备，31+13 张快照）|

**⇒ 这是本 goal 四条硬要求里**第一条被显式实测确认**的**（另三条：量具正确性、无依赖并行、先回顾后修，
   已在 §143/§161/§162/§160 等处分别验证）。**
EOF
echo "已追加，现在 $(wc -l < R581_T5_RESTART.md) 行"
cd /mnt/f/speed_up || exit 1
git add pipeline/ca_pf_framework/R581_T5_RESTART.md pipeline/ca_pf_framework/_t5_fcheck.sh pipeline/ca_pf_framework/_t5_append_s190.sh
git commit -F - <<'MSGEOF'
R581-T5R-s190 ★★★★ 硬要求验证: 「全部仿真数据存 F 盘」已验证满足

用户逐字要求: 全部仿真数据存 F 盘以便日后用新量具重测(重跑前一律 mv 归档改名, 绝不删除)。

实测: ① 所有臂的数据都在 /mnt/f/.../_exp/ 下(dry_t5H3 1.5G ckpt=2 snap=31; dry_t5V2 991M ckpt=2 snap=13;
dry_abA 496M snap=150; 等), 且含两个归档目录 dry_t5G3_superseded_1790967923 / dry_t5V2_superseded_1790986242
=> 符合"绝不删除、一律 mv 归档改名";
② _exp 合计 19 GB;
③ ★ WSL 侧全盘搜 series.csv(产物指纹) => 空 => 没有产物只留在 WSL
(/root/work 存在但那是 MOOSE 项目的工作目录, 不含本 goal 的仿真产物)。

判定: 全部数据在 F 盘 ✅ / 一律 mv 归档绝不删除 ✅ / 便于日后用新量具重测 ✅(series.csv + snap_*.npz +
ckpt/*.npz 齐备, 31+13 张快照)。
=> 这是本 goal 四条硬要求里第一条被显式实测确认的。
MSGEOF
git log --oneline -1
