#!/bin/bash

shopt -s extglob
mednafen "$1"/@(*.img|*.cue)
