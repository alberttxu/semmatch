import numpy as np
import PIL
from scipy.ndimage import gaussian_filter
from semmatch.templateMatch import templateMatch, defocusCorrectedCoords
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


def test_defocusCorrectedCoords1():
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
    assert coords == defocusCorrectedCoords(coords, (0, 0), 0, 1)


def test_defocusCorrectedCoords2():
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
    assert coords == defocusCorrectedCoords(coords, (100, 250), 0, 1)


def test_defocusCorrectedCoords3():
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
    MMM = np.array(PIL.Image.open("MMM.jpg"))
    center = (MMM.shape[0] // 2, MMM.shape[1] // 2)
    correctedCoords = defocusCorrectedCoords(
        coords, center, theta=-4.134216, scale=1.011296
    )
    assert correctedCoords == [
        (2166, 1878),
        (2625, 1383),
        (1698, 1228),
        (2230, 1500),
        (2328, 2093),
        (2864, 1033),
        (2141, 2066),
        (1721, 1039),
        (2812, 1410),
        (2019, 1662),
        (2069, 1285),
        (2599, 1573),
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
