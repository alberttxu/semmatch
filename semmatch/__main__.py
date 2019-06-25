def main():
    import argparse
    import sys
    import imageio
    from scipy.misc import imresize
    from semmatch.image import ImageHandler
    from semmatch.core import Pt, NavOptions, templateMatch
    from semmatch.autodoc import ptsToNavPts, createAutodoc, openNavfile

    parser = argparse.ArgumentParser(description="template matching tool for SerialEM")
    # required
    parser.add_argument("--navfile", help="SerialEM nav file", required=True)
    parser.add_argument("--image", help="jpg", required=True)
    parser.add_argument("--mapLabel", help="label id", required=True)
    parser.add_argument(
        "--newLabel", help="starting label of added points", type=int, required=True
    )
    parser.add_argument("-o", "--output", help="output nav file", required=True)

    # conditionally required
    parser.add_argument(
        "--template",
        help="template image to use; required in non-gui mode",
        required="--gui" not in sys.argv,
    )

    # optional
    parser.add_argument("--gui", help="interactive gui mode", action="store_true")
    parser.add_argument(
        "--groupOption",
        help="grouping option for points; 0 = no groups; 1 = groups within mesh (requires --groupRadius and --pixelSize; 2 = entire mesh as one group; 3 = k-means clustering",
        type=int,
        default=0,
    )
    parser.add_argument(
        "--threshold", help="threshold value for zncc", type=float, default=0.8
    )
    parser.add_argument("--bin", help="external binning factor", type=int, default=1)
    parser.add_argument("-A", "--acquire", help="", action="store_true")
    parser.add_argument(
        "--groupRadius", help="groupRadius in µm", type=float, default=7.0
    )
    parser.add_argument("--pixelSize", help="pixelSize in nm", type=float, default=5.0)
    parser.add_argument(
        "--numGroups",
        help="number of groups for k-means groupOption",
        type=int,
        default=10,
    )
    parser.add_argument("--noBlurImage", help="", action="store_true")
    parser.add_argument("--noBlurTemplate", help="", action="store_true")

    args = parser.parse_args()

    navfile = args.navfile
    image = args.image
    binning = args.bin
    mapLabel = args.mapLabel
    newLabel = args.newLabel
    output = args.output
    template = args.template
    threshold = args.threshold
    groupOption = args.groupOption
    groupRadius = args.groupRadius
    pixelSize = args.pixelSize
    numGroups = args.numGroups
    acquire = int(args.acquire)
    blurImage = not args.noBlurImage
    blurTemplate = not args.noBlurTemplate
    options = NavOptions(groupOption, groupRadius, pixelSize, numGroups, acquire)

    # unnecessary options messages
    if groupOption != 1:
        if groupRadius is not None:
            print(
                "groupRadius will be ignored because groupOption is not 1 (groups within mesh)"
            )
        if pixelSize is not None:
            print(
                "pixelSize will be ignored because groupOption is not 1 (groups within mesh)"
            )
    if groupOption != 3 and numGroups is not None:
        print(
            "numGroups will be ignored because groupOption is not 3 (k-means clustering)"
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

    # clear output file to prevent merging previous points
    createAutodoc(output, [])

    # read and downsize images if necessary
    image = imageio.imread(image)
    if template is not None:
        template = imageio.imread(template)
    MAX_DIM_BEFORE_DOWNSCALE = 2000
    max_dimension = max(image.shape)
    downscale = 1
    if max_dimension > MAX_DIM_BEFORE_DOWNSCALE:
        downscale = float(max_dimension / MAX_DIM_BEFORE_DOWNSCALE)
        image = imresize(image, 1 / downscale, interp="lanczos")
        if template is not None:
            template = imresize(template, 1 / (downscale * binning), interp="lanczos")

    if args.gui == True:
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
        pts = templateMatch(
            image, template, threshold, blurImage=blurImage, blurTemplate=blurTemplate
        )
    pts = [
        Pt(int(binning * downscale * x), int(binning * downscale * y)) for x, y in pts
    ]

    if len(pts) == 0:
        print("no matches found; exiting without creating %s" % output)
        exit()

    navPts = ptsToNavPts(pts, nav, mapLabel, newLabel, options)

    createAutodoc(output, navPts)

    print("%s created" % output)


if __name__ == "__main__":
    main()
