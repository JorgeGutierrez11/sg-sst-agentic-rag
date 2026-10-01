
# Agente 2 — Revisión y trazabilidad del requisito de afiliación

**Estado:** propuesta de diseño pendiente de validación experta.  
**Catálogo analizado:** `res0312-piloto-v6`.  
**Requisito interno:** `res0312_art3_afiliacion_1_10`.

## 1. Propósito

Establecer la correspondencia entre el requisito normativo de afiliación, las
preguntas auxiliares del Agente 2 y las reglas que permitirán presentar un
resultado basado en las declaraciones de la empresa.

Este documento permite decidir qué preguntas conservar, modificar, sustituir
o retirar antes de implementar el flujo definitivo del cuestionario.

Las reglas aquí propuestas **no están implementadas ni validadas**.

## 2. Fuentes y correspondencia con el aplicativo

### Fuente normativa principal

Resolución 0312 de 2019, artículo 3.

- Ítem normativo: Afiliación al Sistema de Seguridad Social Integral.
- Criterio: afiliación a los sistemas de salud, pensión y riesgos laborales
  conforme a la normativa vigente.
- Método de verificación: solicitar soportes de afiliación y del pago
  correspondiente.
- Alcance del piloto: empresas de 1 a 10 trabajadores clasificadas en riesgo I.

Fuente:
https://www.fondoriesgoslaborales.gov.co/wp-content/uploads/2018/09/RESOLUCION-0312-DEL-2019.pdf

### Referencia de presentación en el aplicativo del Ministerio

El aplicativo consultado muestra el ítem `1.1.4`, denominado
«Afiliación al Sistema General de Riesgos Laborales».

Referencia:
https://sgrl.mintrabajo.gov.co/Empresas/ConsultaEstandares/ConsultaCalificacion/700001

**Decisión provisional:** no asignar `1.1.4` al requisito interno de afiliación
integral. Ese código identifica un ítem referido a riesgos laborales y no
representa por sí solo las tres dimensiones que contempla el artículo 3.

La correspondencia definitiva entre los ítems del aplicativo y los requisitos
del catálogo deberá revisarse antes de diseñar el informe final.

## 3. Naturaleza de las preguntas auxiliares

Las nueve preguntas del catálogo v6 son preguntas de elaboración propia.

Hasta ahora no se ha identificado un instrumento publicado que respalde
su redacción exacta. Su justificación preliminar proviene de su relación
con el criterio normativo o con su método de verificación.

No deben presentarse como preguntas oficiales del Ministerio.

**Diferencia fundamental:**

- El criterio normativo establece qué aspecto debe examinarse.
- La pregunta auxiliar recopila información declarada sobre ese aspecto.
- La respuesta no sustituye la revisión de los soportes exigidos por el
  método de verificación.

## 4. Matriz preliminar de las nueve preguntas

| ID de pregunta | Información recopilada | Relación con el requisito | Decisión preliminar |
|---|---|---|---|
| `q_health_affiliation` | Declaración de afiliación a salud. | Criterio: afiliación al sistema de salud. | Conservar; revisar su alcance respecto de las personas trabajadoras a las que corresponda. |
| `q_health_affiliation_support` | Disponibilidad declarada de soportes de afiliación a salud. | Método de verificación: soporte de afiliación. | Conservar provisionalmente; revisar si es necesario preguntar por cada sistema por separado. |
| `q_health_payment_support` | Disponibilidad declarada de comprobantes de pago a salud. | Método de verificación: pago correspondiente. | Revisar: debe distinguirse quién tiene la obligación de realizar y acreditar el aporte en cada situación. |
| `q_pension_affiliation` | Declaración de afiliación a pensión. | Criterio: afiliación al sistema de pensiones. | Conservar; revisar su alcance respecto de las personas trabajadoras a las que corresponda. |
| `q_pension_affiliation_support` | Disponibilidad declarada de soportes de afiliación a pensión. | Método de verificación: soporte de afiliación. | Conservar provisionalmente; revisar posibles redundancias. |
| `q_pension_payment_support` | Disponibilidad declarada de comprobantes de pago a pensión. | Método de verificación: pago correspondiente. | Revisar: la obligación de aporte debe determinarse según el caso, no suponerse para todas las personas por igual. |
| `q_occupational_risk_affiliation` | Declaración de afiliación a riesgos laborales. | Criterio: afiliación al sistema de riesgos laborales. | Conservar; precisar qué personas deben estar cubiertas según su vinculación. |
| `q_occupational_risk_affiliation_support` | Disponibilidad declarada de soportes de afiliación a riesgos laborales. | Método de verificación: soporte de afiliación. | Conservar provisionalmente; revisar posibles redundancias. |
| `q_occupational_risk_payment_support` | Disponibilidad declarada de comprobantes de pago a riesgos laborales. | Método de verificación: pago correspondiente. | Revisar: no atribuir automáticamente a la empresa la obligación de pago en todos los tipos de vinculación. |

