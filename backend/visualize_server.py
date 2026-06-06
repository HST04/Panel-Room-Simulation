import os
import io
import numpy as np
import umap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, StreamingResponse
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

app = FastAPI(title="Substation Vector Space Monitor")

# Path to database directory
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BACKEND_DIR, "chroma_db")

# Initialize embedding function
embedding_fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(path=DB_DIR)

try:
    collection = chroma_client.get_collection(name="substation_manuals", embedding_function=embedding_fn)
except Exception as e:
    collection = chroma_client.get_or_create_collection(name="substation_manuals", embedding_function=embedding_fn)

def get_umap_transform():
    all_data = collection.get(include=['embeddings'])
    embeddings = all_data.get('embeddings', [])
    if not embeddings or len(embeddings) < 2:
        return None, None
    
    embeddings = np.array(embeddings)
    n_neighbors = min(15, len(embeddings) - 1)
    if n_neighbors < 2:
        n_neighbors = 2
        
    transform = umap.UMAP(n_neighbors=n_neighbors, random_state=0, transform_seed=0).fit(embeddings)
    return transform, embeddings

@app.get("/plot.png")
def get_plot(query: str = Query(None)):
    transform, embeddings = get_umap_transform()
    if transform is None:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, "No embeddings found in ChromaDB.\nPlease run the app to index manuals.", 
                ha='center', va='center', fontsize=12)
        ax.axis('off')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")

    all_data = collection.get(include=['embeddings', 'metadatas', 'documents'])
    metadatas = all_data['metadatas']
    
    projected_dataset = transform.transform(embeddings)
    
    fig, ax = plt.subplots(figsize=(10, 8), facecolor='#05080c')
    ax.set_facecolor('#05080c')
    
    sources = [meta.get('source', 'Unknown') for meta in metadatas]
    unique_sources = sorted(list(set(sources)))
    
    colors = {
        "T-4 Transformer Manual": "#ef4444",
        "DC Fail Recovery Protocol": "#38bdf8",
        "P14-C1 Overcurrent Manual": "#10b981"
    }
    
    for idx, source in enumerate(unique_sources):
        mask = [s == source for s in sources]
        points = projected_dataset[mask]
        color = colors.get(source, f"C{idx}")
        ax.scatter(points[:, 0], points[:, 1], s=80, label=source, color=color, alpha=0.8, edgecolors='#1e293b', linewidths=0.5)
        
    if query and query.strip():
        query_vector = embedding_fn([query])[0]
        projected_query = transform.transform([query_vector])
        
        results = collection.query(query_texts=[query], n_results=5, include=['embeddings', 'documents', 'metadatas'])
        retrieved_embeddings = results['embeddings'][0]
        projected_retrieved = transform.transform(retrieved_embeddings)
        
        ax.scatter(projected_query[:, 0], projected_query[:, 1], s=250, marker='X', color='#eab308', 
                   label='User Query', edgecolors='black', linewidths=1.5, zorder=10)
        
        ax.scatter(projected_retrieved[:, 0], projected_retrieved[:, 1], s=180, facecolors='none', 
                   edgecolors='#a855f7', linewidths=2.5, label='Retrieved (Top 5)', zorder=9)

    ax.set_aspect('equal', 'datalim')
    ax.axis('off')
    
    legend = ax.legend(loc='upper right', facecolor='#0a101a', edgecolor='#1e3050', labelcolor='#e2ecf8', framealpha=0.9)
    legend.get_frame().set_boxstyle("round,pad=0.5")
    
    title_text = 'Substation Vector Space Dimensionality Reduction (UMAP)'
    if query:
        title_text += f'\nQuery: "{query}"'
    plt.title(title_text, color='#e2ecf8', fontsize=14, fontweight='bold', pad=20)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='#05080c')
    plt.close(fig)
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

