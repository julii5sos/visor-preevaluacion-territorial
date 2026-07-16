import json
import re
from datetime import date
from io import BytesIO

import ee
import folium
import requests
import streamlit as st
from folium.plugins import Draw, Fullscreen, SideBySideLayers
from google.oauth2 import service_account
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image as ReportLabImage,
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
    .block-container {padding-top: 1.25rem; padding-bottom: 2rem; max-width: 1500px;}
    [data-testid="stMetricValue"] {font-size: 1.8rem;}
    [data-testid="stSidebar"] * {overflow-wrap: anywhere;}
    iframe {max-width: 100% !important;}
    .cabecera-app {
        padding: 1.25rem 1.4rem;
        border-radius: .8rem;
        background: linear-gradient(135deg, #17351f 0%, #2f6338 100%);
        color: white;
        margin-bottom: 1rem;
    }
    .cabecera-app h1 {margin: 0; font-size: 2rem; line-height: 1.15; color: white;}
    .cabecera-app p {margin: .55rem 0 0; color: #e8f2e7; max-width: 950px;}
    .paso-guia {
        padding: .75rem .9rem;
        border-left: 4px solid #3f7d44;
        background: #f4f8f2;
        border-radius: 0 .5rem .5rem 0;
        margin: .35rem 0 .85rem;
    }
    .tarjeta-resumen {
        border: 1px solid rgba(47,99,56,.25);
        border-radius: .65rem;
        padding: .85rem 1rem;
        background: #fbfdf9;
        height: 100%;
    }
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

APP_VERSION = "1.2.1"
PROYECTO_EE = st.secrets.get("EE_PROJECT", "ee-julissaguevaravega")

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
VIS_HANSEN_TOTAL = {
    "min": 1,
    "max": 25,
    "palette": ["FFF9C4", "F9A825", "E65100", "FF1744", "7F0000"],
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
VIS_RGB = {"min": 150, "max": 3200, "gamma": 1.15, "bands": ["B4", "B3", "B2"]}

PERFILES_VISUALIZACION = {
    "Panorama general (recomendado)": {
        "descripcion": "Reúne las principales señales de bosque y pérdida arbórea.",
        "comparador": "JRC TMF",
        "capas": [
            "Pérdida Hansen post-2020",
            "Deforestación JRC",
            "Degradación JRC",
        ],
    },
    "Cambios de uso del suelo": {
        "descripcion": "Compara árboles, cultivos, pastizales y otras coberturas.",
        "comparador": "ESRI LULC",
        "capas": ["Uso y cobertura ESRI", "Transiciones ESRI"],
    },
    "Condición de la vegetación": {
        "descripcion": "Muestra vigor vegetal, cambios recientes y altura del dosel.",
        "comparador": "Sin comparador",
        "capas": ["Altura GEDI", "ΔNDVI", "Vegetación NDVI"],
    },
    "Exploración personalizada": {
        "descripcion": "Permite elegir cada fuente, capa y período de análisis.",
        "comparador": "JRC TMF",
        "capas": ["Pérdida Hansen post-2020"],
    },
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
    secreto = st.secrets.get("EE_SERVICE_ACCOUNT_JSON")
    if secreto is None:
        raise RuntimeError(
            "Falta EE_SERVICE_ACCOUNT_JSON en los secretos de esta aplicación."
        )
    if isinstance(secreto, str):
        informacion = json.loads(secreto)
    else:
        informacion = dict(secreto)
    credenciales = service_account.Credentials.from_service_account_info(
        informacion,
        scopes=[
            "https://www.googleapis.com/auth/earthengine",
            "https://www.googleapis.com/auth/cloud-platform",
        ],
    )
    ee.Initialize(credentials=credenciales, project=PROYECTO_EE)
    return True


def nombre_area_legible(tipo_area, finca_id=None):
    if tipo_area == "Toda la cuenca":
        return "Cuenca hidrográfica de interés"
    if tipo_area == "Dibujar polígono en el mapa":
        return "Polígono dibujado por el usuario"
    nombre = str(finca_id).strip()
    return nombre if nombre.casefold().startswith("finca") else f"Finca {nombre}"


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


def obtener_area(tipo_area, finca_id=None, geometria_geojson=None):
    if tipo_area == "Finca de monitoreo":
        return ee.FeatureCollection(ASSET_FINCAS).filter(
            ee.Filter.eq("FincaID", finca_id)
        )
    if tipo_area == "Dibujar polígono en el mapa":
        if not geometria_geojson:
            raise ValueError("Debe dibujar un polígono antes de ejecutar el análisis.")
        datos_geometria = (
            json.loads(geometria_geojson)
            if isinstance(geometria_geojson, str)
            else geometria_geojson
        )
        geometria = ee.Geometry(datos_geometria)
        geometria_cuenca = ee.FeatureCollection(ASSET_CUENCA).geometry()
        geometria_recortada = geometria.intersection(geometria_cuenca, 1)
        return ee.FeatureCollection(
            [ee.Feature(geometria_recortada, {"Origen": "Dibujo del usuario"})]
        )
    return ee.FeatureCollection(ASSET_CUENCA)


def serializar_poligono_dibujado(dibujo):
    geometria = dibujo.get("geometry", dibujo) if dibujo else None
    if not isinstance(geometria, dict):
        raise ValueError("No fue posible interpretar la geometría dibujada.")
    if geometria.get("type") not in {"Polygon", "MultiPolygon"}:
        raise ValueError("La figura debe ser un polígono cerrado.")
    return json.dumps(geometria, sort_keys=True, separators=(",", ":"))


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


def mascara_sentinel_rgb(imagen):
    scl = imagen.select("SCL")
    mascara = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)).Or(scl.eq(11))
    return imagen.updateMask(mascara).select(["B4", "B3", "B2"]).toFloat()


def obtener_rgb_sentinel(anio, geometria):
    coleccion = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(geometria)
        .filterDate(f"{anio}-01-01", f"{anio}-12-31")
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80))
        .map(mascara_sentinel_rgb)
    )
    respaldo = (
        ee.Image.constant([0, 0, 0])
        .rename(["B4", "B3", "B2"])
        .updateMask(ee.Image(0))
        .toFloat()
    )
    return (
        coleccion.merge(ee.ImageCollection.fromImages([respaldo]))
        .median()
        .clip(geometria)
    )


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


