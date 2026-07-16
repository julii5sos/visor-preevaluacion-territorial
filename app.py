def clave_orden_natural(valor):
    partes = re.split(r"(\d+)", str(valor).strip())

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

    ids = [
        str(valor).strip()
        for valor in valores
        if valor is not None
    ]

    return sorted(ids, key=clave_orden_natural)


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
