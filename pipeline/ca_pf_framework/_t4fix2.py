import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/verify_ca3d_physics.py"
s = io.open(P, encoding="utf-8").read()
s = s.replace('chk("T4c 对照: decentered 规则"偏离正确律"的幅度（多晶淘汰失败根因）",',
              'chk("T4c 对照: decentered 规则偏离正确律的幅度（多晶淘汰失败根因）",', 1)
io.open(P, "w", encoding="utf-8").write(s)
print("fixed quotes")