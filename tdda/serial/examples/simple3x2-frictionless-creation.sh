#!/bin/sh

frictionless describe simple3x2.csv --json --type resource --dialect '{"delimiter": ",", "quoteChar": "\"", "escapeChar": "\\", "header": true, "header_rows": [0], "doubleQuote": false}' > simple3x2.resource.json

frictionless describe simple3x2.csv --yaml --type resource --dialect '{"delimiter": ",", "quoteChar": "\"", "escapeChar": "\\", "header": true, "header_rows": [0], "doubleQuote": false}' > simple3x2.resource.yaml


frictionless describe simple3x2.csv --json --type package --dialect '{"delimiter": ",", "quoteChar": "\"", "escapeChar": "\\", "header": true, "header_rows": [0], "doubleQuote": false}' > simple3x2.package.json

frictionless describe simple3x2.csv --yaml --type package --dialect '{"delimiter": ",", "quoteChar": "\"", "escapeChar": "\\", "header": true, "header_rows": [0], "doubleQuote": false}' > simple3x2.package.yaml




