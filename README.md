# visor-preevaluacion-territorial

Prototipo de preevaluación territorial que integra datos satelitales para
identificar señales y priorizar revisiones. No determina cumplimiento EUDR.

## Fuentes incorporadas

- JRC Tropical Moist Forest 2025.
- Hansen Global Forest Change 2025.
- ESRI Land Use/Land Cover 2017-2024.
- Altura del dosel basada en GEDI.
- NDVI y cambio de NDVI con Sentinel-2.

## Funcionamiento

El visor permite seleccionar la cuenca o una finca, comparar años mediante un
divisor móvil, activar mapas temáticos con sus leyendas y ejecutar una
preevaluación integrada bajo demanda. Después del análisis se habilita la
descarga de una ficha PDF.

Las capas se solicitan a Earth Engine únicamente cuando se seleccionan y los
cálculos regionales solo se ejecutan al presionar **Ejecutar análisis**. Esto
reduce las recargas innecesarias del visor.

## Alcance

Los resultados son indicativos y deben contrastarse con información del sitio,
documentación del predio, imágenes recientes y verificación de campo cuando
corresponda. No constituyen una certificación, una validación metodológica ni
una determinación legal de cumplimiento EUDR.
