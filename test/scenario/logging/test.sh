#!/bin/sh

#
# Sync mode: RECEIVER
#
echo ""
echo "\033[90m#############################################\033[m"
echo "\033[94m[INFO]\033[m Testing sync mode: RECEIVER with logging"
echo "\033[90m#############################################\033[m"
echo ""
docker-compose exec www2 python3 /var/www/html/sync.py -f /var/www/html/test/scenario/logging/sync-www1-to-local.json -v 1
#
# Reset scenario
#
sh ../helper/cleanup.sh
