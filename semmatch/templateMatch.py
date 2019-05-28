import cv2
import math
import numpy as np
import PIL
from scipy.ndimage.filters import gaussian_filter


# for relative distance, square distance is faster to compute
def squareDist(pt1: 'tuple', pt2: 'tuple'):
    return (pt1[0]-pt2[0])**2 + (pt1[1]-pt2[1])**2

# prevent including the same hole multiple times
def pointsExistWithinRadius(center, coords, radius):
    radius_2 = radius ** 2
    if len(coords) == 0:
        return False
    for pt in coords:
        if squareDist(pt, center) < radius_2:
            return True
    return False

# modified from OpenCV docs
# https://docs.opencv.org/3.4/d4/dc6/tutorial_py_template_matching.html
def templateMatch(image, template, threshold=0.8, downSample: int = 1):
    """Return a list of (x,y) pixel coordinates where cross-correlation between
    the image and template surpass the threshold value.

    To prevent double counting, the minimum distance between coordinates is
    constrained to the length of the larger dimension of the template image.

    Following SerialEM conventions, (0,0) is at the bottom-left corner,
    with +x axis to the right and +y axis upwards.

    Images can be downsampled for faster computation and noise reduction.
    """

    image = image[::downSample,::downSample]
    template = template[::downSample,::downSample]

    # flip both arrays upsidedown for coordinate conventions
    image = np.flip(image, 0).copy()
    template = np.flip(template, 0).copy()
    h, w, *_ = template.shape
    xcorrScores = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    loc = zip(*np.where(xcorrScores >= threshold))
    scoresIndex = [(x, y, xcorrScores[y][x]) for y, x in loc]
    scoresIndex.sort(key=lambda a: a[2], reverse=True)

    matches = []
    for x, y, _ in scoresIndex:
        x += w//2
        y += h//2
        if not pointsExistWithinRadius((x,y), matches, radius=max(h,w)):
            matches.append((x,y))
    # multiply back to get correct coordinates
    matches = [(downSample*x, downSample*y) for x,y in matches]
    return matches

def rotate(coords, theta: "deg"):
    '''positive angles ccw'''
    theta = math.radians(theta)
    result = []
    for x,y in coords:
        result.append((x * math.cos(theta) - y * math.sin(theta),
                       x * math.sin(theta) + y * math.cos(theta)))
    return result

def defocusCorrectedCoords(coords, pivot: "(x,y)", theta: "deg", scale):
    """Rotate and scale coordinates to compensate for View mode defocus."""
    coords = [(x - pivot[0], y - pivot[1]) for x,y in coords]
    coords = rotate(coords, theta)
    coords = [(int(scale * x), int(scale * y)) for x,y in coords]
    coords = [(x + pivot[0], y + pivot[1]) for x,y in coords]
    return coords

