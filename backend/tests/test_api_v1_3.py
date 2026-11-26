from io import BytesIO
import os

from PIL import Image
import pytest

# Env vars de prueba antes de importar la app
os.environ["SECRET_KEY"] = "test-secret-key-at-least-32-characters-long"
os.environ["ADMIN_EMAIL"] = "admin@example.com"
os.environ["ADMIN_PASSWORD"] = "SuperSecret123!"
os.environ["CORS_ORIGINS"] = "http://localhost:5173,http://localhost:4321"
os.environ["STORAGE_BACKEND"] = "local"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test_cms.db"
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir()

    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    os.environ["MEDIA_LOCAL_DIR"] = str(uploads_dir)

    from fastapi.testclient import TestClient
    from sqlmodel import SQLModel, create_engine

    import app.core.config as config_mod
    import app.core.database as db_mod
    from app.main import app as fastapi_app

    config_mod.settings.DATABASE_URL = f"sqlite:///{db_file}"
    config_mod.settings.MEDIA_LOCAL_DIR = str(uploads_dir)
    db_mod.engine = create_engine(
        config_mod.settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(db_mod.engine)
    db_mod.seed_admin()
    db_mod.seed_default_template()

    with TestClient(fastapi_app) as tc:
        yield tc


def _auth_headers(client):
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "SuperSecret123!"},
    )
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_auth_me_and_no_admin_jinja(client):
    headers = _auth_headers(client)
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "admin@example.com"
    assert me.json()["role"] == "ADMIN"

    # Panel Jinja retirado
    assert client.get("/admin").status_code == 404


