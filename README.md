# 👾 Angel Marco - Portafolio Personal & Blog

Bienvenido al código fuente de mi portafolio personal y blog. Este espacio está diseñado para presentar mi perfil como **Backend & Cloud Developer**, documentar mis proyectos y compartir mis aprendizajes en el desarrollo de software.

🔗 **[Visita el sitio en vivo aquí](https://portafolio-blog-nine.vercel.app/)**
🔗 **[Vista con ayuda de GitHub pages](https://angelcobos380-art.github.io/Portafolio-Blog/#proyectos)**

## 🛠️ Stack Tecnológico

Este sitio fue construido desde cero enfocándose en el rendimiento, la accesibilidad y un diseño minimalista ("Modern Dev").

- **Framework:** [Astro](https://astro.build/) (Elegido por su velocidad y arquitectura de *islas*, ideal para sitios orientados a contenido).
- **Estilos:** CSS puro / Custom Properties (Diseño *Glassmorphism* y Dark Mode nativo).
- **Despliegue:** Vercel (CI/CD integrado con GitHub).

## 🗄️ CMS / Backend

El contenido (posts, proyectos, categorías y métricas) se gestiona desde un **CMS hecho a medida** en `backend/` (FastAPI + SQLite) con panel de administración en `/admin`.

- El portafolio lee el contenido del CMS en **build-time** (variable `PUBLIC_CMS_BASE_URL`).
- Al publicar/despublicar contenido, el CMS dispara un **rebuild** del sitio.

Consulta la guía completa en [`DEPLOYMENT.md`](DEPLOYMENT.md).
