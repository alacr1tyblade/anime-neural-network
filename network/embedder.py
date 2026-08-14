import gt_all_minilm_l6_v2
import pandas as pd
import numpy as np

model = gt_all_minilm_l6_v2.load_model()
texts = pd.read_csv('./dataset/anime_data.csv', encoding='utf-8')

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

# def unite_embeddings(genres, description, model, all_genres, alpha=0.5):
#     # 1. Вектор жанров
#     genre_vec = np.array([1 if g in genres else 0 for g in all_genres])
#     genre_vec = genre_vec / np.linalg.norm(genre_vec) if np.linalg.norm(genre_vec) > 0 else genre_vec
    
#     # 2. Приводим к размерности 384 (повторяем до 384)
#     genre_vec_384 = np.tile(genre_vec, 8)[:384]
#     genre_vec_384 = genre_vec_384 / np.linalg.norm(genre_vec_384) if np.linalg.norm(genre_vec_384) > 0 else genre_vec_384
    
#     # 3. Вектор описания
#     desc_vec = model.encode(description)
#     desc_vec = desc_vec / np.linalg.norm(desc_vec)
    
#     # 4. Смешивание
#     combined = alpha * genre_vec_384 + (1 - alpha) * desc_vec
#     combined = combined / np.linalg.norm(combined)
    
#     return combined