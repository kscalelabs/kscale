#!/bin/sh
# Install the codegen tool: `pip install datamodel-code-generator`

openapi_url="https://api.kscale.store/openapi.json"
curl -s $openapi_url > openapi.json
datamodel-codegen --input openapi.json --input-file-type openapi --output api.py
