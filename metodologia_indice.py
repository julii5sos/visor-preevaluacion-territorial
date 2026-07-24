"""Reglas auditables del índice operativo de prioridad territorial.

Este módulo no depende de Streamlit ni de Earth Engine. Mantiene en un único
lugar los umbrales, los pesos y la clasificación de prioridad usados por las
dos interfaces de la aplicación.
"""

PESOS_INDICE = {
    "tmf": 2.0,
    "hansen": 2.0,
    "esri": 1.5,
    "gedi": 0.5,
    "ndvi": 0.0,
}

PUNTAJE_MAXIMO = sum(PESOS_INDICE.values())

UMBRALES_INDICE = {
    "hansen_post_2020_ha": 0.18,
    "jrc_deforestacion_ha": 0.5,
    "jrc_deforestacion_pct": 1.0,
    "jrc_degradacion_ha": 2.0,
    "jrc_degradacion_pct": 5.0,
    "esri_salida_arboles_ha": 0.10,
    "esri_salida_arboles_pct": 5.0,
    "gedi_dosel_bajo_m": 8.0,
    "gedi_cobertura_minima_pct": 20.0,
    "gedi_linea_base_minima_pct": 10.0,
}

JUSTIFICACION_UMBRALES = {
    "hansen_post_2020_ha": (
        "0.18 ha equivale aproximadamente a dos píxeles de 30 m. Se evita que "
        "un único píxel aislado active la señal y se conserva sensibilidad a "
        "eventos pequeños posteriores al 31/12/2020."
    ),
    "jrc_deforestacion": (
        "La señal se activa con 0.5 ha o 1% del área. El criterio absoluto "
        "filtra parches mínimos y el relativo conserva sensibilidad en predios "
        "pequeños; cualquiera de los dos puede justificar revisión."
    ),
    "jrc_degradacion": (
        "La señal se activa con 2 ha o 5% del área. Se usa un criterio más "
        "conservador que para deforestación porque la degradación es gradual y "
        "puede presentar mayor ambigüedad espectral."
    ),
    "esri_salida_arboles": (
        "Se exigen simultáneamente 0.10 ha y 5% del área. A 10 m, 0.10 ha "
        "representa diez píxeles; combinar extensión mínima y proporción reduce "
        "transiciones aisladas por error de clasificación. ESRI corrobora, no "
        "domina, las fuentes forestales."
    ),
    "gedi_dosel_y_cobertura": (
        "GEDI solo aporta contexto cuando al menos 20% del área tiene datos "
        "válidos, la altura media es menor de 8 m y la línea base arbórea cubre "
        "al menos 10%. Así se evita interpretar dosel bajo en áreas sin "
        "cobertura arbórea previa o con muestreo insuficiente."
    ),
    "ndvi": (
        "NDVI se mantiene fuera del puntaje porque responde también a "
        "estacionalidad, humedad, cultivos, pastizales, nubes y sombras. Se usa "
        "como evidencia visual para orientar la interpretación."
    ),
}

JUSTIFICACION_PESOS = {
    "tmf": (
        "Peso 2.0: producto forestal anual que distingue directamente "
        "degradación y deforestación en bosque tropical húmedo."
    ),
    "hansen": (
        "Peso 2.0: producto específico de pérdida anual de cobertura arbórea; "
        "aporta una señal independiente posterior al corte de referencia."
    ),
    "esri": (
        "Peso 1.5: producto general de uso y cobertura del suelo. La transición "
        "árbol a no árbol es corroborativa y recibe menos peso que los productos "
        "forestales especializados."
    ),
    "gedi": (
        "Peso 0.5: contexto estructural de altura del dosel con cobertura "
        "espacial limitada; no se interpreta como detección directa de pérdida."
    ),
    "ndvi": (
        "Peso 0.0: apoyo visual de vigor vegetal; no modifica el índice."
    ),
}

REGLAS_PRIORIDAD = {
    "alta": "puntaje >= 3.0",
    "media": "puntaje >= 1.5 y < 3.0",
    "preventiva": "puntaje >= 0.5 y < 1.5",
    "baja": "puntaje < 0.5",
}


def clasificar_prioridad(puntaje):
    """Clasifica un puntaje ya calculado sin alterar su valor."""
    if puntaje >= 3.0:
        return "Alta"
    if puntaje >= 1.5:
        return "Media"
    if puntaje >= 0.5:
        return "Preventiva"
    return "Baja"


def evaluar_senales(
    *,
    tmf_deforestacion_ha,
    tmf_deforestacion_pct,
    tmf_degradacion_ha,
    tmf_degradacion_pct,
    hansen_post_2020_ha,
    esri_salida_arboles_ha,
    esri_salida_arboles_pct,
    gedi_altura_media_m,
    gedi_cobertura_valida_pct,
    linea_base_arborea_pct,
):
    """Aplica los umbrales metodológicos sin asignar pesos todavía."""
    senal_tmf = (
        tmf_deforestacion_ha >= UMBRALES_INDICE["jrc_deforestacion_ha"]
        or tmf_deforestacion_pct >= UMBRALES_INDICE["jrc_deforestacion_pct"]
        or tmf_degradacion_ha >= UMBRALES_INDICE["jrc_degradacion_ha"]
        or tmf_degradacion_pct >= UMBRALES_INDICE["jrc_degradacion_pct"]
    )
    senal_hansen = (
        hansen_post_2020_ha >= UMBRALES_INDICE["hansen_post_2020_ha"]
    )
    # ESRI exige extensión y proporción simultáneamente. Esta conjunción evita
    # que el producto general de cobertura domine el índice por cambios aislados.
    senal_esri = (
        esri_salida_arboles_ha >= UMBRALES_INDICE["esri_salida_arboles_ha"]
        and esri_salida_arboles_pct >= UMBRALES_INDICE["esri_salida_arboles_pct"]
    )
    gedi_disponible = (
        gedi_cobertura_valida_pct
        >= UMBRALES_INDICE["gedi_cobertura_minima_pct"]
    )
    senal_gedi = (
        gedi_disponible
        and gedi_altura_media_m < UMBRALES_INDICE["gedi_dosel_bajo_m"]
        and linea_base_arborea_pct
        >= UMBRALES_INDICE["gedi_linea_base_minima_pct"]
    )
    return {
        "tmf": bool(senal_tmf),
        "hansen": bool(senal_hansen),
        "esri": bool(senal_esri),
        "gedi": bool(senal_gedi),
    }, bool(gedi_disponible)


def calcular_indice_prioridad(
    *,
    senal_tmf,
    senal_hansen,
    senal_esri,
    senal_gedi,
):
    """Suma una sola vez el peso de cada fuente cuya señal está activa."""
    senales = {
        "tmf": bool(senal_tmf),
        "hansen": bool(senal_hansen),
        "esri": bool(senal_esri),
        "gedi": bool(senal_gedi),
        "ndvi": False,
    }
    aportes = {
        fuente: PESOS_INDICE[fuente] if activa else 0.0
        for fuente, activa in senales.items()
    }
    puntaje = round(sum(aportes.values()), 1)
    return aportes, puntaje, clasificar_prioridad(puntaje)
