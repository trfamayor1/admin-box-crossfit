from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_cors import CORS
import gspread
from google.oauth2.service_account import Credentials
import json
import os
from datetime import datetime, date, timedelta

app = Flask(__name__)
CORS(app)

# ============================================
# FUNCIÓN AUXILIAR
# ============================================
def safe_str(value):
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

@app.route('/admin/verificar', methods=['POST'])
def admin_verificar():
    data = request.json
    email = data.get('email')
    try:
        sheet = get_sheet("admins")
        registros = sheet.get_all_records()
        for registro in registros:
            if registro.get('email') == email:
                return jsonify({"autorizado": True})
        return jsonify({"autorizado": False, "error": "Email no autorizado"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        sheet.append_row([
            nuevo_id, data.get('nombre', ''), data.get('email', ''),
            data.get('celular', ''), data.get('eps', ''), data.get('foto_url', ''),
            data.get('membresia_id', ''), data.get('clases_restantes_mes', 0),
            data.get('fecha_vencimiento', ''), data.get('activo', 'TRUE')
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
        fila = None
        for i, r in enumerate(registros, start=2):
            if r.get('id') == cliente_id:
                fila = i
                break
        if fila:
            sheet.update(fila, [
                cliente_id, data.get('nombre', ''), data.get('email', ''),
                data.get('celular', ''), data.get('eps', ''), data.get('foto_url', ''),
                data.get('membresia_id', ''), data.get('clases_restantes_mes', 0),
                data.get('fecha_vencimiento', ''), data.get('activo', 'TRUE')
            ])
            return jsonify({"mensaje": "Cliente actualizado"})
        return jsonify({"error": "No encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/clientes/<int:cliente_id>', methods=['DELETE'])
def admin_eliminar_cliente(cliente_id):
    try:
        sheet = get_sheet("clientes")
        registros = sheet.get_all_records()
        for i, r in enumerate(registros, start=2):
            if r.get('id') == cliente_id:
                sheet.delete_rows(i)
                return jsonify({"mensaje": "Cliente eliminado"})
        return jsonify({"error": "No encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/membresias', methods=['GET'])
def admin_obtener_membresias():
    try:
        sheet = get_sheet("membresias")
        return jsonify(sheet.get_all_records())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/clases', methods=['GET'])
def admin_obtener_clases():
    try:
        sheet = get_sheet("clases")
        return jsonify(sheet.get_all_records())
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
            nuevo_id, data.get('fecha', ''), data.get('hora', ''),
            data.get('cupos_maximos', 0), 0, 'admin'
        ])
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
                return jsonify({"mensaje": "Clase eliminada"})
        return jsonify({"error": "No encontrada"}), 404
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

# ============================================
# API PÚBLICA CLASES (24h)
# ============================================
@app.route('/api/clases', methods=['GET'])
def api_obtener_clases():
    try:
        sheet = get_sheet("clases")
        registros = sheet.get_all_records()
        ahora = datetime.now()
        limite_24h = ahora + timedelta(hours=24)
        clases_disponibles = []
        for c in registros:
            fecha_clase = c.get('fecha', '')
            hora_clase = c.get('hora', '')
            if not fecha_clase or not hora_clase:
                continue
            try:
                datetime_clase = datetime.strptime(f"{fecha_clase} {hora_clase}", "%Y-%m-%d %H:%M")
                if ahora <= datetime_clase <= limite_24h:
                    disponibles = int(c.get('cupos_maximos', 0)) - int(c.get('cupos_ocupados', 0))
                    if disponibles > 0:
                        clases_disponibles.append(c)
            except:
                continue
        return jsonify(clases_disponibles)
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
                return jsonify({
                    "id": registro.get('id'),
                    "nombre": registro.get('nombre', ''),
                    "email": registro.get('email', ''),
                    "celular": registro.get('celular', ''),
                    "eps": registro.get('eps', ''),
                    "membresia_id": registro.get('membresia_id', ''),
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
# API CLIENTE - RESERVAS (CON MEMBRESÍAS)
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
        # 1. Obtener cliente
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
        
        # 2. Verificar clases restantes
        clases_restantes = int(cliente_actual.get('clases_restantes_mes', 0)) if cliente_actual else 0
        if clases_restantes <= 0:
            return jsonify({"error": "No tienes clases disponibles. Contacta al administrador."}), 400
        
        # 3. Obtener clase
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
        
        # 4. Verificar cupos
        disponibles = int(clase.get('cupos_maximos', 0)) - int(clase.get('cupos_ocupados', 0))
        if disponibles <= 0:
            return jsonify({"error": "No hay cupos disponibles"}), 400
        
        # 5. Verificar reserva mismo día
        fecha_clase_reservar = clase.get('fecha', '')
        sheet_reservas = get_sheet("reservas")
        reservas = sheet_reservas.get_all_records()
        sheet_clases_verificar = get_sheet("clases")
        clases_verificar = sheet_clases_verificar.get_all_records()
        for r in reservas:
            if r.get('cliente_id') == cliente_id and r.get('estado') == 'confirmada':
                for c in clases_verificar:
                    if c.get('id') == r.get('clase_id'):
                        if c.get('fecha') == fecha_clase_reservar:
                            return jsonify({"error": "Ya tienes una reserva en este día."}), 400
                        break
        
        # 6. Verificar misma clase
        for r in reservas:
            if r.get('cliente_id') == cliente_id and r.get('clase_id') == clase_id:
                return jsonify({"error": "Ya reservaste esta clase"}), 400
        
        # 7. Crear reserva
        nueva_id = len(reservas) + 1
        fecha_reserva = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet_reservas.append_row([
            str(nueva_id), str(cliente_id), str(clase_id), fecha_reserva, "confirmada"
        ])
        
        # 8. Actualizar cupos
        nuevo_cupo = int(clase.get('cupos_ocupados', 0)) + 1
        sheet_clases.update_cell(fila_clase, 5, nuevo_cupo)
        
        # 9. Descontar membresía
        nuevas_restantes = max(0, clases_restantes - 1)
        sheet_clientes.update_cell(fila_cliente, 8, nuevas_restantes)
        
        return jsonify({
            "mensaje": f"✅ Reserva confirmada. Te quedan {nuevas_restantes} clases.",
            "clases_restantes": nuevas_restantes
        })
    except Exception as e:
        print(f"Error reserva: {e}")
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
        # Obtener cliente
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
        
        # Eliminar reserva
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
        
        # Actualizar cupos
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
        
        # Devolver clase a la membresía
        if fila_cliente and cliente_actual:
            clases_restantes_actual = int(cliente_actual.get('clases_restantes_mes', 0))
            nuevas_restantes = clases_restantes_actual + 1
            sheet_clientes.update_cell(fila_cliente, 8, nuevas_restantes)
            return jsonify({"mensaje": f"✅ Reserva cancelada. Ahora tienes {nuevas_restantes} clases disponibles."})
        return jsonify({"mensaje": "✅ Reserva cancelada."})
    except Exception as e:
        print(f"Error cancelar: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================
# INICIAR SERVIDOR
# ============================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)