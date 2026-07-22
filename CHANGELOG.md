# Historial de versiones

Este historial documenta la evolución de la aplicación UX. Las versiones siguen
el formato `MAJOR.MINOR.PATCH`: una versión principal, mejoras compatibles y
correcciones compatibles, respectivamente.

## [0.1.3] - 2026-07-21 — versión actual

### Mejorado

- El análisis entrega primero los resultados y deja la creación del PDF como una
  acción posterior solicitada por el usuario.
- Las reducciones de JRC, Hansen, ESRI y GEDI se agrupan en una sola respuesta de
  Earth Engine para reducir viajes de red.
- Los intentos de generación cartográfica pueden repetirse si una miniatura no
  está disponible temporalmente.

## [0.1.2] - 2026-07-21

### Mejorado

- El identificador técnico dejó de mostrarse en la experiencia principal y en el
  PDF.
- La interfaz indica de forma comprensible si la configuración es recomendada o
  personalizada.
- El identificador permanece en el JSON metodológico con una explicación de su
  finalidad técnica.

## [0.1.1] - 2026-07-21

### Mejorado

- Se corrigió el espacio superior de la aplicación para evitar que la barra de
  Streamlit cubriera la cabecera.
- “Preevaluación territorial” pasó a ser el título principal, con mayor tamaño y
  adaptación para pantallas pequeñas.
- Se retiró de la pantalla principal la línea interna de versión y metodología.

## [0.1.0] - 2026-07-21

### Añadido

- Nueva aplicación independiente en `app_experiencia.py`.
- Recorrido guiado para seleccionar el área, elegir el enfoque, revisar resultados
  y explorar evidencia cartográfica.
- Configuración recomendada para usuarios no especialistas y modo técnico mediante
  divulgación progresiva.
- Registro metodológico JSON con fuentes, periodos, umbrales, pesos y reglas.
- Informe PDF con resultados y seis mapas temáticos.
- Compatibilidad con fincas, toda la cuenca y polígonos dibujados por el usuario.

### Conservado

- El motor analítico de JRC TMF, Hansen, ESRI, GEDI y Sentinel-2/NDVI.
- El alcance indicativo: la aplicación no constituye validación de campo ni
  determina cumplimiento EUDR.

[0.1.3]: https://github.com/julii5sos/visor-preevaluacion-territorial/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/julii5sos/visor-preevaluacion-territorial/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/julii5sos/visor-preevaluacion-territorial/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/julii5sos/visor-preevaluacion-territorial/releases/tag/v0.1.0
