from pathlib import Path

import numpy as np
import pandas as pd

from model import load_model

ROOT_DIR = Path(__file__).resolve().parent
DATASET_PATH = ROOT_DIR / 'databases' / 'anime_data_anilist.csv'
EMBEDDINGS_PATH = ROOT_DIR / 'databases' / 'embeddings.npy'

model = load_model()
texts = pd.read_csv(DATASET_PATH, encoding='utf-8')

texts = texts['description'].fillna('').astype(str)

def get_embeddings():
    embeddings = model.encode(
        texts.tolist(),
        batch_size=64,
        show_progress_bar=False,
    )
    np.save(EMBEDDINGS_PATH, embeddings)

if __name__ == '__main__':
    get_embeddings()
    # print(texts)