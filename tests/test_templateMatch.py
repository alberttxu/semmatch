import numpy as np
import PIL
from scipy.ndimage import gaussian_filter
from semmatch.core import templateMatch, Pt, NavOptions
from semmatch.autodoc import ptsToNavPts, openNavfile


def test_templateMatch():
    MMM = np.array(PIL.Image.open("MMM.jpg"))
    MMM = gaussian_filter(MMM, sigma=1)

    template = np.array(PIL.Image.open("T.jpg"))
    template = gaussian_filter(template, sigma=1)

    coords = templateMatch(MMM, template, threshold=0.8)
    assert coords == [
        (2149, 1904),
        (2637, 1448),
        (1732, 1229),
        (2239, 1535),
        (2293, 2128),
        (2897, 1120),
        (2111, 2088),
        (1769, 1044),
        (2819, 1488),
        (2019, 1680),
        (2095, 1311),
        (2598, 1633),
    ]


def test_writeToNavFile():
    coords = [
        (2149, 1904),
        (2637, 1448),
        (1732, 1229),
        (2239, 1535),
        (2293, 2128),
        (2897, 1120),
        (2111, 2088),
        (1769, 1044),
        (2819, 1488),
        (2019, 1680),
        (2095, 1311),
        (2598, 1633),
    ]
    coords = [Pt(*coord) for coord in coords]
    mapID = "30-A"
    nav = openNavfile("nav.nav")
    options = NavOptions(groupOption=0, groupRadius=123, pixelSize=1, numGroups=1, acquire=1)
    navPts = ptsToNavPts(coords, nav, mapID, startLabel=9000, options=options)
    newNavData = "AdocVersion = 2.00\n\n" + "".join(str(pt) for pt in navPts)
    with open("newNav.nav", "w") as f:
        f.write(newNavData)

    with open("newNav_validate.nav") as f:
        validationData = f.read()

    assert validationData == newNavData
