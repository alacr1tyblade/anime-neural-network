import BM25

texts_for_bm25 = BM25.load('./databases/anime_data.csv', document_column='description')

def bm25_search(query):
    request = [query]
    retriewer = BM25.index(texts_for_bm25)
    results = retriewer.search(request, k=10)
    list = []
    for i in range(10):
        list.append(results[0][i]['id'])
    return list
    # return results

def get_index_from_bm25(query):
    list = []
    for i in range(10):
        list.append(query[0][i]['id'])
    return list