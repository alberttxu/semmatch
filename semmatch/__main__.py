import argparse

import imageio
import PIL

from semmatch.core import (
    Pt,
    NavOptions,
    templateMatch,
    imresize,
    houghCircles,
    laceySearch,
    meshSearch
)
from semmatch.autodoc import ptsToNavPts, createAutodoc, openNavfile
from semmatch.groups import getRandPts


def parse_commandline():
    parser = argparse.ArgumentParser(description="template matching tool for SerialEM")
    parser.add_argument(
        "--navfile", help="SerialEM Navigator session file", required=True
    )
    parser.add_argument("--mapLabel", help="label of map item", required=True)
    parser.add_argument(
        "--newLabel", help="starting label of added points", type=int, required=True
    )
    parser.add_argument(
        "--acquire",
        help="mark imported points with acquire (A) tag; must be 0 or 1",
        type=int,
        required=True
    )
    parser.add_argument("-o", "--output", help="output nav file", required=True)
    parser.add_argument(
        "--pixelsize", help="pixelsize of input image in nm", type=float, required=True
    )
    parser.add_argument("--image", help="input jpg image")

    subparsers = parser.add_subparsers(dest="command", required=True)
    parser_templateMatch = subparsers.add_parser(
        "templateMatch", help="template matching"
    )
    parser_laceySearch = subparsers.add_parser(
        "laceySearch", help="automatic detection for lacey grid"
    )
    parser_houghCircles = subparsers.add_parser(
        "houghCircles", help="automatically find holes"
    )
    parser_findMeshes = subparsers.add_parser(
        "findMeshes", help="automatically find meshes"
    )

    parser_templateMatch.add_argument(
        "--gui", help="interactive gui mode", action="store_true"
    )
    parser_templateMatch.add_argument(
        "--template", help="template image to use; required in non-gui mode"
    )
    parser_templateMatch.add_argument(
        "--groupOption",
        help="grouping option for points;"
        + "0 = no groups; "
        + "1 = groups based on radius (requires --groupRadius and --pixelsize);"
        + "2 = all points as one group;"
        + "3 = specify number of groups;"
        + "4 = specify number of points per group",
        type=int,
        default=0,
    )
    parser_templateMatch.add_argument(
        "--threshold", help="threshold value for zncc", type=float, default=0.8
    )
    parser_templateMatch.add_argument(
        "--reduction", help="external reduction factor", type=float, default=1.0
    )
    parser_templateMatch.add_argument(
        "--groupRadius", help="groupRadius in µm", type=float, default=7.0
    )
    parser_templateMatch.add_argument(
        "--numGroups",
        help="number of groups for k-means groupOption",
        type=int,
        default=10,
    )
    parser_templateMatch.add_argument(
        "--ptsPerGroup", help="specify number of points per group", type=int, default=8
    )
    parser_templateMatch.add_argument("--blurImage", help="", action="store_true")
    parser_templateMatch.add_argument("--blurTemplate", help="", action="store_true")

    parser_laceySearch.add_argument(
        "--low", help="lower threshold cutoff", type=int, default=195
    )
    parser_laceySearch.add_argument(
        "--high", help="upper threshold cutoff", type=int, default=245
    )
    parser_laceySearch.add_argument("--maxPts", type=int, required=True)

    parser_houghCircles.add_argument("--param2", type=int, default=60)
    parser_houghCircles.add_argument("--maxPts", type=int, required=True)
    parser_houghCircles.add_argument("--reduction", type=float, required=True)

    parser_findMeshes.add_argument('--low', help="low cutoff", type=int, default=25)
    parser_findMeshes.add_argument('--high', help="high cutoff", type=int, default=230)
    parser_findMeshes.add_argument(
        "--minSize",
        help="avoid meshes smaller than this length (um) in either dimension",
        type=float,
        default=60,
    )
    parser_findMeshes.add_argument(
        "--minBorder",
        help="avoid searching near the edge of the montage by this distance (um)",
        type=float,
        default=400,
    )
    parser_findMeshes.add_argument("--maxPts", type=int, required=True)

    args = parser.parse_args()

    if args.acquire not in (0, 1):
        print("--acquire argument must be either 0 or 1")
        exit()

    if args.command in ("findMeshes", "houghCircles", "laceySearch") and args.maxPts < 1:
        print("--maxPts cannot be less than 1")
        exit()

    return args


def main():
    args = parse_commandline()
    print(args)

    # clear output file to prevent merging previous points
    createAutodoc(args.output, [])

    nav = openNavfile(args.navfile)
    if args.mapLabel not in nav:
        print("could not find map label: %s; aborting" % args.mapLabel)
        exit()
    elif not (
        "Regis" in nav[args.mapLabel]
        and "MapID" in nav[args.mapLabel]
        and "StageXYZ" in nav[args.mapLabel]
    ):
        print(
            "either Regis, MapID, and/or StageXYZ missing in section labeled %s; aborting"
            % args.mapLabel
        )
        exit()

    PIL.Image.MAX_IMAGE_PIXELS = None
    image = imageio.imread(args.image)

    if args.command == "templateMatch":
        options = NavOptions(
            args.groupOption,
            args.groupRadius,
            args.pixelsize,
            args.numGroups,
            args.ptsPerGroup,
            int(args.acquire),
        )

        if args.template is not None:
            template = imageio.imread(args.template)
            template = imresize(template, 1 / (args.reduction))
        else:
            template = None

        if args.gui == True:
            print("using template matching gui")
            import semmatch.gui
            pts, options = semmatch.gui.main(
                image,
                template,
                args.threshold,
                options,
                args.blurImage,
                args.blurTemplate,
            )
        else:
            print("using template matching non gui")
            if args.template is None:
                print("non-gui option must specify template")
                exit()
            pts = templateMatch(
                image,
                template,
                args.threshold,
                args.blurImage,
                args.blurTemplate,
            )
        # compensate round off error from reduction
        pts = [Pt(x + 2, y) for x, y in pts]
        pts = [Pt(int(args.reduction * x), int(args.reduction * y)) for x, y in pts]
    else:
        options = NavOptions(
            0,
            None,
            args.pixelsize,
            None,
            None,
            int(args.acquire),
        )

    if args.command == "houghCircles":
        pts = houghCircles(image, args.pixelsize, param2=args.param2)
        pts = [(int(args.reduction * p[0]), int(args.reduction * p[1])) for p in pts]
        pts = getRandPts(pts, args.maxPts)
    elif args.command == "laceySearch":
        pts = laceySearch(image, args.maxPts, args.laceyThreshLow, args.laceyThreshHigh)
    elif args.command == "findMeshes":
        pts = meshSearch(image, args.pixelsize, args.maxPts, args.low, args.high, args.minBorder, args.minSize)

    if len(pts) == 0:
        print("no matches found; exiting without creating %s" % args.output)
        exit()
    navPts = ptsToNavPts(pts, nav, args.mapLabel, args.newLabel, options)
    createAutodoc(args.output, navPts)
    print("%s created" % args.output)