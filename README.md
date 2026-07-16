# Visor de preevaluación territorial

Aplicación Streamlit para identificar señales territoriales, priorizar revisiones y
generar una ficha PDF con resultados y mapas temáticos. Es una herramienta de apoyo:
no constituye una certificación, una validación de campo ni una determinación de
cumplimiento EUDR.

## Flujo para el usuario

1. Seleccionar una finca o, para un resumen regional, toda la cuenca.
2. Elegir un objetivo de revisión:
   - panorama general;
   - cambios de uso del suelo;
   - condición de la vegetación;
   - exploración personalizada.
3. Pulsar **Ejecutar preevaluación**.
4. Revisar la lectura sencilla, el detalle técnico y los mapas.
5. Descargar el informe PDF con seis mapas temáticos.

Los períodos y las capas recomendadas se configuran automáticamente. Los controles
técnicos permanecen disponibles en **Configuración avanzada**.

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

## Informe PDF

La ficha utiliza tipografía Times e incluye:

- identificación del área y períodos analizados;
- prioridad y métricas principales;
- interpretación en lenguaje sencillo;
- acción recomendada y conclusión;
- mapas ESRI, JRC, Hansen, GEDI, cambio de NDVI y vigor vegetal;
- diagnóstico por fuente, notas metodológicas y paginación.

## Configuración de Streamlit Cloud

Los secretos se guardan únicamente en **App settings > Secrets**:

```toml
EE_PROJECT = "proyecto-de-earth-engine"

EE_SERVICE_ACCOUNT_JSON = '''
{
  "type": "service_account",
  "project_id": "proyecto-de-earth-engine",
  "private_key": "CLAVE_PRIVADA_COMPLETA",
  "client_email": "cuenta-de-servicio@proyecto.iam.gserviceaccount.com"
}
'''
```

Nunca se debe guardar el archivo JSON real en el repositorio.

## Rendimiento

- Las capas se solicitan a Earth Engine solo cuando están activas.
- El análisis y el informe se generan únicamente al pulsar el botón.
- Los resultados y miniaturas se almacenan temporalmente en caché.
- La finca es la opción inicial; el análisis de toda la cuenca puede tardar más.
