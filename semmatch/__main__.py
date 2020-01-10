def main():
    import argparse
    import sys

    import imageio

    from semmatch.core import (
        Pt,
        NavOptions,
        templateMatch,
        imresize,
        houghCircles,
        laceySearch,
    )
    from semmatch.autodoc import ptsToNavPts, createAutodoc, openNavfile
    from semmatch.groups import getRandPts

    parser = argparse.ArgumentParser(description="template matching tool for SerialEM")
    # required
    parser.add_argument("--navfile", help="SerialEM nav file", required=True)
    parser.add_argument("--image", help="jpg", required=True)
    parser.add_argument("--mapLabel", help="label id", required=True)
    parser.add_argument(
        "--newLabel", help="starting label of added points", type=int, required=True
    )
    parser.add_argument("-o", "--output", help="output nav file", required=True)

    # optional
    parser.add_argument("--gui", help="interactive gui mode", action="store_true")
    parser.add_argument(
        "--template", help="template image to use; required in non-gui mode"
    )
    parser.add_argument(
        "--houghCircles", help="automatic detection for holey grid", action="store_true"
    )
    parser.add_argument(
        "--param2", help="threshold for houghCircles", type=int, default=60
    )
    parser.add_argument("--pixelSize", help="pixelSize in nm", type=float, required=True)
    parser.add_argument(
        "--laceySearch", help="automatic detection for lacey grid", action="store_true"
    )
    parser.add_argument(
        "--laceyThreshLow",
        help="lower threshold for laceySearch",
        type=int,
        default=195,
    )
    parser.add_argument(
        "--laceyThreshHigh",
        help="upper threshold for laceySearch",
        type=int,
        default=245,
    )
    parser.add_argument(
        "--maxPts",
        help="limit number of pts found via houghCircles or laceySearch",
        type=int,
    )
    parser.add_argument(
        "--groupOption",
        help="grouping option for points;"
        + "0 = no groups; "
        + "1 = groups based on radius (requires --groupRadius and --pixelSize);"
        + "2 = all points as one group;"
        + "3 = specify number of groups;"
        + "4 = specify number of points per group",
        type=int,
        default=0,
    )
    parser.add_argument(
        "--threshold", help="threshold value for zncc", type=float, default=0.8
    )
    parser.add_argument(
        "--reduction", help="external reduction factor", type=float, default=1.0
    )
    parser.add_argument(
        "--acquire", help="mark points with acquire flag", type=int, default=1
    )
    parser.add_argument(
        "--groupRadius", help="groupRadius in µm", type=float, default=7.0
    )
    parser.add_argument(
        "--numGroups",
        help="number of groups for k-means groupOption",
        type=int,
        default=10,
    )
    parser.add_argument(
        "--ptsPerGroup", help="specify number of points per group", type=int, default=8
    )
    parser.add_argument("--noBlurImage", help="", action="store_true")
    parser.add_argument("--noBlurTemplate", help="", action="store_true")

    args = parser.parse_args()

    navfile = args.navfile
    image = args.image
    reduction = args.reduction
    mapLabel = args.mapLabel
    newLabel = args.newLabel
    output = args.output
    template = args.template
    threshold = args.threshold
    groupOption = args.groupOption
    groupRadius = args.groupRadius
    pixelSize = args.pixelSize
    numGroups = args.numGroups
    ptsPerGroup = args.ptsPerGroup
    acquire = args.acquire
    blurImage = not args.noBlurImage
    blurTemplate = not args.noBlurTemplate
    options = NavOptions(
        groupOption, groupRadius, pixelSize, numGroups, ptsPerGroup, acquire
    )
    param2 = args.param2
    laceyThreshLow = args.laceyThreshLow
    laceyThreshHigh = args.laceyThreshHigh
    maxPts = args.maxPts

    # clear output file to prevent merging previous points
    createAutodoc(output, [])

    # unnecessary options messages
    if groupOption != 1:
        if groupRadius is not None:
            print(
                "groupRadius will be ignored because groupOption is not 1 (groups by radius)"
            )
    if groupOption != 3 and numGroups is not None:
        print(
            "numGroups will be ignored because groupOption is not 3 (specify number of groups)"
        )
    if groupOption != 4 and ptsPerGroup is not None:
        print(
            "ptsPerGroup will be ignored because groupOption is not 4 (specify number of points per group)"
        )

    nav = openNavfile(navfile)
    if mapLabel not in nav:
        print("could not find map label: %s; aborting" % mapLabel)
        exit()
    elif not (
        "Regis" in nav[mapLabel]
        and "MapID" in nav[mapLabel]
        and "StageXYZ" in nav[mapLabel]
    ):
        print(
            "either Regis, MapID, and/or StageXYZ missing in section labeled %s; aborting"
            % mapLabel
        )
        exit()

    # read and downsize images if necessary
    image = imageio.imread(image)
    if template is not None:
        try:
            template = imageio.imread(template)
            template = imresize(template, 1 / (reduction))
        except Exception as e:
            print(e)
            print(
                "error reading in template %s; continuing without template" % template
            )
            template = None

    if args.houghCircles == True:
        print("using hough circles")
        pts = houghCircles(image, pixelSize, param2=param2)
        if maxPts is not None:
            pts = getRandPts(pts, maxPts)
    elif args.laceySearch == True:
        if maxPts == None:
            maxPts = 999
        pts = laceySearch(image, maxPts, laceyThreshLow, laceyThreshHigh)
    elif args.gui == True:
        print("using template matching gui")
        import semmatch.gui

        pts, options = semmatch.gui.main(
            image,
            template,
            threshold,
            options,
            blurImage=blurImage,
            blurTemplate=blurTemplate,
        )
        if options.groupRadius is None:
            print("invalid group radius; aborting")
            exit()
        if options.pixelSize is None:
            print("invalid pixel size; aborting")
            exit()
    else:
        print("using template matching non gui")
        if template is None:
            print("non-gui option must specify template")
            exit()
        pts = templateMatch(
            image, template, threshold, blurImage=blurImage, blurTemplate=blurTemplate
        )

    # compensate round off error from reduction
    pts = [Pt(x + 2, y) for x, y in pts]
    pts = [Pt(int(reduction * x), int(reduction * y)) for x, y in pts]

    if len(pts) == 0:
        print("no matches found; exiting without creating %s" % output)
        exit()
    navPts = ptsToNavPts(pts, nav, mapLabel, newLabel, options)
    createAutodoc(output, navPts)
    print("%s created" % output)


if __name__ == "__main__":
    main()
