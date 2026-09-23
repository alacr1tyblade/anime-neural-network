from search.bm25 import bm25_search
from search.semantic import get_index_animes
import pandas as pd

df = pd.read_csv('./databases/anime_data.csv', encoding='utf-8')

def rrf(request, k=60):
    semantic_ids = get_index_animes(request)
    bm25_ids = bm25_search(request)
    scores = {}
    
    for rank, doc_id in enumerate(semantic_ids, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    
    for rank, doc_id in enumerate(bm25_ids, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    
    return sorted(scores.items(), key=lambda x: -x[1])

def get_top_animes(request, top_k=10):
    result = rrf(request)
    ids = [doc_id for doc_id, score in result]
    for anime in ids:
        title_english = df.iloc[anime]['title_english']
        if pd.isna(title_english):
            anime_title = df.iloc[anime]['title_romaji']
        else:
            anime_title = title_english
        print(anime_title)