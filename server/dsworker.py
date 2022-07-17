import re
import gensim
import pandas
import numpy
import math
import scipy.spatial.distance as ds
import spacy

class DSWorker:
    n2v = dict()
    i2g = dict()
    i2gr = dict()
    i2gc = dict()
    vectors = []
    X_names = ['Коды ТН ВЭД ЕАЭС', 'Технические регламенты', 'Группа продукции']
    y_name = 'Общее наименование продукции'
    y_normalized_name = 'NORMALIZED'
    map_names = ['ИЛ' , 'Заявитель', 'Адрес Заявителя', 'Изготовитель', 'Страна', 'Адрес изготовителя']
    
    def normalize_sentence(self, sentence):
        sentence = self.nlp(sentence.lower())
        lemmatized = list()
        for token in sentence:
            if not token.is_stop and not token.is_punct:
                lemmatized.append(token.lemma_.strip())
        return " ".join(lemmatized)

    def getNearestIndexesByVector(self, vector):
        nearest_indexes = []
        if not vector.any():
            return nearest_indexes
        min_dist = math.inf
        for v in self.vectors:
            if v[0].any():
                dist = ds.cosine(v[0], vector)
                if dist < min_dist:
                    min_dist = dist
                    nearest_indexes = v[1]
        return nearest_indexes
        
    def getNearIndexesByVector(self, vector, precision):
        nearest_indexes = []
        if not vector.any():
            return nearest_indexes
        min_dist = math.inf
        min_v = []
        for v in self.vectors:
            if v[0].any():
                dist = ds.cosine(v[0], vector)
                if dist < min_dist:
                    min_dist = dist
                    min_v = v[0]
        for v in self.vectors:
            if v[0].any():
                dist = ds.cosine(min_v, v[0])
                if dist - min_dist <= precision:
                    nearest_indexes = nearest_indexes + v[1]
        return nearest_indexes    
        
    def getNearestIndexesByName(self, name):
        name = self.normalize_sentence(name)
        if name in self.n2v:
            return self.vectors[self.n2v[name]][1]
        return self.getNearestIndexesByVector(self.getSentenceVector(name))

    # sentence must be normalized
    def getSentenceVector(self, sentence):
        words = sentence.split(' ')
        return self.model.get_mean_vector(words)
        
    def getData(self, column, row):
        return self.df[[column]].values[row][0]
        
    def _check(self, indexes, codes, technicals, groups):
        need_result = self.i2g[indexes[0]]
        possible_result = self.i2gc[indexes[0]]
        user_results = [list(map(lambda x: x.strip().lower(), codes)), list(map(lambda x: x.strip().lower(), technicals)), list(map(lambda x: x.strip().lower(), groups))]
        errors = [[], [], []]
        result = True
        for i in range(0, len(user_results)):
            for user in user_results[i]:
                if user not in possible_result[i]:
                    errors[i].append([user, 'redundant'])
                    result = False
            for need in need_result[i]:
                if need not in user_results[i]:
                    errors[i].append([need, 'lost'])
                    result = False
        return [result, errors]
        
    def _getInfo(self, indexes):
        index = indexes[0]
        return self.i2gr[index]

    def check(self, rows):
        indexes = self.getNearestIndexesByName(rows['name'])
        if (len(indexes) == 0):
            return {"result": False}
        return {"result": self._check(indexes, rows['codes'], rows['technicals'], rows['groups'])}

    def getInfo(self, rows):
        indexes = self.getNearestIndexesByName(rows['name'])
        if (len(indexes) == 0):
            return {"codes": [], "technicals": [], "groups": []}
        result = self._getInfo(indexes)
        return {"codes": result[0], "technicals": result[1], "groups": result[2]}

    def getAddresses(self, rows):
        indexes = self.getNearIndexesByVector(self.getSentenceVector(rows['name']), 0.2)
        return list(map(lambda x: {"name": self.getData(self.y_name, x), "il": self.getData(self.map_names[0], x), "zayavitel": self.getData(self.map_names[1], x), "zayavitelAddress": self.getData(self.map_names[2], x), "izgotovitel": self.getData(self.map_names[3], x), "izgotovitelCountry": self.getData(self.map_names[4], x), "izgotovitelAddress": self.getData(self.map_names[5], x)}, indexes))
        
    def addInfo(self, info_fields, i):
        for j in range(0, len(self.X_names)):
            lst = info_fields[j][i]
            if lst == '' or lst == 'nan':
                self.i2g[i][0][j] = self.i2g[i][0][j] + 1
                continue
            lst = lst.split(';')
            for l in lst:
                l = l.strip()
                if l in self.i2g[i][j+1]:
                    self.i2g[i][j+1][l] = self.i2g[i][j+1][l] + 1
                else:
                    self.i2g[i][j+1][l] = 1

    def main(self, config):
        self.nlp = spacy.load('ru_core_news_sm', disable=['ner', 'parser', 'tagger'])
        self.model = gensim.models.KeyedVectors.load_word2vec_format(config['modelpath'])
        self.df = pandas.read_excel(config['datasetpath']).astype('str')
        names = list(map(lambda x : x[0], self.df[[self.y_normalized_name]].values))
        info_fields = []
        self.i2g = dict()
        for i in range(0, len(self.X_names)):
            info_fields.append(list(map(lambda x : x[0], self.df[[self.X_names[i]]].values)))
        for i in range(0, len(names)):
            name = names[i]
            if name in self.n2v:
                self.vectors[self.n2v[name]][1].append(i)
                self.addInfo(info_fields, self.vectors[self.n2v[name]][1][0])
                continue
            new_vector = self.getSentenceVector(name)
            self.vectors.append([new_vector, [i]])
            self.n2v[name] = len(self.vectors) - 1
            self.i2g[i] = [[0, 0, 0], dict(), dict(), dict()]
            self.addInfo(info_fields, i)
        for i in self.i2g:
            name = names[i]
            indexes = self.vectors[self.n2v[name]][1]
            index = indexes[0]
            result = [[], [], []]
            resultr = [[], [], []]
            resultc = [[], [], []]
            for j in range(0, len(self.X_names)):
                values = self.i2g[index][j+1]
                precision = 0.999 * (len(indexes) - self.i2g[i][0][j])
                precisionr = 0.5 * (len(indexes) - self.i2g[i][0][j])
                precisionc = 0.001 * (len(indexes) - self.i2g[i][0][j])
                for value in values:
                    if values[value] >= precisionc:
                        resultc[j].append(value.lower())
                    if values[value] >= precisionr:
                        resultr[j].append(value)
                    if values[value] >= precision:
                        result[j].append(value.lower())
            self.i2g[i] = result
            self.i2gr[i] = resultr
            self.i2gc[i] = resultc
            
    def task1(self, inputfile, outputfile):
        df = pandas.read_excel(inputfile).astype('str')
        names = list(map(lambda x : x[0], df[[self.y_name]].values))
        info_fields = []
        for i in range(0, len(self.X_names)):
            info_fields.append(list(map(lambda x : [] if x[0] == 'nan' else x[0].split(';'), df[[self.X_names[i]]].values)))
        results = []
        errors = []
        count = 0
        for i in range(0, len(names)):
            print(i)
            indexes = self.getNearestIndexesByName(names[i])
            if len(indexes) < 0:
                results.append('0')
            else:
                result = self._check(indexes, info_fields[0][i], info_fields[1][i], info_fields[2][i])
                if result[0] == True:
                    results.append('0')
                    errors.append('')
                else:
                    count = count + 1
                    results.append('1')
                    errors_string = ''
                    for j in range(0, len(self.X_names)):
                        if len(result[1][j]) > 0:
                            errors_string += self.X_names[j] + ': ' + ','.join(list(map(lambda x: x[0] + ' - ' + x[1], result[1][j]))) + ';'
                    errors.append(errors_string)
        print(count)
        df['Наличие ошибки'] = pandas.Series(results)
        df['Ошибка'] = pandas.Series(errors)
        df.to_excel(outputfile)
        
    def task2(self, inputfile, outputfile):
        df = pandas.read_excel(inputfile).astype('str')
        names = list(map(lambda x : x[0], df[[self.y_name]].values))
        results = [[], [], []]
        for i in range(0, len(names)):
            indexes = self.getNearestIndexesByName(names[i])
            if len(indexes) > 0:
                result = self._getInfo(indexes)
            else:
                result = [[], [], []]
            for i in range(0, len(results)):
                results[i].append(';'.join(result[i]))
        for i in range(0, len(self.X_names)):
            df[self.X_names[i]] = pandas.Series(results[i])
        df.to_excel(outputfile)
        
    def __init__(self, config):
        self.main(config)