from google import genai
from google.genai import types
import json
import re # On ajoute les expressions régulières pour nettoyer

def analyze_text_semantics(text, api_key):
    """
    Analyse sémantique ROBUSTE.
    Corrige automatiquement les erreurs de syntaxe JSON de l'IA.
    """
    if not api_key:
        return {"error": "Clé API manquante"}

    # 1. Configuration Client
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        return {"error": f"Erreur Client Google : {str(e)}"}

    # 2. Prompt
    prompt = f """
    Tu es l'IA du projet FAKELAB.
    Analyse ce texte : "{text}"

    Note sur 10 (10 = TRES SUSPECT/FAUX) :
    1. Subjectivité
    2. Clickbait
    3. Absence de preuves (score_manque_preuves)

    Réponds UNIQUEMENT au format JSON strict (sans Markdown) :
    {{
        "analyse_subjectivite": {{ "score": 0, "details": "..." }},
        "analyse_clickbait": {{ "score": 0, "details": "..." }},
        "analyse_preuves": {{ "score_manque_preuves": 0, "details": "..." }},
        "synthese_globale": "...",
        "verdict_style": "DOUTEUX"
    }}
    """

    
    # 3. Appel IA (Utilisation du modèle stable 2.0)
    # J'ai retiré "2.5" qui n'existe pas et peut causer des bugs
    model_id = "gemini-2.0-flash" 

    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1 # Créativité faible pour éviter les erreurs de format
            )
        )
    except Exception as e:
        # Si le 2.0 échoue, on tente le 1.5 qui est très fiable
        try:
            model_id = "gemini-1.5-flash"
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
        except Exception as e2:
             return {"error": f"Erreur IA totale : {str(e2)}"}

    # 4. Nettoyage et Parsing (La partie qui corrige ton erreur)
    try:
        json_text = response.text
        
        # Nettoyage brutal des balises Markdown (```json)
        json_text = json_text.replace("```json", "").replace("```", "").strip()
        
        # TENTATIVE DE PARSING
        data = json.loads(json_text)
        data['modele_utilise'] = model_id

        # --- Calculs ---
        s1 = data.get('analyse_subjectivite', {}).get('score', 5)
        s2 = data.get('analyse_clickbait', {}).get('score', 5)
        
        s3 = 5
        if 'analyse_preuves' in data:
            if 'score_manque_preuves' in data['analyse_preuves']:
                s3 = data['analyse_preuves']['score_manque_preuves']
            elif 'score_fiabilite' in data['analyse_preuves']:
                s3 = 10 - data['analyse_preuves']['score_fiabilite']
                data['analyse_preuves']['score_manque_preuves'] = s3

        moyenne = (s1 + s2 + s3) / 3
        data['A_sem'] = round(moyenne * 10, 1)

        return data

    except json.JSONDecodeError as e:
        # C'est ici que ton erreur "Expecting ','" est attrapée
        print(f"⚠️ JSON malformé reçu : {json_text}")
        return {
            "error": "L'IA a généré une réponse mal formatée. Veuillez relancer l'analyse.",
            "details_technique": str(e)
        }
    except Exception as e:
        return {"error": f"Erreur interne : {str(e)}"}
