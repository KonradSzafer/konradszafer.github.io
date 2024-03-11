#!/bin/bash

# Clean cache
rm -rf _site \
    .sass-cache \
    .jekyll-cache \
    .jekyll-metadata \
    .tweet-cache \
    vendor

# brew install imagemagick
# fix GH deplyment: bundle lock --add-platform x86_64-linux
bundle install
rbenv global 3.0.6
bundle exec jekyll build
bundle exec jekyll serve --open-url --livereload