def test_post_3_state_lifecycle_sanitizer_and_public(client):
    headers = _auth_headers(client)

    # 1. Crear borrador relajado (sin categorías, título corto)
    r1 = client.post("/api/v1/posts", headers=headers, json={"title": "Hi", "tags": ["FastAPI", "Python"]})
    assert r1.status_code == 201
    post = r1.json()
    post_id = post["post_id"]
    assert post["status"] == "BORRADOR"
    assert post["slug"] == "hi"
    assert post["tags"] == ["fastapi", "python"]

    # 2. Segundo borrador con el mismo título genera sufijo único (no 409)
    r2 = client.post("/api/v1/posts", headers=headers, json={"title": "Hi"})
    assert r2.status_code == 201
    assert r2.json()["slug"].startswith("hi-")
    # Eliminar borrador permitido
    assert client.delete(f"/api/v1/posts/{r2.json()['post_id']}", headers=headers).status_code == 204

    # 3. Intentar publicar incompleto devuelve 422 estructurado
    pub_fail = client.post(f"/api/v1/posts/{post_id}/publish", headers=headers)
    assert pub_fail.status_code == 422
    fields = {err["loc"][-1] for err in pub_fail.json()["detail"]}
    assert "title" in fields and "content" in fields

    # 4. PATCH con HTML peligroso -> nh3 + attribute_filter lo sanitiza
    dirty_html = (
        '<div class="callout callout-tip evil-cls" style="color: #0ea5e9; position: fixed; background: url(javascript:alert(1))">'
        '<p onclick="alert(1)">Hola mundo con contenido suficiente para publicar.</p>'
        '<script>alert("xss")</script>'
        '<a href="javascript:alert(1)">malo</a>'
        '<a href="https://example.com" target="_blank">bueno</a>'
        '</div>'
    )
    patched = client.patch(
        f"/api/v1/posts/{post_id}",
        headers=headers,
        json={
            "title": "Guía de CMS Headless en FastAPI",
            "excerpt": "Resumen de prueba",
            "content_html": dirty_html,
            "content_json": {"type": "doc", "content": []},
            "content_schema_version": 1,
        },
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["slug"] == "guia-de-cms-headless-en-fastapi"
    assert "<script>" not in body["content_html"]
    assert "onclick" not in body["content_html"]
    assert "position" not in body["content_html"]
    assert "evil-cls" not in body["content_html"]
    assert "callout-tip" in body["content_html"]
    assert "color: #0ea5e9" in body["content_html"]
    assert 'rel="noopener noreferrer"' in body["content_html"]

    # 5. Publicar con éxito
    pub_ok = client.post(f"/api/v1/posts/{post_id}/publish", headers=headers)
    assert pub_ok.status_code == 200
    assert pub_ok.json()["status"] == "PUBLICADO"
    assert pub_ok.json()["published_at"] is not None

    # 6. Público devuelve listado sin contenido y detalle con template embebida
    pub_list = client.get("/api/v1/public/posts")
    assert pub_list.status_code == 200
    assert pub_list.json()["total"] == 1
    assert "content_html" not in pub_list.json()["items"][0]

    pub_detail = client.get(f"/api/v1/public/posts/{body['slug']}")
    assert pub_detail.status_code == 200
    assert pub_detail.json()["template"] is not None
    assert pub_detail.json()["template"]["tokens"]["colors"]["accent"] == "#e34b4e"

    # 7. Registrar vista y consultar métricas
    assert client.post(f"/api/v1/public/posts/{body['slug']}/view").status_code == 204
    summary = client.get("/api/v1/metrics/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["totals"]["views"] == 1
    assert summary.json()["totals"]["by_status"]["PUBLICADO"] == 1

    views = client.get("/api/v1/metrics/views", headers=headers)
    assert views.status_code == 200
    assert sum(p["views"] for p in views.json()["series"]) == 1

    # 8. Despublicar vuelve a BORRADOR, archivar bloquea PATCH y restore devuelve a BORRADOR
    unpub = client.post(f"/api/v1/posts/{post_id}/unpublish", headers=headers)
    assert unpub.status_code == 200
    assert unpub.json()["status"] == "BORRADOR"

    arch = client.post(f"/api/v1/posts/{post_id}/archive", headers=headers)
    assert arch.status_code == 200
    assert arch.json()["status"] == "ARCHIVADO"

    assert client.patch(f"/api/v1/posts/{post_id}", headers=headers, json={"title": "No debe editar"}).status_code == 409
    assert client.delete(f"/api/v1/posts/{post_id}", headers=headers).status_code == 409

    rest = client.post(f"/api/v1/posts/{post_id}/restore", headers=headers)
    assert rest.status_code == 200
    assert rest.json()["status"] == "BORRADOR"


def test_templates_and_media_endpoints(client):
    headers = _auth_headers(client)

    # Crear plantilla desde cero (ignora tokens desconocidos)
    created = client.post(
        "/api/v1/templates",
        headers=headers,
        json={
            "name": "Editorial Claro",
            "description": "Plantilla limpia",
            "tokens": {"version": 1, "futureUnknownKey": True, "colors": {"accent": "#0ea5e9"}},
        },
    )
    assert created.status_code == 201
    tpl_id = created.json()["template_id"]
    assert "futureUnknownKey" not in created.json()["tokens"]

    # Duplicar y set-default
    dup = client.post(f"/api/v1/templates/{tpl_id}/duplicate", headers=headers)
    assert dup.status_code == 201
    assert "(copia)" in dup.json()["name"]

    assert client.post(f"/api/v1/templates/{tpl_id}/set-default", headers=headers).json()["is_default"] is True

    # Media: rechaza SVG (415) y acepta PNG válido (201)
    bad = client.post(
        "/api/v1/media",
        headers=headers,
        files={"file": ("icon.svg", b"<svg></svg>", "image/svg+xml")},
    )
    assert bad.status_code == 415

    buf = BytesIO()
    Image.new("RGB", (64, 32), color=(227, 75, 78)).save(buf, format="PNG")
    good = client.post(
        "/api/v1/media",
        headers=headers,
        files={"file": ("cover.png", buf.getvalue(), "image/png")},
        data={"alt": "Portada"},
    )
    assert good.status_code == 201
    media = good.json()
    assert media["width"] == 64 and media["height"] == 32
    assert media["alt"] == "Portada"
