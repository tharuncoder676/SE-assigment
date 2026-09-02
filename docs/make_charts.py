"""Render the performance charts in the report from the measured load-test data."""
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = pathlib.Path(__file__).parent / "figures"
OUT.mkdir(exist_ok=True)
DATA = json.loads((pathlib.Path(__file__).parent / "loadtest-results.json").read_text())

INK, GRID = "#12233a", "#dfe7ef"
BLUE, TEAL, AMBER, RED = "#0f6fc5", "#1a7f52", "#b4530a", "#b3261e"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9,
    "axes.edgecolor": "#9fb0c2", "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK, "ytick.color": INK, "axes.titleweight": "bold",
    "figure.dpi": 200,
})

ramp = [s for s in DATA["scenarios"] if s["scenario"] == "GET /api/v1/doctors"]
conc = [s["concurrency"] for s in ramp]


# --------------------------------------------------------------- figure 7
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.2, 3.3))

ax1.plot(conc, [s["throughput_rps"] for s in ramp], "o-", color=BLUE, lw=2, ms=6)
ax1.set_title("Throughput against concurrency")
ax1.set_xlabel("Concurrent virtual users")
ax1.set_ylabel("Requests per second")
ax1.grid(True, color=GRID, ls="--", lw=.7)
peak = max(ramp, key=lambda s: s["throughput_rps"])
ax1.annotate("saturation point\n%s rps at %d users" % (peak["throughput_rps"],
                                                       peak["concurrency"]),
             xy=(peak["concurrency"], peak["throughput_rps"]),
             xytext=(46, -34), textcoords="offset points", fontsize=8,
             arrowprops=dict(arrowstyle="->", color=AMBER, lw=1.2,
                             connectionstyle="arc3,rad=-0.25"), color=AMBER)

ax2.plot(conc, [s["p50_ms"] for s in ramp], "o-", color=TEAL, lw=2, ms=5, label="p50")
ax2.plot(conc, [s["p95_ms"] for s in ramp], "s-", color=AMBER, lw=2, ms=5, label="p95")
ax2.plot(conc, [s["p99_ms"] for s in ramp], "^-", color=RED, lw=2, ms=5, label="p99")
ax2.axhline(500, color="#7a8a9a", ls=":", lw=1.4)
ax2.text(2, 440, "NFR-1 budget: 500 ms", fontsize=8, color="#5f7186")
ax2.set_ylim(-20, 560)
ax2.set_title("Response-time percentiles")
ax2.set_xlabel("Concurrent virtual users")
ax2.set_ylabel("Latency (ms)")
ax2.legend(frameon=False, fontsize=8)
ax2.grid(True, color=GRID, ls="--", lw=.7)

fig.tight_layout()
fig.savefig(OUT / "fig7-performance.png", bbox_inches="tight")
plt.close(fig)


# --------------------------------------------------------------- figure 8
others = [s for s in DATA["scenarios"] if s["scenario"] != "GET /api/v1/doctors"]
sample = [ramp[3]] + others
labels = [s["scenario"].replace(" (", "\n(").replace("/api/v1", "") for s in sample]

fig, ax = plt.subplots(figsize=(9.2, 3.4))
y = range(len(sample))
ax.barh(list(y), [s["throughput_rps"] for s in sample], color=BLUE, height=.55)
for i, s in enumerate(sample):
    ax.text(s["throughput_rps"] + 12, i,
            "%s rps · p95 %s ms" % (s["throughput_rps"], s["p95_ms"]),
            va="center", fontsize=8, color=INK)
ax.set_yticks(list(y))
ax.set_yticklabels(labels, fontsize=8)
ax.invert_yaxis()
ax.set_xlabel("Requests per second (25 concurrent users unless noted)")
ax.set_title("Measured throughput by endpoint")
ax.set_xlim(0, max(s["throughput_rps"] for s in sample) * 1.32)
ax.grid(True, axis="x", color=GRID, ls="--", lw=.7)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(OUT / "fig8-endpoint-throughput.png", bbox_inches="tight")
plt.close(fig)


# --------------------------------------------------------------- figure 9
crypto = DATA["crypto"]
fig, ax = plt.subplots(figsize=(5.4, 3.0))
names = ["PBKDF2 hash\n(600k rounds)", "PBKDF2 verify\n(600k rounds)",
         "JWT sign\n(HS256)", "JWT verify\n(HS256)"]
values = [crypto["pbkdf2_hash_600k_ms"], crypto["pbkdf2_verify_600k_ms"],
          crypto["jwt_sign_ms"], crypto["jwt_verify_ms"]]
bars = ax.bar(names, values, color=[RED, RED, TEAL, TEAL], width=.6)
ax.set_yscale("log")
ax.set_ylabel("Time per operation (ms, log scale)")
ax.set_title("Cost of the security primitives")
for bar, value in zip(bars, values):
    ax.text(bar.get_x() + bar.get_width() / 2, value * 1.25,
            "%.3f ms" % value if value < 1 else "%.0f ms" % value,
            ha="center", fontsize=8)
ax.set_ylim(0.003, 1200)
ax.grid(True, axis="y", color=GRID, ls="--", lw=.7)
ax.set_axisbelow(True)
ax.tick_params(axis="x", labelsize=7.5)
fig.tight_layout()
fig.savefig(OUT / "fig9-crypto-cost.png", bbox_inches="tight")
plt.close(fig)

print("charts written to", OUT)
