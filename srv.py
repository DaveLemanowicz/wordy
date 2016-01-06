from flask import Flask
from flask_restful import Resource, Api
import json
from flask_restful import reqparse
from random import randint
from random import shuffle
from flask.ext.cors import CORS
import datetime

app = Flask(__name__)
api = Api(app)
CORS(app)

#This causes the server to reload
#when the code changes
app.config.update(
    DEBUG = True
)

def getCurrentDate():
    now = datetime.datetime.now()
    return '{}-{:02d}-{:02d}'.format(now.year, now.month, now.day)

class Words(object):
    '''
    Represents the words list on the disk
    '''
    def __init__(self):
        self.file = None
        self.filename = 'wordlist.txt'
        self.data = None # the file is storred here as a dict
        self.change = False
        
    def _maxCorrectInARow(self):
        return self.data['settings']['max_correct_in_a_row']

    def _notSeenToday(self,max_word_length):
        newlist = []
        currdate = getCurrentDate()
        for i in range(0,len(self.data['words'])-1):
            # if  'date_attempted' not in self.data['words'][i] or (self.data['words'][i]['date_attempted'] != currdate and len(self.data['words'][i]['word'])<max_word_length):
                newlist.append(self.data['words'][i])
        return newlist
        
    
    def getList(self,max_word_length=None):
        ary = [x for x in self.data['words'] if len(x['word'])<=max_word_length]
        return ary
       
    def getNewWords(self,max_word_length=None):
        '''
        Get list of words not yet seen
        '''
        fulllist = self.getList(max_word_length);
        #reduce list to words not attempted
        filteredlist = [x for x in fulllist if x['attempts']==0]
        
        shuffle(filteredlist)
        
        return filteredlist

        
    def getWrong(self,max_word_length=None):
        '''
        Get words that were wrong last attempt
        '''
        # get list of items not seen today
        newlist = self._notSeenToday(max_word_length)
        
        # get items that were wrong last. That is, where correct_in_a_row is 0
        ret_list = []
        for i in range(0,len(newlist)-1):
            w = newlist[i]
            if w['attempts'] and w['correct_in_a_row'] == 0:
                ret_list.append(w)
        return ret_list
       
    def getMostCorrect(self,max_word_length=None):
        '''
        Get the words (of a given length) closest to being "done". That is, the words
        having the highest correct_in_a_row score that's not over the "done" limit.
        '''
        # get list of items not seen today
        newlist = self._notSeenToday(max_word_length)
                
        # Sort that list by most correct
        sortedlist = sorted(newlist, key=lambda k: -k['correct_in_a_row'])
        
        #take only those items that were correct last tima and that are under the "done" level
        ret_list = []
        for i in range(0,len(sortedlist)-1):
            w = sortedlist[i]
            if w['correct_in_a_row'] and w['correct_in_a_row'] < self._maxCorrectInARow():
                ret_list.append(w)
        return ret_list     
        
    def getSettings(self):
        return self.data['settings']
     
    def setSettings(self,params):
        self.data['settings']['max_correct_in_a_row'] = params['max_correct_in_a_row']
        self.data['settings']['max_word_size'] = params['max_word_size']
        self.data['settings']['session_length'] = params['session_length']
        self.change = True
     
    def update(self,theword,params):
        found_index = -1
        for i in range(0,len(self.data['words'])-1):
            if self.data['words'][i]['word'] == theword:
               found_index = i
               for key, value in params.iteritems():
                   self.data['words'][i][key] = value
               # add the date
               self.data['words'][i]['date_attempted'] = getCurrentDate()
               
               break
        if found_index > -1:
            self.change = True

        
    def delete(self,theword):
        found_index = -1
        for i in range(0,len(self.data['words'])-1):
            if self.data['words'][i]['word'] == theword:
               found_index = i
               break
        if found_index > -1:
            del self.data['words'][found_index]
            self.change = True
    
    def __enter__(self):
        self.file = open(self.filename,'r+')
        contents = self.file.read()
        self.data = json.loads(contents)
        if self.data['raw_word_list']:
           # Then we have to initialize the file
           words = self.data['raw_word_list'].split()
           for word in words:
               self.data['words'].append({
                   'word': word,
                   'attempts': 0,
                   'correct_count': 0,
                   'correct_in_a_row': 0
               })
           self.data['settings'] = {
               'max_word_size': 4,
               'max_correct_in_a_row': 5,
               'session_length': 20
           }
           self.change = True
        return self
        
    def __exit__(self, type, value, traceback):
        if self.change:
            self.file.seek(0)
            self.file.truncate()
            self.data['raw_word_list'] = ""
            json_string = json.dumps(self.data, indent=4, sort_keys=True)
            self.file.write(json_string)
            self.file.flush()
        self.file.close()


class WordList(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('count', type=int, help='how many words to return')
        self.parser.add_argument('maxlength', type=int, help='How many letters to limit words to')
        
    def get(self):
        # import ipdb;ipdb.set_trace()
        print "compiling list ======================"
        args = self.parser.parse_args()
        count = args['count']         # number of words wanted
        maxlength = args['maxlength'] | 0 # longest word
        with Words() as wl:
             most_correct = wl.getMostCorrect(maxlength)[:count]
             print "The list or previously correct words: " + str(len(most_correct))
             print most_correct
             wrong = wl.getWrong(maxlength)[:count]
             print "The list or previously wrong words: " + str(len(wrong))
             print wrong
             thelist = most_correct + wrong
             if len(thelist) < count*2:
                 print "adding {} new words".format(count*2 - len(thelist))
                 newwords = wl.getNewWords(maxlength)[:count*2 - len(thelist)]
                 print newwords
                 thelist += newwords
             
        shuffle(thelist)

        words = thelist[:count]
        print "words returned"
        print words
        
        return words


api.add_resource(WordList, '/wordlist')

class Word(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('attempts', type=int, help='')
        self.parser.add_argument('correct_count', type=int, help='')
        self.parser.add_argument('correct_in_a_row', type=int, help='')
        
    def get(self):
        pass

    def put(self,theword):
        #import ipdb;ipdb.set_trace()
        print 'Updating ' + theword
        params = self.parser.parse_args()
        with Words() as wl:
            wl.update(theword,params)

    def delete(self,theword):
        with Words() as wl:
            wl.delete(theword)
        print 'deleting ' + theword


api.add_resource(Word, '/word/<string:theword>')

class Settings(Resource):

    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('max_correct_in_a_row', type=int, help='')
        self.parser.add_argument('max_word_size', type=int, help='')
        self.parser.add_argument('session_length', type=int, help='')

    def get(self):
        print "In settings get"
        with Words() as wl:
            return wl.getSettings()
            
    def post(self):
        print "In settings post"
        #import ipdb;ipdb.set_trace()
        params = self.parser.parse_args()
        with Words() as wl:
            wl.setSettings(params)
        
    def put(self):
      print "In settings put"

api.add_resource(Settings, '/settings')

class Stats(Resource):
    def get(self):
        with open('wordlist.txt', 'r') as f:
            contents = f.read()
        data = json.loads(contents)
        ary = data['raw_word_list'].split()
        stats = {
          'Total Words': len(ary),
        }
        return stats


api.add_resource(Stats, '/stats')


class FullWordList(Resource):
    def get(self):
        with open('wordlist.txt', 'r') as f:
            contents = f.read()
        return json.loads(contents)


api.add_resource(FullWordList, '/fullwordlist')

if __name__ == '__main__':
    app.run() # runs at 127.0.0.1:5000
    #app.run("192.168.1.185",5000)