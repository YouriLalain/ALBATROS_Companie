import requests
import json
import gradio as gr
import fitz
import logging
import base64
from flask import Flask, request, jsonify
import io
import os
from PyPDF2 import PdfReader

# Configuration du logger
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Remplacez par votre clé API
OPENROUTER_API_KEY = "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"
YOUR_SITE_URL = "votre-site.com"
YOUR_APP_NAME = "MonChatbot"
MAKE_WEBHOOK_URL = "https://hook.eu2.make.com/yqq8mqiruhwz5j96gqyanpscm3stbydt"  # Webhook Make pour Google Docs

def extract_text_from_pdf(pdf_file):
    doc = fitz.open(pdf_file)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def chatbot_response(message, pdf_text=None):
    messages = [{"role": "system", "content": "Vous êtes un assistant IA RH qui analyse des CV de manière complete en analysant les compétences."}]
    
    if pdf_text:
        messages.append({"role": "system", "content": f"Le contenu du PDF est : {pdf_text}"})
    
    messages.append({"role": "user", "content": message})
    
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": f"{YOUR_SITE_URL}",
                "X-Title": f"{YOUR_APP_NAME}",
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": "mistralai/pixtral-12b:free",
                "messages": messages
            })
        )
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        else:
            return f"Erreur {response.status_code}: {response.text}"
    except Exception as e:
        logger.error(f"Erreur lors de l'appel API: {str(e)}")
        return f"Erreur: {str(e)}"

@app.route('/api/chatbot', methods=['POST'])
def api_chatbot():
    try:
        # Message prédéfini pour le chatbot
        message = "analyse le CV et donne-moi les 3 compétences principales, séparées par des points-virgules (;), sans introduction du type voici les 5 compétence..., directement les 5 compétences précises en fonction du cv"
        
        # Récupérer le fichier PDF uploadé
        pdf_file = request.files.get('pdf')

        if not pdf_file:
            return jsonify({'error': 'Aucun fichier PDF reçu.'}), 400

        # Lire le contenu du PDF avec PyMuPDF (fitz)
        pdf_data = pdf_file.read()
        pdf_doc = fitz.open(stream=pdf_data, filetype="pdf")
        pdf_text = ""
        for page in pdf_doc:
            pdf_text += page.get_text()

        if not pdf_text:
            return jsonify({'error': 'Impossible d\'extraire le texte du PDF.'}), 500

        # Utiliser le texte extrait pour interagir avec le chatbot et récupérer la réponse
        chatbot_reply = chatbot_response(message, pdf_text=pdf_text)

        # Diviser la réponse en compétences séparées par des points-virgules
        competences = [comp.strip() for comp in chatbot_reply.split(';') if comp.strip()]
        
        # Limiter à 5 compétences
        competences = competences[:3]

        # Préparer les compétences pour le webhook de Make (pour Webflow CMS)
        make_payload = {
            "competence_1": competences[0] if len(competences) > 0 else "",
            "competence_2": competences[1] if len(competences) > 1 else "",
            "competence_3": competences[2] if len(competences) > 2 else ""
        }

        # URL du Webhook Make
        MAKE_WEBHOOK_URL = "https://hook.eu2.make.com/yqq8mqiruhwz5j96gqyanpscm3stbydt"

        # Envoyer les compétences à Make
        make_response = requests.post(MAKE_WEBHOOK_URL, json=make_payload)

        if make_response.status_code != 200:
            return jsonify({'error': f"Échec de l'envoi à Make: {make_response.text}"}), 500

        return jsonify({'message': 'Compétences extraites et envoyées à Make pour Webflow', 'competences': competences})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))  # Assure-toi que Flask/Gradio écoute sur 0.0.0.0
