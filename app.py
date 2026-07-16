import json
import re
from datetime import date
from io import BytesIO

import ee
import folium
import streamlit as st
from folium.plugins import Fullscreen, SideBySideLayers
from google.oauth2 import service_account
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from streamlit_folium import st_folium


st.set_page_config(
    page_title="Visor de preevaluación territorial",
    page_icon="🌿",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
    [data-testid="stMetricValue"] {font-size: 1.8rem;}
    [data-testid="stSidebar"] * {overflow-wrap: anywhere;}
    iframe {max-width: 100% !important;}
    .leyenda-fila {
        display: flex;
        align-items: center;
        gap: .55rem;
        margin: .22rem 0;
        font-size: .9rem;
    }
    .leyenda-color {
        width: 1.05rem;
        height: 1.05rem;
        border: 1px solid rgba(0,0,0,.35);
        flex: 0 0 1.05rem;
    }
    .resultado-fuente {
        padding: .7rem .85rem;
        border: 1px solid rgba(128,128,128,.25);
        border-radius: .45rem;
        margin-bottom: .45rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Configuración centralizada
# -----------------------------------------------------------------------------

PROYECTO_EE = st.secrets["EE_PROJECT"]

ASSET_CUENCA = (
    "projects/ee-julissaguevaravega/assets/"
    "CuencasHidrograficadeInteres"
)
ASSET_FINCAS = (
    "projects/ee-julissaguevaravega/assets/"
    "FincasTrinidadv1"
)
HANSEN_ASSET = "UMD/hansen/global_forest_change_2025_v1_13"
TMF_ASSET = "projects/JRC/TMF/v1_2025/AnnualChanges"
ESRI_ASSET = (
    "projects/sat-io/open-datasets/landcover/"
    "ESRI_Global-LULC_10m_TS"
)
GEDI_ASSET = (
    "users/openforisearthmap/World_EarthMap/"
    "CanopyHeight_GEDI_V27"
)

ANO_HANSEN_MAX = 2025
ANO_TMF_MAX = 2025
ANO_ESRI_MIN = 2017
ANO_ESRI_MAX = 2024
ANO_NDVI_MAX = 2025
CUTOFF_YEAR = 20
CUTOFF_LABEL = "31/12/2020"

UMBRAL_ALERTA_HANSEN_HA = 0.18
UMBRAL_REVISION_TMF_DEGRAD_HA = 2.0
UMBRAL_REVISION_TMF_DEFOR_HA = 0.5
UMBRAL_PCT_TMF_DEFOR = 1.0
UMBRAL_PCT_TMF_DEGRAD = 5.0
UMBRAL_PCT_ESRI_SALIDA = 5.0
UMBRAL_DOSEL_BAJO_M = 8.0
UMBRAL_COBERTURA_GEDI_PCT = 20.0

ESRI_ORIG = [1, 2, 4, 5, 7, 8, 9, 10, 11]
ESRI_VIS = [1, 2, 3, 4, 5, 6, 7, 8, 9]
ESRI_COLORES = [
    "1A5BAB",
    "358221",
    "87D19E",
    "FFDB5C",
    "ED022A",
    "EDE9E4",
    "F2FAFF",
    "C8C8C8",
    "C6AD8D",
]

VIS_TMF = {
    "min": 1,
    "max": 6,
    "palette": ["006400", "FFCC00", "FF0000", "00FF00", "0000FF", "BDBDBD"],
}
VIS_ESRI = {"min": 1, "max": 9, "palette": ESRI_COLORES}
VIS_HANSEN_POST = {
    "min": 21,
    "max": 25,
    "palette": ["FF1744", "D50000", "B71C1C", "7F0000", "4A0000"],
}
VIS_HANSEN_PRE = {
    "min": 1,
    "max": 20,
    "palette": ["FFF9C4", "F9A825", "E65100", "C62828"],
}
VIS_LINEA_BASE = {"min": 1, "max": 1, "palette": ["00C853"]}
VIS_TMF_DEFOR = {"min": 1, "max": 1, "palette": ["FF0000"]}
VIS_TMF_DEGRAD = {"min": 1, "max": 1, "palette": ["FFCC00"]}
VIS_ESRI_CAMBIO = {
    "min": 1,
    "max": 3,
    "palette": ["00FF00", "FF0000", "006400"],
}
VIS_GEDI = {
    "min": 0,
    "max": 35,
    "palette": ["FFFFCC", "C2E699", "78C679", "31A354", "006837"],
}
VIS_NDVI_DELTA = {
    "min": -0.3,
    "max": 0.3,
    "palette": ["7F0000", "D32F2F", "FF7043", "FFF9C4", "66BB6A", "2E7D32", "1B5E20"],
}
VIS_NDVI_CLASES = {
    "min": 0,
    "max": 4,
    "palette": ["B30000", "F4A582", "FFFFBF", "78C679", "006837"],
}

LEYENDAS = {
    "JRC TMF": [
        ("#006400", "Bosque no perturbado"),
        ("#FFCC00", "Degradación"),
        ("#FF0000", "Deforestación"),
        ("#00FF00", "Regeneración"),
        ("#0000FF", "Agua"),
        ("#BDBDBD", "Otra cobertura"),
    ],
    "ESRI LULC": [
        ("#1A5BAB", "Agua"),
        ("#358221", "Árboles"),
        ("#87D19E", "Vegetación inundada"),
        ("#FFDB5C", "Cultivos"),
        ("#ED022A", "Área construida"),
        ("#EDE9E4", "Suelo desnudo"),
        ("#F2FAFF", "Nieve/hielo"),
        ("#C8C8C8", "Nubes"),
        ("#C6AD8D", "Pastizal/matorral"),
    ],
    "Pérdida Hansen post-2020": [
        ("#FF1744", "2021"),
        ("#D50000", "2022"),
        ("#B71C1C", "2023"),
        ("#7F0000", "2024"),
        ("#4A0000", "2025"),
    ],
    "Pérdida Hansen 2001-2020": [
        ("#FFF9C4", "Pérdida más antigua"),
        ("#F9A825", "Pérdida intermedia"),
        ("#C62828", "Pérdida próxima a 2020"),
    ],
    "Cobertura arbórea persistente": [("#00C853", "Cobertura arbórea persistente hasta 2020")],
    "Deforestación JRC": [("#FF0000", "Deforestación")],
    "Degradación JRC": [("#FFCC00", "Degradación")],
    "Transiciones ESRI": [
        ("#00FF00", "No árbol → árboles"),
        ("#FF0000", "Árboles → no árbol"),
        ("#006400", "Árboles estables"),
    ],
    "Altura GEDI": [
        ("#FFFFCC", "Dosel bajo"),
        ("#78C679", "Dosel medio"),
        ("#006837", "Dosel alto"),
    ],
    "ΔNDVI": [
        ("#7F0000", "Pérdida fuerte de vigor"),
        ("#FF7043", "Pérdida moderada"),
        ("#FFF9C4", "Cambio pequeño"),
        ("#66BB6A", "Aumento de vigor"),
        ("#1B5E20", "Aumento fuerte"),
    ],
    "Vegetación NDVI": [
        ("#B30000", "Sin vegetación activa"),
        ("#F4A582", "Suelo/cobertura muy escasa"),
        ("#FFFFBF", "Vegetación escasa"),
        ("#78C679", "Vegetación moderada"),
        ("#006837", "Vegetación densa"),
    ],
}


# -----------------------------------------------------------------------------
# Earth Engine y datos
# -----------------------------------------------------------------------------

@st.cache_resource
def iniciar_earth_engine():
    informacion = json.loads(st.secrets["EE_SERVICE_ACCOUNT_JSON"])
    credenciales = service_account.Credentials.from_service_account_info(
        informacion,
        scopes=[
            "https://www.googleapis.com/auth/earthengine",
            "https://www.googleapis.com/auth/cloud-platform",
        ],
    )
    ee.Initialize(credentials=credenciales, project=PROYECTO_EE)
    return True


def clave_orden_natural(valor):
    partes = re.split(r"(\d+)", str(valor).strip())
    return tuple(
        (0, int(parte)) if parte.isdigit() else (1, parte.casefold())
        for parte in partes
        if parte
    )


@st.cache_data(ttl=3600)
def obtener_ids_fincas():
    valores = (
        ee.FeatureCollection(ASSET_FINCAS)
        .aggregate_array("FincaID")
        .distinct()
        .getInfo()
    )
    return sorted(
        [valor for valor in valores if valor is not None],
        key=clave_orden_natural,
    )


def obtener_area(tipo_area, finca_id=None):
    if tipo_area == "Finca de monitoreo":
        return ee.FeatureCollection(ASSET_FINCAS).filter(
            ee.Filter.eq("FincaID", finca_id)
        )
    return ee.FeatureCollection(ASSET_CUENCA)


def obtener_limites(objeto):
    coordenadas = objeto.geometry().bounds(1).coordinates().getInfo()[0]
    longitudes = [punto[0] for punto in coordenadas]
    latitudes = [punto[1] for punto in coordenadas]
    return [
        [min(latitudes), min(longitudes)],
        [max(latitudes), max(longitudes)],
    ]


def obtener_tmf(anio, geometria):
    return (
        ee.ImageCollection(TMF_ASSET)
        .filterBounds(geometria)
        .mosaic()
        .select(f"Dec{anio}")
        .rename(f"tmf_{anio}")
        .clip(geometria)
    )


def obtener_esri(anio, geometria):
    anio_seguro = max(ANO_ESRI_MIN, min(ANO_ESRI_MAX, anio))
    return (
        ee.ImageCollection(ESRI_ASSET)
        .filterBounds(geometria)
        .filterDate(f"{anio_seguro}-01-01", f"{anio_seguro}-12-31")
        .mosaic()
        .select(0)
        .rename(f"esri_{anio_seguro}")
        .clip(geometria)
    )


def obtener_esri_visual(anio, geometria):
    return (
        obtener_esri(anio, geometria)
        .remap(ESRI_ORIG, ESRI_VIS)
        .rename(f"esri_visual_{anio}")
        .selfMask()
    )


def mascara_sentinel_scl(imagen):
    scl = imagen.select("SCL")
    mascara = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)).Or(scl.eq(11))
    return imagen.updateMask(mascara).select(["B8", "B4"]).toFloat()


