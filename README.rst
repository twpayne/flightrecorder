flightrecorder
==============

Utilities for flight recorders Copyright (C) 2011 Tom Payne
twpayne@gmail.com

Supported flight recorders
--------------------------

Flytec: 5020, 5030, 6015, 6020, 6030

Brauniger: Competino, Competino+, Compeo, Compeo+, Galileo, IQ-Basic

Flymaster: B1 Nav

Installation
============

Run:

::

    pip install flightrecorder

Usage
=====

Downloading tracklogs
---------------------

To download all tracklogs, just run

::

    flightrecorder

The program will attempt to detect your flight recorder.

Uploading waypoints
-------------------

::

    flightrecorder waypoint upload filename.wpt

Downloading waypoints
---------------------

::

    flightrecorder waypoints > filename.wpt

Removing waypoints
------------------

To remove all waypoints, run

::

    flightrecorder waypoints remove

To remove selected waypoints, run

::

    flightrecorder waypoints remove name1 [name2 ...]

Flashing
--------

::

    flightrecorder flash firmware-filename

``firmware-filename`` is the name of the file containing the firmware.
The program is fairly clever and can extract firmware from ``.exe``
files, ``.zip`` files, as well as obfuscated and unobfuscated firmware
files (``.moc``).

Getting parameters
------------------

::

    flightrecorder get parameter

Valid values of ``parameter`` depend on the flight recorder model, but
can include ``glider_id``, ``glider_type``, ``pilot_name``,
``recording_interval``, ``utc_offset``, ``civl_id``, and
``competition_id``.

Setting parameters
------------------

::

    flightrecorder set parameter value

Licence
-------

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your
option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
Public License for more details.

You should have received a copy of the GNU General Public License along
with this program. If not, see http://www.gnu.org/licenses/.