@app.get("/", response_class=HTMLResponse)
def get_dashboard(query: str = Query(None)):
    transform, _ = get_umap_transform()
    count = collection.count()
    
    retrieved_items = []
    if query and query.strip() and transform is not None:
        results = collection.query(query_texts=[query], n_results=5, include=['documents', 'metadatas', 'distances'])
        docs = results['documents'][0]
        metas = results['metadatas'][0]
        dists = results['distances'][0]
        for d, m, dist in zip(docs, metas, dists):
            retrieved_items.append({
                "source": m.get("source", "Unknown"),
                "filename": m.get("filename", "Unknown"),
                "distance": round(float(dist), 4),
                "content": d
            })
            
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Substation Vector Space Monitor</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                background-color: #05080c;
                background-image: 
                    linear-gradient(rgba(16, 28, 48, 0.08) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(16, 28, 48, 0.08) 1px, transparent 1px);
                background-size: 20px 20px;
                color: #e2ecf8;
                font-family: 'Inter', sans-serif;
                padding: 40px;
                min-height: 100vh;
            }}
            h1 {{ font-family: 'Outfit', sans-serif; font-weight: 600; margin-bottom: 8px; color: #fff; }}
            .subtitle {{ font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #64748b; margin-bottom: 30px; }}
            .container {{ max-width: 1200px; margin: 0 auto; display: flex; flex-direction: column; gap: 30px; }}
            .grid {{ display: grid; grid-template-columns: 1fr; gap: 30px; }}
            @media (min-width: 900px) {{
                .grid {{ grid-template-columns: 1.5fr 1fr; }}
            }}
            .panel {{
                background: rgba(10, 16, 26, 0.75);
                backdrop-filter: blur(12px);
                border: 1px solid rgba(30, 48, 80, 0.35);
                border-radius: 16px;
                padding: 30px;
                box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            }}
            .panel-title {{ font-family: 'Outfit', sans-serif; font-size: 18px; margin-bottom: 20px; color: #cbd5e1; border-bottom: 1px solid rgba(30, 48, 80, 0.2); padding-bottom: 10px; }}
            .form-group {{ display: flex; gap: 15px; margin-bottom: 20px; }}
            input[type="text"] {{
                flex: 1;
                background: #020617;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
                color: white;
                font-family: 'JetBrains Mono', monospace;
                outline: none;
            }}
            input[type="text"]:focus {{ border-color: #38bdf8; }}
            button {{
                background: #0284c7;
                color: white;
                border: 1px solid #0ea5e9;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                transition: background 0.2s;
            }}
            button:hover {{ background: #0369a1; }}
            .plot-img {{ width: 100%; height: auto; border-radius: 12px; border: 1px solid rgba(30, 48, 80, 0.2); }}
            .chunk-card {{
                background: rgba(15, 23, 42, 0.8);
                border: 1px solid rgba(30, 41, 59, 0.5);
                border-radius: 10px;
                padding: 16px;
                margin-bottom: 15px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 12px;
            }}
            .chunk-header {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 11px; }}
            .source-tag {{ color: #38bdf8; font-weight: 700; }}
            .dist-tag {{ color: #a855f7; }}
            .chunk-body {{ color: #cbd5e1; line-height: 1.5; white-space: pre-wrap; }}
            .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
            .stat-card {{ background: rgba(15, 23, 42, 0.6); padding: 16px; border-radius: 10px; border: 1px solid rgba(30, 41, 59, 0.3); }}
            .stat-label {{ font-size: 11px; color: #64748b; text-transform: uppercase; }}
            .stat-value {{ font-size: 20px; font-weight: 700; margin-top: 5px; font-family: 'JetBrains Mono', monospace; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div>
                <h1>Substation Vector Space Monitor</h1>
                <p class="subtitle">PORT: 8050 | SYSTEM: ChromaDB + UMAP-2D Embedding Visualization</p>
            </div>
            
            <div class="grid">
                <div class="panel">
                    <h2 class="panel-title">Vector Space Embedding Map</h2>
                    <form action="/" method="get">
                        <div class="form-group">
                            <input type="text" name="query" value="{query or ''}" placeholder="Type search query to project and retrieve..." />
                            <button type="submit">Project & Search</button>
                        </div>
                    </form>
                    <img class="plot-img" src="/plot.png{f'?query={query}' if query else ''}" alt="UMAP Embedding Projection" />
                </div>
                
                <div class="panel">
                    <h2 class="panel-title">ChromaDB Stats & Query Results</h2>
                    
                    <div style="margin-bottom: 25px;">
                        <div class="stats-grid">
                            <div class="stat-card">
                                <div class="stat-label">Indexed Chunks</div>
                                <div class="stat-value" style="color: #38bdf8;">{count}</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-label">Model Dimension</div>
                                <div class="stat-value" style="color: #10b981;">384</div>
                            </div>
                        </div>
                    </div>
                    
                    <div>
                        <h3 style="font-size: 14px; color: #94a3b8; margin-bottom: 12px; font-family: 'Outfit';">
                            {f'Retrieved Matches for "{query}"' if query else 'Retrieved Matches (No Query)'}
                        </h3>
                        
                        {"".join([f"""
                        <div class="chunk-card">
                            <div class="chunk-header">
                                <span class="source-tag">{item['source']}</span>
                                <span class="dist-tag">L2 Distance: {item['distance']}</span>
                            </div>
                            <div class="chunk-body">{item['content']}</div>
                        </div>
                        """ for item in retrieved_items]) if retrieved_items else '<p style="color: #64748b; font-size: 13px;">Enter a query in the search field to project it and see its neighboring document chunks.</p>'}
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
