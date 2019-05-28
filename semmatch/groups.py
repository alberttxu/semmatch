from semmatch.templateMatch import squareDist

def centroid(pts: 'ndarray'):
    length = pts.shape[0]
    sum_x = np.sum(pts[:, 0])
    sum_y = np.sum(pts[:, 1])
    return sum_x/length, sum_y/length

def closestPtToCentroid(pts):
    """Returns the coordinate closest to the center of mass"""
    center = centroid(np.array(pts))
    closestPoint = pts[0]
    msd = squareDist(pts[0], center) # min square distance
    for pt in pts:
        dist_2 = squareDist(pt, center)
        if dist_2 < msd:
            closestPoint = pt
            msd = dist_2
    return closestPoint

def greedyPathThroughPts(coords):
    """Returns a list with the first item being the left most coordinate,
       and successive items being the minimum distance from the previous item.
    """
    coords = [tuple(pt) for pt in coords]
    leftMostPt = sorted(coords, key=lambda x: x[0])[0]
    unvisitedPts = set(coords)
    unvisitedPts.remove(leftMostPt)

    result = [leftMostPt]
    while unvisitedPts:
        closestPtToPrev = unvisitedPts.pop()
        unvisitedPts.add(closestPtToPrev)
        minDist = squareDist(closestPtToPrev, result[-1])
        for pt in unvisitedPts:
            distFromPrev = squareDist(pt, result[-1])
            if distFromPrev < minDist:
                minDist = distFromPrev
                closestPtToPrev = pt
        result.append(closestPtToPrev)
        unvisitedPts.remove(closestPtToPrev)
    return result

def makeGroupsOfPoints(pts, max_radius):
    max_radius_2 = max_radius ** 2
    groups = []
    greedyPath = greedyPathThroughPts(pts)[::-1]
    group = [greedyPath.pop()]
    while greedyPath:
        pt = greedyPath.pop()
        if squareDist(pt, group[0]) < max_radius_2:
            group.append(pt)
        else:
            groups.append(group)
            group = [pt]
    if group:
        groups.append(group)

    for i in range(len(groups)):
        groupLeader = closestPtToCentroid(groups[i])
        groups[i] = [groupLeader] + [pt for pt in groups[i] if pt != groupLeader]
    return groups
