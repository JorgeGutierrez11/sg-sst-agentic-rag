# Propuesta de diseño del Agente 2 — Diagnóstico asistido de cumplimiento SG-SST

## 1. Objetivo de este documento

Este documento resume la propuesta actual para el **segundo agente del sistema**, encargado de realizar un **diagnóstico asistido del estado del SG-SST** de una MiPyme colombiana de **clase de riesgo I**, a partir de información declarada por el usuario.

El objetivo es que el equipo pueda revisar y aprobar —o rechazar y modificar— las siguientes decisiones:

- alcance funcional del agente;
- fundamento normativo de la evaluación;
- forma de construir las preguntas;
- flujo de interacción;
- entradas requeridas;
- reglas de evaluación;
- estructura del informe final;
- limitaciones del diagnóstico;
- decisiones técnicas pendientes.

---

# 2. Resumen ejecutivo

El Agente 2 no se plantea como un auditor, abogado ni certificador del cumplimiento del SG-SST.

Se plantea como un **asistente de autoevaluación** que:

1. identifica el perfil de la empresa;
2. determina qué Estándares Mínimos del SG-SST le son aplicables;
3. formula preguntas derivadas de los criterios oficiales;
4. recopila información declarada por el usuario;
5. contrasta esa información con los criterios normativos;
6. calcula el resultado conforme a reglas determinísticas;
7. identifica incumplimientos o información insuficiente;
8. genera recomendaciones y un plan de mejoramiento orientativo;
9. produce un informe final en PDF.

El resultado debe presentarse explícitamente como:

> **Diagnóstico orientativo basado en información declarada por la empresa.**

No constituye auditoría, certificación, concepto jurídico ni reemplaza la evaluación de un profesional competente en Seguridad y Salud en el Trabajo.

---

# 3. Fundamento normativo y fuentes de autoridad

La lógica del diagnóstico no debe ser inventada por el equipo ni decidida libremente por el LLM.

La base principal debe ser la **Resolución 0312 de 2019 del Ministerio del Trabajo**, que define los Estándares Mínimos del SG-SST.

## 3.1 Resolución 0312 de 2019

Fuente oficial:

https://www.fondoriesgoslaborales.gov.co/wp-content/uploads/2018/09/RESOLUCION-0312-DEL-2019.pdf

La resolución define, entre otros elementos:

- Estándares Mínimos del SG-SST.
- Criterios según número de trabajadores y clase de riesgo.
- Tabla de valores y calificación.
- Forma de evaluación.
- Clasificación del resultado.
- Requisitos del plan de mejoramiento.

Esta debe ser la **fuente normativa principal del Agente 2**.

---

## 3.2 Sistema oficial de calificación de Estándares Mínimos

El Ministerio del Trabajo dispone de un sistema donde se visualizan los ítems evaluados, su peso y los estados:

- Cumple totalmente.
- No cumple.
- No aplica.

Fuente oficial:

https://sgrl.mintrabajo.gov.co/Empresas/ConsultaEstandares/ConsultaCalificacion/700001

El sistema muestra ejemplos como:

- 2.1.1 Política SG-SST.
- 2.2.1 Objetivos SG-SST.
- 2.3.1 Evaluación inicial.
- 2.4.1 Plan anual de trabajo.
- 2.7.1 Matriz legal.
- 2.10.1 Evaluación y selección de proveedores.
- entre otros.

Esto sirve como referencia para estructurar el modelo interno de evaluación del agente.

---

## 3.3 Circular 0027 de 2026

Fuente oficial:

https://www.fondoriesgoslaborales.gov.co/wp-content/uploads/2026/03/Circular-0027.pdf

La Circular 0027 del 26 de febrero de 2026 mantiene vigente la obligación de realizar y registrar la **autoevaluación de Estándares Mínimos** y el correspondiente **plan de mejoramiento**, en los términos de la Resolución 0312 de 2019.

