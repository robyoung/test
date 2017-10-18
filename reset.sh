#!/usr/bin/env bash

git checkout begining
for branch in dev master; do
  git branch -D $branch
  git checkout -b $branch
  git push -f origin HEAD
done
git checkout begining
if git branch | grep -q feature ; then
  parallel ::: 'git branch -D' 'git push origin --delete' ::: $(git branch | grep feature)
fi
