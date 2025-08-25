from flask import Flask, request, send_from_directory
import os
from supabase import create_client, Client
import requests # Para llamar a la API de Poe
from sentence_transformers import SentenceTransformer

# --- CONFIGURACIÓN ---
supabase_url: str = os.environ.get("SUPABASE_URL")
supabase_key: str = os.environ.get("SUPABASE_KEY")
poe_api_key: str = os.environ.get("POE_API_KEY") # Leemos la clave de Poe

supabase: Client = create_client(supabase_url, supabase_key)

print("Cargando modelo de embeddings local...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
print("Modelo cargado.")

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

    # 1. BUSCAR LA FICHA DEL PACIENTE
    try:
        response = supabase.table('evaluaciones').select('*').eq('dni', dni_usuario).maybe_single().execute()
        ficha_paciente = response.data
        if not ficha_paciente:
            return {"error": "FICHA NO ENCONTRADA."}, 404
    except Exception as e:
        return {"error": "Error al buscar la ficha en Supabase."}, 500

    # 2. BUSCAR CONTEXTO RELEVANTE EN LA BIBLIOTECA
    try:
        pregunta_para_busqueda = f"Diagnóstico y tratamiento para un paciente con las siguientes características: {ficha_paciente}"
        query_embedding = embedding_model.encode(pregunta_para_busqueda).tolist()
        
        contexto_response = supabase.rpc('match_documentos', {
            'query_embedding': query_embedding,
            'match_threshold': 0.7,
            'match_count': 5
        }).execute()
        
        contexto_relevante = "\n".join([item['contenido'] for item in contexto_response.data])
    except Exception as e:
        print(f"Error buscando contexto: {e}")
        contexto_relevante = "No se pudo recuperar información de la bibliografía."

    # 3. PREPARAR Y ENVIAR LA PETICIÓN A LA API DE POE
    try:
        prompt = f"""
        Eres un asistente médico experto. Tu objetivo es analizar la ficha de un paciente y la documentación de referencia para proporcionar un posible diagnóstico.

        **Documentación de Referencia Relevante (extraída de la bibliografía):**
        ---
        {contexto_relevante}
        ---

        **Ficha Completa del Paciente:**
        ---
        {ficha_paciente}
        ---

        **Tarea:**
        Basándote ESTRICTAMENTE en la ficha del paciente y en la documentación de referencia, genera un análisis y un posible diagnóstico. Sé claro, profesional y estructurado.
        """

        headers = {'Authorization': f'Bearer {poe_api_key}', 'Content-Type': 'application/json'}
        data = {
            "query": [{"role": "user", "content": prompt}],
            "model": "ChatGPT", # Puedes cambiarlo por "Claude-2-instant" si está disponible
            "stream": False
        }
        
        api_response = requests.post('https://api.poe.com/v1/chat/completions', headers=headers, json=data)
        api_response.raise_for_status()
        
        respuesta_json = api_response.json()
        diagnostico = respuesta_json['choices'][0]['message']['content']
        
        return {"diagnostico": diagnostico}

    except Exception as e:
        print(f"Error en la API de Poe: {e}")
        return {"error": "Error al generar el diagnóstico con la IA de Poe."}, 500