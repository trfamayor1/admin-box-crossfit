from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS
import gspread
from google.oauth2.service_account import Credentials
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "clave_secreta_admin_box"  # Cambia esto después
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
    """Conecta con Google Sheets y devuelve una hoja específica"""
    if os.environ.get('GOOGLE_CREDENTIALS'):
        creds_dict = json.loads(os.environ.get('GOOGLE_CREDENTIALS'))
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    else:
        creds = Credentials.from_service_account_file("credenciales.json", scopes=scope)
    
    client = gspread.authorize(creds)
    # Abre el archivo - CAMBIA "BOX_CROSSFIT_ADMIN" por el nombre de tu archivo
    sheet = client.open("BOX_CROSSFIT_ADMIN").worksheet(nombre_hoja)
    return sheet

# ============================================
# RUTAS PARA ARCHIVOS ESTÁTICOS
# ============================================
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/dashboard.html')
def dashboard():
    return send_from_directory('.', 'dashboard.html')

@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('.', 'manifest.json')

@app.route('/sw.js')
def serve_sw():
    return send_from_directory('.', 'sw.js')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# ============================================
# LOGIN DEL ADMINISTRADOR
# ============================================
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({"error": "Email requerido"}), 400
    
    try:
        sheet = get_sheet("admins")
        registros = sheet.get_all_records()
        
        for registro in registros:
            if registro.get('email') == email:
                session['admin_email'] = email
                return jsonify({"mensaje": "Login exitoso", "admin": email})
        
        return jsonify({"error": "Email no autorizado"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/verificar_sesion', methods=['GET'])
def verificar_sesion():
    if 'admin_email' in session:
        return jsonify({"autenticado": True, "admin": session['admin_email']})
    return jsonify({"autenticado": False}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('admin_email', None)
    return jsonify({"mensaje": "Sesión cerrada"})

# ============================================
# CRUD DE CLIENTES
# ============================================
@app.route('/clientes', methods=['GET'])
def obtener_clientes():
    try:
        sheet = get_sheet("clientes")
        registros = sheet.get_all_records()
        return jsonify(registros)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/clientes', methods=['POST'])
def crear_cliente():
    try:
        data = request.json
        sheet = get_sheet("clientes")
        
        # Obtener el último ID para autoincrementar
        registros = sheet.get_all_records()
        nuevo_id = len(registros) + 1
        
        # Agregar nueva fila
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

@app.route('/clientes/<int:cliente_id>', methods=['PUT'])
def actualizar_cliente(cliente_id):
    try:
        data = request.json
        sheet = get_sheet("clientes")
        
        # Buscar la fila del cliente por ID
        registros = sheet.get_all_records()
        fila_index = None
        for i, registro in enumerate(registros, start=2):  # start=2 porque la fila 1 son cabeceras
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
        else:
            return jsonify({"error": "Cliente no encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/clientes/<int:cliente_id>', methods=['DELETE'])
def eliminar_cliente(cliente_id):
    try:
        sheet = get_sheet("clientes")
        
        # Buscar la fila del cliente por ID
        registros = sheet.get_all_records()
        fila_index = None
        for i, registro in enumerate(registros, start=2):
            if registro.get('id') == cliente_id:
                fila_index = i
                break
        
        if fila_index:
            sheet.delete_rows(fila_index)
            return jsonify({"mensaje": "Cliente eliminado"})
        else:
            return jsonify({"error": "Cliente no encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# OBTENER MEMBRESÍAS
# ============================================
@app.route('/membresias', methods=['GET'])
def obtener_membresias():
    try:
        sheet = get_sheet("membresias")
        registros = sheet.get_all_records()
        return jsonify(registros)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)