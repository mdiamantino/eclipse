from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import cv2
import matplotlib.pyplot as plt
import numpy as np
from noise import pnoise2

### Helper Functions ###
'''
Normalize variance spectrum

Implementation based on https://hal.inria.fr/hal-01349134/document 
Fabrice Neyret, Eric Heitz. Understanding and controlling contrast oscillations in stochastic texture
algorithms using Spectrum of Variance. [Research Report] LJK / Grenoble University - INRIA. 2016,
pp.8. <hal-01349134>
'''


def normalize_var(orig):
    # Spectral variance
    mean = np.mean(orig)
    spec_var = np.fft.fft2(np.square(orig - mean))
    # Normalization
    imC = np.sqrt(abs(np.real(np.fft.ifft2(spec_var))))
    imC /= np.max(imC)
    minC = 0.001
    imK = (minC + 1) / (minC + imC)
    img = mean + (orig - mean) * imK
    return normalize(img)


def normalize(vec):
    """
    Normalize vector
    :param vec:
    :return:
    """
    vmax = np.amax(vec)
    vmin = np.amin(vec)
    return (vec - vmin) / (vmax - vmin)


def valid_position(size, x, y):
    """
    Valid positions for Gabor noise
    :param size:
    :param x:
    :param y:
    :return:
    """
    if x < 0 or x >= size: return False
    if y < 0 or y >= size: return False
    return True


def gaborK(ksize, sigma, theta, lambd, xy_ratio, sides):
    """
    Procedural Noise
    # Note: Do not take these as optimized implementations.
    :param ksize:
    :param sigma: variance of gaussian envelope
    :param theta: orientation
    :param lambd: sinusoid wavelength, bandwidth
    :param xy_ratio: value of x/y
    :param sides: number of directions
    :return:
    """
    gabor_kern = cv2.getGaborKernel((ksize, ksize), sigma, theta, lambd, xy_ratio, 0,
                                    ktype=cv2.CV_32F)
    for i in range(1, sides):
        gabor_kern += cv2.getGaborKernel((ksize, ksize), sigma, theta + np.pi * i / sides,
                                         lambd, xy_ratio, 0, ktype=cv2.CV_32F)
    return gabor_kern


