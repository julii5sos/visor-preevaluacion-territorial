import json
from io import BytesIO

import ee
import geemap.foliumap as geemap
import streamlit as st
from google.oauth2 import service_account
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


PROYECTO_EE = st.secrets["EE_PROJECT"]

ASSET_CUENCA = (
    "projects/ee-julissaguevaravega/assets/"
    "CuencasHidrograficadeInteres"
)

ASSET_FINCAS = (
    "projects/ee-julissaguevaravega/assets/"
    "FincasTrinidadv1"
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


@st.cache_data(ttl=3600)
def obtener_ids_finca():
    valores = (
        ee.FeatureCollection(ASSET_FINCAS)
        .aggregate_array("FincaID")
        .distinct()
        .sort()
        .getInfo()
    )

    return [valor for valor in valores if valor is not None]


def generar_pdf(nombre_area, superficie):
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
        f"Área evaluada: {nombre_area}",
    )
    documento.drawString(
        60,
        735,
        f"Superficie aproximada: {superficie:.1f} ha",
    )
    documento.drawString(
        60,
        700,
        "Prototipo para priorizar revisiones.",
    )
    documento.drawString(
        60,
        680,
        "No determina cumplimiento EUDR.",
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

except Exception as error:
    st.error("No fue posible conectar con Earth Engine.")
    st.code(str(error))
    st.stop()


cuenca = ee.FeatureCollection(ASSET_CUENCA)
fincas = ee.FeatureCollection(ASSET_FINCAS)

st.sidebar.header("Área de análisis")

modo_area = st.sidebar.radio(
    "Selecciona el tipo de área",
    ["Toda la cuenca", "Finca de monitoreo"],
)

if modo_area == "Finca de monitoreo":
    ids_finca = obtener_ids_finca()

    finca_elegida = st.sidebar.selectbox(
        "Selecciona la finca",
        ids_finca,
        format_func=str,
    )

    area_seleccionada = fincas.filter(
        ee.Filter.eq("FincaID", finca_elegida)
    )

    nombre_area = f"Finca {finca_elegida}"
    nivel_zoom = 15

else:
    area_seleccionada = cuenca
    nombre_area = "Toda la cuenca"
    nivel_zoom = None


superficie_ha = (
    area_seleccionada
    .geometry()
    .area(1)
    .divide(10000)
    .getInfo()
)

st.success("Earth Engine conectado correctamente.")

columna_1, columna_2 = st.columns(2)

with columna_1:
    st.metric("Área seleccionada", nombre_area)

with columna_2:
    st.metric(
        "Superficie aproximada",
        f"{superficie_ha:,.1f} ha",
    )


mapa = geemap.Map()

mapa.add_basemap("Esri.WorldImagery")

mapa.addLayer(
    cuenca.style(
        color="FF4444",
        fillColor="00000000",
        width=3,
    ),
    {},
    "Límite de la cuenca",
)

mapa.addLayer(
    fincas.style(
        color="C86BFA",
        fillColor="00000000",
        width=2,
    ),
    {},
    "Fincas de monitoreo",
)

if modo_area == "Finca de monitoreo":
    mapa.addLayer(
        area_seleccionada.style(
            color="00FFFF",
            fillColor="00FFFF33",
            width=4,
        ),
        {},
        "Finca seleccionada",
    )

mapa.centerObject(
    area_seleccionada,
    nivel_zoom,
)

mapa.to_streamlit(
    height=650,
    scrolling=False,
    add_layer_control=True,
)


st.download_button(
    label="Descargar ficha PDF",
    data=generar_pdf(nombre_area, superficie_ha),
    file_name="ficha_preevaluacion.pdf",
    mime="application/pdf",
    type="primary",
)
