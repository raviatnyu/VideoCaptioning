import torch
import torch.nn as nn
from torch.autograd import Variable
import torch.nn.functional as functional

try:
	import layers.utils as utils
	from layers.wordspretrained import PretrainedEmbeddings
	from layers.inference import BeamSearch
except:
	import utils as utils
	from wordspretrained import PretrainedEmbeddings
	from inference import BeamSearch


USE_CUDA = False
if torch.cuda.is_available():
        USE_CUDA = True

class LanguageModel(nn.Module):

	def __init__(self, dict_args):
		super(LanguageModel, self).__init__()

		self.input_dim = dict_args['input_dim']
		self.hidden_dim = dict_args['rnn_hdim']
		self.rnn_type = dict_args['rnn_type']
		self.vocab_size = dict_args["vocabulary_size"]
		self.tie_weights = dict_args["tie_weights"]
		if self.tie_weights:
			self.word_embeddings = dict_args["word_embeddings"]

		#Passed as argument to inference function instead
		#self.pretrained_words_layer = dict_args['pretrained_words_layer']


		if self.rnn_type == 'LSTM':
			self.rnn = nn.LSTMCell(self.input_dim, self.hidden_dim) #ToDO
		elif self.rnn_type == 'GRU':
			self.rnn = nn.GRUCell(self.input_dim, self.hidden_dim)
		elif self.rnn_type == 'RNN':
			pass

		self.linear = nn.Linear(self.hidden_dim, self.vocab_size)
		if self.tie_weights:
			self.linear.weight = self.word_embeddings


	def init_hidden(self, batch_size):
		weight = next(self.parameters()).data
		if self.rnn_type == 'LSTM':
			c_0 = Variable(weight.new(batch_size, self.hidden_dim).zero_())
			return c_0
		elif self.rnn_type == 'GRU':
			pass
		elif self.rnn_type == 'RNN':
			pass


	def forward(self, isequence, hidden_t, sequence_mask=None):
		#isequence: batch_size*num_words*iembed
		#hidden_t: batch_size*hidden_dim
		#sequence_mask: batch_size*num_words

		batch_size, num_words, _ = isequence.size()
		isequence = isequence.permute(1,0,2) #isequence: num_words*batch_size*iembed

		h_t = hidden_t
		if self.rnn_type == 'LSTM': c_t = self.init_hidden(batch_size)

		osequence = Variable(isequence.data.new(num_words, batch_size, self.vocab_size).zero_())

		for step in range(num_words):
			input = isequence[step]
			if self.rnn_type == 'LSTM':
				h_t, c_t = self.rnn(input, (h_t, c_t)) #h_t: batch_size*hidden_dim
			elif self.rnn_type == 'GRU':
				h_t = self.rnn(input, h_t) #h_t: batch_size*hidden_dim
			elif self.rnn_type == 'RNN':
				pass

			osequence[step] = self.linear(h_t) #batch_size*vocab_size

		osequence = osequence.permute(1,0,2)

		#redundant because we are masking the loss but who cares?
		#osequence = utils.mask_sequence(osequence, sequence_mask)

		osequence_probs = functional.log_softmax(osequence, dim=2)

		return osequence_probs #batch_size*num_words*vocab_size


	#Works only with batch size of 1 as of now
	def inference(self, hidden_t, pretrained_words_layer):
		#hidden_t: 1*hidden_dim

		dict_args = {
					'beamsize' : 2,
					'eosindex' : 0, #remove hardcoding
					'bosindex' : 1  #remove hardcoding
					} 

		beamsearch = BeamSearch(dict_args)

		hidden_t = hidden_t.expand(dict_args['beamsize'], hidden_t.size(1)) #beamsize*hidden_dim
		input_ix = Variable(torch.LongTensor([dict_args['eosindex']]).expand(dict_args['beamsize']))
		#input_ix = Variable(torch.LongTensor([dict_args['eosindex']]))
		if USE_CUDA: input_ix = input_ix.cuda()
		input_t = pretrained_words_layer(input_ix) #beamsize*wemb_dim

		if self.rnn_type == 'LSTM': c_t = self.init_hidden(dict_args['beamsize'])

		h_t = hidden_t
		for i in range(15):
			if i!=0:
				input_ix, hidden_ix = beamsearch.get_inputs()
				input_t = pretrained_words_layer(input_ix) #beamsize*wemb_dim
				#hidden_t = hidden_t.index_select(0, hidden_ix)
				h_t = h_t.index_select(0, hidden_ix)
				c_t = c_t.index_select(0, hidden_ix)
				#print(hidden_ix.view(1,-1))
			#h_t = hidden_t
			input = input_t #Attention can be added here later
			#print(input_ix.view(1,-1))
			
			if self.rnn_type == 'LSTM':
				h_t, c_t = self.rnn(input, (h_t, c_t)) #h_t: beamsize*hidden_dim
			elif self.rnn_type == 'GRU':
				h_t = self.rnn(input, h_t) #h_t: beamsize*hidden_dim
			elif self.rnn_type == 'RNN':
				pass

			#hidden_t = h_t
			ovalues = self.linear(h_t) #beamsize*vocab_size
			oprobs = functional.log_softmax(ovalues, dim=1)
			stop = beamsearch.step(oprobs, i)
			if stop:
				break

		osequence = beamsearch.get_output(index=0)
		return osequence



if __name__=='__main__':


	dict_args = {
					"use_pretrained_emb" : False,
					"backprop_embeddings" : False,
					"word_embeddings" : torch.randn(10,3), 
					"word_embdim" : 3, 
					"vocabulary_size":10
				}

	pretrainedEmbeddings = PretrainedEmbeddings(dict_args)

	dict_args = {
					'input_dim' : 3, #pretrainedEmbeddings.pretrained_embdim
					'rnn_hdim' : 3,
					'rnn_type' : 'LSTM',
					'vocabulary_size' : pretrainedEmbeddings.vocabulary_size,
					'tie_weights' : True,
					'word_embeddings' : pretrainedEmbeddings.embeddings.weight,
					'pretrained_words_layer' : pretrainedEmbeddings
				}

	sentenceDecoder = LanguageModel(dict_args)
	osequence = sentenceDecoder(Variable(torch.randn(2,3,3)), Variable(torch.randn(2,3)), Variable(torch.LongTensor([[1,1,1],[1,0,0]])))
	#print (osequence)

	osequence = sentenceDecoder.inference(Variable(torch.randn(1,3)), pretrainedEmbeddings)
	print (osequence)
