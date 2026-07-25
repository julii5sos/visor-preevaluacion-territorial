# Metodología del índice operativo de prioridad

**Versión del método:** MT-2026.3

**Versión de implementación auditada:** UX-0.2.4

## Finalidad y alcance

El índice organiza áreas para revisión posterior mediante señales satelitales
complementarias. No representa una probabilidad de deforestación, no identifica por
sí solo la causa de un cambio y no constituye validación de campo, certificación ni
determinación de cumplimiento EUDR.

## Fuentes integradas

| Fuente | Resolución de trabajo | Uso |
|---|---:|---|
| JRC Tropical Moist Forest 2025 | 30 m | Estado anual de bosque, degradación y deforestación |
| Hansen Global Forest Change 2025 | 30 m | Pérdida anual de cobertura arbórea |
| ESRI Land Use/Land Cover | 10 m | Transición de la clase árboles a otra cobertura |
| Altura de dosel GEDI / OpenForis | 100 m | Contexto estructural y cobertura válida |
| Sentinel-2 SR Harmonized | 10 m | NDVI y cambio de vigor vegetal, solo visual |

Cada producto se procesa en su propia proyección y resolución. Las superficies se
calculan dentro del área seleccionada y se integran como evidencia por fuente; no se
fuerzan coincidencias píxel a píxel entre productos.

Para JRC TMF se calculan las seis clases anuales: bosque estable, degradación,
deforestación, recuperación, agua y otra cobertura. Las seis se muestran en las
estadísticas; solo degradación y deforestación pueden activar la señal de deterioro.

## Activación de señales

### JRC TMF

La señal se activa cuando se cumple al menos una condición:

- deforestación ≥ 0.5 ha;
- deforestación ≥ 1% del área;
- degradación ≥ 2.0 ha;
- degradación ≥ 5% del área.

Los criterios absoluto y relativo conservan sensibilidad en áreas de tamaños
diferentes. La degradación utiliza valores más conservadores porque puede ser
gradual y presentar mayor ambigüedad espectral.

### Hansen Global Forest Change

La señal se activa con pérdida posterior al 31/12/2020 ≥ 0.18 ha. Este valor
equivale aproximadamente a dos píxeles de 30 m, por lo que evita que un único píxel
aislado determine el resultado y mantiene sensibilidad a eventos pequeños.

### ESRI Land Use/Land Cover

La señal se activa únicamente cuando se cumplen simultáneamente:

- salida de la clase árboles ≥ 0.10 ha; y
- salida de la clase árboles ≥ 5% del área.

A 10 m, 0.10 ha representa diez píxeles. Exigir extensión y proporción reduce
transiciones aisladas por variabilidad de clasificación. Esta regla y el peso 1.5
impiden que ESRI domine a los productos forestales especializados.

### GEDI

La señal contextual se activa únicamente cuando:

- al menos 20% del área tiene datos válidos;
- la altura media del dosel es menor de 8 m; y
- la línea base arbórea cubre al menos 10% del área.

La combinación evita interpretar dosel bajo en zonas sin cobertura arbórea previa o
con disponibilidad espacial insuficiente.

### NDVI de Sentinel-2

Se calcula como `(B8 - B4) / (B8 + B4)` sobre compuestos anuales con máscara SCL.
Se utiliza solo como evidencia visual porque puede responder a estacionalidad,
humedad, cultivos, pastizales, nubes y sombras. Su aporte al índice es 0.0.

La clasificación visual utilizada en el mapa y el informe es:

| Intervalo NDVI | Lectura visual | Interpretación orientativa |
|---:|---|---|
| < 0 | Sin vegetación activa | Agua, sombra, nubes residuales o superficies no vegetadas |
| 0.0 a < 0.2 | Suelo o cobertura muy escasa | Suelo desnudo, área construida o vegetación muy dispersa |
| 0.2 a < 0.4 | Vegetación escasa | Cobertura poco densa, pastizal o cultivo en etapa temprana |
| 0.4 a < 0.6 | Vegetación moderada | Actividad vegetal y cobertura intermedias |
| ≥ 0.6 | Vegetación densa | Señal alta de vegetación verde y densa |

Los intervalos describen vigor espectral, no tipo de cobertura. Un valor alto no
confirma por sí solo bosque natural, y uno bajo no demuestra por sí solo pérdida
forestal. En la aplicación, cada clase incluye un botón de información accesible
mediante pulsación o teclado.

## Índice ponderado

Cada fuente puede sumar una sola vez:

| Fuente | Peso |
|---|---:|
| JRC TMF | 2.0 |
| Hansen GFC | 2.0 |
| ESRI LULC | 1.5 |
| GEDI | 0.5 |
| NDVI | 0.0 |

La fórmula es:

`puntaje = 2·JRC + 2·Hansen + 1.5·ESRI + 0.5·GEDI`

donde cada variable vale `1` si su señal está activa y `0` en caso contrario. El
puntaje máximo es 6.0. No se suman áreas, píxeles ni subcriterios adicionales al
peso de una misma fuente.

## Reglas de prioridad

| Puntaje | Prioridad |
|---:|---|
| ≥ 3.0 | Alta |
| ≥ 1.5 y < 3.0 | Media |
| ≥ 0.5 y < 1.5 | Preventiva |
| < 0.5 | Baja |

Una señal ESRI aislada produce 1.5 puntos. Una señal JRC aislada produce 2.0 y una
señal Hansen aislada produce 2.0. Por diseño, ESRI nunca aporta más que cualquiera
de las dos fuentes forestales principales.

## Consistencia entre fuentes

La consistencia es una lectura adicional y no modifica el puntaje:

| Lectura | Regla |
|---|---|
| Alta consistencia | JRC TMF, Hansen GFC y ESRI LULC presentan señal de deterioro |
| Consistencia parcial | Exactamente dos de las tres fuentes presentan señal |
| Lectura mixta | Coexisten señales de deterioro y de recuperación o ganancia |
| Sin señal consistente | Menos de dos fuentes principales coinciden en deterioro |

Para evitar que cambios mínimos produzcan una lectura mixta, la recuperación JRC
se filtra con 0.5 ha o 1% del área y la ganancia de árboles ESRI con 0.10 ha y 5%
del área. Son criterios simétricos a los umbrales de cambio usados para esas
fuentes. Las ganancias no compensan ni restan puntos a una señal de deterioro,
porque pueden ocurrir simultáneamente en sectores diferentes de la misma área.

## Trazabilidad

Las constantes y funciones se mantienen en `metodologia_indice.py`. Las pruebas de
`test_metodologia_indice.py` verifican pesos, umbrales, suma única por fuente,
clasificación, consistencia y exclusión de NDVI. El registro JSON conserva fuentes,
períodos, umbrales, justificaciones, pesos, aportes efectivos, estadísticas y reglas
de prioridad y consistencia.
