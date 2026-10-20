"""兼容入口：所有规则由 runtime_contract.py 维护。"""
try:
    from .runtime_contract import scan_runtime_contract, main
except ImportError:
    from runtime_contract import scan_runtime_contract, main

scan = scan_runtime_contract

if __name__ == '__main__':
    raise SystemExit(main())