**Observación:** la matriz justifica por qué se propuso recopilar cada dato.
No demuestra todavía que estas nueve preguntas sean suficientes para
determinar el resultado del requisito.

## 5. Información necesaria antes de decidir qué preguntas aplican

El perfil empresarial actual contiene el número de trabajadores y la clase
de riesgo de la empresa. Esos datos permiten seleccionar el conjunto inicial
de requisitos del piloto, pero no bastan para resolver todas las situaciones
individuales de afiliación y aportes.

Antes de definir omisiones o excepciones, se debe revisar si el cuestionario
necesita conocer información adicional, como la modalidad de vinculación de
las personas trabajadoras y la existencia de situaciones particulares que
afecten la obligación de afiliación o pago.

Las posibles excepciones deberán tener un fundamento normativo específico.
Una respuesta «No» o «No sé» no demuestra por sí sola que una obligación
no sea aplicable.

## 6. Flujo condicional propuesto

### 6.1. Pregunta de afiliación

Para cada sistema de seguridad social:

- Si la empresa declara «Sí», continuar con las preguntas necesarias para
  conocer la situación de los soportes y aportes correspondientes.
- Si declara «No», registrar la declaración negativa y revisar si hacen falta
  preguntas para precisar a qué personas afecta y cuál es la obligación
  aplicable. No pedir automáticamente soportes de una afiliación que la
  empresa acaba de declarar inexistente.
- Si responde «No sé» o no responde, registrar información insuficiente.
  No convertir la incertidumbre en una respuesta negativa.

### 6.2. Preguntas sobre soportes

Las preguntas sobre soportes deben mostrarse cuando sean pertinentes para
la situación declarada.

Si una pregunta se omite, el resultado debe registrar:

1. Identificador de la pregunta omitida.
2. Regla que produjo la omisión.
3. Respuesta o dato empresarial que activó esa regla.
4. Motivo legible para el usuario o para el registro de auditoría.

**Una pregunta auxiliar omitida no significa que el requisito normativo
principal «No aplica».**

### 6.3. Casos particulares

Si falta información para establecer si corresponde una afiliación o un
aporte, el agente debe solicitar una aclaración o conservar el estado
«Información insuficiente».

No debe inferir excepciones únicamente a partir del tamaño de la empresa
o de su clasificación de riesgo.

## 7. Interpretación del requisito en el informe

El objetivo de presentación acordado es utilizar las categorías:

- «Cumple según declaración».
- «No cumple según declaración».
- «No aplica».

Para impedir conclusiones infundadas, el diseño también debe permitir
«Información insuficiente» cuando no sea posible determinar un resultado.

### Reglas preliminares pendientes de validación

**Cumple según declaración:** solo podrá emitirse si las respuestas
necesarias, las condiciones de aplicabilidad y las reglas aprobadas permiten
sostener ese resultado. Debe quedar visible que los soportes no fueron
revisados.

**No cumple según declaración:** solo podrá emitirse cuando la empresa
declare una situación incompatible con una obligación que efectivamente
le resulte aplicable. Deben identificarse las respuestas que originaron
el resultado.

**No aplica:** solo podrá emitirse cuando una regla de aplicabilidad
fundamentada permita excluir el requisito para el caso concreto. Deben
registrarse la norma y los datos utilizados para tomar esa decisión.

**Información insuficiente:** se utiliza cuando faltan respuestas, existen
ambigüedades o no está determinada la aplicabilidad necesaria para resolver
el requisito.

Estas reglas describen la intención del diseño, no un resultado autorizado
por el motor actual.

## 8. Aspectos que debe revisar el experto en SST

Para este requisito se solicitará al experto determinar:

1. Si las preguntas cubren los aspectos necesarios del criterio.
2. Si alguna pregunta es redundante o debe retirarse.
3. Si hacen falta preguntas para distinguir situaciones de vinculación,
   afiliación y aportes.
4. Si las reglas de aplicabilidad y omisión están suficientemente
   justificadas.
5. Si las combinaciones de respuestas permiten obtener las categorías
   propuestas para el informe, sin una inferencia indebida.
6. Qué casos deben producir «Información insuficiente» o quedar sujetos
   a verificación posterior.

Cada observación debe asociarse con el requisito, la pregunta o la regla
correspondiente, e indicar si se acepta, se modifica o se rechaza.

## 9. Decisiones pendientes

- Confirmar la correspondencia del requisito integral con la presentación
  de los ítems del aplicativo del Ministerio.
- Buscar instrumentos confiables con preguntas reutilizables para este
  requisito y registrar cuáles son textuales y cuáles son propias.
- Determinar qué información adicional exige la aplicabilidad por persona.
- Decidir si las nueve preguntas actuales se mantienen o se reorganizan.
- Definir y validar las reglas que transformarán las respuestas en el estado
  mostrado en el informe.
- Implementar el registro de preguntas omitidas y sus motivos.
- Someter el instrumento y sus reglas a revisión experta.
