from __future__ import annotations
import argparse
import json
from .parsing import parse_maturity_date, load_yield_curve
from .pricer import price_swap, solve_par_rate
from .utils import find_curve_file
from .config import get_config


def main() -> int:
    """CLI entry point for Gemini IRD Pricer."""
    parser = argparse.ArgumentParser(
        description="Gemini IRD Pricer CLI - Price interest rate swaps"
    )
    parser.add_argument("--notional", type=str, help="Notional amount (e.g., 10m, 1000000)")
    parser.add_argument("--maturity", type=str, help="Maturity (e.g., 5y, 2028-12-31)")
    parser.add_argument("--fixed", type=float, help="Fixed rate in percent (for pricing)")
    parser.add_argument("--data-dir", type=str, help="Override data directory")
    parser.add_argument("--config", action="store_true", help="Print configuration")
    parser.add_argument("--version", action="store_true", help="Print version")

    args = parser.parse_args()

    try:
        if args.version:
            try:
                from .version import __version__
                print(f"Gemini IRD Pricer v{__version__}")
            except ImportError:
                print("Gemini IRD Pricer v0.1.0")
            return 0
        
        if args.config:
            cfg = get_config()
            print(json.dumps(cfg.model_dump(), indent=2))
            return 0

        if not args.notional or not args.maturity:
            parser.print_help()
            return 1

        try:
            cfg = get_config()
            config_dict = cfg.model_dump()
            
            if args.data_dir:
                config_dict["DATA_DIR"] = args.data_dir

            file_path = find_curve_file(config_dict)
            yield_curve = load_yield_curve(file_path)

            if args.fixed is not None:
                # Price the swap
                notional = float(args.notional.replace('m', '000000').replace('k', '000'))
                maturity_date = parse_maturity_date(args.maturity)
                fixed_rate = args.fixed / 100.0
                
                npv, schedule = price_swap(notional, fixed_rate, maturity_date, yield_curve, config_dict)
                
                print(f"Swap NPV: {npv:,.2f}")
                print(f"Notional: {notional:,.0f}")
                print(f"Fixed Rate: {args.fixed:.2f}%")
                print(f"Maturity: {args.maturity}")
            else:
                # Solve for par rate
                notional = float(args.notional.replace('m', '000000').replace('k', '000'))
                maturity_date = parse_maturity_date(args.maturity)
                
                par_rate = solve_par_rate(notional, maturity_date, yield_curve, config_dict)
                
                print(f"Par Rate: {par_rate * 100:.4f}%")
                print(f"Notional: {notional:,.0f}")
                print(f"Maturity: {args.maturity}")

            return 0

        except Exception as e:
            print(f"Error: {e}")
            return 1

    except KeyboardInterrupt:
        print("\nInterrupted")
        return 130


if __name__ == "__main__":
    exit(main())
