#!/bin/bash

shopt -s extglob
flycast "$1"/@(*.img|*.cue)
