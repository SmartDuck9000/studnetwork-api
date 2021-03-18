import gensim

class WordVectorizer:
    """main use - word-embedding
    uses pre-trained model (word2vec one), which is loaded from file."""

    def __init__(self, vectorizer_model, tagset:str = 'universal'):
        if tagset == 'universal':
            self.tags = ['NOUN', 'ADV', 'ADJ', 'VERB']

        self.vectorizer = gensim.models.KeyedVectors.load_word2vec_format(
            vectorizer_model, binary=True, encoding='utf-8')

    def get_vector(self, word: str, add_tag=True):
        """word embedding using vectorizer. by default, adds a POS-tag to the word
        guesses the tag of all possible variants"""
        for tag in self.tags:
            x = self.get_vector_tagged(word+ '_' + tag)
            if x is not None: return word + '_' + tag if add_tag else word, x
        return word, None

    def get_vector_tagged(self, word: str):
        """word is already tagged, no guesses are needed"""
        try:
            # todo check the tagset of a word
            x = self.vectorizer.get_vector(word)
            return x
        except:
            return None