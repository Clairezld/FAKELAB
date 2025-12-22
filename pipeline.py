import os
from dotenv import load_dotenv

# --- IMPORTS DES VRAIS MODULES ---
# Le nom du fichier est 'scraping', la classe dedans est 'RobustExtractor'
from modules.extractor import RobustExtractor  

# Le nom du fichier est 'reputation', la classe dedans est 'ReputationChecker'
from modules.reputation_checker import ReputationChecker

# Le nom du fichier est 'factcheck', la fonction est 'check_google_facts'
from modules.fact_checker import check_google_facts

# Le nom du fichier est 'semantic', la fonction est 'analyze_text_semantics'
from modules.gemini_analyzer import analyze_text_semantics

load_dotenv()

def calculer_score_final(R_source, V_fact, A_sem):
    """
    Applique la formule mathématique stricte du PDF (Page 7).
    S_final = alpha * R + beta * V + gamma * A
    """
    
    # --- 1. Définition des Poids (Coefficients) ---
    # La somme doit faire 1.0
    alpha = 0.50  # Poids de la Réputation (R_source)
    beta  = 0.3  # Poids du Fact-Checking (V_fact)
    gamma = 0.2  # Poids de l'Analyse Sémantique (A_sem)
    
    # --- 2. Normalisation des valeurs sur 100 ---
    
    # A. Réputation (R) : Déjà sur 100 via ton module reputation.py
    Score_R = R_source
    
    # B. Fact-Checking (V) : On doit transformer le texte en note sur 100
    if V_fact == "FOUND_FAKE":
        Score_V = 0.0      # C'est prouvé faux -> 0/100
    elif V_fact == "FOUND_TRUE":
        Score_V = 100.0    # C'est prouvé vrai -> 100/100
    else:
        Score_V = 50.0     # On ne sait pas (NOT_FOUND) -> 50/100 (Neutre)
        
    # C. Sémantique (A) : Attention, A_sem est un score de RISQUE (100 = Mauvais).
    # On doit le transformer en score de FIABILITÉ (100 = Bon).
    Score_A = 100 - A_sem

    # --- 3. Application de la Formule ---
    # S_final = (0.25 * R) + (0.35 * V) + (0.40 * A)
    S_final = (alpha * Score_R) + (beta * Score_V) + (gamma * Score_A)
    
    return round(S_final, 1)

def run_fakelab_pipeline(url, api_key_gemini):
    """
    Orchestre tout le processus FAKELAB avec tes vrais modules.
    """
    resultats = {}
    print(f"Lancement du pipeline pour : {url}")

    # ---------------------------------------------------------
    # ÉTAPE 1 : EXTRACTION (Web Scraping)
    # ---------------------------------------------------------
    try:
        extractor = RobustExtractor()  # On initialise ta classe
        data_article, method = extractor.extract(url)
        
        if not data_article:
            return {"error": "Impossible d'extraire le contenu de cette page."}
            
        resultats['titre'] = data_article['titre']
        resultats['contenu'] = data_article['texte']
        resultats['methode_extraction'] = method
        print("✅ Extraction terminée.")

    except Exception as e:
        return {"error": f"Erreur lors de l'extraction : {str(e)}"}

    # ---------------------------------------------------------
    # ÉTAPE 2 : RÉPUTATION (Source Scoring)
    # ---------------------------------------------------------
    try:
        rep_checker = ReputationChecker() # On initialise ta classe
        # Ton module renvoie 4 valeurs (score, status, source, details)
        # Note : Ton module renvoie un score entre 0.0 et 1.0
        r_score_brut, r_status, r_source, r_details = rep_checker.check_source(url)
        
        # Conversion du score sur 100 pour le calcul final
        r_score_100 = r_score_brut * 100
        
        resultats['R_source'] = r_score_100
        resultats['details_reputation'] = {
            "status": r_status,
            "source": r_source,
            "details": r_details
        }
        print(f"✅ Réputation analysée : {r_status} ({r_score_100}/100)")

    except Exception as e:
        print(f"⚠️ Erreur réputation : {e}")
        resultats['R_source'] = 50.0 # Valeur neutre par défaut

    # ---------------------------------------------------------
    # ÉTAPE 3 : FACT-CHECKING (Google API)
    # ---------------------------------------------------------
    api_key_factcheck = os.getenv("GOOGLE_FACT_CHECK_API_KEY")
    resultats['V_fact'] = "NOT_FOUND" # Par défaut
    resultats['preuves_factcheck'] = []

    if api_key_factcheck:
        try:
            print("🔍 Recherche Fact-Checking...")
            # On cherche avec le titre de l'article extrait
            claims = check_google_facts(resultats['titre'], api_key_factcheck)
            
            if claims:
                # Si on trouve des résultats, on regarde s'ils parlent de "Faux"
                # On prend le premier résultat pertinent
                premier_claim = claims[0]
                review = premier_claim.get('claimReview', [])[0]
                rating = review.get('textualRating', '').lower()
                
                resultats['preuves_factcheck'] = claims # On garde tout pour l'affichage
                
                # Si le rating contient "faux", "fake", "incorrect"
                mots_cles_faux = ['faux', 'fake', 'incorrect', 'trompeur', 'false']
                if any(mot in rating for mot in mots_cles_faux):
                    resultats['V_fact'] = "FOUND_FAKE"
                    print("🚨 FACT-CHECKING : C'est une FAKE NEWS connue !")
        except Exception as e:
            print(f"⚠️ Erreur Fact-Check : {e}")
    else:
        print("⚠️ Pas de clé API Fact Check trouvée (.env)")

    # Si le Fact-Checking a déjà prouvé que c'est faux, on skip l'IA pour économiser
    if resultats['V_fact'] == "FOUND_FAKE":
        resultats['A_sem'] = 100 # Risque maximal
        resultats['details_ia'] = None
        s_final = 0.0
        verdict = "FAUX (Avéré)"
    else:
        # ---------------------------------------------------------
        # ÉTAPE 4 : ANALYSE SÉMANTIQUE (IA Gemini)
        # ---------------------------------------------------------
        print("🤖 Analyse IA en cours...")
        gemini_data = analyze_text_semantics(resultats['contenu'], api_key_gemini)
        
        if "error" in gemini_data:
            return {"error": gemini_data["error"]}
        
        resultats['A_sem'] = gemini_data.get('A_sem', 50) # Score de risque
        resultats['details_ia'] = gemini_data
        
        # ---------------------------------------------------------
        # ÉTAPE 5 : CALCUL FINAL
        # ---------------------------------------------------------
        s_final = calculer_score_final(
            R_source=resultats['R_source'],
            V_fact=resultats['V_fact'],
            A_sem=resultats['A_sem']
        )
        
        # Détermination du verdict textuel
        if s_final >= 75:
            verdict = "FIABLE"
        elif s_final >= 40:
            verdict = "DOUTEUX"
        else:
            verdict = "TROMPEUR / FAUX"

    resultats['S_final'] = s_final
    resultats['verdict'] = verdict
    
    return resultats