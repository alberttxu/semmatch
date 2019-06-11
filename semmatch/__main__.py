def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="template matching tool for SerialEM")
    # required
    parser.add_argument("--gui", help="interactive gui mode", action="store_true")
    parser.add_argument("--navfile", help="SerialEM nav file", required=True)
    parser.add_argument("--image", help="binning 1 jpg", required=True)
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
    parser.add_argument("--template", help="", required="--gui" not in sys.argv)
    parser.add_argument("--threshold", help="", required="--gui" not in sys.argv)
    parser.add_argument("--groupOption", help="", required="--gui" not in sys.argv)

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

    if args.gui == True:
        import semmatch.gui

        semmatch.gui.main(
            args.navfile,
            args.image,
            args.mapLabel,
            args.newLabel,
            args.output,
            args.template,
            args.threshold,
            args.groupOption,
            args.groupRadius,
            args.pixelSize,
            args.acquire,
        )

    else:
        from semmatch.image import ImageHandler
        from semmatch.templateMatch import templateMatch
        from semmatch.autodoc import coordsToNavPoints, sectionToDict

        image = ImageHandler(args.image)
        template = ImageHandler(args.template)
        pts = list(
            map(
                image.toOrigCoord,
                templateMatch(
                    image.getData(),
                    template.getData(),
                    threshold=float(args.threshold),
                    blurImage=True,
                    blurTemplate=True,
                ),
            )
        )

        with open(args.navfile) as f:
            navdata = [line.strip() for line in f.readlines()]
        if args.groupRadius == None:
            groupRadius = 0
        else:
            groupRadius = int(args.groupRadius)
        navPts = coordsToNavPoints(
            pts,
            navdata,
            args.mapLabel,
            int(args.newLabel),
            acquire=args.acquire,
            groupOpt=int(args.groupOption),
        )[0]

        with open(args.output, "w") as f:
            f.write("AdocVersion = 2.00\n\n" + "".join(str(pt) for pt in navPts))


if __name__ == "__main__":
    main()
