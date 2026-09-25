# 在 W/dc >= 1 的区制下扫 ALPHA: 定 ALPHA*
import io, os, subprocess
BIN = "/root/moose/modules/phase_field/phase_field-opt"
os.environ["PATH"] = "/root/miniconda3/envs/moose/bin:" + os.environ.get("PATH", "")
BASE = "p1c_alpha2.i"
CASES = [("2.0e-7", "0.0"), ("2.0e-7", "2.0"), ("2.0e-7", "-2.0"),
         ("4.0e-7", "0.0"), ("4.0e-7", "2.0"), ("4.0e-7", "-2.0")]
WORK = "p1c_W.i"
def build(Wv, A):
    s = io.open(BASE, encoding="utf-8").read()
    assert "sqrt(2)*3.0e-8" in s, "phi_f W not found"
    s = s.replace("sqrt(2)*3.0e-8", "sqrt(2)*" + Wv, 1)
    lines = s.split(chr(10))
    hit = False
    for i, l in enumerate(lines):
        if "3.0e-8 0.6303" in l:
            lines[i] = "    constant_expressions = \"" + A + " " + Wv + " 0.6303\""
            hit = True
            break
    assert hit, "at_susc W not found"
    io.open(WORK, "w", encoding="utf-8").write(chr(10).join(lines))
    return Wv, A
print("W(nm)   ALPHA   c(1.00um)   dev vs c0=0.036    c(1.70um)   exit")
for Wv, A in CASES:
    build(Wv, A)
    for f in ("p1c_W_out.csv",):
        if os.path.exists(f): os.remove(f)
    rc, err = -1, True
    try:
        r = subprocess.run([BIN, "-i", WORK], capture_output=True, text=True, timeout=900)
        rc = r.returncode; err = ("ERROR" in r.stdout)
        if err:
            for l in r.stdout.splitlines():
                if "ERROR" in l: print("   " + l.strip()[:100]); break
    except Exception as e:
        print("   exc " + str(e)[:80])
    if os.path.exists("p1c_W_out.csv"):
        last = io.open("p1c_W_out.csv").read().strip().splitlines()[-1].split(",")
        c1000 = float(last[1]); c1700 = float(last[4]) if len(last) > 4 else float("nan")
        print("%-7s %-7s %-11.6f %+9.3e        %-11.6f %s" % (
            str(float(Wv)*1e9), A, c1000, c1000 - 0.036, c1700, rc))
    else:
        print("%-7s %-7s (no csv) exit=%s" % (str(float(Wv)*1e9), A, rc))
