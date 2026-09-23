import numpy as np
from embedder import unite_embeddings

def save_embeddings():
    combined = unite_embeddings(alpha=0.3)
    np.save('./databases/embeddings.npy', combined)

if __name__ == '__main__':
    save_embeddings()