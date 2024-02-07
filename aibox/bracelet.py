# Some comments:

# issues.... perhaps every n frame this bbox_info should be wipped clean....
# or when the hand reaches an object.....
# empty it when it reaches the object or empty it within limited frame, like 20 or 50....

# now we have four numbers...which we need two of them the first two...
# write a function so it would outout left, right, up, down so the two number reach each other!!!!

# bbox_info ---- This is a list...each element is dictionary which had the key label and bbox
# we only need to accses the label that is person....and one other object
# then these two are needed for always....

# xywh --- xy is the center!
# simple version of bounding boxes

import time
from pybelt.belt_controller import (BeltConnectionState, BeltController,
                                    BeltControllerDelegate, BeltMode,
                                    BeltOrientationType,
                                    BeltVibrationTimerOption)

from auto_connect import interactive_belt_connect, setup_logger

import keyboard

from pynput.mouse import Listener

def on_click(x, y, button, pressed):
    if pressed:
        print(f"Mouse clicked at (x, y): {x}, {y}")
        return False

# Variable that determines if belt is connected
# If belt is not connected value is set to 1 and instead of vibrations print commands serve as guidance
mock_belt = 0

class Delegate(BeltControllerDelegate):
    # Belt controller delegate
    pass

def connect_belt():
    setup_logger()

    belt_controller_delegate = Delegate()
    belt_controller = BeltController(belt_controller_delegate)

    # Interactive script to connect the belt
    interactive_belt_connect(belt_controller)
    if belt_controller.get_connection_state() != BeltConnectionState.CONNECTED:
        print("Connection failed.")
        global mock_belt
        #mock_belt = 1
        return False
    else:
        # Change belt mode to APP mode
        belt_controller.set_belt_mode(BeltMode.APP_MODE)
        return True, belt_controller

vibration_intensity = 100

