from agno.vectordb.lancedb import LanceDb
ld = LanceDb(table_name="test_probe", uri="data/lancedb")
attrs = [a for a in dir(ld) if not a.startswith("__")]
print("Attributes:", attrs)
for attr in attrs:
    try:
        val = getattr(ld, attr)
        if not callable(val):
            print(f"  {attr} = {type(val).__name__}: {repr(val)[:120]}")
    except Exception as e:
        print(f"  {attr} = ERROR: {e}")
