from __future__ import annotations
import argparse
import json
from .parsing import parse_maturity_date, load_yield_curve
from .pricer import price_swap, solve_par_rate
from .utils import find_curve_file
from .config import BaseConfig




def main(argv: list[str] | None = None) -> int:
    import sys
    parser = argparse.ArgumentParser(prog="gemini-ird-pricer", description="IR swap pricing CLI")
    parser.add_argument("price", nargs="?", help="Price a swap", default="price")
    parser.add_argument("--notional", required=False, default="1m")
    parser.add_argument("--maturity", required=False, default="5y")
    parser.add_argument("--fixed", required=False, help="Fixed rate in %% (omit to solve par rate)", type=float)
    parser.add_argument("--data-dir", required=False)
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    parser.add_argument("--config", action="store_true", help="Print resolved config as JSON and exit")
    try:
        # Normalize argv and handle help explicitly to avoid SystemExit confusing return codes
        if argv is None:
            argv = sys.argv[1:]
        # If help requested, print and exit 0
        if any(a in ("-h", "--help") for a in argv):
            parser.print_help()
            return 0
        # Workaround: allow negative-looking maturity like "-5y" as value by joining with the flag
        _argv = list(argv)
        for i, tok in enumerate(list(_argv)):
            if tok == "--maturity" and i + 1 < len(_argv):
                _argv[i] = f"--maturity={_argv[i+1]}"
                del _argv[i+1]
                break
        # Be tolerant of unknown positional subcommands (e.g., 'price')
        args, _unknown = parser.parse_known_args(_argv)

        # Handle meta flags
        if args.version:
            from .version import __version__
            print(__version__)
            return 0
        if args.config:
            cfg = BaseConfig.from_env()
            print(json.dumps(cfg.model_dump(), indent=2))
            return 0

        try:
            cfg = BaseConfig.from_env()
            if args.data_dir:
                cfg.DATA_DIR = args.data_dir
                # If user explicitly provided a data dir, require a match and do not fallback
                import glob, os
                matches = glob.glob(os.path.join(cfg.DATA_DIR, cfg.CURVE_GLOB))
                if not matches:
                    raise FileNotFoundError(f"No curve files found in {cfg.DATA_DIR} matching {cfg.CURVE_GLOB}")
            curve_file = find_curve_file(cfg)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2
        try:
            yc = load_yield_curve(curve_file)
        except Exception as e:
            print(f"Error: failed to load curve: {e}", file=sys.stderr)
            return 3
        try:
            mdate = parse_maturity_date(args.maturity)
        except Exception as e:
            print(f"Error: invalid maturity '{args.maturity}': {e}", file=sys.stderr)
            return 4

        if args.fixed is None:
            par = solve_par_rate(1_000_000.0, mdate, yc)
            print(f"Par rate: {par*100:.4f}%")
            return 0

        try:
            fixed_rate = float(args.fixed) / 100.0
        except Exception as e:
            print(f"Error: invalid fixed rate '{args.fixed}': {e}", file=sys.stderr)
            return 5
        value, _ = price_swap(1_000_000.0, fixed_rate, mdate, yc)
        print(f"Swap NPV: {value:,.2f}")
        return 0
    except SystemExit as se:
        # argparse uses SystemExit for usage errors
        code = int(getattr(se, "code", 2) or 2)
        if code != 0:
            print("Error: invalid arguments", file=sys.stderr)
        return code


if __name__ == "__main__":
    raise SystemExit(main())
