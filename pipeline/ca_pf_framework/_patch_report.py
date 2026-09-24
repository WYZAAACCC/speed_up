# -*- coding: utf-8 -*-
import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/CA3D_FIX_REPORT_2026-09-23.md"
s = io.open(P, encoding="utf-8").read()

old = '3. **D1 的分位选择未做敏感度扫描**（p90 / max / 面积加权平均三档对照），目前只用了 p90。'
new = ('3. **D1 分位选择已做敏感度**（`_audit_d1.py`）：熔池算例下 `p50 / p90 / p100` 结果**逐位相同**'
       '（池内前沿 ΔT 近似均匀，分位不起作用）。**结论：本区制下 D1 不敏感**；'
       '只有当前沿跨越很宽的 ΔT 区间（强梯度 + 长晶粒）时才需要重扫。')
s = s.replace(old, new) if old in s else s

old2 = '8. `decentered / analytic` 两个旧模式保留，仅供对照与考古；**任何新结果不得再用它们**。'
new2 = ('8. `decentered / analytic` 两个旧模式保留，仅供对照与考古；**任何新结果不得再用它们**。\n'
        '9. **`seed_solid_from_substrate` 的性能**：改成各向异性 Voronoi 后是 O(种子数×冷胞数)，'
        '64 种子 / 150³ 算例约 10 s。已改为**分块 + 精确剪枝**（利用 sup ≥ |Δ|；剪枝版与暴力参考'
        '**逐位相同**，已用 30³/40³ 两例核对）。\n'
        '10. **新架构的含义**：低于固相线的液相归给「包络先到」的晶粒，因此池内绝大部分胞的'
        '**归属时刻由热场给、归属对象由包络竞争给**（本演示 95%）。这正是审计 §5 想要的架构；'
        '但它也意味着 CA 自身包络动理学在当前热历史下上场机会少，要单独考它需要更慢的冷却算例。')
s = s.replace(old2, new2) if old2 in s else s

old3 = '基线（修前）日志与熔池 gid：`_audit_logs/baseline/`。'
new3 = ('基线（修前）日志与熔池 gid：`_audit_logs/baseline/`。\n\n'
        '---\n\n## 7. 最后一次全量回归的读数\n\n'
        '| 套件 | 项 | 结果 | 说明 |\n|---|---|---|---|\n'
        '| `verify_ca3d.py` | 21 | **PASS 20 / WARN 1 / FAIL 0** | WARN 是既有的 F_MIN 敏感度（A 档参数） |\n'
        '| `verify_ca3d_solute.py` | 11 | **11 / 0 / 0** | 未受影响 |\n'
        '| `verify_ca3d_physics.py` | 16 | **16 / 0 / 0** | T4b/T4c 已按支撑函数与径向函数的区分修正 |\n'
        '| `verify_ca3d_envelope.py`（新） | 12 | **12 / 0 / 0** | 本次新增的正面判据 E1~E6 |\n'
        '| `verify_ca3d_wc_cet.py` | 12 | 见 `_audit_logs/after_fix1/`（基线 10/2/0） | 那次 22 min 的跑用的是剪枝前的等价代码 |\n\n'
        '日志：`_audit_logs/final_verify_ca3d*.log`、`_audit_logs/after_fix1/`。')
s = s.replace(old3, new3) if old3 in s else s

io.open(P, "w", encoding="utf-8").write(s)
print("修复报告已补 §5/§7; 行数 =", s.count(chr(10))+1)