import os
import requests
import json
import time

def check_google_facts(query, api_key):
    """
    Interroge l'API Google Fact Check Tools pour vérifier une information.
    """
    url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
    params = {
        'query': query,
        'key': api_key,
        'languageCode': 'fr' # On privilégie les sources francophones
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status() # Lève une erreur si le statut HTTP n'est pas 200
        
        data = response.json()
        claims = data.get('claims', [])
        
        return claims
    except requests.exceptions.RequestException as e:
        print(f"Erreur de connexion à l'API : {e}")
        return None

def format_result(claim):
    """
    Formate un résultat brut de l'API pour l'affichage.
    """
    text = claim.get('text', 'Texte non disponible')
    claim_date = claim.get('claimDate', 'Date inconnue')
    
    # On prend la première revue (souvent la plus pertinente)
    reviews = claim.get('claimReview', [])
    if reviews:
        review = reviews[0]
        publisher = review.get('publisher', {}).get('name', 'Source inconnue')
        rating = review.get('textualRating', 'Non évalué')
        url = review.get('url', '#')
        title = review.get('title', 'Titre non disponible')
    else:
        publisher = "Inconnu"
        rating = "Non évalué"
        url = "#"
        title = "Titre non disponible"
        
    return {
        "source": publisher,
        "verdict": rating,
        "titre_article": title,
        "lien": url,
        "date_reclamation": claim_date
    }

def main():
    print("=======================================================")
    print("      FAKELAB - Outil de Vérification Factuelle        ")
    print("=======================================================")
    
    # 1. Récupération de la clé API
    # On regarde d'abord dans les variables d'environnement, sinon on demande à l'utilisateur
    api_key = os.getenv("GOOGLE_FACT_CHECK_API_KEY")
    
    if not api_key:
        print("\n[!] Aucune clé API trouvée dans l'environnement.")
        print("Pour obtenir une clé : https://console.cloud.google.com/apis/credentials")
        api_key = input("Veuillez coller votre clé API Google ici : ").strip()
    
    if not api_key:
        print("Erreur : La clé API est obligatoire.")
        return

    print("\nConnexion API configurée. Prêt à vérifier.")

    while True:
        print("\n-------------------------------------------------------")
        user_query = input("Entrez le titre de l'info ou des mots-clés (ou 'q' pour quitter) : ")
        
        if user_query.lower() in ['q', 'quit', 'exit']:
            print("Fermeture du programme.")
            break
        
        if not user_query.strip():
            continue

        print(f"--> Recherche en cours pour : '{user_query}'...")
        
        results = check_google_facts(user_query, api_key)
        
        if results:
            print(f"\n✅ {len(results)} résultat(s) trouvé(s) :\n")
            for i, item in enumerate(results):
                formatted = format_result(item)
                print(f"  Resultat #{i+1}")
                print(f"  • Source  : {formatted['source']}")
                print(f"  • Verdict : {formatted['verdict'].upper()}")
                print(f"  • Détail  : {formatted['titre_article']}")
                print(f"  • Preuve  : {formatted['lien']}")
                print("")
        elif results is None:
            print("Une erreur technique est survenue.")
        else:
            print("❌ Aucune correspondance trouvée dans les bases de fact-checking.")
            print("Cela signifie que l'info n'a pas encore été traitée par les fact-checkers,")
            print("ou qu'elle est trop récente/spécifique.")

if __name__ == "__main__":
    main()
