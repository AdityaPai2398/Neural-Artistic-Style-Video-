
from scipy.misc import imread, imresize, imsave, fromimage, toimage
from scipy.optimize import fmin_l_bfgs_b
import numpy as np
import time
import argparse
import warnings

from keras.models import Model
from keras.layers import Input
from keras.layers.convolutional import Convolution2D, AveragePooling2D, MaxPooling2D
from keras import backend as K
from keras.utils.data_utils import get_file
from keras.utils.layer_utils import convert_all_kernels_in_model
import cv2

def Stylize(arg_base_image_path, arg_style_image_path, arg_result_prefix, arg_style_masks = None, arg_color_mask=None, arg_rescale_image = False, arg_maintain_aspect_ratio = True, arg_color = False, arg_content_weight = 0.025, arg_tv_weight = 8.5e-5, arg_style_weight = [1], arg_style_scale = 1.0, arg_pool = "max", arg_init_image = "content", arg_content_loss_type = 0, arg_img_size = 400, arg_model = "vgg16", arg_content_layer= "conv5_2", arg_num_iter = 10, arg_min_improvement = 0.0, arg_rescale_method = "bilinear"):
	"""
	Neural Style Transfer with Keras 1.1.2

	Based on:
	https://github.com/fchollet/keras/blob/master/examples/neural_style_transfer.py

	-----------------------------------------------------------------------------------------------------------------------
	"""

	THEANO_WEIGHTS_PATH_NO_TOP = 'https://github.com/fchollet/deep-learning-models/releases/download/v0.1/vgg16_weights_th_dim_ordering_th_kernels_notop.h5'
	TF_WEIGHTS_PATH_NO_TOP = 'https://github.com/fchollet/deep-learning-models/releases/download/v0.1/vgg16_weights_tf_dim_ordering_tf_kernels_notop.h5'

	TH_19_WEIGHTS_PATH_NO_TOP = 'https://github.com/fchollet/deep-learning-models/releases/download/v0.1/vgg19_weights_th_dim_ordering_th_kernels_notop.h5'

	TF_19_WEIGHTS_PATH_NO_TOP = 'https://github.com/fchollet/deep-learning-models/releases/download/v0.1/vgg19_weights_tf_dim_ordering_tf_kernels_notop.h5'

	''' Arguments '''

	base_image_path = arg_base_image_path
	style_reference_image_paths = [arg_style_image_path] #arg_style_image_paths
	result_prefix = arg_result_prefix

	style_image_paths = []
	for style_image_path in style_reference_image_paths:
		style_image_paths.append(style_image_path)

	style_masks_present = arg_style_masks is not None
	mask_paths = []

	if style_masks_present:
		for mask_path in arg_style_masks:
			mask_paths.append(mask_path)

	if style_masks_present:
		assert len(style_image_paths) == len(mask_paths), "Wrong number of style masks provided.\n" \
														  "Number of style images = %d, \n" \
														  "Number of style mask paths = %d." % \
														  (len(style_image_paths), len(style_masks_present))

	color_mask_present = arg_color_mask is not None

	rescale_image = arg_rescale_image
	maintain_aspect_ratio = arg_maintain_aspect_ratio
	preserve_color = arg_color

	# these are the weights of the different loss components
	content_weight = arg_content_weight
	total_variation_weight = arg_tv_weight

	style_weights = []

	if len(style_image_paths) != len(arg_style_weight):
		print("Mismatch in number of style images provided and number of style weights provided. \n"
			  "Found %d style images and %d style weights. \n"
			  "Equally distributing weights to all other styles." % (len(style_image_paths), len(arg_style_weight)))

		weight_sum = sum(arg_style_weight) * arg_style_scale
		count = len(style_image_paths)

		for i in range(len(style_image_paths)):
			style_weights.append(weight_sum / count)
	else:
		for style_weight in arg_style_weight:
			style_weights.append(style_weight * arg_style_scale)

	# Decide pooling function
	pooltype = str(arg_pool).lower()
	assert pooltype in ["ave", "max"], 'Pooling argument is wrong. Needs to be either "ave" or "max".'

	pooltype = 1 if pooltype == "ave" else 0

	read_mode = "gray" if arg_init_image == "gray" else "color"

	# dimensions of the generated picture.
	img_width = img_height = 0
	
	img_WIDTH = base_image_path.shape[0]
	img_HEIGHT = base_image_path.shape[1]
	
	aspect_ratio = float(img_HEIGHT) / img_WIDTH

	img_width = arg_img_size
	
	if maintain_aspect_ratio:
		img_height = int(img_width * aspect_ratio)
	else:
		img_height = arg_img_size

	assert arg_content_loss_type in [0, 1, 2], "Content Loss Type must be one of 0, 1 or 2"


	# util function to open, resize and format pictures into appropriate tensors
	def preprocess_image(image_path, load_dims=False, read_mode="color"):
		#global img_width, img_height, img_WIDTH, img_HEIGHT, aspect_ratio

		mode = "RGB" if read_mode == "color" else "L"
		img = imread(image_path, mode=mode)  # Prevents crashes due to PNG images (ARGB)

		if mode == "L":
			# Expand the 1 channel grayscale to 3 channel grayscale image
			temp = np.zeros(img.shape + (3,), dtype=np.uint8)
			temp[:, :, 0] = img
			temp[:, :, 1] = img.copy()
			temp[:, :, 2] = img.copy()

			img = temp

		# if load_dims:
			# img_WIDTH = img.shape[0]
			# img_HEIGHT = img.shape[1]
			# aspect_ratio = float(img_HEIGHT) / img_WIDTH

			# img_width = arg_img_size
			# if maintain_aspect_ratio:
				# img_height = int(img_width * aspect_ratio)
			# else:
				# img_height = arg_img_size

		img = imresize(img, (img_width, img_height)).astype('float32')

		# RGB -> BGR
		img = img[:, :, ::-1]

		img[:, :, 0] -= 103.939
		img[:, :, 1] -= 116.779
		img[:, :, 2] -= 123.68

		if K.image_dim_ordering() == "th":
			img = img.transpose((2, 0, 1)).astype('float32')

		img = np.expand_dims(img, axis=0)
		return img

	def preprocess_image_wo_path(image, load_dims=True):
		#global img_width, img_height, img_WIDTH, img_HEIGHT, aspect_ratio
		
		img = image
		#print ("in preprocess_image width x height: ",img_width,img_height)
		img = imresize(img, (img_width, img_height)).astype('float32')

		# RGB -> BGR
		img = img[:, :, ::-1]

		img[:, :, 0] -= 103.939
		img[:, :, 1] -= 116.779
		img[:, :, 2] -= 123.68

		if K.image_dim_ordering() == "th":
			img = img.transpose((2, 0, 1)).astype('float32')

		img = np.expand_dims(img, axis=0)
		return img


	# util function to convert a tensor into a valid image
	def deprocess_image(x):
		if K.image_dim_ordering() == "th":
			x = x.reshape((3, img_width, img_height))
			x = x.transpose((1, 2, 0))
		else:
			x = x.reshape((img_width, img_height, 3))

		x[:, :, 0] += 103.939
		x[:, :, 1] += 116.779
		x[:, :, 2] += 123.68

		# BGR -> RGB
		x = x[:, :, ::-1]

		x = np.clip(x, 0, 255).astype('uint8')
		return x


	# util function to preserve image color
	def original_color_transform(content, generated, mask=None):
		generated = fromimage(toimage(generated, mode='RGB'), mode='YCbCr')  # Convert to YCbCr color space

		if mask is None:
			generated[:, :, 1:] = content[:, :, 1:]  # Generated CbCr = Content CbCr
		else:
			width, height, channels = generated.shape

			for i in range(width):
				for j in range(height):
					if mask[i, j] == 1:
						generated[i, j, 1:] = content[i, j, 1:]

		generated = fromimage(toimage(generated, mode='YCbCr'), mode='RGB')  # Convert to RGB color space
		return generated


	def load_mask(mask_path, shape, return_mask_img=False):
		if K.image_dim_ordering() == "th":
			_, channels, width, height = shape
		else:
			_, width, height, channels = shape

		mask = imread(mask_path, mode="L") # Grayscale mask load
		mask = imresize(mask, (width, height)).astype('float32')

		# Perform binarization of mask
		mask[mask <= 127] = 0
		mask[mask > 128] = 255

		max = np.amax(mask)
		mask /= max

		if return_mask_img: return mask

		mask_shape = shape[1:]

		mask_tensor = np.empty(mask_shape)

		for i in range(channels):
			if K.image_dim_ordering() == "th":
				mask_tensor[i, :, :] = mask
			else:
				mask_tensor[:, :, i] = mask

		return mask_tensor


	def pooling_func(x):
		if pooltype == 1:
			return AveragePooling2D((2, 2), strides=(2, 2))(x)
		else:
			return MaxPooling2D((2, 2), strides=(2, 2))(x)


	# get tensor representations of our images
	base_image = K.variable(preprocess_image_wo_path(base_image_path, True))

	print ("width x height: ",img_width,img_height)
	style_reference_images = []
	for style_path in style_image_paths:
		style_reference_images.append(K.variable(preprocess_image(style_path)))

		
	print ("width x height: ",img_width,img_height)
	# this will contain our generated image
	if K.image_dim_ordering() == 'th':
		combination_image = K.placeholder((1, 3, img_width, img_height))
	else:
		combination_image = K.placeholder((1, img_width, img_height, 3))

	image_tensors = [base_image]
	for style_image_tensor in style_reference_images:
		image_tensors.append(style_image_tensor)
	image_tensors.append(combination_image)

	nb_tensors = len(image_tensors)
	nb_style_images = nb_tensors - 2 # Content and Output image not considered

	print ("nb_tensor ",nb_tensors)
	print ("nb_style_images ",nb_style_images)
	print ("image_tensors.shape ",np.array(image_tensors).shape)
	# combine the various images into a single Keras tensor
	input_tensor = K.concatenate(image_tensors, axis=0)

	if K.image_dim_ordering() == "th":
		shape = (nb_tensors, 3, img_width, img_height)
	else:
		shape = (nb_tensors, img_width, img_height, 3)

	ip = Input(tensor=input_tensor, shape=shape)

	# build the VGG16 network with our 3 images as input
	x = Convolution2D(64, 3, 3, activation='relu', name='conv1_1', border_mode='same')(ip)
	x = Convolution2D(64, 3, 3, activation='relu', name='conv1_2', border_mode='same')(x)
	x = pooling_func(x)

	x = Convolution2D(128, 3, 3, activation='relu', name='conv2_1', border_mode='same')(x)
	x = Convolution2D(128, 3, 3, activation='relu', name='conv2_2', border_mode='same')(x)
	x = pooling_func(x)

	x = Convolution2D(256, 3, 3, activation='relu', name='conv3_1', border_mode='same')(x)
	x = Convolution2D(256, 3, 3, activation='relu', name='conv3_2', border_mode='same')(x)
	x = Convolution2D(256, 3, 3, activation='relu', name='conv3_3', border_mode='same')(x)
	if arg_model == "vgg19":
		x = Convolution2D(256, 3, 3, activation='relu', name='conv3_4', border_mode='same')(x)
	x = pooling_func(x)

	x = Convolution2D(512, 3, 3, activation='relu', name='conv4_1', border_mode='same')(x)
	x = Convolution2D(512, 3, 3, activation='relu', name='conv4_2', border_mode='same')(x)
	x = Convolution2D(512, 3, 3, activation='relu', name='conv4_3', border_mode='same')(x)
	if arg_model == "vgg19":
		x = Convolution2D(512, 3, 3, activation='relu', name='conv4_4', border_mode='same')(x)
	x = pooling_func(x)

	x = Convolution2D(512, 3, 3, activation='relu', name='conv5_1', border_mode='same')(x)
	x = Convolution2D(512, 3, 3, activation='relu', name='conv5_2', border_mode='same')(x)
	x = Convolution2D(512, 3, 3, activation='relu', name='conv5_3', border_mode='same')(x)
	if arg_model == "vgg19":
		x = Convolution2D(512, 3, 3, activation='relu', name='conv5_4', border_mode='same')(x)
	x = pooling_func(x)

	model = Model(ip, x)

	if K.image_dim_ordering() == "th":
		if arg_model == "vgg19":
			weights = get_file('vgg19_weights_th_dim_ordering_th_kernels_notop.h5', TH_19_WEIGHTS_PATH_NO_TOP, cache_subdir='models')
		else:
			weights = get_file('vgg16_weights_th_dim_ordering_th_kernels_notop.h5', THEANO_WEIGHTS_PATH_NO_TOP, cache_subdir='models')
	else:
		if arg_model == "vgg19":
			weights = get_file('vgg19_weights_tf_dim_ordering_tf_kernels_notop.h5', TF_19_WEIGHTS_PATH_NO_TOP, cache_subdir='models')
		else:
			weights = get_file('vgg16_weights_tf_dim_ordering_tf_kernels_notop.h5', TF_WEIGHTS_PATH_NO_TOP, cache_subdir='models')

	model.load_weights(weights)

	if K.backend() == 'tensorflow' and K.image_dim_ordering() == "th":
		warnings.warn('You are using the TensorFlow backend, yet you '
					  'are using the Theano '
					  'image dimension ordering convention '
					  '(`image_dim_ordering="th"`). '
					  'For best performance, set '
					  '`image_dim_ordering="tf"` in '
					  'your Keras config '
					  'at ~/.keras/keras.json.')
		convert_all_kernels_in_model(model)

	print('Model loaded.')

	# get the symbolic outputs of each "key" layer (we gave them unique names).
	outputs_dict = dict([(layer.name, layer.output) for layer in model.layers])
	shape_dict = dict([(layer.name, layer.output_shape) for layer in model.layers])

	# compute the neural style loss
	# first we need to define 4 util functions

	# the gram matrix of an image tensor (feature-wise outer product)
	def gram_matrix(x):
		assert K.ndim(x) == 3
		if K.image_dim_ordering() == "th":
			features = K.batch_flatten(x)
		else:
			features = K.batch_flatten(K.permute_dimensions(x, (2, 0, 1)))
		gram = K.dot(features, K.transpose(features))
		return gram


	# the "style loss" is designed to maintain
	# the style of the reference image in the generated image.
	# It is based on the gram matrices (which capture style) of
	# feature maps from the style reference image
	# and from the generated image
	def style_loss(style, combination, mask_path=None, nb_channels=None):
		assert K.ndim(style) == 3
		assert K.ndim(combination) == 3

		if mask_path is not None:
			style_mask = load_mask(mask_path, nb_channels)

			style = style * style_mask
			combination = combination * style_mask

			del style_mask

		S = gram_matrix(style)
		C = gram_matrix(combination)
		channels = 3
		size = img_width * img_height
		return K.sum(K.square(S - C)) / (4. * (channels ** 2) * (size ** 2))


	# an auxiliary loss function
	# designed to maintain the "content" of the
	# base image in the generated image
	def content_loss(base, combination):
		channel_dim = 0 if K.image_dim_ordering() == "th" else -1

		channels = K.shape(base)[channel_dim]
		size = img_width * img_height

		if arg_content_loss_type == 1:
			multiplier = 1 / (2. * channels ** 0.5 * size ** 0.5)
		elif arg_content_loss_type == 2:
			multiplier = 1 / (channels * size)
		else:
			multiplier = 1.

		return multiplier * K.sum(K.square(combination - base))


	# the 3rd loss function, total variation loss,
	# designed to keep the generated image locally coherent
	def total_variation_loss(x):
		assert K.ndim(x) == 4
		if K.image_dim_ordering() == 'th':
			a = K.square(x[:, :, :img_width - 1, :img_height - 1] - x[:, :, 1:, :img_height - 1])
			b = K.square(x[:, :, :img_width - 1, :img_height - 1] - x[:, :, :img_width - 1, 1:])
		else:
			a = K.square(x[:, :img_width - 1, :img_height - 1, :] - x[:, 1:, :img_height - 1, :])
			b = K.square(x[:, :img_width - 1, :img_height - 1, :] - x[:, :img_width - 1, 1:, :])
		return K.sum(K.pow(a + b, 1.25))


	# combine these loss functions into a single scalar
	loss = K.variable(0.)
	layer_features = outputs_dict[arg_content_layer]  # 'conv5_2' or 'conv4_2'
	base_image_features = layer_features[0, :, :, :]
	combination_features = layer_features[nb_tensors - 1, :, :, :]
	loss += content_weight * content_loss(base_image_features,
										  combination_features)
	style_masks = []
	if style_masks_present:
		style_masks = mask_paths # If mask present, pass dictionary of masks to style loss
	else:
		style_masks = [None for _ in range(nb_style_images)] # If masks not present, pass None to the style loss

	channel_index = 1 if K.image_dim_ordering() == "th" else -1

	feature_layers = ['conv1_1', 'conv2_1', 'conv3_1', 'conv4_1', 'conv5_1']
	for layer_name in feature_layers:
		layer_features = outputs_dict[layer_name]
		shape = shape_dict[layer_name]
		combination_features = layer_features[nb_tensors - 1, :, :, :]

		style_reference_features = layer_features[1:nb_tensors - 1, :, :, :]
		sl = []
		for j in range(nb_style_images):
			sl.append(style_loss(style_reference_features[j], combination_features, style_masks[j], shape))

		for j in range(nb_style_images):
			loss += (style_weights[j] / len(feature_layers)) * sl[j]

	loss += total_variation_weight * total_variation_loss(combination_image)

	# get the gradients of the generated image wrt the loss
	grads = K.gradients(loss, combination_image)

	outputs = [loss]
	if type(grads) in {list, tuple}:
		outputs += grads
	else:
		outputs.append(grads)

	f_outputs = K.function([combination_image], outputs)


	def eval_loss_and_grads(x):
		if K.image_dim_ordering() == 'th':
			x = x.reshape((1, 3, img_width, img_height))
		else:
			x = x.reshape((1, img_width, img_height, 3))
		outs = f_outputs([x])
		loss_value = outs[0]
		if len(outs[1:]) == 1:
			grad_values = outs[1].flatten().astype('float64')
		else:
			grad_values = np.array(outs[1:]).flatten().astype('float64')
		return loss_value, grad_values


	# this Evaluator class makes it possible
	# to compute loss and gradients in one pass
	# while retrieving them via two separate functions,
	# "loss" and "grads". This is done because scipy.optimize
	# requires separate functions for loss and gradients,
	# but computing them separately would be inefficient.
	class Evaluator(object):
		def __init__(self):
			self.loss_value = None
			self.grads_values = None

		def loss(self, x):
			assert self.loss_value is None
			loss_value, grad_values = eval_loss_and_grads(x)
			self.loss_value = loss_value
			self.grad_values = grad_values
			return self.loss_value

		def grads(self, x):
			assert self.loss_value is not None
			grad_values = np.copy(self.grad_values)
			self.loss_value = None
			self.grad_values = None
			return grad_values


	evaluator = Evaluator()

	# run scipy-based optimization (L-BFGS) over the pixels of the generated image
	# so as to minimize the neural style loss


	if "content" in arg_init_image or "gray" in arg_init_image:
		x = preprocess_image_wo_path(base_image_path, True)
	elif "noise" in arg_init_image:
		x = np.random.uniform(0, 255, (1, img_width, img_height, 3)) - 128.

		if K.image_dim_ordering() == "th":
			x = x.transpose((0, 3, 1, 2))
	else:
		print("Using initial image : ", arg_init_image)
		x = preprocess_image(arg_init_image, read_mode=read_mode)

	# We require original image if we are to preserve color in YCbCr mode
	if preserve_color:
		#content = imread(base_image_path, mode="YCbCr")
		content = cv2.cvtColor(base_image_path,cv2.COLOR_RGB2YCrCb)
		content = imresize(content, (img_width, img_height))

		if color_mask_present:
			if K.image_dim_ordering() == "th":
				color_mask_shape = (None, None, img_width, img_height)
			else:
				color_mask_shape = (None, img_width, img_height, None)

			color_mask = load_mask(arg_color_mask, color_mask_shape, return_mask_img=True)
		else:
			color_mask = None
	else:
		color_mask = None

	num_iter = arg_num_iter
	prev_min_val = -1

	improvement_threshold = float(arg_min_improvement)

	for i in range(num_iter):
		print("Starting iteration %d of %d" % ((i + 1), num_iter))
		start_time = time.time()

		x, min_val, info = fmin_l_bfgs_b(evaluator.loss, x.flatten(), fprime=evaluator.grads, maxfun=20)

		if prev_min_val == -1:
			prev_min_val = min_val

		improvement = (prev_min_val - min_val) / prev_min_val * 100

		print('Current loss value:', min_val, " Improvement : %0.3f" % improvement, "%")
		prev_min_val = min_val
		# save current generated image
		img = deprocess_image(x.copy())

		if preserve_color and content is not None:
			img = original_color_transform(content, img, mask=color_mask)

		if not rescale_image:
			img_ht = int(img_width * aspect_ratio)
			print("width x height : aspect_ratio == ",img_width,img_height,aspect_ratio)
#			img_ht = img_height
			print("Rescaling Image to (%d, %d)" % (img_width, img_ht))
			img = imresize(img, (img_width, img_ht), interp=arg_rescale_method)

		if rescale_image:
			print("Rescaling Image to (%d, %d)" % (img_WIDTH, img_HEIGHT))
			img = imresize(img, (img_WIDTH, img_HEIGHT), interp=arg_rescale_method)

		fname = result_prefix + '_at_iteration_%d.png' % (i + 1)
		end_time = time.time()
		print('Iteration %d completed in %ds' % (i + 1, end_time - start_time))
		#return the image img
		#imsave(fname, img)
	
	return img

if __name__ == "__main__":
	#cap = cv2.VideoCapture(0)
	#ret, frame = cap.read()
	#cap.release()
	frame = cv2.imread("rrf.jpg")
	frame = Stylize(frame,"./images/inputs/style/seated-nude.jpg","./output/first_try_bro", arg_num_iter = 2, arg_img_size = 600)
	cv2.imshow('frame',frame)
	imsave("dp_deep_potty.jpg", frame)
	cv2.waitKey(0)
