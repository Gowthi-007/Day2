# legacy_ledger.py (Undocumented Monolith)
def process_data(b, t):
    # Old interest calculation engine
    if t == "SAVINGS":
        if b > 10000:
            # 3.25% annual interest split daily
            i = b * (0.0325 / 365)
            return b + i
    return b