def reducir_superficies(imagen, geometria, escala, proyeccion=None):
    parametros = {
        "reducer": ee.Reducer.sum(),
        "geometry": geometria,
        "scale": escala,
        "bestEffort": True,
        "maxPixels": 1e9,
        "tileScale": 4,
    }
    if proyeccion is not None:
        parametros["crs"] = proyeccion
    return imagen.reduceRegion(**parametros).getInfo()


@st.cache_data(ttl=3600, show_spinner=False)
def ejecutar_analisis(
    tipo_area,
    finca_id,
    anio_tmf,
    anio_esri_inicial,
    anio_esri_final,
    geometria_geojson=None,
):
    area_fc = obtener_area(tipo_area, finca_id, geometria_geojson)
    geometria = area_fc.geometry()
    area_ha = float(geometria.area(1).divide(10000).getInfo())

    tmf = obtener_tmf(anio_tmf, geometria)
    esri_inicial = obtener_esri(anio_esri_inicial, geometria)
    esri_final = obtener_esri(anio_esri_final, geometria)
    perdida_post, perdida_pre, linea_base = imagenes_hansen(geometria)
    gedi = imagen_gedi(geometria)
    pixel_ha = ee.Image.pixelArea().divide(10000)

    # Cada fuente se reduce en su propia resolución y proyección. Esto evita
    # forzar los datos ESRI de 10 m a la malla de los productos de 30 m.
    areas_tmf = ee.Image.cat(
        [
            tmf.eq(1).unmask(0).multiply(pixel_ha).rename("tmf_estable"),
            tmf.eq(2).unmask(0).multiply(pixel_ha).rename("tmf_degradacion"),
            tmf.eq(3).unmask(0).multiply(pixel_ha).rename("tmf_deforestacion"),
            tmf.eq(4).unmask(0).multiply(pixel_ha).rename("tmf_recuperacion"),
        ]
    )
    areas_hansen = ee.Image.cat(
        [
            perdida_post.gt(0).unmask(0).multiply(pixel_ha).rename("hansen_post"),
            perdida_pre.gt(0).unmask(0).multiply(pixel_ha).rename("hansen_pre"),
            linea_base.unmask(0).multiply(pixel_ha).rename("linea_base"),
        ]
    )
    areas_esri = ee.Image.cat(
        [
            esri_final.eq(2).unmask(0).multiply(pixel_ha).rename("esri_arboles_final"),
            esri_inicial.eq(2).And(esri_final.neq(2)).unmask(0).multiply(pixel_ha).rename("esri_salida"),
            esri_inicial.neq(2).And(esri_final.eq(2)).unmask(0).multiply(pixel_ha).rename("esri_ganancia"),
            esri_inicial.eq(2).And(esri_final.eq(2)).unmask(0).multiply(pixel_ha).rename("esri_estable"),
        ]
    )

    resumen_areas = {}
    resumen_areas.update(
        reducir_superficies(areas_tmf, geometria, 30, tmf.projection())
    )
    resumen_areas.update(
        reducir_superficies(
            areas_hansen,
            geometria,
            30,
            ee.Image(HANSEN_ASSET).projection(),
        )
    )
    resumen_areas.update(
        reducir_superficies(
            areas_esri,
            geometria,
            10,
            esri_final.projection(),
        )
    )

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


def visualizar_con_borde(imagen, visualizacion, area_fc, fondo=None):
    visual = ee.Image(imagen).visualize(**visualizacion)
    if fondo is not None:
        visual = ee.Image(fondo).visualize(**VIS_RGB).blend(visual)
    borde = (
        ee.Image()
        .byte()
        .paint(featureCollection=area_fc, color=1, width=4)
        .selfMask()
        .visualize(min=1, max=1, palette=["00E5FF"])
    )
    return visual.blend(borde)


def descargar_miniatura(imagen, geometria):
    region = geometria.bounds(1).coordinates().getInfo()
    url = ee.Image(imagen).getThumbURL(
        {
            "region": region,
            "dimensions": "1200x760",
            "format": "png",
        }
    )
    respuesta = requests.get(
        url,
        timeout=60,
        headers={"User-Agent": "visor-preevaluacion-territorial/1.0"},
    )
    respuesta.raise_for_status()
    if len(respuesta.content) < 1000 or not respuesta.content.startswith(b"\x89PNG"):
        raise RuntimeError("Earth Engine no devolvió una imagen PNG válida.")
    return respuesta.content


