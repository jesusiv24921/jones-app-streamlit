# JONES APP (Streamlit)

Réplica en Python/Streamlit de la app original en MATLAB App Designer (`jones_app_exported.m`,
diseñada por Jesús Pacheco) para determinar **Vp** y **permeabilidad Klinkenberg (Kk)** corregidas
por esfuerzo neto usando la **ecuación de Jones** (modelo de compactación).

## Qué hace

1. **DATA**: ingresas Depth, Net Stress, Vp, Porosity y Kk para 1 punto (Single Stress) o 2 puntos
   (Two Stress) de laboratorio, y presionas **Calculate**.
2. **VP**: muestra los coeficientes calibrados (Vo, av, C, σ0), permite predecir Vp a cualquier
   Net Stress, y grafica el dato medido contra la curva de Jones (0–4500 psi).
3. **K**: lo mismo para permeabilidad (Ko, ak, Ck, σk).

Las fórmulas de calibración y el modelo directo son una traducción 1:1 de las usadas en el
`.m` original (constantes `C = 3e-6` y `σ0 = 3000` incluidas).

## Correr localmente

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
streamlit run app.py
```

Abre `http://localhost:8501`.

## Desplegar gratis en Streamlit Community Cloud

1. Sube esta carpeta a un repositorio de **GitHub** (puede ser público o privado).
2. Entra a [share.streamlit.io](https://share.streamlit.io) e inicia sesión con tu cuenta de GitHub.
3. Click en **"New app"** → selecciona el repo, la rama y el archivo `app.py`.
4. Click en **Deploy**. En 1–2 minutos tendrás una URL pública tipo
   `https://<nombre>.streamlit.app`.

No requiere tarjeta ni configuración adicional; el plan gratuito de Streamlit Community Cloud
alcanza sin problema para esta app.
