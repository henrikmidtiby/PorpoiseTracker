---
title: "Porpoise tracker - installation"
author: "Henrik Skov Midtiby"
date: "June 26, 2019"
output: html_document
---

## Installation

The Porpoise tracker program was developed under Ubuntu 18.04, and the installation guide 
below is intended for that platform.

```
sudo apt install python3-venv wine64 gstreamer1.0-libav gobject-introspection python3-gi python3-gi-cairo gir1.2-gtk-3.0 libgirepository1.0-dev git python-gst-1.0 ffmpeg libcairo2-dev pkg-config python3-dev
mkdir ~/porpoisetracker
cd ~/porpoisetracker
python3 -m venv env
source env/bin/activate
git clone https://github.com/henrikmidtiby/PorpoiseTracker.git
cd PorpoiseTracker
pip install -r requirements.txt
cd ..
git clone https://github.com/henrikmidtiby/gtk_modules.git
cd gtk_modules
pip install -e .
cd ..
```