Esto permite justificar que la autoevaluación sigue siendo relevante y vigente en 2026.

---

# 4. Alcance del Agente 2

## Incluido

El agente cubrirá:

- MiPymes colombianas.
- Clase de riesgo I.
- Cualquier número de trabajadores dentro del alcance MiPyme.
- Diagnóstico SG-SST basado en Estándares Mínimos aplicables.
- Interacción conversacional.
- Evaluación basada principalmente en información declarada.
- Generación de diagnóstico.
- Identificación de incumplimientos.
- Recomendaciones.
- Plan de mejoramiento orientativo.
- Informe final en PDF.

## Fuera de alcance

El agente no debe presentarse como:

- auditor oficial;
- inspector del trabajo;
- abogado;
- consultor jurídico;
- certificador de cumplimiento;
- sustituto de un profesional SST;
- mecanismo oficial de reporte ante el Ministerio del Trabajo.

Tampoco debe requerir obligatoriamente que el usuario suba documentación sensible para poder finalizar la evaluación.

---

# 5. Perfil inicial de la empresa

Antes de iniciar el diagnóstico, el agente debe construir un perfil mínimo.

## Entrada mínima

- actividad económica;
- código CIIU, si está disponible;
- número de trabajadores;
- clase de riesgo;
- información básica necesaria para determinar aplicabilidad.

Dado el alcance actual:

```text
risk_class = I
```

El número de trabajadores será una variable crítica para determinar qué grupo de estándares aplicar.

---

# 6. Determinación de estándares aplicables

El agente no debe hacer las mismas preguntas a todas las empresas.

La Resolución 0312 de 2019 establece distintos conjuntos de Estándares Mínimos según características de la organización.

Flujo conceptual:

```text
Perfil empresarial
        |
        v
Número de trabajadores
        |
        v
Reglas de aplicabilidad
        |
        v
Estándares aplicables
        |
        v
Cuestionario correspondiente
```

Para el alcance del proyecto se debe construir un **motor de aplicabilidad** que reciba el perfil de la empresa y devuelva únicamente los criterios que le corresponden.

Esta lógica debe ser determinística y trazable.

No debería depender de una decisión libre del LLM.

---

# 7. Cómo deben construirse las preguntas

Las preguntas no deberían redactarse primero y después buscar cómo relacionarlas con la normativa.

El flujo correcto debe ser:

```text
Resolución 0312
      |
      v
Estándar / ítem
      |
      v
Criterio oficial
      |
      v
Modo de verificación
      |
      v
Condiciones mínimas del criterio
      |
      v
Preguntas conversacionales
```

## Ejemplo conceptual

Un error sería preguntar únicamente:

> ¿Cuenta con un Plan Anual de Trabajo?

Una respuesta afirmativa no permite determinar si realmente se cumplen los elementos del criterio.

Debería descomponerse en preguntas más concretas, por ejemplo:

- ¿Cuenta actualmente con un Plan Anual de Trabajo del SG-SST?
- ¿Corresponde al periodo vigente?
- ¿Incluye objetivos?
- ¿Incluye metas?
- ¿Define responsables?
- ¿Establece recursos?
- ¿Incluye un cronograma?

El agente sigue confiando en la declaración del usuario, pero recopila suficiente información para realizar un contraste razonable con el criterio normativo.

---

# 8. Principio de información declarada

El proyecto no debe asumir que los usuarios estarán dispuestos a subir documentos internos, datos de trabajadores, historias clínicas, contratos u otra evidencia sensible.

Por tanto, el flujo principal debe funcionar sin carga documental.

El agente evaluará principalmente:

> **Información declarada por el usuario durante la conversación.**

Esto implica que el informe debe evitar expresiones como:

- “cumplimiento certificado”;
- “cumplimiento verificado”;
- “la empresa cumple legalmente”;
- “auditoría aprobada”.

En su lugar deben utilizarse expresiones como:

