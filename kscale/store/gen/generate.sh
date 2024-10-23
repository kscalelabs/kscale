#!/bin/sh
# Install the codegen tool: `pip install datamodel-code-generator`

openapi_url="https://api.kscale.dev/openapi.json"
curl -s $openapi_url > openapi.json
datamodel-codegen --input openapi.json --input-file-type openapi --output api.py

# Prepends docstring.
echo "\"\"\"Auto-generated by generate.sh script.\"\"\"\n" | cat - api.py > temp && mv temp api.py
black api.py
ruff format api.py
