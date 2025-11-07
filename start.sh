#!/bin/bash
# Unset DATABASE_URL for local development to use SQLite
unset DATABASE_URL
export SESSION_SECRET="${SESSION_SECRET}"
exec gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
