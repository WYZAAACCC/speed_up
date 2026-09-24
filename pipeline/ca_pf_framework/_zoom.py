import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.image import imread
img = imread("/mnt/f/speed_up/pipeline/ca_pf_framework/FIG_pool_grains_3d_v2.png")
H, W, _ = img.shape
print("full", W, H)
crops = [("A", 0.485, 0.175, 0.635, 0.44),    # ② 蓝色斑块
         ("B", 0.02, 0.20, 0.20, 0.45),        # ① 左中棋盘
         ("C", 0.62, 0.62, 0.80, 0.88)]        # ① 池底棋盘
fig, axes = plt.subplots(1, 3, figsize=(18, 7))
for (nm, fx0, fy0, fx1, fy1), ax in zip(crops, axes):
    c = img[int(fy0*H):int(fy1*H), int(fx0*W):int(fx1*W)]
    ax.imshow(c, interpolation="nearest")
    ax.set_title("%s  %dx%d" % (nm, c.shape[1], c.shape[0]), fontsize=11)
    ax.axis("off")
fig.tight_layout()
fig.savefig("/mnt/f/speed_up/pipeline/ca_pf_framework/_zoom_v2.png", dpi=110)
print("saved")