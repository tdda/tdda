#!/bin/sh

frictionless describe simple3x2.csv --json --type resource --field-missing-values "" --dialect '{"delimiter": ",", "quoteChar": "\"", "escapeChar": "\\", "header": true, "header_rows": [0], "doubleQuote": false}' > simple3x2.resource.json

frictionless describe simple3x2.csv --yaml --type resource --field-missing-values "" --dialect '{"delimiter": ",", "quoteChar": "\"", "escapeChar": "\\", "header": true, "header_rows": [0], "doubleQuote": false}' > simple3x2.resource.yaml


frictionless describe simple3x2.csv --json --type package --field-missing-values "" --dialect '{"delimiter": ",", "quoteChar": "\"", "escapeChar": "\\", "header": true, "header_rows": [0], "doubleQuote": false}' > simple3x2.package.json

frictionless describe simple3x2.csv --yaml --type package --field-missing-values "" --dialect '{"delimiter": ",", "quoteChar": "\"", "escapeChar": "\\", "header": true, "header_rows": [0], "doubleQuote": false}' > simple3x2.package.yaml




