# Rúbricas de validación experta en SST — Actividad 2

## Objetivo general

Validar el comportamiento funcional y técnico-normativo de los dos agentes mediante **casos de prueba ejecutados directamente por un experto en SST** en el prototipo web. 
## Procedimiento

1. Definir escenarios representativos y casos límite para cada agente, con identificador, datos de entrada, pasos y resultado esperado, antes de ejecutar la prueba.
2. El experto ejecutará cada caso en la interfaz web y registrará las salidas obtenidas, incluyendo referencias normativas o informe generado, cuando corresponda.
3. Comparará el resultado real con el resultado esperado y aplicará la rúbrica correspondiente **al caso completo**.
4. Documentará fallos, evidencias y recomendaciones. Cuando un criterio no sea observable o no corresponda al escenario, se marcará **N/E (no evaluable)** y se excluirá del denominador; no se calificará arbitrariamente con cero.

**Control:** los resultados esperados deben estar fundamentados en la normativa aplicable y ser revisados por el experto. Un caso puede incluir varias preguntas, pasos o decisiones; su valoración no equivale a promediar respuestas individuales.

## Escala de valoración

| Puntaje | Interpretación |
|---:|---|
| 0 | Incorrecto / incumple el criterio |
| 1 | Presenta deficiencias importantes |
| 2 | Adecuado, pero presenta deficiencias menores |
| 3 | Correcto y completo |
| N/E | No evaluable en este caso; no se incluye en el puntaje máximo aplicable |

---

# Rúbrica A — Agente 1: Consulta normativa

## Objetivo específico

Comprobar que el agente resuelve **escenarios de consulta normativa** de principio a fin, incluyendo consultas contextualizadas, solicitudes de aclaración y situaciones de información insuficiente.


## Criterios de evaluación por caso

| Criterio | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **Resolución del escenario** | No resuelve el objetivo del caso. | Resuelve solo una parte menor o falla en pasos esenciales. | Resuelve el objetivo con omisiones menores. | Resuelve todos los pasos y el objetivo esperado del caso. |
| **Exactitud normativa** | El resultado del caso contradice la normativa. | Contiene errores normativos importantes. | Es esencialmente correcto, con imprecisiones menores. | Las conclusiones del caso son normativamente correctas. |
| **Pertinencia y aplicabilidad** | Aplica requisitos ajenos al escenario. | Omite requisitos esenciales o interpreta mal el perfil. | Aplica correctamente los requisitos principales, con omisiones menores. | Aplica correctamente la normativa al perfil y las condiciones del caso. |
| **Sustento y trazabilidad** | No existe sustento verificable para las conclusiones. | El sustento es insuficiente o contiene referencias erróneas importantes. | La mayoría de las conclusiones tiene soporte adecuado. | Las conclusiones relevantes se sustentan en referencias pertinentes y verificables. |
| **Continuidad y coherencia del flujo** | Pierde información esencial o se contradice entre pasos. | Presenta inconsistencias importantes durante el caso. | Mantiene el flujo con inconsistencias menores. | Conserva correctamente los datos y responde coherentemente a lo largo del caso. |
| **Manejo de incertidumbre y límites** | Inventa conclusiones ante información insuficiente o fuera de alcance. | Reconoce parcialmente los límites, pero emite conclusiones injustificadas. | Maneja la incertidumbre con deficiencias menores. | Solicita aclaraciones o limita la respuesta correctamente cuando corresponde. |

## Puntaje

- **Máximo:** 18 puntos por caso, si los seis criterios son evaluables.
- **Porcentaje del caso:** (puntos obtenidos / [3 × número de criterios evaluables]) × 100.
- Informar los criterios N/E y no comparar puntajes brutos con denominadores diferentes.

---

# Rúbrica B — Agente 2: Diagnóstico de cumplimiento

## Objetivo específico

Comprobar el **flujo completo de diagnóstico** desde la definición del perfil empresarial y la respuesta al cuestionario hasta la matriz de estándares, la calificación y el informe final, según la información declarada.


## Criterios de evaluación por caso

| Criterio | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **Ejecución del flujo y manejo del perfil** | El caso no puede completarse o acepta un perfil que debía rechazarse. | Presenta fallos importantes de navegación, validación o continuidad. | Completa el flujo con deficiencias menores. | Ejecuta correctamente los pasos previstos y valida el perfil según el alcance. |
| **Selección y aplicabilidad de estándares** | Selecciona requisitos incompatibles o excluye requisitos obligatorios. | Presenta errores importantes de aplicabilidad. | La selección es correcta salvo omisiones menores. | Selecciona los estándares correspondientes al perfil y trata correctamente los no aplicables. |
| **Interpretación de las respuestas declaradas** | Los estados contradicen los datos introducidos. | Existen inconsistencias importantes en los estados asignados. | Los estados son mayoritariamente coherentes, con errores menores. | Los estados se derivan correctamente de las respuestas del caso. |
| **Tratamiento de información insuficiente** | Asume estados concluyentes sin datos suficientes. | Maneja incorrectamente varias respuestas incompletas. | Reconoce la insuficiencia con deficiencias menores. | Identifica y comunica correctamente las situaciones de información insuficiente. |
| **Cálculo y valoración normativa** | Puntaje o valoración final incorrectos. | Errores importantes en pesos, no aplicabilidad o clasificación. | Cálculo y valoración correctos con deficiencias menores de presentación. | Puntaje, tratamiento de no aplicabilidad y valoración final corresponden a la normativa y a los datos del caso. |
| **Informe final y trazabilidad** | El informe es incorrecto, no se genera cuando corresponde o no permite verificar el resultado. | Omite información esencial o contiene errores importantes. | Refleja el diagnóstico con omisiones menores. | Refleja fielmente perfil, requisitos, estados, puntaje, valoración y fundamentos normativos. |

## Puntaje

- **Máximo:** 18 puntos por caso, si los seis criterios son evaluables.
- **Porcentaje del caso:** (puntos obtenidos / [3 × número de criterios evaluables]) × 100.
- En casos de rechazo de perfiles fuera de alcance, los criterios sobre calificación e informe pueden ser N/E.

---

# Registro de ejecución de casos

| Campo | Registro |
|---|---|
| ID del caso | |
| Agente | |
| Escenario y objetivo | |
| Perfil empresarial / precondiciones | |
| Datos de entrada y pasos ejecutados | |
| Resultado esperado y fundamento normativo | |
| Resultado real / evidencia | |
| Puntuación por criterio y N/E | |
| Total obtenido / máximo aplicable | |
| Fallos detectados y severidad | |
| Observaciones del experto | |

