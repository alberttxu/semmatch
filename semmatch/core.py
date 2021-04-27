from collections import namedtuple
import logging
import math

import cv2
import numpy as np
import PIL
from PIL import Image, ImageFilter
import scipy
from scipy import ndimage
from scipy.ndimage.filters import gaussian_filter, maximum_filter
import skimage.filters
from skimage.morphology import convex_hull_image

# ubiquitous Point type
Pt = namedtuple("Pt", "x y")

# output nav grouping/acquire options
NavOptions = namedtuple(
    "NavOptions", "groupOption groupRadius pixelSize numGroups ptsPerGroup acquire"
)


# for relative distance, square distance is faster to compute
def squareDist(pt1, pt2):
    return (pt1.x - pt2.x) ** 2 + (pt1.y - pt2.y) ** 2


# prevent including the same hole multiple times
def pointsExistWithinRadius(center: "Pt", coords, radius):
    radius_2 = radius ** 2
    if len(coords) == 0:
        return False
    for pt in coords:
        if squareDist(pt, center) < radius_2:
            return True
    return False


# modified from OpenCV docs
# https://docs.opencv.org/3.4/d4/dc6/tutorial_py_template_matching.html
def templateMatch(
    image,
    template,
    threshold,
    downSample: int = 1,
    blurImage=False,
    blurTemplate=False,
    sigma=10,
):
    """Return a list of (x,y) pixel coordinates where cross-correlation between
    the image and template surpass the threshold value.

    To prevent double counting, the minimum distance between coordinates is
    constrained to the length of the larger dimension of the template image.

    Following SerialEM conventions, (0,0) is at the bottom-left corner,
    with +x axis to the right and +y axis upwards.

    Images can be downsampled for faster computation and noise reduction.
    """

    if len(image.shape) == 3:
        image = image[:, :, 0]
    if len(template.shape) == 3:
        template = template[:, :, 0]
    image = image[::downSample, ::downSample]
    template = template[::downSample, ::downSample]
    if blurImage:
        image = gaussian_filter(image, sigma=sigma)
    if blurTemplate:
        template = gaussian_filter(template, sigma=sigma)

    # flip both arrays upsidedown for coordinate conventions
    image = np.flip(image, 0).copy()
    template = np.flip(template, 0).copy()
    h, w, *_ = template.shape
    xcorrScores = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    maxfilter = maximum_filter(
        xcorrScores, size=(template.shape[0] // 2, template.shape[1] // 2)
    )
    loc = zip(*np.where((xcorrScores >= threshold) & (xcorrScores == maxfilter)))

    scoresIndex = [(x, y, xcorrScores[y][x]) for y, x in loc]
    scoresIndex.sort(key=lambda a: a[2], reverse=True)

    matches = []
    for x, y, _ in scoresIndex:
        x += w // 2
        y += h // 2
        if not pointsExistWithinRadius(Pt(x, y), matches, radius=max(h, w)):
            matches.append(Pt(x, y))
    # multiply back to get correct coordinates
    matches = [Pt(downSample * x, downSample * y) for x, y in matches]
    return matches


def imresize(img: "ndarray", factor):
    return np.array(
        PIL.Image.fromarray(img).resize(
            size=(int(img.shape[1] * factor), int(img.shape[0] * factor)),
            resample=PIL.Image.LANCZOS,
        )
    )


# https://pastebin.com/sBsPX4Y7
def anisodiff(
    img, niter=10, kappa=50, gamma=0.1, step=(1.0, 1.0), option=1, ploton=False
):
    """
    Anisotropic diffusion.

    Usage:
    imgout = anisodiff(im, niter, kappa, gamma, option)

    Arguments:
            img    - input image
            niter  - number of iterations
            kappa  - conduction coefficient 20-100 ?
            gamma  - max value of .25 for stability
            step   - tuple, the distance between adjacent pixels in (y,x)
            option - 1 Perona Malik diffusion equation No 1
                     2 Perona Malik diffusion equation No 2
            ploton - if True, the image will be plotted on every iteration

    Returns:
            imgout   - diffused image.

    kappa controls conduction as a function of gradient.  If kappa is low
    small intensity gradients are able to block conduction and hence diffusion
    across step edges.  A large value reduces the influence of intensity
    gradients on conduction.

    gamma controls speed of diffusion (you usually want it at a maximum of
    0.25)

    step is used to scale the gradients in case the spacing between adjacent
    pixels differs in the x and y axes

    Diffusion equation 1 favours high contrast edges over low contrast ones.
    Diffusion equation 2 favours wide regions over smaller ones.

    Reference:
    P. Perona and J. Malik.
    Scale-space and edge detection using ansotropic diffusion.
    IEEE Transactions on Pattern Analysis and Machine Intelligence,
    12(7):629-639, July 1990.

    Original MATLAB code by Peter Kovesi
    School of Computer Science & Software Engineering
    The University of Western Australia
    pk @ csse uwa edu au
    <http://www.csse.uwa.edu.au>

    Translated to Python and optimised by Alistair Muldal
    Department of Pharmacology
    University of Oxford
    <alistair.muldal@pharm.ox.ac.uk>

    June 2000  original version.
    March 2002 corrected diffusion eqn No 2.
    July 2012 translated to Python
    """

    # ...you could always diffuse each color channel independently if you
    # really want
    if img.ndim == 3:
        warnings.warn("Only grayscale images allowed, converting to 2D matrix")
        img = img.mean(2)

    # initialize output array
    img = img.astype("float32")
    imgout = img.copy()

    # initialize some internal variables
    deltaS = np.zeros_like(imgout)
    deltaE = deltaS.copy()
    NS = deltaS.copy()
    EW = deltaS.copy()
    gS = np.ones_like(imgout)
    gE = gS.copy()

    # create the plot figure, if requested
    if ploton:
        import pylab as pl
        from time import sleep

        fig = pl.figure(figsize=(20, 5.5), num="Anisotropic diffusion")
        ax1, ax2 = fig.add_subplot(1, 2, 1), fig.add_subplot(1, 2, 2)

        ax1.imshow(img, interpolation="nearest")
        ih = ax2.imshow(imgout, interpolation="nearest", animated=True)
        ax1.set_title("Original image")
        ax2.set_title("Iteration 0")

        fig.canvas.draw()

    for ii in range(niter):

        # calculate the diffs
        deltaS[:-1, :] = np.diff(imgout, axis=0)
        deltaE[:, :-1] = np.diff(imgout, axis=1)

        # conduction gradients (only need to compute one per dim!)
        if option == 1:
            gS = np.exp(-((deltaS / kappa) ** 2.0)) / step[0]
            gE = np.exp(-((deltaE / kappa) ** 2.0)) / step[1]
        elif option == 2:
            gS = 1.0 / (1.0 + (deltaS / kappa) ** 2.0) / step[0]
            gE = 1.0 / (1.0 + (deltaE / kappa) ** 2.0) / step[1]

        # update matrices
        E = gE * deltaE
        S = gS * deltaS

        # subtract a copy that has been shifted 'North/West' by one
        # pixel. don't as questions. just do it. trust me.
        NS[:] = S
        EW[:] = E
        NS[1:, :] -= S[:-1, :]
        EW[:, 1:] -= E[:, :-1]

        # update the image
        imgout += gamma * (NS + EW)

        if ploton:
            iterstring = "Iteration %i" % (ii + 1)
            ih.set_data(imgout)
            ax2.set_title(iterstring)
            fig.canvas.draw()
            # sleep(0.01)

    return imgout.astype(np.uint8)


def median_filt(img, radius=5):
    return np.array(Image.fromarray(img).filter(ImageFilter.MedianFilter(size=radius)))


def scharr(img):
    return (2000 * skimage.filters.scharr(img)).astype("uint8")


def prefilter_before_hough(img):
    img = anisodiff(img, niter=20)
    img = median_filt(img)
    img = scharr(img)
    return img


def houghCircles(
    img,
    pixelSize,
    param1=50,
    param2=60,
    minDistNm=600,
    minRadiusNm=600,
    maxRadiusNm=1300,
):
    minRadius = int(minRadiusNm / pixelSize)
    maxRadius = int(maxRadiusNm / pixelSize)
    minDist = int(minDistNm / pixelSize)

    img = prefilter_before_hough(img)

    circles = cv2.HoughCircles(
        img,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=minDist,
        param1=param1,
        param2=param2,
        minRadius=minRadius,
        maxRadius=maxRadius,
    )
    try:
        circles = np.uint16(np.around(circles))
    except Exception as e:
        logging.error("general exception in finding circles")
        logging.error(e)
        circles = None

    if circles is not None:
        pts = [(x, img.shape[0] - y) for x, y in circles[0][:, :2]]
    else:
        pts = []

    return pts


def to_binary(img, lower, upper):
    return ((lower < img) & (img < upper)).astype(np.uint8) * 255


def find_segment_centers(labelled_img, num_features, maxPts):
    results = []
    segments = []
    for label in range(1, num_features + 1):
        segment = labelled_img == label
        area = np.sum(segment)
        segments.append((label, segment, area))
    segments = sorted(segments, key=lambda x: x[2])[::-1][:maxPts]
    for label, segment, _ in segments:
        center = scipy.ndimage.measurements.center_of_mass(segment)
        center = (int(center[0]), int(center[1]))
        results.append(center)
    return results


def find_lacey_holes(img, maxPts, theshold_low, threshold_high):
    binary_img = to_binary(
        anisodiff(img, niter=30, kappa=20), theshold_low, threshold_high
    )
    img_erosion = cv2.erode(binary_img, np.ones((5, 5), np.uint8), iterations=1)
    labelled_img, num_features = scipy.ndimage.measurements.label(img_erosion)
    return find_segment_centers(labelled_img, num_features, maxPts)


def laceySearch(img, maxPts, theshold_low, threshold_high):
    pts = find_lacey_holes(img, maxPts, theshold_low, threshold_high)
    pts_sem = [Pt(x, img.shape[0] - y) for y, x in pts]
    return pts_sem


def is_good_mesh(
    loc,
    dilated_img,
    min_border_pixels,
    min_height_pixels,
    min_width_pixels,
    min_area_ratio=0.9,
):
    # check if too close to border
    if (
        loc[0].start < min_border_pixels
        or loc[1].start < min_border_pixels
        or dilated_img.shape[0] - loc[0].stop < min_border_pixels
        or dilated_img.shape[1] - loc[1].stop < min_border_pixels
    ):
        return False

    # check dimension ratio
    height = loc[0].stop - loc[0].start
    width = loc[1].stop - loc[1].start
    if height < min_height_pixels and width < min_width_pixels:
        return False
    if max(height, width) > 1.5 * min(height, width):
        return False

    # check for occlusions by computing area ratio between image and convex hull
    mesh = dilated_img[loc]
    convex_hull = convex_hull_image(mesh)
    if np.sum(mesh.astype(bool)) / np.sum(convex_hull) < min_area_ratio:
        return False

    return True


"""
min_border, min_heigth, min_width: in microns
min_area_ratio: ratio of area between segmented image and convex hull
pixelsize: in nm
"""
def findMeshes(
    img,
    pixelsize,
    maxPts,
    theshold_low,
    threshold_high,
    min_border=400,
    min_height=45,
    min_width=45,
    min_area_ratio=0.92,
):
    # binarize image
    binary_img = to_binary(img, theshold_low, threshold_high)
    # erode image
    eroded_img = cv2.erode(binary_img, np.ones((3, 3), np.uint8), iterations=1)
    # dilate image
    dilated_img = cv2.dilate(eroded_img, np.ones((5, 5), np.uint8), iterations=3)
    # get mesh labels
    labelled_img, num_meshes = ndimage.label(dilated_img)
    locs = ndimage.find_objects(labelled_img)
    # filter out bad meshes
    good_labels = []
    pixelsize_um = pixelsize / 1000
    min_border_pixels = min_border / pixelsize_um
    min_height_pixels = min_height / pixelsize_um
    min_width_pixels = min_width / pixelsize_um
    print(min_border_pixels, min_width_pixels)
    for label, loc in zip(range(1, num_meshes + 1), locs):
        if is_good_mesh(
            loc,
            dilated_img,
            min_border_pixels,
            min_height_pixels,
            min_width_pixels,
            min_area_ratio,
        ):
            good_labels.append(label)
    # return centers of meshes (int)
    centers = ndimage.center_of_mass(dilated_img, labelled_img, good_labels)
    centers = [(int(x[0]), int(x[1])) for x in centers]
    return centers


def meshSearch(img, pixelsize, maxPts, theshold_low, threshold_high, minBorder, minSize):
    pts = findMeshes(img, pixelsize, maxPts, theshold_low, threshold_high, minBorder, minSize, minSize)
    pts_sem = [Pt(x, img.shape[0] - y) for y, x in pts]
    return pts_sem