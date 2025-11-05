

import PyPDF2
import json
import os
from datetime import datetime
import glob

class LocalPDFProcessor:
    def __init__(self):
        # Créer les dossiers si nécessaire
        os.makedirs('data', exist_ok=True)
        os.makedirs('data/pdfs', exist_ok=True)
        
        # Charger le corpus existant ou créer un nouveau
        self.corpus = self.load_existing_corpus()
    
    def load_existing_corpus(self):
        """Charge le corpus existant ou retourne une liste vide"""
        if os.path.exists('data/corpus.json'):
            with open('data/corpus.json', 'r', encoding='utf-8') as f:
                corpus = json.load(f)
                print(f"📚 Corpus existant chargé: {len(corpus)} documents")
                return corpus
        else:
            print("📝 Nouveau corpus créé")
            return []
    
    def extract_text_from_pdf(self, pdf_path):
        """Extrait le texte d'un PDF"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                
                print(f"   📄 Nombre de pages: {len(reader.pages)}")
                
                for page_num, page in enumerate(reader.pages, 1):
                    page_text = page.extract_text()
                    text += page_text + "\n"
                
                # Nettoyer le texte
                text = ' '.join(text.split())  # Supprimer espaces multiples
                
                return text
        except Exception as e:
            print(f"   ❌ Erreur extraction: {str(e)}")
            return ""
    
    def detect_category(self, filename, text):
        """Détecte automatiquement la catégorie du document"""
        filename_lower = filename.lower()
        text_lower = text.lower()
        
        # Mots-clés par catégorie
        keywords = {
            "creation_entreprise": ["création", "cefore", "formalités", "immatriculation", "registre"],
            "financement": ["financement", "crédit", "prêt", "apej", "microcrédit", "subvention"],
            "fiscalite": ["fiscalité", "impôt", "taxe", "tva", "contribution"],
            "formation": ["formation", "accompagnement", "incubateur", "accélérateur"],
            "secteur": ["secteur", "agriculture", "technologie", "commerce", "artisanat"]
        }
        
        # Vérifier les mots-clés
        for category, words in keywords.items():
            if any(word in filename_lower or word in text_lower[:1000] for word in words):
                return category
        
        return "entrepreneuriat"
    
    def process_pdf(self, pdf_path):
        """Traite un seul PDF"""
        filename = os.path.basename(pdf_path)
        print(f"\n📥 Traitement: {filename}")
        
        # Extraire le texte
        text = self.extract_text_from_pdf(pdf_path)
        
        if len(text) < 100:
            print(f"   ⚠️  Texte trop court ({len(text)} caractères), ignoré")
            return False
        
        # Détecter la catégorie
        category = self.detect_category(filename, text)
        
        # Créer le titre à partir du nom de fichier
        title = filename.replace('.pdf', '').replace('_', ' ').replace('-', ' ')
        title = ' '.join(word.capitalize() for word in title.split())
        
        # Créer le document
        document = {
            "id": len(self.corpus) + 1,
            "title": title,
            "content": text,
            "source": "PDF Local",
            "url": pdf_path,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "category": category,
            "type": "pdf",
            "filename": filename,
            "file_size": os.path.getsize(pdf_path),
            "char_count": len(text)
        }
        
        self.corpus.append(document)
        
        print(f"   ✅ Ajouté: {len(text)} caractères")
        print(f"   📂 Catégorie: {category}")
        
        return True
    
    def process_folder(self, folder_path):
        """Traite tous les PDFs d'un dossier"""
        print(f"\n🔍 Recherche de PDFs dans: {folder_path}")
        
        # Trouver tous les PDFs
        pdf_files = glob.glob(os.path.join(folder_path, "*.pdf"))
        pdf_files += glob.glob(os.path.join(folder_path, "**/*.pdf"), recursive=True)
        
        if not pdf_files:
            print("❌ Aucun PDF trouvé!")
            return
        
        print(f"📚 {len(pdf_files)} PDF(s) trouvé(s)")
        
        # Traiter chaque PDF
        success_count = 0
        for pdf_path in pdf_files:
            if self.process_pdf(pdf_path):
                success_count += 1
        
        print(f"\n✅ {success_count}/{len(pdf_files)} PDFs traités avec succès")
    
    def save_corpus(self):
        """Sauvegarde le corpus"""
        with open('data/corpus.json', 'w', encoding='utf-8') as f:
            json.dump(self.corpus, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Corpus sauvegardé: {len(self.corpus)} documents au total")
    
    def show_statistics(self):
        """Affiche les statistiques"""
        print("\n" + "=" * 70)
        print("📊 STATISTIQUES FINALES")
        print("=" * 70)
        
        total = len(self.corpus)
        pdf_docs = [d for d in self.corpus if d['type'] == 'pdf']
        
        print(f"Total documents: {total}")
        print(f"Documents PDF: {len(pdf_docs)}")
        
        if total >= 500:
            print(f"✅ OBJECTIF ATTEINT! ({total} documents)")
        else:
            print(f"⚠️  IL MANQUE: {500 - total} documents")
        
        print("=" * 70)


def main():
    """Fonction principale"""
    print("=" * 70)
    print("📄 TRAITEMENT DES PDFs LOCAUX")
    print("=" * 70)
    
    processor = LocalPDFProcessor()
    
    # OPTION 1: Traiter un dossier spécifique
    print("\n🔧 OPTIONS:")
    print("1. Traiter tous les PDFs d'un dossier")
    print("2. Traiter un seul PDF")
    print("3. Traiter les PDFs dans le dossier actuel")
    
    choice = input("\nVotre choix (1/2/3): ").strip()
    
    if choice == "1":
        folder_path = input("Chemin du dossier contenant les PDFs: ").strip()
        if os.path.exists(folder_path):
            processor.process_folder(folder_path)
        else:
            print(f"❌ Dossier introuvable: {folder_path}")
            return
    
    elif choice == "2":
        pdf_path = input("Chemin complet du PDF: ").strip()
        if os.path.exists(pdf_path) and pdf_path.endswith('.pdf'):
            processor.process_pdf(pdf_path)
        else:
            print(f"❌ Fichier PDF introuvable: {pdf_path}")
            return
    
    elif choice == "3":
        processor.process_folder(".")
    
    else:
        print("❌ Choix invalide")
        return
    
    # Sauvegarder
    processor.save_corpus()
    
    # Afficher statistiques
    processor.show_statistics()
    
    print("\n✅ Traitement terminé!")
    print("💡 Lancez 'python check_corpus.py' pour voir les statistiques détaillées")


if __name__ == "__main__":
    main()