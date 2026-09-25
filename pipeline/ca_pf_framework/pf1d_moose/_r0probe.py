import io, sys, os, subprocess
sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose")
import mk_phys3d as M3
H = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"
BIN = "/root/moose/modules/phase_field/phase_field-opt"
ENV = dict(os.environ)
ENV["PATH"] = "/root/miniconda3/envs/moose/bin:" + ENV.get("PATH", "")
# 3D, NO automatic_scaling, 3 steps only -> read the unscaled |R0|
s = M3.make_input(8.0e-6, 1600, 1.5e-7, "2.0e-7", "2.04", 400, scaling=False)
assert "automatic_scaling" not in s
d = os.path.join(H, "R0probe3D")
if not os.path.isdir(d):
    os.makedirs(d)
io.open(os.path.join(d, "p.i"), "w", encoding="utf-8").write(s)
r = subprocess.run([BIN, "-i", "p.i"], cwd=d, capture_output=True, text=True, timeout=1200, env=ENV)
out = r.stdout + r.stderr
n0 = out.count(" 0 Nonlinear"); n1 = out.count("\n 1 Nonlinear")
vals = [l.strip() for l in out.splitlines() if "0 Nonlinear" in l]
print("rc", r.returncode, "n0", n0, "n1", n1)
print("\n".join(vals[:4]))