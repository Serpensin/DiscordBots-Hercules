#!/bin/bash
docker build -t serpensin/hercules:debug ./Hercules
docker run --env-file ./Hercules/.env -it --rm --name hercules serpensin/hercules:debug
