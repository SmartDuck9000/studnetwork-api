import pandas as pd
import numpy as np

from sklearn.metrics.pairwise import cosine_distances

from analysis.data_parsing.word_data_parser import WordDataParser
from .config import *

def imply_tags(tag_list, interest_groups_df, parser: WordDataParser,
               save_to:str=None, save_to_text:str=None,
               save_tag_descriptions:str = None):
    """ generates dataframes with tags
    input:
    - taglist - string, tags are words separated with comma
    - interest_groups_df - dataframe (or filename) with interest groups (where their interest vectors are defined)
    - save_to: where to save dataframe, where each interest has its tag index
    - save_to_text: file where to write implied tag groups. each tag is followed with associated interest descriptions
    - save_tag_descriptions: file where to save dataframe, where each tag has its description
    usage example:
        tags = 'музыка кино книги спорт технологии развлечения путешествия животные наука история еда природа мода'
        wv = WordVectorizer('model.bin')
        parser = WordDataParser(wv)
        path = '../interest_data/'
        imply_tags(tags, path+'interest_groups.csv', parser, path+'interest_tags.csv', path+'interest_tags.txt',
                   path+'tag_descriptions.csv')
    """

    if isinstance(interest_groups_df, str):
        df = pd.read_csv(interest_groups_df, index_col=0)
    else: df = interest_groups_df

    vectors = np.array(df.select_dtypes(include=['number']))
    tag_lemmas = parser.raw_text_to_lemmas(tag_list)

    tag_list = tag_list.replace('\n',' ').split()
    tag_vectors = [parser.vectorizer.get_vector(tag)[1] for tag in tag_lemmas]

    dist = cosine_distances(vectors, tag_vectors)
    interest_tags = np.argmin(dist, axis=1)
    tag_interests = [np.where(interest_tags==i)[0] for i in range(len(tag_list))]

    if save_to_text is not None:
        with open(save_to_text, 'w') as f:
            for i in range(len(tag_interests)):
                f.write(tag_list[i] + ' ' + str(len(tag_interests[i])) + '\n')
                for x in tag_interests[i]:
                    f.write('    ' + df['description'][x] + '\n')

    df_tags = pd.DataFrame(interest_tags, columns=['tag'])
    if save_to:
        df_tags.to_csv(save_to)
    if save_tag_descriptions:
        df = pd.DataFrame(tag_list, columns=['description'])
        df.to_csv(save_tag_descriptions)
    else: return df_tags


class InterestTagManager():
    def __init__(self, tags_descr_df, interest_tags_df):
        if isinstance(tags_descr_df, str):
            tags_descr_df = pd.read_csv(tags_descr_df)
        self.tags_description = tags_descr_df

        if isinstance(interest_tags_df, str):
            interest_tags_df = pd.read_csv(interest_tags_df)
        self.interest_tags = interest_tags_df

        self.tag_len = self.tags_description.shape[0]
        self.interest_len = self.interest_tags.shape[0]

        x = []
        for _ in range(self.tag_len): x.append([])
        self.tags_description['interests'] = x
        for i, tag in enumerate(self.interest_tags['tag']):
            self.tags_description['interests'][tag] += [i]

    def get_tag_vector(self, interest_vector):
        """input: interest vector
        returns vector with size of tag count, each dimension - sum of associated with tag interests
        """
        vec = np.array([0.]*self.tag_len)
        for i in range(self.interest_len):
            vec[self.interest_tags['tag'][i]] += interest_vector[i]
        return vec

    def get_maximal_tag(self, interest_vector):
        """returns dict: maximum value of tag vector and tag index"""
        vec = self.get_tag_vector(interest_vector)

        '''inds = np.where(vec==mx)[0]
        if len(inds) > 1:
            ind = np.random.choice(inds)
            pass
            s = sum(vec)
            dists = [70 + 5*i for i in range(len(inds))]
            i = 0
            while i < len(inds):
                if s > dists[i]:
                    ind = inds[i]
                i += 1
        else:
            ind = np.argmax(vec)
            #vec[ind]=0'''

        def f(ind, tag):
            if self.tags_description['description'][ind] == tag:
                best = vec[ind]
                vec[ind]=0
                ind1 = np.argmax(vec)
                if best - vec[ind1] < 1:
                    ind = ind1
            return ind

        ind = np.argmax(vec)
        ind = f(f(f(ind, 'наука'),'природа'), 'технологии')

        return {'id': ind, 'description': self.tags_description['description'][ind]}

    def get_weight_array(self, tag_dict):
        """returns interest vector, weighed with tags. if tag is active (tagname:True in dict),
        weight is tag_weight_on, else - tag_weight_off
        input: dict: {'tag_name1': bool, 'tn2':bool, ...} - tag flags. if no tagname present,
               it's supposed to be inactive"""
        vec = np.array([tag_weight_off] * self.interest_len)
        for tag_name, val in tag_dict.items():
            if val == 0: continue
            elif val == 1:
                t = self.tags_description[self.tags_description['description'] == tag_name]
                if t.shape[0] == 0: continue
                t = t.index[0]
                for interest in self.tags_description['interests'][t]:
                    vec[interest] = tag_weight_on
        return vec