def gaborN_rand(size, grid, num_kern, ksize, sigma, theta, lambd, xy_ratio=1, sides=1,
                seed=0):
    """
    Gabor noise
        - randomly distributed kernels
        - anisotropic when sides = 1, pseudo-isotropic for larger "sides"
    :param size:
    :param grid:
    :param num_kern:
    :param ksize:
    :param sigma:
    :param theta:
    :param lambd:
    :param xy_ratio:
    :param sides:
    :param seed:
    :return:
    """
    np.random.seed(seed)

    # Gabor kernel
    if sides != 1:
        gabor_kern = gaborK(ksize, sigma, theta, lambd, xy_ratio, sides)
    else:
        gabor_kern = cv2.getGaborKernel((ksize, ksize), sigma, theta, lambd, xy_ratio, 0,
                                        ktype=cv2.CV_32F)

    # Sparse convolution noise
    sp_conv = np.zeros([size, size])
    dim = int(size / 2 // grid)
    noise = []
    for i in range(-dim, dim + 1):
        for j in range(-dim, dim + 1):
            x = i * grid + size / 2 - grid / 2
            y = j * grid + size / 2 - grid / 2
            for _ in range(num_kern):
                dx = np.random.randint(0, grid)
                dy = np.random.randint(0, grid)
                while not valid_position(size, x + dx, y + dy):
                    dx = np.random.randint(0, grid)
                    dy = np.random.randint(0, grid)
                weight = np.random.random() * 2 - 1
                sp_conv[int(x + dx)][int(y + dy)] = weight

    sp_conv = cv2.filter2D(sp_conv, -1, gabor_kern)
    return normalize(sp_conv)


def gaborN_uni(size, grid, ksize, sigma, lambd, xy_ratio, thetas):
    """
    Gabor noise
        - controlled, uniformly distributed kernels
    :param size:
    :param grid: ideally is odd and a factor of size
    :param ksize:
    :param sigma:
    :param lambd:
    :param xy_ratio:
    :param thetas: orientation of kernels, has length (size / grid)^2
    :return:
    """
    sp_conv = np.zeros([size, size])
    temp_conv = np.zeros([size, size])
    dim = int(size / 2 // grid)

    for i in range(-dim, dim + 1):
        for j in range(-dim, dim + 1):
            x = i * grid + size // 2
            y = j * grid + size // 2
            temp_conv[x][y] = 1
            theta = thetas[(i + dim) * dim * 2 + (j + dim)]
            # Gabor kernel
            gabor_kern = cv2.getGaborKernel((ksize, ksize), sigma, theta, lambd, xy_ratio,
                                            0, ktype=cv2.CV_32F)
            sp_conv += cv2.filter2D(temp_conv, -1, gabor_kern)
            temp_conv[x][y] = 0

    return normalize(sp_conv)


def perlin(size, period, octave, freq_sine, lacunarity=2):
    """
    Perlin noise
        - with sine color map
    :param size:
    :param period:
    :param octave:
    :param freq_sine:
    :param lacunarity:
    :return:
    """
    # Perlin noise
    noise = np.empty((size, size), dtype=np.float32)
    for x in range(size):
        for y in range(size):
            noise[x][y] = pnoise2(x / period, y / period, octaves=octave,
                                  lacunarity=lacunarity)
    # Sine function color map
    noise = normalize(noise)
    noise = np.sin(noise * freq_sine * np.pi)
    return normalize(noise)


def colorize(img, color=[1, 1, 1]):
    """
    Color image
    :param img: has dimension 2 or 3, pixel range [0, 1]
    :param color: is [a, b, c] where a, b, c are from {-1, 0, 1}
    :return:
    """
    if img.ndim == 2:  # expand to include color channels
        img = np.expand_dims(img, 2)
    return (img - 0.5) * color + 0.5  # output pixel range [0, 1]


def plot_colored(img, title):
    """
    Plot images in different colors
    :param img:
    :param title:
    :return:
    """
    fig = plt.figure(figsize=(20, 6.5))
    plt.subplots_adjust(wspace=0.05)
    plt.title(title, size=20)
    plt.axis('off')

    ax = fig.add_subplot(1, 4, 1)
    ax.set_title('Black & White', size=16)
    ax.axis('off')
    plt.imshow(colorize(img, color=[1, 1, 1]))

    ax = fig.add_subplot(1, 4, 2)
    ax.set_title('Red & Cyan', size=16)
    ax.axis('off')
    plt.imshow(colorize(img, color=[1, -1, -1]))

    ax = fig.add_subplot(1, 4, 3)
    ax.set_title('Green & Magenta', size=16)
    ax.axis('off')
    plt.imshow(colorize(img, color=[-1, 1, -1]))

    ax = fig.add_subplot(1, 4, 4)
    ax.set_title('Blue & Yellow', size=16)
    ax.axis('off')
    plt.imshow(colorize(img, color=[-1, -1, 1]))


def plot_spectral(img, title):
    """
    Plot power spectrum of image
    :param img:
    :param title:
    :return:
    """
    fig = plt.figure(figsize=(20, 6.5))
    plt.subplots_adjust(wspace=0.05)
    plt.title(title, size=20)
    plt.axis('off')

    # Original image (spatial)
    ax = fig.add_subplot(1, 4, 1)
    ax.set_title('Spatial Domain', size=16)
    ax.axis('off')
    plt.imshow(img, cmap=plt.cm.gray)

    # Original image (spectral)
    ax = fig.add_subplot(1, 4, 2)
    ax.set_title('Power Spectrum', size=16)
    ax.axis('off')
    plt.imshow(100 * abs(np.fft.fftshift(np.fft.fft2(img))), cmap=plt.cm.gray)

    # Original image (spectral variance)
    ax = fig.add_subplot(1, 4, 3)
    ax.set_title('Spectral Variance', size=16)
    ax.axis('off')
    mean = np.mean(img)
    spec_var = np.fft.fft2(np.square(img - mean))
    plt.imshow(100 * abs(np.fft.fftshift(spec_var)), cmap=plt.cm.gray)

    # Normalized variance
    ax = fig.add_subplot(1, 4, 4)
    ax.set_title('Variance Normalized Image', size=16)
    ax.axis('off')
    img = normalize_var(img)
    plt.imshow(img, cmap=plt.cm.gray)
