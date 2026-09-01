"""Generate docs/architecture.png — a clean pipeline diagram for the README
and for sharing on social media.

Usage:
    python docs/make_diagram.py
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

BG = "#0D1117"
FG = "#E6EDF3"
MUTED = "#8B949E"

fig, ax = plt.subplots(figsize=(12.8, 6.6), dpi=150)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
ax.set_xlim(0, 100)
ax.set_ylim(0, 40)
ax.axis("off")


def box(x, y, w, h, text, fc, fs=9, tc="#FFFFFF", weight="bold", lw=0):
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.5,rounding_size=1.4",
        linewidth=lw, edgecolor=fc, facecolor=fc, zorder=2,
    )
    ax.add_patch(p)
    ax.text(
        x + w / 2, y + h / 2, text,
        ha="center", va="center", fontsize=fs, color=tc,
        weight=weight, zorder=3, linespacing=1.5,
    )


def arrow(x1, y1, x2, y2, color=MUTED, style="-|>", dashed=False):
    a = FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle=style, mutation_scale=16,
        linewidth=1.8, color=color, zorder=1,
        linestyle=(0, (4, 3)) if dashed else "solid",
    )
    ax.add_patch(a)


# Title
ax.text(50, 37.5, "Webasyst AI Rewriter — pipeline",
        ha="center", va="center", fontsize=17, color=FG, weight="bold")
ax.text(50, 34.6, "Batch AI rewrite of product cards via LLM + Webasyst REST API",
        ha="center", va="center", fontsize=10.5, color=MUTED)

# Main pipeline row
box(2, 20, 13, 8, "Sitemap\nsitemap-shop.xml", "#3A3F47", fs=8.5)
box(19, 20, 15, 8, "Scanner\ninventory.json", "#2563EB")
box(38, 20, 17, 8, "LLM Copywriter\nDeepSeek / OpenAI / Ollama", "#7C3AED")
box(59, 20, 15, 8, "Poster\nshop.product.update", "#059669")
box(78, 20, 17, 8, "Validator\nlive page check", "#D97706")

arrow(15, 24, 19, 24)
arrow(34, 24, 38, 24)
arrow(55, 24, 59, 24)
arrow(74, 24, 78, 24)

# Supporting row
box(19, 5.5, 15, 7, "State\nresumable progress", "#1F2937", fs=8.5)
box(59, 5.5, 15, 7, "Backups\nrollback", "#1F2937", fs=8.5)

arrow(26.5, 20, 26.5, 12.5, dashed=True)
arrow(66.5, 20, 66.5, 12.5, dashed=True)

# Footer caption
ax.text(50, 1.6,
        "Deterministic rewrite detection  ·  SEO-safe posting  ·  rollback  ·  retries",
        ha="center", va="center", fontsize=9, color=MUTED)

plt.savefig("docs/architecture.png", dpi=150, bbox_inches="tight",
            facecolor=BG)
print("saved: docs/architecture.png")
