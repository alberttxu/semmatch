import numpy as np
import PIL
from scipy.ndimage import gaussian_filter
from semmatch.templateMatch import templateMatch
from semmatch.autodoc import coordsToNavPoints, sectionToDict


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
    mapID = "30-A"
    with open("nav.nav") as f:
        navfileLines = [line.strip() for line in f.readlines()]
    mapSection = sectionToDict(navfileLines, mapID)
    navPts = coordsToNavPoints(
        coords, mapSection, startLabel=9000, acquire=1, groupOpt=0, groupRadiusPix=123
    )[0]
    newNavData = "AdocVersion = 2.00\n\n" + "".join(str(pt) for pt in navPts)
    with open("newNav.nav", "w") as f:
        f.write(newNavData)

    with open("newNav_validate.nav") as f:
        validationData = f.read()

    assert validationData == newNavData
