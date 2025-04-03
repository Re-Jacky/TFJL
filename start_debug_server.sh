#!/bin/bash
cd production/backend

# Check if running on macOS or Windows and use appropriate activation path
if [[ "$(uname)" == "Darwin" ]]; then
    source venv/bin/activate
else
    source venv/Scripts/activate
fi

python -m uvicorn main:app --reload