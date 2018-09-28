# PorpoiseTracker

PorpoiseTracker is a tool to measure and track porpoises or other things.

## Getting Started Ubuntu

### Prerequisites

* python 3 and pip
* PyGObject

### Installation

* Open a terminal in the folder where PorpoiseTracker shall be.
* Clone the repository:  `git clone git@gitlab.com:UAS-centre/PorpoiseTracker.git`
* Install dependencies: `pip install -r requirements.txt`

## Usage

```
python3 porpoisetracker.py
```

### GUI usage:

* First a video must be opened.
* Then a drone log and a FOV file must be opened.
* A camera calibration file from Matlab can also be opened.
* Now lines can be drawn and the length is displayed in the side menu.

#### Saved markings file format:
header: 'Name', 'length', 'time', 'lat', 'lon', 'drone height', 'drone yaw', 'drone pitch', 'drone roll', 'drone lat', 'drone lon', 'x1', 'y1', 'x2', 'y2', 'width', 'height', 'video position', 'red', 'green', 'blue', 'alpha', 'video name'

## Author
Written by Henrik Dyrberg Egemose (hesc@mmmi.sdu.dk) as part of the InvaDrone and Back2Nature projects, research projects by the University of Southern Denmark UAS Center (SDU UAS Center).

## License

This project is licensed under the 3-Clause BSD License - see the [LICENSE](LICENSE) file for details.