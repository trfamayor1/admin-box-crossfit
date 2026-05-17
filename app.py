from flask import Flask, jsonify, request, send_from_directory, session, render_template
from flask_cors import CORS
import gspread
from google.oauth2.service_account import Credentials
import json
import os

app = Flask(__name__)
app.secret_key = "clave_secreta_admin_box_2025"
app.config['SESSION_COOKIE_DOMAIN'] = None
app.config['SESSION_COOKIE_PATH'] = '/'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
CORS(app)

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
    if 'admin_email' not in session:
        return render_template('admin/login.html')
    return render_template('admin/dashboard.html')

# ============================================
# API ADMINISTRADOR
# ============================================
@app.route('/admin/login', methods=['POST'])
def admin_login_post():
    data = request.json
    email = data.get('email')
    
    try:
        sheet = get_sheet("admins")
        registros = sheet.get_all_records()
        
        for registro in registros:
            if registro.get('email') == email:
                session['admin_email'] = email
                return jsonify({"mensaje": "Login exitoso"})
        
        return jsonify({"error": "Email no autorizado"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/verificar_sesion', methods=['GET'])
def admin_verificar_sesion():
    if 'admin_email' in session:
        return jsonify({"autenticado": True})
    return jsonify({"autenticado": False}), 401

@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('admin_email', None)
    return jsonify({"mensaje": "Sesión cerrada"})

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
# RUTAS HTML CLIENTE
# ============================================
@app.route('/cliente/login')
def cliente_login():
    return render_template('cliente/login.html')

@app.route('/cliente/perfil')
def cliente_perfil():
    if 'cliente_email' not in session:
        return render_template('cliente/login.html')
    return render_template('cliente/perfil.html')

# ============================================
# API CLIENTE
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
                
                session.permanent = True
                session['cliente_email'] = email
                session['cliente_id'] = registro.get('id')
                return jsonify({"mensaje": f"Bienvenido {registro.get('nombre')}"})
        
        return jsonify({"error": "Email no registrado"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/cliente/perfil', methods=['GET'])
def cliente_obtener_perfil():
    if 'cliente_email' not in session:
        return jsonify({"error": "No autenticado"}), 401
    
    try:
        sheet = get_sheet("clientes")
        registros = sheet.get_all_records()
        
        for registro in registros:
            if registro.get('email') == session['cliente_email']:
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

@app.route('/cliente/verificar_sesion', methods=['GET'])
def cliente_verificar_sesion():
    if 'cliente_email' in session:
        return jsonify({"autenticado": True})
    return jsonify({"autenticado": False}), 401

@app.route('/cliente/logout', methods=['POST'])
def cliente_logout():
    session.pop('cliente_email', None)
    session.pop('cliente_id', None)
    return jsonify({"mensaje": "Sesión cerrada"})

# ============================================
# INICIAR SERVIDOR
# ============================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)