- “cumplimiento declarado”;
- “no cumplimiento declarado”;
- “según la información suministrada”;
- “información insuficiente para determinar el estado”.

---

# 9. Estados internos de evaluación

No se recomienda representar cada criterio únicamente como:

```text
true / false
```

Se propone utilizar como mínimo:

```text
DECLARED_COMPLIANT
DECLARED_NON_COMPLIANT
INSUFFICIENT_INFORMATION
NOT_APPLICABLE
```

Equivalencia para presentación:

| Estado interno | Presentación al usuario |
|---|---|
| DECLARED_COMPLIANT | Cumplimiento declarado |
| DECLARED_NON_COMPLIANT | No cumplimiento declarado |
| INSUFFICIENT_INFORMATION | Información insuficiente |
| NOT_APPLICABLE | No aplica |

Esto evita que el sistema afirme un cumplimiento que realmente no pudo comprobar externamente.

---

# 10. Separación de responsabilidades: reglas vs. LLM

Esta separación es crítica.

## El LLM puede encargarse de

- conversar con el usuario;
- reformular preguntas;
- adaptar lenguaje técnico;
- detectar respuestas ambiguas;
- solicitar aclaraciones;
- extraer información estructurada;
- explicar resultados;
- redactar hallazgos;
- redactar recomendaciones;
- generar el texto narrativo del informe.

## El LLM no debería decidir libremente

- qué estándar aplica;
- cuánto vale un ítem;
- cómo se calcula el puntaje;
- qué clasificación corresponde a un porcentaje;
- si se modifica una regla oficial;
- cuál es la fórmula de evaluación.

Estas decisiones deben estar gobernadas por reglas determinísticas derivadas de fuentes oficiales.

---

# 11. Flujo propuesto del agente

```text
INICIO
  |
  v
Recopilar perfil empresarial
  |
  v
Validar alcance del proyecto
  |
  v
Determinar estándares aplicables
  |
  v
Construir / seleccionar cuestionario
  |
  v
Realizar preguntas al usuario
  |
  v
Interpretar respuestas
  |
  v
¿Información suficiente?
  |                |
  | Sí             | No
  v                v
Evaluar criterio   Solicitar aclaración
  |                |
  +-------<--------+
  |
  v
Guardar resultado por criterio
  |
  v
¿Quedan criterios?
  |           |
  | Sí        | No
  |           v
  +------  Calcular resultado
              |
              v
       Identificar brechas
              |
              v
       Generar recomendaciones
              |
              v
       Construir plan de mejora
              |
              v
       Generar informe final
              |
              v
             FIN
```

---

# 12. Modelo de datos conceptual por criterio

Se propone construir una matriz maestra de evaluación.

Ejemplo conceptual:

```yaml
criterion_id: "2.4.1"

source:
  regulation: "Resolución 0312 de 2019"
  article: "..."

applicability:
  risk_classes:
    - I
  worker_ranges:
    - "..."

criterion:
  name: "Plan anual de trabajo"
  official_text: "..."

verification_method:
  official_text: "..."

questions:
  - id: "2.4.1_q1"
    text: "¿Cuenta actualmente con un Plan Anual de Trabajo del SG-SST?"
    type: boolean

  - id: "2.4.1_q2"
    text: "¿El plan incluye objetivos y metas?"
    type: boolean

decision_rule:
  type: "all_required"

score:
  official_value: 2.0

output:
  compliant_state: "DECLARED_COMPLIANT"
  non_compliant_state: "DECLARED_NON_COMPLIANT"
```

La redacción final y los campos exactos deberán definirse después de extraer los criterios oficiales.

---

# 13. Cálculo del resultado

El cálculo debe seguir la estructura de valores establecida oficialmente.

El LLM no debe producir porcentajes por intuición.

La salida cuantitativa debe ser producto de:

```text
criterios aplicables
        +
estado de cada criterio
        +
valor oficial del criterio
        =
resultado
```

