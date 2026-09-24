import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/demo_meltpool_growth.py"
s = io.open(P, encoding="utf-8").read()
if "fig_meltpool_3d.py" in s:
    print("already"); raise SystemExit
s = s.replace("    fig_process(ca, snaps, times)\n    fig_final3d(ca)",
              "    fig_process(ca, snaps, times)\n"
              "    # 三维图统一由 fig_meltpool_3d.py 出（那里的软件渲染器才能把晶界画成实心面片）\n"
              "    # fig_final3d(ca)", 1)
io.open(P, "w", encoding="utf-8").write(s)
print("disabled demo's 3D figure")