@st.cache_data(ttl=3600, show_spinner=False)
def generar_mapas_reporte(
    tipo_area,
    finca_id,
    anio_tmf,
    anio_esri_inicial,
    anio_esri_final,
    anio_ndvi_inicial,
    geometria_geojson=None,
):
    area_fc = obtener_area(tipo_area, finca_id, geometria_geojson)
    geometria = area_fc.geometry()
    tmf = obtener_tmf(anio_tmf, geometria)
    gedi = imagen_gedi(geometria)
    ndvi_final = obtener_ndvi(ANO_NDVI_MAX, geometria)
    ndvi_inicial = obtener_ndvi(anio_ndvi_inicial, geometria)
    delta_ndvi = ndvi_final.subtract(ndvi_inicial).rename("delta_ndvi")

    hansen = ee.Image(HANSEN_ASSET).select("lossyear")
    rgb = obtener_rgb_sentinel(ANO_NDVI_MAX, geometria)

    especificaciones = [
        (
            f"ESRI - Uso y cobertura {anio_esri_final}",
            visualizar_con_borde(
                obtener_esri_visual(anio_esri_final, geometria),
                VIS_ESRI,
                area_fc,
            ),
            "Azul: agua | Verde: árboles | Amarillo: cultivos | Rojo: construido | Beige: pastizal",
        ),
        (
            f"JRC TMF - Estado forestal {anio_tmf}",
            visualizar_con_borde(tmf, VIS_TMF, area_fc),
            "Verde oscuro: bosque estable | Amarillo: degradación | Rojo: deforestación | Verde claro: recuperación",
        ),
        (
            f"Hansen - Pérdida arbórea 2001-{ANO_HANSEN_MAX}",
            visualizar_con_borde(
                hansen.updateMask(hansen.gt(0)).clip(geometria),
                VIS_HANSEN_TOTAL,
                area_fc,
                fondo=rgb,
            ),
            "Amarillo: pérdida antigua | Naranja: intermedia | Rojo oscuro: pérdida más reciente",
        ),
        (
            "GEDI - Altura del dosel",
            visualizar_con_borde(gedi, VIS_GEDI, area_fc),
            "Amarillo claro: dosel bajo | Verde medio: dosel intermedio | Verde oscuro: dosel alto",
        ),
        (
            f"ΔNDVI - Cambio de vigor {anio_ndvi_inicial}-{ANO_NDVI_MAX}",
            visualizar_con_borde(delta_ndvi, VIS_NDVI_DELTA, area_fc),
            "Rojo: disminución de vigor | Crema: cambio pequeño | Verde: aumento de vigor",
        ),
        (
            f"Vigor vegetal NDVI - {ANO_NDVI_MAX}",
            visualizar_con_borde(
                clasificar_ndvi(ndvi_final),
                VIS_NDVI_CLASES,
                area_fc,
            ),
            "Rojo: sin vegetación activa | Amarillo: vegetación escasa | Verde: vegetación moderada a densa",
        ),
    ]

    mapas = []
    errores = []
    for titulo, imagen, leyenda in especificaciones:
        try:
            mapas.append(
                {
                    "titulo": titulo,
                    "imagen": descargar_miniatura(imagen, geometria),
                    "leyenda": leyenda,
                }
            )
        except Exception as error:
            mapas.append({"titulo": titulo, "imagen": None, "leyenda": leyenda})
            errores.append(f"{titulo}: {type(error).__name__}")
    return mapas, errores


# -----------------------------------------------------------------------------
# PDF institucional
# -----------------------------------------------------------------------------

