import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from network.embedder import model, unite_embeddings, texts

def search(query, model, combined_embeddings, df, top_k=5):
    
    query_vector = model.encode(query)
    
    similarities = cosine_similarity([query_vector], combined_embeddings)[0]
    
    top_indices = np.argsort(similarities)[::-1][:top_k]
    
    results = df.iloc[top_indices].copy()
    results['score'] = similarities[top_indices]
    
    return results

def get_search(query):
    combined_embeddings = unite_embeddings()
    return search(query, model, combined_embeddings, texts)

query = input('your request: ')
combined_embeddings = unite_embeddings()
result = search(query, model, combined_embeddings, texts)
print(result)
