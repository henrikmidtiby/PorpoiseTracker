---
title: "Porpoise tracker - user guide"
author: "Henrik Skov Midtiby"
date: "June 25, 2019"
output: html_document
---

A short guide on how to use the Porpoise Tracker program.


## Installation

The Porpoise tracker program was developed under Ubuntu 18.04, and the installation guide 
below is intended for that platform.



```
sudo apt install python3-venv wine64 gstreamer1.0-libav gobject-introspection 
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0
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


## Using the program

### Launching the program

The program is launched from the command line,by running the commands.
```
cd ~/porpoisetracker
source env/bin/activate
cd PorpoiseTracker
python porpoisetracker.py
```

At this point, the main window is displayed.

![Main window when no video has been loaded.](pic/Porpoise Measure_010.png)

### Loading data into the program

It is now time to load video, logfile and camera information into the system.
The video should origin from a DJI drone eg. a Phantom or Mavic; these video files are usually named like `DJI_0013.MOV`.
The log file should be from the same flight. It is usually named like `DJIFlightRecord_2015-10-05_[09-39-07].txt`.
The file containing information about the field of view, should have contents like shown below:
```{bash eval=FALSE, include=TRUE}
horizontal_fov,vertical_fov
71.15,43.97 
```
Enter the File menu and `Open video`, `Import drone log` and `Import fov`.

![File menu](pic/Menu_009.png)


After having loaded the required data into the program, the two windows will
be displayed.
The first window shows the first frame from the video and the second 
window contains curves representing the drone height and camera orientation 
during the flight.


### Main window

The main window consists of three elements: the video display (top left), 
video navigation toolbar (botton left) and an annotation widget (right).
The video display, shows the current frama from the video and
details about the camera heigth and orientation.
The camera height and orientation is displayed as rough numbers in the 
top left corner of the video display.
The camera orientation is specified by the numbers: yaw, pitch and roll.
The yaw is the compas heading of the camera, the pitch is the angle between
the horisontal plane and the camera orientation; and finally the roll
is how much the horizon is tilted in the image.

Based on the camera orientation and information about the field of view
of the drone, an artificial horizon is added to the video display.
The artificial horison contains the following elements:

* Horizontal line (pitch = 0), shown with a dashed blue line
* Negative 45 degree pitch line (pitch = -45 degree), shown with a dashed blue line
* East/west direction indicator, shown with a red dashed line
* and a north south direction indicator, shown with a green dashed line.

When playing back the video, it is important to observe the 
artificial horizon and see if it follows the motion of the camera.
If the artificial horizon moves independently of the camera, 
it indicates that the video and logfile is not matched properly
and that the generated results will be **invalid**.




![Artificial horison](pic/Porpoise Measure_002.png)


![Artificial horison with compas directors. In this case the camera is looking down.](pic/Porpoise Measure_003.png)

### Yaw, pitch and roll plot

After opening a drone log file, the Yaw, pitch and roll plot open automatically.
In the plot, it is possible to see how the yaw, pitch and roll of the camera and 
the UAV altitude changes over time.
The current time of the frame shown in the main windows is indicated with a 
vertical red line in the plots.
The time indication is only updated when the video is paused.

The areas that are marked with a grey shade, is when the UAV was recording a video.
The bright green rectangle shows the timewise alignment between the logfile and
the video.
If the timewise alignment of video and logfile is wrong, it is possible to realign 
the video by clicking on a gray shaded region in the Yaw, pitch, roll plot.



![Camera height and orientation](pic/Yaw Pitch Roll Plot_001.png)




# Todo: 

Publish some example data.