def generar_pdf(
    nombre_area,
    resultados,
    anio_tmf,
    anio_esri_inicial,
    anio_esri_final,
    anio_ndvi_inicial,
    mapas=None,
):
    memoria = BytesIO()
    documento = SimpleDocTemplate(
        memoria,
        pagesize=A4,
        rightMargin=1.55 * cm,
        leftMargin=1.55 * cm,
        topMargin=1.55 * cm,
        bottomMargin=1.6 * cm,
        title="Ficha de preevaluación territorial",
        author="Visor de preevaluación territorial",
    )

    verde = colors.HexColor("#244d23")
    verde_claro = colors.HexColor("#e8f0e3")
    borde = colors.HexColor("#8aa684")
    estilos = getSampleStyleSheet()
    estilos.add(
        ParagraphStyle(
            name="TituloFicha",
            parent=estilos["Title"],
            fontName="Times-Bold",
            fontSize=15,
            leading=18,
            alignment=TA_CENTER,
            textColor=verde,
            spaceAfter=8,
        )
    )
    estilos.add(
        ParagraphStyle(
            name="SubtituloFicha",
            parent=estilos["BodyText"],
            fontName="Times-Italic",
            fontSize=9,
            leading=11,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#4d5f4c"),
            spaceAfter=10,
        )
    )
    estilos.add(
        ParagraphStyle(
            name="SeccionFicha",
            parent=estilos["Heading2"],
            fontName="Times-Bold",
            fontSize=10.5,
            leading=13,
            textColor=verde,
            spaceBefore=8,
            spaceAfter=4,
        )
    )
    estilos.add(
        ParagraphStyle(
            name="CuerpoFicha",
            parent=estilos["BodyText"],
            fontName="Times-Roman",
            fontSize=9.2,
            leading=12.2,
            alignment=4,
            spaceAfter=5,
        )
    )
    estilos.add(
        ParagraphStyle(
            name="MapaTitulo",
            parent=estilos["BodyText"],
            fontName="Times-Bold",
            fontSize=8.6,
            leading=10,
            alignment=TA_CENTER,
            textColor=verde,
            spaceAfter=3,
        )
    )
    estilos.add(
        ParagraphStyle(
            name="MapaNota",
            parent=estilos["BodyText"],
            fontName="Times-Roman",
            fontSize=6.8,
            leading=8,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#4d4d4d"),
        )
    )
    estilos.add(
        ParagraphStyle(
            name="CabeceraTabla",
            parent=estilos["BodyText"],
            fontName="Times-Bold",
            fontSize=8.8,
            leading=10,
            textColor=colors.white,
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
        "reciente, temporal o encontrarse en bordes de distintas coberturas."
        if fuentes == 1
        else "Las fuentes evaluadas no muestran señales relevantes de deterioro reciente."
    )
    texto_dosel = (
        f"La altura promedio del dosel fue de {r['gedi_altura']:.1f} m. "
        f"El {r['gedi_cobertura_pct']:.0f}% del área presentó datos válidos en el producto de altura."
        if r["gedi_disponible"]
        else "El producto de altura del dosel no presenta información suficiente para interpretar esta área."
    )

    historia = [
        Paragraph("FICHA DE PREEVALUACIÓN TERRITORIAL", estilos["TituloFicha"]),
        Paragraph(
            "Documento indicativo para orientar revisiones territoriales. No determina cumplimiento EUDR.",
            estilos["SubtituloFicha"],
        ),
    ]
    datos = [
        [Paragraph("Área evaluada", estilos["CuerpoFicha"]), Paragraph(nombre_area, estilos["CuerpoFicha"])],
        [Paragraph("Superficie total", estilos["CuerpoFicha"]), Paragraph(f"{area:,.2f} ha", estilos["CuerpoFicha"])],
        [Paragraph("Fecha del análisis", estilos["CuerpoFicha"]), Paragraph(date.today().strftime("%d/%m/%Y"), estilos["CuerpoFicha"])],
        [Paragraph("Períodos principales", estilos["CuerpoFicha"]), Paragraph(f"JRC 2020-{anio_tmf} | ESRI {anio_esri_inicial}-{anio_esri_final} | NDVI {anio_ndvi_inicial}-{ANO_NDVI_MAX}", estilos["CuerpoFicha"])],
    ]
    tabla = Table(datos, colWidths=[4.0 * cm, 12.5 * cm])
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), verde_claro),
                ("FONTNAME", (0, 0), (0, -1), "Times-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Times-Roman"),
                ("GRID", (0, 0), (-1, -1), 0.4, borde),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    historia.extend([tabla, Spacer(1, 7)])

    color_prioridad = {
        "Alta": "#b71c1c",
        "Media": "#e65100",
        "Preventiva": "#b8860b",
        "Baja": "#2e7d32",
    }[r["prioridad"]]
    tarjeta_prioridad = Table(
        [[Paragraph(
            f"<b>PRIORIDAD {r['prioridad'].upper()} DE REVISIÓN</b><br/>"
            f"Índice operativo: {r['puntaje']:.1f}/6.0 - {texto_recomendacion(r['prioridad'])}",
            ParagraphStyle(
                "Prioridad",
                fontName="Times-Roman",
                fontSize=9.5,
                leading=12,
                textColor=colors.white,
            ),
        )]],
        colWidths=[16.5 * cm],
    )
    tarjeta_prioridad.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(color_prioridad)),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(color_prioridad)),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    metricas = Table(
        [
            [
                Paragraph("Cobertura clasificada como árboles", estilos["CuerpoFicha"]),
                Paragraph(f"<b>{r['esri_arboles_final']:.1f} ha ({pct_arbol:.1f}%)</b>", estilos["CuerpoFicha"]),
                Paragraph("Pérdida posterior a 2020", estilos["CuerpoFicha"]),
                Paragraph(f"<b>{r['hansen_post']:.2f} ha</b>", estilos["CuerpoFicha"]),
            ],
            [
                Paragraph("Deforestación señalada por JRC", estilos["CuerpoFicha"]),
                Paragraph(f"<b>{r['tmf_deforestacion']:.1f} ha</b>", estilos["CuerpoFicha"]),
                Paragraph("Altura promedio del dosel", estilos["CuerpoFicha"]),
                Paragraph(
                    f"<b>{r['gedi_altura']:.1f} m</b>" if r["gedi_disponible"] else "Datos insuficientes",
                    estilos["CuerpoFicha"],
                ),
            ],
        ],
        colWidths=[4.6 * cm, 3.0 * cm, 4.6 * cm, 3.0 * cm],
    )
    metricas.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.35, borde),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7faf6")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    historia.extend([tarjeta_prioridad, Spacer(1, 5), metricas, Spacer(1, 3)])

    secciones = [
        (
            "RESULTADO GENERAL",
            f"El área {descripcion_cobertura}. El análisis identificó {resultado_general}. "
            "Este resultado no confirma por sí solo que haya ocurrido deforestación. "
            "Su función es señalar sectores que requieren una revisión más detallada.",
        ),
        (
            "¿QUÉ SE ENCONTRÓ?",
            f"<b>1. Estado actual de la cobertura.</b> En {anio_esri_final} se identificaron "
            f"{r['esri_arboles_final']:.1f} ha con cobertura clasificada como árboles, "
            f"aproximadamente {pct_arbol:.1f}% del área.<br/><br/>"
            f"<b>2. Cambios que requieren atención.</b> Entre {anio_esri_inicial} y "
            f"{anio_esri_final}, {r['esri_salida']:.1f} ha pasaron de árboles a otra "
            f"cobertura ({r['pct_esri_salida']:.1f}% del área), mientras "
            f"{r['esri_ganancia']:.1f} ha pasaron a árboles ({pct_ganancia:.1f}%). "
            f"Hansen registró {r['hansen_post']:.2f} ha de pérdida después del "
            f"{CUTOFF_LABEL}. {coincidencia}<br/><br/>"
            f"<b>3. Condición del bosque y la vegetación.</b> JRC TMF {anio_tmf} registró "
            f"{r['tmf_estable']:.1f} ha de bosque estable, {r['tmf_degradacion']:.1f} ha "
            f"de degradación, {r['tmf_deforestacion']:.1f} ha de deforestación y "
            f"{r['tmf_recuperacion']:.1f} ha de recuperación. {texto_dosel}",
        ),
        (
            "¿QUÉ SIGNIFICAN ESTOS RESULTADOS?",
            "Las imágenes satelitales permiten reconocer dónde pudo ocurrir un cambio, "
            "pero no establecen automáticamente su causa. El patrón observado puede "
            "corresponder a manejo productivo, cosecha de plantaciones, regeneración, "
            "nubosidad residual o una modificación real de la cobertura forestal.",
        ),
        (
            "¿DÓNDE SE DEBE REVISAR?",
            "Los sectores resaltados en los mapas temáticos son una referencia visual para "
            "orientar la revisión. Deben contrastarse con imágenes recientes, registros de "
            "manejo, información del predio y verificación de campo cuando corresponda.",
        ),
        ("ACCIÓN RECOMENDADA", texto_recomendacion(r["prioridad"])),
        (
            "CONCLUSIÓN DE LA PREEVALUACIÓN",
            f"El área presenta prioridad {r['prioridad'].lower()} de revisión. La decisión "
            "final debe complementarse con información del productor, documentación del "
            "predio, imágenes recientes y verificación de campo cuando corresponda.",
        ),
    ]
    for titulo, cuerpo in secciones:
        historia.append(Paragraph(titulo, estilos["SeccionFicha"]))
        historia.append(Paragraph(cuerpo, estilos["CuerpoFicha"]))

    historia.extend([PageBreak(), Paragraph("MAPAS TEMÁTICOS DEL ÁREA EVALUADA", estilos["TituloFicha"])])
    celdas = []
    for mapa in mapas or []:
        contenido = [Paragraph(mapa["titulo"], estilos["MapaTitulo"])]
        if mapa.get("imagen"):
            imagen = ReportLabImage(BytesIO(mapa["imagen"]))
            escala = min((7.65 * cm) / imagen.imageWidth, (4.85 * cm) / imagen.imageHeight)
            imagen.drawWidth = imagen.imageWidth * escala
            imagen.drawHeight = imagen.imageHeight * escala
            contenido.extend([imagen, Spacer(1, 2)])
        else:
            contenido.append(
                Table(
                    [[Paragraph("Imagen no disponible. Consulte el mapa interactivo.", estilos["MapaNota"])]],
                    colWidths=[7.4 * cm],
                    rowHeights=[4.6 * cm],
                    style=TableStyle(
                        [
                            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdbdbd")),
                            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f4f4")),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ]
                    ),
                )
            )
        contenido.append(Paragraph(mapa["leyenda"], estilos["MapaNota"]))
        celdas.append(contenido)
    if celdas:
        filas_mapas = [celdas[i : i + 2] for i in range(0, len(celdas), 2)]
        if len(filas_mapas[-1]) == 1:
            filas_mapas[-1].append("")
        tabla_mapas = Table(filas_mapas, colWidths=[8.15 * cm, 8.15 * cm])
        tabla_mapas.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.45, borde),
                    ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c8d6c4")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        historia.append(tabla_mapas)
    historia.append(
        Paragraph(
            "Nota cartográfica: el contorno celeste identifica el área evaluada. Las imágenes "
            "se generan automáticamente a partir de las fuentes indicadas y deben interpretarse "
            "junto con las leyendas y las limitaciones metodológicas.",
            estilos["CuerpoFicha"],
        )
    )

    historia.extend([PageBreak(), Paragraph("DIAGNÓSTICO POR FUENTE", estilos["TituloFicha"])])
    filas_fuentes = [
        ["Fuente", "Resultado específico", "Señal"],
        [f"JRC TMF {anio_tmf}", f"Deforestación {r['tmf_deforestacion']:.1f} ha; degradación {r['tmf_degradacion']:.1f} ha", "Sí" if r["senal_tmf"] else "No"],
        [f"ESRI {anio_esri_inicial}-{anio_esri_final}", f"Salida de árboles {r['esri_salida']:.1f} ha ({r['pct_esri_salida']:.1f}%)", "Sí" if r["senal_esri"] else "No"],
        ["Hansen GFC", f"Pérdida posterior al {CUTOFF_LABEL}: {r['hansen_post']:.2f} ha", "Sí" if r["senal_hansen"] else "No"],
        ["GEDI", f"Dosel {r['gedi_altura']:.1f} m; área con datos válidos {r['gedi_cobertura_pct']:.0f}%" if r["gedi_disponible"] else "Datos insuficientes", "Contexto" if r["senal_gedi"] else "No"],
        [f"NDVI {anio_ndvi_inicial}-{ANO_NDVI_MAX}", "Apoyo visual; no participa en el índice operativo", "No aplica"],
    ]
    filas_fuentes = [
        [
            Paragraph(str(c), estilos["CabeceraTabla"] if i == 0 else estilos["CuerpoFicha"])
            for c in fila
        ]
        for i, fila in enumerate(filas_fuentes)
    ]
    tabla_fuentes = Table(filas_fuentes, colWidths=[4.0 * cm, 9.8 * cm, 2.4 * cm], repeatRows=1)
    tabla_fuentes.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), verde),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.4, borde),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7f2")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    historia.extend(
        [
            tabla_fuentes,
            Paragraph("INFORMACIÓN TÉCNICA DE RESPALDO", estilos["SeccionFicha"]),
            Paragraph(
                "La preevaluación integró JRC Tropical Moist Forest, Hansen Global Forest "
                "Change, ESRI Land Use/Land Cover, altura del dosel basada en GEDI y NDVI "
                "derivado de Sentinel-2. Los cálculos se realizan por fuente en su resolución "
                "de trabajo; no se interpretan como coincidencias píxel a píxel.",
                estilos["CuerpoFicha"],
            ),
            Paragraph(
                "Los pesos del índice son criterios operativos preliminares: JRC TMF 2.0, "
                "Hansen 2.0, ESRI 1.5 y GEDI 0.5. El índice no representa una probabilidad, "
                "una certificación, una determinación legal ni una confirmación definitiva "
                "de deforestación o de cumplimiento EUDR.",
                estilos["CuerpoFicha"],
            ),
        ]
    )

    def pie_pagina(canvas_pdf, documento_pdf):
        canvas_pdf.saveState()
        ancho, _ = A4
        canvas_pdf.setStrokeColor(colors.HexColor("#9aab96"))
        canvas_pdf.setLineWidth(0.4)
        canvas_pdf.line(1.55 * cm, 1.2 * cm, ancho - 1.55 * cm, 1.2 * cm)
        canvas_pdf.setFont("Times-Roman", 7.5)
        canvas_pdf.setFillColor(colors.HexColor("#555555"))
        canvas_pdf.drawString(1.55 * cm, 0.82 * cm, "Preevaluación territorial indicativa - requiere verificación")
        canvas_pdf.drawRightString(ancho - 1.55 * cm, 0.82 * cm, f"Página {documento_pdf.page}")
        canvas_pdf.restoreState()

    documento.build(historia, onFirstPage=pie_pagina, onLaterPages=pie_pagina)
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
    area = resultados["area_ha"]
    pct_arboles = resultados["esri_arboles_final"] / area * 100 if area else 0
    resumen, detalle = st.tabs(["Lectura sencilla", "Detalle técnico por fuente"])
    with resumen:
        st.markdown(
            "**¿Qué significa?** La prioridad sirve para decidir dónde conviene revisar "
            "imágenes, documentos o realizar una visita. No demuestra por sí sola la causa del cambio."
        )
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Cobertura de árboles", f"{resultados['esri_arboles_final']:.1f} ha", f"{pct_arboles:.1f}% del área", delta_color="off")
        c2.metric("Árboles que cambiaron", f"{resultados['esri_salida']:.1f} ha", f"{resultados['pct_esri_salida']:.1f}% del área", delta_color="off")
        c3.metric("Pérdida posterior a 2020", f"{resultados['hansen_post']:.2f} ha")
        c4.metric("Deforestación señalada por JRC", f"{resultados['tmf_deforestacion']:.1f} ha")
        st.markdown(f"**Siguiente paso recomendado:** {texto_recomendacion(prioridad)}")

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
    with detalle:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Bosque estable JRC", f"{resultados['tmf_estable']:.1f} ha")
        c2.metric("Degradación JRC", f"{resultados['tmf_degradacion']:.1f} ha")
        c3.metric("Deforestación JRC", f"{resultados['tmf_deforestacion']:.1f} ha")
        c4.metric("Recuperación JRC", f"{resultados['tmf_recuperacion']:.1f} ha")
        for titulo, texto_detalle, alerta in filas:
            icono = "⚠" if alerta else "✓"
            color_texto = "#c62828" if alerta else "#2e7d32"
            st.markdown(
                f'<div class="resultado-fuente"><b style="color:{color_texto};">'
                f"{icono} {titulo}</b><br/>{texto_detalle}</div>",
                unsafe_allow_html=True,
            )
        st.caption("Use el menú de cada gráfico para guardarlo como imagen o descargar sus datos.")
        grafico_jrc, grafico_esri = st.columns(2)
        with grafico_jrc:
            st.markdown("**Distribución del estado forestal JRC**")
            st.bar_chart(
                {
                    "Clase": ["Bosque estable", "Degradación", "Deforestación", "Recuperación"],
                    "Hectáreas": [
                        resultados["tmf_estable"],
                        resultados["tmf_degradacion"],
                        resultados["tmf_deforestacion"],
                        resultados["tmf_recuperacion"],
                    ],
                },
                x="Clase",
                y="Hectáreas",
                height=280,
            )
        with grafico_esri:
            st.markdown("**Cambios de la clase árboles ESRI**")
            st.bar_chart(
                {
                    "Clase": ["Árboles estables", "Salida de árboles", "Ganancia de árboles"],
                    "Hectáreas": [
                        resultados["esri_estable"],
                        resultados["esri_salida"],
                        resultados["esri_ganancia"],
                    ],
                },
                x="Clase",
                y="Hectáreas",
                height=280,
            )


