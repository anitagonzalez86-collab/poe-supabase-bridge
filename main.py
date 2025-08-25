from flask import Flask, request, send_from_directory
import os
from supabase import create_client, Client
import requests # Usaremos la librería requests para llamar a la API de Poe
import json

# --- CONFIGURACIÓN ---
supabase_url: str = os.environ.get("SUPABASE_URL")
supabase_key: str = os.environ.get("SUPABASE_KEY")
poe_api_key: str = os.environ.get("POE_API_KEY") # Leemos la clave de Poe

supabase: Client = create_client(supabase_url, supabase_key)

try:
    with open('bibliografia.txt', 'r', encoding='utf-8') as f:
        bibliografia_contexto = f.read()
except FileNotFoundError:
    bibliografia_contexto = "No se encontró bibliografía de referencia."

app = Flask(__name__)

# --- RUTAS DE LA APLICACIÓN ---
@app.route('/', methods=['GET'])
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/buscar', methods=['POST'])
def handle_request():
    body = request.json
    dni_usuario = body.get('dni', '').strip()

    if not dni_usuario:
        return {"error": "DNI no proporcionado"}, 400

    # 1. BUSCAR LA FICHA EN SUPABASE
    try:
        response = supabase.table('evaluaciones').select('*').eq('dni', dni_usuario).maybe_single().execute()
        ficha_paciente = response.data
        
        if not ficha_paciente:
            return {"error": "FICHA NO ENCONTRADA. El DNI no está en la base de datos."}, 404
    except Exception as e:
        return {"error": "Error al conectar con la base de datos."}, 500

    # 2. PREPARAR Y ENVIAR LA PETICIÓN A LA API DE POE
    try:
        prompt = f"""
        Eres un asistente médico experto en diagnósticos. Tu objetivo es analizar la ficha de un paciente y la documentación de referencia para proporcionar un posible diagnóstico.

        **Documentación de Referencia (Bibliografía):**
        ---
        {bibliografia_contexto}
        ---

        **Ficha del Paciente:**
        ---
        {ficha_paciente}
        ---

        **Tarea:**
        Basándote ESTRICTAMENTE en la ficha del paciente y en la bibliografía proporcionada, genera un análisis y un posible diagnóstico. Sé claro, profesional y estructurado.
        """

        # Preparamos la llamada a la API de Poe
        headers = {
            'Authorization': f'Bearer {poe_api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            "query": [
                {"role": "user", "content": prompt}
            ],
            "model": "ChatGPT", # O "Claude-2-instant", "Google-PaLM", etc.
            "stream": False
        }
        
        # Hacemos la llamada
        api_response = requests.post('https://api.poe.com/v1/chat/completions', headers=headers, json=data)
        api_response.raise_for_status() # Lanza un error si la petición falla
        
        # Extraemos la respuesta
        respuesta_json = api_response.json()
        diagnostico = respuesta_json['choices'][0]['message']['content']
        
        return {"diagnostico": diagnostico}

    except Exception as e:
        print(f"Error en la API de Poe: {e}")
        return {"error": "Error al generar el diagnóstico con la IA de Poe."}, 500