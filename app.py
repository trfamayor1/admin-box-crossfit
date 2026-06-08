from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import tempfile
import re
import requests
from datetime import datetime, date, timedelta

app = Flask(__name__)
CORS(app)

# ============================================
# RATE LIMITING
# ============================================
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# ============================================
# CACHÉ PARA REDUCIR PETICIONES A GOOGLE SHEETS
# ============================================
cache = {}
CACHE_TTL = 30  # segundos

def get_cached_sheet(nombre_hoja):
    from time import time
    key = nombre_hoja
    now = time()
    if key in cache and (now - cache[key]['time']) < CACHE_TTL:
        return cache[key]['data']
    data = get_sheet(nombre_hoja).get_all_records()
    cache[key] = {'data': data, 'time': now}
    return data

def invalidate_cache(nombre_hoja):
    if nombre_hoja in cache:
        del cache[nombre_hoja]

# ============================================
# FUNCIONES AUXILIARES
# ============================================
def safe_str(value):
    return '' if value is None else str(value)

def validar_email(email):
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(patron, email) is not None

# ============================================
# SUBIR FOTO A IMGBB
# ============================================
def subir_a_imgbb(archivo_temporal):
    try:
        api_key = "6d207e02198a847aa98d0a2a901485a5"
        with open(archivo_temporal, 'rb') as f:
            files = {'image': f}
            data = {'key': api_key}
            response = requests.post('https://api.imgbb.com/1/upload', data=data, files=files)
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 200:
                return result['data']['url']
        return None
    except Exception as e:
        print(f"Error subiendo a ImgBB: {e}")
        return None

# ============================================
# ANTI-CACHÉ
# ============================================
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# ============================================
# CONEXIÓN A GOOGLE SHEETS
# ============================================
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_sheet(nombre_hoja):
    if os.environ.get('GOOGLE_CREDENTIALS'):
        creds_dict = json.loads(os.environ.get('GOOGLE_CREDENTIALS'))
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    else:
        creds = Credentials.from_service_account_file("credenciales.json", scopes=scope)
    
    client = gspread.authorize(creds)
    sheet = client.open("BOX_CROSSFIT_ADMIN").worksheet(nombre_hoja)
    return sheet

# ============================================
# PÁGINA PRINCIPAL
# ============================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

# ============================================
# PWA ADMINISTRADOR
# ============================================
@app.route('/ADMIN/manifest.json')
def admin_manifest():
    return send_from_directory('ADMIN', 'manifest.json')

@app.route('/ADMIN/sw.js')
def admin_sw():
    return send_from_directory('ADMIN', 'sw.js')

@app.route('/ADMIN/static/<path:path>')
def admin_static(path):
    return send_from_directory('ADMIN/static', path)

# ============================================
# PWA CLIENTE
# ============================================
@app.route('/CLIENTE/manifest.json')
def cliente_manifest():
    return send_from_directory('CLIENTE', 'manifest.json')

@app.route('/CLIENTE/sw.js')
def cliente_sw():
    return send_from_directory('CLIENTE', 'sw.js')

@app.route('/CLIENTE/static/<path:path>')
def cliente_static(path):
    return send_from_directory('CLIENTE/static', path)

# ============================================
# RUTAS ADMINISTRADOR
# ============================================
@app.route('/admin/login')
def admin_login():
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin/dashboard.html')

@app.route('/admin/cliente_perfil')
def admin_cliente_perfil():
    return render_template('admin/cliente_perfil.html')

