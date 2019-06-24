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
    parser.add_argument("--gui", help="interactive gui mode", action="store_true")
    parser.add_argument("--navfile", help="SerialEM nav file", required=True)
    parser.add_argument("--image", help="jpg", required=True)
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
    parser.add_argument("--bin", help="external binning factor", default=1)
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
    options = NavOptions(groupOption, groupRadius, pixelSize, acquire)

    nav = openNavfile(navfile)
    if mapLabel not in nav:
        raise Exception("could not find map label: %s" % mapLabel)

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
            template = imresize(template, 1 / downscale, interp="lanczos")

    if args.gui == True:
        import semmatch.gui

        pts, options = semmatch.gui.main(image, template, threshold, options)
    else:
        pts = templateMatch(image, template, threshold)
    pts = [
        Pt(int(binning * downscale * x), int(binning * downscale * y)) for x, y in pts
    ]
    navPts = ptsToNavPts(pts, nav, mapLabel, newLabel, options)

    createAutodoc(output, navPts)


if __name__ == "__main__":
    main()
