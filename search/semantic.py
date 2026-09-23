import pandas as pd
import numpy as np
import torch
from network.model import load_model

embeddings = np.load('./databases/embeddings.npy')
model = load_model()
texts = pd.read_csv('./databases/anime_data.csv', encoding='utf-8')
df = pd.read_csv('./databases/anime_data.csv', encoding='utf-8')
texts = texts['genres'].fillna('').astype(str) + texts['description'].fillna('').astype(str)

def encode_request(request):
    request_embedding = model.encode(request)
    return request_embedding

def semantic_search(request):
    request_local = encode_request(request)
    similarities = model.similarity(request_local, embeddings)
    return similarities

def get_index_animes(request, top_k=10):
    similarities = semantic_search(request).squeeze()
    # sims = similarities.squeeze()
    top_indeces = torch.argsort(similarities, descending=True)[:top_k]
    indeces = top_indeces.tolist()
    return indeces