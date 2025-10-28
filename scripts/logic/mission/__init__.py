"""
TRIGGER
---
Call button | auto line sensor trigger
-> Generate mission by Backend
-> Save mission to Database with status Created
-> Create mission handler

Trigger cancel
-> Set cancel flag

RCS feedback
-> Update agv code | Set flag

Cancel flag from RCS:
-> Cancel without RCS

METHOD
---
Clean mission:
    1, Remove mission in database
    2, Remove handler
    3, Turn off led if button id in callbox list

Finish mission:
    1, Update mission status in WCS -> Done
    2, Clean mission

Cancel mission without RCS:
    1, Update mission status in WCS -> Cancel
    2, Clean mission

Cancel mission:
    1, Cancel task in RCS
    2, Cancel mission without RCS
"""