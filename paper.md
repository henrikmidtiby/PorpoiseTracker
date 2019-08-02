---
title: Using drones to quantify the
  length of marine animals
authors:
- affiliation: 1
  name: Henrik Dyrberg Egemose
- affiliation: 1
  name: Henrik Skov Midtiby
  orcid: 0000-0002-3310-5680
date: '2019-06-21'
output: pdf_document
bibliography: paper.bib
tags:
- Python
- UAV
- DJI
- Marine animals
affiliations:
- index: 1
  name: UAS Center, University of Southern Denmark
---

# Summary

It is a daunting task to quantify the length of marine mammals like porpoises and seals, 
as it most often is required to catch the animal before it can be quantified.
Using video acquired with an Unmanned Aerial Vehicle (UAV) and then utilizing information
about camera position and orientation from the flight log of the UAV, it is possible to 
estimate lengths of marine animals while they are in the water surface and get gps 
coordinates to the location of the animal.
The ``Porpoise tracker`` python program enables the user to combine videos recorded by
DJI drones with information from the flight log. 
The accuracy of method was investigated by [@Midtiby2019Havforsker].

With the software marine biologist can estimate the size of marine animals
in UAV recordings, using an noninvasive method and with a significantly
lower time usage compared to the capture and measure process.

The Porpoise Tracker software is available on [github.com] [@Egemose2019PorpoiseTracker]
and is released under the BSD 3-Clause License.
The software was developed as part of the Back2Nature project
at the University of Southern Denmark.


# Acknowledgements

We want to thank Magnus Wahlberg, Emilie Nicoline Stepien and
Gema Palacino-Gonzalez which all have tested early versions of the 
``Porpoise Tracker`` program and given us valuable insights into the 
marine environment.

The ``Porpoise Tracker`` is currently used in several studies
related to harbor porpoises and grey seals at both the 
University of Southern Denmark and Aarhus University.


# References
