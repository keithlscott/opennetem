#!/bin/bash

now=`date -u -Iseconds`Z

echo "now is $now"

curl --request POST "http://192.168.1.176:8086/api/v2/delete?org=netem&bucket=netem" \
  --header 'Authorization: Token srd9qKlNH-7oKdCNILi47Ner5OLUOB_AyfkDvLIrmJ6UT4VnOH89foo6SfUDR45bfhfATvCo_HYqQqBxLb6G-Q==' \
  --header 'Content-Type: application/json' \
  --data '{
    "start": "2020-03-01T00:00:00Z",
    "stop":  "2024-02-16T10:00:00Z"
  }'

