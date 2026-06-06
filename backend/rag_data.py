import os
import re
import chromadb
from chromadb.utils import embedding_functions

class SubstationRAG:
    def __init__(self):
        self.backend_dir = os.path.dirname(__file__)
        self.manuals_dir = os.path.join(self.backend_dir, "manuals")
        self.db_dir = os.path.join(self.backend_dir, "chroma_db")
        
        # Initialize ChromaDB Persistent Client
        self.chroma_client = chromadb.PersistentClient(path=self.db_dir)
        
        # Initialize Sentence Transformer Embedding Function
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Get or create the collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="substation_manuals",
            embedding_function=self.embedding_fn
        )
        
        # Only parse and index if collection is empty
        if self.collection.count() == 0:
            self.load_and_index()

    def load_and_index(self):
        manual_files = [
            ("T-4 Transformer Manual", "T-4_Transformer_Manual.txt"),
            ("DC Fail Recovery Protocol", "DC_Fail_Relay_Protocol.txt"),
            ("P14-C1 Overcurrent Manual", "P14-C1_Overcurrent_Manual.txt")
        ]

        documents = []
        metadatas = []
        ids = []

        chunk_id = 0
        for name, filename in manual_files:
            filepath = os.path.join(self.manuals_dir, filename)
            if not os.path.exists(filepath):
                continue
            
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Split manual by sections (labeled with numbers or major headings)
            sections = re.split(r'\n(?=(?:[0-9]+\.|\bSTEP\b|================================================================================))', content)
            
            for section in sections:
                clean_sec = section.strip()
                if not clean_sec or len(clean_sec) < 50:
                    continue
                
                documents.append(clean_sec)
                metadatas.append({
                    "source": name,
                    "filename": filename
                })
                ids.append(f"doc_{chunk_id}")
                chunk_id += 1

        if documents:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"Indexed {len(documents)} chunks into ChromaDB.")

    def search(self, query, top_k=3):
        if self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )

        top_matches = []
        # Chroma returns lists of lists for distances, documents, metadatas
        if results and "documents" in results and len(results["documents"][0]) > 0:
            for i in range(len(results["documents"][0])):
                doc = results["documents"][0][i]
                meta = results["metadatas"][0][i]
                dist = results["distances"][0][i]
                
                top_matches.append({
                    "score": round(float(dist), 4),
                    "source": meta["source"],
                    "filename": meta["filename"],
                    "content": doc
                })
                
        return top_matches

if __name__ == "__main__":
    rag = SubstationRAG()
    print(f"ChromaDB Collection has {rag.collection.count()} items.")
    test_query = "T-4 trip winding temperature cooling fans"
    res = rag.search(test_query, 2)
    for r in res:
        print(f"\n--- MATCH (Distance: {r['score']} from {r['source']}) ---")
        print(r['content'][:300] + "...")
