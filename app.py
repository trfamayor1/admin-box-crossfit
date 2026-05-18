from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_cors import CORS
import gspread
from google.oauth2.service_account import Credentials
import json
import os
from datetime import datetime, date

app = Flask(__name__)
CORS(app)

# ============================================
# FUNCIÓN AUXILIAR PARA VALORES SEGUROS
# ============================================
def safe_str(value):
    """Convierte cualquier valor a string seguro, evitando None"""
    return '' if value is None else str(value)

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

# ============================================
# ARCHIVOS ESTÁTICOS
# ============================================
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
# RUTAS HTML ADMINISTRADOR
# ============================================
@app.route('/admin/login')
def admin_login():
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin/dashboard.html')

# ============================================
# API ADMINISTRADOR
# ============================================
@app.route('/admin/verificar', methods=['POST'])
def admin_verificar():
    data = request.json
    email = data.get('email')
    
    try:
        sheet = get_sheet("admins")
        registros = sheet.get_all_records()
        
        for registro in registros:
            if registro.get('email') == email:
                return jsonify({"autorizado": True, "mensaje": "Admin autorizado"})
        
        return jsonify({"autorizado": False, "error": "Email no autorizado"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/clientes', methods=['GET'])
def admin_obtener_clientes():
    try:
        sheet = get_sheet("clientes")
        registros = sheet.get_all_records()
        return jsonify(registros)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/clientes', methods=['POST'])
def admin_crear_cliente():
    try:
        data = request.json
        sheet = get_sheet("clientes")
        registros = sheet.get_all_records()
        nuevo_id = len(registros) + 1
        
        sheet.append_row([
            nuevo_id,
            data.get('nombre', ''),
            data.get('email', ''),
            data.get('celular', ''),
            data.get('eps', ''),
            data.get('foto_url', ''),
            data.get('membresia_id', ''),
            data.get('clases_restantes_mes', 0),
            data.get('fecha_vencimiento', ''),
            data.get('activo', 'TRUE')
        ])
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
            if registro.get('id') == cliente_id:
                fila_index = i
                break
        
        if fila_index:
            sheet.update(fila_index, [
                cliente_id,
                data.get('nombre', ''),
                data.get('email', ''),
                data.get('celular', ''),
                data.get('eps', ''),
                data.get('foto_url', ''),
                data.get('membresia_id', ''),
                data.get('clases_restantes_mes', 0),
                data.get('fecha_vencimiento', ''),
                data.get('activo', 'TRUE')
            ])
            return jsonify({"mensaje": "Cliente actualizado"})
        return jsonify({"error": "Cliente no encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/clientes/<int:cliente_id>', methods=['DELETE'])
def admin_eliminar_cliente(cliente_id):
    try:
        sheet = get_sheet("clientes")
        registros = sheet.get_all_records()
        
        fila_index = None
        for i, registro in enumerate(registros, start=2):
            if registro.get('id') == cliente_id:
                fila_index = i
                break
        
        if fila_index:
            sheet.delete_rows(fila_index)
            return jsonify({"mensaje": "Cliente eliminado"})
        return jsonify({"error": "Cliente no encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/membresias', methods=['GET'])
def admin_obtener_membresias():
    try:
        sheet = get_sheet("membresias")
        registros = sheet.get_all_records()
        return jsonify(registros)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# API CLASES (Administrador)
# ============================================
@app.route('/admin/clases', methods=['GET'])
def admin_obtener_clases():
    try:
        sheet = get_sheet("clases")
        registros = sheet.get_all_records()
        return jsonify(registros)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/clases', methods=['POST'])
def admin_crear_clase():
    try:
        data = request.json
        sheet = get_sheet("clases")
        registros = sheet.get_all_records()
        nuevo_id = len(registros) + 1
        
        sheet.append_row([
            nuevo_id,
            data.get('fecha', ''),
            data.get('hora', ''),
            data.get('cupos_maximos', 0),
            0,
            'admin'
        ])
        return jsonify({"mensaje": "Clase creada", "id": nuevo_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/clases/<int:clase_id>', methods=['DELETE'])
def admin_eliminar_clase(clase_id):
    try:
        sheet = get_sheet("clases")
        registros = sheet.get_all_records()
        
        fila_index = None
        for i, registro in enumerate(registros, start=2):
            if registro.get('id') == clase_id:
                fila_index = i
                break
        
        if fila_index:
            sheet.delete_rows(fila_index)
            return jsonify({"mensaje": "Clase eliminada"})
        return jsonify({"error": "Clase no encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# RUTAS HTML CLIENTE
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

# ============================================
# API PÚBLICA PARA CLASES (sin autenticación)
# ============================================
@app.route('/api/clases', methods=['GET'])
def api_obtener_clases():
    try:
        sheet = get_sheet("clases")
        registros = sheet.get_all_records()
        
        hoy = date.today().isoformat()
        clases_futuras = []
        for c in registros:
            fecha_clase = c.get('fecha', '')
            if fecha_clase and fecha_clase >= hoy:
                clases_futuras.append(c)
        
        return jsonify(clases_futuras)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# API CLIENTE - LOGIN Y PERFIL
# ============================================
@app.route('/cliente/login', methods=['POST'])
def cliente_login_post():
    data = request.json
    email = data.get('email')
    
    try:
        sheet = get_sheet("clientes")
        registros = sheet.get_all_records()
        
        for registro in registros:
            if registro.get('email') == email:
                if registro.get('activo') != 'TRUE':
                    return jsonify({"error": "Usuario inactivo"}), 401
                
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
                membresia_nombre = ""
                try:
                    sheet_memb = get_sheet("membresias")
                    membresias = sheet_memb.get_all_records()
                    for m in membresias:
                        if str(m.get('id')) == str(registro.get('membresia_id')):
                            membresia_nombre = m.get('nombre', '')
                            break
                except:
                    pass
                
                return jsonify({
                    "id": registro.get('id'),
                    "nombre": registro.get('nombre', ''),
                    "email": registro.get('email', ''),
                    "celular": registro.get('celular', ''),
                    "eps": registro.get('eps', ''),
                    "membresia_id": registro.get('membresia_id', ''),
                    "membresia_nombre": membresia_nombre,
                    "fecha_vencimiento": registro.get('fecha_vencimiento', ''),
                    "activo": registro.get('activo', 'TRUE')
                })
        return jsonify({"error": "Perfil no encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/cliente/logout', methods=['POST'])
def cliente_logout():
    return jsonify({"mensaje": "Sesión cerrada"})

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
def cliente_reservar():
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
            return jsonify({"error": "Cliente no encontrado"}), 404
        
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
        
        disponibles = int(safe_str(clase.get('cupos_maximos', 0))) - int(safe_str(clase.get('cupos_ocupados', 0)))
        if disponibles <= 0:
            return jsonify({"error": "No hay cupos disponibles"}), 400
        
        sheet_reservas = get_sheet("reservas")
        reservas = sheet_reservas.get_all_records()
        for r in reservas:
            if r.get('cliente_id') == cliente_id and r.get('clase_id') == clase_id:
                return jsonify({"error": "Ya reservaste esta clase"}), 400
        
        nueva_id = len(reservas) + 1
        fecha_reserva = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Guardar reserva
        sheet_reservas.append_row([
            safe_str(nueva_id),
            safe_str(cliente_id),
            safe_str(clase_id),
            safe_str(fecha_reserva),
            "confirmada"
        ])
        
        # Actualizar cupos
        nuevo_cupo = int(safe_str(clase.get('cupos_ocupados', 0))) + 1
        sheet_clases.update(fila_clase, [
            safe_str(clase.get('id')),
            safe_str(clase.get('fecha')),
            safe_str(clase.get('hora')),
            safe_str(clase.get('cupos_maximos', 0)),
            safe_str(nuevo_cupo),
            safe_str(clase.get('creada_por', 'admin'))
        ])
        
        return jsonify({"mensaje": "Reserva confirmada"})
    except Exception as e:
        print(f"Error en reserva: {e}")
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
        
        resultado = []
        for r in reservas:
            if r.get('cliente_id') == cliente_id and r.get('estado') == 'confirmada':
                for c in clases:
                    if c.get('id') == r.get('clase_id'):
                        resultado.append({
                            "reserva_id": r.get('id'),
                            "clase_id": c.get('id'),
                            "fecha": c.get('fecha'),
                            "hora": c.get('hora')
                        })
                        break
        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/cliente/cancelar-reserva', methods=['POST'])
def cliente_cancelar_reserva():
    data = request.json
    email = data.get('email')
    reserva_id = data.get('reserva_id')
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
            return jsonify({"error": "Cliente no encontrado"}), 404
        
        sheet_reservas = get_sheet("reservas")
        reservas = sheet_reservas.get_all_records()
        
        fila_reserva = None
        reserva_valida = False
        for i, r in enumerate(reservas, start=2):
            if r.get('id') == reserva_id and r.get('cliente_id') == cliente_id:
                fila_reserva = i
                reserva_valida = True
                break
        
        if not reserva_valida:
            return jsonify({"error": "Reserva no encontrada"}), 404
        
        if fila_reserva:
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
            cupos_ocupados_actual = int(safe_str(clase.get('cupos_ocupados', 0)))
            nuevo_cupo_ocupado = max(0, cupos_ocupados_actual - 1)
            
            sheet_clases.update(fila_clase, [
                safe_str(clase.get('id')),
                safe_str(clase.get('fecha')),
                safe_str(clase.get('hora')),
                safe_str(clase.get('cupos_maximos', 0)),
                safe_str(nuevo_cupo_ocupado),
                safe_str(clase.get('creada_por', 'admin'))
            ])
        
        return jsonify({"mensaje": "Reserva cancelada exitosamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# INICIAR SERVIDOR
# ============================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)