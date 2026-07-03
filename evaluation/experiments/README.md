# evaluation/experiments/

Un archivo de config (yaml/json) por corrida: etapa + técnica candidata.
Ejemplo: etapa2_tecnica_a.yaml, etapa2_tecnica_b.yaml, etapa2_tecnica_c.yaml

Cada config referencia el commit/tag de agents/consulta_normativa/ evaluado
y guarda el resultado ARES correspondiente (relevancia contexto, fidelidad,
relevancia respuesta + intervalos de confianza).

Así se compara qué técnica ganó en cada etapa SIN duplicar código en carpetas.
