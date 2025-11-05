from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import json
import os
from typing import List, Optional
from datetime import datetime
from backend.database import DatabaseManager
import numpy as np
from sentence_transformers import SentenceTransformer
import requests
import asyncio
import aiohttp

app = FastAPI(title="Yolsda IA Assistant")

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["\n"],
    allow_credentials=True,
    allow_methods=["\n"],
    allow_headers=["\n"],
)

# Monte le dossier static pour servir les fichiers CSS/JS
app.mount("/static", StaticFiles(directory="static"), name="static")

class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class AIResponse(BaseModel):
    response: str
    conversation_id: str
    sources: List[str] = []

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "gemma:2b"):
        self.base_url = base_url
        self.model = model
        self.session = None
    
    async def ensure_session(self):
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=15, connect=5)  # Timeout plus court
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def generate_response(self, prompt: str, context: str = "") -> str:
        await self.ensure_session()
        
        # Limite la taille du contexte
        if context and len(context) > 1000:
            context = context[:1000] + "..."
        
        # Construction du prompt avec contexte
        system_prompt = """Tu es un assistant IA spécialisé dans l'analyse d'informations entrepreneuriales. Ton objectif est de fournir des réponses **rapides (<5 secondes)**, **précises** et **factuelles**, basées uniquement sur le contexte fourni.

INSTRUCTIONS :
1. Utilise **uniquement les informations présentes dans le contexte** fourni par l'utilisateur.
2. Si une information n'est pas dans le contexte, réponds clairement : "Information non disponible dans le contexte fourni."
3. Sois **direct, concis et structuré en paragraphes fluides**.
4. **Structure tes réponses en paragraphes** :
   - Commence par une introduction qui répond directement à la question
   - Développe les détails pertinents dans un paragraphe organisé
   - Mentionne les points d'attention si nécessaire
   - Termine par une conclusion synthétique
5. Utilise des **connecteurs logiques** (ainsi, cependant, par conséquent, de plus) pour lier les idées.
6. Évite les listes à puces, privilégie les phrases complètes en paragraphes.
7. Limite les digressions et évite les généralisations.
8. Priorise la rapidité avec des phrases courtes mais structurées.

TON COMPORTEMENT :
- Tu agis comme un expert entrepreneurial capable d'analyser des données, des projets ou des situations d'affaires.
- Tu synthétises rapidement les informations pertinentes et les présentes en paragraphes fluides.
- Tu restes neutre, objectif et factuel.

Contexte disponible :
{context}

Question : {question}

Réponse structurée en paragraphes :"""
        
        full_prompt = system_prompt.format(context=context, question=prompt)
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,  # Réduit pour des réponses plus cohérentes
                        "top_p": 0.9,       # Légèrement réduit pour plus de précision
                        "top_k": 40,  
                        "num_thread": 4,     
                        "num_predict": 800, # Augmenté pour des réponses plus détaillées
                        "repeat_penalty": 1.2, # Évite les répétitions
                        "stop": ["Question :", "Contexte :"]  # Arrête la génération aux marqueurs
                    },
                    "system": "Tu es Yolsda, un assistant IA dédié à l'entrepreneuriat. Tu réponds toujours en français et en anglais de manière professionnelle et utile."
                },
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["response"]
                else:
                    error_text = await response.text()
                    print(f"Erreur Ollama {response.status}: {error_text}")
                    return f"Erreur Ollama {response.status}: {error_text}"
                    
        except asyncio.TimeoutError:
            return "Désolé, la requête a pris trop de temps. Veuillez réessayer."
        except Exception as e:
            return f"Erreur de connexion à Ollama: {str(e)}"
    
    async def close(self):
        if self.session:
            await self.session.close()

