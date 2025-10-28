# System design of DAL

## Database & Signal
### Database
- Queue of mission trigger: Mission_Trigger_Model
- Table of mission: Mission_Model
- Table of device connection: Device_Connection_Model
- Table of light curtain status: Curtain_Status_Model
- Record of PWM status: PWM_Information_Model

### Signal
- Agv states from AIS: AIS_States_Signal
- Bind/Unbind trigger from WCS: Bind_RCS_Signal
- Feedback from RCS: RCS_Notify_Signal

## Procedure
### Callback
- AIS: agv target state -> LOGIC: pause robot
- WCS: bind/unbind request -> RCS: bind/unbind location
- RCS: agv_code -> LOGIC: Update to mission handler; Update to Backend
- RCS: method -> LOGIC: Set flag to mission handler

### Service
- (ONCE - START UP) Read all missions in Backend (at Logic init)
  - If mission not in Database, cancel mission
  - If mission Sign, Pending, create mission handler
  - If mission Process, cancel mission

- (ONCE - START UP) Initialize default values in Database (at Database init)
  - PWM info: no pallet, wrap busy, not ready
  - Curtain status: on
  - Device connection: disconnected

- (LOOP - START UP) Read mission trigger in Database (in Logic init)
  - If creator is PDA, get device info from Backend
  - If call and no handler, create mission
  - If cancel and have handler, check step and creator to cancel mission

- (LOOP - START UP) Read device connection status in Database (NOT USED - no uptime from gateway)
  - If device was update long time ago, remove connection
  - If device is newly updated and is connected, report to Backend

- (LOOP - START UP) Read pwm info from Gateway (in Logic init)
  - If has pallet and wrap done, create mission handler by pwm information

### Handle mission
(see https://rostekcoltd.sharepoint.com/:u:/s/Out-SourceProject/ES_HZTvuszxGhfH77cXcsJoBR3YMVzugnmLoA7NuhjZ7XQ?e=AAdcgO)

## Interface
### AIS
- Get all agv goal states (mqtt: agv_states)

### PDA
- Save mission trigger from PDA (POST: /pda/trigger)

### Database
- Save call/cancel mission trigger
- Get call/cancel mission trigger
- Get device connection status
- Add device connection status
- Remove device connection status
- Get mission information
- Update mission information
- Remove mission information
- RCS get mission information by task code
- Get light curtain status of all machines
- Update light curtain status of all machines
- Get PWM information
- Update PWM information

### Gateway
- Subscribe uptime and save connection status (mqtt: /v2.0.0/rostek/uptime) (NOT USED - no uptime from gateway)
- Generate token to communicate with gateway (private)
- Auto line:
  - Check auto line call
  - Confirm auto line call
  - Check auto line curtain status
  - Turn on/off auto line curtain
- Manual line:
  - Check manual line call
  - Confirm manual line call
- Pallet wrapping machine:
  - Check pwm status
  - Trigger start pwm
  - Check pwm curtain status
  - Open/Close pwm curtain

### WCS
- Login and get auth token (POST: /auth/login)
- Get device information (POST: /call_boxes/list)
- Update device connection status to connected (PATCH: /call_boxes/update_status_connect/dal)
- Get mission information (POST: /mission_history/list)
- Update mission with agv code (PATCH: /mission_history)
- Update mission status (PATCH: /mission_history)
- Call mission from line to pwm and get mission information (PATCH: /call_boxes/update_status_curtain_wrap/dal)
- Call mission from pwm to storage and get mission information (PATCH: /call_boxes/update_status_action/dal)
- Report cancel mission trigger (PATCH: /call_boxes/update_status_curtain_wrap/dal)
- Update location status (PATCH: /location)

### RCS
- Call (DAL is client)
  - Send agv mission (POST: /genAgvSchedulingTask)
  - Block/Unblock an area (POST: /blockArea)
  - Trigger continue mission (POST: /continueTask)
  - Pause robot (POST: /stopRobot)
  - Resume robot from pause (POST: /resumeRobot)
  - Cancel mission (POST: /cancelTask)
  - Get mission status (POST: /queryTaskStatus)
  - Bind/Unbind a location (POST: /bindCtnrAndBin)
  - Get all tasks (POST: /mockupList) (Not working)
  - Release robot from task (POST: /freeRobot)
- Feedback (DAL is server, fix path: /rcs_fb/v2)
  - All mission
    + Agv code (POST: /agv)
    + Cancel (POST: /cancel)
  - Manual input
    + Agv reach pickup point (POST: /manual_input, method: pickup)
    + Agv reach check point (POST: /manual_input, method: check)
    + Agv unload done (POST: /manual_input, method: unload)
  - Auto input
    + Agv reach pickup point (POST: /auto_input, method: pickup)
    + Agv reach check point (POST: /auto_input, method: check)
    + Agv unload done (POST: /auto_input, method: unload)
    + Agv reach last point (POST: /auto_input, method: last)
  - Manual output
    + Agv reach pickup point (POST: /manual_output, method: pickup)
    + Agv reach PWM front point (POST: /manual_output, method: pwm)
    + Agv unload done (POST: /manual_output, method: unload)
    + Agv reach last point (POST: /manual_output, method: last)
  - Auto output
    + Agv reach auto line front point (POST: /auto_output, method: pickup)
    + Agv load done (POST: /auto_output, method: load)
    + Agv reach PWM front point (POST: /auto_output, method: pwm)
    + Agv unload done (POST: /auto_output, method: unload)
    + Agv reach last point (POST: /auto_output, method: last)
  - PWM output
    + Agv load done (POST: /pwm, method: load)
    + Agv unload done (POST: /pwm, method: unload)