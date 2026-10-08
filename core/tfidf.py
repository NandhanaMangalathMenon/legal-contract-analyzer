import math
from collections import Counter
import re

class SimpleTfidf:
    def __init__(self):
        self.doc_freqs = Counter()
        self.doc_count = 0
        self.vocab = {}
        self.idf = {}

    def _tokenize(self, text: str) -> list[str]:
        words = re.findall(r"\b\w+\b", text.lower())
        unigrams = words
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
        return unigrams + bigrams

    def fit_transform(self, texts: list[str]):
        self.doc_count = len(texts)
        tokenized_docs = [self._tokenize(t) for t in texts]
        
        for tokens in tokenized_docs:
            for token in set(tokens):
                self.doc_freqs[token] += 1
                
        for token, df in self.doc_freqs.items():
            self.vocab[token] = len(self.vocab)
            self.idf[token] = math.log((1 + self.doc_count) / (1 + df)) + 1
            
        return self.transform(texts, tokenized_docs)

    def transform(self, texts: list[str], tokenized_docs=None):
        if tokenized_docs is None:
            tokenized_docs = [self._tokenize(t) for t in texts]
            
        matrix = []
        for tokens in tokenized_docs:
            counts = Counter(tokens)
            vec = [0.0] * len(self.vocab)
            for token, count in counts.items():
                if token in self.vocab:
                    idx = self.vocab[token]
                    tf = count
                    vec[idx] = tf * self.idf[token]
            
            # L2 normalize
            norm = math.sqrt(sum(v*v for v in vec))
            if norm > 0:
                vec = [v / norm for v in vec]
            matrix.append(vec)
        return matrix


def cosine_similarity(query_matrix: list[list[float]], doc_matrix: list[list[float]]) -> list[list[float]]:
    result = []
    for q_vec in query_matrix:
        scores = []
        for d_vec in doc_matrix:
            score = sum(a * b for a, b in zip(q_vec, d_vec))
            scores.append(score)
        result.append(scores)
    return result
