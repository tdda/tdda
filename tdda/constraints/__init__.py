try:
    import pandas as pd
except ImportError:
    pd = None

if pd is not None:
    from tdda.constraints.pd.constraints import (discover_df,
                                                 verify_df,
                                                 detect_df)

from tdda.constraints.db.constraints import (discover_db_table,
                                             verify_db_table,
                                             detect_db_table)