class DataProcessor:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.data = []
        self.embeddings = None
        
    def load_data_from_folder(self, folder_path: str = "data"):
        """Charge tous les fichiers JSON du dossier data"""
        if not os.path.exists(folder_path):
            print(f"Le dossier {folder_path} n'existe pas")
            return
            
        for filename in os.listdir(folder_path):
            if filename.endswith('.json'):
                file_path = os.path.join(folder_path, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                        self.process_file_data(file_data, filename)
                except Exception as e:
                    print(f"Erreur lors du chargement de {filename}: {e}")
    
    def process_file_data(self, data: dict, filename: str):
        """Traite les données d'un fichier JSON"""
        if isinstance(data, list):
            for item in data:
                self.process_item(item, filename)
        elif isinstance(data, dict):
            self.process_item(data, filename)
    
    def process_item(self, item: dict, source: str):
        """Traite un élément individuel de données"""
        text_content = self.extract_text_content(item)
        if text_content:
            self.data.append({
                'content': text_content,
                'source': source,
                'embedding': None
            })
    
    def extract_text_content(self, item: dict) -> str:
        """Extrait le contenu textuel d'un élément"""
        content_parts = []
        
        # Essaye différents champs possibles selon la structure de vos données
        possible_fields = ['content', 'text', 'body', 'article', 'description', 'title']
        
        for field in possible_fields:
            if field in item and item[field]:
                content_parts.append(str(item[field]))
        
        # Si aucun champ standard n'est trouvé, concatène tous les champs string
        if not content_parts:
            for key, value in item.items():
                if isinstance(value, str) and len(value) > 10:  # Évite les champs trop courts
                    content_parts.append(value)
        
        return " ".join(content_parts) if content_parts else ""
    
    def generate_embeddings(self):
        """Génère les embeddings pour tout le contenu chargé"""
        if not self.data:
            print("Aucune donnée à traiter")
            return
            
        texts = [item['content'] for item in self.data]
        self.embeddings = self.model.encode(texts)
        
        for i, item in enumerate(self.data):
            item['embedding'] = self.embeddings[i]
    
    def find_similar_content(self, query: str, top_k: int = 2) -> List[dict]:
        """Trouve le contenu le plus similaire à la requête"""
        if not self.data or self.embeddings is None:
            return []
        
        # Encode sans barre de progression pour plus de rapidité
        query_embedding = self.model.encode([query], show_progress_bar=False)
        similarities = np.dot(self.embeddings, query_embedding.T).flatten()
        
        # Utilise argpartition au lieu de argsort pour plus de rapidité
        top_indices = np.argpartition(similarities, -top_k)[-top_k:]
        
        results = []
        for idx in top_indices:
            similarity = float(similarities[idx])
            if similarity > 0.3:  # Seuil de similarité augmenté pour plus de pertinence
                # Tronque le contenu s'il est trop long
                content = self.data[idx]['content']
                if len(content) > 1000:
                    content = content[:1000] + "..."
                    
                results.append({
                    'content': content,
                    'source': self.data[idx]['source'],
                    'similarity': similarity
                })
        
        return results

class AIAssistant:
    def __init__(self, ollama_model: str = "llama2"):
        self.data_processor = DataProcessor()
        self.ollama_client = OllamaClient(model=ollama_model)
        self.load_knowledge_base()
    
    def load_knowledge_base(self):
        """Charge la base de connaissances"""
        print("Chargement de la base de connaissances...")
        self.data_processor.load_data_from_folder("data")
        print(f"Données chargées: {len(self.data_processor.data)} éléments")
        
        if self.data_processor.data:
            print("Génération des embeddings...")
            self.data_processor.generate_embeddings()
            print("Embeddings générés avec succès")
    
    async def generate_response(self, query: str) -> dict:
        """Génère une réponse basée sur les données disponibles avec Ollama"""
        # Cherche le contenu pertinent
        similar_content = self.data_processor.find_similar_content(query)
        
        if not similar_content:
            # Si pas de contenu pertinent, on utilise quand même Ollama
            response = await self.ollama_client.generate_response(
                query, 
                "Aucune information spécifique dans la base de connaissances. Réponds en tant qu'expert en entrepreneuriat."
            )
            print(f"Réponse sans contexte: {response}")
            return {
                "response": response,
                "sources": []
            }
        
        # Construit le contexte avec les informations pertinentes
        context = "INFORMATIONS PERTINENTES DE LA BASE DE CONNAISSANCES:\n\n"
        for i, item in enumerate(similar_content):
            context += f"--- Source {i+1} ({item['source']}) ---\n"
            context += f"{item['content']}\n\n"
        
        # Génère la réponse avec Ollama
        response = await self.ollama_client.generate_response(query, context)
        
        return {
            "response": response,
            "sources": list(set([item['source'] for item in similar_content]))
        }
    
    async def close(self):
        await self.ollama_client.close()

# Initialisation de l'assistant et de la base de données
assistant = None
db_manager = None

@app.on_event("startup")
async def startup_event():
    global assistant, db_manager
    assistant = AIAssistant(ollama_model="gemma:2b")  # Configuration pour utiliser Gemma 2B
    db_manager = DatabaseManager()  # Initialisation de la base de données
    print("Assistant IA et base de données initialisés")

@app.on_event("shutdown")
async def shutdown_event():
    if assistant:
        await assistant.close()

@app.get("/")
async def read_index():
    return FileResponse("templates/index.html")

@app.post("/chat", response_model=AIResponse)
async def chat_endpoint(chat_message: ChatMessage):
    try:
        if not assistant or not db_manager:
            raise HTTPException(status_code=500, detail="Assistant ou base de données non initialisé")
        
        # Génère la réponse
        response_data = await assistant.generate_response(chat_message.message)
        
        # Crée un ID de conversation si non fourni
        conversation_id = chat_message.conversation_id or f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Sauvegarde dans l'historique
        db_manager.save_message(
            conversation_id=conversation_id,
            message=chat_message.message,
            response=response_data["response"],
            sources=response_data["sources"]
        )
        
        return AIResponse(
            response=response_data["response"],
            conversation_id=conversation_id,
            sources=response_data["sources"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement: {str(e)}")

@app.get("/api/conversations")
async def get_conversations(limit: int = 20):
    """Récupère la liste des conversations"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Base de données non initialisée")
    # Retourne une liste directement (frontend attend un tableau)
    return db_manager.get_all_conversations(limit)


@app.post("/api/conversations")
async def create_conversation(payload: dict):
    """Crée une nouvelle conversation (optionnellement avec un titre)"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Base de données non initialisée")

    title = payload.get('title') if isinstance(payload, dict) else None
    # Génère un ID unique simple
    conversation_id = payload.get('id') if isinstance(payload, dict) and payload.get('id') else f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"

    db_manager.create_conversation(conversation_id, title)

    return {
        "id": conversation_id,
        "title": title or "Nouvelle conversation",
        "created_at": datetime.now().isoformat()
    }


@app.put("/api/conversations/{conversation_id}")
async def update_conversation(conversation_id: str, payload: dict):
    """Met à jour le titre d'une conversation"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Base de données non initialisée")

    title = payload.get('title') if isinstance(payload, dict) else None
    if title is None:
        raise HTTPException(status_code=400, detail="title is required")

    db_manager.update_conversation_title(conversation_id, title)
    return {"id": conversation_id, "title": title}


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation_api(conversation_id: str):
    """Supprime une conversation et tous ses messages"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Base de données non initialisée")

    try:
        db_manager.delete_conversation(conversation_id)
        return {"status": "deleted", "id": conversation_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression: {str(e)}")


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Récupère une conversation complète (métadonnées + messages)"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Base de données non initialisée")

    conv = db_manager.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation non trouvée")

    return conv


@app.post("/api/chat", response_model=AIResponse)
async def api_chat(chat_message: ChatMessage):
    """Compatibilité : endpoint utilisé par le frontend (/api/chat)"""
    # Appelle la même logique que /chat
    return await chat_endpoint(chat_message)

@app.get("/api/conversations/{conversation_id}/history")
async def get_conversation_history(conversation_id: str, limit: int = 10):
    """Récupère l'historique d'une conversation spécifique"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="Base de données non initialisée")
    return {"history": db_manager.get_conversation_history(conversation_id, limit)}

@app.get("/health")
async def health_check():
    ollama_status = "unknown"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:11434/api/tags") as response:
                ollama_status = "healthy" if response.status == 200 else "unhealthy"
    except:
        ollama_status = "unreachable"
    
    return {
        "status": "healthy", 
        "data_loaded": len(assistant.data_processor.data) if assistant else 0,
        "ollama_status": ollama_status
    }

@app.get("/models")
async def get_models():
    """Récupère la liste des modèles disponibles dans Ollama"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:11434/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    return {"models": data.get("models", [])}
                else:
                    return {"models": [], "error": "Impossible de récupérer les modèles"}
    except Exception as e:
        return {"models": [], "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
