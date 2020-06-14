"""
utility script to view data augmentations
"""

import sys, time
# import cv2
import os
import numpy as np
# modified from https://towardsdatascience.com/exploring-image-data-augmentation-with-keras-and-tensorflow-a8162d89b844
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from matplotlib.pyplot import imread, imshow, subplots, show
from tensorflow.keras.applications.resnet50 import preprocess_input #https://stackoverflow.com/questions/47555829/preprocess-input-method-in-keras

def plot(data_generator, images):
    """
    Plots 4 images generated by an object of the ImageDataGenerator class.
    """
    data_generator.fit(images)
    image_iterator = data_generator.flow(images)

    # Plot the images given by the iterator
    rows = 3
    cols = 5
    fig, axes = subplots(nrows=rows, ncols=cols, figsize=(20,10))
    for r in range(rows):
        for c in range(cols):
            axes[r, c].imshow(image_iterator.next()[0].astype('int'))
            axes[r,c].get_xaxis().set_visible(False)
            axes[r,c].get_yaxis().set_visible(False)
    show()

filename = sys.argv[1]
image = imread(filename)

# Creating a dataset which contains just one image.
images = image.reshape((1, image.shape[0], image.shape[1], image.shape[2]))

# imshow(images[0])
# show()

# some values tweaked off:
data_generator = ImageDataGenerator(
    # preprocessing_function=preprocess_input,
    rotation_range=0,
    shear_range=10,

    width_shift_range=0.1,
    height_shift_range=0.1,
    zoom_range=0.3,

    brightness_range=(0.75,1),
    channel_shift_range=90,

    horizontal_flip=True,
)
plot(data_generator, images)
