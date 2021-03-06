import os
import torch
import torch.nn as nn
import torchvision.models as models
from torch.autograd import Variable


class PreTrainedResnet(nn.Module):

	def __init__(self, dict_args):
		super(PreTrainedResnet, self).__init__()

		self.intermediate_layers = dict_args['intermediate_layers']
		self.pretrained_model = models.resnet18(pretrained=True).eval()
		if torch.cuda.is_available():
			self.pretrained_model = self.pretrained_model.cuda()
		for param in self.pretrained_model.parameters():
			param.requires_grad = False

	def forward(self, x):
		intermediate_features = []
		for name, module in self.pretrained_model._modules.items():
			x = module(x).squeeze().contiguous()
			if name in self.intermediate_layers:
				intermediate_features += [x]
		return intermediate_features


class PreTrainedAlexnet(nn.Module):

        def __init__(self, dict_args):
                super(PreTrainedAlexnet, self).__init__()

                self.spatial_boolean = dict_args['spatial_boolean']
                self.pretrained_model = models.alexnet(pretrained=True).eval()
                if torch.cuda.is_available():
                        self.pretrained_model = self.pretrained_model.cuda()

                if self.spatial_boolean:
                        self.features = nn.Sequential(*list(self.pretrained_model.features.children()))
                else:
                        self.features = self.pretrained_model

        def forward(self, x):
                x = self.features(x)
                x = nn.functional.avg_pool2d(x, 2, 2)
                #x = nn.functional.max_pool2d(x, 4, 1)
                return x



if __name__=='__main__':
	'''dict_args = {
				 'intermediate_layers':['layer4', 'fc']
				}
	resnet = PreTrainedResnet(dict_args)

	input = Variable(torch.randn(2,3,224,224))
	output = resnet(input)

	print(output[1].data.shape)
	print(output[1].data.type())
	print(output[1].data[0,1:3])'''


	dict_args = {
				 'spatial_boolean': True
				}
	resnet = PreTrainedAlexnet(dict_args)

	input = Variable(torch.randn(2,3,224,224))
	output = resnet(input)
	print(output.data.shape)


