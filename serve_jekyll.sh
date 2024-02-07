#!/bin/bash
# brew install imagemagick
bundle install
rbenv global 3.0.6
bundle exec jekyll build
bundle exec jekyll serve --open-url --livereload
