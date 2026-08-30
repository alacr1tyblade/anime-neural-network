import numpy as np
from embedder import unite_embeddings

def save_embeddings():
    combined = unite_embeddings(alpha=0.3)
    np.save('dataset/embeddings.npy', combined)

if __name__ == '__main__':
    save_embeddings()