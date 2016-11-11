#!/bin/sh

while inotifywait -e modify /var/www/wx-test/static/style.less; do
        lessc /var/www/wx-test/static/style.less > /var/www/wx-test/static/style.css 
done
