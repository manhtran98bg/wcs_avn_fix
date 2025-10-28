"""
TRIGGER
---
Trigger cancel:
-> Able till step 6
  
PROCESS
---
0,  Initialize value

1,  Update mission status in Backend -> Pending
    Unbind return location in RCS

2,  Create task rcs and wait
    - If cancel flag:
    -> Cancel mission without RCS
    - After wait
    -> Update mission status in Backend -> Process

3,  Wait for agv code
    - If cancel flag:
    -> Cancel mission

4,  Wait to reach pickup point
    - If cancel flag:
    -> Cancel mission
    - After wait:
    -> Empty pickup location in Backend

5,  Wait to reach check point

6,  Turn off auto line light curtain and wait
    - If cancel flag or auto line idle
    -> Goto step 11

7,  Continue task in RCS to return point and wait

8,  Wait to unload at return point

9,  Continue task in RCS to auto line front point and wait

10, Wait to reach auto line front point

11, Turn on auto line light curtain and wait
    - After wait
    -> Finish mission

12, Continue task in RCS to pickup point and wait

13, Wait to unload at pickup point
    - After wait:
    -> Fill pickup location in Backend

14, Continue task in RCS to pickup front point (+ "_1") and wait

15, Wait to reach pickup front point
    - After wait:
    -> Cancel mission without RCS
"""