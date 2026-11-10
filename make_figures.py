"""
Reproduce Figures 1-3 of:
"Recommended again: An audit of safety recommendations in Nepal's published
aircraft accident investigation reports, 2012-2025"

Input : Supplementary_Data_S1.xlsx (sheets 'Recommendations' and 'Chain_members')
Output: Figure_1/2/3 as .png (300 dpi) and .pdf (vector) in the output folder

Usage : python make_figures.py [path/to/Supplementary_Data_S1.xlsx] [output_folder]
Needs : pandas, numpy, matplotlib, openpyxl
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

XLSX = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Supplementary_Data_S1.xlsx")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
OUT.mkdir(parents=True, exist_ok=True)

# ---------- style: journal asks for Times New Roman, 5-8 pt, lines 0.3-2 pt ----------
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
    "font.size": 8,
    "pdf.fonttype": 42,              # embed TrueType so text stays editable
    "axes.edgecolor": "#8a8985", "axes.linewidth": 0.6,
    "xtick.color": "#52514e", "ytick.color": "#52514e",
    "axes.labelcolor": "#0b0b0b", "text.color": "#0b0b0b",
})
BLUE, ORANGE, AQUA, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#b5b3ad"
INK2 = "#52514e"
FULL_WIDTH_IN = 7.48                 # full page width at 300 dpi = 2244 px


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=300)
    fig.savefig(OUT / f"{name}.pdf")
    plt.close(fig)


# ---------- data (tables start on row 5 of each sheet; row 4 holds the headers) ----------
rec = pd.read_excel(XLSX, sheet_name="Recommendations", header=3)
rec["Accident date"] = pd.to_datetime(rec["Accident date"])
members = pd.read_excel(XLSX, sheet_name="Chain_members", header=3)
members["Accident date"] = pd.to_datetime(members["Accident date"])

# =====================================================================
# Figure 1 - recommendations per report, stacked by addressee level
# =====================================================================
levels = ["State", "Regulator", "Operators", "Other bodies"]
labels = {"State": "Ministry / Government", "Regulator": "Regulator (CAAN)",
          "Operators": "Operators (named or all)", "Other bodies": "Other bodies"}
colours = {"State": BLUE, "Regulator": ORANGE, "Operators": AQUA, "Other bodies": GREY}

order = rec.groupby("Report ID")["Accident date"].min().sort_values()
ct = (pd.crosstab(rec["Report ID"], rec["Addressee level"])
        .reindex(order.index).reindex(columns=levels, fill_value=0))

fig, ax = plt.subplots(figsize=(FULL_WIDTH_IN, 3.6))
x = np.arange(len(ct))
bottom = np.zeros(len(ct))
for lv in levels:
    ax.bar(x, ct[lv], bottom=bottom, color=colours[lv], width=0.72,
           edgecolor="white", linewidth=1.0, label=labels[lv])
    bottom += ct[lv].values
for i, total in enumerate(bottom):
    ax.text(i, total + 0.8, int(total), ha="center", va="bottom", fontsize=7, color=INK2)
ax.set_xticks(x)
ax.set_xticklabels([f"{r}\n{d.year}" for r, d in order.items()], fontsize=6.3)
ax.set_ylabel("Safety recommendations (n)")
ax.set_ylim(0, 55)
ax.spines[["top", "right"]].set_visible(False)
ax.yaxis.grid(True, color="#e6e5e1", linewidth=0.5)
ax.set_axisbelow(True)
ax.legend(frameon=False, ncol=4, loc="upper left", fontsize=7, handlelength=1.2)
fig.tight_layout()
save(fig, "Figure_1")

# =====================================================================
# Figure 2 - directive force and type of action, by period
# (the 49-recommendation 9N-AME report is shown on its own)
# =====================================================================
def group(r):
    if r["Report ID"] == "9N-AME":
        return "9N-AME\n(2024)"
    return {"2012–16": "2012–16\n(7 reports)",
            "2017–19": "2017–19\n(6 reports)",
            "2022–25": "2022–25 excl.\n9N-AME (4)"}[r["Period"]]

rec["grp"] = rec.apply(group, axis=1)
G = ["2012–16\n(7 reports)", "2017–19\n(6 reports)", "2022–25 excl.\n9N-AME (4)", "9N-AME\n(2024)"]
n = rec["grp"].value_counts().reindex(G)

fig, axs = plt.subplots(1, 2, figsize=(FULL_WIDTH_IN, 3.1), gridspec_kw={"wspace": 0.12})

def stacked(ax, col, cats, cols, labs, title, dark):
    p = pd.crosstab(rec["grp"], rec[col], normalize="index").reindex(G)[cats] * 100
    left = np.zeros(len(G))
    for c in cats:
        ax.barh(range(len(G)), p[c], left=left, color=cols[c], edgecolor="white",
                linewidth=1, height=0.66, label=labs[c])
        for i, (l, v) in enumerate(zip(left, p[c])):
            if v >= 9:
                ax.text(l + v / 2, i, f"{v:.0f}%", ha="center", va="center", fontsize=6.5,
                        color="white" if c in dark else "#0b0b0b")
        left += p[c].values
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("% of recommendations")
    ax.set_title(title, loc="left", fontsize=8, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)

stacked(axs[0], "Directive force", ["Weak", "Advisory", "Mandatory"],
        {"Weak": "#bcd3f2", "Advisory": "#5f9ae3", "Mandatory": "#1d4f91"},
        {"Weak": "Weak", "Advisory": "Advisory (should)", "Mandatory": "Mandatory (shall/must)"},
        "a  Directive force", dark={"Advisory", "Mandatory"})
axs[0].set_yticks(range(len(G)))
axs[0].set_yticklabels([f"{g}  n={n[g]}" for g in G], fontsize=6.6)
axs[0].legend(frameon=False, fontsize=6.3, loc="upper center", bbox_to_anchor=(0.45, -0.24), ncol=3, handlelength=1)

stacked(axs[1], "Type of action", ["Discrete action", "General aim"],
        {"Discrete action": "#1d4f91", "General aim": "#bcd3f2"},
        {"Discrete action": "Discrete, checkable action", "General aim": "General aim"},
        "b  Type of action requested", dark={"Discrete action"})
axs[1].set_yticks(range(len(G)))
axs[1].set_yticklabels([])
axs[1].legend(frameon=False, fontsize=6.3, loc="upper center", bbox_to_anchor=(0.5, -0.24), ncol=2, handlelength=1)

fig.subplots_adjust(left=0.17, right=0.98, bottom=0.3, top=0.9)
save(fig, "Figure_2")

# =====================================================================
# Figure 3 - recurrence chains on a timeline, strict vs broad reissues
# =====================================================================
LIGHT = "#9dc0ec"
chains = []
for (cid, label), grp in members.groupby(["Chain", "Safety problem"]):
    d = (grp.groupby("Report ID")
            .agg(date=("Accident date", "min"), n=("Rec ID", "size"),
                 first=("Status in chain", lambda s: (s == "First issue").any()),
                 strict=("Status in chain", lambda s: (s == "Strict reissue").any()))
            .sort_values("date"))
    chains.append((cid, label, d))
chains.sort(key=lambda c: (c[2]["date"].min(), c[0]))   # earliest first issue at top

fig, ax = plt.subplots(figsize=(FULL_WIDTH_IN, 4.9))
for row, (cid, label, d) in enumerate(chains[::-1]):
    ax.plot(d["date"], [row] * len(d), color="#c9c7c1", linewidth=1.2, zorder=1)
    for _, r in d.iterrows():
        if r["first"]:
            fc, ec = "white", BLUE          # open = first issue
        elif r["strict"]:
            fc, ec = BLUE, BLUE             # dark = same remedy requested again
        else:
            fc, ec = LIGHT, LIGHT           # light = same problem, different remedy
        ax.scatter(r["date"], row, s=22 + 14 * r["n"], facecolor=fc, edgecolor=ec,
                   linewidth=1.3, zorder=3)
    span = (d["date"].max() - d["date"].min()).days / 365.25
    ax.text(pd.Timestamp("2026-04-01"), row, f"{len(d)} reports · {span:.1f} y",
            va="center", fontsize=6.5, color=INK2)
ax.set_yticks(range(len(chains)))
ax.set_yticklabels([f"{c[0]}  {c[1]}" for c in chains[::-1]], fontsize=6.6)
ax.set_xlim(pd.Timestamp("2012-03-01"), pd.Timestamp("2028-06-01"))
ticks = [pd.Timestamp(f"{y}-01-01") for y in range(2012, 2027, 2)]
ax.set_xticks(ticks)
ax.set_xticklabels([t.year for t in ticks])
ax.set_xlabel("Accident date of the report in which the recommendation was issued")
ax.spines[["top", "right", "left"]].set_visible(False)
ax.tick_params(axis="y", length=0)
ax.xaxis.grid(True, color="#eeede9", linewidth=0.5)
ax.set_axisbelow(True)
handles = [
    Line2D([], [], marker="o", linestyle="", markerfacecolor="white", markeredgecolor=BLUE, markersize=6, label="First issue"),
    Line2D([], [], marker="o", linestyle="", markerfacecolor=BLUE, markeredgecolor=BLUE, markersize=6, label="Same remedy again (strict)"),
    Line2D([], [], marker="o", linestyle="", markerfacecolor=LIGHT, markeredgecolor=LIGHT, markersize=6, label="Same problem, other remedy (broad only)"),
    Line2D([], [], marker="o", linestyle="", markerfacecolor="#d9d8d3", markeredgecolor="#d9d8d3", markersize=8, label="Size = recommendations"),
]
ax.legend(handles=handles, frameon=False, loc="upper center", bbox_to_anchor=(0.40, 1.085), ncol=4, fontsize=6.6, handletextpad=0.3, columnspacing=1.0)
fig.tight_layout()
save(fig, "Figure_3")
print(f"Saved Figure_1-3 (.png, .pdf) to {OUT.resolve()}")
