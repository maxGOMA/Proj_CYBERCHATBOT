# LSMiniSocial

LSMiniSocial es una aplicación web sencilla tipo red social desarrollada con **CodeIgniter 4**. Permite a usuarios de la comunidad La Salle registrarse, iniciar sesión, crear publicaciones, subir imágenes, dar likes, comentar, editar su perfil y mejorar el texto de sus publicaciones mediante IA.

El proyecto incluye un entorno local con **Docker**, **Nginx**, **PHP**, **MySQL** y **phpMyAdmin**, por lo que se puede levantar de forma rápida sin instalar manualmente todos los servicios.

## Funcionalidades principales

- Registro e inicio de sesión de usuarios.
- Restricción de registro a correos de La Salle:
  - `@students.salle.url.edu`
  - `@ext.salle.url.edu`
  - `@salle.url.edu`
- Perfil de usuario editable con nombre, contraseña y foto de perfil.
- Creación, edición y eliminación de publicaciones.
- Subida opcional de imágenes en publicaciones.
- Sistema de likes por publicación.
- Sistema de comentarios.
- Feed privado para usuarios autenticados.
- Selector de idioma: español e inglés.
- Integración con Hugging Face para mejorar textos con IA.
- Validación de formularios y protección de rutas privadas mediante filtros.

## Tecnologías utilizadas

- **PHP 8**
- **CodeIgniter 4**
- **MySQL 8.4**
- **Nginx**
- **Docker / Docker Compose**
- **Composer**
- **Guzzle HTTP** para peticiones a servicios externos
- **Hugging Face Router API** para la funcionalidad de IA
- **HTML, CSS y JavaScript**

## Estructura del proyecto

```text
grupo-26/
└── local-environment-PracWeb2/
    ├── docker-compose.yaml
    ├── Dockerfile
    ├── .env
    ├── docker-compose/
    │   ├── mysql/
    │   ├── nginx/
    │   ├── PHP/
    │   └── xdebug/
    └── www/
        ├── app/
        │   ├── Config/
        │   ├── Controllers/
        │   ├── Database/Migrations/
        │   ├── Filters/
        │   ├── Language/
        │   ├── Models/
        │   └── Views/
        ├── public/
        │   ├── css/
        │   ├── img/
        │   └── index.php
        ├── writable/
        ├── composer.json
        └── spark
```

## Requisitos previos

