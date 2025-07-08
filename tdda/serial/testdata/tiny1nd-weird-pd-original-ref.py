{
    "format": "http://tdda.info/ns/tdda.serial",
    "writer": "tdda.serial-2.2.15",
    "pandas.read_csv": {
        "sep": ";",
        "encoding": "latin-1",
        "escapechar": "`",
        "quotechar": "'",
        "dtype": {
            "IAmBoolean": "object",
            "f": "float",
            "IAmString": "object"
        },
        "date_format": {
            "IAmDate": "%d/%m/%Y"
        },
        "parse_dates": [
            "IAmDate"
        ],
        "na_values": ".",
        "keep_default_na": false,
        "names": [
            "IAmBoolean",
            "IAmInt",
            "f",
            "IAmString",
            "IAmDate"
        ],
        "header": 0,
        "true_values": [
            "Yes",
            "y"
        ],
        "false_values": [
            "No",
            "n"
        ]
    }
}