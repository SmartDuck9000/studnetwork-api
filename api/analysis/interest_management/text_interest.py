import numpy as np
import pandas as pd

from sklearn.metrics.pairwise import cosine_distances

from analysis.data_parsing.word_vectorizer import WordVectorizer
from analysis.data_parsing.word_data_parser import WordDataParser


class TextInterestManager:
    """used to get an interest-vector from text sources (word, text).
    interest-vectors are described using a pd.DataFrame instance (where vector's ones are only numeric fields)

    usage example:
        wv = WordVectorizer('../data/model.bin')
        trans = TextInterestManager('../data/interest_data/interest_groups.csv', wv)
        text = '''прекрасный рыцарь спасет принцессу от любящего читать дракона'''
        print('original text is:\n', text, '\ntrained high-meanings:\n')
        trans.print_interest(trans.text_to_interest(text), head=20)
    """

    def __init__(self, df, vectorizer: WordVectorizer = None):
        if isinstance(df, str):
            df = pd.read_csv(df, index_col=0)
        self.description = np.array(df['description'])
        self.vectors = np.array(df.select_dtypes(include=['number']))

        if vectorizer is not None:
            self.vectorizer = vectorizer

        self.word_data_parser = WordDataParser(vectorizer.vectorizer)

    def make_zeros(self):
        """makes zero-vector with size of interest count"""
        return np.zeros(self.vectors.shape[0])

    def vector_to_interest(self, vec):
        cs = cosine_distances([vec], self.vectors)[0]
        return 1-cs*cs

    def word_to_interest(self, word):
        if self.vectorizer is None:
            raise Exception('no vectorizer given!')
        _, vector = self.vectorizer.get_vector(word)
        if vector is None:
            return self.make_zeros()
        return self.vector_to_interest(vector)

    def text_to_interest(self, text):
        words = self.word_data_parser.raw_text_to_lemmas(text)

        if len(words) == 0: return self.make_zeros()
        vectors = [self.word_to_interest(w) for w in words]
        return self.combine_vectors(vectors)

    def combine_vectors(self, vectors):
        vector = self.make_zeros()
        cnts = self.make_zeros()
        for v in vectors:
            for i in range(len(v)):
                if v[i] <= 0.3: continue      # not hardcode. some heuristic for better calculations
                vector[i] = (vector[i]*cnts[i] + v[i]) / (cnts[i]+1)
                cnts[i] += 1
        return vector

    def combine_vectors_weighed(self, vectors):
        """'vectors' is array of pairs: (weight, vector)"""
        vector = self.make_zeros()
        cnts = self.make_zeros()
        for x in vectors:
            w, v = x[0], x[1]
            for i in range(len(v)):
                if v[i] <= 0.3: continue      # not hardcode. some heuristic for better calculations
                vector[i] = (vector[i]*cnts[i] + w*v[i]) / (cnts[i]+1)
                cnts[i] += 1
        return vector

    def print_interest(self, vector, head=10, tail=0):
        """more or less beautiful humanable output of interest vector"""
        x = pd.DataFrame([vector, self.description]).T
        x.columns = ['values', 'description']
        x = x.sort_values(by='values', ascending=False)
        print('value description')
        for i, x in x.head(head).iterrows():
            print("%5.2f"%x['values'], x['description'])
        if tail != 0:
            for i, x in x.tail(tail).iterrows():
                print("%5.2f" % x['values'], x['description'])