def obtener_ndvi(anio, geometria):
    anio_respaldo = max(anio - 1, 2017)

    def coleccion(anio_consulta):
        return (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(geometria)
            .filterDate(f"{anio_consulta}-01-01", f"{anio_consulta}-12-31")
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80))
            .map(mascara_sentinel_scl)
        )

    fallback = (
        ee.Image.constant([0, 0])
        .rename(["B8", "B4"])
        .updateMask(ee.Image(0))
        .toFloat()
    )

    def mediana_con_fallback(coleccion_s2):
        return coleccion_s2.merge(
            ee.ImageCollection.fromImages([fallback])
        ).median()

    actual = mediana_con_fallback(coleccion(anio))
    anterior = mediana_con_fallback(coleccion(anio_respaldo))
    compuesto = ee.ImageCollection.fromImages(
        [fallback, anterior, actual]
    ).mosaic()

    return (
        compuesto.normalizedDifference(["B8", "B4"])
        .rename(f"ndvi_{anio}")
        .toFloat()
        .clip(geometria)
    )


def clasificar_ndvi(ndvi):
    clases = (
        ee.Image(0)
        .where(ndvi.lt(0.0), 0)
        .where(ndvi.gte(0.0).And(ndvi.lt(0.2)), 1)
        .where(ndvi.gte(0.2).And(ndvi.lt(0.4)), 2)
        .where(ndvi.gte(0.4).And(ndvi.lt(0.6)), 3)
        .where(ndvi.gte(0.6), 4)
    )
    return clases.updateMask(ndvi.mask()).rename("ndvi_clases").toInt()


