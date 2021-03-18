import numpy as np
import pandas as pd
import re

from nltk.corpus import stopwords
from pymystem3 import Mystem

from .word_vectorizer import WordVectorizer
from .config import *

def _read_words_from_file(filename: str):
    """extract 'words' (space-separated) from file, return as string array"""
    with open(filename, 'r') as file:
        text = ''.join(file.readlines())
        text = text.replace('\n', ' ').lower()
        text = re.sub(" +", " ", text)
        words = text.split(' ')
    return words


def _manage_words(words, save_to=None):
    """just return or write to file"""
    if save_to is None:
        return words
    with open(save_to, 'w+') as file:
        file.write('\n'.join(words))


class WordDataParser:
    """works with texts, extracting lemmas, words, their frequences.
    different stages of text input are possible (both file and strings):
    - raw text/document: no parsing was made. anything may be there;
    - lemmas text/document: cleaned of waste, lemmatized. existance in dictionaries not confirmed
    - dataframe: each row holds a word, it's embedding-vector, maybe its frequency.

    most methods have two parameters:
    - save_to: filename to save the results (None returned). if save_to=None - result is returned;
    - unique_only - of all equal elements only one will be present in the result.

     usage example:
           parser = WordDataParser(vectorizer=WordVectorizer('model.bin'))
           parser.raw_document_to_dataframe(filename='raw_data.txt', save_to='word_dataset.csv', count_freq=True)"""

    def __init__(self, vectorizer: WordVectorizer = None):
        """vectorizer is used for embeddings when text parsing"""
        self.parse_size = text_parse_size

        self.mst = Mystem()
        self.stop_words_set = set(stopwords.words('english'))
        self.stop_words_set.update(stopwords.words('russian'))

        if vectorizer is not None:
            self.vectorizer = vectorizer

    def raw_document_to_dataframe(self, filename, save_to: str = None, count_freq=True):
        lemmas = self.raw_document_to_lemmas(filename, None, not count_freq)
        return self._make_lemmas_vector_dataframe(lemmas, save_to, count_freq)

    def lemmas_document_to_dataframe(self, filename, save_to: str = None, count_freq=True):
        lemmas = _read_words_from_file(filename)
        return self._make_lemmas_vector_dataframe(lemmas, save_to, count_freq)

    def raw_text_to_lemmas(self, text: str):
        # preparing data
        text = text.replace('\n', ' ').lower()
        text = re.sub(" +", " ", text)
        reg = re.compile('[^a-zA-Zа-яА-я -]')
        text = reg.sub('', text).strip()

        # lemmatization
        lemmas = self.mst.lemmatize(text)[::2]

        # deleting stop-words
        lemmas = [lemma for lemma in lemmas if not lemma in self.stop_words_set]
        return lemmas

    def raw_document_to_lemmas(self, filename: str, save_to=None, unique_only=True,
                               verbose=True):
        if verbose: print('loading file')
        with open(filename, 'r') as file:
            all_text = file.readlines()

        offset = 0
        all_size = len(all_text)
        words = set() if unique_only else list()

        while offset < all_size:
            if verbose: print('lines:', offset, '/', all_size)
            text = ''.join(all_text[offset:offset+self.parse_size])
            offset += self.parse_size

            w = self.raw_text_to_lemmas(text)
            if unique_only: words.update(w)
            else: words.extend(w)

        if unique_only: words = np.array(list(words))
        words = np.sort(words)
        return _manage_words(words, save_to)

    def _make_lemmas_vector_dataframe(self, lemmas, save_to:str = None, count_freq=True):
        if self.vectorizer is None:
            raise Exception('no vectorizer set to class! impossible to do embeddings')

        vectors, good_words, lemmas_counter = [], [], dict()
        for lm in lemmas:
            if lemmas_counter.get(lm) is None:
                lemmas_counter[lm] = 1
                word, vec = self.vectorizer.get_vector(lm)
                if vec is not None:
                    vectors.append(vec)
                    good_words.append(word)
            else: lemmas_counter[lm] += 1

        df = pd.DataFrame(vectors, columns=range(vectors[0].shape[0]))
        df['word'] = good_words
        if count_freq:  # add column with word-frequences
            freq = []
            for w in good_words:
                freq.append(lemmas_counter[w[:w.find('_')]])
            df['frequency'] = freq

        if save_to is None:
            return df
        df.to_csv(save_to)