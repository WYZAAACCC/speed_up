# -*- coding: utf-8 -*-
# Test B: same physics as mk_quad (production quadratic f_loc), in a real 3D mesh
# with a PLANAR front advancing along x, insulated lateral BCs.
# With a y,z-independent solution this must reproduce the 1D answer; it exercises the
# full 3D assembly / 3D gradient / 3D solver path.
import io
import mk_quad as MQ

HERE = "/mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose"
OLD_MESH = """[Mesh]
  type = GeneratedMesh
  dim = 1
  nx = %d
  xmin = 0.0
  xmax = %.4e
[]"""


def make_input(xmax, nx, tend, Wv, aform, lvs_n, front, ny=3, nz=3, ly=None):
    if ly is None:
        ly = 3.0 * (xmax / nx)   # lateral spacing == dx so the cell measure matches 1D
    s = MQ.make_input(xmax, nx, tend, Wv, aform, lvs_n, front)
    old = OLD_MESH % (nx, xmax)
    assert old in s, "mesh anchor"
    new = ("[Mesh]\n  type = GeneratedMesh\n  dim = 3\n  nx = %d\n  ny = %d\n  nz = %d\n"
           "  xmin = 0.0\n  xmax = %.4e\n  ymin = 0.0\n  ymax = %.4e\n"
           "  zmin = 0.0\n  zmax = %.4e\n[]" % (nx, ny, nz, xmax, ly, ly))
    return s.replace(old, new, 1)


if __name__ == "__main__":
    io.open(HERE + "/_quad3d.i", "w", encoding="utf-8").write(
        make_input(8.0e-6, 1600, 5.0e-5, "2.0e-7", "2.04", 400, "smooth"))
    print("ok")