La Resolución 0312 de 2019 establece además una interpretación del resultado general.

De forma general:

- menor a 60 %: **Crítico**;
- entre 60 % y 85 %: **Moderadamente aceptable**;
- mayor a 85 %: **Aceptable**.

La implementación exacta debe validarse contra el texto normativo antes de codificarse.

---

# 14. Salida propuesta

Nombre provisional:

> **Informe de diagnóstico orientativo del SG-SST**

Subtítulo sugerido:

> Autoevaluación asistida de Estándares Mínimos basada en información declarada por la empresa.

No se recomienda utilizar como título principal:

> Auditoría SG-SST

porque podría dar a entender que el sistema realiza una auditoría formal.

---

# 15. Estructura propuesta del informe final

## 1. Identificación de la empresa

- actividad económica;
- CIIU;
- número de trabajadores;
- clase de riesgo;
- fecha de evaluación.

## 2. Alcance del diagnóstico

- propósito de la evaluación;
- estándares evaluados;
- fundamento normativo;
- aclaración de que se basa en información declarada.

## 3. Resultado general

Ejemplo:

```text
Resultado global: 72 %

Clasificación:
MODERADAMENTE ACEPTABLE
```

## 4. Resultados por estándar o grupo

Tabla sugerida:

| Ítem | Estándar | Estado | Puntaje |
|---|---|---|---|
| X.X.X | ... | Cumplimiento declarado | ... |
| X.X.X | ... | No cumplimiento declarado | ... |
| X.X.X | ... | Información insuficiente | ... |

## 5. Fortalezas identificadas

Criterios en los que la información suministrada evidencia un estado favorable.

## 6. Brechas o hallazgos

Cada hallazgo debería incluir como mínimo:

- ítem;
- criterio;
- estado;
- información suministrada;
- motivo del resultado;
- referencia normativa.

## 7. Recomendaciones

Recomendaciones orientativas derivadas de los incumplimientos detectados.

## 8. Plan de mejoramiento

Campos mínimos propuestos:

- ítem relacionado;
- actividad de mejora;
- responsable;
- plazo;
- recursos necesarios;
- soporte o evidencia esperada;
- estado de seguimiento.

## 9. Conclusión general

Resumen narrativo del estado reportado de la empresa.

## 10. Fuentes normativas

Listado de normas y fuentes oficiales utilizadas.

## 11. Limitaciones y descargo

Texto propuesto:

> Los resultados presentados corresponden a una autoevaluación asistida construida a partir de la información declarada por el usuario. El informe tiene carácter orientativo y no constituye una auditoría, certificación de cumplimiento, concepto jurídico ni reemplaza la evaluación de un profesional competente en Seguridad y Salud en el Trabajo.

---

# 16. De dónde surge esta estructura de salida

La estructura propuesta combina tres fuentes:

## Elementos derivados de normativa oficial

- Estándares aplicables.
- Criterios de evaluación.
- Valores y calificación.
- Clasificación del resultado.
- Plan de mejoramiento.

Fuente principal:

Resolución 0312 de 2019.

## Elementos observados en herramientas oficiales

- organización por estándares;
- valor por ítem;
- estados de cumplimiento;
- total de calificación.

Fuente:

Sistema General de Riesgos Laborales del Ministerio del Trabajo.

## Elementos de diseño propios del proyecto

- resumen ejecutivo;
- fortalezas;
- presentación de brechas;
- explicaciones en lenguaje natural;
- organización visual del PDF;
- recomendaciones;
- estructura conversacional.

Estos elementos son diseño del sistema y no deben presentarse como requisitos literales de la norma.

---

# 17. Relación entre preguntas e informe final

Una decisión importante es que **cada pregunta debe existir porque alimenta un criterio específico del informe**.

No deberían existir preguntas que después no influyan en ninguna evaluación.

Tampoco debería existir un resultado en el PDF que no pueda rastrearse hasta:

