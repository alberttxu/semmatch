import random
from semmatch.groups import greedyPathThroughPts, makeGroupsOfPoints


def openNavfile(navfile) -> dict:
    nav = {}
    with open(navfile) as f:
        data = f.read()
    sections = data.split("\n\n")
    if "AdocVersion" not in sections[0]:
        raise Exception("could not find AdocVersion")
    sections = [section.split("\n") for section in sections[1:]]
    for section in sections:
        item = section[0][1:-1].split("=")[1].strip()
        sectionData = {}
        for line in section[1:]:
            if "=" in line:
                key, val = line.split("=")
                key = key.strip()
                val = val.strip()
                sectionData[key] = val
        nav[item] = sectionData
    return nav


def isValidAutodoc(navfile):
    try:
        with open(navfile) as f:
            for line in f:
                if line.strip():
                    if line.split()[0] == "AdocVersion":
                        return True
                    else:
                        print("error: could not find AdocVersion")
                        return False
    except:
        print("invalid autodoc")
        return False


def isValidLabel(data: "list", label: str):
    try:
        mapSectionIndex = data.index(f"[Item = {label}]")
    except:
        print("unable to write new autodoc file: label %s not found" % label)
        return False
    return True


class NavFilePoint:
    def __init__(
        self,
        label: str,
        regis: int,
        ptsX: int,
        ptsY: int,
        zHeight: float,
        drawnID: int,
        numPts: int = 1,
        itemType: int = 0,
        color: int = 0,
        groupID: int = 0,
        acquire: int = 0,
        **kwargs,
    ):
        self._label = label
        self.Color = color
        self.NumPts = numPts
        self.Regis = regis
        self.Type = itemType
        self.PtsX = ptsX
        self.PtsY = ptsY
        self.DrawnID = drawnID
        self.GroupID = groupID
        self.Acquire = acquire
        self.CoordsInMap = [ptsX, ptsY, zHeight]
        vars(self).update(kwargs)

    def __str__(self):
        result = [f"[Item = {self._label}]"]
        for key, val in vars(self).items():
            if key == "_label":
                continue
            if key == "CoordsInMap":
                val = " ".join(str(x) for x in val)
            result.append(f"{key} = {val}")
        result.append("\n")
        return "\n".join(result)


def ptsToNavPts(
    coords, nav: dict, mapLabel: str, startLabel: int, options: "NavOptions"
):
    regis = int(nav[mapLabel]["Regis"][0])
    drawnID = int(nav[mapLabel]["MapID"][0])
    zHeight = float(nav[mapLabel]["StageXYZ"].split()[2])
    navPoints = []
    label = startLabel

    if options.groupOption == 0:  # no groups
        for pt in greedyPathThroughPts(coords):
            navPoints.append(
                NavFilePoint(
                    label, regis, *pt, zHeight, drawnID, acquire=options.acquire
                )
            )
            label += 1
    elif options.groupOption == 1:  # groups withing mesh
        groupRadiusPix = options.groupRadius * 1000 / options.pixelSize
        for group in makeGroupsOfPoints(coords, groupRadiusPix):
            subLabel = 1
            groupID = random.randint(10 ** 9, 2 * 10 ** 9)
            for pt in group:
                navPoints.append(
                    NavFilePoint(
                        f"{label}-{subLabel}",
                        regis,
                        *pt,
                        zHeight,
                        drawnID,
                        groupID=groupID,
                        acquire=options.acquire,
                    )
                )
                subLabel += 1
            label += 1
    elif options.groupOption == 2:  # entire mesh as group
        groupID = random.randint(10 ** 9, 2 * 10 ** 9)
        subLabel = 1
        for pt in greedyPathThroughPts(coords):
            navPoints.append(
                NavFilePoint(
                    f"{label}-{subLabel}",
                    regis,
                    *pt,
                    zHeight,
                    drawnID,
                    groupID=groupID,
                    acquire=options.acquire,
                )
            )
            subLabel += 1
        label += 1
    else:
        raise ValueError("groupOption needs to be 0, 1, or 2")
    return navPoints


def createAutodoc(outputfile, navPts):
    with open(outputfile, "w") as f:
        f.write("AdocVersion = 2.00\n\n" + "".join(str(pt) for pt in navPts))
