import streamlit as st
import os
from dotenv import load_dotenv
from pipeline import run_fakelab_pipeline
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Chargement config
load_dotenv()
api_key = os.getenv("GOOGLE_GEMINI_API_KEY")

# --- FONCTION EMAIL SÉCURISÉE ---
def envoyer_rapport_email(destinataire, url, verdict, score):
    """Envoie le résultat par email via les secrets .env"""
    # On récupère les identifiants depuis le fichier .env pour la sécurité
    sender_email = os.getenv("EMAIL_USER") 
    sender_password = os.getenv("EMAIL_PASSWORD")
    
    if not sender_email or not sender_password:
        st.error("Erreur config : Email ou Mot de passe manquant dans .env")
        return False
    
    sujet = f"FAKELAB - Résultat d'analyse : {verdict}"
    body = f"""
    Bonjour,
    
    Voici le rapport d'analyse pour le lien soumis :
    {url}
    
    -------------------------------------------
    📊 Score de Fiabilité : {score}/100
    ⚖️ Verdict : {verdict}
    -------------------------------------------
    
    Ceci est un mail automatique généré par le dispositif FAKELAB.
    Groupe 1 - Projet Universitaire.
    """
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = destinataire
    msg['Subject'] = sujet
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, destinataire, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Erreur mail: {e}")
        return False

# Configuration de la page
st.set_page_config(page_title="FAKELAB Scanner", page_icon="🛡️", layout="wide")

# --- EN-TÊTE ---
st.title("🛡️ FAKELAB Scanner")
st.markdown("""
**Dispositif digitalisé pour identifier, contrôler et limiter les fake news.**  
*Projet universitaire - Groupe 1*
""")
st.divider()

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("Paramètres")
    st.info("Mode connecté : API Active ✅")

# --- INITIALISATION DE LA MÉMOIRE (SESSION STATE) ---
if 'resultat_analyse' not in st.session_state:
    st.session_state.resultat_analyse = None

# --- COEUR DE L'APP ---
url_input = st.text_input("🔗 Entrez le lien de l'article suspect :", placeholder="https://site-douteux.com/article...")

# Bouton d'analyse
if st.button("Lancer l'Analyse FAKELAB", type="primary"):
    if not url_input:
        st.error("Veuillez entrer une URL.")
    else:
        with st.spinner('🕵️ Extraction du contenu et vérification des sources...'):
            # On stocke le résultat dans la session pour qu'il reste affiché
            st.session_state.resultat_analyse = run_fakelab_pipeline(url_input, api_key)

# --- AFFICHAGE DES RÉSULTATS (Si disponibles en mémoire) ---
if st.session_state.resultat_analyse:
    result = st.session_state.resultat_analyse
    
    if "error" in result:
        st.error(f"Erreur : {result['error']}")
    else:
        st.success("Analyse terminée !")
        
        # 1. Le Grand Verdict
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Score de Fiabilité Global (S_final)", value=f"{result['S_final']}/100")
        with col2:
            if result['verdict'] == "FIABLE":
                st.success(f"Verdict : {result['verdict']}")
            elif result['verdict'] == "DOUTEUX":
                st.warning(f"Verdict : {result['verdict']}")
            else:
                st.error(f"Verdict : {result['verdict']}")
        with col3:
            st.metric(label="Réputation Source", value=f"{result['R_source']}/100")

        # Jauge visuelle
        st.progress(result['S_final'] / 100)
        
        st.divider()
        
        # 2. Détails de l'IA
        if result['details_ia']:
            st.subheader("🧠 Analyse Sémantique (IA)")
            ia = result['details_ia']
            
            # Calcul du A_sem pour l'affichage
            s1 = ia['analyse_subjectivite']['score']
            s2 = ia['analyse_clickbait']['score']
            s3 = ia['analyse_preuves']['score_manque_preuves']
            score_ia_total = round(((s1 + s2 + s3) / 3) * 10, 1)

            st.markdown(f"#### 📉 Score de Risque Sémantique : **{score_ia_total}/100**")
            
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Subjectivité** : `{s1}/10`")
            c1.caption(ia['analyse_subjectivite']['details'])
            
            c2.markdown(f"**Clickbait** : `{s2}/10`")
            c2.caption(ia['analyse_clickbait']['details'])
            
            c3.markdown(f"**Manque Preuves** : `{s3}/10`")
            c3.caption(ia['analyse_preuves']['details'])
            
            st.info(f"💡 **Synthèse de l'IA** : {ia['synthese_globale']}")
        
        # 3. Contenu extrait
        with st.expander("Voir le contenu extrait de l'article"):
            st.write(f"**Titre :** {result['titre']}")
            st.write(result['contenu'])

        st.divider()
        
        # --- SECTION EMAIL (FONCTIONNE MAINTENANT GRÂCE AU SESSION STATE) ---
        st.subheader("📧 Recevoir le rapport")
        col_mail, col_btn = st.columns([3, 1])
        
        with col_mail:
            email_user = st.text_input("Votre adresse email :")
        
        with col_btn:
            st.write("") # Espacement pour aligner le bouton
            st.write("") 
            if st.button("Envoyer le rapport"):
                if email_user:
                    with st.spinner("Envoi du mail..."):
                        # Note: pour que ça marche, configure ton .env (voir plus bas)
                        succes = envoyer_rapport_email(email_user, url_input, result['verdict'], result['S_final'])
                        if succes:
                            st.success("📩 Envoyé !")
                        else:
                            st.error("Échec envoi.")
                else:
                    st.warning("Email requis.")

# --- PIED DE PAGE ---
st.markdown("---")
st.caption("FAKELAB © 2025 - UNSTIM Abomey / ENSGMM - Filière GMM-3")