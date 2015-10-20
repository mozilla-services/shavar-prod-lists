#!/bin/sh
RET=0

for f in *.json ; do
  echo "$f:"
  json_verify < "$f" || RET=1
  echo
done

exit $RET
