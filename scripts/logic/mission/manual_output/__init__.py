"""
TRIGGER
---
Trigger cancel:
-> Able till step 4 by callbox

Cancel mission:
-> Add: Free agv

PROCESS
---
0,  Initialize value
    - If PWM not bypass
    -> Next step

1,  Update mission status in Backend -> Pending
    Bind pickup location in RCS

2,  Create task rcs and wait
    - After wait:
    -> Update mission status in Backend -> Process

3,  Wait for agv code

4,  Wait to load semi product pallet

5,  Wait to reach PWM front point
    - After wait:
    -> Start timer

6,  Wait PWM ready (no pallet, ready, curtain on)
    - If timeout or PWM bypass
    -> Unbind manual wrap point
    -> Goto step 12

7,  Turn off PWM light curtain and wait
    - If timeout or PWM bypass
    -> Unbind manual wrap point
    -> Goto step 12
    - After wait:
    -> Unbind PWM inside point
    -> Unblock wrapping area on RCS

8, Continue task in RCS to PWM inside point and wait
        
9, Wait to unload at PWM inside point
    - After wait:
    -> Update PWM infomation

10, Continue task in RCS to PWM behind point and wait

11,  Wait to reach PWM behind point
    - After wait:
    -> Set block wrapping area on RCS
    -> Turn on PWM light curtain
    -> Trigger PWM start wrapping
    -> Finish mission

12, Continue task in RCS to manual wrap point and wait

13, Wait to unload at manual wrap point

14, Continue task in RCS to manual wrap front point and wait
        
15, Wait to reach manual wrap front point
    - After wait:
    -> Cancel mission without RCS
"""