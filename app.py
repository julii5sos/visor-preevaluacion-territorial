import json
from io import BytesIO

import ee
import streamlit as st
from google.oauth2 import service_account
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


PROYECTO_EE = st.secrets["EE_PROJECT"]
ASSET_CUENCA = (
    "projects/ee-julissaguevaravega/assets/"
    "CuencasHidrograficadeInteres"
)


st.set_page_config(
    page_title="Visor de preevaluación territorial",
    layout="wide",
)


@st.cache_resource
def iniciar_earth_engine():
    informacion = json.loads(
        st.secrets["EE_SERVICE_ACCOUNT_JSON"]
    )

    credenciales = (
        service_account.Credentials.from_service_account_info(
            informacion,
            scopes=[
                "https://www.googleapis.com/auth/earthengine",
                "https://www.googleapis.com/auth/cloud-platform",
            ],
        )
    )

    ee.Initialize(
        credentials=credenciales,
        project=PROYECTO_EE,
    )

    return True


def generar_pdf():
    memoria = BytesIO()
    documento = canvas.Canvas(memoria, pagesize=A4)

    documento.setFont("Helvetica-Bold", 16)
    documento.drawString(
        60,
        790,
        "FICHA DE PREEVALUACIÓN TERRITORIAL",
    )

    documento.setFont("Helvetica", 11)
    documento.drawString(
        60,
        755,
        "Conexión de Streamlit con Earth Engine.",
    )

    documento.save()
    memoria.seek(0)
    return memoria.getvalue()


st.title("Visor de preevaluación territorial")

st.info(
    "Prototipo para identificar señales y priorizar revisiones. "
    "No determina cumplimiento EUDR."
)

try:
    iniciar_earth_engine()

    cuenca = ee.FeatureCollection(ASSET_CUENCA)
    cantidad_elementos = cuenca.size().getInfo()

    st.success(
        "Earth Engine conectado correctamente. "
        f"Elementos encontrados en la cuenca: {cantidad_elementos}."
    )

except Exception as error:
    st.error("No fue posible conectar con Earth Engine.")
    st.code(str(error))


st.download_button(
    label="Descargar ficha PDF",
    data=generar_pdf(),
    file_name="ficha_preevaluacion.pdf",
    mime="application/pdf",
    type="primary",
)
