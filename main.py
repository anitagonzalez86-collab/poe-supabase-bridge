 ```python
 from flask import Flask, request, send_from_directory
 import os
 from supabase import create_client, Client
 import google.generativeai as genai
 from sentence_transformers import SentenceTransformer

 # --- CONFIGURACIÓN ---
 supabase_url: str = os.environ.get("SUPABASE_URL")
 supabase_key: str = os.environ.get("SUPABASE_KEY")
 gemini_key: str = os.environ.get("GEMINI_API_KEY")

 supabase: Client = create_client(supabase_url, supabase_key)
 genai.configure(api_key=gemini_key)
 model = genai.GenerativeModel('gemini-pro')

 print("Cargando modelo de embeddings local...")
 embedding_model = SentenceTransformer('paraphrase-MiniLM-L3-v2') # Usamos el modelo ligero
 print("Modelo cargado.")

 app = Flask(__name__)

 # --- RUTAS DE LA APLICACIÓN ---
 @app.route('/', methods=['GET'])
 def serve_index():
     return send_from_directory('.', 'index.html')

 @app.route('/chat', methods=['POST'])
 def handle_chat():
     body = request.json
     dni_usuario = body.get('dni', '').strip()
     pregunta_usuario = body.get('question', '').strip()
     if not dni_usuario or not pregunta_usuario: return {"error": "Falta el DNI o la pregunta."}, 400
     try:
         response = supabase.table('evaluaciones').select('*').eq('dni', dni_usuario).maybe_single().execute()
         ficha_paciente = response.data
         if not ficha_paciente: return {"error": "FICHA NO ENCONTRADA."}, 404
     except Exception as e: return {"error": "Error al buscar la ficha en Supabase."}, 500
     try:
         query_embedding = embedding_model.encode(pregunta_usuario).tolist()
         contexto_response = supabase.rpc('match_documentos', {'query_embedding': query_embedding, 'match_threshold': 0.7, 'match_count': 5}).execute()
         contexto_relevante = "\n".join([item['contenido'] for item in contexto_response.data])
     except Exception as e:
         contexto_relevante = "No se pudo recuperar información de la bibliografía."
     try:
         prompt = f"""
         Eres un asistente médico experto. Responde a la pregunta del usuario basándote ESTRICTAMENTE en la ficha del paciente y en la documentación de referencia proporcionada.
         **Documentación de Referencia Relevante:**\n---\n{contexto_relevante}\n---\n
         **Ficha Completa del Paciente:**\n---\n{ficha_paciente}\n---\n
         **Pregunta del Usuario:**\n---\n{pregunta_usuario}\n---\n
         **Respuesta:**
         """
         respuesta_ia = model.generate_content(prompt)
         return {"answer": respuesta_ia.text}
     except Exception as e: return {"error": "Error al generar la respuesta con la IA de Google."}, 500
 ```