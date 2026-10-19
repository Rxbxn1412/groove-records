# Groove Records: tienda de vinilos y CD (Flask + PostgreSQL + Docker)

Tienda online de vinilos y CD desarrollada con [Flask](https://flask.palletsprojects.com/es/stable/) siguiendo la estructura y el estilo de los ejemplos del
[seminario-flask](https://github.com/josejuansanchez/seminario-flask).
Toda la aplicación funciona en **contenedores Docker**.

**RA1 (c, e, f):** instalación y configuración del servidor web (Gunicorn + Flask), del
servidor de bases de datos (PostgreSQL), de los módulos de procesamiento de código en el
servidor y del acceso a la base de datos.

## Arquitectura (4 contenedores)

| Contenedor | Imagen | Función | Puerto (tu equipo) |
|---|---|---|---|
| `tienda_web` | construida con el `Dockerfile` (Python 3.12 + Flask + Gunicorn) | Servidor web y de aplicaciones | 5000 (`WEB_PORT`) |
| `tienda_db` | `postgres:16` | Base de datos PostgreSQL (carga `schema.sql` al crearse) | interno |
| `tienda_pgadmin` | `dpage/pgadmin4` | Administración web de PostgreSQL (el servidor ya viene registrado) | 5050 (`PGADMIN_PORT`) |
| `tienda_mail` | `axllent/mailpit` | Servidor SMTP de pruebas: captura los correos y los muestra en una web | 8025 (`MAIL_WEB_PORT`) |

Si alguno de los puertos está ocupado en tu equipo, crea un archivo `.env` (copia de `.env.example`) y
cambia `WEB_PORT`, `MAIL_WEB_PORT` y/o `PGADMIN_PORT`. Por ejemplo `WEB_PORT=5001` y `MAIL_WEB_PORT=8026`.
En esta guía se usan los puertos por defecto: sustitúyelos por los tuyos si los has cambiado.

## Relación con el seminario

| Requisito | Dónde está | Ejemplo del seminario |
|---|---|---|
| Rutas y secciones variables | `/disco/<int:id>` | Ejemplos 02, 04 |
| Gestión de errores y redirecciones | `@app.errorhandler(404)`, `redirect(url_for(...))` | Ejemplo 05 |
| Métodos HTTP `GET` y `POST` | `@app.get` / `@app.post` en `/registro/` y en las rutas del carrito (`/carrito/anadir/<id>`, `/carrito/finalizar`…); `methods=['GET','POST']` en `/login/` y `/contacto/`; parámetros GET en el buscador de `/` | Ejemplos 06, 07 |
| Plantillas Jinja2 y CSS | carpeta `templates/` (con herencia de `base.html`) y `static/styles.css` | Ejemplos 08, 09 |
| Formularios | búsqueda (GET), registro, login, contacto y carrito de la compra (POST) | Ejemplos 10, 11 |
| Formularios de administración | `/admin/disco/nuevo/` y `/admin/disco/<id>/editar/` (solo administrador, decorador `admin_requerido`) | Ejemplos 10, 11 |
| Registro de usuarios | `/registro/` (contraseña cifrada con `werkzeug.security`) | — |
| Correos automáticos | `correo.py`: bienvenida, confirmación de pedido y de contacto | — |
| Portadas reales | `portadas.py`: consulta la API pública de iTunes y guarda la URL en `discos.portada_url` | — |
| Base de datos **PostgreSQL** | `db.py` (psycopg2) y `schema.sql` | — |
| Contenedores | `Dockerfile` y `docker-compose.yml` (web, db, pgAdmin, mailpit) | — |

## Estructura del proyecto

```
.
├── app.py                # Rutas de la aplicación
├── db.py                 # Acceso a PostgreSQL
├── correo.py             # Envío de correos (SMTP)
├── portadas.py           # Búsqueda de portadas reales (API de iTunes)
├── schema.sql            # Tablas y 12 discos de ejemplo
├── Dockerfile            # Imagen de la aplicación Flask
├── docker-compose.yml    # Orquestación: web + db + pgAdmin + mailpit
├── pgadmin
│   └── servers.json      # Registra la base de datos en pgAdmin
├── requirements.txt
├── .env.example          # Opcional: puertos, contraseñas, SMTP real
├── static
│   └── styles.css
└── templates
    ├── base.html
    ├── index.html        # Catálogo con buscador
    ├── disco.html        # Ficha de un disco y botón «Añadir al carrito»
    ├── carrito.html      # Carrito de la compra
    ├── registro.html
    ├── login.html
    ├── contacto.html
    ├── admin_disco.html  # Formulario añadir/editar disco (administrador)
    ├── compras.html      # Mis pedidos (agrupados por pedido)
    └── 404.html
```

## Guía de pruebas paso a paso

### 0. Requisitos

Docker y Docker Compose (Docker Desktop en Windows/macOS, o Docker Engine + plugin `compose` en Linux).
**Docker Desktop debe estar abierto** y con el motor en marcha.

```bash
docker --version
docker compose version
docker info
```

### 1. Arrancar los contenedores

Desde la carpeta del proyecto:

```bash
docker compose up -d --build
```

> Si ya habías arrancado una versión anterior del proyecto (la de la tienda genérica), borra antes
> los datos antiguos, porque `schema.sql` solo se carga con la base de datos vacía:
> `docker compose down -v` y después el comando de arriba.

Comprueba el estado:

```bash
docker compose ps
```

**Resultado esperado:** los cuatro contenedores (`tienda_web`, `tienda_db`, `tienda_pgadmin`, `tienda_mail`) en estado
`running`, y `tienda_db` como `healthy`. Si algo falla, mira los registros:

```bash
docker compose logs web
docker compose logs db
```

### 2. Comprobar el servidor de bases de datos (RA1 c, f)

```bash
docker compose exec db psql -U tienda_user -d tienda -c "\dt"
docker compose exec db psql -U tienda_user -d tienda -c "SELECT id, artista, titulo, formato, stock FROM discos ORDER BY id;"
```

**Resultado esperado:** aparecen las tablas `usuarios`, `discos`, `pedidos`, `compras` y `mensajes`, y
12 discos de ejemplo. Esto demuestra que PostgreSQL funciona y que `schema.sql` se ha cargado solo.
Tras abrir el catálogo (paso 3), puedes ver las portadas guardadas con:
`docker compose exec db psql -U tienda_user -d tienda -c "SELECT id, titulo, left(portada_url, 50) FROM discos ORDER BY id;"`

### 2b. Comprobar pgAdmin (administración de la base de datos)

1. Abre **http://localhost:5050** e inicia sesión con `admin@grooverecords.com` / `admin1234`
   (si no cambias `PGADMIN_EMAIL` y `PGADMIN_PASSWORD` en `.env`). pgAdmin tarda ~30 s en arrancar la primera vez.
2. En el panel izquierdo aparece el servidor **Groove Records DB** (ya registrado). Al abrirlo pide la
   contraseña de PostgreSQL: `tienda_pass` (marca *Save Password*).
3. Navega a *Databases → tienda → Schemas → public → Tables*: verás `usuarios`, `discos`, `pedidos`, `compras`, `mensajes`.
4. Clic derecho en `discos` → *View/Edit Data → All Rows*: se ven los 12 discos. También puedes abrir
   *Query Tool* y ejecutar `SELECT * FROM discos;`.

**Resultado esperado:** ves y editas la base de datos PostgreSQL desde el navegador. Si no entras,
mira `docker compose logs pgadmin`.

### 3. Comprobar el servidor web y las plantillas (RA1 c, e)

Abre en el navegador **http://localhost:5000**.

**Resultado esperado:** el catálogo de Groove Records, con tarjetas de discos con su portada real, formato
(Vinilo/CD), género y precio, con estilos CSS (plantillas Jinja2 + hoja de estilos).

> **Portadas reales:** la primera vez que se abre el catálogo, la aplicación busca la portada de cada
> disco en la API pública de iTunes y guarda la URL en la base de datos (columna `portada_url`), así que
> esa primera carga puede tardar unos segundos y las siguientes son inmediatas. Necesita conexión a
> internet. Si no hay conexión o no encuentra un álbum, se muestra una portada de respaldo dibujada con CSS.
Pulsa **Ver disco** en uno de ellos (ruta variable `/disco/<id>`).

### 4. Probar el buscador (método GET con parámetros)

En el catálogo prueba el formulario de búsqueda. Observa cómo cambia la URL:

- Escribe `pink` y pulsa **Buscar** → `http://localhost:5000/?q=pink&formato=&genero=`: solo sale Pink Floyd.
- Elige formato **CD** → solo salen discos en CD.
- Elige género **Rock** y formato **Vinilo** → un único resultado.
- Escribe algo que no exista (`zzz`) → mensaje "No se ha encontrado ningún disco...".

También por URL directa: `http://localhost:5000/?genero=Jazz`.

### 5. Probar los métodos HTTP y los errores

En una terminal (en PowerShell usa `curl.exe` en lugar de `curl`):

```bash
# GET de un disco existente -> 200
curl -i http://localhost:5000/disco/1

# Disco inexistente -> 404 (errorhandler)
curl -i http://localhost:5000/disco/99

# GET a una ruta que solo admite POST -> 405 Method Not Allowed
curl -i http://localhost:5000/carrito/anadir/1

# Ruta protegida sin iniciar sesión -> 302 redirección a /login/
curl -i http://localhost:5000/mis-compras/
```

### 6. Registro de usuario y correo automático de bienvenida

1. En el navegador entra en **http://localhost:5000/registro/** y rellena el formulario
   (por ejemplo: nombre `Ana`, correo `ana@test.com`, contraseña `secreto1`).
2. Serás redirigido a la pantalla de login con el mensaje "Registro completado".
3. Abre **http://localhost:8025** (Mailpit): debe haber un correo **"Bienvenido a Groove Records"**
   dirigido a `ana@test.com`.
4. Comprueba el usuario en la base de datos (la contraseña aparece cifrada):

```bash
docker compose exec db psql -U tienda_user -d tienda -c "SELECT id, nombre, email, left(password, 25) AS password FROM usuarios;"
```

5. Prueba también el caso de error: vuelve a registrar el mismo correo → mensaje
   "Ya existe un usuario con ese correo electrónico."

### 7. Inicio de sesión

1. Entra en **http://localhost:5000/login/**.
2. Con una contraseña incorrecta → mensaje de error.
3. Con la correcta → vuelves al catálogo y el menú muestra "Hola, Ana", **Mis pedidos** y **Salir**.

### 8. Carrito de la compra y correo automático de confirmación

El carrito se guarda en la sesión del usuario y permite comprar **varios discos a la vez**. Al finalizar,
se crea **un pedido** (tabla `pedidos`) con una línea por disco (tabla `compras`), todo dentro de una
**transacción**: o se guarda el pedido entero o no se guarda nada.

1. Entra en un disco (por ejemplo el nº 1, *The Dark Side of the Moon*, stock 10), pon cantidad `2` y pulsa
   **Añadir al carrito**. Aparece el aviso y en el menú el contador **Carrito (2)**.
2. Vuelve al catálogo, abre otro disco (por ejemplo el nº 2) y pulsa **Añadir al carrito** (cantidad 1).
   El contador pasa a 3.
3. Abre **Carrito** en el menú: verás los dos discos, los subtotales y el total. Prueba **Actualizar**
   (cambiar la cantidad), **Quitar** y **Vaciar carrito**. Si superas el stock, aparece un error.
4. Sin sesión iniciada puedes llenar el carrito, pero **Finalizar compra** te pide iniciar sesión
   (el carrito se conserva).
5. Con la sesión iniciada, pulsa **Finalizar compra**. Serás redirigido a **Mis pedidos**, donde aparece
   el **pedido nº 1** con sus dos líneas y el total.
6. En **http://localhost:8025** debe aparecer **un único** correo, *"Confirmación de tu pedido nº 1"*,
   con todos los discos, cantidades y el total.
7. Comprueba el pedido, sus líneas y que el stock ha bajado (disco 1: de 10 a 8; disco 2: un descuento de 1):

```bash
docker compose exec db psql -U tienda_user -d tienda -c "SELECT * FROM pedidos;"
docker compose exec db psql -U tienda_user -d tienda -c "SELECT * FROM compras;"
docker compose exec db psql -U tienda_user -d tienda -c "SELECT id, artista, titulo, stock FROM discos WHERE id IN (1, 2);"
```

8. **Prueba de la transacción (stock insuficiente):** añade al carrito 1 unidad del disco 3 y 1 del disco 4.
   Antes de finalizar, simula que alguien se ha llevado las últimas unidades del disco 4:

```bash
docker compose exec db psql -U tienda_user -d tienda -c "UPDATE discos SET stock = 0 WHERE id = 4;"
```

   Ahora pulsa **Finalizar compra**: aparece *"Algún disco ya no tiene stock suficiente…"* y **no se crea
   ningún pedido** ni se descuenta nada del disco 3, aunque ese sí tenía stock (esa es la utilidad de la
   transacción). Compruébalo: `SELECT count(*) FROM pedidos;` no ha aumentado y el stock del disco 3 sigue igual.

(Opcional) El mismo flujo con `curl`, guardando la cookie de sesión:

```bash
curl -i -c cookies.txt -X POST http://localhost:5000/login/ -d "email=ana@test.com&password=secreto1"
curl -i -b cookies.txt -c cookies.txt -X POST http://localhost:5000/carrito/anadir/1 -d "cantidad=1"
curl -i -b cookies.txt -c cookies.txt -X POST http://localhost:5000/carrito/anadir/2 -d "cantidad=1"
curl -b cookies.txt http://localhost:5000/carrito/
curl -i -b cookies.txt -c cookies.txt -X POST http://localhost:5000/carrito/finalizar
curl -b cookies.txt http://localhost:5000/mis-compras/
```

### 9. Formulario de contacto (notificación automática)

1. Entra en **http://localhost:5000/contacto/**, rellena el formulario y envíalo
   (los datos se envían a la misma ruta, como en el ejemplo 11 del seminario).
2. Se muestra la caja de confirmación y en Mailpit llega el correo **"Hemos recibido tu mensaje - Groove Records"**.
3. Comprueba que se ha guardado:

```bash
docker compose exec db psql -U tienda_user -d tienda -c "SELECT nombre, email, mensaje FROM mensajes;"
```

### 9b. Administración: añadir y editar discos desde la web

Solo puede hacerlo el **administrador**: el usuario cuyo correo coincide con `ADMIN_EMAIL`
(por defecto `admin@grooverecords.com`).

1. **Sin ser admin:** con la sesión de `ana@test.com` abre `http://localhost:5000/admin/disco/nuevo/`
   → te redirige al catálogo con el mensaje "Solo el administrador puede hacer esto." (y el menú no muestra el enlace).
2. Regístrate en `/registro/` con el correo `admin@grooverecords.com` (cualquier contraseña) e inicia sesión.
   El menú muestra ahora **+ Añadir disco**.
3. Pulsa **+ Añadir disco** y rellena el formulario (por ejemplo: `Queen`, `A Night at the Opera`, `Rock`,
   `1975`, `Vinilo`, `24,90`, stock `5`). Deja la URL de portada vacía para que se busque sola.
4. Se vuelve al catálogo con el mensaje "Disco añadido" y aparece el nuevo disco (con su portada real).
5. Abre ese disco: como administrador verás el botón **Editar disco**. Cambia el precio o el stock y guarda.
6. Prueba la validación: pon un precio negativo o un texto en el año → mensaje de error y no se guarda.
7. Compruébalo en la base de datos y también en pgAdmin (*View/Edit Data* de `discos`):

```bash
docker compose exec db psql -U tienda_user -d tienda -c "SELECT id, artista, titulo, precio, stock FROM discos ORDER BY id DESC LIMIT 3;"
```

### 10. Cerrar sesión

Pulsa **Salir**: el menú vuelve a mostrar *Iniciar sesión* / *Registrarse* y `/mis-compras/`
vuelve a redirigir al login.

### 11. Persistencia de los datos

```bash
docker compose down        # para y elimina los contenedores (los datos se conservan)
docker compose up -d       # al volver a arrancar, usuarios, pedidos y stock siguen ahí
```

Para empezar desde cero (borra también la base de datos y vuelve a cargar `schema.sql`):

```bash
docker compose down -v
docker compose up -d --build
```

### 12. Parar todo al terminar

```bash
docker compose down
```

## Solución de problemas

| Problema | Solución |
|---|---|
| `error during connect ... dockerDesktopLinuxEngine` | Docker Desktop no está arrancado. Ábrelo y espera a que el motor esté en marcha (`docker info`). |
| `port is already allocated` | Otro programa usa el puerto. Crea un `.env` con `WEB_PORT=5001` y/o `MAIL_WEB_PORT=8026` y ejecuta `docker compose up -d`. |
| Veo los productos antiguos o falla la consulta de `discos` | Volumen con el esquema anterior: `docker compose down -v` y `docker compose up -d --build`. |
| `relation "pedidos" does not exist` o error al finalizar la compra | Tu volumen tiene el esquema antiguo (sin carrito). Ejecuta `docker compose down -v` y `docker compose up -d --build` para recargar `schema.sql`. |
| Las portadas no aparecen (salen las dibujadas con CSS) | 1) Asegúrate de tener la versión más reciente del proyecto y reconstruye: `docker compose down -v` y `docker compose up -d --build`. 2) Mira `docker compose logs web` (líneas `[portadas]`). 3) Fuerza una nueva búsqueda: `docker compose exec web python portadas.py` (muestra cuántas encuentra). El contenedor necesita internet. |
| pgAdmin no abre o no acepta el correo | Mira `docker compose logs pgadmin`. El correo debe tener formato válido (no `.local`). Si cambiaste `PGADMIN_EMAIL`/`PASSWORD` tras la primera vez: `docker compose down -v`. |
| No me aparece "+ Añadir disco" | Debes iniciar sesión con el correo de `ADMIN_EMAIL` (por defecto `admin@grooverecords.com`; regístralo primero). |
| Puerto 5050 ocupado | Pon `PGADMIN_PORT=5051` en `.env` y ejecuta `docker compose up -d`. |
| La web no conecta con la base de datos | Revisa `docker compose logs db`; espera a que `tienda_db` esté `healthy`. |
| No llegan correos a Mailpit | Revisa `docker compose logs web` (los fallos de envío se imprimen con `[correo]`). |
| Quiero enviar correos reales | Copia `.env.example` a `.env`, descomenta las variables `MAIL_*` y ejecuta `docker compose up -d`. |