```text
Resultado
   |
   v
Criterio evaluado
   |
   v
Respuesta(s) del usuario
   |
   v
Pregunta(s)
   |
   v
Fuente normativa
```

Esto permite trazabilidad y facilita justificar académicamente el diseño.

---

# 18. Trazabilidad requerida

Por cada resultado debería ser posible conocer:

- qué estándar se evaluó;
- qué norma lo sustenta;
- qué preguntas se hicieron;
- qué respondió el usuario;
- qué regla se aplicó;
- qué puntaje resultó;
- qué recomendación se generó.

Ejemplo:

```text
Ítem 2.4.1
       |
       +-- Fuente: Resolución 0312 de 2019
       |
       +-- Preguntas: q1, q2, q3...
       |
       +-- Respuestas: sí, sí, no...
       |
       +-- Regla aplicada
       |
       +-- Resultado: NO CUMPLIMIENTO DECLARADO
       |
       +-- Puntaje
       |
       +-- Hallazgo
       |
       +-- Acción de mejora
```

---

# 19. Riesgos del diseño

## 19.1 Aceptar un “sí” como evidencia suficiente

Una sola pregunta demasiado general puede producir falsos positivos.

Mitigación:

- descomponer criterios complejos;
- hacer preguntas sobre condiciones concretas.

## 19.2 Cuestionario demasiado largo

Descomponer todos los criterios excesivamente puede producir una experiencia inviable.

Mitigación:

- preguntas condicionales;
- branching;
- reutilización de información ya suministrada;
- agrupar preguntas cuando no se pierda precisión.

## 19.3 LLM tomando decisiones normativas

Puede producir resultados inconsistentes.

Mitigación:

- reglas determinísticas;
- matriz de criterios;
- valores oficiales.

## 19.4 Sobreafirmar el resultado

El sistema no verifica documentos ni realiza inspección física.

Mitigación:

- estados explícitos de “cumplimiento declarado”;
- descargo visible;
- evitar lenguaje de certificación.

## 19.5 Información desactualizada

La normativa puede cambiar.

Mitigación:

- corpus normativo versionado;
- fecha de vigencia por norma;
- referencias oficiales;
- mecanismo para actualizar criterios.

---

# 20. Decisiones técnicas pendientes

Estas decisiones deben discutirse antes de implementar completamente el agente.

### 1. Granularidad de las preguntas

¿Cuántas preguntas son suficientes para evaluar razonablemente cada criterio sin generar una interacción demasiado larga?

### 2. Información insuficiente

¿Cómo afecta al puntaje un criterio donde el usuario no sabe responder?

No debería asumirse automáticamente que “no sabe” equivale a “no cumple” sin justificarlo normativamente.

### 3. “No aplica”

Debe definirse cuándo puede utilizarse y bajo qué reglas.

No debe permitir que el usuario elimine arbitrariamente un criterio del cálculo.

### 4. Recomendaciones

Definir si:

- serán plantillas determinísticas por criterio;
- serán generadas por LLM sobre una base normativa;
- o se utilizará un enfoque híbrido.

### 5. Plan de mejoramiento

Definir qué campos debe diligenciar el sistema automáticamente y cuáles debe dejar al usuario.

### 6. Persistencia

Definir cómo se almacenará el progreso para permitir evaluaciones largas en varias sesiones.

### 7. Reanudación de diagnóstico

Definir si un usuario puede continuar una evaluación incompleta posteriormente.

---

# 21. Arquitectura lógica preliminar

