from semmatch.groups import greedyPathThroughPts, makeGroupsOfPoints

class NavFilePoint:

    def __init__(self, label: str, regis: int, ptsX: int, ptsY: int,
            zHeight: float, drawnID: int, numPts: int = 1, itemType: int = 0,
            color: int = 0, groupID: int = 0, acquire: int = 0, **kwargs):
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
            if key == '_label': continue
            if key == 'CoordsInMap':
                val = ' '.join(str(x) for x in val)
            result.append(f"{key} = {val}")
        result.append('\n')
        return '\n'.join(result)


def isValidAutodoc(navfile):
    try:
        with open(navfile) as f:
            for line in f:
                if line.strip():
                    if line.split()[0] == 'AdocVersion':
                        return True
                    else:
                        print("error: could not find AdocVersion")
                        return False
    except:
        print("invalid autodoc")
        return False

def isValidLabel(data: 'list', label: str):
    try:
        mapSectionIndex = data.index(f"[Item = {label}]")
    except:
        print("unable to write new autodoc file: label %s not found" % label)
        return False
    return True

def sectionToDict(data: 'list', label: str):
    start = data.index(f"[Item = {label}]") + 1
    try:
        section = data[start : data.index('', start)]
    except ValueError: # end of file reached
        section = data[start:]

    result = {}
    for line in section:
        key, val = [s.strip() for s in line.split('=')]
        if key != 'Note':
            val = val.split()
        result[key] = val
    return result

def coordsToNavPoints(coords, mapSection: 'Dict', startLabel: int, acquire,
                      groupOpt: int, groupRadiusPix):
    regis = int(mapSection['Regis'][0])
    drawnID = int(mapSection['MapID'][0])
    zHeight = float(mapSection['StageXYZ'][2])
    navPoints = []
    label = startLabel

    if groupOpt == 0: # no groups
        for pt in greedyPathThroughPts(coords):
            navPoints.append(NavFilePoint(label, regis, *pt, zHeight, drawnID,
                                          acquire=acquire))
            label += 1
    elif groupOpt == 1: # groups withing mesh
        for group in makeGroupsOfPoints(coords, groupRadiusPix):
            subLabel = 1
            groupID = id(group)
            for pt in group:
                navPoints.append(NavFilePoint(f"{label}-{subLabel}", regis,
                                             *pt, zHeight, drawnID,
                                             groupID=groupID, acquire=acquire))
                subLabel += 1
            label += 1
    elif groupOpt == 2: # entire mesh as group
        subLabel = 1
        for pt in greedyPathThroughPts(coords):
            navPoints.append(NavFilePoint(f"{label}-{subLabel}", regis, *pt,
                                          zHeight, drawnID, acquire=acquire))
            subLabel += 1
        label += 1

    numGroups = label - startLabel
    return navPoints, numGroups

