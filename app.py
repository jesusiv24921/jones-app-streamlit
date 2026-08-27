"""JONES APP — Vp & Permeability stress correction (Jones equation).

Streamlit port of the original MATLAB App Designer app (jones_app_exported.m)
by Jesús Pacheco. Same inputs, same calibration formulas, same forward model.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Constants (hardcoded in the original MATLAB app for both Vp and Kk branches)
# ---------------------------------------------------------------------------
C = 3e-6
SIGMA0 = 3000.0
STRESS_GRID = np.arange(0, 4501, 100)  # 0..4500 psi, step 100 (46 points)

SERIES_MEASURED = "#2a78d6"   # categorical slot 1 (blue)
SERIES_MODEL = "#eb6834"      # categorical slot 2 (orange)

EMPTY_ROW = {
    "Depth (ft)": None,
    "Net Stress (psi)": None,
    "Vp (cc)": None,
    "Porosity (%)": None,
    "Kk (md)": None,
}

st.set_page_config(
    page_title="JONES APP",
    page_icon="🪨",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Jones equation
# ---------------------------------------------------------------------------


def compute_av(porosity_pct: float) -> float:
    return 0.0336 + 4.556 * ((porosity_pct / 100) - 0.25) ** 2


def compute_ak(kk: float) -> float:
    lnk = np.log(kk)
    return np.exp(-0.2 - lnk + 0.13 * lnk * np.sqrt(abs(lnk)))


def calibrate_single(value0, stress0, coef):
    x0 = value0 * (1 + C * stress0) * np.exp(coef * (1 - np.exp(-stress0 / SIGMA0)))
    return x0


def calibrate_two_stress(value1, stress1, value2, stress2):
    coef = np.log((value1 * (1 + C * stress1)) / (value2 * (1 + C * stress2))) / (
        np.exp(-stress1 / SIGMA0) - np.exp(-stress2 / SIGMA0)
    )
    x0 = value1 * (1 + C * stress1) * np.exp(coef * (1 - np.exp(-stress1 / SIGMA0)))
    return coef, x0


def forward_model(x0, coef, stress):
    return x0 * np.exp(coef * (np.exp(-stress / SIGMA0) - 1)) / (1 + C * stress)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "mode" not in st.session_state:
    st.session_state.mode = "Single Stress"
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame([EMPTY_ROW])
if "coefs" not in st.session_state:
    st.session_state.coefs = None  # dict once Calculate succeeds


def reset_all():
    st.session_state.data = pd.DataFrame(
        [EMPTY_ROW] * (1 if st.session_state.mode == "Single Stress" else 2)
    )
    st.session_state.coefs = None


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

col_logo, col_title = st.columns([1, 5], vertical_alignment="center")
with col_logo:
    st.markdown(
        "<div style='font-size:2.6rem;font-weight:800;line-height:1;'>"
        "<span style='color:#0b0b0b;'>J</span><span style='color:#eda100;'>P</span>"
        "</div>",
        unsafe_allow_html=True,
    )
with col_title:
    st.markdown("### APP TO DETERMINE VP AND PERMEABILITY WITH JONES EQUATION")
    st.caption("App designed by Jesús Pacheco · réplica en Streamlit de la app original en MATLAB")

tab_data, tab_vp, tab_k = st.tabs(["📋 DATA", "🌊 VP", "🧪 K"])

# ---------------------------------------------------------------------------
# DATA tab
# ---------------------------------------------------------------------------
with tab_data:
    mode = st.radio(
        "Button Group",
        options=["Single Stress", "Two Stress"],
        horizontal=True,
        key="mode",
        on_change=reset_all,
        label_visibility="collapsed",
    )

    n_rows = 1 if mode == "Single Stress" else 2
    if len(st.session_state.data) != n_rows:
        st.session_state.data = pd.DataFrame([EMPTY_ROW] * n_rows)

    st.session_state.data = st.data_editor(
        st.session_state.data,
        num_rows="fixed",
        use_container_width=True,
        key="data_editor",
    )

    c1, c2 = st.columns(2)
    calculate = c1.button("Calculate", type="primary", use_container_width=True)
    delete = c2.button("Delete", use_container_width=True)

    if delete:
        reset_all()
        st.rerun()

    if calculate:
        df = st.session_state.data
        try:
            if mode == "Single Stress":
                row = df.iloc[0]
                p1, v1, poro1, kk1 = (
                    float(row["Net Stress (psi)"]),
                    float(row["Vp (cc)"]),
                    float(row["Porosity (%)"]),
                    float(row["Kk (md)"]),
                )
                av = compute_av(poro1)
                vo = calibrate_single(v1, p1, av)
                ak = compute_ak(kk1)
                ko = calibrate_single(kk1, p1, ak)
            else:
                r1, r2 = df.iloc[0], df.iloc[1]
                p1, v1 = float(r1["Net Stress (psi)"]), float(r1["Vp (cc)"])
                p2, v2 = float(r2["Net Stress (psi)"]), float(r2["Vp (cc)"])
                kk1, kk2 = float(r1["Kk (md)"]), float(r2["Kk (md)"])
                av, vo = calibrate_two_stress(v1, p1, v2, p2)
                ak, ko = calibrate_two_stress(kk1, p1, kk2, p2)

            st.session_state.coefs = {
                "av": av, "Vo": vo,
                "ak": ak, "Ko": ko,
                "measured": df.copy(),
            }
            st.success("Coeficientes calculados. Revisa las pestañas VP y K.")
        except (TypeError, ValueError):
            st.error("Completa todas las celdas de la tabla con valores numéricos antes de calcular.")
        except ZeroDivisionError:
            st.error("Net Stress no puede repetirse entre filas en modo Two Stress.")


# ---------------------------------------------------------------------------
# Shared chart builder
# ---------------------------------------------------------------------------


def render_result_tab(*, label, x0, coef, measured_col, y_axis_title, chart_title, curve_col_name):
    coefs = st.session_state.coefs
    if coefs is None:
        st.info("Ingresa los datos y presiona **Calculate** en la pestaña DATA.")
        return

    left, right = st.columns([1, 2])
    with left:
        st.markdown("**Jones equation coefficients**")
        m1, m2 = st.columns(2)
        m1.metric(f"{label}o", f"{x0:.3f}")
        m2.metric(f"a{label}", f"{coef:.3f}")
        m3, m4 = st.columns(2)
        m3.metric("C", f"{C:.0e}")
        m4.metric("σ0", f"{SIGMA0:.0f}")

        st.markdown(f"**{label}**")
        stress_input = st.number_input(
            "Net Stress (psi)", min_value=0.0, value=float(measured_col.iloc[0]), step=50.0,
            key=f"stress_input_{label}",
        )
        predicted = forward_model(x0, coef, stress_input)
        st.metric(f"{label} predicted", f"{predicted:.3f}")

    curve = pd.DataFrame({
        "Net Stress (psi)": STRESS_GRID,
        curve_col_name: forward_model(x0, coef, STRESS_GRID).round(3),
    })

    with right:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=coefs["measured"]["Net Stress (psi)"], y=measured_col,
            mode="markers", name=f"Measured {label}",
            marker=dict(size=11, color=SERIES_MEASURED, line=dict(width=1, color="white")),
            hovertemplate="Net Stress: %{x} psi<br>" + label + ": %{y:.3f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=curve["Net Stress (psi)"], y=curve[curve_col_name],
            mode="lines", name="Jones", line=dict(width=2, color=SERIES_MODEL),
            hovertemplate="Net Stress: %{x} psi<br>Jones: %{y:.3f}<extra></extra>",
        ))
        fig.update_layout(
            title=chart_title,
            xaxis_title="Net Stress (psi)",
            yaxis_title=y_axis_title,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(t=60, b=40, l=40, r=20),
            height=430,
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"**{curve_col_name} vs Net Stress**")
    st.dataframe(curve, use_container_width=True, hide_index=True)
    st.download_button(
        f"⬇️ Descargar curva {label} (CSV)",
        curve.to_csv(index=False).encode("utf-8"),
        file_name=f"jones_{label.lower()}_curve.csv",
        mime="text/csv",
    )


with tab_vp:
    if st.session_state.coefs:
        render_result_tab(
            label="Vp", x0=st.session_state.coefs["Vo"], coef=st.session_state.coefs["av"],
            measured_col=st.session_state.coefs["measured"]["Vp (cc)"],
            y_axis_title="Vp (cc)", chart_title="VP vs Net Stress",
            curve_col_name="Vp Jones (cc)",
        )
    else:
        st.info("Ingresa los datos y presiona **Calculate** en la pestaña DATA.")

with tab_k:
    if st.session_state.coefs:
        render_result_tab(
            label="Kk", x0=st.session_state.coefs["Ko"], coef=st.session_state.coefs["ak"],
            measured_col=st.session_state.coefs["measured"]["Kk (md)"],
            y_axis_title="Kk (md)", chart_title="Kk vs Net Stress",
            curve_col_name="K Jones (md)",
        )
    else:
        st.info("Ingresa los datos y presiona **Calculate** en la pestaña DATA.")
