#!/usr/bin/env bash

git checkout dev
git push -f origin HEAD
git branch -D master
git checkout -b master
git push -f origin HEAD
git checkout dev
if git branch | grep -q feature ; then
  parallel ::: 'git branch -D' 'git push origin --delete' ::: $(git branch | grep feature)
fi
