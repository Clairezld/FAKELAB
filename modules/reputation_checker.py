import json
import tldextract
import wikipediaapi
import os

class ReputationChecker:
    def __init__(self):
        # Configuration Wikipédia (User-Agent requis par leur politique)
        self.wiki = wikipediaapi.Wikipedia(
            user_agent='FakeLabProject/1.0 (contact@fakelab.org)',
            language='fr'
        )
        self.local_db = self._load_local_db()

    def _load_local_db(self):
        """
        Charge la base de données locale (Format simple Whitelist/Blacklist).
        """
        try:
            with open('sources.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Erreur chargement DB : {e}")
            return {"whitelist": [], "blacklist": []}

    def get_domain(self, url):
        """Extrait le domaine principal (ex: 'lemonde.fr' depuis 'http://www.lemonde.fr/article')"""
        # Si c'est déjà juste un domaine, tldextract le gère bien
        extracted = tldextract.extract(url)
        if extracted.suffix:
            return f"{extracted.domain}.{extracted.suffix}"
        return extracted.domain # Cas localhost ou sans suffixe

    def check_source(self, url):
        """
        Analyse la réputation du domaine.
        Retourne : (Score, Status, Méthode, Détails)
        Score est maintenant entre 0 et 1 (automatique selon la liste).
        """
        domain = self.get_domain(url)
        print(f"🔎 Analyse du domaine : {domain}")

    def check_source(self, url):
        """
        Analyse la réputation du domaine.
        Combine Base Locale ET Wikipédia pour un résultat robuste.
        """
        domain = self.get_domain(url)
        print(f"🔎 Analyse du domaine : {domain}")

        # 1. Vérification Base Locale
        local_score = None
        local_status = None
        local_comment = ""
        
        if domain in self.local_db.get('blacklist', []):
            local_score = 0.0
            local_status = "DANGEREUX"
            local_comment = "Liste Noire"
        elif domain in self.local_db.get('whitelist', []):
            local_score = 1.0
            local_status = "FIABLE"
            local_comment = "Liste Blanche"

        # 2. Vérification Wikipédia (Toujours exécutée pour cross-check en arrière-plan)
        print("   ...Interrogation de Wikipédia (Analyse croisée)...")
        wiki_score, wiki_status, wiki_source, wiki_details = self._check_wikipedia(domain)

        # 3. Consolidation des résultats
        if local_score is not None:
            # Si présent localement, le score local prime (c'est notre vérité terrain)
            # Mais on enrichit les détails avec les infos Wiki
            final_details = (f"📍 [LOCAL] {local_comment}. "
                             f"📚 [WIKIPEDIA] {wiki_details} (Statut Wiki: {wiki_status})")
            
            return local_score, local_status, "Hybride (Locale + Wiki)", final_details

        # Sinon, on se base entièrement sur Wikipédia
        return wiki_score, wiki_status, wiki_source, wiki_details

    def _check_wikipedia(self, domain):
        """
        Cherche le site sur Wikipédia et calcule un score intelligent basé sur le vocabulaire utilisé.
        """
        # 1. Heuristique sur le nom de domaine (Bonus/Malus immédiats)
        if ".gouv." in domain or ".gov" in domain:
            return 1.0, "OFFICIEL", "Heuristique TLD", "Extension gouvernementale (.gouv/.gov) détectée."
        if ".edu" in domain:
            return 0.95, "ACADÉMIQUE", "Heuristique TLD", "Site universitaire ou éducatif."

        # 2. Recherche Wikipédia
        search_terms = [domain, domain.split('.')[0]]
        page = None
        for term in search_terms:
            page = self.wiki.page(term)
            if page.exists():
                break
        
        if not page or not page.exists():
            return 0.5, "INCONNU", "Non trouvé", "Aucune donnée sur ce site (Score neutre 0.5)."

        summary = page.summary.lower()
        
        # --- LOGIQUE DE SCORING INTELLIGENT ---
        
        # Catégorie 1 : Très Fiable (Agences, Service Public)
        if any(w in summary for w in ["agence de presse", "service public", "établissement public"]):
            return 1.0, "TRÈS FIABLE", "Analyse Wikipédia", "Source institutionnelle ou agence de référence."

        # Catégorie 2 : Presse Établie
        if any(w in summary for w in ["journal quotidien", "presse quotidienne", "journal d'information", "média d'information"]):
            return 0.9, "FIABLE", "Analyse Wikipédia", "Média de presse reconnu."

        # Catégorie 3 : Presse Magazine / Web (Neutre positif)
        if any(w in summary for w in ["hebdomadaire", "magazine", "site web d'information", "pure player"]):
            return 0.8, "GÉNÉRALEMENT FIABLE", "Analyse Wikipédia", "Média d'information standard."

        # Catégorie 4 : Satire (Faux mais "honnête")
        if any(w in summary for w in ["satirique", "parodique", "pastiche", "humoristique"]):
            return 0.2, "SATIRIQUE", "Analyse Wikipédia", "Site à but humoristique, ne pas prendre au premier degré."

        # Catégorie 5 : Désinformation / Douteux (Toxique)
        if any(w in summary for w in ["fake news", "fausses nouvelles", "désinformation", "complotiste", "extrême droite", "propagande", "conspiration"]):
            return 0.0, "DANGEREUX", "Analyse Wikipédia [ALERTE]", "Site associé à de la désinformation ou théories du complot."

        # Par défaut
        return 0.5, "NEUTRE", "Wikipédia (Indécis)", "Page trouvée mais sans marqueur fort de fiabilité ou danger."

def main():
    print("=======================================================")
    print("      FAKELAB - Vérificateur de Réputation (Source)    ")
    print("=======================================================")
    
    checker = ReputationChecker()
    
    while True:
        url = input("\nEntrez une URL à vérifier (ex: lemonde.fr) [q pour quitter] : ").strip()
        if url.lower() in ['q', 'quit']: break
        
        if not url: continue
        if "." not in url: 
            print("URL invalide (manque l'extension .fr, .com...)")
            continue

        score, status, source, details = checker.check_source(url)
        
        print(f"\nRÉSULTAT pour '{url}' :")
        print(f"🎯 Score   : {score}/100")
        print(f"🚦 Statut  : {status}")
        print(f"ℹ️  Source  : {source}")
        print(f"📝 Détails : {details}")

if __name__ == "__main__":
    main()
