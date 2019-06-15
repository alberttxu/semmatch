def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="template matching tool for SerialEM")
    # required
    parser.add_argument("--gui", help="interactive gui mode", action="store_true")
    parser.add_argument("--navfile", help="SerialEM nav file", required=True)
    parser.add_argument("--image", help="jpg", required=True)
    parser.add_argument("--bin", help="external binning factor", required=True)
    parser.add_argument("--mapLabel", help="label id", required=True)
    parser.add_argument(
        "--newLabel", help="starting label of added points", required=True
    )
    parser.add_argument(
        "-o",
        "--output",
        help="output nav file",
        default="semmatchNav.nav",
        required=True,
    )

    # conditionally required
    # template, threshold, and groupOption/groupRadius/pixelSize are
    #   required in non-gui mode, but optional in gui mode
    parser.add_argument(
        "--template",
        help="template image to use; required in non-gui mode",
        required="--gui" not in sys.argv,
    )
    parser.add_argument(
        "--threshold", help="threshold value for zncc", required="--gui" not in sys.argv
    )
    parser.add_argument(
        "--groupOption",
        help="grouping option for points; 0 = no groups; 1 = groups within mesh (requires --groupRadius and --pixelSize; 2 = entire mesh as one group",
        required="--gui" not in sys.argv,
    )

    # optional
    parser.add_argument("-A", "--acquire", help="", action="store_true")
    parser.add_argument("--groupRadius", help="groupRadius in µm")
    parser.add_argument("--pixelSize", help="pixelSize in nm")

    args = parser.parse_args()

    if args.groupOption != "1" and (
        args.groupRadius is not None or args.pixelSize is not None
    ):
        parser.error(
            "groupRadius and pixelSize only valid for groupOption 1: groups within mesh"
        )
    if args.groupOption == "1" and (args.groupRadius is None or args.pixelSize is None):
        parser.error("groupOption 1 requires groupRadius and pixelSize")

    navfile = args.navfile
    image = args.image
    binning = int(args.bin)
    mapLabel = args.mapLabel
    newLabel = int(args.newLabel)
    output = args.output
    template = args.template
    if args.threshold:
        threshold = float(args.threshold)
    else:
        threshold = None
    if args.groupOption:
        groupOption = int(args.groupOption)
        if groupOption == 1:
            groupRadius = float(args.groupRadius)
            pixelSize = float(args.pixelSize)
        else:
            groupRadius = 0
            pixelSize = 1
    else:
        groupOption = None
        groupRadius = None
        pixelSize = None
    acquire = int(args.acquire)

    if args.gui == True:
        import semmatch.gui

        semmatch.gui.main(
            navfile,
            image,
            mapLabel,
            newLabel,
            output,
            template,
            threshold,
            groupOption,
            groupRadius,
            pixelSize,
            acquire,
            binning,
        )

    else:
        import imageio
        from semmatch.image import ImageHandler
        from semmatch.templateMatch import templateMatch
        from semmatch.autodoc import coordsToNavPoints, sectionToDict

        image = imageio.imread(image)
        template = imageio.imread(template)
        MAX_DIM_BEFORE_DOWNSCALE = 2000
        max_dimension = max(image.shape)
        downscale = 1
        if max_dimension > MAX_DIM_BEFORE_DOWNSCALE:
            downscale = int(max_dimension / MAX_DIM_BEFORE_DOWNSCALE)
        pts = templateMatch(
            image,
            template,
            threshold=threshold,
            downSample=downscale,
        )

        pts = [(binning * x, binning * y) for x,y in pts]

        with open(navfile) as f:
            navdata = [line.strip() for line in f.readlines()]
        navPts = coordsToNavPoints(
            pts,
            navdata,
            mapLabel,
            newLabel,
            acquire=acquire,
            groupOpt=groupOption,
            groupRadiusPix=groupRadius * 1000 / pixelSize,
        )[0]

        with open(output, "w") as f:
            f.write("AdocVersion = 2.00\n\n" + "".join(str(pt) for pt in navPts))


if __name__ == "__main__":
    main()
