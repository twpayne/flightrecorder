flightrecorder
==============

1. Remove all waypoints doesn't work on 5020.


Flytec 5020
===========

1. The `PBRWPX` (delete all waypoints) command takes tens of seconds and does not delete all waypoints (1.22).

2. The `PBRWPR` (upload waypoint) does not always result in the waypoint being uploaded (1.22).

3. The `PBRTR` (download tracklog) command sometimes generates duplicate B records (1.22).


Flytec 6030
===========

1. The `PBRWPRE` (upload extended waypoint) command appears not to work at all.



Flymaster B1 Nav
================

1. The `PFMDNL` (download tracklog) sometimes sends a Track Position Record Delta packet before the first Key Track Position Record (1.21k).

2. The Flight Information Record contains two extra bytes (1.21j, 1.21k).

3. When the CIVL ID, competition ID and pilot name are set with `PBRIDS` they are padded with garbage if they sent strings are not full length (1.21k).

4. The competition ID set with the `PFMIDS` command is return in the glider type field of the Flight Information Record packet.

5. The CIVL ID set with the `PFMIDS` command is returned in the competition ID field of the Flight Information Record packet.

6. There is no way to set the glider brand field returned in the Flight Information Record.

7. There is no way to set the glider model field returned in the Flight Information Record.

8. The `PFMDNL,LST` (tracklog list) command returns the track start times in local time, not UTC.  If the user changes the UTC offset between flights then this can result in duplicate start times.

9. The position of waypoints uploaded with `PFMWPR` and downloaded by `PFMWPL` can vary by 15 meters or more.  Example:

    send `$PFMWPR,4704.428,N,04704.428,E,,B01 ERROR EXAMPL,0000,0*13`
    send `$PFMWPL,*3C`
    recieve `$PFMWPL,047.0737,N,047.0737,E,0,B01 ERROR EXAMPL,0*21`

The 4th decimal place of the latitude and longitude is incorrect, it should be 047.0738, not 047.0737.  This corresponds to an error of approximately 15 metres.
