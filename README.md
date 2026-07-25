# Visor de preevaluación territorial

Aplicación Streamlit para identificar señales territoriales, priorizar revisiones y
generar una ficha PDF con resultados y mapas temáticos. Es una herramienta de apoyo:
no constituye una certificación, una validación de campo ni una determinación de
cumplimiento EUDR.

## Versión actual

La versión principal de la nueva experiencia es **v0.2.2**. El historial completo
de mejoras y correcciones está disponible en [CHANGELOG.md](CHANGELOG.md), y el
método reproducible se documenta en [METODOLOGIA.md](METODOLOGIA.md). La
correspondencia con el visor original de Google Earth Engine está registrada en
[PARIDAD_VISOR_GEE.md](PARIDAD_VISOR_GEE.md).

## Flujo para el usuario

1. Seleccionar una finca, dibujar un polígono o, para un resumen regional, toda la cuenca.
2. Elegir un objetivo de revisión:
   - panorama general;
   - cambios de uso del suelo;
   - condición de la vegetación;
   - exploración personalizada.
3. Pulsar **Ejecutar análisis**.
4. Revisar la lectura sencilla, el detalle técnico y los mapas.
5. Descargar el informe PDF con seis mapas temáticos.

Los períodos y las capas recomendadas se configuran automáticamente. Los controles
técnicos permanecen disponibles en **Configuración avanzada**.

### Área dibujada

La opción **Dibujar polígono en el mapa** permite delimitar un área personalizada
directamente sobre la imagen satelital. El visor acepta polígonos cerrados, conserva
el último dibujo durante la sesión y recorta automáticamente cualquier porción que
quede fuera de la cuenca hidrográfica. El análisis, los mapas y el PDF utilizan la
geometría resultante.

## Fuentes incorporadas

- JRC Tropical Moist Forest 2025.
- Hansen Global Forest Change 2025.
- ESRI Land Use/Land Cover 2017-2024.
- Altura del dosel basada en GEDI / OpenForis.
- NDVI y cambio de NDVI derivados de Sentinel-2.

El cálculo de superficies se realiza por fuente en su resolución de trabajo: ESRI a
10 m, JRC y Hansen aproximadamente a 30 m, y el producto de altura a su escala de
análisis. Las fuentes se integran por área; no se interpretan como coincidencias
píxel a píxel.

## Índice operativo de prioridad

Cada fuente activa su señal mediante umbrales explícitos y puede sumar una sola vez:

| Fuente | Peso máximo | Función en el índice |
|---|---:|---|
| JRC Tropical Moist Forest | 2.0 | Evidencia forestal directa de degradación o deforestación |
| Hansen Global Forest Change | 2.0 | Evidencia independiente de pérdida arbórea posterior a 2020 |
| ESRI Land Use/Land Cover | 1.5 | Corroboración de la transición árboles → otra cobertura |
| GEDI | 0.5 | Contexto estructural cuando existe cobertura válida suficiente |
| Sentinel-2 NDVI | 0.0 | Evidencia visual; no modifica la prioridad |

ESRI no puede aportar más que JRC o Hansen. Además, su señal exige simultáneamente
un mínimo de 0.10 ha y 5% del área para reducir cambios aislados de clasificación.
El código centraliza pesos, umbrales, justificaciones y reglas en
`metodologia_indice.py`; el informe PDF y el registro JSON muestran el aporte
efectivo de cada fuente.

La aplicación también informa la consistencia entre JRC, Hansen y ESRI como alta,
parcial, mixta o sin señal consistente. Esta lectura no suma ni resta puntos:
explica si las fuentes principales coinciden y si existen simultáneamente sectores
con deterioro y con recuperación.

## Informe PDF

La ficha utiliza tipografía Times e incluye:

