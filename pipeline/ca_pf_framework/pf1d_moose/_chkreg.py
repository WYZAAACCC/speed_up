import io, sys
sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose")
import mk_phys as M
H = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"
io.open(H + "/_reg.i", "w", encoding="utf-8").write(
    M.make_input(8.0e-6, 1600, 5.0e-5, "2.0e-7", "2.04", 400))
s = io.open(H + "/_reg.i", encoding="utf-8").read()
for blk in ("f_loc", "M_mob", "at_susc"):
    i = s.index("  [" + blk + "]")
    j = s.index("\n  []\n", i)
    print(s[i:j].replace("log(", "log(")[:700])
    print("-----")
print("C1/C2 in file:", "1.0000000000e-03" in s, "9.5000000000e-01" in s)