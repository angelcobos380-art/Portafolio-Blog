# Especificación Técnica Completa y Documentación del Ecosistema de Microservicios CMS/Blog en FastAPI

## 1. Visión General de la Arquitectura
El sistema implementa una arquitectura modular de 5 microservicios RESTful desarrollados sobre **FastAPI**, **Pydantic v2** y patrones de **Domain-Driven Design (DDD)** para el control estricto de invariantes del ciclo de vida editorial.

```
+-----------------------------------------------------------------------------------+
|                                 ARQUITECTURA CMS                                  |
+------------------------+---------------------------------+------------------------+
                         |                                 |
                         v                                 v
        +----------------------------------+    +----------------------------------+
        |        auth-identity-api         |    |         media-assets-api         |
        | Autenticación, RBAC y Tokens JWT |    | Carga de imágenes y Presigned URLs|
        +----------------+-----------------+    +----------------+-----------------+
                         |                                 |
                         +----------------+----------------+
                                          |
                                          v
                        +------------------------------------+
                        |            posting-909             |
                        | API Core de Publicaciones y Blogs  |
                        +-----------------+------------------+
                                          |
                         +----------------+----------------+
                         |                                 |
                         v                                 v
        +----------------------------------+    +----------------------------------+
        |   public-content-delivery-api    |    |   notifications-webhooks-api     |
        | Lectura Pública y Cache CDN      |    | Eventos, Alertas Slack y Emails  |
        +----------------------------------+    +----------------------------------+
```

---

## 2. Especificación Formal por Microservicio (Metodología de 6 Pasos)

### 2.1. Service: `posting-909` (API Core de Gestión de Posts)
- **PASO 1:** Administrar el ciclo de vida de posts (BORRADOR -> EN_REVISION -> PUBLICADO -> DESPUBLICADO -> ARCHIVADO).
- **PASO 2:** Entidades principales: `Post`, `Category`, `ReviewReport`, `MetricSnapshot`.
- **PASO 3:** Invariantes:
  1. Sistema siempre posee al menos 1 categoría. Eliminación bloqueada si total == 1.
  2. Slug globalmente único.
  3. `PUBLICADO` congela metadatos de categoría en `frozen_category`.
  4. Posts en `PUBLICADO`, `DESPUBLICADO` o `ARCHIVADO` tienen **prohibición absoluta de eliminación física**.
  5. `ARCHIVADO` es un estado inmutable y terminal.
- **PASO 4:** Tipos: `UUIDv7`, `ISO 8601 Timestamp`, `Enum(PostStatus)`.
- **PASO 5:** Endpoints:
  - `POST /api/v1/posts` (201) - Crear Borrador
  - `GET /api/v1/posts/{post_id}` (200) - Obtener Post
  - `PUT /api/v1/posts/{post_id}` (200) - Modificar Borrador
  - `POST /api/v1/posts/{post_id}/submit-review` (200) - Enviar a Auditoría
  - `POST /api/v1/posts/{post_id}/publish` (200) - Publicar y Congelar Taxonomía
  - `POST /api/v1/posts/{post_id}/unpublish` (200) - Despublicar
  - `POST /api/v1/posts/{post_id}/archive` (200) - Archivar Definitivamente
  - `DELETE /api/v1/posts/{post_id}` (204) - Borrar Borrador Físicamente
  - `GET /api/v1/posts/{post_id}/metrics` (200) - Consultar Métricas
- **PASO 6:** Relevo: Integración síncrona/asíncrona con SSG, Agente Auditor y CDN.

### 2.2. Service: `auth-identity-api`
- **PASO 1:** Autenticación de usuarios y emisión de JWT (Access Token 15 min, Refresh Token 7 días).
- **PASO 5:** Endpoints:
  - `POST /api/v1/auth/login` (200) - Login de administradores
  - `POST /api/v1/auth/introspect` (200) - Validación de tokens por middleware

### 2.3. Service: `media-assets-api`
- **PASO 1:** Generación de Presigned URLs para carga de archivos a S3/GCS.
- **PASO 3:** Invariantes: Tamaño máximo 10MB; MIME permitidos (`image/jpeg`, `image/png`, `image/webp`, `image/svg+xml`).
- **PASO 5:** Endpoints:
  - `POST /api/v1/media/upload-url` (200) - Expedir Presigned URL y Public CDN URL.

### 2.4. Service: `public-content-delivery-api`
- **PASO 1:** Entrega de contenido público optimizado para lectura y CDN.
- **PASO 3:** Invariante: Únicamente retorna artículos con estado `PUBLICADO`.
- **PASO 5:** Endpoints:
  - `GET /api/v1/public/posts` (200) - Feed de publicaciones públicas
  - `GET /api/v1/public/posts/{slug}` (200) - Detalle por slug

### 2.5. Service: `notifications-webhooks-api`
- **PASO 1:** Despacho asíncrono de eventos de dominio hacia suscriptores externos y re-construcción SSG.
- **PASO 5:** Endpoints:
  - `POST /api/v1/events/dispatch` (202) - Encolar evento de dominio.

---

## 3. Instrucciones de Ejecución Local
```bash
# 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Linux/Mac

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Iniciar el servidor FastAPI con Uvicorn
uvicorn app.main:app --reload --port 8000

# 4. Acceder a la documentación interactiva Swagger OpenAPI
# http://127.0.0.1:8000/docs
```