def imagenes_hansen(geometria):
    hansen = ee.Image(HANSEN_ASSET)
    cobertura_2000 = hansen.select("treecover2000").unmask(0).gte(30)
    perdida = hansen.select("loss").unmask(0)
    anio_perdida = hansen.select("lossyear")

    perdida_post = (
        anio_perdida.updateMask(anio_perdida.gt(CUTOFF_YEAR))
        .rename("perdida_post")
        .clip(geometria)
    )
    perdida_pre = (
        anio_perdida.updateMask(
            anio_perdida.gt(0).And(anio_perdida.lte(CUTOFF_YEAR))
        )
        .rename("perdida_pre")
        .clip(geometria)
    )
    linea_base = (
        cobertura_2000.And(
            perdida.eq(0).Or(anio_perdida.unmask(0).gt(CUTOFF_YEAR))
        )
        .selfMask()
        .rename("linea_base_2020")
        .clip(geometria)
    )
    return perdida_post, perdida_pre, linea_base


def imagen_gedi(geometria):
    return (
        ee.ImageCollection(GEDI_ASSET)
        .filterBounds(geometria)
        .mosaic()
        .select(0)
        .rename("altura_dosel")
        .clip(geometria)
    )


def capa_gee(mapa, imagen, visualizacion, nombre, mostrar=True, opacidad=1.0, control=True):
    datos = ee.Image(imagen).getMapId(visualizacion)
    capa = folium.TileLayer(
        tiles=datos["tile_fetcher"].url_format,
        attr="Google Earth Engine",
        name=nombre,
        overlay=True,
        control=control,
        show=mostrar,
        opacity=opacidad,
    )
    capa.add_to(mapa)
    return capa


# -----------------------------------------------------------------------------
# Análisis bajo demanda
# -----------------------------------------------------------------------------

def numero(diccionario, clave):
    valor = diccionario.get(clave)
    return float(valor) if valor is not None else 0.0


@st.cache_data(ttl=3600, show_spinner=False)
def ejecutar_analisis(
    tipo_area,
    finca_id,
    anio_tmf,
    anio_esri_inicial,
    anio_esri_final,
):
    area_fc = obtener_area(tipo_area, finca_id)
    geometria = area_fc.geometry()
    area_ha = float(geometria.area(1).divide(10000).getInfo())

    tmf = obtener_tmf(anio_tmf, geometria)
    esri_inicial = obtener_esri(anio_esri_inicial, geometria)
    esri_final = obtener_esri(anio_esri_final, geometria)
    perdida_post, perdida_pre, linea_base = imagenes_hansen(geometria)
    gedi = imagen_gedi(geometria)
    pixel_ha = ee.Image.pixelArea().divide(10000)

    areas = ee.Image.cat(
        [
            tmf.eq(1).multiply(pixel_ha).rename("tmf_estable"),
            tmf.eq(2).multiply(pixel_ha).rename("tmf_degradacion"),
            tmf.eq(3).multiply(pixel_ha).rename("tmf_deforestacion"),
            tmf.eq(4).multiply(pixel_ha).rename("tmf_recuperacion"),
            perdida_post.mask().multiply(pixel_ha).rename("hansen_post"),
            perdida_pre.mask().multiply(pixel_ha).rename("hansen_pre"),
            linea_base.mask().multiply(pixel_ha).rename("linea_base"),
            esri_final.eq(2).multiply(pixel_ha).rename("esri_arboles_final"),
            esri_inicial.eq(2).And(esri_final.neq(2)).multiply(pixel_ha).rename("esri_salida"),
            esri_inicial.neq(2).And(esri_final.eq(2)).multiply(pixel_ha).rename("esri_ganancia"),
            esri_inicial.eq(2).And(esri_final.eq(2)).multiply(pixel_ha).rename("esri_estable"),
        ]
    ).unmask(0)

    resumen_areas = areas.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geometria,
        scale=30,
        bestEffort=True,
        maxPixels=1e9,
        tileScale=4,
    ).getInfo()

    resumen_gedi = ee.Dictionary(
        {
            "altura": gedi.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometria,
                scale=100,
                bestEffort=True,
                maxPixels=1e9,
                tileScale=4,
            ).get("altura_dosel"),
            "area_datos": gedi.mask().multiply(pixel_ha).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometria,
                scale=100,
                bestEffort=True,
                maxPixels=1e9,
                tileScale=4,
            ).get("altura_dosel"),
        }
    ).getInfo()

    resultados = {clave: numero(resumen_areas, clave) for clave in resumen_areas}
    resultados["area_ha"] = area_ha
    resultados["gedi_altura"] = numero(resumen_gedi, "altura")
    resultados["gedi_area_datos"] = numero(resumen_gedi, "area_datos")
    resultados["gedi_cobertura_pct"] = (
        resultados["gedi_area_datos"] / area_ha * 100 if area_ha else 0
    )

    pct_tmf_defor = resultados["tmf_deforestacion"] / area_ha * 100 if area_ha else 0
    pct_tmf_degrad = resultados["tmf_degradacion"] / area_ha * 100 if area_ha else 0
    pct_esri_salida = resultados["esri_salida"] / area_ha * 100 if area_ha else 0
    pct_linea_base = resultados["linea_base"] / area_ha * 100 if area_ha else 0

    senal_tmf = (
        resultados["tmf_deforestacion"] >= UMBRAL_REVISION_TMF_DEFOR_HA
        or pct_tmf_defor >= UMBRAL_PCT_TMF_DEFOR
        or resultados["tmf_degradacion"] >= UMBRAL_REVISION_TMF_DEGRAD_HA
        or pct_tmf_degrad >= UMBRAL_PCT_TMF_DEGRAD
    )
    senal_hansen = resultados["hansen_post"] >= UMBRAL_ALERTA_HANSEN_HA
    senal_esri = (
        resultados["esri_salida"] >= 0.10
        and pct_esri_salida >= UMBRAL_PCT_ESRI_SALIDA
    )
    gedi_disponible = resultados["gedi_cobertura_pct"] >= UMBRAL_COBERTURA_GEDI_PCT
    senal_gedi = (
        gedi_disponible
        and resultados["gedi_altura"] < UMBRAL_DOSEL_BAJO_M
        and pct_linea_base >= 10
    )

    puntaje = (
        (2.0 if senal_tmf else 0.0)
        + (2.0 if senal_hansen else 0.0)
        + (1.5 if senal_esri else 0.0)
        + (0.5 if senal_gedi else 0.0)
    )
    prioridad = (
        "Alta"
        if puntaje >= 3
        else "Media"
        if puntaje >= 1.5
        else "Preventiva"
        if puntaje >= 0.5
        else "Baja"
    )

    resultados.update(
        {
            "pct_tmf_defor": pct_tmf_defor,
            "pct_tmf_degrad": pct_tmf_degrad,
            "pct_esri_salida": pct_esri_salida,
            "pct_linea_base": pct_linea_base,
            "senal_tmf": senal_tmf,
            "senal_hansen": senal_hansen,
            "senal_esri": senal_esri,
            "senal_gedi": senal_gedi,
            "gedi_disponible": gedi_disponible,
            "puntaje": puntaje,
            "prioridad": prioridad,
        }
    )
    return resultados


