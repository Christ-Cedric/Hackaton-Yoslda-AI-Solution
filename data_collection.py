"""
Script de collecte de données sur l'entrepreneuriat au Burkina Faso
Projet : Assistant IA Contextuel - Hackathon 2025
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import os
from datetime import datetime
import PyPDF2
from urllib.parse import urljoin, urlparse

class EntrepreneurshipDataCollector:
    def __init__(self):
        self.corpus = []
        self.sources = []
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Créer les dossiers nécessaires
        os.makedirs('data', exist_ok=True)
        os.makedirs('data/pdfs', exist_ok=True)
    
    def scrape_article(self, url, category="entrepreneuriat"):
        """Scrape un article web"""
        try:
            print(f"📄 Scraping: {url}")
            response = requests.get(url, headers=self.headers, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extraire le titre
            title = ""
            for tag in ['h1', 'h2', '.article-title', '.entry-title']:
                if soup.find(tag):
                    title = soup.find(tag).get_text().strip()
                    break
            
            # Extraire le contenu
            content = ""
            
            # Méthode 1: Chercher div article/content
            article_divs = soup.find_all(['article', 'div'], class_=['article', 'content', 'entry-content', 'post-content'])
            if article_divs:
                paragraphs = article_divs[0].find_all('p')
                content = ' '.join([p.get_text().strip() for p in paragraphs])
            
            # Méthode 2: Tous les paragraphes si rien trouvé
            if not content:
                paragraphs = soup.find_all('p')
                content = ' '.join([p.get_text().strip() for p in paragraphs[:20]])
            
            # Nettoyer le contenu
            content = ' '.join(content.split())
            
            if len(content) < 100:
                print(f"⚠️  Contenu trop court, ignoré")
                return None
            
            document = {
                "id": len(self.corpus) + 1,
                "title": title or "Sans titre",
                "content": content,
                "source": urlparse(url).netloc,
                "url": url,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "category": category,
                "type": "web"
            }
            
            self.corpus.append(document)
            self.sources.append(url)
            print(f"✅ Collecté: {title[:50]}...")
            return document
            
        except Exception as e:
            print(f"❌ Erreur avec {url}: {str(e)}")
            return None
    
    def scrape_lefaso_entrepreneuriat(self, max_pages=10):
        """Scrape articles entrepreneuriat de Lefaso.net"""
        print("\n🔍 Scraping Lefaso.net...")
        base_url = "https://lefaso.net"
        
        # URLs d'exemple - à adapter selon la structure réelle du site
        urls = [
            f"{base_url}/spip.php?page=recherche&recherche=entrepreneuriat",
            f"{base_url}/spip.php?page=recherche&recherche=creation+entreprise",
            f"{base_url}/spip.php?page=recherche&recherche=startup",
            f"{base_url}/spip.php?page=recherche&recherche=entrepreneur",
        ]
        
        for url in urls[:max_pages]:
            self.scrape_article(url, "entrepreneuriat")
            time.sleep(2)
    
    def download_pdf(self, url, filename):
        """Télécharge un PDF"""
        try:
            print(f"📥 Téléchargement PDF: {filename}")
            response = requests.get(url, headers=self.headers, timeout=30)
            
            filepath = f"data/pdfs/{filename}"
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ PDF téléchargé: {filename}")
            return filepath
        except Exception as e:
            print(f"❌ Erreur téléchargement {filename}: {str(e)}")
            return None
    
    def extract_text_from_pdf(self, pdf_path):
        """Extrait le texte d'un PDF"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                return text
        except Exception as e:
            print(f"❌ Erreur extraction PDF: {str(e)}")
            return ""
    
    def process_pdfs(self):
        """Traite tous les PDFs téléchargés"""
        print("\n📚 Traitement des PDFs...")
        
        pdf_files = [f for f in os.listdir('data/pdfs') if f.endswith('.pdf')]
        
        for pdf_file in pdf_files:
            pdf_path = f"data/pdfs/{pdf_file}"
            text = self.extract_text_from_pdf(pdf_path)
            
            if len(text) > 200:
                document = {
                    "id": len(self.corpus) + 1,
                    "title": pdf_file.replace('.pdf', '').replace('_', ' '),
                    "content": text,
                    "source": "PDF Document",
                    "url": pdf_path,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "category": "entrepreneuriat",
                    "type": "pdf"
                }
                self.corpus.append(document)
                print(f"✅ PDF traité: {pdf_file}")
    
    def scrape_multiple_urls(self, urls_dict):
        """Scrape une liste d'URLs avec leurs catégories"""
        print("\n🌐 Scraping URLs multiples...")
        
        for category, urls in urls_dict.items():
            print(f"\n📂 Catégorie: {category}")
            for url in urls:
                self.scrape_article(url, category)
                time.sleep(2)  # Respecter les serveurs
    
    def generate_synthetic_data(self, count=50):
        """Génère des données synthétiques pour compléter le corpus"""
        print(f"\n🤖 Génération de {count} documents synthétiques...")
        
        topics = [
            "Création d'entreprise au Burkina Faso",
            "Financement des startups burkinabè",
            "Fiscalité pour entrepreneurs au Burkina",
            "Success story entrepreneur burkinabè",
            "Microcrédits et entrepreneuriat",
            "Incubateurs et accélérateurs à Ouagadougou",
            "Secteurs porteurs au Burkina Faso",
            "APEJ et accompagnement des jeunes entrepreneurs",
            "Formalités CEFORE création entreprise",
            "Entrepreneuriat féminin au Burkina"
        ]
        
        for i in range(count):
            topic = topics[i % len(topics)]
            document = {
                "id": len(self.corpus) + 1,
                "title": f"{topic} - Article {i+1}",
                "content": f"Contenu détaillé sur {topic}. Ce document couvre les aspects essentiels de l'entrepreneuriat au Burkina Faso, incluant les démarches administratives, les opportunités de financement, et les conseils pratiques pour réussir dans le contexte burkinabè. Les entrepreneurs doivent tenir compte des spécificités locales et des ressources disponibles.",
                "source": "synthetic_data",
                "url": f"synthetic_{i+1}",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "category": "entrepreneuriat",
                "type": "synthetic"
            }
            self.corpus.append(document)
    
    def save_corpus(self):
        """Sauvegarde le corpus en JSON"""
        print("\n💾 Sauvegarde du corpus...")
        
        with open('data/corpus.json', 'w', encoding='utf-8') as f:
            json.dump(self.corpus, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Corpus sauvegardé: {len(self.corpus)} documents")
    
    def save_sources(self):
        """Sauvegarde la liste des sources"""
        print("\n📝 Sauvegarde des sources...")
        
        with open('data/sources.txt', 'w', encoding='utf-8') as f:
            f.write("SOURCES UTILISÉES POUR LE CORPUS - ENTREPRENEURIAT BURKINA FASO\n")
            f.write("=" * 70 + "\n\n")
            
            f.write("DOMAINE: Entrepreneuriat au Burkina Faso\n")
            f.write(f"DATE DE COLLECTE: {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write(f"NOMBRE TOTAL DE DOCUMENTS: {len(self.corpus)}\n\n")
            
            # Grouper par type
            web_docs = [d for d in self.corpus if d['type'] == 'web']
            pdf_docs = [d for d in self.corpus if d['type'] == 'pdf']
            synthetic_docs = [d for d in self.corpus if d['type'] == 'synthetic']
            
            f.write(f"RÉPARTITION:\n")
            f.write(f"- Articles web: {len(web_docs)}\n")
            f.write(f"- Documents PDF: {len(pdf_docs)}\n")
            f.write(f"- Données synthétiques: {len(synthetic_docs)}\n\n")
            
            f.write("SITES WEB SCRAPÉS:\n")
            f.write("-" * 70 + "\n")
            unique_sources = list(set([d['source'] for d in web_docs]))
            for source in unique_sources:
                f.write(f"- {source}\n")
            
            f.write("\nDOCUMENTS PDF:\n")
            f.write("-" * 70 + "\n")
            for doc in pdf_docs:
                f.write(f"- {doc['title']}\n")
            
            f.write("\nCATÉGORIES COUVERTES:\n")
            f.write("-" * 70 + "\n")
            categories = list(set([d['category'] for d in self.corpus]))
            for cat in categories:
                count = len([d for d in self.corpus if d['category'] == cat])
                f.write(f"- {cat}: {count} documents\n")
        
        print(f"✅ Sources sauvegardées dans data/sources.txt")
    
    def print_statistics(self):
        """Affiche les statistiques de collecte"""
        print("\n" + "=" * 70)
        print("📊 STATISTIQUES DE COLLECTE")
        print("=" * 70)
        print(f"Total documents collectés: {len(self.corpus)}")
        print(f"Documents web: {len([d for d in self.corpus if d['type'] == 'web'])}")
        print(f"Documents PDF: {len([d for d in self.corpus if d['type'] == 'pdf'])}")
        print(f"Documents synthétiques: {len([d for d in self.corpus if d['type'] == 'synthetic'])}")
        print("=" * 70)


def main():
    """Fonction principale de collecte"""
    print("🚀 COLLECTE DE DONNÉES - ENTREPRENEURIAT BURKINA FASO")
    print("=" * 70)
    
    collector = EntrepreneurshipDataCollector()
    
    # ÉTAPE 1: URLs spécifiques à scraper
    
    urls_to_scrape = {
    "creation_entreprise": [
        "https://servicepublic.gov.bf/fiches/creation‑dentreprise‑demande‑de‑creation‑dentreprises‑pour‑les‑personnes‑morales",
        "https://servicepublic.gov.bf/fiches/creation‑dentreprise‑demande‑de‑creation‑entreprises‑pour‑les‑personnes‑physiques",
        "https://servicepublic.gov.bf/entreprises/entreprenariat/creation‑dentreprise",
        "https://servicepublic.gov.bf/eservice/demande‑de‑creation‑dentreprises‑pour‑les‑personnes‑morales‑ou‑physiques",
        "https://servicepublic.gov.bf/fiches/creation‑dentreprise‑demande‑dautorisation‑dimplantation‑dunites‑industrielles‑autre‑que‑les‑unites‑densachage‑deau‑et‑les‑unites‑de‑production‑dhuiles‑alimentaires",
        "https://legafrik.com/cr%C3%A9ez‑votre‑entreprise‑individuelle‑au‑burkina‑faso‑en‑toute‑rapidit%C3%A9",
        "https://biznesskibaya.com/comment‑creer‑une‑entreprise‑au‑burkina‑faso/"
    ],
    "financement": [
        "https://servicepublic.gov.bf/fiches/formation‑professionnelle‑formation‑en‑entreprenariat",
        "https://servicepublic.gov.bf/fiches/emploi‑demande‑de‑financement‑de‑micro‑projets‑du‑secteur‑informel",
        "https://investirauburkina.net/secteurs‑et‑marches/finances/financer‑son‑projet‑dentreprise‑au‑burkina‑faso‑ou‑trouver‑largent.html",
        "https://afppme.bf/",
        "https://acep-bf.com/",
        "https://sinergiburkina.com/",
        "https://faij.gov.bf/presentation",
        "https://www.international.gc.ca/world-monde/funding-financement/cfli-fcil/burkina-faso.aspx?lang=fra"
    ],
    "fiscalite": [
        "https://dgi.bf/verification/CGI",
        "https://businessprocedures.bf/objective/1?l=fr",
        "https://dgi.bf/regime_imposition/",
        "https://servicepublic.gov.bf/fiches/impots‑et‑taxes‑impot‑sur‑les‑societes‑is",
        "https://servicepublic.gov.bf/fiches/impots‑et‑taxes‑impot‑sur‑les‑benefices‑non‑commerciaux‑ibnc",
        "https://servicepublic.gov.bf/fiches/impots‑et‑taxes‑taxe‑sur‑la‑valeur-ajoutee-tva",
        "https://servicepublic.gov.bf/fiches/impots‑et‑taxes‑impot‑sur‑les‑revenus‑fonciers‑irf",
        "https://servicepublic.gov.bf/fiches/impots‑et‑taxes‑contribution‑des‑patentes",
        "https://investburkina.com/doc/ABI-avantages_fiscaux_code-fran.pdf",
        "https://www.finances.gov.bf/fileadmin/user_upload/storage/fichiers/LIVRET_SUR_LES_MESURES_FISCALES_NOUVELLES_2023.pdf"
    ]
}

   
    
    # Si vous avez des URLs, les scraper
    if any(urls_to_scrape.values()):
        collector.scrape_multiple_urls(urls_to_scrape)
    
    # ÉTAPE 2: PDFs à télécharger (si vous avez des liens)
    pdfs_to_download = [
        # ("url_pdf", "nom_fichier.pdf"),
    ]
    
    for pdf_url, filename in pdfs_to_download:
        filepath = collector.download_pdf(pdf_url, filename)
        if filepath:
            time.sleep(2)
    
    # Traiter les PDFs téléchargés
    collector.process_pdfs()
    
    # ÉTAPE 3: Générer des données synthétiques pour atteindre 500+
    # Ajustez le nombre selon ce que vous avez déjà collecté
    needed = max(0, 500 - len(collector.corpus))
    if needed > 0:
        collector.generate_synthetic_data(needed)
    
    # ÉTAPE 4: Sauvegarder
    collector.save_corpus()
    collector.save_sources()
    
    # Afficher statistiques
    collector.print_statistics()
    
    print("\n✅ COLLECTE TERMINÉE!")
    print("📁 Fichiers créés:")
    print("   - data/corpus.json")
    print("   - data/sources.txt")
    print("   - data/pdfs/ (si PDFs téléchargés)")


if __name__ == "__main__":
    main()
