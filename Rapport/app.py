import streamlit as st
import os
import io
import requests
import base64
from abc import ABC, abstractmethod
from PIL import Image, ImageDraw
from dotenv import load_dotenv

load_dotenv()

# --- IMPORT UNIQUE ---
try:
    from scraper import scrape_political_site, generate_bd_prompt_logic
except ImportError as e:
    st.error(f"Erreur d'importation : {e}. Vérifiez que 'scraper.py' est dans le même dossier.")
    st.stop()

# --- CONFIG ---
PARTY_URLS = {
    "rn": ["https://rassemblementnational.fr/22-mesures"],
    "lfi": ["https://programme.lafranceinsoumise.fr/programme-version-courte/"],
    "ps": ["https://www.parti-socialiste.fr/le_programme"],
    "lr": ["https://www.touteleurope.eu/vie-politique-des-etats-membres/elections-legislatives-2024-quel-est-le-programme-des-republicains-sur-l-europe/"],
    "eeln": ["https://www.latribune.fr/economie/union-europeenne/europeennes-le-programme-de-valerie-hayer-renaissance-en-3-minutes-chrono-999162.html"],
}
PARTIS_NOMS = {
    "Rassemblement National": "rn", "La France Insoumise": "lfi",
    "Parti Socialiste": "ps", "Les Républicains": "lr",
    "Renaissance": "eeln", 
}
ANGLE_SATIRIQUE = "Économie vs Réalité"

# --- PROVIDERS IMAGE ---
class ImageProvider(ABC):
    @abstractmethod
    def generate_image(self, prompt: str) -> bytes: pass

class DummyProvider(ImageProvider):
    def generate_image(self, prompt: str) -> bytes:
        img = Image.new("RGB", (1024, 512), color=(50, 60, 70))
        d = ImageDraw.Draw(img)
        d.text((360, 240), "MODE DUMMY\n(Pas de clé API)", fill=(220, 220, 220))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

class AzureOpenAIProvider(ImageProvider):
    def __init__(self, key, endpoint):
        from openai import AzureOpenAI
        self.client = AzureOpenAI(api_key=key, azure_endpoint=endpoint, api_version="2024-02-01")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "dall-e-3")
    def generate_image(self, prompt: str) -> bytes:
        try:
            res = self.client.images.generate(model=self.deployment, prompt=prompt[:3900], n=1)
            if hasattr(res.data[0], 'url') and res.data[0].url: return requests.get(res.data[0].url).content
            elif hasattr(res.data[0], 'b64_json') and res.data[0].b64_json: return base64.b64decode(res.data[0].b64_json)
            else: raise ValueError("Erreur Azure: Pas d'image.")
        except Exception as e:
            if "content_filter" in str(e): raise ValueError("⚠️ Image censurée par Azure (Sécurité).")
            raise e

def get_provider():
    if os.getenv("AZURE_OPENAI_API_KEY"): return AzureOpenAIProvider(os.getenv("AZURE_OPENAI_API_KEY"), os.getenv("AZURE_OPENAI_ENDPOINT"))
    return DummyProvider()

# --- INTERFACE ---
st.set_page_config(page_title="Politique en BD", layout="wide")
st.markdown("""
<style>
    .stExpander { border: 1px solid #444; margin-bottom: 10px; background-color: #0e1117; }
    div[data-testid="stSidebar"] button { width: 100%; border-radius: 5px; margin-bottom: 8px; }
    /* Premier bouton rouge */
    div[data-testid="stSidebar"] button:first-of-type { background-color: #ff4b4b; color: white; border: none; }
    .success-box { padding: 15px; background-color: #1e3a29; color: #d4edda; border: 1px solid #28a745; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

if "analysis_results" not in st.session_state: st.session_state.analysis_results = None
if "generated_prompt" not in st.session_state: st.session_state.generated_prompt = ""
if "generated_image" not in st.session_state: st.session_state.generated_image = None
if "status_msg" not in st.session_state: st.session_state.status_msg = ""

with st.sidebar:
    st.header("⚙️ Configuration")
    choix = st.selectbox("Parti", list(PARTIS_NOMS.keys()))
    url = st.text_input("URL", value=PARTY_URLS.get(PARTIS_NOMS[choix], [""])[0])
    st.markdown("---")
    
    # Boutons d'action
    if st.button("1. Scraper & analyser"):
        with st.spinner("Analyse..."):
            res = scrape_political_site(url)
            if res:
                st.session_state.analysis_results = res
                st.session_state.status_msg = f"{sum(len(x[2]) for x in res)} phrases pertinentes."
            else: st.error("Erreur de scraping.")
            
    if st.session_state.status_msg: st.markdown(f"<div class='success-box'>{st.session_state.status_msg}</div>", unsafe_allow_html=True)
    
    if st.button("2. Générer le prompt"):
        if st.session_state.analysis_results:
            st.session_state.generated_prompt = generate_bd_prompt_logic(choix, st.session_state.analysis_results, ANGLE_SATIRIQUE)
            
    if st.button("3. Générer l’image"):
        if st.session_state.generated_prompt:
            with st.spinner("Génération..."):
                try: st.session_state.generated_image = get_provider().generate_image(st.session_state.generated_prompt)
                except Exception as e: st.error(e)

st.title("🏛️ Politique en BD")
st.caption(f"Style : Satire Mordante | Angle : {ANGLE_SATIRIQUE}")

tab1, tab2, tab3 = st.tabs(["📄 Données", "💬 Prompt", "🎨 Résultat"])

with tab1:
    if st.session_state.analysis_results:
        for t, f, p in st.session_state.analysis_results:
            with st.expander(f"📌 {t} ({f})"):
                for phrase in p: st.write(f"• {phrase}")
                
with tab2:
    if st.session_state.generated_prompt: st.text_area("Prompt", st.session_state.generated_prompt, height=400)

with tab3:
    if st.session_state.generated_image: st.image(st.session_state.generated_image, width=650)