Antes de ejecutar el proyecto, asegúrate de tener instalado:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Git](https://git-scm.com/)
- Composer no es obligatorio en local si se ejecuta dentro del contenedor.

## Instalación y ejecución

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd grupo-26/local-environment-PracWeb2
```

### 2. Revisar las variables de entorno

El entorno Docker se configura desde el archivo `.env` situado en `local-environment-PracWeb2/`.

Ejemplo de configuración usada por el proyecto:

```env
PROJECT_NAME=local_environment
PROJECT_PREFIX=PracWeb2

MYSQL_PORT=3366
NGINX_PORT=8480
PHPMYADMIN_PORT=8084

DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_DATABASE=project_db
DB_USERNAME=pw2user
```

La aplicación CodeIgniter usa su propio archivo de entorno en `www/.env`. Revisa especialmente la base de datos, la URL base y la configuración de IA:

```env
database.default.hostname = mysql
database.default.database = project_db
database.default.username = pw2user
database.default.password = <password>
database.default.DBDriver = MySQLi
database.default.port = 3306

app.baseURL = 'http://localhost:8480/'

HF_API_TOKEN=<tu_token_de_hugging_face>
HF_MODEL=Qwen/Qwen2.5-7B-Instruct
```

> No subas tokens reales ni contraseñas privadas a repositorios públicos. Usa valores locales o variables de entorno seguras.

### 3. Levantar los contenedores

Desde `local-environment-PracWeb2/` ejecuta:

```bash
docker compose up -d --build
```

Comprueba que los servicios están activos:

```bash
docker compose ps
```

### 4. Instalar dependencias PHP

Si la carpeta `vendor/` no está instalada o se parte de una copia limpia del proyecto, ejecuta:

```bash
docker compose exec app composer install
```

### 5. Ejecutar las migraciones

Para crear las tablas necesarias en la base de datos:

```bash
docker compose exec app php spark migrate
```

## Acceso a la aplicación

Con la configuración actual, los servicios quedan disponibles en:

| Servicio | URL |
|---|---|
| Aplicación | `http://localhost:8480/` |
| phpMyAdmin | `http://localhost:8084/` |
| MySQL | `localhost:3366` |

## Uso básico

1. Accede a `http://localhost:8480/`.
2. Crea una cuenta con un correo válido de La Salle.
3. Inicia sesión.
4. Crea publicaciones desde la sección **New Post**.
5. Añade imágenes opcionales a tus publicaciones.
6. Interactúa con otros posts mediante likes y comentarios.
7. Edita tu perfil desde la sección **Profile**.
8. Usa la opción de IA para mejorar el texto antes de publicar.

## Rutas principales

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Landing pública |
| `GET` | `/sign-up` | Formulario de registro |
| `POST` | `/sign-up` | Crear usuario |
| `GET` | `/sign-in` | Formulario de login |
| `POST` | `/sign-in` | Iniciar sesión |
| `POST` | `/logout` | Cerrar sesión |
| `GET` | `/home` | Feed privado |
| `GET` | `/profile` | Perfil del usuario |
| `POST` | `/profile` | Actualizar perfil |
| `POST` | `/delete-account` | Eliminar cuenta |
| `GET` | `/post/create` | Crear publicación |
| `POST` | `/posts` | Guardar publicación |
| `GET` | `/post/edit/{id}` | Editar publicación |
| `POST` | `/post/update/{id}` | Actualizar publicación |
| `POST` | `/post/delete/{id}` | Eliminar publicación |
| `POST` | `/posts/{id}/like` | Dar o quitar like |
| `POST` | `/posts/{id}/comments` | Crear comentario |
| `POST` | `/comments/{id}/delete` | Eliminar comentario |
| `GET` | `/language/{locale}` | Cambiar idioma |
| `POST` | `/ai/improve` | Mejorar texto con IA |

## Base de datos

El proyecto define migraciones para las siguientes tablas:

- `users`: usuarios registrados.
- `posts`: publicaciones de usuarios.
- `likes`: likes asociados a usuarios y publicaciones.
- `comments`: comentarios asociados a usuarios y publicaciones.

Las relaciones principales son:

- Un usuario puede tener muchas publicaciones.
- Una publicación pertenece a un usuario.
- Un usuario puede dar like a muchas publicaciones.
- Una publicación puede tener muchos likes.
- Una publicación puede tener muchos comentarios.
- Un comentario pertenece a un usuario y a una publicación.

## Comandos útiles

Levantar el entorno:

```bash
docker compose up -d
```

Parar el entorno:

```bash
docker compose down
```

Ver logs:

```bash
docker compose logs -f
```

Ejecutar comandos de CodeIgniter:

```bash
docker compose exec app php spark <comando>
```

Ejecutar migraciones:

```bash
docker compose exec app php spark migrate
```

Acceder al contenedor PHP:

```bash
docker compose exec app bash
```

Ejecutar Composer dentro del contenedor:

```bash
docker compose exec app composer install
```

## Notas de desarrollo

- El código de la aplicación se encuentra en `www/app/`.
- Los archivos públicos, estilos e imágenes base se encuentran en `www/public/`.
- Las imágenes subidas por usuarios se guardan dentro de `www/public/uploads/`.
- Las rutas privadas están protegidas con el filtro de autenticación.
- La selección de idioma se guarda en sesión.
- La funcionalidad de IA requiere configurar correctamente `HF_API_TOKEN` en `www/.env`.

## Autores

Proyecto desarrollado por **David, Max y Martin** para La Salle URL.
