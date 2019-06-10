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
    parser.add_argument(
        "--groupRadius", help="groupRadius in µm", required="--gui" not in sys.argv
    )
    parser.add_argument(
        "--pixelSize", help="pixelSize in nm", required="--gui" not in sys.argv
    )

    # optional
    parser.add_argument("-A", "--acquire", help="", action="store_true")

    args = parser.parse_args()
    print(args)

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
        # import templateMatch et al.
        pass


if __name__ == "__main__":
    main()
