import time
from pybelt.belt_controller import (BeltConnectionState, BeltController,
                                    BeltControllerDelegate, BeltMode,
                                    BeltOrientationType,
                                    BeltVibrationTimerOption)

from auto_connect import interactive_belt_connect, setup_logger

import threading
import sys

from pynput.keyboard import Key, Listener


# Variable that determines if belt is connected
# If belt is not connected value is set to 1 and instead of vibrations print commands serve as guidance
mock_belt = 0
vibration_intensity = 100
one_round = 0

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
        return False, belt_controller
    else:
        # Change belt mode to APP mode
        belt_controller.set_belt_mode(BeltMode.APP_MODE)
        return True, belt_controller

def navigate_hand(belt_controller,bboxs_hands,bboxs_objs, search_key_obj: str, search_key_hand: list, hor_correct: bool = False, ver_correct: bool = False, grasp: bool = False, obj_seen_prev: bool = False, search: bool = False, count_searching: int = 0, count_see_object: int = 0, jitter_guard: int=0, navigating: bool = False):
    
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
    global mock_belt, one_round

    horizontal, vertical = False, False

    max_hand_confidence = 0
    max_obj_confidence = 0
    
    # Diffrence between the hand xy and object xy
    x_threshold = 50
    y_threshold = 50

    global termination_signal 
    termination_signal = False
    
    #print(bbox_info)

    bbox_hand, bbox_obj = None, None

    def abort(key):
        # Check if the pressed key is the left clicker key    
        if key == Key.page_up:
            sys.exit()

    def on_click(key):
        # Check if the pressed key is the right clicker key
        if key == Key.page_down:
            return False

    def listener():

        # listen for clicker
        with Listener(on_press=abort) as listener:
            listener.join()

    def start_listener():

        global termination_signal, one_round
        existing_thead = threading.enumerate()
        listener_thread = None

        for thread in existing_thead:
            if thread.name == 'clicker':
                listener_thread = thread
                termination_signal = False
                break
        
        if listener_thread is None:
            if one_round == 0:
                listener_thread = threading.Thread(target=listener, name='clicker')
                listener_thread.start()
                one_round += 1
            else:
                termination_signal = True
        
        return termination_signal

    termination_signal = start_listener()

    if termination_signal:
        print('Manual Abort')
        belt_controller.stop_vibration()
        sys.exit()

    # Search for object and hand with the highest prediction confidence
    for bbox in bboxs_hands:
        if bbox["class"] in search_key_hand and bbox["confidence"] > max_hand_confidence:
            bbox_hand = bbox.get("bbox")
            max_hand_confidence = bbox["confidence"]
            #print(f"hand confidence: {bbox['confidence']} \n")

    for bbox in bboxs_objs:
        if bbox["label"] == search_key_obj and bbox["confidence"] > max_obj_confidence:
            #print(f"label: {bbox['label']}")
            bbox_obj = bbox.get("bbox")
            max_obj_confidence = bbox["confidence"]
            #print(f"obj confidence: {bbox['confidence']} \n")

    # Getting horizontal and vertical position of the bounding box around tbarget object and hand
    if bbox_hand != None:

        x_center_hand, y_center_hand = bbox_hand[0], bbox_hand[1]
        y_center_hand = y_center_hand - (bbox_hand[3]/2)

    if bbox_obj != None:

        x_center_obj, y_center_obj = bbox_obj[0], bbox_obj[1]
 
    # Hand is detected, object is not detected, and they are aligned horizontally and vertically - send grasp command
    # Assumption: occlusion of the object by hand

    if bbox_hand != None and hor_correct and ver_correct:

        obj_seen_prev = False
        search = False
        count_searching = 0
        count_see_object = 0
        jitter_guard = 0
        navigating = 0

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
                        pulse_iterations=5,
                        series_period=5000,
                        series_iterations=1,
                        timer_option=BeltVibrationTimerOption.RESET_TIMER,
                        exclusive_channel=False,
                        clear_other_channels=False
                    )

        print('Please use the clicker to indicate you have grasped the object')

        # listen for clicker
        with Listener(on_press=on_click) as listener:
            listener.join()

        grasp = True

        return horizontal, vertical, grasp, obj_seen_prev, search, count_searching, count_see_object, jitter_guard, navigating
    
    # If the camera can see both hand and object but not yet aligned, navigate the hand to the object, horizontal first
    if bbox_hand != None and bbox_obj != None:

        obj_seen_prev = False
        search = False
        count_searching = 0
        count_see_object = 0
        jitter_guard = 0

        # if not mock_belt:
        #belt_controller.stop_vibration()

        if navigating == False:
            belt_controller.stop_vibration()

        # Horizontal movement logic
        # Centers of the hand and object bounding boxes further away than x_threshold - move hand horizontally
        if abs(x_center_hand - x_center_obj) > x_threshold:
            horizontal = False
            if x_center_hand < x_center_obj:
                print('right')
                #if not mock_belt:
                belt_controller.vibrate_at_angle(120, channel_index=0, intensity=vibration_intensity)
            elif x_center_hand > x_center_obj:
                print('left')
                #if not mock_belt:
                belt_controller.vibrate_at_angle(45, channel_index=0, intensity=vibration_intensity)

            navigating = True

        else:
            horizontal = True


        # Vertical movement logic
        # Centers of the hand and object bounding boxes further away than y_threshold - move hand vertically
        if horizontal == True:
            if abs(y_center_hand - y_center_obj) > y_threshold:
                vertical = False
                if y_center_hand < y_center_obj:
                    print('down')
                    #if not mock_belt:
                    belt_controller.vibrate_at_angle(60, channel_index=0, intensity=vibration_intensity)
                elif y_center_hand > y_center_obj:
                    print('up')
                    #if not mock_belt:
                    belt_controller.vibrate_at_angle(90, channel_index=0, intensity=vibration_intensity)

                navigating = True
                    
            else:
                vertical = True

        return horizontal, vertical, grasp, obj_seen_prev, search, count_searching, count_see_object, jitter_guard, navigating

    # if the camera cannot see the hand or the object, tell them they need to move around
    if bbox_obj == None and grasp == False:

        if obj_seen_prev == True:
            jitter_guard = 0 
            obj_seen_prev = False
        
        jitter_guard += 1

        if jitter_guard >= 40:
        
            count_see_object = 0 
            navigating = False

            #if not mock_belt:
            if search == False:

                    belt_controller.stop_vibration()

                    #left
                    belt_controller.send_pulse_command(
                                channel_index=0,
                                orientation_type=BeltOrientationType.ANGLE,
                                orientation=45,
                                intensity=vibration_intensity,
                                on_duration_ms=100,
                                pulse_period=500,
                                pulse_iterations=3,
                                series_period=5000,
                                series_iterations=1,
                                timer_option=BeltVibrationTimerOption.RESET_TIMER,
                                exclusive_channel=False,
                                clear_other_channels=False
                            )
                
                    search = True
                
            count_searching += 1

            if count_searching >= 150:
                search = False
                count_searching = 0
            
        return horizontal, vertical, grasp, obj_seen_prev, search, count_searching, count_see_object, jitter_guard, navigating
        
    # if the camera cannot see the hand but the object is visible, tell them to move the hand around
    if bbox_obj != None:

        if search == True:
            jitter_guard = 0
            search = False

        jitter_guard += 1

        if jitter_guard >= 40:
            
            navigating = False
            count_searching = 0
            
            if obj_seen_prev == False:

                belt_controller.stop_vibration()

                #down
                belt_controller.send_pulse_command(
                            channel_index=0,
                            orientation_type=BeltOrientationType.ANGLE,
                            orientation=120,
                            intensity=vibration_intensity,
                            on_duration_ms=100,
                            pulse_period=500,
                            pulse_iterations=3,
                            series_period=5000,
                            series_iterations=1,
                            timer_option=BeltVibrationTimerOption.RESET_TIMER,
                            exclusive_channel=False,
                            clear_other_channels=False
                        )
                
                obj_seen_prev = True
            
            count_see_object += 1

            if count_see_object >= 150:
                obj_seen_prev = False
                count_see_object = 0
        
        return horizontal, vertical, grasp, obj_seen_prev, search, count_searching, count_see_object, jitter_guard, navigating
    
    else:

        print('Condition not covered by logic. Maintaining variables and standing by.')

        return horizontal, vertical, grasp, obj_seen_prev, search, count_searching, count_see_object, jitter_guard, navigating

    
