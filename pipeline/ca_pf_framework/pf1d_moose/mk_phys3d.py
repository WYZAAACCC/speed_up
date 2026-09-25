# -*- coding: utf-8 -*-
# 3D twin of mk_phys (ideal-solution f_loc, correct antitrapping F = a W [c_l - c_s]).
# automatic_scaling + compute_scaling_once=false: the residual scales like dx^dim
# (1D ~1e-9 vs 3D ~1e-17 for the same physics), so absolute tolerances are only
# meaningful with scaling; and the scaling must be refreshed as the front advances.
import io
import mk_phys as MP

HERE = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"
OLD_MESH = "[Mesh]\n  type = GeneratedMesh\n  dim = 1\n  nx = %d\n  xmin = 0.0\n  xmax = %.4e\n[]"
SCALE = "  l_tol = 1e-10\n  automatic_scaling = true\n  compute_scaling_once = false"


def make_input(xmax, nx, tend, Wv, aform, lvs_n, ny=3, nz=3, scaling=True):
    s = MP.make_input(xmax, nx, tend, Wv, aform, lvs_n)
    old = OLD_MESH % (nx, xmax)
    assert old in s, "mesh anchor"
    ly = 3.0 * (xmax / nx)
    new = ("[Mesh]\n  type = GeneratedMesh\n  dim = 3\n  nx = %d\n  ny = %d\n  nz = %d\n"
           "  xmin = 0.0\n  xmax = %.4e\n  ymin = 0.0\n  ymax = %.4e\n"
           "  zmin = 0.0\n  zmax = %.4e\n[]" % (nx, ny, nz, xmax, ly, ly))
    s = s.replace(old, new, 1)
    if scaling:
        assert "  l_tol = 1e-10" in s, "l_tol anchor"
        s = s.replace("  l_tol = 1e-10", SCALE, 1)
    return s


if __name__ == "__main__":
    io.open(HERE + "/_phys3d.i", "w", encoding="utf-8").write(
        make_input(8.0e-6, 1600, 5.0e-5, "2.0e-7", "2.04", 400))
    print("ok")