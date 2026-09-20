from sentence_transformers import SentenceTransformer
import pandas as pd
import numpy as np
import torch
import BM25

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
path_to_csv = './dataset/anime_data.csv'
texts = pd.read_csv('./dataset/anime_data.csv', encoding='utf-8')
df = pd.read_csv('./dataset/anime_data.csv', encoding='utf-8')
texts_for_bm25 = BM25.load('./dataset/anime_data.csv', document_column='description')

texts = texts['genres'].fillna('').astype(str) + texts['description'].fillna('').astype(str)
documents = []

def load_model():
    return model

def get_index_from_bm25(query):
    list = []
    for i in range(10):
        list.append(query[0][i]['id'])
    return list

def bm25_search(query):
    retriewer = BM25.index(texts_for_bm25)
    results = retriewer.search(query, k=10)
    return results

def get_embeddings():
    for i in texts:
        documents.append(i)
        
    embeddings = model.encode(documents, batch_size=64, show_progress_bar=True)
    np.save('embeddings.npy', embeddings)

def encode_request(request):
    request_embedding = model.encode(request)
    return request_embedding

def semantic_search(request, embeddings):
    similarities = model.similarity(request, embeddings)
    return similarities

def get_top_animes(ids, top_k=10):
    for anime in ids:
        title_english = df.iloc[anime]['title_english']
        if pd.isna(title_english):
            anime_title = df.iloc[anime]['title_romaji']
        else:
            anime_title = title_english
        print(anime_title)

def get_index_animes(similarities, top_k=10):
    sims = similarities.squeeze()
    top_indeces = torch.argsort(sims, descending=True)[:top_k]
    indeces = top_indeces.tolist()
    return indeces

def rrf(semantic_ids, bm25_ids, k=60):
    scores = {}
    
    for rank, doc_id in enumerate(semantic_ids, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    
    for rank, doc_id in enumerate(bm25_ids, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    
    return sorted(scores.items(), key=lambda x: -x[1])

if __name__ == '__main__':
    request = input('your request: ')
    request_tensor = encode_request(request)
    file = np.load('embeddings.npy')
    similarities = semantic_search(request=request_tensor, embeddings=file)
    semantic_indeces = get_index_animes(similarities)
    a = bm25_search([request])
    bm25_indeces = get_index_from_bm25(a)
    result = rrf(semantic_indeces, bm25_indeces)
    ids = [doc_id for doc_id, score in result]
    get_top_animes(ids)