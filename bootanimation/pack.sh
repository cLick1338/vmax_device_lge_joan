#!/bin/bash -e
#Vmax
# pack.sh <render dir> <out zip>: 000-449 -> part0/1/2, each frame cropped to its content + trim.txt, stored zip
# PNGQUANT=/path/to/pngquant: palette-quantize frames (quality 90-100; frames that can't reach it stay 24-bit)
R=$1; OUT=$2; W=$(mktemp -d)
mkdir -p $W/part0 $W/part1 $W/part2
for i in $(seq 0 449); do
  f=$(printf %03d $i).png
  if [ $i -lt 150 ]; then p=part0; elif [ $i -lt 240 ]; then p=part1; else p=part2; fi
  g=$(convert $R/$f -format '%@' info: 2>/dev/null)
  case $g in 0x0*) g=1x1+0+0 ;; esac  # all-black frame: one black pixel
  convert $R/$f -crop $g +repage -define png:color-type=2 $W/$p/$f
  if [ -n "$PNGQUANT" ]; then
    $PNGQUANT --quality=90-100 --speed 1 --strip --force --output $W/$p/$f $W/$p/$f 2>/dev/null || true
  fi
  echo "$g" >> $W/$p/trim.txt
done
printf '%s 60\nc 1 0 part0\nc 0 0 part1\nc 1 0 part2\n' "$(identify -format '%w %h' $R/000.png)" > $W/desc.txt
rm -f $OUT
(cd $W && zip -0qX $OUT desc.txt && for p in part0 part1 part2; do zip -0qX $OUT $p/ $(ls $p/*.png | sort) $p/trim.txt; done)
rm -rf $W