# ============================================
# API ADMINISTRADOR
# ============================================
@app.route('/admin/verificar', methods=['POST'])
@limiter.limit("50 per minute")
def admin_verificar():
    data = request.json
    email = data.get('email')
    
    if not validar_email(email):
        return jsonify({"error": "Email no válido"}), 400
    
    try:
        sheet = get_sheet("admins")
        registros = sheet.get_all_records()
        for registro in registros:
            if registro.get('email') == email:
                return jsonify({"autorizado": True})
        return jsonify({"autorizado": False, "error": "Email no autorizado"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# ADMIN - CLIENTES CRUD
# ============================================
@app.route('/admin/clientes', methods=['GET'])
def admin_obtener_clientes():
    try:
        sheet = get_sheet("clientes")
        return jsonify(sheet.get_all_records())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/clientes', methods=['POST'])
def admin_crear_cliente():
    try:
        data = request.json
        sheet = get_sheet("clientes")
        registros = sheet.get_all_records()
        nuevo_id = len(registros) + 1
        
        membresia_id = data.get('membresia_id', '')
        clases_restantes = 0
        try:
            sheet_memb = get_sheet("membresias")
            membresias = sheet_memb.get_all_records()
            for m in membresias:
                if str(m.get('id')) == str(membresia_id):
                    clases_restantes = int(m.get('clases_por_mes', 0))
                    break
        except:
            pass
        
        sheet.append_row([
            str(nuevo_id),
            str(data.get('nombre', '')),
            str(data.get('email', '')),
            str(data.get('celular', '')),
            str(data.get('eps', '')),
            str(data.get('foto_url', '')),
            str(membresia_id),
            str(clases_restantes),
            str(data.get('fecha_vencimiento', '')),
            str(data.get('activo', 'TRUE'))
        ])
        invalidate_cache("clientes")
        return jsonify({"mensaje": "Cliente creado", "id": nuevo_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/clientes/<int:cliente_id>', methods=['PUT'])
def admin_actualizar_cliente(cliente_id):
    try:
        data = request.json
        
        sheet = get_sheet("clientes")
        registros = sheet.get_all_records()
        
        fila_index = None
        for i, registro in enumerate(registros, start=2):
            if int(registro.get('id')) == cliente_id:
                fila_index = i
                break
        
        if not fila_index:
            return jsonify({"error": "Cliente no encontrado"}), 404
        
        sheet.update_cell(fila_index, 1, str(cliente_id))
        sheet.update_cell(fila_index, 2, str(data.get('nombre', '')))
        sheet.update_cell(fila_index, 3, str(data.get('email', '')))
        sheet.update_cell(fila_index, 4, str(data.get('celular', '')))
        sheet.update_cell(fila_index, 5, str(data.get('eps', '')))
        sheet.update_cell(fila_index, 6, str(data.get('foto_url', '')))
        sheet.update_cell(fila_index, 7, str(data.get('membresia_id', '')))
        sheet.update_cell(fila_index, 8, str(data.get('clases_restantes_mes', 0)))
        sheet.update_cell(fila_index, 9, str(data.get('fecha_vencimiento', '')))
        sheet.update_cell(fila_index, 10, str(data.get('activo', 'TRUE')))
        
        invalidate_cache("clientes")
        return jsonify({"mensaje": "Cliente actualizado correctamente"})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/admin/clientes/<int:cliente_id>', methods=['DELETE'])
def admin_eliminar_cliente(cliente_id):
    try:
        sheet = get_sheet("clientes")
        registros = sheet.get_all_records()
        
        for i, r in enumerate(registros, start=2):
            if int(r.get('id')) == cliente_id:
                sheet.delete_rows(i)
                invalidate_cache("clientes")
                return jsonify({"mensaje": "Cliente eliminado"})
        return jsonify({"error": "No encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# ADMIN - MEMBRESIAS
# ============================================
@app.route('/admin/membresias', methods=['GET'])
def admin_obtener_membresias():
    try:
        sheet = get_sheet("membresias")
        return jsonify(sheet.get_all_records())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# ADMIN - CLASES
# ============================================
@app.route('/admin/clases', methods=['GET'])
def admin_obtener_clases():
    try:
        sheet = get_sheet("clases")
        registros = sheet.get_all_records()
        
        from datetime import datetime as dt
        ahora = dt.now()
        
        clases_futuras = []
        for c in registros:
            fecha_clase = c.get('fecha', '')
            hora_clase = c.get('hora', '')
            if not fecha_clase or not hora_clase:
                continue
            
            try:
                datetime_clase = dt.strptime(f"{fecha_clase} {hora_clase}", "%Y-%m-%d %H:%M")
                # Solo mostrar clases que NO han pasado
                if datetime_clase >= ahora:
                    clases_futuras.append(c)
            except:
                continue
        
        clases_futuras.sort(key=lambda x: x.get('fecha', ''))
        
        return jsonify(clases_futuras)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    

@app.route('/admin/clases', methods=['POST'])
def admin_crear_clase():
    try:
        data = request.json
        sheet = get_sheet("clases")
        registros = sheet.get_all_records()
        nuevo_id = len(registros) + 1
        
        # Guardar la hora exactamente como viene (sin conversión)
        fecha = data.get('fecha', '')
        hora = data.get('hora', '')
        cupos = data.get('cupos_maximos', 0)
        
        sheet.append_row([
            nuevo_id, fecha, hora, cupos, 0, 'admin'
        ])
        invalidate_cache("clases")
        return jsonify({"mensaje": "Clase creada", "id": nuevo_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/admin/clases/<int:clase_id>', methods=['DELETE'])
def admin_eliminar_clase(clase_id):
    try:
        sheet = get_sheet("clases")
        registros = sheet.get_all_records()
        for i, r in enumerate(registros, start=2):
            if r.get('id') == clase_id:
                sheet.delete_rows(i)
                invalidate_cache("clases")
                return jsonify({"mensaje": "Clase eliminada"})
        return jsonify({"error": "No encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# ADMIN - ANUNCIOS
# ============================================
@app.route('/admin/anuncios', methods=['GET'])
def admin_obtener_anuncios():
    try:
        sheet = get_sheet("anuncios")
        registros = sheet.get_all_records()
        return jsonify(registros)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/anuncios', methods=['POST'])
def admin_crear_anuncio():
    try:
        data = request.json
        sheet = get_sheet("anuncios")
        registros = sheet.get_all_records()
        nuevo_id = len(registros) + 1
        fecha_actual = date.today().isoformat()
        
        sheet.append_row([
            nuevo_id,
            data.get('titulo', ''),
            data.get('texto', ''),
            data.get('imagen_url', ''),
            fecha_actual,
            'TRUE'
        ])
        invalidate_cache("anuncios")
        return jsonify({"mensaje": "Anuncio creado", "id": nuevo_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/anuncios/<int:anuncio_id>', methods=['DELETE'])
def admin_eliminar_anuncio(anuncio_id):
    try:
        sheet = get_sheet("anuncios")
        registros = sheet.get_all_records()
        for i, r in enumerate(registros, start=2):
            if r.get('id') == anuncio_id:
                sheet.delete_rows(i)
                invalidate_cache("anuncios")
                return jsonify({"mensaje": "Anuncio eliminado"})
        return jsonify({"error": "No encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/anuncios/<int:anuncio_id>', methods=['PUT'])
def admin_toggle_anuncio(anuncio_id):
    try:
        data = request.json
        vigente = data.get('vigente', 'TRUE')
        
        sheet = get_sheet("anuncios")
        registros = sheet.get_all_records()
        
        fila_index = None
        for i, r in enumerate(registros, start=2):
            if r.get('id') == anuncio_id:
                fila_index = i
                break
        
        if fila_index:
            sheet.update_cell(fila_index, 6, vigente)
            invalidate_cache("anuncios")
            return jsonify({"mensaje": "Anuncio actualizado"})
        return jsonify({"error": "Anuncio no encontrado"}), 404
    except Exception as e:
        print(f"Error en toggle anuncio: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/admin/subir-imagen-anuncio', methods=['POST'])
def admin_subir_imagen_anuncio():
    imagen = request.files.get('imagen')
    
    if not imagen:
        return jsonify({"error": "No se recibió imagen"}), 400
    
    if not imagen.content_type.startswith('image/'):
        return jsonify({"error": "Solo se permiten imágenes"}), 400
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
        imagen.save(tmp.name)
        tmp_path = tmp.name
    
    url_publica = subir_a_imgbb(tmp_path)
    os.unlink(tmp_path)
    
    if not url_publica:
        return jsonify({"error": "Error al subir la imagen"}), 500
    
    return jsonify({"url": url_publica})

# ============================================
# ADMIN - VER RM DE CLIENTE
# ============================================
@app.route('/admin/rm/<string:email>', methods=['GET'])
def admin_obtener_rm_cliente(email):
    try:
        sheet_clientes = get_sheet("clientes")
        clientes = sheet_clientes.get_all_records()
        cliente_id = None
        for c in clientes:
            if c.get('email') == email:
                cliente_id = c.get('id')
                break
        
        if not cliente_id:
            return jsonify([])
        
        sheet_rm = get_sheet("rm_records")
        registros = sheet_rm.get_all_records()
        
        resultado = []
        for r in registros:
            if r.get('cliente_id') == cliente_id:
                resultado.append({
                    "id": r.get('id'),
                    "habilidad_id": r.get('habilidad_id'),
                    "peso_kg": r.get('peso_kg'),
                    "fecha_registro": r.get('fecha_registro')
                })
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# RUTAS CLIENTE (HTML)
# ============================================
@app.route('/cliente/login')
def cliente_login():
    return render_template('cliente/login.html')

@app.route('/cliente/perfil')
def cliente_perfil():
    return render_template('cliente/perfil.html')

@app.route('/cliente/clases')
def cliente_clases_html():
    return render_template('cliente/clases.html')

@app.route('/cliente/mis-reservas')
def cliente_mis_reservas_html():
    return render_template('cliente/mis-reservas.html')

@app.route('/cliente/rm')
def cliente_rm_html():
    return render_template('cliente/rm.html')

# ============================================
# API PÚBLICA CLASES (24h - DESDE HOY 00:00 LOCAL)
# ============================================
@app.route('/api/clases', methods=['GET'])
def api_obtener_clases():
    try:
        # Obtener email del cliente desde la URL
        email = request.args.get('email')
        
        sheet = get_sheet("clases")
        registros = sheet.get_all_records()
        
        from datetime import datetime as dt
        ahora = dt.now()
        limite_24h = ahora + timedelta(hours=24)
        
        # ============================================
        # VERIFICAR SI EL CLIENTE YA TIENE RESERVA ACTIVA
        # ============================================
        tiene_reserva_activa = False
        if email:
            try:
                sheet_clientes = get_sheet("clientes")
                clientes = sheet_clientes.get_all_records()
                cliente_id = None
                for c in clientes:
                    if c.get('email') == email:
                        cliente_id = c.get('id')
                        break
                
                if cliente_id:
                    sheet_reservas = get_sheet("reservas")
                    reservas = sheet_reservas.get_all_records()
                    sheet_clases_verificar = get_sheet("clases")
                    clases_verificar = sheet_clases_verificar.get_all_records()
                    hoy = date.today().isoformat()
                    
                    for r in reservas:
                        if r.get('cliente_id') == cliente_id and r.get('estado') == 'confirmada':
                            for c in clases_verificar:
                                if c.get('id') == r.get('clase_id'):
                                    fecha_clase = c.get('fecha', '')
                                    if fecha_clase and fecha_clase >= hoy:
                                        tiene_reserva_activa = True
                                        break
                            if tiene_reserva_activa:
                                break
            except Exception as e:
                print(f"Error verificando reserva activa: {e}")
        
        # Si tiene reserva activa, devolver lista vacía
        if tiene_reserva_activa:
            return jsonify([])
        
        # ============================================
        # FILTRAR CLASES DISPONIBLES (24h)
        # ============================================
        clases_disponibles = []
        ids_vistos = set()
        
        for c in registros:
            clase_id = c.get('id')
            if clase_id in ids_vistos:
                continue
            ids_vistos.add(clase_id)
            
            fecha_clase = c.get('fecha', '')
            hora_clase = c.get('hora', '')
            if not fecha_clase or not hora_clase:
                continue
            
            try:
                datetime_clase = dt.strptime(f"{fecha_clase} {hora_clase}", "%Y-%m-%d %H:%M")
                if datetime_clase >= ahora and datetime_clase <= limite_24h:
                    disponibles = int(c.get('cupos_maximos', 0)) - int(c.get('cupos_ocupados', 0))
                    if disponibles > 0:
                        clases_disponibles.append(c)
            except:
                continue
        
        return jsonify(clases_disponibles)
    except Exception as e:
        print(f"Error en api/clases: {e}")
        return jsonify({"error": str(e)}), 500
    
    
    

    

# ============================================
# API PÚBLICA HABILIDADES
# ============================================
@app.route('/api/habilidades', methods=['GET'])
def api_obtener_habilidades():
    try:
        sheet = get_sheet("habilidades")
        registros = sheet.get_all_records()
        return jsonify(registros)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# API PÚBLICA RM
# ============================================
@app.route('/api/rm', methods=['GET'])
def api_obtener_rm():
    email = request.args.get('email')
    if not email:
        return jsonify([])
    
    try:
        sheet_clientes = get_sheet("clientes")
        clientes = sheet_clientes.get_all_records()
        cliente_id = None
        for c in clientes:
            if c.get('email') == email:
                cliente_id = c.get('id')
                break
        
        if not cliente_id:
            return jsonify([])
        
        sheet_rm = get_sheet("rm_records")
        registros = sheet_rm.get_all_records()
        
        resultado = []
        for r in registros:
            if r.get('cliente_id') == cliente_id:
                resultado.append({
                    "id": r.get('id'),
                    "habilidad_id": r.get('habilidad_id'),
                    "peso_kg": r.get('peso_kg'),
                    "fecha_registro": r.get('fecha_registro')
                })
        return jsonify(resultado)
    except Exception as e:
        return jsonify([])

# ============================================
# API CLIENTE - LOGIN Y PERFIL
# ============================================
@app.route('/cliente/login', methods=['POST'])
@limiter.limit("50 per minute")
def cliente_login_post():
    data = request.json
    email = data.get('email')
    
    if not validar_email(email):
        return jsonify({"error": "Email no válido"}), 400
    
    try:
        sheet = get_sheet("clientes")
        registros = sheet.get_all_records()
        for registro in registros:
            if registro.get('email') == email:
                if registro.get('activo') != 'TRUE':
                    return jsonify({"error": "Usuario inactivo"}), 401
                
                # Validar membresía vencida
                fecha_vencimiento = registro.get('fecha_vencimiento', '')
                if fecha_vencimiento:
                    try:
                        fecha_venc = datetime.strptime(fecha_vencimiento, "%Y-%m-%d").date()
                        if fecha_venc < date.today():
                            return jsonify({"error": "Tu membresía ha vencido. Contacta al administrador."}), 401
                    except:
                        pass
                
                return jsonify({
                    "mensaje": f"Bienvenido {registro.get('nombre')}",
                    "email": email,
                    "nombre": registro.get('nombre')
                })
        return jsonify({"error": "Email no registrado"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/cliente/perfil', methods=['POST'])
def cliente_obtener_perfil():
    data = request.json
    email = data.get('email')
    if not email:
        return jsonify({"error": "Email requerido"}), 400
    try:
        sheet = get_sheet("clientes")
        registros = sheet.get_all_records()
        for registro in registros:
            if registro.get('email') == email:
                return jsonify({
                    "id": registro.get('id'),
                    "nombre": registro.get('nombre', ''),
                    "email": registro.get('email', ''),
                    "celular": registro.get('celular', ''),
                    "eps": registro.get('eps', ''),
                    "membresia_id": registro.get('membresia_id', ''),
                    "clases_restantes": registro.get('clases_restantes_mes', 0),
                    "fecha_vencimiento": registro.get('fecha_vencimiento', ''),
                    "activo": registro.get('activo', 'TRUE'),
                    "foto_url": registro.get('foto_url', '')
                })
        return jsonify({"error": "Perfil no encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/cliente/logout', methods=['POST'])
def cliente_logout():
    return jsonify({"mensaje": "Sesión cerrada"})

# ============================================
# API CLIENTE - ANUNCIOS
# ============================================
@app.route('/cliente/anuncios', methods=['GET'])
def cliente_obtener_anuncios():
    try:
        sheet = get_sheet("anuncios")
        registros = sheet.get_all_records()
        vigentes = [a for a in registros if a.get('vigente') == 'TRUE']
        vigentes.sort(key=lambda x: x.get('fecha_publicacion', ''), reverse=True)
        return jsonify(vigentes)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# API CLIENTE - RM (POST, PUT, DELETE)
# ============================================
@app.route('/cliente/rm', methods=['POST'])
def cliente_agregar_rm():
    data = request.json
    email = data.get('email')
    habilidad_id = data.get('habilidad_id')
    peso_kg = data.get('peso_kg')
    
    try:
        sheet_clientes = get_sheet("clientes")
        clientes = sheet_clientes.get_all_records()
        cliente_id = None
        for c in clientes:
            if c.get('email') == email:
                cliente_id = c.get('id')
                break
        
        if not cliente_id:
            return jsonify({"error": "Cliente no encontrado"}), 404
        
        sheet_rm = get_sheet("rm_records")
        registros = sheet_rm.get_all_records()
        nuevo_id = len(registros) + 1
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        
        sheet_rm.append_row([
            str(nuevo_id), str(cliente_id), str(habilidad_id), str(peso_kg), fecha_actual
        ])
        return jsonify({"mensaje": "RM guardado correctamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/cliente/rm', methods=['PUT'])
def cliente_actualizar_rm():
    data = request.json
    email = data.get('email')
    rm_id = data.get('id')
    habilidad_id = data.get('habilidad_id')
    peso_kg = data.get('peso_kg')
    
    try:
        sheet_clientes = get_sheet("clientes")
        clientes = sheet_clientes.get_all_records()
        cliente_id = None
        for c in clientes:
            if c.get('email') == email:
                cliente_id = c.get('id')
                break
        
        if not cliente_id:
            return jsonify({"error": "Cliente no encontrado"}), 404
        
        sheet_rm = get_sheet("rm_records")
        registros = sheet_rm.get_all_records()
        
        fila_index = None
        for i, r in enumerate(registros, start=2):
            if r.get('id') == rm_id and r.get('cliente_id') == cliente_id:
                fila_index = i
                break
        
        if fila_index:
            sheet_rm.update(fila_index, [
                str(rm_id), str(cliente_id), str(habilidad_id), str(peso_kg), datetime.now().strftime("%Y-%m-%d")
            ])
            return jsonify({"mensaje": "RM actualizado correctamente"})
        return jsonify({"error": "RM no encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/cliente/rm', methods=['DELETE'])
def cliente_eliminar_rm():
    data = request.json
    email = data.get('email')
    rm_id = data.get('id')
    
    try:
        sheet_clientes = get_sheet("clientes")
        clientes = sheet_clientes.get_all_records()
        cliente_id = None
        for c in clientes:
            if c.get('email') == email:
                cliente_id = c.get('id')
                break
        
        if not cliente_id:
            return jsonify({"error": "Cliente no encontrado"}), 404
        
        sheet_rm = get_sheet("rm_records")
        registros = sheet_rm.get_all_records()
        
        fila_index = None
        for i, r in enumerate(registros, start=2):
            if r.get('id') == rm_id and r.get('cliente_id') == cliente_id:
                fila_index = i
                break
        
        if fila_index:
            sheet_rm.delete_rows(fila_index)
            return jsonify({"mensaje": "RM eliminado correctamente"})
        return jsonify({"error": "RM no encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# API CLIENTE - VER RM DE OTRO CLIENTE (público)
# ============================================
@app.route('/cliente/rm/publico', methods=['GET'])
def cliente_ver_rm_publico():
    email = request.args.get('email')
    if not email:
        return jsonify([])
    
    try:
        sheet_clientes = get_sheet("clientes")
        clientes = sheet_clientes.get_all_records()
        cliente_id = None
        for c in clientes:
            if c.get('email') == email:
                cliente_id = c.get('id')
                break
        
        if not cliente_id:
            return jsonify([])
        
        sheet_habilidades = get_sheet("habilidades")
        habilidades = sheet_habilidades.get_all_records()
        habilidades_dict = {h.get('id'): h.get('nombre_habilidad') for h in habilidades}
        
        sheet_rm = get_sheet("rm_records")
        registros = sheet_rm.get_all_records()
        
        resultado = []
        for r in registros:
            if r.get('cliente_id') == cliente_id:
                resultado.append({
                    "id": r.get('id'),
                    "habilidad_id": r.get('habilidad_id'),
                    "habilidad_nombre": habilidades_dict.get(r.get('habilidad_id'), 'Desconocido'),
                    "peso_kg": r.get('peso_kg'),
                    "fecha_registro": r.get('fecha_registro')
                })
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# API CLIENTE - OBTENER OTROS CLIENTES EN LA MISMA CLASE
# ============================================
@app.route('/cliente/otros-reservas', methods=['POST'])
def cliente_otros_reservas():
    data = request.json
    email_actual = data.get('email')
    clase_id = data.get('clase_id')
    
    try:
        sheet_clientes = get_sheet("clientes")
        clientes = sheet_clientes.get_all_records()
        
        cliente_actual_id = None
        for c in clientes:
            if c.get('email') == email_actual:
                cliente_actual_id = c.get('id')
                break
        
        if not cliente_actual_id:
            return jsonify([])
        
        sheet_reservas = get_sheet("reservas")
        reservas = sheet_reservas.get_all_records()
        
        otros_ids = set()
        for r in reservas:
            if r.get('clase_id') == clase_id and r.get('cliente_id') != cliente_actual_id:
                otros_ids.add(r.get('cliente_id'))
        
        resultado = []
        for c in clientes:
            if c.get('id') in otros_ids:
                resultado.append({
                    "nombre": c.get('nombre', 'Cliente'),
                    "email": c.get('email', '')
                })
        
        return jsonify(resultado)
    except Exception as e:
        print(f"Error en otros-reservas: {e}")
        return jsonify([])

# ============================================
# API CLIENTE - DATOS PÚBLICOS DE OTRO CLIENTE
# ============================================
@app.route('/cliente/datos-publicos', methods=['GET'])
def cliente_datos_publicos():
    email = request.args.get('email')
    if not email:
        return jsonify({"error": "Email requerido"}), 400
    
    try:
        sheet_clientes = get_sheet("clientes")
        clientes = sheet_clientes.get_all_records()
        cliente_info = None
        for c in clientes:
            if c.get('email') == email:
                cliente_info = {
                    "nombre": c.get('nombre', 'Cliente'),
                    "email": c.get('email', '')
                }
                break
        
        if not cliente_info:
            return jsonify({"error": "Cliente no encontrado"}), 404
        
        sheet_habilidades = get_sheet("habilidades")
        habilidades = sheet_habilidades.get_all_records()
        habilidades_dict = {h.get('id'): h.get('nombre_habilidad') for h in habilidades}
        
        sheet_rm = get_sheet("rm_records")
        registros = sheet_rm.get_all_records()
        
        rm_lista = []
        for r in registros:
            if r.get('email') == email or r.get('cliente_email') == email:
                rm_lista.append({
                    "habilidad_nombre": habilidades_dict.get(r.get('habilidad_id'), 'Desconocido'),
                    "peso_kg": r.get('peso_kg'),
                    "fecha_registro": r.get('fecha_registro')
                })
        
        if not rm_lista:
            sheet_clientes = get_sheet("clientes")
            clientes_all = sheet_clientes.get_all_records()
            cliente_id = None
            for c in clientes_all:
                if c.get('email') == email:
                    cliente_id = c.get('id')
                    break
            
            if cliente_id:
                sheet_rm = get_sheet("rm_records")
                registros = sheet_rm.get_all_records()
                for r in registros:
                    if r.get('cliente_id') == cliente_id:
                        rm_lista.append({
                            "habilidad_nombre": habilidades_dict.get(r.get('habilidad_id'), 'Desconocido'),
                            "peso_kg": r.get('peso_kg'),
                            "fecha_registro": r.get('fecha_registro')
                        })
        
        return jsonify({
            "nombre": cliente_info['nombre'],
            "rm": rm_lista
        })
    except Exception as e:
        print(f"Error en datos-publicos: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================
# API CLIENTE - SUBIR FOTO DE PERFIL
# ============================================
@app.route('/cliente/subir-foto', methods=['POST'])
def cliente_subir_foto():
    email = request.form.get('email')
    foto = request.files.get('foto')
    
    if not email or not foto:
        return jsonify({"error": "Email y foto son requeridos"}), 400
    
    if not foto.content_type.startswith('image/'):
        return jsonify({"error": "Solo se permiten imágenes"}), 400
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
        foto.save(tmp.name)
        tmp_path = tmp.name
    
    url_publica = subir_a_imgbb(tmp_path)
    os.unlink(tmp_path)
    
    if not url_publica:
        return jsonify({"error": "Error al subir la foto"}), 500
    
    try:
        sheet = get_sheet("clientes")
        clientes = sheet.get_all_records()
        
        fila_cliente = None
        for i, c in enumerate(clientes, start=2):
            if c.get('email') == email:
                fila_cliente = i
                break
        
        if fila_cliente:
            sheet.update_cell(fila_cliente, 6, url_publica)
            invalidate_cache("clientes")
        
        return jsonify({"mensaje": "Foto actualizada", "url": url_publica})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# API CLIENTE - RESERVAS
# ============================================
@app.route('/cliente/verificar-reserva', methods=['POST'])
def cliente_verificar_reserva():
    data = request.json
    email = data.get('email')
    clase_id = data.get('clase_id')
    try:
        sheet_clientes = get_sheet("clientes")
        clientes = sheet_clientes.get_all_records()
        cliente_id = None
        for c in clientes:
            if c.get('email') == email:
                cliente_id = c.get('id')
                break
        if not cliente_id:
            return jsonify({"reservado": False})
        sheet_reservas = get_sheet("reservas")
        reservas = sheet_reservas.get_all_records()
        for r in reservas:
            if r.get('cliente_id') == cliente_id and r.get('clase_id') == clase_id:
                return jsonify({"reservado": True})
        return jsonify({"reservado": False})
    except Exception as e:
        return jsonify({"reservado": False})

@app.route('/cliente/reservar', methods=['POST'])
@limiter.limit("50 per minute")
def cliente_reservar():
    data = request.json
    email = data.get('email')
    clase_id = data.get('clase_id')
    
    try:
        sheet_clientes = get_sheet("clientes")
        clientes = sheet_clientes.get_all_records()
        cliente_id = None
        fila_cliente = None
        cliente_actual = None
        for i, c in enumerate(clientes, start=2):
            if c.get('email') == email:
                cliente_id = c.get('id')
                fila_cliente = i
                cliente_actual = c
                break
        if not cliente_id:
            return jsonify({"error": "Cliente no encontrado"}), 404
        
        clases_restantes = int(cliente_actual.get('clases_restantes_mes', 0)) if cliente_actual else 0
        if clases_restantes <= 0:
            return jsonify({"error": "No tienes clases disponibles"}), 400
        
        sheet_clases = get_sheet("clases")
        clases = sheet_clases.get_all_records()
        clase = None
        fila_clase = None
        for i, c in enumerate(clases, start=2):
            if c.get('id') == clase_id:
                clase = c
                fila_clase = i
                break
        if not clase:
            return jsonify({"error": "Clase no encontrada"}), 404
        
        disponibles = int(clase.get('cupos_maximos', 0)) - int(clase.get('cupos_ocupados', 0))
        if disponibles <= 0:
            return jsonify({"error": "No hay cupos"}), 400
        
        sheet_reservas = get_sheet("reservas")
        reservas = sheet_reservas.get_all_records()
        
        from datetime import date
        hoy = date.today().isoformat()
        reservas_activas_futuras = 0
        for r in reservas:
            if r.get('cliente_id') == cliente_id and r.get('estado') == 'confirmada':
                for c in clases:
                    if c.get('id') == r.get('clase_id'):
                        fecha_clase = c.get('fecha', '')
                        if fecha_clase and fecha_clase >= hoy:
                            reservas_activas_futuras += 1
                        break
        
        if reservas_activas_futuras >= 1:
            return jsonify({"error": "Ya tienes una reserva activa para una clase futura. Cancélala primero para reservar otra."}), 400
        
        fecha_clase_reservar = clase.get('fecha', '')
        
        for r in reservas:
            if r.get('cliente_id') == cliente_id and r.get('estado') == 'confirmada':
                sheet_clases_verificar = get_sheet("clases")
                clases_verificar = sheet_clases_verificar.get_all_records()
                for c in clases_verificar:
                    if c.get('id') == r.get('clase_id') and c.get('fecha') == fecha_clase_reservar:
                        return jsonify({"error": "Ya tienes reserva este día"}), 400
        
        for r in reservas:
            if r.get('cliente_id') == cliente_id and r.get('clase_id') == clase_id:
                return jsonify({"error": "Ya reservaste esta clase"}), 400
        
        nueva_id = len(reservas) + 1
        fecha_reserva = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet_reservas.append_row([
            str(nueva_id), str(cliente_id), str(clase_id), fecha_reserva, "confirmada"
        ])
        
        nuevo_cupo = int(clase.get('cupos_ocupados', 0)) + 1
        sheet_clases.update_cell(fila_clase, 5, nuevo_cupo)
        
        nuevas_restantes = max(0, clases_restantes - 1)
        sheet_clientes.update_cell(fila_cliente, 8, nuevas_restantes)
        
        invalidate_cache("clases")
        invalidate_cache("reservas")
        invalidate_cache("clientes")
        
        return jsonify({
            "mensaje": f"✅ Reserva confirmada. Te quedan {nuevas_restantes} clases."
        })
    except Exception as e:
        print(f"Error en reservar: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/cliente/mis-reservas', methods=['POST'])
def cliente_mis_reservas():
    data = request.json
    email = data.get('email')
    try:
        sheet_clientes = get_sheet("clientes")
        clientes = sheet_clientes.get_all_records()
        cliente_id = None
        for c in clientes:
            if c.get('email') == email:
                cliente_id = c.get('id')
                break
        if not cliente_id:
            return jsonify([])
        
        sheet_reservas = get_sheet("reservas")
        reservas = sheet_reservas.get_all_records()
        sheet_clases = get_sheet("clases")
        clases = sheet_clases.get_all_records()
        
        hoy = date.today().isoformat()
        
        resultado = []
        for r in reservas:
            if r.get('cliente_id') == cliente_id and r.get('estado') == 'confirmada':
                for c in clases:
                    if c.get('id') == r.get('clase_id'):
                        fecha_clase = c.get('fecha', '')
                        if fecha_clase and fecha_clase >= hoy:
                            resultado.append({
                                "reserva_id": r.get('id'),
                                "clase_id": c.get('id'),
                                "fecha": fecha_clase,
                                "hora": c.get('hora', '')
                            })
                        break
        return jsonify(resultado)
    except Exception as e:
        print(f"Error en mis-reservas: {e}")
        return jsonify([])

@app.route('/cliente/cancelar-reserva', methods=['POST'])
@limiter.limit("50 per minute")
def cliente_cancelar_reserva():
    data = request.json
    email = data.get('email')
    reserva_id = data.get('reserva_id')
    clase_id = data.get('clase_id')
    
    try:
        sheet_clientes = get_sheet("clientes")
        clientes = sheet_clientes.get_all_records()
        
        cliente_id = None
        fila_cliente = None
        cliente_actual = None
        for i, c in enumerate(clientes, start=2):
            if c.get('email') == email:
                cliente_id = c.get('id')
                fila_cliente = i
                cliente_actual = c
                break
        if not cliente_id:
            return jsonify({"error": "Cliente no encontrado"}), 404
        
        sheet_reservas = get_sheet("reservas")
        reservas = sheet_reservas.get_all_records()
        fila_reserva = None
        for i, r in enumerate(reservas, start=2):
            if r.get('id') == reserva_id and r.get('cliente_id') == cliente_id:
                fila_reserva = i
                break
        if not fila_reserva:
            return jsonify({"error": "Reserva no encontrada"}), 404
        sheet_reservas.delete_rows(fila_reserva)
        
        sheet_clases = get_sheet("clases")
        clases = sheet_clases.get_all_records()
        fila_clase = None
        clase = None
        for i, c in enumerate(clases, start=2):
            if c.get('id') == clase_id:
                clase = c
                fila_clase = i
                break
        if fila_clase and clase:
            cupos_actual = int(clase.get('cupos_ocupados', 0)) if clase.get('cupos_ocupados') is not None else 0
            nuevo_cupo = max(0, cupos_actual - 1)
            sheet_clases.update_cell(fila_clase, 5, nuevo_cupo)
        
        if fila_cliente and cliente_actual:
            clases_restantes_actual = int(cliente_actual.get('clases_restantes_mes', 0))
            nuevas_restantes = clases_restantes_actual + 1
            sheet_clientes.update_cell(fila_cliente, 8, nuevas_restantes)
        
        # 👇 LIMPIAR CACHÉ (importante)
        invalidate_cache("clases")
        invalidate_cache("reservas")
        invalidate_cache("clientes")
        
        return jsonify({"mensaje": f"✅ Reserva cancelada. Ahora tienes {nuevas_restantes} clases."})
    except Exception as e:
        print(f"Error en cancelar: {e}")
        return jsonify({"error": str(e)}), 500
    

# ============================================
# MANIFEST Y SERVICE WORKER
# ============================================
@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('.', 'manifest.json')

@app.route('/sw.js')
def serve_sw():
    return send_from_directory('.', 'sw.js')

@app.route('/manifest-admin.json')
def serve_manifest_admin():
    return send_from_directory('.', 'manifest-admin.json')

@app.route('/sw-admin.js')
def serve_sw_admin():
    return send_from_directory('.', 'sw-admin.js')


@app.route('/test-clases', methods=['GET'])
def test_clases():
    try:
        sheet = get_sheet("clases")
        registros = sheet.get_all_records()
        return jsonify({
            "total": len(registros),
            "registros": registros
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ============================================
# INICIAR SERVIDOR
# ============================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)