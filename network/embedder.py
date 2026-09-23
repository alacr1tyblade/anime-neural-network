from sentence_transformers import SentenceTransformer
import pandas as pd
import numpy as np

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
texts = pd.read_csv('./databases/anime_data.csv', encoding='utf-8')

texts = texts['genres'].fillna('').astype(str) + texts['description'].fillna('').astype(str)
documents = []

def load_model():
    return model

def get_embeddings():
    for i in texts:
        documents.append(i)
        
    embeddings = model.encode(documents, batch_size=64, show_progress_bar=True)
    np.save('embeddings.npy', embeddings)