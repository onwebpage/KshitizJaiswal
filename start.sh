#!/bin/bash
export DATABASE_URL="${DATABASE_URL}"
export SESSION_SECRET="${SESSION_SECRET}"
exec gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