```text
                    +-----------------------+
                    | Perfil empresarial    |
                    +-----------+-----------+
                                |
                                v
                    +-----------------------+
                    | Applicability Engine  |
                    +-----------+-----------+
                                |
                                v
                    +-----------------------+
                    | Question Planner      |
                    +-----------+-----------+
                                |
                                v
                    +-----------------------+
                    | Agente conversacional |
                    +-----------+-----------+
                                |
                                v
                    +-----------------------+
                    | Structured Answers    |
                    +-----------+-----------+
                                |
                                v
                    +-----------------------+
                    | Compliance Engine     |
                    | reglas deterministas  |
                    +-----------+-----------+
                                |
                 +--------------+---------------+
                 |                              |
                 v                              v
        +----------------+             +-------------------+
        | Score Engine   |             | Finding Generator |
        +--------+-------+             +---------+---------+
                 |                               |
                 +---------------+---------------+
                                 |
                                 v
                      +----------------------+
                      | Improvement Planner  |
                      +----------+-----------+
                                 |
                                 v
                      +----------------------+
                      | Report Generator     |
                      +----------------------+
```

---

# 22. Próximo paso recomendado

Antes de implementar el flujo completo, construir una **Matriz Maestra de Evaluación**.

Cada fila debe representar un criterio normativo y contener, como mínimo:

| Campo | Descripción |
|---|---|
| ID | Identificador del estándar |
| Norma | Fuente normativa |
| Artículo | Ubicación |
| Aplicabilidad | Empresas a las que aplica |
| Criterio | Texto normativo |
| Modo de verificación | Referencia oficial |
| Valor | Peso oficial |
| Preguntas | Preguntas necesarias |
| Tipo de respuesta | Sí/no, opción múltiple, fecha, cantidad, etc. |
| Regla | Cómo se determina el resultado |
| Estado | Estados posibles |
| Recomendación | Acción orientativa |
| Fuente | URL oficial |

Una vez construida esta matriz:

```text
Matriz
   |
   +--> genera cuestionario
   |
   +--> gobierna cálculo
   |
   +--> explica hallazgos
   |
   +--> alimenta recomendaciones
   |
   +--> alimenta PDF
```

La matriz debería ser considerada el **núcleo del Agente 2**.

---

# 23. Puntos que el equipo debe aprobar o rechazar

Para cerrar el diseño inicial, se propone que el equipo responda explícitamente:

- [ ] ¿Estamos de acuerdo con definir el agente como una **autoevaluación asistida** y no como auditoría?
- [ ] ¿Estamos de acuerdo con que el alcance sea MiPymes de riesgo I independientemente del número de trabajadores?
- [ ] ¿Estamos de acuerdo con utilizar la Resolución 0312 de 2019 como base principal de evaluación?
- [ ] ¿Estamos de acuerdo con que la evaluación funcione sin exigir documentos?
- [ ] ¿Estamos de acuerdo con utilizar “cumplimiento declarado” en lugar de “cumplimiento verificado”?
- [ ] ¿Estamos de acuerdo con separar decisiones normativas determinísticas del LLM?
- [ ] ¿Estamos de acuerdo con construir primero la matriz de criterios antes de implementar el cuestionario?
- [ ] ¿Estamos de acuerdo con la estructura propuesta del informe PDF?
- [ ] ¿Qué campos del plan de mejoramiento deben ser generados automáticamente?
- [ ] ¿Cómo debe tratarse la respuesta “no sé”?
- [ ] ¿Cómo se manejará “no aplica”?
- [ ] ¿Cuál será el máximo razonable de preguntas por sesión?

---

# 24. Conclusión de diseño

La propuesta consiste en construir el Agente 2 como un **asistente conversacional de autoevaluación del SG-SST**.

La lógica de cumplimiento debe estar respaldada por la Resolución 0312 de 2019 y reglas explícitas; el LLM debe facilitar la interacción, estructurar respuestas y explicar resultados, pero no sustituir la lógica normativa.

La salida final será un **diagnóstico orientativo basado en información declarada por la empresa**, acompañado por brechas, recomendaciones y un plan de mejoramiento.

La prioridad antes de implementar el agente completo debe ser construir y validar la **Matriz Maestra de Evaluación**, porque de ella dependerán tanto las preguntas como el cálculo y el informe final.
