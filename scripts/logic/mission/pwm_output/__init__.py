"""
PROCESS
---
0,  Initialize value

1,  Update mission status in Backend -> Pending

2,  Turn off PWM light curtain and wait
    - After wait:
    -> Unblock wrapping area

3,  Create task rcs and wait
    - After wait:
    -> Update mission status in Backend -> Process

4,  Wait to load pallet in PWM
    - After wait:
    -> Set block wrapping area
    -> Update PWM info: no pallet

5,  Turn on PWM light curtain and wait

6,  Trigger PWM reset and wait

7,  Wait to unload done
    - After wait:
    -> Fill return location in Backend
    -> Finish mission
"""