def texto_recomendacion(prioridad):
    return {
        "Alta": "Visita de campo prioritaria en los sectores con señales coincidentes.",
        "Media": "Revisar imágenes recientes y evaluar si se justifica una visita.",
        "Preventiva": "Mantener monitoreo periódico y revisar condiciones de riesgo.",
        "Baja": "Sin acción inmediata. Continuar el monitoreo anual normal.",
    }[prioridad]


# -----------------------------------------------------------------------------
# PDF institucional
# -----------------------------------------------------------------------------

def generar_pdf(nombre_area, resultados, anio_tmf, anio_esri_inicial, anio_esri_final):
    memoria = BytesIO()
    documento = SimpleDocTemplate(
        memoria,
        pagesize=A4,
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title="Ficha de preevaluación territorial",
    )
    estilos = getSampleStyleSheet()
    estilos.add(
        ParagraphStyle(
            name="TituloFicha",
            parent=estilos["Title"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#244d23"),
            spaceAfter=12,
        )
    )
    estilos.add(
        ParagraphStyle(
            name="SeccionFicha",
            parent=estilos["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#244d23"),
            spaceBefore=10,
            spaceAfter=6,
        )
    )
    estilos.add(
        ParagraphStyle(
            name="CuerpoFicha",
            parent=estilos["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            spaceAfter=6,
        )
    )

    r = resultados
    area = r["area_ha"]
    pct_arbol = r["esri_arboles_final"] / area * 100 if area else 0
    pct_ganancia = r["esri_ganancia"] / area * 100 if area else 0
    fuentes = sum(
        [r["senal_tmf"], r["senal_esri"], r["senal_hansen"], r["senal_gedi"]]
    )

    descripcion_cobertura = (
        "mantiene una cobertura arbórea importante"
        if pct_arbol >= 50
        else "presenta una cobertura arbórea limitada"
        if pct_arbol < 20
        else "combina áreas arboladas y áreas productivas"
    )
    resultado_general = (
        "señales de pérdida o deterioro"
        if fuentes >= 2
        else "una señal localizada de cambio"
        if fuentes == 1
        else "ninguna señal relevante de deterioro reciente"
    )
    coincidencia = (
        "Dos o más fuentes independientes presentan señales en la misma dirección. "
        "Esta coincidencia aumenta la necesidad de revisar los sectores señalados."
        if fuentes >= 2
        else "Las fuentes no muestran el mismo resultado. El cambio puede ser pequeño, "
        "reciente, temporal o estar en bordes de distintas coberturas."
        if fuentes == 1
        else "Las fuentes evaluadas no muestran señales relevantes de deterioro reciente."
    )
    texto_dosel = (
        f"La altura promedio del dosel fue de {r['gedi_altura']:.1f} m, con "
        f"{r['gedi_cobertura_pct']:.0f}% del área cubierta por datos válidos."
        if r["gedi_disponible"]
        else "El producto de altura del dosel no presenta información suficiente para interpretar esta área."
    )

    historia = [Paragraph("FICHA DE PREEVALUACIÓN TERRITORIAL", estilos["TituloFicha"])]
    datos = [
        ["Área evaluada", nombre_area],
        ["Superficie total", f"{area:,.1f} ha"],
        ["Fecha del análisis", date.today().isoformat()],
    ]
    tabla = Table(datos, colWidths=[4.2 * cm, 12.0 * cm])
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f0e3")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#8aa684")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    historia.extend([tabla, Spacer(1, 8)])

    secciones = [
        (
            "RESULTADO GENERAL",
            f"<b>PRIORIDAD {r['prioridad'].upper()} DE REVISIÓN</b><br/><br/>"
            f"El área {descripcion_cobertura}. El análisis identificó {resultado_general}. "
            "Este resultado no confirma por sí solo que haya ocurrido deforestación; "
            "indica si existen sectores que deben revisarse con mayor detalle.",
        ),
        (
            "¿QUÉ SE ENCONTRÓ?",
            f"<b>1. Estado actual de la cobertura</b><br/><br/>"
            f"En {anio_esri_final} se identificaron {r['esri_arboles_final']:.1f} ha "
            f"con cobertura de árboles, aproximadamente {pct_arbol:.1f}% del área.<br/><br/>"
            f"<b>2. Cambios que requieren atención</b><br/><br/>"
            f"Se identificaron {r['esri_salida']:.1f} ha donde la clase árboles pasó "
            f"a otra cobertura entre {anio_esri_inicial} y {anio_esri_final} "
            f"({r['pct_esri_salida']:.1f}% del área). En dirección opuesta, "
            f"{r['esri_ganancia']:.1f} ha pasaron a árboles ({pct_ganancia:.1f}%). "
            f"Hansen registró {r['hansen_post']:.2f} ha de pérdida después del {CUTOFF_LABEL}.<br/><br/>"
            f"{coincidencia}<br/><br/>"
            f"<b>3. Condición del bosque y la vegetación</b><br/><br/>"
            f"JRC TMF {anio_tmf}: {r['tmf_estable']:.1f} ha de bosque estable, "
            f"{r['tmf_degradacion']:.1f} ha de degradación, "
            f"{r['tmf_deforestacion']:.1f} ha de deforestación y "
            f"{r['tmf_recuperacion']:.1f} ha de recuperación.<br/><br/>{texto_dosel}",
        ),
        (
            "¿QUÉ SIGNIFICAN ESTOS RESULTADOS?",
            "Las imágenes satelitales permiten reconocer dónde pudo ocurrir un cambio, "
            "pero no establecen automáticamente su causa. Puede corresponder a manejo "
            "productivo, cosecha de plantaciones, limpieza, regeneración, nubosidad "
            "residual o una modificación real de la cobertura forestal.",
        ),
        (
            "¿DÓNDE SE DEBE REVISAR?",
            "Los sectores resaltados en los mapas temáticos constituyen la referencia "
            "visual para orientar una revisión. Deben contrastarse con imágenes recientes "
            "e información del predio.",
        ),
        ("ACCIÓN RECOMENDADA", texto_recomendacion(r["prioridad"])),
        (
            "CONCLUSIÓN DE LA PREEVALUACIÓN",
            f"El área presenta prioridad {r['prioridad'].lower()} de revisión, con un "
            f"índice operativo de {r['puntaje']:.1f}/6.0. La decisión final debe "
            "complementarse con información del productor, documentación del predio, "
            "imágenes recientes y verificación de campo cuando corresponda.",
        ),
        (
            "INFORMACIÓN TÉCNICA DE RESPALDO",
            "La preevaluación integró JRC Tropical Moist Forest, Hansen Global Forest "
            "Change, ESRI Land Use/Land Cover y altura del dosel basada en GEDI. "
            "Los umbrales son operativos para priorización y no constituyen definiciones legales.<br/><br/>"
            "Los resultados corresponden a una preevaluación territorial. No constituyen "
            "una certificación, una determinación legal ni una confirmación definitiva "
            "de deforestación o de cumplimiento EUDR.",
        ),
    ]
    for titulo, cuerpo in secciones:
        historia.append(Paragraph(titulo, estilos["SeccionFicha"]))
        historia.append(Paragraph(cuerpo, estilos["CuerpoFicha"]))

    historia.extend(
        [
            PageBreak(),
            Paragraph("DIAGNÓSTICO POR FUENTE", estilos["SeccionFicha"]),
        ]
    )
    filas_fuentes = [
        ["Fuente", "Resultado", "Señal"],
        [
            f"JRC TMF {anio_tmf}",
            f"Deforestación {r['tmf_deforestacion']:.1f} ha; degradación {r['tmf_degradacion']:.1f} ha",
            "Sí" if r["senal_tmf"] else "No",
        ],
        [
            f"ESRI {anio_esri_inicial}-{anio_esri_final}",
            f"Salida de árboles {r['esri_salida']:.1f} ha",
            "Sí" if r["senal_esri"] else "No",
        ],
        [
            "Hansen GFC",
            f"Pérdida post-{CUTOFF_LABEL}: {r['hansen_post']:.2f} ha",
            "Sí" if r["senal_hansen"] else "No",
        ],
        [
            "GEDI",
            (
                f"Dosel {r['gedi_altura']:.1f} m; cobertura válida {r['gedi_cobertura_pct']:.0f}%"
                if r["gedi_disponible"]
                else "Datos insuficientes"
            ),
            "Contexto" if r["senal_gedi"] else "No",
        ],
        ["Cambio NDVI Sentinel-2", "Capa de apoyo visual; no participa en el índice", "No"],
    ]
    tabla_fuentes = Table(filas_fuentes, colWidths=[4.0 * cm, 9.8 * cm, 2.2 * cm], repeatRows=1)
    tabla_fuentes.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#244d23")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#8aa684")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7f2")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    historia.extend(
        [
            tabla_fuentes,
            Spacer(1, 12),
            Paragraph(
                "Pesos preliminares de criterio experto: JRC TMF 2.0, Hansen 2.0, "
                "ESRI 1.5 y GEDI 0.5. El índice no es una probabilidad ni una conclusión legal.",
                estilos["CuerpoFicha"],
            ),
        ]
    )
    documento.build(historia)
    memoria.seek(0)
    return memoria.getvalue()


