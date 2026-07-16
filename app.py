import json
import re
from io import BytesIO

import ee
import folium
import streamlit as st
from google.oauth2 import service_account
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from streamlit_folium import st_folium


st.set_page_config(
    page_title="Visor de preevaluación territorial",
    page_icon="🌿",
    layout="wide",
)


PROYECTO_EE = st.secrets["EE_PROJECT"]

ASSET_CUENCA = (
    "projects/ee-julissaguevaravega/assets/"
    "CuencasHidrograficadeInteres"
)

ASSET_FINCAS = (
    "projects/ee-julissaguevaravega/assets/"
    "FincasTrinidadv1"
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


def clave_orden_natural(valor):
    partes = re.split(
        r"(\d+)",
        str(valor).strip(),
    )

    return tuple(
        (0, int(parte))
        if parte.isdigit()
        else (1, parte.casefold())
        for parte in partes
        if parte
    )


@st.cache_data(ttl=3600)
def obtener_ids_fincas():
    fincas = ee.FeatureCollection(ASSET_FINCAS)

    valores = (
        fincas.aggregate_array("FincaID")
        .distinct()
        .getInfo()
    )

    valores_validos = [
        valor
        for valor in valores
        if valor is not None
    ]

    return sorted(
        valores_validos,
        key=clave_orden_natural,
    )


def agregar_capa_ee(
    mapa,
    imagen,
    parametros,
    nombre,
    mostrar=True,
    opacidad=1.0,
):
    datos_mapa = ee.Image(imagen).getMapId(
        parametros
    )

    folium.TileLayer(
        tiles=datos_mapa["tile_fetcher"].url_format,
        attr="Google Earth Engine",
        name=nombre,
        overlay=True,
        control=True,
        show=mostrar,
        opacity=opacidad,
    ).add_to(mapa)


def obtener_limites(objeto):
    coordenadas = (
        objeto.geometry()
        .bounds(1)
        .coordinates()
        .getInfo()[0]
    )

    longitudes = [
        punto[0]
        for punto in coordenadas
    ]

    latitudes = [
        punto[1]
        for punto in coordenadas
    ]

    return [
        [
            min(latitudes),
            min(longitudes),
        ],
        [
            max(latitudes),
            max(longitudes),
        ],
    ]


def generar_pdf(
    nombre_area,
    superficie_ha,
):
    memoria = BytesIO()

    pdf = canvas.Canvas(
        memoria,
        pagesize=A4,
    )

    ancho, alto = A4

    pdf.setTitle(
        "Ficha de preevaluación territorial"
    )

    pdf.setFont(
        "Helvetica-Bold",
        15,
    )

    pdf.drawString(
        55,
        alto - 60,
        "FICHA DE PREEVALUACIÓN TERRITORIAL",
    )

    pdf.setFont(
        "Helvetica",
        11,
    )

    y = alto - 100

    lineas = [
        f"Área evaluada: {nombre_area}",
        (
            "Superficie aproximada: "
            f"{superficie_ha:,.2f} ha"
        ),
        "",
        "Finalidad:",
        (
            "Identificar señales territoriales "
            "y priorizar revisiones."
        ),
        "",
        "Alcance:",
        (
            "Este documento corresponde a una "
            "preevaluación indicativa."
        ),
        (
            "No constituye una validación de campo "
            "ni determina"
        ),
        "cumplimiento del Reglamento EUDR.",
    ]

    for linea in lineas:
        pdf.drawString(
            55,
            y,
            linea,
        )

        y -= 18

    pdf.setFont(
        "Helvetica-Oblique",
        9,
    )

    pdf.drawString(
        55,
        55,
        (
            "Los resultados deben verificarse "
            "con información del sitio."
        ),
    )

    pdf.save()
    memoria.seek(0)

    return memoria.getvalue()


st.title(
    "Visor de preevaluación territorial"
)

st.info(
    "Prototipo para identificar señales y "
    "priorizar revisiones. "
    "No determina cumplimiento EUDR."
)


try:
    iniciar_earth_engine()

    cuenca = ee.FeatureCollection(
        ASSET_CUENCA
    )

    fincas = ee.FeatureCollection(
        ASSET_FINCAS
    )

    st.sidebar.header(
        "Área de análisis"
    )

    tipo_area = st.sidebar.radio(
        "Seleccione el área:",
        [
            "Toda la cuenca",
            "Finca de monitoreo",
        ],
    )

    if tipo_area == "Finca de monitoreo":
        ids_fincas = obtener_ids_fincas()

        finca_seleccionada = (
            st.sidebar.selectbox(
                "Seleccione la finca:",
                ids_fincas,
                format_func=lambda valor: str(valor),
            )
        )

        area_seleccionada = fincas.filter(
            ee.Filter.eq(
                "FincaID",
                finca_seleccionada,
            )
        )

        nombre_area = (
            f"Finca {finca_seleccionada}"
        )

    else:
        area_seleccionada = cuenca

        nombre_area = (
            "Cuenca hidrográfica de interés"
        )

    superficie_ha = (
        area_seleccionada.geometry()
        .area(1)
        .divide(10000)
        .getInfo()
    )

    columna_1, columna_2 =
