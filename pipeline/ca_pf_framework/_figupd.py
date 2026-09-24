import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/make_overview_fig.py"
s = io.open(P, encoding="utf-8").read()
old = ' ("倾斜梯度下\\n取向淘汰未复现", "双晶正对照通过；多晶 + 倾斜 + 有限域需专门研究（放大域 + 侧向周期边界）", "开放", YELLOW),'
if old in s:
    new = ' ("倾斜梯度下\\n取向淘汰已修复", "根因=包络支撑律用错(L*max vs L/Sum)+格点路径偏差；修法=周期侧边界+analytic 捕获", "已修", GREEN),'
    s = s.replace(old, new, 1)
    io.open(P, "w", encoding="utf-8").write(s)
    print("fig text updated")
else:
    print("fig anchor not found (ok)")