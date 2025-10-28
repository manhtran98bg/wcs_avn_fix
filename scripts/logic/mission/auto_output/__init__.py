"""
TRIGGER
---
Trigger cancel:
-> Able till step 5

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

4,  Wait to reach auto front point
    - After wait:
    -> Check auto line call again
        - If idle:
        -> Cancel mission

5,  Turn off auto line light curtain and wait

6,  Continue task in RCS to auto line point and wait

7,  Wait to load done

8,  Turn on auto line light curtain and wait

9,  Wait to reach PWM front point
    - After wait:
    -> Start timer

10, Wait PWM ready (no pallet, ready, curtain on)
    - If timeout or PWM bypass
    -> Unbind manual wrap point
    -> Goto step 15

11, Turn off PWM light curtain and wait
    - If timeout or PWM bypass
    -> Unbind manual wrap point
    -> Goto step 15
    - After wait:
    -> Unbind PWM inside point
    -> Unblock wrapping area on RCS

12, Continue task in RCS to PWM inside point and wait

13, Wait to unload at PWM inside point
    - After wait:
    -> Update PWM infomation

14, Continue task in RCS to PWM behind point and wait

15, Wait to reach PWM behind point
    - After wait:
    -> Set block wrapping area on RCS
    -> Turn on PWM light curtain
    -> Trigger PWM start wrapping
    -> Finish mission

16, Continue task in RCS to manual wrap point and wait

17, Wait to unload at manual wrap point

18, Continue task in RCS to manual wrap front point and wait

19, Wait to reach manual wrap front point
    - After wait:
    -> Cancel mission without RCS
"""