from tdda.constraints.api import (discover, verify, detect)

# backwards compatibility
discover_df = discover
verify_df = verify
detect_df = detect

from tdda.constraints.db.constraints import (discover_db_table,
                                             verify_db_table,
                                             detect_db_table)

