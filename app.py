"""
BF Digital Twin — Blast Furnace Process Simulation Dashboard
=============================================================
A SCADA/HMI-inspired Streamlit dashboard for simulating and visualizing
blast furnace ironmaking process parameters, built for presentation to
senior engineers and R&D teams at an integrated steel plant.

Author: Generated for metallurgical process visualization
Tech stack: Streamlit + Plotly + NumPy + Pandas
"""

import io
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ==============================================================================
# 1. PAGE CONFIGURATION
# ==============================================================================
st.set_page_config(
    layout="wide",
    page_title="BF Digital Twin",
    page_icon="🏭",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------------------
# Color palette — used consistently across CSS + Plotly charts
# ------------------------------------------------------------------------------
COLORS = {
    "bg": "#0e1420",
    "panel": "#161d2b",
    "border": "#2a3547",
    "accent": "#00d4ff",       # cyan — primary HMI accent
    "accent2": "#ff9f1c",      # amber — warning / heat accent
    "good": "#2ee6a6",         # green — nominal status
    "warn": "#ffb703",         # amber — caution
    "bad": "#ff4d6d",          # red — alarm
    "text": "#e8edf5",
    "subtext": "#8a94a6",
    "coke": "#5b6b8c",
    "pci": "#00d4ff",
}

PLOTLY_TEMPLATE = "plotly_dark"


# ==============================================================================
# 2. CUSTOM CSS — Industrial SCADA/HMI styling
# ==============================================================================
def inject_custom_css() -> None:
    """Inject custom CSS to give the dashboard an industrial monitor look."""
    st.markdown(
        f"""
        <style>
        /* Overall app background */
        .stApp {{
            background: radial-gradient(circle at top left, #101826 0%, {COLORS['bg']} 60%);
        }}

        /* Metric cards styled as industrial monitor tiles */
        div[data-testid="stMetric"] {{
            background: linear-gradient(145deg, {COLORS['panel']}, #121826);
            border: 1px solid {COLORS['border']};
            border-radius: 12px;
            padding: 14px 18px 10px 18px;
            box-shadow: 0 0 0 1px rgba(0,212,255,0.03), 0 4px 14px rgba(0,0,0,0.35);
        }}
        div[data-testid="stMetric"]:hover {{
            border: 1px solid {COLORS['accent']};
            transition: 0.2s ease-in-out;
        }}
        div[data-testid="stMetricLabel"] {{
            color: {COLORS['subtext']} !important;
            font-size: 0.78rem !important;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }}
        div[data-testid="stMetricValue"] {{
            color: {COLORS['accent']} !important;
            font-weight: 700 !important;
        }}

        /* Section headers */
        h1, h2, h3 {{
            color: {COLORS['text']};
            font-family: 'Segoe UI', 'Inter', sans-serif;
        }}
        h1 {{
            border-bottom: 1px solid {COLORS['border']};
            padding-bottom: 10px;
        }}

        /* Sidebar */
        section[data-testid="stSidebar"] {{
            background-color: {COLORS['panel']};
            border-right: 1px solid {COLORS['border']};
        }}

        /* Tabs */
        button[data-baseweb="tab"] {{
            font-size: 0.95rem;
            color: {COLORS['subtext']};
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            color: {COLORS['accent']} !important;
        }}

        /* Dividers */
        hr {{
            border-color: {COLORS['border']} !important;
        }}

        /* Status pill badges */
        .status-pill {{
            display: inline-block;
            padding: 4px 14px;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 600;
            letter-spacing: 0.03em;
        }}
        .status-good {{ background: rgba(46,230,166,0.12); color: {COLORS['good']}; border: 1px solid {COLORS['good']}; }}
        .status-warn {{ background: rgba(255,183,3,0.12); color: {COLORS['warn']}; border: 1px solid {COLORS['warn']}; }}
        .status-bad  {{ background: rgba(255,77,109,0.12); color: {COLORS['bad']};  border: 1px solid {COLORS['bad']};  }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ==============================================================================
# 3. CORE PROCESS CALCULATIONS
# ==============================================================================
# NOTE ON METALLURGICAL REASONING:
# These are simplified, heuristic engineering-style relationships intended for
# visualization / training purposes — NOT a replacement for validated furnace
# process models (e.g. Rist diagram, heat/mass balance solvers). They are
# tuned to reproduce qualitatively correct trends seen in blast furnace
# operating practice.

def calc_total_fuel_rate(coke_rate: float, pci_rate: float) -> float:
    """Total reducing-agent rate (kg/tHM). Coke + PCI is the standard
    'fuel rate' KPI used to benchmark furnace efficiency."""
    return coke_rate + pci_rate


def calc_hot_metal_production(working_volume: float, productivity: float) -> float:
    """Hot metal production (t/day) = furnace working volume (m3) x
    productivity index (tHM per m3 of working volume per day). This is the
    standard BF productivity KPI used across ironmaking plants."""
    return working_volume * productivity


def calc_raft(hot_blast_temp: float, blast_moisture: float, pci_rate: float) -> float:
    """
    Raceway Adiabatic Flame Temperature (RAFT), simplified heuristic (°C).

    Metallurgical reasoning:
    - RAFT rises with hot blast temperature (sensible heat carried into the
      raceway raises flame temperature almost 1:1 in simplified models).
    - RAFT falls with blast moisture, since H2O decomposition in the raceway
      (H2O -> H2 + 1/2 O2) is endothermic and consumes carbon (moisture
      decomposition reaction), cooling the raceway.
    - RAFT falls with PCI rate, because injected coal must be devolatilized
      and gasified in the raceway (endothermic), and because higher PCI
      lowers the effective coke/blast ratio entering the raceway. Very high
      PCI without oxygen enrichment is a classic cause of "cold raceway".

    Baseline ~2050°C at a reference condition; deltas built from typical
    plant sensitivities (~+90°C RAFT per 100°C hot blast temp increase,
    ~-9°C per g/Nm3 moisture, ~-1.1°C per kg/tHM PCI).
    """
    baseline = 2180.0
    delta_hbt = (hot_blast_temp - 1000.0) * 0.9      # °C per °C hot blast temp
    delta_moist = -(blast_moisture - 10.0) * 9.0      # °C per g/Nm3 moisture
    delta_pci = -(pci_rate - 100.0) * 1.1              # °C per kg/tHM PCI
    return baseline + delta_hbt + delta_moist + delta_pci


def calc_co2_emission(coke_rate: float, pci_rate: float) -> float:
    """
    CO2 emission estimate (kg CO2/tHM), simplified heuristic.

    Metallurgical reasoning: Both coke and PCI carbon are oxidized (directly
    or via CO -> CO2 in downstream reduction/combustion), so total CO2 scales
    roughly with total carbon input. Coke carbon content (~87%) is higher
    than typical injectant coal carbon content (~75-80%), so a slightly
    higher emission factor is applied to coke on a per-kg basis.
    """
    coke_co2_factor = 3.05   # kg CO2 per kg coke carbon oxidized (~87% C, full oxidation to CO2)
    pci_co2_factor = 2.65    # kg CO2 per kg PCI coal (lower C%, partial volatile losses)
    return coke_rate * coke_co2_factor + pci_rate * pci_co2_factor


def calc_kpis(coke_rate, pci_rate, hbt, burden_ratio, moisture, volume, productivity) -> dict:
    """Bundle all derived KPIs into a single dictionary for reuse across the UI."""
    fuel_rate = calc_total_fuel_rate(coke_rate, pci_rate)
    production = calc_hot_metal_production(volume, productivity)
    raft = calc_raft(hbt, moisture, pci_rate)
    co2 = calc_co2_emission(coke_rate, pci_rate)
    return {
        "fuel_rate": fuel_rate,
        "production": production,
        "raft": raft,
        "co2": co2,
        "coke_rate": coke_rate,
        "pci_rate": pci_rate,
        "hbt": hbt,
        "burden_ratio": burden_ratio,
        "moisture": moisture,
        "volume": volume,
        "productivity": productivity,
    }


# ------------------------------------------------------------------------------
# Alarm thresholds (typical industrial practice)
# ------------------------------------------------------------------------------
RAFT_CRITICAL_LOW = 2100.0     # °C — below this, raceway risks becoming "cold" / unstable
RAFT_WARN_LOW = 2180.0         # °C — early caution band
FUEL_RATE_ECONOMIC_LIMIT = 560.0  # kg/tHM — typical high-efficiency furnace target ceiling


def evaluate_alarms(kpis: dict) -> list:
    """Return a list of (level, message) tuples for triggered alarms."""
    alarms = []
    if kpis["raft"] < RAFT_CRITICAL_LOW:
        alarms.append(("error", f"RAFT critically low ({kpis['raft']:.0f}°C) — raceway instability risk. "
                                 f"Reduce moisture/PCI or raise hot blast temperature."))
    elif kpis["raft"] < RAFT_WARN_LOW:
        alarms.append(("warning", f"RAFT approaching lower limit ({kpis['raft']:.0f}°C) — monitor raceway conditions."))

    if kpis["fuel_rate"] > FUEL_RATE_ECONOMIC_LIMIT:
        alarms.append(("warning", f"Fuel rate ({kpis['fuel_rate']:.0f} kg/tHM) exceeds economic benchmark "
                                   f"({FUEL_RATE_ECONOMIC_LIMIT:.0f} kg/tHM)."))
    return alarms


# ==============================================================================
# 4. GEOMETRIC COORDINATE MATH — Tall, slender textbook-style BF profile
# ==============================================================================
def generate_furnace_profile(height: float = 100.0) -> tuple:
    """
    Generate a tall, slender, textbook-accurate BF inner-profile half-width
    curve, from throat (top) to hearth (bottom):

        Throat -> Stack (long, gently tapering cone) -> Belly (max width) ->
        Bosh (sharply tapering cone toward tuyeres) -> Hearth (cylindrical)

    Returns (y, half_width) arrays for the RIGHT profile; caller mirrors for
    the left side to build a closed polygon.
    """
    # Relative zone heights (fractions of total height), top to bottom.
    # Stack dominates (>=55%) and tapers very gradually; bosh is short and steep.
    z_throat = 0.05
    z_stack = 0.57
    z_belly = 0.06
    z_bosh = 0.17
    z_hearth = 0.15
    assert abs(z_throat + z_stack + z_belly + z_bosh + z_hearth - 1.0) < 1e-6

    # Relative half-widths (all ~50% narrower than before -> tall/slender silhouette)
    w_throat_top = 0.17
    w_throat_bot = 0.19
    w_stack_bot = 0.31     # very gradual stack flare over a long run
    w_belly = 0.34         # belly = maximum furnace diameter
    w_bosh_bot = 0.19       # sharp inward taper toward the tuyeres
    w_hearth = 0.23

    def ease(t):
        """Cosine easing for smooth (C1-continuous-looking) transitions."""
        return 0.5 - 0.5 * np.cos(np.pi * t)

    n_per_zone = 60
    y_vals, w_vals = [], []
    y_cursor = height  # start at top, integrate downward

    zones = [
        (z_throat, w_throat_top, w_throat_bot),
        (z_stack, w_throat_bot, w_stack_bot),
        (z_belly, w_stack_bot, w_belly),
        (z_bosh, w_belly, w_bosh_bot),
        (z_hearth, w_bosh_bot, w_hearth),
    ]

    for frac_h, w_start, w_end in zones:
        zone_height = frac_h * height
        t = np.linspace(0, 1, n_per_zone)
        y_zone = y_cursor - t * zone_height
        w_zone = w_start + (w_end - w_start) * ease(t)
        y_vals.append(y_zone)
        w_vals.append(w_zone)
        y_cursor -= zone_height

    y = np.concatenate(y_vals)
    w = np.concatenate(w_vals) * (height / 2.0)  # scale half-width relative to height
    return y, w


def build_furnace_polygon(height: float = 100.0):
    """Mirror the right-side profile to build the full closed furnace outline."""
    y, w = generate_furnace_profile(height)
    x_right = w
    x_left = -w
    x_poly = np.concatenate([x_right, x_left[::-1]])
    y_poly = np.concatenate([y, y[::-1]])
    return x_poly, y_poly, y, w


# ==============================================================================
# 4b. NEW ANATOMICAL DRAWING HELPERS
# ==============================================================================
def build_charging_equipment(y_profile: np.ndarray, w_profile: np.ndarray, height: float) -> list:
    """Draw the top-charging hopper and rotating distribution chute above the throat."""
    traces = []
    w_throat = width_at(y_profile, w_profile, height)

    hop_bottom = height + 1.5
    hop_top = height + 15
    hw_top = w_throat * 1.7
    hw_bottom = w_throat * 0.85

    # Charging hopper (bell-less top style, trapezoid narrowing downward)
    hopper_x = [-hw_top, hw_top, hw_bottom, -hw_bottom, -hw_top]
    hopper_y = [hop_top, hop_top, hop_bottom, hop_bottom, hop_top]
    traces.append(go.Scatter(
        x=hopper_x, y=hopper_y, fill="toself",
        fillcolor="rgba(95,105,125,0.85)",
        line=dict(color=COLORS["border"], width=2),
        mode="lines", hoverinfo="text", text="Charging Hopper", showlegend=False,
    ))

    # Rotating distribution chute — angled boom swinging from center down into the throat
    chute_x = [0, w_throat * 0.75]
    chute_y = [hop_bottom, height - 2]
    traces.append(go.Scatter(
        x=chute_x, y=chute_y, mode="lines+markers",
        line=dict(color=COLORS["accent2"], width=5),
        marker=dict(size=[0, 7], color=COLORS["accent2"]),
        hoverinfo="text", text="Rotating Distribution Chute", showlegend=False,
    ))
    # small pivot hub
    traces.append(go.Scatter(
        x=[0], y=[hop_bottom], mode="markers",
        marker=dict(size=10, color="rgba(200,210,225,0.9)", line=dict(color=COLORS["border"], width=1)),
        hoverinfo="skip", showlegend=False,
    ))
    return traces


def build_burden_layers(y_profile: np.ndarray, w_profile: np.ndarray,
                         y_top: float, y_bottom: float, n_bands: int = 9) -> list:
    """
    Generate alternating V-shaped burden bands (iron ore / coke) stacked
    through the throat and stack, mimicking layers piling from the rotating
    chute. Each band's top/bottom edges dip toward the furnace centerline,
    giving the characteristic chevron ("V") cross-section seen in charging
    diagrams, then mirrors to a slight peak-toward-wall pattern to alternate
    visual rhythm between bands.
    """
    traces = []
    band_edges = np.linspace(y_top, y_bottom, n_bands + 1)
    ore_color = "rgba(150,110,70,0.55)"     # iron ore / sinter — brownish
    coke_color = "rgba(75,82,98,0.60)"      # coke — dark blue-grey

    for i in range(n_bands):
        y_hi, y_lo = band_edges[i], band_edges[i + 1]
        y_mid = (y_hi + y_lo) / 2.0
        w_mid = width_at(y_profile, w_profile, y_mid) * 0.96  # inset slightly from the wall
        if w_mid <= 0:
            continue

        xs = np.linspace(-w_mid, w_mid, 36)
        band_thickness = y_hi - y_lo
        v_depth = band_thickness * 0.4
        # V-shape: layer dips toward the centerline (material sliding off the chute apex)
        dip = v_depth * (np.abs(xs) / w_mid)
        y_top_curve = (y_hi - v_depth) + dip
        y_bot_curve = (y_lo - v_depth) + dip

        poly_x = np.concatenate([xs, xs[::-1]])
        poly_y = np.concatenate([y_top_curve, y_bot_curve[::-1]])
        color = ore_color if i % 2 == 0 else coke_color
        label = "Iron Ore / Sinter Layer" if i % 2 == 0 else "Coke Layer"
        traces.append(go.Scatter(
            x=poly_x, y=poly_y, fill="toself", fillcolor=color,
            line=dict(color="rgba(255,255,255,0.10)", width=0.5),
            mode="lines", hoverinfo="text", text=label, showlegend=False,
        ))
    return traces


def build_cohesive_zone(y_profile: np.ndarray, w_profile: np.ndarray,
                         center_y: float, half_thick: float, width_frac: float = 0.9) -> go.Scatter:
    """
    Draw a jagged, layered inverted-V (mountain-peak-upward) softening-melting
    zone spanning the belly / lower stack.
    """
    w_center = width_at(y_profile, w_profile, center_y) * width_frac
    n = 16
    xs = np.linspace(-w_center, w_center, n)

    # Jagged perturbation for a layered/irregular melting-zone edge
    jag = half_thick * 0.18 * np.array([1 if i % 2 == 0 else -1 for i in range(n)])

    # Top edge peaks at the centerline (inverted-V / mountain shape), tapering to walls
    top_y = center_y + half_thick * (1 - (np.abs(xs) / w_center) ** 1.3) + jag
    # Bottom edge is shallower, roughly parallel, giving the band thickness
    bot_y = center_y - half_thick * 0.55 - (np.abs(xs) / w_center) * half_thick * 0.35

    poly_x = np.concatenate([xs, xs[::-1]])
    poly_y = np.concatenate([top_y, bot_y[::-1]])

    return go.Scatter(
        x=poly_x, y=poly_y, fill="toself",
        fillcolor="rgba(255,90,40,0.55)",
        line=dict(color="rgba(255,150,70,0.9)", width=2),
        mode="lines", hoverinfo="text",
        text="Cohesive Zone (Softening-Melting)", showlegend=False,
    )


def build_tuyeres_and_bustle(y_profile: np.ndarray, w_profile: np.ndarray,
                              tuyere_y: float, raceway_color: str) -> list:
    """Draw the bustle pipe (hot blast main) on both sides with tuyere pipes
    feeding into the furnace wall at the bosh/hearth boundary."""
    traces = []
    w_wall = width_at(y_profile, w_profile, tuyere_y)
    bustle_r = 6.0

    for sign in (-1, 1):
        cx = sign * (w_wall + bustle_r + 5)
        cy = tuyere_y
        theta = np.linspace(0, 2 * np.pi, 32)
        circ_x = cx + bustle_r * np.cos(theta)
        circ_y = cy + bustle_r * 0.65 * np.sin(theta)

        # Bustle pipe ring
        traces.append(go.Scatter(
            x=circ_x, y=circ_y, fill="toself", fillcolor="rgba(85,95,115,0.75)",
            line=dict(color=COLORS["border"], width=2), mode="lines",
            hoverinfo="text", text="Bustle Pipe (Hot Blast Main)", showlegend=False,
        ))

        # Tuyere pipe connecting bustle to the furnace wall — colored by RAFT
        traces.append(go.Scatter(
            x=[cx - sign * bustle_r, sign * w_wall * 0.97], y=[cy, cy],
            mode="lines", line=dict(color=raceway_color, width=9),
            hoverinfo="text", text="Tuyere / Raceway", showlegend=False,
        ))
        # small tuyere nozzle tip
        traces.append(go.Scatter(
            x=[sign * w_wall * 0.97], y=[cy], mode="markers",
            marker=dict(size=8, color=raceway_color, line=dict(color=COLORS["border"], width=1)),
            hoverinfo="skip", showlegend=False,
        ))
    return traces


def build_hearth_taphole(y_profile: np.ndarray, w_profile: np.ndarray) -> list:
    """Draw the taphole/spout on the bottom-right of the hearth with a molten
    iron flow stream dropping away from the furnace wall."""
    traces = []
    hearth_bottom = y_profile.min()
    hearth_span = (y_profile.max() - hearth_bottom)
    taphole_y = hearth_bottom + 0.12 * hearth_span
    w_wall = width_at(y_profile, w_profile, taphole_y)

    # Spout / taphole runner extending outward from the wall
    spout_x = [w_wall, w_wall + 11, w_wall + 11, w_wall]
    spout_y = [taphole_y + 1.6, taphole_y + 3.2, taphole_y - 1.0, taphole_y - 1.8]
    traces.append(go.Scatter(
        x=spout_x, y=spout_y, fill="toself", fillcolor="rgba(120,124,132,0.85)",
        line=dict(color=COLORS["border"], width=1.5), mode="lines",
        hoverinfo="text", text="Taphole / Iron Runner", showlegend=False,
    ))

    # Molten hot metal flow, dropping away from the runner
    flow_x = [w_wall + 10, w_wall + 14, w_wall + 12, w_wall + 8]
    flow_y = [taphole_y - 1.0, taphole_y - 1.0, taphole_y - 10, taphole_y - 10]
    traces.append(go.Scatter(
        x=flow_x, y=flow_y, fill="toself", fillcolor="rgba(255,110,30,0.85)",
        line=dict(width=0), mode="lines",
        hoverinfo="text", text="Molten Hot Metal Flow", showlegend=False,
    ))
    return traces


def build_gas_flow_arrows(height: float) -> tuple:
    """Curved light-grey scatter lines tracing ascending reducing gas paths
    through the furnace center; returns (traces, top_points) so callers can
    add arrowhead annotations at the top of each line."""
    traces = []
    top_points = []
    x_offsets = [-height * 0.10, 0.0, height * 0.10]

    for xo in x_offsets:
        y_line = np.linspace(height * 0.06, height * 0.94, 24)
        x_line = xo + np.sin(y_line / height * np.pi * 1.4) * height * 0.025
        traces.append(go.Scatter(
            x=x_line, y=y_line, mode="lines",
            line=dict(color="rgba(225,235,250,0.55)", width=1.6, dash="dot"),
            hoverinfo="skip", showlegend=False,
        ))
        top_points.append((x_line[-1], y_line[-1], x_line[-3], y_line[-3]))
    return traces, top_points
# ==============================================================================
# 5. DYNAMIC SCHEMATIC — Plotly cross-section figure
# ==============================================================================
def raft_to_color(raft: float) -> str:
    """Map RAFT (°C) to a raceway glow color: dull orange (cold) -> white-blue (hot)."""
    t = np.clip((raft - 1900) / (2400 - 1900), 0.0, 1.0)  # normalize 1900-2400°C
    # Interpolate from dull orange (#7a3b1e) to glowing white-blue (#e8f6ff)
    c_cold = np.array([122, 59, 30])
    c_hot = np.array([232, 246, 255])
    c = (c_cold + (c_hot - c_cold) * t).astype(int)
    return f"rgb({c[0]},{c[1]},{c[2]})"


def build_furnace_schematic(kpis: dict) -> go.Figure:
    """
    Construct the anatomically detailed 2D blast furnace cross-section,
    dynamically synced to sidebar inputs:
      - Raceway/tuyere glow color <- RAFT
      - Cohesive zone vertical position <- burden ratio & fuel rate
      - Hearth liquid level <- productivity
    """
    height = 100.0
    x_poly, y_poly, y_profile, w_profile = build_furnace_polygon(height)

    fig = go.Figure()

    # --- Furnace shell outline (structural steel body) ---
    fig.add_trace(go.Scatter(
        x=x_poly, y=y_poly, fill="toself",
        fillcolor="rgba(45,52,68,0.35)",
        line=dict(color=COLORS["border"], width=2.5),
        mode="lines", hoverinfo="skip", showlegend=False,
    ))

    # --- Top charging equipment: hopper + rotating chute ---
    for tr in build_charging_equipment(y_profile, w_profile, height):
        fig.add_trace(tr)

    # --- Alternating burden layers (ore/coke V-bands) through throat + stack ---
    burden_top = height * 0.97
    burden_bottom = height * 0.42  # stops above the cohesive zone
    for tr in build_burden_layers(y_profile, w_profile, burden_top, burden_bottom, n_bands=9):
        fig.add_trace(tr)

    # --- Cohesive zone (jagged inverted-V), position synced to burden ratio & fuel rate ---
    base_center = height * 0.40
    shift = (kpis["burden_ratio"] - 3.75) * -3.5 + (450 - kpis["fuel_rate"]) * 0.018
    cz_center = np.clip(base_center + shift, height * 0.28, height * 0.46)
    cz_half_thick = height * 0.055
    fig.add_trace(build_cohesive_zone(y_profile, w_profile, cz_center, cz_half_thick))

    # --- Tuyeres & bustle pipe, glow color driven by RAFT ---
    raceway_color = raft_to_color(kpis["raft"])
    tuyere_y = height * 0.155  # bosh/hearth boundary
    for tr in build_tuyeres_and_bustle(y_profile, w_profile, tuyere_y, raceway_color):
        fig.add_trace(tr)

    # --- Hearth hot metal liquid level, scaled by productivity ---
    hearth_bottom = y_profile.min()
    hearth_zone_top = height * 0.11
    prod_frac = np.clip((kpis["productivity"] - 2.0) / (3.0 - 2.0), 0.15, 1.0)
    liquid_top = hearth_bottom + (hearth_zone_top - hearth_bottom) * prod_frac
    mask_h = y_profile <= hearth_zone_top
    yh, wh = y_profile[mask_h], w_profile[mask_h]
    liquid_mask = yh <= liquid_top
    if liquid_mask.any():
        xh_poly = np.concatenate([wh[liquid_mask], -wh[liquid_mask][::-1]])
        yh_poly = np.concatenate([yh[liquid_mask], yh[liquid_mask][::-1]])
        fig.add_trace(go.Scatter(
            x=xh_poly, y=yh_poly, fill="toself",
            fillcolor="rgba(255,90,30,0.75)",
            line=dict(width=0), mode="lines",
            hoverinfo="text", text=f"Hot Metal Level — Productivity {kpis['productivity']:.2f} tHM/m³/day",
            showlegend=False,
        ))

    # --- Hearth & taphole with molten iron flow ---
    for tr in build_hearth_taphole(y_profile, w_profile):
        fig.add_trace(tr)

    # --- Ascending gas flow arrows through the furnace core ---
    gas_traces, gas_tops = build_gas_flow_arrows(height)
    for tr in gas_traces:
        fig.add_trace(tr)
    for (x1, y1, x0, y0) in gas_tops:
        fig.add_annotation(
            x=x1, y=y1, ax=x0, ay=y0,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1.6,
            arrowcolor="rgba(225,235,250,0.7)",
        )

    # --- Zone labels ---
    labels = [
        (height * 1.10, "Charging Hopper"),
        (height * 0.80, "Stack (Burden Layers)"),
        (height * 0.40, "Belly / Cohesive Zone"),
        (height * 0.22, "Bosh"),
        (height * 0.15, "Tuyeres"),
        (height * 0.05, "Hearth"),
    ]
    for y_lab, text in labels:
        fig.add_annotation(
            x=height * 0.75, y=y_lab, text=text, showarrow=False,
            font=dict(size=11, color=COLORS["subtext"]), xanchor="left",
        )

    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False, range=[-height * 0.75, height * 0.75], scaleanchor="y", scaleratio=1),
        yaxis=dict(visible=False, range=[y_profile.min() - 12, height * 1.20]),
        margin=dict(l=10, r=10, t=10, b=10),
        height=760,
        showlegend=False,
    )
    return fig

def width_at(y_profile: np.ndarray, w_profile: np.ndarray, y_target: float) -> float:
    """Linear interpolation helper to get furnace half-width at a given height."""
    order = np.argsort(y_profile)
    return float(np.interp(y_target, y_profile[order], w_profile[order]))


# ==============================================================================
# 6. ANALYTICS CHARTS — donut, gauge, benchmark bar, sensitivity
# ==============================================================================
def build_fuel_donut(kpis: dict) -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=["Coke", "PCI"],
        values=[kpis["coke_rate"], kpis["pci_rate"]],
        hole=0.62,
        marker=dict(colors=[COLORS["coke"], COLORS["pci"]], line=dict(color=COLORS["bg"], width=2)),
        textinfo="label+percent",
        textfont=dict(color=COLORS["text"]),
    ))
    fig.add_annotation(
        text=f"<b>{kpis['fuel_rate']:.0f}</b><br><span style='font-size:11px'>kg/tHM</span>",
        x=0.5, y=0.5, showarrow=False, font=dict(size=20, color=COLORS["accent"]),
    )
    fig.update_layout(
        template=PLOTLY_TEMPLATE, paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10), height=320,
    )
    return fig


def build_productivity_gauge(kpis: dict) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=kpis["productivity"],
        number={"suffix": " tHM/m³/day", "font": {"color": COLORS["accent"], "size": 26}},
        gauge={
            "axis": {"range": [2.0, 3.0], "tickcolor": COLORS["subtext"]},
            "bar": {"color": COLORS["accent"]},
            "bgcolor": COLORS["panel"],
            "borderwidth": 1,
            "bordercolor": COLORS["border"],
            "steps": [
                {"range": [2.0, 2.4], "color": "rgba(255,77,109,0.18)"},
                {"range": [2.4, 2.7], "color": "rgba(255,183,3,0.18)"},
                {"range": [2.7, 3.0], "color": "rgba(46,230,166,0.18)"},
            ],
        },
    ))
    fig.update_layout(
        template=PLOTLY_TEMPLATE, paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=30, b=10), height=320,
    )
    return fig


def build_emissions_bar(kpis: dict) -> go.Figure:
    """Compare current CO2 estimate against illustrative industry benchmarks."""
    categories = ["Best-in-Class", "Industry Average", "Regulatory Ceiling", "Current Furnace"]
    values = [1500, 1750, 2000, kpis["co2"]]
    colors = [COLORS["good"], COLORS["subtext"], COLORS["bad"],
              COLORS["accent"] if kpis["co2"] <= 1900 else COLORS["warn"]]
    fig = go.Figure(go.Bar(
        x=categories, y=values, marker_color=colors,
        text=[f"{v:.0f}" for v in values], textposition="outside",
    ))
    fig.update_layout(
        template=PLOTLY_TEMPLATE, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(title="kg CO₂ / tHM", gridcolor=COLORS["border"]),
        xaxis=dict(showgrid=False),
        margin=dict(l=10, r=10, t=20, b=10), height=380,
    )
    return fig


def build_raft_trend(coke_rate, hbt, burden_ratio, moisture, base_pci) -> go.Figure:
    """Show RAFT sensitivity across a PCI sweep, for What-If context."""
    pci_range = np.linspace(100, 250, 40)
    raft_vals = [calc_raft(hbt, moisture, p) for p in pci_range]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pci_range, y=raft_vals, mode="lines", line=dict(color=COLORS["accent"], width=3),
        fill="tozeroy", fillcolor="rgba(0,212,255,0.08)", name="RAFT",
    ))
    fig.add_hline(y=RAFT_CRITICAL_LOW, line_dash="dash", line_color=COLORS["bad"],
                  annotation_text="Critical limit", annotation_font_color=COLORS["bad"])
    fig.add_vline(x=base_pci, line_dash="dot", line_color=COLORS["text"],
                  annotation_text="Current PCI")
    fig.update_layout(
        template=PLOTLY_TEMPLATE, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="PCI Rate (kg/tHM)", gridcolor=COLORS["border"]),
        yaxis=dict(title="RAFT (°C)", gridcolor=COLORS["border"]),
        margin=dict(l=10, r=10, t=20, b=10), height=350,
    )
    return fig


# ==============================================================================
# 7. SIDEBAR — Input parameters
# ==============================================================================
def render_sidebar() -> dict:
    st.sidebar.markdown("## 🏭 BF Digital Twin")
    st.sidebar.caption("Process parameter control panel")
    st.sidebar.divider()

    with st.sidebar.expander("🔥 Thermal Inputs", expanded=True):
        hbt = st.slider("Hot Blast Temperature (°C)", 1000, 1300, 1200, step=10)
        moisture = st.slider("Blast Moisture (g/Nm³)", 10, 50, 20, step=1)

    with st.sidebar.expander("⛏️ Burden & Fuel Inputs", expanded=True):
        coke_rate = st.slider("Coke Rate (kg/tHM)", 300, 500, 380, step=5)
        pci_rate = st.slider("PCI Rate (kg/tHM)", 100, 250, 160, step=5)
        burden_ratio = st.slider("Burden Ratio (Ore/Coke)", 3.0, 4.5, 3.8, step=0.05)

    with st.sidebar.expander("⚙️ Furnace & Productivity", expanded=True):
        volume = st.number_input("Furnace Working Volume (m³)", value=4000, step=50)
        productivity = st.slider("Productivity (tHM/m³/day)", 2.0, 3.0, 2.5, step=0.01)

    st.sidebar.divider()
    st.sidebar.caption(f"Simulation timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return dict(
        coke_rate=coke_rate, pci_rate=pci_rate, hbt=hbt,
        burden_ratio=burden_ratio, moisture=moisture,
        volume=volume, productivity=productivity,
    )


# ==============================================================================
# 8. MAIN APPLICATION
# ==============================================================================
def render_header(kpis: dict, alarms: list) -> None:
    col_title, col_status = st.columns([3, 1])
    with col_title:
        st.title("🏭 Blast Furnace Digital Twin")
        st.caption("Real-time process simulation & KPI monitoring — Ironmaking Division")
    with col_status:
        if any(level == "error" for level, _ in alarms):
            st.markdown('<div class="status-pill status-bad">⚠ ALARM ACTIVE</div>', unsafe_allow_html=True)
        elif any(level == "warning" for level, _ in alarms):
            st.markdown('<div class="status-pill status-warn">◎ CAUTION</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-pill status-good">● NOMINAL</div>', unsafe_allow_html=True)


def render_kpi_row(kpis: dict) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Fuel Rate", f"{kpis['fuel_rate']:.0f} kg/tHM")
    c2.metric("Hot Metal Production", f"{kpis['production']:.0f} t/day")
    c3.metric("RAFT", f"{kpis['raft']:.0f} °C",
              delta=f"{kpis['raft'] - RAFT_WARN_LOW:.0f} vs. caution limit")
    c4.metric("CO₂ Emissions", f"{kpis['co2']:.0f} kg/tHM")


def render_alarms(alarms: list) -> None:
    for level, msg in alarms:
        if level == "error":
            st.error(f"🔴 {msg}")
        else:
            st.warning(f"🟡 {msg}")
    if not alarms:
        st.success("🟢 All process parameters within nominal operating range.")


def render_export(kpis: dict) -> None:
    df = pd.DataFrame([kpis])
    df.insert(0, "timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    st.download_button(
        label="⬇️ Export Simulation Data (CSV)",
        data=buf.getvalue(),
        file_name=f"bf_digital_twin_simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True,
    )


def render_whatif_tab(kpis: dict) -> None:
    st.subheader("What-If Simulation")
    st.caption("Adjust a parameter below to compare against the current baseline.")

    sim_param = st.selectbox("Parameter to vary", ["PCI Rate (kg/tHM)", "Coke Rate (kg/tHM)",
                                                     "Hot Blast Temperature (°C)"])
    if sim_param == "PCI Rate (kg/tHM)":
        sim_val = st.slider("Simulated PCI Rate", 100, 250, int(kpis["pci_rate"]) + 20, step=5)
        sim_kpis = calc_kpis(kpis["coke_rate"], sim_val, kpis["hbt"], kpis["burden_ratio"],
                              kpis["moisture"], kpis["volume"], kpis["productivity"])
    elif sim_param == "Coke Rate (kg/tHM)":
        sim_val = st.slider("Simulated Coke Rate", 300, 500, int(kpis["coke_rate"]) - 15, step=5)
        sim_kpis = calc_kpis(sim_val, kpis["pci_rate"], kpis["hbt"], kpis["burden_ratio"],
                              kpis["moisture"], kpis["volume"], kpis["productivity"])
    else:
        sim_val = st.slider("Simulated Hot Blast Temp", 1000, 1300, int(kpis["hbt"]) + 20, step=10)
        sim_kpis = calc_kpis(kpis["coke_rate"], kpis["pci_rate"], sim_val, kpis["burden_ratio"],
                              kpis["moisture"], kpis["volume"], kpis["productivity"])

    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Fuel Rate", f"{sim_kpis['fuel_rate']:.0f} kg/tHM",
              delta=f"{sim_kpis['fuel_rate'] - kpis['fuel_rate']:.0f}", delta_color="inverse")
    c2.metric("Production", f"{sim_kpis['production']:.0f} t/day",
              delta=f"{sim_kpis['production'] - kpis['production']:.0f}")
    c3.metric("CO₂ Emissions", f"{sim_kpis['co2']:.0f} kg/tHM",
              delta=f"{sim_kpis['co2'] - kpis['co2']:.0f}", delta_color="inverse")

    st.plotly_chart(build_raft_trend(kpis["coke_rate"], kpis["hbt"], kpis["burden_ratio"],
                                      kpis["moisture"], kpis["pci_rate"]),
                     use_container_width=True)


def main() -> None:
    inject_custom_css()

    inputs = render_sidebar()
    kpis = calc_kpis(**inputs)
    alarms = evaluate_alarms(kpis)

    render_header(kpis, alarms)
    render_kpi_row(kpis)
    st.divider()

    left_col, right_col = st.columns([1, 1.3])

    with left_col:
        st.subheader("Furnace Cross-Section — Live Schematic")
        st.plotly_chart(build_furnace_schematic(kpis), use_container_width=True)
        render_alarms(alarms)
        render_export(kpis)

    with right_col:
        tab1, tab2, tab3 = st.tabs(["📊 Live Overview", "🌫️ Emissions Tracking", "🧪 What-If Simulation"])

        with tab1:
            g1, g2 = st.columns(2)
            with g1:
                st.markdown("**Fuel Breakdown**")
                st.plotly_chart(build_fuel_donut(kpis), use_container_width=True)
            with g2:
                st.markdown("**Productivity**")
                st.plotly_chart(build_productivity_gauge(kpis), use_container_width=True)

        with tab2:
            st.markdown("**CO₂ Emissions vs. Industry Benchmarks**")
            st.plotly_chart(build_emissions_bar(kpis), use_container_width=True)

        with tab3:
            render_whatif_tab(kpis)


if __name__ == "__main__":
    main()
