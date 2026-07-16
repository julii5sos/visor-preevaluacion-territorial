import json
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


@st.cache_data(ttl=3600)
def obtener_ids_fincas():
    fincas = ee.FeatureCollection(ASSET_FINCAS)

    valores = (
        fincas.aggregate_array("FincaID")
        .distinct()
        .sort()
        .getInfo()
    )

    return [
        str(valor)
        for valor in valores
        if valor is not None
    ]


def agregar_capa_ee(
    mapa,
    imagen,
    parametros,
    nombre,
    mostrar=True,
    opacidad=1.0,
):
    datos_mapa = ee.Image(imagen).getMapId(parametros)

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

    longitudes = [punto[0] for punto in coordenadas]
    latitudes = [punto[1] for punto in coordenadas]

    return [
        [min(latitudes), min(longitudes)],
        [max(latitudes), max(longitudes)],
    ]


def generar_pdf(nombre_area, superficie_ha):
    memoria = BytesIO()

    pdf = canvas.Canvas(memoria, pagesize=A4)
    ancho, alto = A4

    pdf.setTitle("Ficha de preevaluación territorial")

    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(
        55,
        alto - 60,
        "FICHA DE PREEVALUACIÓN TERRITORIAL",
    )

    pdf.setFont("Helvetica", 11)

    y = alto - 100

    lineas = [
        f"Área evaluada: {nombre_area}",
        f"Superficie aproximada: {superficie_ha:,.2f} ha",
        "",
        "Finalidad:",
        "Identificar señales territoriales y priorizar revisiones.",
        "",
        "Alcance:",
        "Este documento corresponde a una preevaluación indicativa.",
        "No constituye una validación de campo ni determina",
        "cumplimiento del Reglamento EUDR.",
    ]

    for linea in lineas:
        pdf.drawString(55, y, linea)
        y -= 18

    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(
        55,
        55,
        "Los resultados deben verificarse con información del sitio.",
    )

    pdf.save()
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
    fincas = ee.FeatureCollection(ASSET_FINCAS)

    st.sidebar.header("Área de análisis")

    tipo_area = st.sidebar.radio(
        "Seleccione el área:",
        [
            "Toda la cuenca",
            "Finca de monitoreo",
        ],
    )

    if tipo_area == "Finca de monitoreo":
        ids_fincas = obtener_ids_fincas()

        finca_seleccionada = st.sidebar.selectbox(
            "Seleccione la finca:",
            ids_fincas,
        )

        area_seleccionada = fincas.filter(
            ee.Filter.eq("FincaID", finca_seleccionada)
        )

        nombre_area = f"Finca {finca_seleccionada}"

    else:
        area_seleccionada = cuenca
        nombre_area = "Cuenca hidrográfica de interés"

    superficie_ha = (
        area_seleccionada.geometry()
        .area(1)
        .divide(10000)
        .getInfo()
    )

    columna_1, columna_2 = st.columns(2)

    with columna_1:
        st.metric(
            "Área seleccionada",
            nombre_area,
        )

    with columna_2:
        st.metric(
            "Superficie aproximada",
            f"{superficie_ha:,.1f} ha",
        )

    mapa = folium.Map(
        location=[8.7, -80.0],
        zoom_start=8,
        tiles=None,
        control_scale=True,
    )

    folium.TileLayer(
        tiles=(
            "https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Imagery/MapServer/tile/{z}/{y}/{x}"
        ),
        attr="Esri",
        name="Imagen satelital",
        overlay=False,
        control=True,
        max_zoom=20,
    ).add_to(mapa)

    imagen_cuenca = cuenca.style(
        color="FF4444",
        fillColor="00000000",
        width=3,
    )

    imagen_fincas = fincas.style(
        color="CC55FF",
        fillColor="00000000",
        width=2,
    )

    imagen_seleccion = area_seleccionada.style(
        color="00FFFF",
        fillColor="00FFFF22",
        width=4,
    )

    agregar_capa_ee(
        mapa,
        imagen_cuenca,
        {},
        "Límite de la cuenca",
        True,
    )

    agregar_capa_ee(
        mapa,
        imagen_fincas,
        {},
        "Fincas de monitoreo",
        tipo_area == "Finca de monitoreo",
    )

    agregar_capa_ee(
        mapa,
        imagen_seleccion,
        {},
        "Área seleccionada",
        True,
    )

    mapa.fit_bounds(
        obtener_limites(area_seleccionada)
    )

    folium.LayerControl(
        collapsed=False
    ).add_to(mapa)

    st.subheader("Mapa del área evaluada")

    st_folium(
        mapa,
        width=1200,
        height=650,
        returned_objects=[],
        key=f"mapa-{tipo_area}-{nombre_area}",
    )

    archivo_pdf = generar_pdf(
        nombre_area,
        superficie_ha,
    )

    st.download_button(
        label="Descargar ficha PDF",
        data=archivo_pdf,
        file_name="ficha_preevaluacion_territorial.pdf",
        mime="application/pdf",
        type="primary",
    )

except Exception as error:
    st.error(
        "No fue posible cargar el visor territorial."
    )

    st.exception(error)
