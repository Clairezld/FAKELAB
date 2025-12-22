import os
import google.generativeai as genai
from dotenv import load_dotenv
import json

# Chargement des variables d'environnement
load_dotenv()

def analyze_text_semantics(text, api_key):
    """
    Analyse un texte pour détecter les marqueurs de désinformation via Google Gemini.
    """
    genai.configure(api_key=api_key)
    
    # Liste des modèles à tester par ordre de préférence (Mise à jour selon disponibilité utilisateur)
    models_to_try = [
        'gemini-2.0-flash', 
        'gemini-2.5-flash',
        'gemini-flash-latest'
    ]
    
    selected_model = None
    response = None
    error_log = []

    prompt = f"""
    Tu es un expert en analyse linguistique et détection de désinformation pour le projet FAKELAB.
    
    Analyse le texte suivant : "{text}"
    
    Concentre-toi sur ces 3 marqueurs stylistiques précis :
    1. Subjectivité excessive : Usage abusif d'adjectifs émotionnels (peur, colère, indignation).
    2. Syntaxe "Clickbait" : Titres en majuscules, ponctuation excessive (!!!), formules racoleuses.
    3. Absence de preuves : Affirmations péremptoires non sourcées, généralisations hâtives.
    
    Réponds UNIQUEMENT au format JSON strict avec la structure suivante :
    {{
        "analyse_subjectivite": {{
            "score": <note sur 10>,
            "details": "<observation courte>"
        }},
        "analyse_clickbait": {{
            "score": <note sur 10>,
            "details": "<observation courte>"
        }},
        "analyse_preuves": {{
            "score_fiabilite": <note sur 10>,
            "details": "<observation courte>"
        }},
        "synthese_globale": "<Phrase de résumé sur la crédibilité du style>",
        "verdict_style": "<FIABLE | DOUTEUX | TROMPEUR>"
    }}
    """

    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            # Si on arrive ici, ça a marché
            selected_model = model_name
            break 
        except Exception as e:
            error_log.append(f"Modèle '{model_name}' échoué : {str(e)}")
            continue

    if not response and error_log:
        return {
            "error": "Impossible de contacter l'IA.",
            "details": error_log,
            "help": "Vérifiez votre clé API ou les modèles disponibles."
        }

    try:
        # Nettoyage pour récupérer le JSON pur
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(clean_json)

        #  --- CALCUL DU SCORE GLOBAL MANQUE DE PREUVES ---
        score_subjectivite = data['analyse_subjectivite']['score']
        score_clickbait = data['analyse_clickbait']['score']
        score_absence_preuves = data['analyse_preuves']['score_fiabilite']

        score_manque_preuves = round(
            (score_subjectivite + score_clickbait + score_absence_preuves) / 3, 2
        )

        # Injection du score calculé
        data['analyse_preuves']['score_manque_preuves'] = score_manque_preuves

        # Métadonnée modèle
        data['modele_utilise'] = selected_model

        return data

    except Exception as e:
        return {
        "error": f"Erreur de lecture ou de calcul IA ({selected_model}) : {str(e)}"
    }
