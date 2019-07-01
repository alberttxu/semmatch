from collections import namedtuple
import cv2
import math
import numpy as np
import PIL
from scipy.ndimage.filters import gaussian_filter, maximum_filter

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
