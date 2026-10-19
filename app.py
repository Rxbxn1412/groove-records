import os
from functools import wraps

from dotenv import load_dotenv
from flask import Flask
from flask import request
from flask import render_template
from flask import redirect
from flask import url_for
from flask import session
from flask import flash
from werkzeug.security import generate_password_hash, check_password_hash

import db
from correo import enviar_correo
from portadas import completar_portadas

load_dotenv()

# Creamos una instancia de Flask
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'cambia-esta-clave')

FORMATOS = ('Vinilo', 'CD')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@grooverecords.com').lower()


# Decorador para proteger las rutas que requieren sesión iniciada
def login_requerido(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Debes iniciar sesión para acceder.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


# Decorador para las rutas de administración (solo el administrador)
def admin_requerido(f):
    @wraps(f)
    @login_requerido
    def wrapper(*args, **kwargs):
        if not session.get('es_admin'):
            flash('Solo el administrador puede hacer esto.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Páginas públicas (método GET)
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    # Parámetros GET del buscador: /?q=pink&formato=Vinilo&genero=Rock
    q = request.args.get('q', '').strip()
    formato = request.args.get('formato', '')
    genero = request.args.get('genero', '')

    sql = 'SELECT * FROM discos WHERE 1 = 1'
    params = []

    if q:
        sql += ' AND (titulo ILIKE %s OR artista ILIKE %s)'
        params += [f'%{q}%', f'%{q}%']
    if formato in FORMATOS:
        sql += ' AND formato = %s'
        params.append(formato)
    if genero:
        sql += ' AND genero = %s'
        params.append(genero)

    sql += ' ORDER BY artista, anio'

    discos = db.consultar(sql, tuple(params))
    generos = db.consultar('SELECT DISTINCT genero FROM discos ORDER BY genero')

    # Busca las portadas reales que aún no tengamos guardadas
    completar_portadas(discos)

    return render_template('index.html', discos=discos, generos=generos,
                           q=q, formato=formato, genero=genero)


@app.route('/disco/<int:id>')
def disco(id):
    d = db.consultar('SELECT * FROM discos WHERE id = %s', (id,), uno=True)
    if d is None:
        return render_template('404.html'), 404
    completar_portadas([d])
    return render_template('disco.html', disco=d)


@app.route('/contacto/', methods=['GET', 'POST'])
def contacto():
    # Formulario que envía los datos a la misma ruta (como el ejemplo 11)
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        mensaje = request.form['mensaje']

        db.ejecutar(
            'INSERT INTO mensajes (nombre, email, mensaje) VALUES (%s, %s, %s)',
            (nombre, email, mensaje))

        enviar_correo(
            email,
            'Hemos recibido tu mensaje - Groove Records',
            f'Hola {nombre},\n\nGracias por escribirnos. Hemos recibido tu '
            f'mensaje y te responderemos lo antes posible.\n\n'
            f'Tu mensaje:\n{mensaje}\n\nGroove Records')

        return render_template('contacto.html', nombre=nombre, email=email)
    return render_template('contacto.html')


# ---------------------------------------------------------------------------
# Registro e inicio de sesión
# ---------------------------------------------------------------------------
@app.get('/registro/')
def registro_form():
    return render_template('registro.html')


@app.post('/registro/')
def registro():
    # Obtenemos los parámetros del formulario
    nombre = request.form['nombre']
    email = request.form['email']
    password = request.form['password']

    existente = db.consultar(
        'SELECT id FROM usuarios WHERE email = %s', (email,), uno=True)
    if existente:
        flash('Ya existe un usuario con ese correo electrónico.', 'error')
        return redirect(url_for('registro_form'))

    db.ejecutar(
        'INSERT INTO usuarios (nombre, email, password) VALUES (%s, %s, %s)',
        (nombre, email, generate_password_hash(password)))

    # Correo automático de bienvenida
    enviar_correo(
        email,
        'Bienvenido a Groove Records',
        f'Hola {nombre},\n\nTu cuenta se ha creado correctamente. '
        f'Ya puedes iniciar sesión y empezar a llenar tu colección de '
        f'vinilos y CD.\n\nGroove Records')

    flash('Registro completado. Ya puedes iniciar sesión.', 'ok')
    return redirect(url_for('login'))


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        usuario = db.consultar(
            'SELECT * FROM usuarios WHERE email = %s', (email,), uno=True)

        if usuario and check_password_hash(usuario['password'], password):
            session['usuario_id'] = usuario['id']
            session['usuario_nombre'] = usuario['nombre']
            session['es_admin'] = usuario['email'].lower() == ADMIN_EMAIL
            flash(f"Bienvenido, {usuario['nombre']}.", 'ok')
            return redirect(url_for('index'))

        flash('Correo o contraseña incorrectos.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado la sesión.', 'ok')
    return redirect(url_for('index'))


# ---------------------------------------------------------------------------
# Carrito de la compra
# El carrito vive en la sesión: {'id_del_disco': cantidad}
# ---------------------------------------------------------------------------
class StockInsuficiente(Exception):
    pass


def leer_carrito():
    """Devuelve (lineas, total) con los datos actuales de la base de datos."""
    carrito = session.get('carrito', {})
    if not carrito:
        return [], 0

    discos = db.consultar(
        'SELECT * FROM discos WHERE id = ANY(%s) ORDER BY artista, titulo',
        ([int(i) for i in carrito],))

    lineas = []
    for d in discos:
        cantidad = carrito[str(d['id'])]
        lineas.append({'disco': d, 'cantidad': cantidad,
                       'subtotal': d['precio'] * cantidad})
    return lineas, sum(l['subtotal'] for l in lineas)


@app.context_processor
def contador_carrito():
    # Número de unidades en el carrito, disponible en todas las plantillas
    return {'carrito_items': sum(session.get('carrito', {}).values())}


@app.get('/carrito/')
def carrito():
    lineas, total = leer_carrito()
    return render_template('carrito.html', lineas=lineas, total=total)


@app.post('/carrito/anadir/<int:id>')
def carrito_anadir(id):
    d = db.consultar('SELECT * FROM discos WHERE id = %s', (id,), uno=True)
    if d is None:
        return render_template('404.html'), 404

    try:
        cantidad = int(request.form.get('cantidad', 1))
    except ValueError:
        cantidad = 0
    if cantidad < 1:
        flash('Cantidad no válida.', 'error')
        return redirect(url_for('disco', id=id))

    carrito = session.get('carrito', {})
    nueva = carrito.get(str(id), 0) + cantidad
    if nueva > d['stock']:
        flash(f"Solo quedan {d['stock']} unidades de «{d['titulo']}».", 'error')
        return redirect(url_for('disco', id=id))

    carrito[str(id)] = nueva
    session['carrito'] = carrito
    flash(f"«{d['titulo']}» añadido al carrito.", 'ok')
    return redirect(url_for('disco', id=id))


@app.post('/carrito/actualizar/<int:id>')
def carrito_actualizar(id):
    carrito = session.get('carrito', {})
    if str(id) in carrito:
        d = db.consultar('SELECT stock FROM discos WHERE id = %s', (id,), uno=True)
        try:
            cantidad = int(request.form.get('cantidad', 1))
        except ValueError:
            cantidad = 0
        if d is None or cantidad < 1:
            carrito.pop(str(id))
        elif cantidad > d['stock']:
            flash(f"Solo quedan {d['stock']} unidades.", 'error')
        else:
            carrito[str(id)] = cantidad
        session['carrito'] = carrito
    return redirect(url_for('carrito'))


@app.post('/carrito/quitar/<int:id>')
def carrito_quitar(id):
    carrito = session.get('carrito', {})
    carrito.pop(str(id), None)
    session['carrito'] = carrito
    return redirect(url_for('carrito'))


@app.post('/carrito/vaciar')
def carrito_vaciar():
    session.pop('carrito', None)
    flash('Carrito vaciado.', 'ok')
    return redirect(url_for('carrito'))


@app.post('/carrito/finalizar')
@login_requerido
def carrito_finalizar():
    carrito = session.get('carrito', {})
    if not carrito:
        flash('Tu carrito está vacío.', 'error')
        return redirect(url_for('carrito'))

    resumen = []
    total = 0
    try:
        # Todo el pedido se guarda en una sola transacción: o se completa
        # entero o no se guarda nada (si falla el stock de un disco, ROLLBACK)
        with db.transaccion() as cur:
            cur.execute('INSERT INTO pedidos (usuario_id, total) '
                        'VALUES (%s, 0) RETURNING id', (session['usuario_id'],))
            pedido_id = cur.fetchone()['id']

            for id_disco, cantidad in sorted(carrito.items(), key=lambda x: int(x[0])):
                # Descuenta el stock solo si quedan unidades suficientes
                cur.execute(
                    'UPDATE discos SET stock = stock - %s '
                    'WHERE id = %s AND stock >= %s '
                    'RETURNING artista, titulo, formato, precio',
                    (cantidad, int(id_disco), cantidad))
                d = cur.fetchone()
                if d is None:
                    raise StockInsuficiente(id_disco)

                subtotal = d['precio'] * cantidad
                cur.execute(
                    'INSERT INTO compras (pedido_id, disco_id, cantidad, '
                    'precio_unitario, total) VALUES (%s, %s, %s, %s, %s)',
                    (pedido_id, int(id_disco), cantidad, d['precio'], subtotal))
                resumen.append((d, cantidad, subtotal))
                total += subtotal

            cur.execute('UPDATE pedidos SET total = %s WHERE id = %s',
                        (total, pedido_id))
    except StockInsuficiente:
        flash('Algún disco ya no tiene stock suficiente. Revisa el carrito; '
              'no se ha realizado ningún cobro.', 'error')
        return redirect(url_for('carrito'))

    # Correo automático con el resumen de TODO el pedido
    usuario = db.consultar(
        'SELECT * FROM usuarios WHERE id = %s',
        (session['usuario_id'],), uno=True)
    lineas = '\n'.join(
        f"  {c} x {d['artista']} - {d['titulo']} ({d['formato']}): {s:.2f} €"
        for d, c, s in resumen)
    enviar_correo(
        usuario['email'],
        f'Confirmación de tu pedido nº {pedido_id} - Groove Records',
        f"Hola {usuario['nombre']},\n\nGracias por tu compra. "
        f"Este es el resumen de tu pedido nº {pedido_id}:\n\n"
        f"{lineas}\n\n  TOTAL: {total:.2f} €\n\n"
        f"Te avisaremos cuando salga de nuestro almacén.\n\nGroove Records")

    session.pop('carrito', None)
    flash('Pedido realizado. Te hemos enviado un correo de confirmación.', 'ok')
    return redirect(url_for('mis_compras'))


@app.route('/mis-compras/')
@login_requerido
def mis_compras():
    filas = db.consultar(
        'SELECT p.id AS pedido_id, p.total AS total_pedido, p.fecha, '
        'c.cantidad, c.precio_unitario, c.total AS subtotal, '
        'd.artista, d.titulo, d.formato '
        'FROM pedidos p '
        'JOIN compras c ON c.pedido_id = p.id '
        'JOIN discos d ON d.id = c.disco_id '
        'WHERE p.usuario_id = %s ORDER BY p.fecha DESC, p.id DESC, c.id',
        (session['usuario_id'],))

    # Agrupamos las líneas por pedido
    pedidos = {}
    for f in filas:
        p = pedidos.setdefault(f['pedido_id'], {
            'id': f['pedido_id'], 'total': f['total_pedido'],
            'fecha': f['fecha'], 'lineas': []})
        p['lineas'].append(f)
    return render_template('compras.html', pedidos=list(pedidos.values()))


# ---------------------------------------------------------------------------
# Administración del catálogo (solo administrador)
# ---------------------------------------------------------------------------
def leer_formulario_disco():
    """Lee y valida los campos del formulario de disco. Devuelve (datos, error)."""
    f = request.form
    try:
        datos = {
            'artista': f['artista'].strip(),
            'titulo': f['titulo'].strip(),
            'genero': f['genero'].strip(),
            'anio': int(f['anio']),
            'formato': f['formato'],
            'descripcion': f.get('descripcion', '').strip(),
            'precio': round(float(f['precio'].replace(',', '.')), 2),
            'stock': int(f['stock']),
            'portada_url': f.get('portada_url', '').strip() or None,
        }
    except (KeyError, ValueError):
        return None, 'Revisa los campos numéricos (año, precio y stock).'

    if not (datos['artista'] and datos['titulo'] and datos['genero']):
        return None, 'Artista, título y género son obligatorios.'
    if datos['formato'] not in FORMATOS:
        return None, 'Formato no válido.'
    if datos['precio'] < 0 or datos['stock'] < 0:
        return None, 'El precio y el stock no pueden ser negativos.'
    return datos, None


@app.get('/admin/disco/nuevo/')
@admin_requerido
def disco_nuevo_form():
    return render_template('admin_disco.html', disco=None, formatos=FORMATOS)


@app.post('/admin/disco/nuevo/')
@admin_requerido
def disco_nuevo():
    datos, error = leer_formulario_disco()
    if error:
        flash(error, 'error')
        return render_template('admin_disco.html', disco=request.form,
                               formatos=FORMATOS), 400

    db.ejecutar(
        'INSERT INTO discos (artista, titulo, genero, anio, formato, '
        'descripcion, precio, stock, portada_url) '
        'VALUES (%(artista)s, %(titulo)s, %(genero)s, %(anio)s, %(formato)s, '
        '%(descripcion)s, %(precio)s, %(stock)s, %(portada_url)s)', datos)
    flash(f"Disco «{datos['titulo']}» añadido al catálogo.", 'ok')
    return redirect(url_for('index'))


@app.get('/admin/disco/<int:id>/editar/')
@admin_requerido
def disco_editar_form(id):
    d = db.consultar('SELECT * FROM discos WHERE id = %s', (id,), uno=True)
    if d is None:
        return render_template('404.html'), 404
    return render_template('admin_disco.html', disco=d, formatos=FORMATOS)


@app.post('/admin/disco/<int:id>/editar/')
@admin_requerido
def disco_editar(id):
    datos, error = leer_formulario_disco()
    if error:
        flash(error, 'error')
        return redirect(url_for('disco_editar_form', id=id))

    datos['id'] = id
    db.ejecutar(
        'UPDATE discos SET artista = %(artista)s, titulo = %(titulo)s, '
        'genero = %(genero)s, anio = %(anio)s, formato = %(formato)s, '
        'descripcion = %(descripcion)s, precio = %(precio)s, '
        'stock = %(stock)s, portada_url = %(portada_url)s WHERE id = %(id)s',
        datos)
    flash('Disco actualizado.', 'ok')
    return redirect(url_for('disco', id=id))


# ---------------------------------------------------------------------------
# Gestión de errores
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


# Programa principal
if __name__ == '__main__':
    app.run(debug=True)
