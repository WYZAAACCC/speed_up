# -*- coding: utf-8 -*-
import io
def banner(path, text, anchor=None):
    s = io.open(path, encoding="utf-8").read()
    if text[:60] in s:
        print("已存在:", path); return
    if anchor and anchor in s:
        s = s.replace(anchor, text + anchor, 1)
    else:
        s = text + s
    io.open(path, "w", encoding="utf-8").write(s)
    print("已加横幅:", path)

B = ('> **状态（2026-09-23）**：本文件记录的问题**已按** `CA3D_FIX_PLAN_2026-09-23.md` 修复，'
     '验收见 `CA3D_FIX_REPORT_2026-09-23.md`（T1~T8 全部达成）。\n'
     '> 本文件保留为**审计证据与复现记录**（含实测数字与探针脚本）。\n\n')
banner("/mnt/f/speed_up/pipeline/ca_pf_framework/CA3D_AUDIT_2026-09-23.md", B)

B2 = ('> **状态（2026-09-23）**：Step 0~5 已执行完（Step 6 演示与图已完成），'
      '执行结果与判据见 `CA3D_FIX_REPORT_2026-09-23.md`。\n\n')
banner("/mnt/f/speed_up/pipeline/ca_pf_framework/CA3D_FIX_PLAN_2026-09-23.md", B2)

B3 = ('> ⚠️ **重要（2026-09-23 审计结论）**：本报告 §5、§9、§10 里由 `decentered` 默认捕获产生的'
      '**几何/取向相关数字已作废**（该规则的 KD 各向异性被格点路径代价抹平：实测径向可达距离短 25~40%、'
      '体积 −25%、且不随 dx 收敛；两处过冷液相洪泛还依赖扫描顺序、并会制造 1 胞假晶粒）。\n'
      '> 修复与验收见 `CA3D_AUDIT_2026-09-23.md` / `CA3D_FIX_REPORT_2026-09-23.md`；'
      '新默认 `capture="envelope"`。**本报告未逐节改写**，引用时请先看修复报告。\n\n')
banner("/mnt/f/speed_up/pipeline/ca_pf_framework/CA3D_REPORT.md", B3)