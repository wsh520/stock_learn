"""
生成一朵玫瑰花并保存为图片（PNG）
运行：python make_rose.py
依赖：matplotlib, numpy
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager

# ---------- 可调参数 ----------
PETAL_K = 7                 # 控制“花瓣数”（r = |sin(k*θ)| 型）; k 为奇数时真实花瓣数为 k
LAYERS = 8                  # 花瓣层数（数值越大越丰满）
PETAL_SCALE = 1.2           # 花瓣基础尺度
PETAL_LINEWIDTH = 1.2
STEM_WIDTH = 5
OUTPUT_PATH = "rose_qixi.png"   # 输出文件名
GREETING = "七夕快乐，爱你永远"   # 图片上的问候语（若字体不可用可能不显示中文）

# 可选颜色配置（可用 CSS/HTML 颜色名或 RGB 元组）
PETAL_EDGE_COLOR = "#b30000"
STEM_COLOR = "#0b6623"
LEAF_FILL_ALPHA = 0.6
PETAL_LINESTYLE = "-"


# ---------- 字体设置（尝试设置中文字体，若失败使用默认） ----------
def _set_chinese_font():
    # 常见中文字体名，可以按系统实际情况调整
    candidates = ["SimHei", "Microsoft YaHei", "WenQuanYi Micro Hei", "Noto Sans CJK SC"]
    for name in candidates:
        try:
            font = font_manager.FontProperties(family=name)
            plt.rcParams['font.family'] = font.get_name()
            return
        except Exception:
            continue
    # 若没有找到中文字体，保持 matplotlib 默认字体（可能导致中文显示为方块）
    return

_set_chinese_font()


# ---------- 绘图开始 ----------
fig = plt.figure(figsize=(6, 8))
ax = plt.gca()

# 花瓣（使用多层 rhodonea / rose 曲线叠加）
theta = np.linspace(0, 2 * np.pi, 4000)
k = PETAL_K
a = PETAL_SCALE

scales = np.linspace(1.0, 0.55, LAYERS)
for idx, s in enumerate(scales):
    # 绝对值使曲线成为闭合花瓣形状
    r = s * a * np.abs(np.sin(k * theta + idx * 0.08))  # 每层略微偏移，增加自然感
    x = r * np.cos(theta)
    y = r * np.sin(theta) + 0.5  # 向上移动花瓣中心
    ax.plot(x, y,
            linewidth=PETAL_LINEWIDTH,
            linestyle=PETAL_LINESTYLE,
            color=PETAL_EDGE_COLOR,
            alpha=0.9 * (0.9 - idx * 0.05))  # 外层略淡，内层较亮

# 花蕊（一个小螺旋）
t_core = np.linspace(0, 6 * np.pi, 1200)
r_core = 0.02 * t_core
x_core = r_core * np.cos(t_core)
y_core = r_core * np.sin(t_core) + 0.5
ax.plot(x_core, y_core, linewidth=1.1)

# 花茎（平滑曲线）
t = np.linspace(0, 1.8, 400)
x_stem = 0.06 * np.sin(6 * t)  # 轻微弯曲
y_stem = -t - 0.22 * t**2 - 0.15
ax.plot(x_stem, y_stem, linewidth=STEM_WIDTH, solid_capstyle='round', color=STEM_COLOR)

# 叶子（两个椭圆填充）
def ellipse(cx, cy, rx, ry, angle_deg, resolution=400):
    u = np.linspace(0, 2*np.pi, resolution)
    cos_a = np.cos(np.deg2rad(angle_deg))
    sin_a = np.sin(np.deg2rad(angle_deg))
    x = cx + rx * np.cos(u) * cos_a - ry * np.sin(u) * sin_a
    y = cy + rx * np.cos(u) * sin_a + ry * np.sin(u) * cos_a
    return x, y

# 左叶
x1, y1 = ellipse(-0.28, -0.95, 0.36, 0.18, 36)
ax.fill(x1, y1, alpha=LEAF_FILL_ALPHA, linewidth=0, color=STEM_COLOR)
# 右叶
x2, y2 = ellipse(0.36, -1.28, 0.40, 0.20, -28)
ax.fill(x2, y2, alpha=LEAF_FILL_ALPHA, linewidth=0, color=STEM_COLOR)

# 装饰性缎带环（小圆环）
phi = np.linspace(0, 2*np.pi, 600)
x_rib = 0.1*np.cos(phi) + 0.12
y_rib = 0.05*np.sin(phi) - 0.25
ax.plot(x_rib, y_rib, linewidth=2.0)

# 文本（问候语）
ax.text(0.0, -1.95, GREETING, ha='center', va='center', fontsize=16, fontweight='bold')

# 画布设置
ax.set_aspect('equal', adjustable='box')
ax.axis('off')
plt.tight_layout()

# 保存文件
plt.savefig(OUTPUT_PATH, dpi=200, bbox_inches='tight', pad_inches=0.1)
plt.show()

print(f"已保存：{OUTPUT_PATH}")
