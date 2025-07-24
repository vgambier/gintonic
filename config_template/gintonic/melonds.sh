#!/bin/bash

#filepath=${1%/*}
filebase=${1##*/}
fileprefix=${filebase%.*}
fileextension=${filebase##*.}

echo "$1|$fileprefix.nds"

if [ $fileextension == "zip" ]; then
	melonDS "$1|$fileprefix.nds"
elif [ $fileextension == "nds" ]; then
	melonDS "$1"
else
	echo "Error: only .nds and .zip are allowed"
fi

# melonDS can open archives, but not via the CLI. This workaround is necessary until the feature is implemented.
# https://github.com/Arisotura/melonDS/issues/1108
# https://github.com/Arisotura/melonDS/issues/1393
# https://github.com/Arisotura/melonDS/issues/1425
