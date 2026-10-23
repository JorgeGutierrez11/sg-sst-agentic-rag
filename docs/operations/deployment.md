# Guía operativa: despliegue en la VPS

> **Status:** `Current`
> **Audience:** operator
> **Verified against:** `deploy/compose.yaml`, `deploy/.env.example`
> **Last verified:** 2026-10-22
> **Replacement:** N/A

Esta guía despliega el backend y el frontend en la VPS con las imágenes publicadas en GHCR (ver [`docker.md`](docker.md#imagen-publicada-en-ghcr)). El único punto de entrada público es un **Cloudflare Tunnel**: la VPS no abre los puertos 80 ni 443 y ningún contenedor publica puertos en el host. Ejecuta todos los comandos desde `deploy/` dentro del checkout del repositorio en la VPS.

## Arquitectura

```text
navegador ──HTTPS──> Cloudflare (sgsst.gimnasiouis.com)
                         │ túnel saliente
                     cloudflared ──┬── /api/v1/*  ──> backend:8000
                                   └── todo lo demás ─> frontend:3000 ── /api/v1 (proxy interno) ──> backend:8000
```

| Servicio | Imagen | Notas |
|---|---|---|
| `backend` | `ghcr.io/jorgegutierrez11/sg-sst-backend:${BACKEND_TAG}` | Monta el corpus en solo lectura; `/tmp` en tmpfs para la copia de trabajo de Chroma. |
| `frontend` | `ghcr.io/jorgegutierrez11/sg-sst-frontend:${FRONTEND_TAG}` | `SGSST_API_URL=http://backend:8000` para su proxy interno. |
| `cloudflared` | `cloudflare/cloudflared:2026.10.0` | Arranca solo cuando `backend` y `frontend` están `healthy`. |

Las rutas públicas se configuran en el panel de Cloudflare (**Networking → Tunnels → túnel → Routes → Published application**), en este orden:

1. Hostname `sgsst.gimnasiouis.com`, Path `^/api/v1/`, Service URL `http://backend:8000`.
2. Hostname `sgsst.gimnasiouis.com`, Path vacío, Service URL `http://frontend:3000`.

`/docs`, `/openapi.json` y `/health` del backend no son accesibles desde internet porque ninguna ruta pública los incluye.

## Prerrequisitos en la VPS

| Requisito | Detalle |
|---|---|
| Docker Engine y Compose v2 | `docker compose version`. |
| Recursos | Mínimo 4 GB de RAM y 2 vCPU; recomendado 8 GB y 4 vCPU. Unos 7 GB de disco para imágenes. |
| Red | Salida a internet (GHCR, DeepSeek, Cloudflare). No requiere puertos de entrada aparte de SSH. |
| Secretos | Clave de DeepSeek y token del túnel (`eyJ...`, en **Networking → Tunnels → túnel → Overview → Add a replica**). |

## Primer despliegue

```bash
git clone https://github.com/JorgeGutierrez11/sg-sst-agentic-rag.git
cd sg-sst-agentic-rag/deploy
cp .env.example .env
chmod 600 .env
# Completar DEEPSEEK_API_KEY y TUNNEL_TOKEN en .env
docker compose pull
docker compose up -d
docker compose ps          # backend y frontend "healthy"; cloudflared "Up"
```

El corpus publicado está versionado en `data/processed/`, así que el checkout ya lo contiene; `CORPUS_DIR` solo se usa si el corpus vive en otra ruta. El backend tarda hasta unos dos minutos en quedar `healthy`; hasta entonces `cloudflared` no arranca y el hostname responde con el error 1033 (HTTP 530).

## Verificación

```bash
docker compose logs cloudflared | grep -i "registered tunnel connection"
curl -fsS https://sgsst.gimnasiouis.com/ -o /dev/null -w '%{http_code}\n'        # 200 (frontend)
curl -sS https://sgsst.gimnasiouis.com/api/v1/diagnostics/no-existe              # {"detail":"Diagnostic session not found."}
```

## Actualizar o volver a una versión anterior

Las versiones se fijan con tags inmutables `sha-<7>`, nunca con `main`:

```bash
# Editar BACKEND_TAG o FRONTEND_TAG en .env
docker compose pull
docker compose up -d
```

Para volver atrás, restaura el tag anterior en `.env` y repite los dos comandos.

Tras actualizar el corpus con `git pull`, reinicia el backend para que lo cargue: `docker compose restart backend`.

## Limitaciones conocidas

- Cloudflare corta en **100 s** las peticiones que pasan por su proxy (error 524). Una consulta tarda entre 20 y 60 s; varias consultas simultáneas se encolan en el único worker del backend.
- Las sesiones de diagnóstico viven en memoria: se pierden al reiniciar o actualizar el backend.
- No hay autenticación ni rate limiting en la aplicación (Fase 9 de [`plan-docker.md`](../plans/plan-docker.md)).
- Los contenedores no tienen límites de memoria ni CPU; se fijarán tras medir el consumo en la VPS (pico medido del backend: 3.34 GiB).

## Troubleshooting

| Síntoma | Causa probable | Acción |
|---|---|---|
| Error 1033 / HTTP 530 en el hostname | `cloudflared` no está conectado. | `docker compose ps` y `docker compose logs cloudflared`; si espera a `backend`, revisar sus logs. |
| `cloudflared` en estado `restarting`; log `Provided Tunnel token is not valid.` | `TUNNEL_TOKEN` incorrecto. | Copiar de nuevo el token del panel en `.env` y `docker compose up -d`. |
| `required variable ... is missing a value` | Falta una variable en `.env`. | Completar la variable indicada. |
| Error 502 en `/api/v1/*` | Ruta del túnel apunta a un servicio incorrecto o con `https://`. | Verificar en el panel `http://backend:8000` y el orden de las rutas. |
| Backend en estado `restarting`; log con código `3` (`Missing runtime artifact`) | Corpus incompleto en `CORPUS_DIR`; `unless-stopped` lo reinicia indefinidamente y `cloudflared` no arranca. | `docker compose logs backend`; corregir el corpus (ver [`docker.md`](docker.md#troubleshooting)) y `docker compose up -d`. |
