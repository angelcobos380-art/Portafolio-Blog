# Despliegue

El proyecto tiene dos partes que se despliegan por separado:

1. **Backend (CMS)** — FastAPI + SQLite, en `backend/`.
2. **Frontend (Portafolio)** — Astro, en `src/` (Vercel y/o GitHub Pages).

El frontend lee el contenido del backend **en build-time** y el backend **dispara un rebuild** del frontend al publicar/despublicar contenido.

---

## 1. Desplegar el backend (CMS)

### Opción A — Render (recomendado)

Usa el archivo `render.yaml` incluido en la raíz (Blueprint de Render):

1. Crea una cuenta en [render.com](https://render.com).
2. `New +` → **Blueprint** → conecta el repositorio `Portafolio-Blog`.
3. Render detecta `render.yaml` y crea el servicio web **`cms-api`** con:
   - Dockerfile en `backend/`.
   - Disco persistente montado en `/var/data` (para que SQLite no se pierda al redeploy).
   - `SECRET_KEY` generado automáticamente.
4. En el dashboard del servicio, configura las variables que quedaron pendientes:
   - `ADMIN_EMAIL` — tu correo.
   - `ADMIN_PASSWORD` — tu contraseña de admin (mín. 8 caracteres).
   - `VERCEL_DEPLOY_HOOK` — se explica en el paso 2.
5. Anota la URL del servicio (ej. `https://cms-api.onrender.com`).

> Nota: el disco persistente en Render es de pago (muy bajo costo). Si prefieres no pagar, puedes desplegar sin disco (`DATABASE_URL` apuntando a `/tmp/cms.db`), pero **los datos se pierden en cada redeploy**. Otra alternativa gratuita y persistente es usar PostgreSQL (Neon/Supabase) — cambio menor de `DATABASE_URL`.

### Opción B — Docker (VPS, Railway, Fly, etc.)

El `Dockerfile` de `backend/` funciona en cualquier host con Docker:

```bash
cd backend
docker build -t cms-api .
docker run -d --name cms-api \
  -p 8000:8000 \
  -e SECRET_KEY=... \
  -e ADMIN_EMAIL=... \
  -e ADMIN_PASSWORD=... \
  -e DATABASE_URL=sqlite:////data/cms.db \
  -e COOKIE_SECURE=true \
  -e VERCEL_DEPLOY_HOOK=... \
  -v cms-data:/data \
  cms-api
```

O con Docker Compose (desde la raíz, definiendo las variables en un `.env`):

```bash
docker compose up -d
```

### Verificar el backend

- `GET https://<tu-backend>/health` → `{"status":"ok"}`.
- `GET https://<tu-backend>/docs` → Swagger.
- `GET https://<tu-backend>/admin/login` → panel de administración.

---

## 2. Conectar el frontend

### Vercel (sitio principal)

1. En [vercel.com](https://vercel.com), abre el proyecto del portafolio.
2. **Settings → Environment Variables** y agrega:
   - `PUBLIC_CMS_BASE_URL` = `https://<tu-backend>/api/v1`.
3. **Settings → Git → Deploy Hooks** → `Create Hook` → nómbralo `cms-publish` y copia la URL.
4. Pega esa URL en el backend como variable `VERCEL_DEPLOY_HOOK`.

### GitHub Pages (alternativa)

1. En el repositorio, **Settings → Secrets and variables → Actions** y agrega el secreto:
   - `PUBLIC_CMS_BASE_URL` = `https://<tu-backend>/api/v1`.
2. El workflow `.github/workflows/deploy.yml` ya la inyecta al build.

> El rebuild automático al publicar (`VERCEL_DEPLOY_HOOK`) está pensado para Vercel. Para GitHub Pages puedes disparar el workflow manualmente o con un `repository_dispatch`.

---

## 3. Flujo completo

```
Admin publica un post en /admin
   → backend confirma el cambio en SQLite
   → BackgroundTasks hace POST a VERCEL_DEPLOY_HOOK
   → Vercel reconstruye el sitio
   → el build de Astro hace fetch a /public/posts y /public/projects
   → el sitio se publica con el contenido nuevo
```

Si `VERCEL_DEPLOY_HOOK` no está configurado, publicar no falla; solo no habrá rebuild automático.

---

## 4. Variables de entorno (resumen)

### Backend (`backend/.env` o entorno del servicio)

| Variable | Requerida | Descripción |
|---|---|---|
| `SECRET_KEY` | Sí | Clave para firmar los JWT (mín. 32 caracteres). |
| `ADMIN_EMAIL` | Sí | Correo del administrador. |
| `ADMIN_PASSWORD` | Sí | Contraseña del admin (mín. 8). |
| `DATABASE_URL` | No | URL de SQLite (por defecto `sqlite:///./cms.db`). |
| `COOKIE_SECURE` | No | `true` en producción (HTTPS). |
| `VERCEL_DEPLOY_HOOK` | No | Hook para rebuild automático. |

### Frontend

| Variable | Dónde | Descripción |
|---|---|---|
| `PUBLIC_CMS_BASE_URL` | Vercel / secreto de Actions | URL base de la API pública del CMS (`/api/v1`). |
