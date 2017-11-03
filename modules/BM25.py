import math
BM_N_doc = 8521860
BM_N_term = 4151693235
BM_Doc_AVG_Len = BM_N_term/BM_N_doc
BM_K1 = 1.2
BM_K1_P1 = BM_K1 + 1
BM_b  = 0.75
BM_K2 = BM_K1 * (1 - BM_b)
BM_K3 = BM_K1 * BM_b / BM_Doc_AVG_Len
def IDF(term_len: int) -> float:
    return math.log((BM_N_doc - term_len + 0.5)/(term_len + 0.5))

def K_BM25(doc_len: int) -> float:
    # K = K2 + |d| * K3
    return BM_K2 + doc_len * BM_K3

def BM25(TF: int, K: float, IDF: float) -> float:
    # IDF * (K1 + 1) * TF / ( K + TF )
    return IDF * BM_K1_P1 * TF / (K * TF)

