import io, sys, os, subprocess
sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose")
import mk_phys3d as M3
H = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"
BIN = "/root/moose/modules/phase_field/phase_field-opt"
ENV = dict(os.environ)
ENV["PATH"] = "/root/miniconda3/envs/moose/bin:" + ENV.get("PATH", "")
s = M3.make_input(8.0e-6, 1600, 1.2e-6, "2.0e-7", "2.04", 400, scaling=False)
s = s.replace("nl_abs_tol = 1e-9", "nl_abs_tol = 1e-16", 1)
extra = """  [cmn]
    type = NodalMinValue
    variable = c
  []
  [cmx]
    type = NodalMaxValue
    variable = c
  []
"""
s = s.replace("\n[]\n\n[VectorPostprocessors]", "\n" + extra + "[]\n\n[VectorPostprocessors]", 1)
assert "NodalMinValue" in s
d = os.path.join(H, "range3D")
if not os.path.isdir(d):
    os.makedirs(d)
io.open(os.path.join(d, "p.i"), "w", encoding="utf-8").write(s)
r = subprocess.run([BIN, "-i", "p.i"], cwd=d, capture_output=True, text=True, timeout=1800, env=ENV)
out = r.stdout + r.stderr
io.open(os.path.join(d, "r.log"), "w", encoding="utf-8").write(out)
rows = [l for l in io.open(os.path.join(d, "p_out.csv"), encoding="utf-8").read().strip().splitlines()]
print("rc", r.returncode)
for l in rows[:3] + rows[-6:]:
    print(l)