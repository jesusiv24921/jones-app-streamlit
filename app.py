"""JONES APP — Vp & Permeability stress correction (Jones equation).

Streamlit port of the original MATLAB App Designer app (jones_app_exported.m)
by Jesús Pacheco. Same inputs, same calibration formulas, same forward model —
this file only changes the UI/UX layer, not the Jones equation math below.
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
MUTED_TEXT = "#52514e"

st.set_page_config(page_title="JONES APP", page_icon="🪨", layout="wide")

# ---------------------------------------------------------------------------
# Jones equation — business logic, unchanged
# ---------------------------------------------------------------------------


def compute_av(porosity_pct: float) -> float:
    return 0.0336 + 4.556 * ((porosity_pct / 100) - 0.25) ** 2


def compute_ak(kk: float) -> float:
    lnk = np.log(kk)
    return np.exp(-0.2 - lnk + 0.13 * lnk * np.sqrt(abs(lnk)))


def calibrate_single(value0, stress0, coef):
    return value0 * (1 + C * stress0) * np.exp(coef * (1 - np.exp(-stress0 / SIGMA0)))


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
if "coefs" not in st.session_state:
    st.session_state.coefs = None  # dict once Calculate succeeds

FIELD_SPECS = [
    ("depth", "Depth (ft) *", 0.0, None, 10.0, "%.1f", "Profundidad de la muestra en el pozo."),
    ("stress", "Net Stress (psi) *", 0.0, None, 50.0, "%.0f", "Esfuerzo neto efectivo aplicado en el ensayo de laboratorio."),
    ("vp", "Vp (cc) *", 0.0, None, 0.001, "%.4f", "Velocidad compresional medida en laboratorio."),
    ("poro", "Porosity (%) *", 0.0, 100.0, 0.5, "%.1f", "Porosidad medida en la muestra (0-100)."),
    ("kk", "Kk (md) *", 0.0, None, 0.5, "%.2f", "Permeabilidad Klinkenberg medida (debe ser mayor a 0)."),
]


def field_key(name, point):
    return f"f_{name}_{point}"


def clear_fields():
    for k in list(st.session_state.keys()):
        if k.startswith("f_"):
            del st.session_state[k]
    st.session_state.coefs = None


@st.dialog("Reiniciar formulario")
def confirm_reset_dialog():
    st.write("Se perderán los datos ingresados y los resultados calculados. ¿Deseas continuar?")
    c1, c2 = st.columns(2)
    if c1.button("Sí, reiniciar", type="primary", use_container_width=True):
        clear_fields()
        st.rerun()
    if c2.button("Cancelar", use_container_width=True):
        st.rerun()


def render_point_group(point, title):
    """Renders one 'Punto de referencia' input group and returns (values, errors)."""
    with st.container(border=True):
        st.markdown(f"**{title}**")
        cols = st.columns(len(FIELD_SPECS))
        values = {}
        for col, (name, label, vmin, vmax, step, fmt, help_text) in zip(cols, FIELD_SPECS):
            key = field_key(name, point)
            with col:
                values[name] = st.number_input(
                    label, min_value=vmin, max_value=vmax, step=step, format=fmt,
                    help=help_text, key=key,
                )

        errors = []
        if values["depth"] <= 0:
            errors.append("Ingresa la profundidad (ft).")
        if values["vp"] <= 0:
            errors.append("Ingresa un Vp mayor a 0 (cc).")
        if not (0 < values["poro"] <= 100):
            errors.append("Ingresa una porosidad entre 0 y 100 (%).")
        if values["kk"] <= 0:
            errors.append("Ingresa un Kk mayor a 0 (md).")
        for msg in errors:
            st.caption(f":gray[{msg}]")

        return values


def fields_valid(values):
    return (
        values["depth"] > 0
        and values["vp"] > 0
        and 0 < values["poro"] <= 100
        and values["kk"] > 0
    )


def empty_state(what):
    with st.container(border=True):
        st.markdown(
            f"<div style='text-align:center; padding:2.5rem 1rem;'>"
            f"<div style='font-size:2rem;'>📭</div>"
            f"<div style='font-size:1.05rem;font-weight:600;margin-top:.5rem;'>Todavía no hay resultados</div>"
            f"<div style='color:{MUTED_TEXT};margin-top:.25rem;'>"
            f"Completa los datos en el <b>Paso 1 · Datos</b> y presiona <b>Calculate</b> para ver {what}.</div>"
            f"</div>",
            unsafe_allow_html=True,
        )


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

step1_done = "✓" if st.session_state.coefs else "1"
st.caption(
    f"**Paso 1 · Datos** {'✅' if st.session_state.coefs else ''}  →  "
    f"**Paso 2 · Resultado VP**  →  **Paso 3 · Resultado K**"
)

tab_data, tab_vp, tab_k = st.tabs(["1️⃣ DATA", "2️⃣ VP", "3️⃣ K"])

# ---------------------------------------------------------------------------
# DATA tab
# ---------------------------------------------------------------------------
with tab_data:
    mode = st.radio(
        "Modo de calibración",
        options=["Single Stress", "Two Stress"],
        horizontal=True,
        key="mode",
        on_change=clear_fields,
        help="Single Stress calibra con 1 punto de laboratorio. Two Stress usa 2 puntos y suele ser más preciso.",
    )

    v1 = render_point_group("1", "Punto de referencia 1")
    v2 = None
    if mode == "Two Stress":
        v2 = render_point_group("2", "Punto de referencia 2")

    valid = fields_valid(v1) and (mode == "Single Stress" or (v2 and fields_valid(v2)))
    same_stress = mode == "Two Stress" and valid and v1["stress"] == v2["stress"]
    if same_stress:
        valid = False
        st.caption(":gray[Net Stress debe ser distinto entre el punto 1 y el punto 2.]")

    c1, c2 = st.columns(2)
    calculate = c1.button(
        "Calculate", type="primary", use_container_width=True, disabled=not valid,
        help=None if valid else "Completa todos los campos obligatorios (*) para habilitar el cálculo.",
    )
    delete = c2.button("Reiniciar", use_container_width=True)

    if delete:
        confirm_reset_dialog()

    if calculate:
        if mode == "Single Stress":
            av = compute_av(v1["poro"])
            vo = calibrate_single(v1["vp"], v1["stress"], av)
            ak = compute_ak(v1["kk"])
            ko = calibrate_single(v1["kk"], v1["stress"], ak)
            measured = pd.DataFrame([{
                "Depth (ft)": v1["depth"], "Net Stress (psi)": v1["stress"],
                "Vp (cc)": v1["vp"], "Porosity (%)": v1["poro"], "Kk (md)": v1["kk"],
            }])
        else:
            av, vo = calibrate_two_stress(v1["vp"], v1["stress"], v2["vp"], v2["stress"])
            ak, ko = calibrate_two_stress(v1["kk"], v1["stress"], v2["kk"], v2["stress"])
            measured = pd.DataFrame([
                {"Depth (ft)": v1["depth"], "Net Stress (psi)": v1["stress"],
                 "Vp (cc)": v1["vp"], "Porosity (%)": v1["poro"], "Kk (md)": v1["kk"]},
                {"Depth (ft)": v2["depth"], "Net Stress (psi)": v2["stress"],
                 "Vp (cc)": v2["vp"], "Porosity (%)": v2["poro"], "Kk (md)": v2["kk"]},
            ])

        st.session_state.coefs = {"av": av, "Vo": vo, "ak": ak, "Ko": ko, "measured": measured}
        st.toast("Coeficientes calculados correctamente", icon="✅")
        st.success("✓ Coeficientes calculados. Revisa los pasos **VP** y **K** para ver el resultado.")


# ---------------------------------------------------------------------------
# Shared result renderer (VP / K tabs)
# ---------------------------------------------------------------------------


def render_result_tab(*, label, x0, coef, x0_help, coef_help, measured_col, y_axis_title, chart_title, curve_col_name, empty_label):
    coefs = st.session_state.coefs
    if coefs is None:
        empty_state(empty_label)
        return

    left, right = st.columns([1, 2])
    with left:
        with st.container(border=True):
            st.markdown("**Jones equation coefficients**")
            m1, m2 = st.columns(2)
            m1.metric(f"{label}o", f"{x0:.3f}", help=x0_help)
            m2.metric(f"a{label}", f"{coef:.3f}", help=coef_help)
            m3, m4 = st.columns(2)
            m3.metric("C", f"{C:.0e}", help="Constante de compresibilidad del modelo (fija).")
            m4.metric("σ0", f"{SIGMA0:.0f}", help="Constante de esfuerzo de referencia del modelo (fija).")

        with st.container(border=True):
            st.markdown(f"**Predicción de {label}**")
            stress_input = st.number_input(
                "Net Stress (psi)", min_value=0.0, value=float(measured_col.iloc[0]), step=50.0,
                help="Esfuerzo neto al que quieres predecir el valor.",
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

    with st.container(border=True):
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
            x0_help="Vp a esfuerzo cero (cc).", coef_help="Sensibilidad de Vp al esfuerzo neto.",
            measured_col=st.session_state.coefs["measured"]["Vp (cc)"],
            y_axis_title="Vp (cc)", chart_title="VP vs Net Stress",
            curve_col_name="Vp Jones (cc)", empty_label="el resultado de VP",
        )
    else:
        empty_state("el resultado de VP")

with tab_k:
    if st.session_state.coefs:
        render_result_tab(
            label="Kk", x0=st.session_state.coefs["Ko"], coef=st.session_state.coefs["ak"],
            x0_help="Kk a esfuerzo cero (md).", coef_help="Sensibilidad de Kk al esfuerzo neto.",
            measured_col=st.session_state.coefs["measured"]["Kk (md)"],
            y_axis_title="Kk (md)", chart_title="Kk vs Net Stress",
            curve_col_name="K Jones (md)", empty_label="el resultado de K",
        )
    else:
        empty_state("el resultado de K")
