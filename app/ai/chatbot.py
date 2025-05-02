import nltk
import numpy as np
import json
import random
import re
from nltk.stem import ISRIStemmer
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.optimizers import SGD
from flask import current_app
import os

# Download necessary NLTK data
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
    nltk.download('punkt')

class WaqafChatbot:
    """Arabic-language chatbot for investor support"""
    
    def __init__(self, intents_file=None):
        self.intents_file = intents_file
        self.intents = None
        self.words = []
        self.classes = []
        self.documents = []
        self.model = None
        self.stemmer = ISRIStemmer()
        
        # Ensure required NLTK data is available
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')
        
        # Load intents if file is provided
        if intents_file and os.path.exists(intents_file):
            self.load_intents(intents_file)
    
    def load_intents(self, intents_file):
        """Load intents from JSON file"""
        with open(intents_file, 'r', encoding='utf-8') as file:
            self.intents = json.load(file)
        return self.intents
    
    def preprocess_data(self):
        """Preprocess training data from intents"""
        if not self.intents:
            raise ValueError("No intents loaded")
        
        # Clear existing data
        self.words = []
        self.classes = []
        self.documents = []
        
        # Process each intent and pattern
        for intent in self.intents['intents']:
            for pattern in intent['patterns']:
                # Tokenize pattern
                word_list = nltk.word_tokenize(pattern)
                self.words.extend(word_list)
                self.documents.append((word_list, intent['tag']))
                
                # Add to classes list
                if intent['tag'] not in self.classes:
                    self.classes.append(intent['tag'])
        
        # Stem and lower each word, remove duplicates
        self.words = [self.stemmer.stem(word.lower()) for word in self.words if len(word) > 1]
        self.words = sorted(list(set(self.words)))
        
        # Sort classes
        self.classes = sorted(list(set(self.classes)))
        
        return {
            'words': self.words,
            'classes': self.classes,
            'documents': self.documents
        }
    
    def create_training_data(self):
        """Create training data for the neural network"""
        training = []
        output_empty = [0] * len(self.classes)
        
        # Create training set, bag of words for each sentence
        for doc in self.documents:
            # Initialize bag of words
            bag = []
            # List of tokenized words for the pattern
            pattern_words = doc[0]
            # Stem each word
            pattern_words = [self.stemmer.stem(word.lower()) for word in pattern_words]
            
            # Create bag of words array
            for word in self.words:
                bag.append(1) if word in pattern_words else bag.append(0)
            
            # Output is '0' for each tag and '1' for current tag
            output_row = list(output_empty)
            output_row[self.classes.index(doc[1])] = 1
            
            training.append([bag, output_row])
        
        # Shuffle and convert to numpy array
        random.shuffle(training)
        training = np.array(training, dtype=object)
        
        # Create train and test lists
        train_x = list(training[:, 0])
        train_y = list(training[:, 1])
        
        return np.array(train_x), np.array(train_y)
    
    def build_model(self):
        """Build and compile neural network model"""
        # Create model - 3 layers
        model = Sequential()
        model.add(Dense(128, input_shape=(len(self.words),), activation='relu'))
        model.add(Dropout(0.5))
        model.add(Dense(64, activation='relu'))
        model.add(Dropout(0.5))
        model.add(Dense(len(self.classes), activation='softmax'))
        
        # Compile model
        sgd = SGD(learning_rate=0.01, momentum=0.9, nesterov=True)
        model.compile(loss='categorical_crossentropy', optimizer=sgd, metrics=['accuracy'])
        
        self.model = model
        return model
    
    def train(self, epochs=200, batch_size=5):
        """Train the chatbot model"""
        # Preprocess data
        self.preprocess_data()
        
        # Create training data
        train_x, train_y = self.create_training_data()
        
        # Build model
        self.build_model()
        
        # Train model
        history = self.model.fit(
            np.array(train_x), np.array(train_y),
            epochs=epochs,
            batch_size=batch_size,
            verbose=1
        )
        
        return history
    
    def clean_up_sentence(self, sentence):
        """Clean up and tokenize a sentence"""
        # Tokenize the pattern
        sentence_words = nltk.word_tokenize(sentence)
        # Stem each word
        sentence_words = [self.stemmer.stem(word.lower()) for word in sentence_words]
        return sentence_words
    
    def bow(self, sentence):
        """Convert a sentence to bag-of-words"""
        # Tokenize and stem the sentence
        sentence_words = self.clean_up_sentence(sentence)
        # Bag of words
        bag = [0] * len(self.words)
        for s in sentence_words:
            for i, w in enumerate(self.words):
                if w == s:
                    bag[i] = 1
        return np.array(bag)
    
    def predict_class(self, sentence):
        """Predict the intent class for a given sentence"""
        if not self.model:
            raise ValueError("Model not trained or loaded")
        
        # Filter out predictions below a threshold
        ERROR_THRESHOLD = 0.25
        
        # Generate probabilities from the model
        bow = self.bow(sentence)
        res = self.model.predict(np.array([bow]))[0]
        
        # Filter out predictions below threshold
        results = [[i, r] for i, r in enumerate(res) if r > ERROR_THRESHOLD]
        
        # Sort by strength of probability
        results.sort(key=lambda x: x[1], reverse=True)
        
        return_list = []
        for r in results:
            return_list.append({"intent": self.classes[r[0]], "probability": str(r[1])})
        
        return return_list
    
    def get_response(self, intents_list, intents_json):
        """Get a response based on the predicted intent"""
        if not intents_list:
            return "عذراً، لم أفهم سؤالك. هل يمكنك إعادة صياغته؟"
        
        tag = intents_list[0]['intent']
        list_of_intents = intents_json['intents']
        
        for i in list_of_intents:
            if i['tag'] == tag:
                result = random.choice(i['responses'])
                break
        else:
            result = "عذراً، لم أفهم سؤالك. هل يمكنك إعادة صياغته؟"
        
        return result
    
    def chat(self, message):
        """Process user message and generate response"""
        # Clean and prepare message
        message_words = nltk.word_tokenize(message)
        message_words = [self.stemmer.stem(word.lower()) for word in message_words]
        
        # Create bag of words
        bag = [0] * len(self.words)
        for word in message_words:
            for i, w in enumerate(self.words):
                if w == word:
                    bag[i] = 1
        
        # Predict using model
        if self.model:
            res = self.model.predict(np.array([bag]))[0]
            ERROR_THRESHOLD = 0.25
            results = [[i, r] for i, r in enumerate(res) if r > ERROR_THRESHOLD]
            
            results.sort(key=lambda x: x[1], reverse=True)
            return_list = []
            
            for r in results:
                return_list.append({
                    "intent": self.classes[r[0]],
                    "probability": str(r[1])
                })
            
            if return_list:
                # Get the top intent
                top_intent = return_list[0]
                
                # Find matching response
                for intent in self.intents['intents']:
                    if intent['tag'] == top_intent['intent']:
                        # Get random response
                        response = random.choice(intent['responses'])
                        
                        # Get suggestions if available
                        suggestions = intent.get('suggestions', [])
                        
                        return {
                            'response': response,
                            'intents': [top_intent],
                            'suggestions': suggestions
                        }
            
        # If no match found or no model loaded
        return {
            'response': 'عذراً، لم أفهم سؤالك. هل يمكنك إعادة صياغته؟',
            'intents': [],
            'suggestions': []
        }
    
    def save_model(self, model_path, words_path, classes_path):
        """Save the trained model and data"""
        if not self.model:
            raise ValueError("No trained model to save")
        
        # Save model
        self.model.save(model_path)
        
        # Save words and classes
        with open(words_path, 'w', encoding='utf-8') as file:
            json.dump(self.words, file, ensure_ascii=False)
        
        with open(classes_path, 'w', encoding='utf-8') as file:
            json.dump(self.classes, file, ensure_ascii=False)
        
        return True
    
    def load_model(self, model_path, words_path, classes_path):
        """Load a trained model and data"""
        from tensorflow.keras.models import load_model
        
        # Load model
        self.model = load_model(model_path)
        
        # Load words and classes
        with open(words_path, 'r', encoding='utf-8') as file:
            self.words = json.load(file)
        
        with open(classes_path, 'r', encoding='utf-8') as file:
            self.classes = json.load(file)
        
        return True
