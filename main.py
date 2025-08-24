from flask import Flask, request, Response
import os
from supabase import create_client, Client
import json

# 1. Conexión a Supabase usando las Variables de Entorno de Render
#    Render las inyecta automáticamente, igual que Replit.
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# 2. Crear la aplicación del servidor
#    Render (con Gunicorn) necesita que la variable se llame 'app'.
app = Flask(__name__)

# Esta es una ruta de prueba para verificar que el servidor está vivo.
# Simplemente abre la URL de Render en tu navegador y deberías ver "Servidor activo".
@app.route('/', methods=['GET'])
def health_check():
    return "Servidor activo y listo para recibir peticiones de Poe."

# Esta es la ruta a la que Poe enviará las peticiones.
@app.route('/', methods=['POST'])
def handle_request():
    body = request.json
    
    # Lógica para extraer el DNI (a prueba de fallos)
    dni_usuario = ""
    if 'query' in body and len(body['query']) > 0:
        dni_usuario = body['query'][-1]['content'].strip()
    elif 'input' in body:
        dni_usuario = body['input'].strip()

    if not dni_usuario:
        return Response(status=400) # Petición incorrecta si no hay DNI

    # 3. Hacemos la consulta a Supabase
    try:
        response = supabase.table('evaluaciones').select('*').eq('dni', dni_usuario).maybe_single().execute()
        data = response.data
        
        if data:
            # Formateamos la respuesta si encontramos al paciente
            responseText = f"Ficha del Paciente