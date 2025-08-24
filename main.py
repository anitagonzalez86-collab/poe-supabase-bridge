from flask import Flask, request, Response
import os
from supabase import create_client, Client
import json

# 1. Conexión a Supabase
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# 2. Crear la aplicación del servidor
app = Flask(__name__)

@app.route('/', methods=['GET'])
def health_check():
    return "Servidor activo y listo para recibir peticiones de Poe."

@app.route('/', methods=['POST'])
def handle_request():
    body = request.json
    
    dni_usuario = ""
    if 'query' in body and len(body['query']) > 0:
        dni_usuario = body['query'][-1]['content'].strip()
    elif 'input' in body:
        dni_usuario = body['input'].strip()

    if not dni_usuario:
        return Response(status=400)

    try:
        response = supabase.table('evaluaciones').select('*').eq('dni', dni_usuario).maybe_single().execute()
        data = response.data
        
        if data:
            responseText = f"Ficha del Paciente DNI {data.get('dni', '')}:\n"
            responseText += f"- Nombre: {data.get('nombre_completo', 'No especificado')}\n"
            responseText += f"- Historia Clínica: {data.get('n_historia_clinica', 'No especificado')}\n"
            # Añade aquí el resto de tus columnas
        else:
            responseText = "FICHA NO ENCONTRADA. El DNI no está en la base de datos."

    except Exception as e:
        print(f"Error en Supabase: {e}")
        responseText = "Error al conectar con la base de datos."

    def generate():
        # DESPUÉS (con comillas triples, a prueba de errores)
chunk = f"""data: {{"text": "{json.dumps(responseText)[1:-1]}"}}\n\n"""
        yield chunk

    return Response(generate(), mimetype='application/json-seq')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)