# Historial de versiones

Este historial documenta la evolución de la aplicación UX. Las versiones siguen
el formato `MAJOR.MINOR.PATCH`: una versión principal, mejoras compatibles y
correcciones compatibles, respectivamente.

## [0.2.1] - 2026-07-24 — versión actual

### Metodología y trazabilidad

- Se centralizaron pesos, umbrales, justificaciones y reglas de prioridad en
  `metodologia_indice.py`.
- El índice suma cada fuente una sola vez: JRC 2.0, Hansen 2.0, ESRI 1.5,
  GEDI 0.5 y NDVI 0.0.
- Se añadieron pruebas que demuestran que ESRI no puede superar el aporte
  individual de JRC ni de Hansen.
- El registro metodológico JSON incluye la justificación de cada peso y umbral,
  además del aporte efectivo por fuente.

### Interfaz e informe

- La composición ponderada se muestra antes que las métricas temáticas.
- JRC, Hansen, ESRI y GEDI reciben una métrica principal cada uno, en ese orden.
- El PDF incorpora una columna de aporte al índice y la justificación de pesos y
  umbrales; NDVI queda identificado explícitamente como evidencia visual.

## [0.2.0] - 2026-07-24

### Mejorado

- El recorrido muestra visualmente qué etapas están completadas, cuál es el paso
  actual y qué falta por hacer.
- Las opciones de área utilizan nombres cotidianos y explican cuándo conviene usar
  una finca, dibujar un polígono o analizar la cuenca completa.
- Antes de ejecutar se anticipan los tres productos que recibirá el usuario:
  conclusión resumida, evidencia cartográfica e informe trazable.
- El resultado incorpora una lectura rápida organizada en tres preguntas:
  qué se detectó, dónde mirar y qué hacer después.

### Accesibilidad y recuperación

- Las tarjetas se reorganizan en una sola columna en pantallas pequeñas y no
  dependen del color para comunicar el estado.
- Los errores de conexión incluyen una explicación comprensible y tres pasos de
  recuperación, conservando el detalle técnico en un panel secundario.

### Metodología

- No se modificaron fuentes, umbrales, pesos, reglas de prioridad ni cálculos
  territoriales.

## [0.1.7] - 2026-07-24

### Corregido

- Los controles de información de la leyenda NDVI ahora se abren con clic o toque,
  además de admitir navegación mediante teclado.
- Cada explicación aparece debajo de su categoría y muestra el intervalo NDVI
  correspondiente sin depender de una ayuda emergente al pasar el cursor.

### Accesibilidad

- El área interactiva ocupa toda la línea de la categoría, conserva un indicador
  de foco visible y funciona en pantallas táctiles.

## [0.1.6] - 2026-07-22

### Añadido

- Acceso mediante código privado antes de consultar o mostrar la lista de fincas.
- Caducidad de la autorización a los 30 minutos, cierre manual y bloqueo temporal
  después de cinco intentos incorrectos.

### Seguridad

- La dirección del asset de fincas se trasladó a los secretos de Streamlit.
- El mapa dejó de solicitar y mostrar la colección completa de fincas; conserva
  únicamente el contorno del área seleccionada.
- El registro metodológico JSON ya no contiene la dirección del asset ni la
  geometría vectorial de las fincas privadas.

## [0.1.5] - 2026-07-22

### Corregido

- Descargar el registro metodológico JSON ya no reinicia la aplicación ni
  interrumpe la preparación de los mapas del informe PDF.
- Descargar un PDF ya preparado tampoco provoca una nueva ejecución de
  Streamlit.

## [0.1.4] - 2026-07-21

### Mejorado

- Los seis mapas del informe se descargan en paralelo, en grupos de tres, en vez
  de esperar cada mapa de forma consecutiva.
- Los límites del área se solicitan una sola vez a Earth Engine para toda la
  generación cartográfica.
- Cada mapa dispone de un intento principal y un segundo intento más liviano;
  se eliminaron esperas consecutivas innecesarias.
- Cuando el usuario reintenta un informe parcial, se conservan los mapas que ya
  fueron descargados y se solicitan únicamente los faltantes.
- El primer informe conserva una clave de caché estable y solo se invalida cuando
  es necesario reintentar mapas faltantes.
- La interfaz informa cuántos mapas fueron entregados antes de armar el PDF y
  conserva los resultados si la generación cartográfica falla.

## [0.1.3] - 2026-07-21

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

[0.2.0]: https://github.com/julii5sos/visor-preevaluacion-territorial/compare/v0.1.7...v0.2.0
[0.1.7]: https://github.com/julii5sos/visor-preevaluacion-territorial/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/julii5sos/visor-preevaluacion-territorial/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/julii5sos/visor-preevaluacion-territorial/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/julii5sos/visor-preevaluacion-territorial/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/julii5sos/visor-preevaluacion-territorial/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/julii5sos/visor-preevaluacion-territorial/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/julii5sos/visor-preevaluacion-territorial/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/julii5sos/visor-preevaluacion-territorial/releases/tag/v0.1.0
