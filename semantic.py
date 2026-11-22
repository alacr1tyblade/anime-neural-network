import pandas as pd
import numpy as np
import torch
from model import load_model

dataset_csv = pd.read_csv('./databases/anime_data_anilist.csv', encoding='utf-8')
embeddings = np.load('./databases/embeddings.npy')
if len(dataset_csv) != len(embeddings):
    raise ValueError(
        f'Dataset has {len(dataset_csv)} rows but embeddings have '
        f'{len(embeddings)} vectors'
    )
model = load_model()

def encode_request(request):
    request_embedding = model.encode(request)
    return request_embedding

def semantic_search(request):
    request_local = encode_request(request)
    similarities = model.similarity(request_local, embeddings)
    return similarities

def get_index_animes(request, top_k=10):
    similarities = semantic_search(request).squeeze()
    top_indeces = torch.argsort(similarities, descending=True)[:top_k]
    indeces = top_indeces.tolist()
    return indeces

def get_titles(request):
    indices = get_index_animes(request)
    return dataset_csv.iloc[indices].copy()


if __name__ == '__main__':
    query = input('request: ')
    print(get_titles(query)[['title_english', 'title_romaji', 'genres']])