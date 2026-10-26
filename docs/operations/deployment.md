# Guía operativa: despliegue en la VPS

> **Status:** `Current`
> **Audience:** operator
> **Verified against:** `deploy/compose.yaml`, `deploy/.env.example`, despliegue en la VPS del 2026-10-23
> **Last verified:** 2026-10-23
> **Replacement:** N/A

Esta guía despliega el backend y el frontend en la VPS con las imágenes publicadas en GHCR (ver [`docker.md`](docker.md#imagen-publicada-en-ghcr)). El único punto de entrada público es un **Cloudflare Tunnel**: la VPS no abre los puertos 80 ni 443 y ningún contenedor publica puertos en el host. Tras la instalación, los comandos de `docker compose` se ejecutan desde `deploy/` dentro del checkout del repositorio en la VPS.

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

## Prerrequisitos

| Requisito | Detalle |
|---|---|
| Imágenes publicadas | `sg-sst-backend` y `sg-sst-frontend` públicas en GHCR con el tag `sha-<7>` que se va a desplegar (workflow `image` en verde sobre `main`). |
| Repositorio | `deploy/` mergeado en `main`. |
| VPS | Ubuntu o Debian con acceso SSH; 8 GB de RAM (los límites suman 5.75 GB) y al menos 2 vCPU (4 vCPU reducen la latencia); unos 10 GB de disco libre. Verificado en una VPS de 2 vCPU, 8 GB de RAM y 100 GB de disco. |
| Red | Salida a internet (GHCR, DeepSeek, Cloudflare). No requiere puertos de entrada aparte de SSH. |
| Cuentas | Dominio en Cloudflare y clave de la API de DeepSeek. |

## Despliegue manual paso a paso

Procedimiento ejecutado en el primer despliegue (2026-10-23). Los pasos 1 y 2 se hacen una sola vez en el panel de Cloudflare; los pasos 3 a 10, en la VPS.

### 1. Crear el túnel en Cloudflare

1. En el panel de Cloudflare: **Networking → Tunnels → Create a tunnel**, tipo **Cloudflared**, nombre `sg-sst`.
2. Elegir **Docker** como entorno y copiar el token: la cadena que empieza con `eyJ` después de `--token`. **No ejecutar** el comando que muestra el panel; `cloudflared` corre dentro del Compose.
3. Si el panel exige un conector activo para continuar, salir de esa pantalla: las rutas se agregan después desde la pestaña **Routes** del túnel.

El token se recupera en cualquier momento en **Networking → Tunnels → túnel → Overview → Add a replica**. Quien lo tenga puede conectar el túnel: guardarlo solo en `deploy/.env` de la VPS.

### 2. Publicar las rutas del túnel

Dentro del túnel (no en el menú general **Networking → Routes**, que solo ofrece rutas privadas): pestaña **Routes → Add route → Published application**. Crear dos rutas con el mismo hostname, **en este orden**:

| # | Subdomain | Domain | Path | Service URL |
|---|---|---|---|---|
| 1 | `sgsst` | `gimnasiouis.com` | `^/api/v1/` | `http://backend:8000` |
| 2 | `sgsst` | `gimnasiouis.com` | (vacío) | `http://frontend:3000` |

- La primera ruta que coincide gana: la de `/api/v1/` debe quedar primero.
- El Service URL usa `http`: el tráfico entre contenedores es HTTP plano y Cloudflare termina el HTTPS.
- Cloudflare crea el registro DNS del hostname. Si ya existe un registro A o CNAME con ese nombre, la ruta no se guarda: borrarlo o usar otro subdominio. No se crea ningún registro hacia la IP de la VPS.
- Hasta que la VPS conecte el túnel, el hostname responde con el error 1033 (HTTP 530).

### 3. Identificar el sistema y los recursos

```bash
cat /etc/os-release | head -3
whoami
nproc && lscpu | grep "Model name" && free -h && df -h /
```

Si la sesión es `root`, omitir `sudo` en los comandos siguientes y el `usermod` del paso 6.

### 4. Actualizar el sistema

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl
```

### 5. Firewall: solo SSH

```bash
sudo ufw allow OpenSSH
sudo ufw enable
sudo ufw status
```

Si SSH escucha en un puerto distinto de 22, ejecutar antes `sudo ufw allow <puerto>/tcp`; de lo contrario se pierde el acceso al activar el firewall. El túnel es una conexión saliente y no necesita los puertos 80 ni 443.

### 6. Instalar Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

Cerrar la sesión SSH y volver a entrar para aplicar el grupo; luego:

```bash
docker compose version
docker run --rm hello-world
```

El grupo `docker` equivale a privilegios de root: agregar solo al usuario operador. `systemctl enable` hace que Docker, y con él los contenedores con `restart: unless-stopped`, arranquen tras un reinicio de la VPS.

### 7. Clonar el repositorio y configurar los secretos

```bash
git clone https://github.com/JorgeGutierrez11/sg-sst-agentic-rag.git
cd sg-sst-agentic-rag/deploy
cp .env.example .env
chmod 600 .env
nano .env
```

| Variable | Valor |
|---|---|
| `DEEPSEEK_API_KEY` | Clave de la API de DeepSeek. |
| `TUNNEL_TOKEN` | Token `eyJ...` del paso 1, sin el resto del comando. |
| `BACKEND_TAG`, `FRONTEND_TAG` | Tags `sha-<7>` a desplegar; los valores de `.env.example` corresponden a la última versión publicada. |
| `PUBLIC_HOSTNAME` | `sgsst.gimnasiouis.com`, sin esquema. |

Comprobar la configuración sin imprimir los secretos:

```bash
docker compose config --quiet && echo "config OK"
```

El corpus publicado está versionado en `data/processed/`, así que el checkout ya lo contiene; `CORPUS_DIR` solo se usa si el corpus vive en otra ruta.

### 8. Descargar las imágenes y levantar el stack

```bash
docker compose pull          # unos 6.3 GB
docker compose up -d
watch -n 5 docker compose ps
```

Esperar a que `backend` y `frontend` muestren `(healthy)`; con 2 vCPU el backend puede tardar dos minutos o más. Después arranca `cloudflared`. Salir de `watch` con `Ctrl+C`.

### 9. Verificar

```bash
docker compose logs cloudflared | grep -i "registered tunnel connection"
curl -sS -o /dev/null -w "%{http_code}\n" https://sgsst.gimnasiouis.com/       # 200 (frontend)
curl -sS https://sgsst.gimnasiouis.com/api/v1/diagnostics/no-existe            # {"detail":"Diagnostic session not found."}
curl -sS -o /dev/null -w "%{http_code}\n" https://sgsst.gimnasiouis.com/docs   # 404: la documentación del backend no es pública
```

En el panel de Cloudflare el túnel debe figurar como **Healthy**. Por último, abrir `https://sgsst.gimnasiouis.com` en el navegador y completar una consulta normativa.

### 10. Medir el consumo

Durante una consulta real, en la VPS:

```bash
docker stats --no-stream
```

Registrar el tiempo de respuesta y el uso de CPU y memoria; sirven para ajustar los límites y vigilar el corte de 100 s de Cloudflare.

## Actualizar o volver a una versión anterior

Las versiones se fijan con tags inmutables `sha-<7>`, nunca con `main`:

```bash
git pull                     # trae cambios de deploy/compose.yaml y del corpus
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
- Límites de memoria: `backend` 5 GB (pico medido 3.34 GiB), `frontend` 512 MB, `cloudflared` 256 MB; si un contenedor los supera, el kernel lo termina y Docker lo reinicia. No hay límite de CPU: el backend usa todos los núcleos y con 2 vCPU las consultas simultáneas pueden acercarse al corte de 100 s.

## Troubleshooting

| Síntoma | Causa probable | Acción |
|---|---|---|
| Error 1033 / HTTP 530 en el hostname | `cloudflared` no está conectado. | `docker compose ps` y `docker compose logs cloudflared`; si espera a `backend`, revisar sus logs. |
| `cloudflared` en estado `restarting`; log `Provided Tunnel token is not valid.` | `TUNNEL_TOKEN` incorrecto. | Copiar de nuevo el token del panel en `.env` y `docker compose up -d`. |
| `required variable ... is missing a value` | Falta una variable en `.env`. | Completar la variable indicada. |
| Error 502 en `/api/v1/*` | Ruta del túnel apunta a un servicio incorrecto o con `https://`. | Verificar en el panel `http://backend:8000` y el orden de las rutas. |
| Backend en estado `restarting`; log con código `3` (`Missing runtime artifact`) | Corpus incompleto en `CORPUS_DIR`; `unless-stopped` lo reinicia indefinidamente y `cloudflared` no arranca. | `docker compose logs backend`; corregir el corpus (ver [`docker.md`](docker.md#troubleshooting)) y `docker compose up -d`. |
