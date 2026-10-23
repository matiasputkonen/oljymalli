#!/bin/bash
d=$1; out="/home/claude/oil/data/raw3/cpc_fc/$(echo $d | tr '/' '-').txt"
[ -s "$out" ] && exit 0
curl -sS --max-time 40 -o "$out" "https://ftp.cpc.ncep.noaa.gov/htdocs/degree_days/weighted/daily_forecasts_7day/$d/Population.Heating.txt" || rm -f "$out"
