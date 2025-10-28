"""
TRIGGER
---
Trigger cancel:
-> Able till step 5
    
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
    - After wait:
        - If cancel flag:
        -> Goto step 8

6,  Continue task in RCS to return point and wait

7,  Wait to unload at return point
    - After wait:
    -> Finish mission

8,  Continue task in RCS to pickup point and wait

9,  Wait to unload at pickup point
    - After wait:
    -> Fill pickup location in Backend
    -> Cancel mission without RCS
"""