# -----------------------------------------------------------------------------
# Aplicación
# -----------------------------------------------------------------------------

st.markdown(
    """
    <div class="cabecera-app">
      <h1>Visor de preevaluación territorial</h1>
      <p>Herramienta de apoyo para identificar señales territoriales y orientar revisiones.
      Los resultados son indicativos: no sustituyen la verificación de campo ni determinan
      cumplimiento del Reglamento EUDR.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption(f"Versión {APP_VERSION} · Informe PDF con mapas temáticos")

with st.expander("Cómo utilizar el visor", expanded=False):
    st.markdown(
        """
        1. **Seleccione una finca, dibuje un polígono o elija toda la cuenca**.
        2. **Elija qué desea revisar**; la opción recomendada configura las capas automáticamente.
        3. Pulse **Ejecutar preevaluación** y espere los resultados.
        4. Revise los mapas y descargue la ficha PDF con el diagnóstico y las imágenes.

        Los ajustes técnicos son opcionales y están disponibles en **Configuración avanzada**.
        """
    )

try:
    iniciar_earth_engine()

    st.sidebar.markdown("## 1. Área que desea evaluar")
    tipo_area = st.sidebar.radio(
        "Seleccione una opción:",
        ["Finca de monitoreo", "Dibujar polígono en el mapa", "Toda la cuenca"],
        help="Se recomienda iniciar con una finca. El análisis de toda la cuenca puede tardar varios minutos.",
    )
    finca_seleccionada = None
    geometria_dibujada_json = st.session_state.get("geometria_dibujada_json")
    version_mapa_dibujo = st.session_state.get("version_mapa_dibujo", 0)
    if tipo_area == "Finca de monitoreo":
        finca_seleccionada = st.sidebar.selectbox(
            "Finca:",
            obtener_ids_fincas(),
            format_func=str,
            help="Las fincas están ordenadas de forma natural: 1, 2, 3...",
        )
    elif tipo_area == "Dibujar polígono en el mapa":
        st.subheader("1. Dibuje el área que desea evaluar")
        st.markdown(
            "Seleccione la herramienta de polígono en el mapa, marque los vértices y "
            "haga clic en el primer punto para cerrar la figura. El área se limitará "
            "automáticamente a la cuenca hidrográfica."
        )
        if geometria_dibujada_json and st.button("Borrar polígono y dibujar otro"):
            st.session_state.pop("geometria_dibujada_json", None)
            st.session_state.pop("resultados_analisis", None)
            st.session_state.pop("pdf_analisis", None)
            st.session_state.pop("firma_analisis", None)
            st.session_state.pop("errores_mapas", None)
            st.session_state["version_mapa_dibujo"] = version_mapa_dibujo + 1
            st.rerun()

        mapa_dibujo = folium.Map(
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
            control=False,
            max_zoom=20,
        ).add_to(mapa_dibujo)
        cuenca_dibujo = ee.FeatureCollection(ASSET_CUENCA)
        capa_gee(
            mapa_dibujo,
            cuenca_dibujo.style(color="FF4444", fillColor="00000000", width=3),
            {},
            "Límite de la cuenca",
            control=False,
        )
        if geometria_dibujada_json:
            folium.GeoJson(
                json.loads(geometria_dibujada_json),
                name="Polígono dibujado",
                style_function=lambda _: {
                    "color": "#00E5FF",
                    "weight": 4,
                    "fillColor": "#00E5FF",
                    "fillOpacity": 0.12,
                },
            ).add_to(mapa_dibujo)
        Draw(
            export=False,
            position="topleft",
            draw_options={
                "polyline": False,
                "rectangle": False,
                "circle": False,
                "marker": False,
                "circlemarker": False,
                "polygon": {
                    "allowIntersection": False,
                    "showArea": True,
                    "shapeOptions": {"color": "#00E5FF", "weight": 4},
                },
            },
            edit_options={"edit": True, "remove": True},
        ).add_to(mapa_dibujo)
        mapa_dibujo.fit_bounds(obtener_limites(cuenca_dibujo))
        resultado_dibujo = st_folium(
            mapa_dibujo,
            height=520,
            use_container_width=True,
            returned_objects=["all_drawings"],
            key=f"mapa-seleccion-poligono-{version_mapa_dibujo}",
        )
        dibujos = (resultado_dibujo or {}).get("all_drawings") or []
        if dibujos:
            nuevo_poligono = serializar_poligono_dibujado(dibujos[-1])
            if nuevo_poligono != geometria_dibujada_json:
                st.session_state["geometria_dibujada_json"] = nuevo_poligono
                st.rerun()
        geometria_dibujada_json = st.session_state.get("geometria_dibujada_json")
        if not geometria_dibujada_json:
            st.info("Dibuje un polígono para continuar con la preevaluación.")
            st.stop()
        st.success(
            "Polígono listo. Puede continuar con el tipo de revisión y ejecutar la preevaluación."
        )
    nombre_area = nombre_area_legible(tipo_area, finca_seleccionada)

    area_seleccionada = obtener_area(
        tipo_area,
        finca_seleccionada,
        geometria_dibujada_json,
    )
    geometria = area_seleccionada.geometry()
    superficie_ha = float(geometria.area(1).divide(10000).getInfo())
    if tipo_area == "Dibujar polígono en el mapa":
        superficie_original_ha = float(
            ee.Geometry(json.loads(geometria_dibujada_json))
            .area(1)
            .divide(10000)
            .getInfo()
        )
        if superficie_ha <= 0:
            st.error("El polígono no intersecta la cuenca. Bórrelo y dibuje uno dentro del límite rojo.")
            st.stop()
        if superficie_ha + 0.01 < superficie_original_ha:
            st.warning(
                "Una parte del polígono estaba fuera de la cuenca y fue excluida del análisis."
            )

    st.sidebar.markdown("## 2. ¿Qué desea revisar?")
    objetivo = st.sidebar.selectbox(
        "Tipo de revisión:",
        list(PERFILES_VISUALIZACION),
        help="Cada opción activa automáticamente las capas más útiles para ese objetivo.",
    )
    perfil = PERFILES_VISUALIZACION[objetivo]
    st.sidebar.caption(perfil["descripcion"])

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
    nombres_capas = {
        "Pérdida Hansen post-2020": "Pérdida de árboles posterior a 2020",
        "Pérdida Hansen 2001-2020": "Pérdida histórica de árboles (2001-2020)",
        "Cobertura arbórea persistente": "Cobertura arbórea persistente hasta 2020",
        "Deforestación JRC": "Señales de deforestación (JRC)",
        "Degradación JRC": "Señales de degradación (JRC)",
        "Uso y cobertura ESRI": "Uso y cobertura del suelo (ESRI)",
        "Transiciones ESRI": "Cambios de la clase árboles (ESRI)",
        "Altura GEDI": "Altura del dosel (GEDI)",
        "ΔNDVI": "Cambio del vigor vegetal (ΔNDVI)",
        "Vegetación NDVI": f"Vigor vegetal en {ANO_NDVI_MAX} (NDVI)",
    }

    modo_comparador = perfil["comparador"]
    capas_activas = list(perfil["capas"])
    anio_tmf_inicial, anio_tmf_final = 2020, ANO_TMF_MAX
    anio_esri_inicial, anio_esri_final = ANO_ESRI_MIN, ANO_ESRI_MAX
    anio_ndvi_inicial = 2022

    with st.sidebar.expander("Configuración avanzada (opcional)", expanded=False):
        personalizar = st.checkbox(
            "Elegir manualmente mapas y períodos",
            value=objetivo == "Exploración personalizada",
        )
        if personalizar:
            modo_comparador = st.selectbox(
                "Comparación principal:",
                ["JRC TMF", "ESRI LULC", "Sin comparador"],
                index=["JRC TMF", "ESRI LULC", "Sin comparador"].index(modo_comparador),
                help="JRC compara el estado del bosque; ESRI compara el uso y la cobertura del suelo.",
            )
            if modo_comparador == "JRC TMF":
                anio_tmf_inicial = st.selectbox(
                    "Año inicial del bosque:",
                    list(range(1990, ANO_TMF_MAX)),
                    index=list(range(1990, ANO_TMF_MAX)).index(2020),
                )
                anio_tmf_final = st.selectbox(
                    "Año final del bosque:",
                    list(range(anio_tmf_inicial + 1, ANO_TMF_MAX + 1)),
                    index=len(list(range(anio_tmf_inicial + 1, ANO_TMF_MAX + 1))) - 1,
                )
            if modo_comparador == "ESRI LULC":
                anio_esri_inicial = st.selectbox(
                    "Año inicial del uso del suelo:",
                    list(range(ANO_ESRI_MIN, ANO_ESRI_MAX)),
                )
                anio_esri_final = st.selectbox(
                    "Año final del uso del suelo:",
                    list(range(anio_esri_inicial + 1, ANO_ESRI_MAX + 1)),
                    index=len(list(range(anio_esri_inicial + 1, ANO_ESRI_MAX + 1))) - 1,
                )
            capas_activas = st.multiselect(
                "Mapas adicionales:",
                opciones_capas,
                default=capas_activas,
                format_func=lambda valor: nombres_capas[valor],
                help="Seleccione solo los mapas que realmente necesita para mantener el visor ágil.",
            )
            anio_ndvi_inicial = st.selectbox(
                "Año inicial del cambio vegetal:",
                list(range(2017, ANO_NDVI_MAX)),
                index=list(range(2017, ANO_NDVI_MAX)).index(2022),
                disabled="ΔNDVI" not in capas_activas,
            )
        else:
            st.caption(
                f"Períodos recomendados: JRC 2020-{ANO_TMF_MAX}, "
                f"ESRI {ANO_ESRI_MIN}-{ANO_ESRI_MAX} y NDVI 2022-{ANO_NDVI_MAX}."
            )

    columna_area, columna_superficie = st.columns(2)
    columna_area.metric("Área seleccionada", nombre_area)
    columna_superficie.metric("Superficie aproximada", f"{superficie_ha:,.1f} ha")

    if tipo_area == "Toda la cuenca":
        st.warning(
            "El análisis regional puede tardar varios minutos. Para una revisión rápida y "
            "más detallada se recomienda seleccionar una finca."
        )

    st.markdown(
        f"""
        <div class="paso-guia"><b>Configuración lista.</b> Está revisando <b>{nombre_area}</b>
        con el perfil <b>{objetivo}</b>. Pulse el botón de análisis antes de interpretar los mapas.</div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("¿Qué diferencia hay entre cambio vegetal y vigor vegetal?", expanded=False):
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

    st.subheader("3. Ejecute la preevaluación")
    st.caption(
        "El visor calculará las señales y preparará automáticamente la ficha PDF con "
        "seis mapas temáticos. El proceso puede tardar un momento."
    )
    firma_actual = (
        tipo_area,
        finca_seleccionada,
        anio_tmf_final,
        anio_esri_inicial,
        anio_esri_final,
        anio_ndvi_inicial,
        geometria_dibujada_json,
    )
    if st.button(
        "Ejecutar preevaluación",
        type="primary",
        use_container_width=True,
        help="Calcula los resultados y prepara el informe descargable.",
    ):
        with st.spinner("Calculando señales y preparando el informe cartográfico..."):
            resultados_nuevos = ejecutar_analisis(
                tipo_area,
                finca_seleccionada,
                anio_tmf_final,
                anio_esri_inicial,
                anio_esri_final,
                geometria_dibujada_json,
            )
            mapas_reporte, errores_mapas = generar_mapas_reporte(
                tipo_area,
                finca_seleccionada,
                anio_tmf_final,
                anio_esri_inicial,
                anio_esri_final,
                anio_ndvi_inicial,
                geometria_dibujada_json,
            )
            st.session_state["resultados_analisis"] = resultados_nuevos
            st.session_state["firma_analisis"] = firma_actual
            st.session_state["errores_mapas"] = errores_mapas
            if any(mapa.get("imagen") for mapa in mapas_reporte):
                st.session_state["pdf_analisis"] = generar_pdf(
                    nombre_area,
                    resultados_nuevos,
                    anio_tmf_final,
                    anio_esri_inicial,
                    anio_esri_final,
                    anio_ndvi_inicial,
                    mapas_reporte,
                )
            else:
                st.session_state.pop("pdf_analisis", None)

    if st.session_state.get("firma_analisis") == firma_actual:
        resultados = st.session_state["resultados_analisis"]
        mostrar_resultados(
            resultados,
            anio_tmf_final,
            anio_esri_inicial,
            anio_esri_final,
        )
        errores_mapas = st.session_state.get("errores_mapas", [])
        if errores_mapas:
            disponibles = 6 - len(errores_mapas)
            if disponibles:
                st.warning(
                    f"El informe contiene {disponibles} de 6 mapas. Algunas imágenes "
                    "no estuvieron disponibles temporalmente; puede ejecutar nuevamente el análisis."
                )
            else:
                st.error(
                    "Earth Engine no entregó las imágenes cartográficas. No se generó un PDF "
                    "incompleto. Ejecute nuevamente la preevaluación y, si continúa, envíe el "
                    "detalle técnico mostrado abajo."
                )
            with st.expander("Detalle de los mapas no disponibles", expanded=False):
                st.code("\n".join(errores_mapas))
        if st.session_state.get("pdf_analisis"):
            nombre_archivo = re.sub(r"[^A-Za-z0-9_-]+", "_", nombre_area).strip("_").lower()
            st.download_button(
                "Descargar informe PDF con mapas",
                data=st.session_state["pdf_analisis"],
                file_name=f"ficha_preevaluacion_{nombre_archivo}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )
    elif "resultados_analisis" in st.session_state:
        st.warning(
            "Cambió el área o el período. Ejecute nuevamente la preevaluación para "
            "actualizar los resultados y el informe."
        )
    else:
        st.info("Los resultados aparecerán aquí después de ejecutar la preevaluación.")

    st.divider()
    st.subheader("4. Explore los mapas")

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

    st.markdown("#### Mapa interactivo del área evaluada")
    st.caption(
        "Si aparece un divisor vertical, muévalo para comparar dos años. Use el botón "
        "de capas ubicado dentro del mapa para mostrar u ocultar información."
    )
    st_folium(
        mapa,
        height=650,
        use_container_width=True,
        returned_objects=[],
        key=(
            f"mapa-{tipo_area}-{finca_seleccionada}-{modo_comparador}-"
            f"{anio_tmf_inicial}-{anio_tmf_final}-{anio_esri_inicial}-"
            f"{anio_esri_final}-{anio_ndvi_inicial}-{'-'.join(capas_activas)}-"
            f"{hash(geometria_dibujada_json or '')}"
        ),
    )

    with st.expander("Ver leyendas de colores", expanded=True):
        columnas_leyenda = st.columns(2)
        leyendas_activas = []
        if modo_comparador in ("JRC TMF", "ESRI LULC"):
            leyendas_activas.append((modo_comparador, LEYENDAS[modo_comparador]))
        for nombre in capas_activas:
            if nombre in LEYENDAS:
                leyendas_activas.append((nombres_capas.get(nombre, nombre), LEYENDAS[nombre]))
            elif nombre == "Uso y cobertura ESRI":
                leyendas_activas.append((nombres_capas[nombre], LEYENDAS["ESRI LULC"]))
        for indice, (titulo, elementos) in enumerate(leyendas_activas):
            with columnas_leyenda[indice % 2]:
                mostrar_leyenda(titulo, elementos)

    with st.expander("Fuentes utilizadas y alcance de la herramienta", expanded=False):
        st.markdown(
            """
            - **JRC Tropical Moist Forest:** estado anual del bosque tropical húmedo.
            - **Hansen Global Forest Change:** alertas anuales de pérdida de cobertura arbórea.
            - **ESRI Land Use/Land Cover:** clases de uso y cobertura del suelo a 10 m.
            - **GEDI / OpenForis:** altura estimada del dosel y disponibilidad de datos.
            - **Sentinel-2 NDVI:** vigor vegetal y su cambio entre dos períodos.

            Las fuentes tienen resoluciones, fechas y metodologías diferentes. El visor integra
            señales por área para priorizar revisiones; no compara píxeles exactos entre productos
            y no constituye una certificación ni una determinación legal.
            """
        )

except Exception as error:
    st.error("No fue posible cargar el visor territorial.")
    with st.expander("Detalle técnico para soporte", expanded=False):
        st.code(f"{type(error).__name__}: {error}")