# -----------------------------------------------------------------------------
# Presentación de leyendas y resultados
# -----------------------------------------------------------------------------

def mostrar_leyenda(titulo, elementos):
    st.markdown(f"**{titulo}**")
    html = "".join(
        f'<div class="leyenda-fila"><span class="leyenda-color" '
        f'style="background:{color};"></span><span>{texto}</span></div>'
        for color, texto in elementos
    )
    st.markdown(html, unsafe_allow_html=True)


def mostrar_resultados(resultados, anio_tmf, anio_esri_inicial, anio_esri_final):
    prioridad = resultados["prioridad"]
    color = {
        "Alta": "#b71c1c",
        "Media": "#e65100",
        "Preventiva": "#f9a825",
        "Baja": "#2e7d32",
    }[prioridad]
    st.markdown(
        f"""
        <div style="background:{color}; color:white; padding:1rem 1.2rem;
                    border-radius:.55rem; margin:.5rem 0 1rem 0;">
          <div style="font-size:1.25rem; font-weight:700;">PRIORIDAD {prioridad.upper()} DE REVISIÓN</div>
          <div>Índice operativo: {resultados['puntaje']:.1f}/6.0</div>
          <div style="margin-top:.35rem;">{texto_recomendacion(prioridad)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Bosque estable JRC", f"{resultados['tmf_estable']:.1f} ha")
    c2.metric("Degradación JRC", f"{resultados['tmf_degradacion']:.1f} ha")
    c3.metric("Deforestación JRC", f"{resultados['tmf_deforestacion']:.1f} ha")
    c4.metric("Recuperación JRC", f"{resultados['tmf_recuperacion']:.1f} ha")

    filas = [
        (
            f"Mapa forestal JRC {anio_tmf}",
            f"Deforestación {resultados['tmf_deforestacion']:.1f} ha; "
            f"degradación {resultados['tmf_degradacion']:.1f} ha",
            resultados["senal_tmf"],
        ),
        (
            f"Transiciones ESRI {anio_esri_inicial} → {anio_esri_final}",
            f"Árboles → no árbol: {resultados['esri_salida']:.1f} ha "
            f"({resultados['pct_esri_salida']:.1f}%)",
            resultados["senal_esri"],
        ),
        (
            "Pérdida arbórea Hansen",
            f"Pérdida post-{CUTOFF_LABEL}: {resultados['hansen_post']:.2f} ha",
            resultados["senal_hansen"],
        ),
        (
            "Altura del dosel GEDI",
            (
                f"Dosel {resultados['gedi_altura']:.1f} m; "
                f"{resultados['gedi_cobertura_pct']:.0f}% del área con datos válidos"
                if resultados["gedi_disponible"]
                else "Sin datos válidos suficientes para interpretar el dosel"
            ),
            resultados["senal_gedi"],
        ),
        (
            "ΔNDVI Sentinel-2",
            "Solo visualización; activar la capa en el mapa",
            False,
        ),
    ]
    for titulo, detalle, alerta in filas:
        icono = "⚠" if alerta else "✓"
        color_texto = "#c62828" if alerta else "#2e7d32"
        st.markdown(
            f'<div class="resultado-fuente"><b style="color:{color_texto};">'
            f"{icono} {titulo}</b><br/>{detalle}</div>",
            unsafe_allow_html=True,
        )


# -----------------------------------------------------------------------------
# Aplicación
# -----------------------------------------------------------------------------

st.title("Visor de preevaluación territorial")
st.info(
    "Prototipo para identificar señales y priorizar revisiones. "
    "No determina cumplimiento EUDR."
)

try:
    iniciar_earth_engine()

    st.sidebar.header("Área de análisis")
    tipo_area = st.sidebar.radio(
        "Seleccione el área:",
        ["Toda la cuenca", "Finca de monitoreo"],
    )
    finca_seleccionada = None
    if tipo_area == "Finca de monitoreo":
        finca_seleccionada = st.sidebar.selectbox(
            "Seleccione la finca:",
            obtener_ids_fincas(),
            format_func=str,
        )
        nombre_area = f"Finca {finca_seleccionada}"
    else:
        nombre_area = "Cuenca hidrográfica de interés"

    area_seleccionada = obtener_area(tipo_area, finca_seleccionada)
    geometria = area_seleccionada.geometry()
    superficie_ha = float(geometria.area(1).divide(10000).getInfo())

    st.sidebar.header("Comparador temporal")
    modo_comparador = st.sidebar.selectbox(
        "Fuente del barrido:",
        ["JRC TMF", "ESRI LULC", "Sin comparador"],
    )
    if modo_comparador == "JRC TMF":
        anio_tmf_inicial = st.sidebar.selectbox(
            "Año inicial JRC:",
            list(range(1990, ANO_TMF_MAX)),
            index=list(range(1990, ANO_TMF_MAX)).index(2020),
        )
        anio_tmf_final = st.sidebar.selectbox(
            "Año final JRC:",
            list(range(1991, ANO_TMF_MAX + 1)),
            index=len(list(range(1991, ANO_TMF_MAX + 1))) - 1,
        )
    else:
        anio_tmf_inicial, anio_tmf_final = 2020, ANO_TMF_MAX

    if modo_comparador == "ESRI LULC":
        anio_esri_inicial = st.sidebar.selectbox(
            "Año inicial ESRI:",
            list(range(ANO_ESRI_MIN, ANO_ESRI_MAX)),
            index=0,
        )
        anio_esri_final = st.sidebar.selectbox(
            "Año final ESRI:",
            list(range(ANO_ESRI_MIN + 1, ANO_ESRI_MAX + 1)),
            index=len(list(range(ANO_ESRI_MIN + 1, ANO_ESRI_MAX + 1))) - 1,
        )
    else:
        anio_esri_inicial, anio_esri_final = ANO_ESRI_MIN, ANO_ESRI_MAX

    st.sidebar.header("Mapas temáticos")
    opciones_capas = [
        "Pérdida Hansen post-2020",
        "Pérdida Hansen 2001-2020",
        "Cobertura arbórea persistente",
        "Deforestación JRC",
        "Degradación JRC",
        "Uso y cobertura ESRI",
        "Transiciones ESRI",
        "Altura GEDI",
        "ΔNDVI",
        "Vegetación NDVI",
    ]
    capas_activas = st.sidebar.multiselect(
        "Seleccione las capas que desea cargar:",
        opciones_capas,
        default=["Pérdida Hansen post-2020"],
        help="Solo las capas seleccionadas se solicitan a Earth Engine para mantener el visor rápido.",
    )
    anio_ndvi_inicial = st.sidebar.selectbox(
        "Año inicial para ΔNDVI:",
        list(range(2017, ANO_NDVI_MAX)),
        index=list(range(2017, ANO_NDVI_MAX)).index(2022),
        disabled="ΔNDVI" not in capas_activas,
    )

    columna_area, columna_superficie = st.columns(2)
    columna_area.metric("Área seleccionada", nombre_area)
    columna_superficie.metric("Superficie aproximada", f"{superficie_ha:,.1f} ha")

    with st.expander("Diferencia entre ΔNDVI y vegetación 2025", expanded=False):
        st.markdown(
            f"""
            - **ΔNDVI {anio_ndvi_inicial} → {ANO_NDVI_MAX}:** muestra cuánto cambió el vigor
              vegetal entre ambos años. Rojo indica disminución y verde indica aumento.
            - **Vegetación {ANO_NDVI_MAX}:** muestra la condición del vigor vegetal únicamente
              en {ANO_NDVI_MAX}. No representa un cambio y no distingue por sí sola entre bosque,
              cultivo o pastizal denso.

            GEDI aporta el componente estructural —altura del dosel— que NDVI no puede determinar.
            """
        )

    mapa = folium.Map(
        location=[8.7, -80.0],
        zoom_start=8,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
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
    Fullscreen(position="topleft", title="Pantalla completa").add_to(mapa)

    capa_izquierda = None
    capa_derecha = None
    if modo_comparador == "JRC TMF":
        capa_izquierda = capa_gee(
            mapa,
            obtener_tmf(anio_tmf_inicial, geometria),
            VIS_TMF,
            f"JRC TMF {anio_tmf_inicial}",
            control=False,
        )
        capa_derecha = capa_gee(
            mapa,
            obtener_tmf(anio_tmf_final, geometria),
            VIS_TMF,
            f"JRC TMF {anio_tmf_final}",
            control=False,
        )
    elif modo_comparador == "ESRI LULC":
        capa_izquierda = capa_gee(
            mapa,
            obtener_esri_visual(anio_esri_inicial, geometria),
            VIS_ESRI,
            f"ESRI {anio_esri_inicial}",
            control=False,
        )
        capa_derecha = capa_gee(
            mapa,
            obtener_esri_visual(anio_esri_final, geometria),
            VIS_ESRI,
            f"ESRI {anio_esri_final}",
            control=False,
        )
    if capa_izquierda is not None and capa_derecha is not None:
        SideBySideLayers(
            layer_left=capa_izquierda,
            layer_right=capa_derecha,
        ).add_to(mapa)

    perdida_post = perdida_pre = linea_base = None
    if any(
        nombre in capas_activas
        for nombre in [
            "Pérdida Hansen post-2020",
            "Pérdida Hansen 2001-2020",
            "Cobertura arbórea persistente",
        ]
    ):
        perdida_post, perdida_pre, linea_base = imagenes_hansen(geometria)

    if "Pérdida Hansen post-2020" in capas_activas:
        capa_gee(mapa, perdida_post, VIS_HANSEN_POST, f"Hansen 2021-{ANO_HANSEN_MAX}")
    if "Pérdida Hansen 2001-2020" in capas_activas:
        capa_gee(mapa, perdida_pre, VIS_HANSEN_PRE, "Hansen 2001-2020")
    if "Cobertura arbórea persistente" in capas_activas:
        capa_gee(mapa, linea_base, VIS_LINEA_BASE, "Cobertura arbórea persistente")
    if "Deforestación JRC" in capas_activas:
        capa_gee(
            mapa,
            obtener_tmf(anio_tmf_final, geometria).eq(3).selfMask(),
            VIS_TMF_DEFOR,
            f"Deforestación JRC {anio_tmf_final}",
        )
    if "Degradación JRC" in capas_activas:
        capa_gee(
            mapa,
            obtener_tmf(anio_tmf_final, geometria).eq(2).selfMask(),
            VIS_TMF_DEGRAD,
            f"Degradación JRC {anio_tmf_final}",
        )
    if "Uso y cobertura ESRI" in capas_activas:
        capa_gee(
            mapa,
            obtener_esri_visual(anio_esri_final, geometria),
            VIS_ESRI,
            f"Uso y cobertura ESRI {anio_esri_final}",
        )
    if "Transiciones ESRI" in capas_activas:
        esri_i = obtener_esri(anio_esri_inicial, geometria)
        esri_f = obtener_esri(anio_esri_final, geometria)
        transicion = (
            ee.Image(0)
            .where(esri_i.neq(2).And(esri_f.eq(2)), 1)
            .where(esri_i.eq(2).And(esri_f.neq(2)), 2)
            .where(esri_i.eq(2).And(esri_f.eq(2)), 3)
            .selfMask()
        )
        capa_gee(
            mapa,
            transicion,
            VIS_ESRI_CAMBIO,
            f"Transiciones ESRI {anio_esri_inicial}-{anio_esri_final}",
        )
    if "Altura GEDI" in capas_activas:
        gedi = imagen_gedi(geometria)
        capa_gee(mapa, gedi, VIS_GEDI, "Altura del dosel GEDI")
    ndvi_final = None
    if "ΔNDVI" in capas_activas or "Vegetación NDVI" in capas_activas:
        ndvi_final = obtener_ndvi(ANO_NDVI_MAX, geometria)
    if "ΔNDVI" in capas_activas:
        ndvi_inicial = obtener_ndvi(anio_ndvi_inicial, geometria)
        delta_ndvi = ndvi_final.subtract(ndvi_inicial).rename("delta_ndvi")
        capa_gee(
            mapa,
            delta_ndvi,
            VIS_NDVI_DELTA,
            f"ΔNDVI {anio_ndvi_inicial}-{ANO_NDVI_MAX}",
        )
    if "Vegetación NDVI" in capas_activas:
        capa_gee(
            mapa,
            clasificar_ndvi(ndvi_final),
            VIS_NDVI_CLASES,
            f"Vegetación NDVI {ANO_NDVI_MAX}",
        )

    cuenca = ee.FeatureCollection(ASSET_CUENCA)
    fincas = ee.FeatureCollection(ASSET_FINCAS)
    capa_gee(
        mapa,
        cuenca.style(color="FF4444", fillColor="00000000", width=3),
        {},
        "Límite de la cuenca",
    )
    if tipo_area == "Finca de monitoreo":
        capa_gee(
            mapa,
            fincas.style(color="E040FB", fillColor="00000000", width=2),
            {},
            "Fincas de monitoreo",
        )
    capa_gee(
        mapa,
        area_seleccionada.style(color="00E5FF", fillColor="00E5FF18", width=4),
        {},
        "Área seleccionada",
    )
    mapa.fit_bounds(obtener_limites(area_seleccionada))
    folium.LayerControl(collapsed=True).add_to(mapa)

    st.subheader("Mapa del área evaluada")
    st.caption(
        "Mueva el divisor para comparar los años. Las capas temáticas pueden activarse "
        "o desactivarse desde el control del mapa."
    )
    st_folium(
        mapa,
        height=650,
        use_container_width=True,
        returned_objects=[],
        key=(
            f"mapa-{tipo_area}-{finca_seleccionada}-{modo_comparador}-"
            f"{anio_tmf_inicial}-{anio_tmf_final}-{anio_esri_inicial}-"
            f"{anio_esri_final}-{anio_ndvi_inicial}-{'-'.join(capas_activas)}"
        ),
    )

    st.subheader("Leyenda activa")
    columnas_leyenda = st.columns(2)
    leyendas_activas = []
    if modo_comparador in ("JRC TMF", "ESRI LULC"):
        leyendas_activas.append((modo_comparador, LEYENDAS[modo_comparador]))
    for nombre in capas_activas:
        if nombre in LEYENDAS:
            leyendas_activas.append((nombre, LEYENDAS[nombre]))
        elif nombre == "Uso y cobertura ESRI":
            leyendas_activas.append((nombre, LEYENDAS["ESRI LULC"]))
    for indice, (titulo, elementos) in enumerate(leyendas_activas):
        with columnas_leyenda[indice % 2]:
            mostrar_leyenda(titulo, elementos)

    st.divider()
    st.subheader("Preevaluación integrada")
    st.caption(
        "El análisis se ejecuta únicamente al presionar el botón. Esto evita recalcular "
        "toda la cuenca cada vez que se cambia una capa del mapa."
    )
    if st.button("Ejecutar análisis", type="primary"):
        with st.spinner("Calculando señales territoriales en Earth Engine…"):
            st.session_state["resultados_analisis"] = ejecutar_analisis(
                tipo_area,
                finca_seleccionada,
                anio_tmf_final,
                anio_esri_inicial,
                anio_esri_final,
            )
            st.session_state["firma_analisis"] = (
                tipo_area,
                finca_seleccionada,
                anio_tmf_final,
                anio_esri_inicial,
                anio_esri_final,
            )

    firma_actual = (
        tipo_area,
        finca_seleccionada,
        anio_tmf_final,
        anio_esri_inicial,
        anio_esri_final,
    )
    if st.session_state.get("firma_analisis") == firma_actual:
        resultados = st.session_state["resultados_analisis"]
        mostrar_resultados(
            resultados,
            anio_tmf_final,
            anio_esri_inicial,
            anio_esri_final,
        )
        pdf = generar_pdf(
            nombre_area,
            resultados,
            anio_tmf_final,
            anio_esri_inicial,
            anio_esri_final,
        )
        nombre_archivo = re.sub(r"[^A-Za-z0-9_-]+", "_", nombre_area).strip("_").lower()
        st.download_button(
            "Descargar ficha PDF",
            data=pdf,
            file_name=f"ficha_preevaluacion_{nombre_archivo}.pdf",
            mime="application/pdf",
            type="primary",
        )
    elif "resultados_analisis" in st.session_state:
        st.warning(
            "Cambió el área o el período. Presione “Ejecutar análisis” para actualizar los resultados."
        )

except Exception as error:
    st.error("No fue posible cargar el visor territorial.")
    st.exception(error)
