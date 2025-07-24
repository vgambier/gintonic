#!/bin/bash

shopt -s extglob
ares "$1"/@(*.img|*.cue) --fullscreen
