"""Append-only sell metadata; original positional fields remain at 0..63."""
BASE_FIELD_COUNT = 64
# name, SQL type, default. Times are KST strings; epoch companions are seconds.
EXTRA_COLUMNS = [("buyUid", "BIGINT", 0)]
for leg in (1, 2):
    EXTRA_COLUMNS.extend([
        (f"sell{leg}Price", "DOUBLE", 0),
        (f"sell{leg}Quantity", "DOUBLE", 0),
        (f"sell{leg}Time", "VARCHAR(19)", ""),
        (f"sell{leg}TimeEpoch", "BIGINT", 0),
        (f"sell{leg}ProfitPrice", "DOUBLE", 0),
        (f"sell{leg}Reason", "VARCHAR(16)", ""),
    ])


def ensure_sell_columns(connection):
    cursor = connection.cursor
    cursor.execute("SHOW COLUMNS FROM candleSellResultList")
    existing = {row["Field"].lower() for row in cursor.fetchall()}
    for name, kind, default in EXTRA_COLUMNS:
        if name.lower() not in existing:
            literal = "''" if default == "" else "0"
            cursor.execute(f"ALTER TABLE candleSellResultList ADD COLUMN "
                           f"`{name}` {kind} NOT NULL DEFAULT {literal}")
    connection.commit()


def with_sell_columns(data):
    values = list(data)
    if len(values) == BASE_FIELD_COUNT:
        values.extend(default for name, kind, default in EXTRA_COLUMNS)
    elif len(values) != BASE_FIELD_COUNT + len(EXTRA_COLUMNS):
        raise ValueError("Unexpected candleSellResultList field count")
    return values
