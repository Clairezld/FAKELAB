import sys
import requests
from newspaper import Article
import trafilatura
from readability import Document
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

class RobustExtractor:
    def __init__(self, headless_browser=True):
        self.headless = headless_browser

    def extract(self, url):
        """
        Tente d'extraire le contenu via une stratégie en cascade.
        """
        print(f"\n🔍 Analyse de : {url}")
        
        # 1. Newspaper3k
        print("   [1/4] Tentative Newspaper3k...", end="")
        try:
            data = self._try_newspaper(url)
            if self._validate(data):
                print("  Succès")
                return data, "Newspaper3k"
            print("  Contenu vide/incomplet")
        except Exception as e:
            print(f"  Échec ({str(e)})")

        # 2. Trafilatura
        print("   [2/4] Tentative Trafilatura...", end="")
        try:
            data = self._try_trafilatura(url)
            if self._validate(data):
                print("  Succès")
                return data, "Trafilatura"
            print("  Contenu vide")
        except Exception as e:
            print(f"  Échec ({str(e)})")

        # 3. Readability (Legacy)
        print("   [3/4] Tentative Readability...", end="")
        try:
            data = self._try_readability(url)
            if self._validate(data):
                print("  Succès")
                return data, "Readability"
            print("  Contenu vide")
        except Exception as e:
            print(f" Échec ({str(e)})")

        # 4. Selenium (Dynamic)
        print("   [4/4] Tentative Selenium (Pour sites dynamiques)...")
        try:
            data = self._try_selenium(url)
            if self._validate(data):
                print("     Succès Selenium")
                return data, "Selenium"
            print("      Contenu vide même avec Selenium")
        except Exception as e:
            print(f"      Échec Selenium ({str(e)})")

        return None, "FAILED"

    def _validate(self, data):
        """Vérifie si on a récupéré un minimum de texte."""
        if not data or not data.get('texte'):
            return False
        return len(data['texte'].strip()) > 50  # Au moins 50 caractères

    def _try_newspaper(self, url):
        article = Article(url)
        article.download()
        article.parse()
        return {
            "titre": article.title,
            "texte": article.text,
            "image": article.top_image,
            "date": str(article.publish_date)
        }

    def _try_trafilatura(self, url):
        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            return None
        text = trafilatura.extract(downloaded)
        # Trafilatura extrait moins de métadonnées par défaut, on se focus sur le texte
        return {
            "titre": "Titre (via Trafilatura)", 
            "texte": text,
            "image": None,
            "date": None
        }

    def _try_readability(self, url):
        response = requests.get(url, timeout=10)
        doc = Document(response.text)
        return {
            "titre": doc.title(),
            "texte": doc.summary(), # Readability donne du HTML souvent, à nettoyer si besoin
            "image": None,
            "date": None
        }

    def _try_selenium(self, url):
        options = Options()
        if self.headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Installation automatique du driver
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        try:
            driver.get(url)
            time.sleep(3) # Attente chargement JS
            
            # On réutilise Newspaper sur le HTML rendu par Selenium !
            # C'est une astuce puissante : Selenium charge, Newspaper parse.
            html = driver.page_source
            article = Article(url) # URL juste pour référence
            article.download(input_html=html)
            article.parse()
            
            return {
                "titre": article.title,
                "texte": article.text,
                "image": article.top_image,
                "date": None
            }
        finally:
            driver.quit()

def main():
    print("=======================================================")
    print("      FAKELAB - Pipeline d'Extraction ROBUSTE          ")
    print("=======================================================")
    
    extractor = RobustExtractor()
    
    while True:
        url = input("\nURL > ").strip()
        if url.lower() in ['q', 'quit']: break
        
        result, method = extractor.extract(url)
        
        if result:
            print(f"\n EXTRACTION RÉUSSIE via [{method}]")
            print(f"Titre : {result['titre']}")
            
            # Affichage partiel
            preview = result['texte'][:300].replace('\n', ' ') if result['texte'] else "Pas de texte"
            print(f"Aperçu : {preview}...\n")
            
            # Sauvegarde dans un fichier
            filename = "resultat_extraction.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"URL : {url}\n")
                f.write(f"TITRE : {result['titre']}\n")
                f.write(f"MÉTHODE : {method}\n")
                f.write("-" * 50 + "\n")
                f.write(result['texte'])
            
            print(f"💾 Le texte COMPLET a été sauvegardé dans : {filename}")
            print(f"   (Ouvrez ce fichier pour copier le texte entier)")
        else:
            print("\nIMPOSSIBLE D'EXTRAIRE LE CONTENU (Toutes méthodes échouées)")

if __name__ == "__main__":
    main()
