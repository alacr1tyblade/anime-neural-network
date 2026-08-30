import numpy as np
import pandas as pd
from network.embedder import load_model
model = load_model()

df = pd.read_csv('dataset/anime_data.csv', encoding='utf-8')

embeddings = np.load('dataset/embeddings.npy')

def search(query, top_k=5):
    query_vec = model.encode(query)
    similarities = np.dot(embeddings, query_vec) / (np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_vec))
    top_indices = np.argsort(similarities)[::-1][:top_k]
    results = df.iloc[top_indices].copy()
    results['score'] = similarities[top_indices]
    return results