## Ejecución sin Docker (opcional, desarrollo local)

Requiere un PostgreSQL local con la base `tienda` creada y cargada con `schema.sql`:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DB_HOST=localhost DB_NAME=tienda DB_USER=tienda_user DB_PASSWORD=tienda_pass
python app.py
```

## Checklist del RA1 (c, e, f)

| Criterio | Cómo se cumple | Cómo comprobarlo |
|---|---|---|
| **c)** Se han instalado y configurado servidores Web y de bases de datos | Servidor web/aplicaciones: Gunicorn + Flask en `tienda_web` (`Dockerfile`). Servidor de BD: PostgreSQL 16 en `tienda_db`, con volumen persistente, healthcheck y `schema.sql` cargado al inicio. pgAdmin para administrarla. Orquestado en `docker-compose.yml`. | `docker compose ps` (4 contenedores `running`), paso 2, 2b y 3 |
| **e)** Se han añadido y configurado los componentes y módulos necesarios para el procesamiento de código en el servidor | Python 3.12 y dependencias de `requirements.txt` (Flask/Jinja2, psycopg2, python-dotenv, Gunicorn) instaladas en la imagen; módulos propios `db.py`, `correo.py` (smtplib), `portadas.py`; plantillas Jinja2; configuración por variables de entorno. | `docker compose exec web pip list`, pasos 3 a 9b |
| **f)** Se ha instalado y configurado el acceso a bases de datos | `db.py` conecta con PostgreSQL usando psycopg2 y las variables `DB_*` (host `db` dentro de la red de Docker), consultas parametrizadas (`%s`), transacciones (`db.transaccion()`, usada al finalizar el pedido), con usuario y contraseña propios configurables en `.env`. | `docker compose exec web python -c "import db; print(db.consultar('SELECT count(*) FROM discos'))"`, pasos 2, 6, 8 y 9b |
