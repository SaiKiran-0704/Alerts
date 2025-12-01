#!/bin/bash
export FLASK_APP=run_alerts_multi.py
export FLASK_ENV=production
flask run --host=0.0.0.0 --port=$PORT