- identificación del área y períodos analizados;
- prioridad y métricas principales;
- consistencia entre fuentes y estadísticas Hansen anteriores y posteriores a 2020;
- interpretación en lenguaje sencillo;
- acción recomendada y conclusión;
- mapas ESRI, JRC, Hansen, GEDI, cambio de NDVI y vigor vegetal;
- diagnóstico por fuente, notas metodológicas y paginación.

## Configuración de Streamlit Cloud

Los secretos se guardan únicamente en **App settings > Secrets**:

```toml
EE_PROJECT = "proyecto-de-earth-engine"
EE_ASSET_FINCAS = "projects/PROYECTO/assets/COLECCION_PRIVADA_DE_FINCAS"
FINCAS_ACCESS_CODE = "CODIGO_PRIVADO_DE_AL_MENOS_8_CARACTERES"

EE_SERVICE_ACCOUNT_JSON = '''
{
  "type": "service_account",
  "project_id": "proyecto-de-earth-engine",
  "private_key": "CLAVE_PRIVADA_COMPLETA",
  "client_email": "cuenta-de-servicio@proyecto.iam.gserviceaccount.com"
}
'''
```

Nunca se debe guardar el archivo JSON real, la dirección verdadera del asset de
fincas ni el código de acceso en el repositorio.

### Protección de las fincas

- La lista de fincas solo se consulta después de ingresar el código autorizado.
- La autorización caduca después de 30 minutos y puede cerrarse manualmente.
- Cinco intentos incorrectos bloquean temporalmente el acceso.
- El mapa muestra únicamente la finca seleccionada, no la colección completa.
- El registro JSON no contiene la ruta del asset ni la geometría vectorial de la finca.
- La colección de Earth Engine debe permanecer privada y compartirse únicamente con
  la cuenta de servicio utilizada por la aplicación.

## Rendimiento

- Las capas se solicitan a Earth Engine solo cuando están activas.
- El análisis entrega primero los resultados; el informe con seis mapas se prepara
  únicamente cuando el usuario lo solicita.
- Las reducciones de JRC, Hansen, ESRI y GEDI se agrupan en una sola respuesta de
  Earth Engine para reducir viajes de red.
- Los resultados y miniaturas se almacenan temporalmente en caché.
- La finca es la opción inicial; el análisis de toda la cuenca puede tardar más.

## Nueva experiencia guiada

El archivo `app_experiencia.py` contiene una segunda aplicación con el mismo motor
territorial de `app.py`, pero con un recorrido pensado para usuarios no especialistas:

- selección del área y del objetivo en dos pasos;
- configuración científica recomendada por defecto;
- controles técnicos mediante divulgación progresiva;
- resumen en lenguaje sencillo y evidencia por fuente;
- mapas interactivos, informe PDF y registro metodológico JSON;
- código de reproducibilidad para identificar cada configuración.

El detalle técnico conserva las seis clases JRC, las transiciones ESRI, la cobertura
arbórea persistente a 2020, las pérdidas Hansen antes y después del corte, GEDI y
un gráfico del aporte ponderado por fuente.

El registro metodológico documenta las fuentes, los períodos, las resoluciones de
trabajo, los umbrales, los pesos y las reglas de prioridad. Esta trazabilidad permite
repetir la configuración y auditar cómo se produjo el resultado, pero no convierte el
prototipo en una herramienta validada ni en una determinación de cumplimiento EUDR.

Para desplegarla como una aplicación independiente en Streamlit Community Cloud use:

- repositorio: `julii5sos/visor-preevaluacion-territorial`;
- rama principal: `main`;
- archivo principal: `app_experiencia.py`;
- los secretos `EE_PROJECT`, `EE_SERVICE_ACCOUNT_JSON`, `EE_ASSET_FINCAS` y
  `FINCAS_ACCESS_CODE` configurados en la aplicación.

`app.py` y `app_experiencia.py` utilizan el mismo módulo metodológico y mantienen
las mismas fuentes, umbrales, pesos y reglas de consistencia. La rama principal
despliega `app_experiencia.py` como interfaz recomendada.
