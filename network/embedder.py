import gt_all_minilm_l6_v2
import pandas as pd
import numpy as np

model = gt_all_minilm_l6_v2.load_model()
texts = pd.read_csv('./dataset/anime_data.csv', encoding='utf-8')

texts['genres'] = texts['genres'].fillna('').astype(str)
texts['description'] = texts['description'].fillna('').astype(str)

def load_model():
    return model

def compute_embeddings_genres(model, texts):
    titles = texts['genres'].tolist()
    embedding_genres = model.encode(titles)
    return embedding_genres
    
def compute_embeddings_descriptions(model, texts):
    descriptions = texts['description'].tolist()
    embedding_descriptions = model.encode(descriptions)
    return embedding_descriptions

def unite_embeddings(alpha=0.3):
    genres_embeddings = compute_embeddings_genres(model, texts)
    descriptions_embeddings = compute_embeddings_descriptions(model, texts)
    combined_embeddings = alpha * genres_embeddings + (1 - alpha) * descriptions_embeddings
    return combined_embeddings