import os
import io
import base64  # Ajout nécessaire pour le décodage si Azure envoie du code au lieu d'une URL
import requests
from abc import ABC, abstractmethod
from PIL import Image, ImageDraw, ImageFont

class ImageProvider(ABC):
    @abstractmethod
    def generate_image(self, prompt: str, log_callback=None) -> bytes:
        pass

class DummyProvider(ImageProvider):
    def generate_image(self, prompt: str, log_callback=None) -> bytes:
        if log_callback: log_callback("[Dummy] Début de la génération locale...", "info")
        
        # Simulation d'un petit délai pour le réalisme
        import time
        time.sleep(1)
        
        img = Image.new('RGB', (1024, 1024), color=(73, 109, 137))
        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.load_default()
        except:
            font = None
            
        d.text((50, 400), "BD Satirique Générée (Mode Dummy)", fill=(255, 255, 0))
        d.text((50, 450), "Configurez Azure OpenAI pour de vraies images.", fill=(255, 255, 255))
        d.text((50, 500), f"Prompt reçu ({len(prompt)} chars)", fill=(255, 255, 255))
        
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        
        if log_callback: log_callback("[Dummy] Image générée avec succès.", "success")
        return img_byte_arr.getvalue()

class AzureOpenAIProvider(ImageProvider):
    def __init__(self):
        from openai import AzureOpenAI
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "dall-e-3")

        if not self.endpoint or not self.api_key:
            raise ValueError("Variables d'environnement Azure manquantes.")

        self.client = AzureOpenAI(
            api_version=self.api_version,
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
        )

    def generate_image(self, prompt: str, log_callback=None) -> bytes:
        # Logs détaillés avant l'envoi
        if log_callback:
            log_callback(f"[Azure] Initialisation du client vers: {self.endpoint}", "info")
            log_callback(f"[Azure] Modèle cible: {self.deployment}", "info")
            log_callback(f"[Azure] Envoi du prompt ({len(prompt)} caractères)...", "info")

        # Tronquer pour sécurité DALL-E (max ~4000 chars)
        safe_prompt = prompt[:3900] 
        
        try:
            result = self.client.images.generate(
                model=self.deployment,
                prompt=safe_prompt,
                n=1,
                # On ne force pas le format ici pour voir ce que le serveur préfère,
                # mais le code ci-dessous gèrera les deux cas (url ou b64_json).
            )
            
            if log_callback: log_callback("[Azure] Réponse API reçue. Analyse du format...", "info")
            
            # Vérification de base : est-ce qu'on a des données ?
            if not result.data:
                raise ValueError("L'API Azure a répondu 'Succès' mais la liste 'data' est vide.")

            first_item = result.data[0]
            
            # CAS 1 : L'API renvoie une URL (Cas standard)
            if first_item.url:
                image_url = first_item.url
                if log_callback: log_callback(f"[Azure] Mode URL détecté. Téléchargement...", "info")
                
                response = requests.get(image_url)
                response.raise_for_status()
                
                if log_callback: log_callback("[Azure] Image téléchargée avec succès.", "success")
                return response.content
            
            # CAS 2 : L'API renvoie du Base64 (Cas fréquent sur certaines configs Azure)
            elif getattr(first_item, 'b64_json', None):
                if log_callback: log_callback(f"[Azure] Mode Base64 détecté. Décodage...", "info")
                image_data = base64.b64decode(first_item.b64_json)
                
                if log_callback: log_callback("[Azure] Image décodée avec succès.", "success")
                return image_data
            
            # CAS 3 : Ni URL ni Base64 -> C'est un blocage (Content Filter)
            else:
                revised_prompt = getattr(first_item, 'revised_prompt', 'Non disponible')
                error_details = f"Raison possible : Filtre de contenu (Content Filter). Prompt révisé : {revised_prompt}"
                raise ValueError(f"Azure n'a renvoyé ni URL ni image. {error_details}")

        except Exception as e:
            error_msg = str(e)
            if log_callback: log_callback(f"[Azure] ERREUR CRITIQUE: {error_msg}", "error")
            raise e

def get_provider() -> ImageProvider:
    if os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT"):
        try:
            return AzureOpenAIProvider()
        except Exception as e:
            print(f"Erreur init Azure: {e}. Fallback sur Dummy.")
            return DummyProvider()
    return DummyProvider()