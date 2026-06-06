import os
import re
import math

class SubstationRAG:
    def __init__(self):
        self.manuals_dir = os.path.join(os.path.dirname(__file__), "manuals")
        self.chunks = []
        self.vocabulary = []
        self.idf = {}
        self.chunk_vectors = []
        self.load_and_index()

    def clean_text(self, text):
        # Remove special characters and split into lowercase words
        text = text.lower()
        words = re.findall(r'\b[a-z0-9-]+\b', text)
        return words

    def load_and_index(self):
        # 1. Read files and chunk them
        manual_files = [
            ("T-4 Transformer Manual", "T-4_Transformer_Manual.txt"),
            ("DC Fail Recovery Protocol", "DC_Fail_Relay_Protocol.txt"),
            ("P14-C1 Overcurrent Manual", "P14-C1_Overcurrent_Manual.txt")
        ]

        raw_chunks = []
        for name, filename in manual_files:
            filepath = os.path.join(self.manuals_dir, filename)
            if not os.path.exists(filepath):
                # Fallback if files aren't found for any reason
                continue
            
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Split manual by sections (labeled with numbers or major headings like STEP)
            # Let's split by double line breaks or section headings
            sections = re.split(r'\n(?=(?:[0-9]+\.|\bSTEP\b|================================================================================))', content)
            
            for section in sections:
                clean_sec = section.strip()
                if not clean_sec or len(clean_sec) < 50:
                    continue
                raw_chunks.append({
                    "source": name,
                    "filename": filename,
                    "content": clean_sec
                })

        self.chunks = raw_chunks

        # 2. Build TF-IDF Vocabulary
        doc_count = len(self.chunks)
        if doc_count == 0:
            return

        # Count frequencies
        all_doc_tfs = []
        df = {}
        
        for chunk in self.chunks:
            words = self.clean_text(chunk["content"])
            tf = {}
            for w in words:
                tf[w] = tf.get(w, 0) + 1
            all_doc_tfs.append(tf)
            
            for w in set(words):
                df[w] = df.get(w, 0) + 1

        # Calculate IDF
        for word, count in df.items():
            self.idf[word] = math.log((1 + doc_count) / (1 + count)) + 1
            
        self.vocabulary = list(df.keys())

        # 3. Calculate TF-IDF vectors for all chunks
        for tf in all_doc_tfs:
            vector = {}
            length = 0
            for word, freq in tf.items():
                tf_val = freq
                tfidf_val = tf_val * self.idf.get(word, 0)
                vector[word] = tfidf_val
                length += tfidf_val ** 2
            
            # Normalize vector
            length = math.sqrt(length)
            normalized_vector = {}
            if length > 0:
                for word, val in vector.items():
                    normalized_vector[word] = val / length
            
            self.chunk_vectors.append(normalized_vector)

    def search(self, query, top_k=3):
        if not self.chunks:
            return []

        # Process query
        query_words = self.clean_text(query)
        query_tf = {}
        for w in query_words:
            if w in self.idf:
                query_tf[w] = query_tf.get(w, 0) + 1

        # Calculate Query Vector
        query_vector = {}
        length = 0
        for word, freq in query_tf.items():
            tfidf_val = freq * self.idf.get(word, 0)
            query_vector[word] = tfidf_val
            length += tfidf_val ** 2
        
        length = math.sqrt(length)
        if length > 0:
            for word, val in query_vector.items():
                query_vector[word] = val / length

        # Compute Cosine Similarity
        results = []
        for i, chunk_vector in enumerate(self.chunk_vectors):
            score = 0
            # Dot product of normalized vectors
            for word, val in query_vector.items():
                if word in chunk_vector:
                    score += val * chunk_vector[word]
            
            results.append((score, self.chunks[i]))

        # Sort by score descending
        results.sort(key=lambda x: x[0], reverse=True)

        # Return top K matches with non-zero similarity (or top 1 if none match)
        top_matches = []
        for score, chunk in results[:top_k]:
            if score > 0.01 or len(top_matches) == 0:
                top_matches.append({
                    "score": round(score, 4),
                    "source": chunk["source"],
                    "filename": chunk["filename"],
                    "content": chunk["content"]
                })
                
        return top_matches

# Simple smoke test
if __name__ == "__main__":
    rag = SubstationRAG()
    print(f"Loaded {len(rag.chunks)} chunks from manuals.")
    test_query = "T-4 trip winding temperature cooling fans"
    res = rag.search(test_query, 2)
    for r in res:
        print(f"\n--- MATCH (Score: {r['score']} from {r['source']}) ---")
        print(r['content'][:300] + "...")