def navigate_hand(belt_controller,bboxs_hands,bboxs_objs, search_key_obj: str, search_key_hand: list, hor_correct: bool = False, ver_correct: bool = False, grasp: bool = False, look_hand: bool = False, look_obj: bool = False):
    '''
    Function that navigates the hand to the target object. Handles cases when either hand or target is not detected
    Input:
    • bbox_info - structure containing following information about each prediction: "class","label","confidence","bbox"
    • search_key_obj - integer representing target object class
    • search_key_hand - list of integers containing hand detection classes used for navigation
    • hor_correct - boolean representing whether hand and object are assumed to be aligned horizontally; by default False
    • ver_correct - boolean representing whether hand and object are assumed to be aligned vertically; by default False
    • grasp - boolean representing whether grasp command has been sent; by default False
    Output:
    • horizontal - boolean representing whether hand and object are aligned horizontally after execution of the function; by default False
    • vertical - boolean representing whether hand and object are aligned vertically after execution of the function; by default False
    • grasp - boolean representing whether grasp command has been sent; by default False
    • check
    • check_dur
    '''
    global mock_belt

    horizontal, vertical = False, False

    max_hand_confidence = 0
    max_obj_confidence = 0

    #print(bbox_info)

    bbox_hand, bbox_obj = None, None

    # Search for object and hand with the highest prediction confidence
    for bbox in bboxs_hands:
        if bbox["class"] in search_key_hand and bbox["confidence"] > max_hand_confidence:
            bbox_hand = bbox.get("bbox")
            max_hand_confidence = bbox["confidence"]
            print(f"hand confidence: {bbox['confidence']} \n")

    for bbox in bboxs_objs:
        if bbox["label"] == search_key_obj and bbox["confidence"] > max_obj_confidence:
            print(f"label: {bbox['label']}")
            bbox_obj = bbox.get("bbox")
            max_obj_confidence = bbox["confidence"]
            print(f"obj confidence: {bbox['confidence']} \n")

    print(bbox_hand)
    print(bbox_obj)
 
    # Hand is detected, object is not detected, and they are aligned horizontally and vertically - send grasp command
    # Assumption: occlusion of the object by hand
    if bbox_hand != None and hor_correct and ver_correct:

        #if not mock_belt:
        belt_controller.stop_vibration()

        print("G R A S P !")
        
        #if not mock_belt:
        belt_controller.send_pulse_command(
                        channel_index=0,
                        orientation_type=BeltOrientationType.ANGLE,
                        orientation=90,
                        intensity=vibration_intensity,
                        on_duration_ms=150,
                        pulse_period=500,
                        pulse_iterations=9,
                        series_period=5000,
                        series_iterations=1,
                        timer_option=BeltVibrationTimerOption.RESET_TIMER,
                        exclusive_channel=False,
                        clear_other_channels=False
                    )

        #input('Press Enter to indicate you have grasped the object')

        print('Press mouse button to indicate that the object was grasped')

        with Listener(on_click=on_click) as mouse_listener:
            mouse_listener.join()

        grasp = True

        return True, True, grasp, False, False
    
    if bbox_hand == None and bbox_obj == None:

        if look_hand == False and look_obj == False:

            belt_controller.stop_vibration()

            #down
            belt_controller.send_pulse_command(
                        channel_index=0,
                        orientation_type=BeltOrientationType.ANGLE,
                        orientation=60,
                        intensity=vibration_intensity,
                        on_duration_ms=250,
                        pulse_period=500,
                        pulse_iterations=3,
                        series_period=5000,
                        series_iterations=1,
                        timer_option=BeltVibrationTimerOption.RESET_TIMER,
                        exclusive_channel=False,
                        clear_other_channels=False
                    )
            
            look_hand, look_obj = True, True
            
        return False, False, grasp, look_hand, look_obj
    
    # if you cannot see the hand but the object is visible, tell them to move the hand around
    if bbox_hand == None and bbox_obj != None:
            
        if look_hand == False:

            belt_controller.stop_vibration()

            #right
            belt_controller.send_pulse_command(
                        channel_index=0,
                        orientation_type=BeltOrientationType.ANGLE,
                        orientation=120,
                        intensity=vibration_intensity,
                        on_duration_ms=250,
                        pulse_period=500,
                        pulse_iterations=3,
                        series_period=5000,
                        series_iterations=1,
                        timer_option=BeltVibrationTimerOption.RESET_TIMER,
                        exclusive_channel=False,
                        clear_other_channels=False
                    )
            
            look_hand = True
        
        return False, False, grasp, look_hand, False
    
    # if you can see the hand but not the object and are not lined up for a grasp, look around for the object
    if bbox_hand != None and bbox_obj == None:
        # if not mock_belt:
        # if look_obj == False:

        #     belt_controller.stop_vibration()

        #     #left
        #     belt_controller.send_pulse_command(
        #                 channel_index=0,
        #                 orientation_type=BeltOrientationType.ANGLE,
        #                 orientation=45,
        #                 intensity=vibration_intensity,
        #                 on_duration_ms=250,
        #                 pulse_period=500,
        #                 pulse_iterations=3,
        #                 series_period=5000,
        #                 series_iterations=1,
        #                 timer_option=BeltVibrationTimerOption.RESET_TIMER,
        #                 exclusive_channel=False,
        #                 clear_other_channels=False
        #             )
            
        #     look_obj = True
        
        return False, False, grasp, False, look_obj

    # This will be adjusted in within if-loop
    x_threshold = 50
    y_threshold = 50

    if bbox_hand != None and bbox_obj != None:

        # Getting horizontal and vertical position of the bounding box around target object and hand
        x_center_hand, y_center_hand = bbox_hand[0], bbox_hand[1]
        y_center_hand = bbox_hand[1] - (bbox_hand[3] / 4)
        x_center_obj, y_center_obj = bbox_obj[0], bbox_obj[1]

        # if not mock_belt:
        belt_controller.stop_vibration()

        # Vertical movement logic
        # Centers of the hand and object bounding boxes further away than y_threshold - move hand vertically
        if abs(y_center_hand - y_center_obj) > y_threshold:
            if y_center_hand < y_center_obj:
                print('down')
                #if not mock_belt:
                belt_controller.vibrate_at_angle(60, channel_index=0, intensity=vibration_intensity)
            elif y_center_hand > y_center_obj:
                print('up')
                #if not mock_belt:
                belt_controller.vibrate_at_angle(90, channel_index=0, intensity=vibration_intensity)
                
        else:
            vertical = True

        # Horizontal movement logic
        # Centers of the hand and object bounding boxes further away than x_threshold - move hand horizontally
        if abs(x_center_hand - x_center_obj) > x_threshold:
            if x_center_hand < x_center_obj:
                print('right')
                #if not mock_belt:
                belt_controller.vibrate_at_angle(120, channel_index=0, intensity=vibration_intensity)
            elif x_center_hand > x_center_obj:
                print('left')
                #if not mock_belt:
                belt_controller.vibrate_at_angle(45, channel_index=0, intensity=vibration_intensity)
        else:
            horizontal = True

        return horizontal, vertical, grasp, False, False