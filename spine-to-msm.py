# spine-to-msm.py
import argparse
from pathlib import Path


def main():
    p = argparse.ArgumentParser(
        prog="spine-to-msm",
        description="Convert skeleton to msm yay",
    )
    p.add_argument("spine_json", type=Path, help="Spine skeleton json")
    p.add_argument("spine_atlas", type=Path, help="Spine atlas")
    p.add_argument("-o", "--out-bin", type=Path, required=True, help="Destination .bin")
    p.add_argument("--out-xml", type=Path, required=True, help="Destination atlas XML")
    p.add_argument(
        "--anim",
        action="append",
        default=None,
        help="Only export this animation? default: all",
    )
    p.add_argument(
        "--fps", type=float, default=30.0, help="Bake sample rate (default 30)"
    )
    p.add_argument("--no-y-flip", action="store_true", help="Skip y-axis flip")
    p.add_argument("--hires", action="store_true", help='Mark hires="true"')
    p.add_argument(
        "--scale", type=float, default=0.17, help="Root scale (default 0.17)"
    )
    p.add_argument(
        "--target-height", type=float, default=200.0, help="Monster height in canvas px"
    )
    args = p.parse_args()

    from converter import spine_to_msm

    spine_to_msm(
        args.spine_json,
        args.spine_atlas,
        args.out_bin,
        args.out_xml,
        anim_names=args.anim,
        fps=args.fps,
        y_flip=not args.no_y_flip,
        hires=args.hires,
        scale=args.scale,
        target_height=args.target_height,
    )
    print(f"Wrote {args.out_bin}")
    print(f"Wrote {args.out_xml}")


if __name__ == "__main__":
    main()
