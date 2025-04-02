#!/bin/bash
cd production/backend
source venv/Scripts/activate
python -m uvicorn main:app --reload