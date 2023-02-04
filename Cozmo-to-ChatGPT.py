import string
import sys
import cozmo
from cozmo.util import degrees, speed_mmps, distance_mm
import openai
import re
import datetime
import random
import azure.cognitiveservices.speech as speechsdk
import keyboard
import asyncio
import time
#import os
from api_secrets import API_KEY, SPEECH_KEY, SPEECH_REGION
from character_prompts import cozmo_prompt, hal_prompt, kitt_prompt, jarvis_prompt

# Set Debug mode on or off
Viewer = False
Viewer3d = False

# Speech to Text mode and PTT on/off #
ptt = False
longspeech = True

#Streamlit or viewer
if Viewer == False:
    import streamlit as st

# Set Defult Locale
locale = 'en-US'

# Set the API key for OpenAI
openai.api_key = API_KEY

# Chose character and define name + starting prompt #
character = 'Cozmo'

# Cozmo
if character == 'Cozmo':
    character_name = 'Cozmo'
    your_name = 'Human'
    cozmo_voice = True
    voice_speed = 0.7
    start_prompt = cozmo_prompt
    wakeup_sequence = 'ConnectWakeUp'
    goodnight_sequence = 'CodeLabSleep'
    character_temp = 0.9
    startup_text = 'Good morning, Human.'
    driving_anim = True

# HAL 9000
elif character == 'HAL':
    character_name = 'HAL 9000'
    your_name = 'Dave'
    cozmo_voice = False
    voice_speed = 0.5
    start_prompt = hal_prompt
    wakeup_sequence = 'DroneModeIdle' 
    goodnight_sequence = 'AcknowledgeFaceInitPause'
    character_temp = 0.9
    startup_text = 'Good morning, Dave.'
    driving_anim = False

# KITT
elif character == 'KITT':
    character_name = 'KITT'
    your_name = 'Michael Knight'
    cozmo_voice = False
    voice_speed = 0.5
    start_prompt = kitt_prompt
    wakeup_sequence = 'DroneModeIdle'
    goodnight_sequence = 'AcknowledgeFaceInitPause'
    character_temp = 0.9
    startup_text = 'Good morning, Michael.'
    driving_anim = False

# Jarvis
elif character == 'Jarvis':
    character_name = 'Jarvis'
    your_name = 'Tony'
    cozmo_voice = False
    voice_speed = 0.5
    start_prompt = jarvis_prompt
    wakeup_sequence = 'DroneModeIdle'
    goodnight_sequence = 'AcknowledgeFaceInitPause'
    character_temp = 0.9
    startup_text = 'Good morning, Tony.'
    driving_anim = False

# Wrong name in character variable
else:
    print("Invalid character.")

# AUXILIARY FUNCTIONS #

# Start Speech API using environment variables "SPEECH_KEY" and "SPEECH_REGION"
speech_config = speechsdk.SpeechConfig(subscription = SPEECH_KEY, region = SPEECH_REGION)

def recognize_from_microphone_short(locale_code):
    global ptt
    speech_config.speech_recognition_language = locale_code

    audio_config = speechsdk.audio.AudioConfig(use_default_microphone = True)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config = speech_config, audio_config = audio_config)

    if (ptt == True):
        # Print a message asking the user to press the spacebar to start speaking if PTT is active
        print("Press the spacebar to start speaking in your microphone.")
        st.markdown('<strong><font color="orange">Press Spacebar to speak</font></strong>\n', unsafe_allow_html = 1)
        # Wait for the spacebar to be pressed 
        keyboard.wait('space')

    st.markdown('<strong><font color="green">Speak now!</font></strong>\n', unsafe_allow_html = 1)
    print("Speak in your microphone.")
    speech_recognition_result = speech_recognizer.recognize_once_async().get()

    if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
        print("Recognized: {}".format(speech_recognition_result.text))
        return format(speech_recognition_result.text)
    elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
        print("No speech could be recognized: {}".format(speech_recognition_result.no_match_details))
    elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_recognition_result.cancellation_details
        print("Speech Recognition canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print("Error details: {}".format(cancellation_details.error_details))
            print("Did you set the speech resource key and region values?")

def recognize_from_microphone(locale_code):
    speech_config.speech_recognition_language = locale_code

    audio_config = speechsdk.audio.AudioConfig(use_default_microphone = True)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config = speech_config, audio_config = audio_config)
    
    all_results = []

    def handle_final_result(evt):
        all_results.append(evt.result.text)

    def print_partial(evt):
        print(evt.result.text)
    
    speech_recognizer.recognizing.connect(print_partial)
    speech_recognizer.recognized.connect(handle_final_result)
    speech_recognizer.start_continuous_recognition()
    
    while True:
        if keyboard.is_pressed("space"):
            speech_recognizer.stop_continuous_recognition()
            return ' '.join(all_results)

        if keyboard.is_pressed("backspace"):
            speech_recognizer.stop_continuous_recognition()
            print(">>> VOICE RECOGNITION CANCELED, START OVER <<<")
            return ''

        time.sleep(0.01)

def extract_commands(string):
    # Put a space in front of the commands in case Cozmo forgets
    string = string.replace("--", " --").rstrip('.,;:')
    commands = []
    # Split the string by spaces
    words = string.split(" ")
    for word in words:
        # Remove leading and trailing spaces from the word
        word = word.strip()
        # If the first character of the word is '--', then it is a command
        if word[:2] == "--":
            commands.append(word)
    return commands

def remove_commands(string):
    # Channge AI to A.I.
    string = string.replace(" AI ", " A.I. ")
    # Put a space in front of the commands in case Cozmo forgets
    string = string.replace("--", " --")
    # Split string at spaces
    words = string.split(" ")
    # Remove commands from the list of words
    words = [word for word in words if word[:2] != "--"]
    # Join the remaining words into a new string
    return " ".join(words)

class BlinkyCube(cozmo.objects.LightCube):
    '''Subclass LightCube and add a light-chaser effect.'''
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._chaser = None

    def start_light_chaser(self):
        '''Cycles the lights around the cube with 1 corner lit up blue,
        changing to the next corner every 0.1 seconds.
        '''
        if self._chaser:
            raise ValueError("Light chaser already running")
        async def _chaser():
            while True:
                for i in range(4):
                    cols = [cozmo.lights.off_light] * 4
                    cols[i] = cozmo.lights.blue_light
                    self.set_light_corners(*cols)
                    await asyncio.sleep(0.1, loop=self._loop)
        self._chaser = asyncio.ensure_future(_chaser(), loop=self._loop)

    def stop_light_chaser(self):
        if self._chaser:
            self._chaser.cancel()
            self._chaser = None

# Make sure World knows how to instantiate the subclass
cozmo.world.World.light_cube_factory = BlinkyCube

async def kitt_lights(robot: cozmo.robot.Robot):
    outer_left_light = cozmo.lights.off_light
    left_light = cozmo.lights.off_light
    middle_light = cozmo.lights.off_light
    right_light = cozmo.lights.off_light
    outer_right_light = cozmo.lights.off_light

    while True:
        robot.set_backpack_lights(outer_left_light, left_light, middle_light, right_light, outer_right_light)
        left_light = cozmo.lights.Light(on_color=cozmo.lights.red, on_period_ms=500, off_period_ms=500, transition_off_period_ms=150, transition_on_period_ms=150)
        middle_light = cozmo.lights.off_light
        right_light = cozmo.lights.off_light
        await asyncio.sleep(0.7)

        robot.set_backpack_lights(outer_left_light, left_light, middle_light, right_light, outer_right_light)
        left_light = cozmo.lights.off_light
        middle_light = cozmo.lights.Light(on_color=cozmo.lights.red, on_period_ms=500, off_period_ms=500, transition_off_period_ms=150, transition_on_period_ms=150)
        right_light = cozmo.lights.off_light
        await asyncio.sleep(0.7)

        robot.set_backpack_lights(outer_left_light, left_light, middle_light, right_light, outer_right_light)
        left_light = cozmo.lights.off_light
        middle_light = cozmo.lights.off_light
        right_light = cozmo.lights.Light(on_color=cozmo.lights.red, on_period_ms=500, off_period_ms=500, transition_off_period_ms=150, transition_on_period_ms=150)
        await asyncio.sleep(0.7)

        robot.set_backpack_lights(outer_left_light, left_light, middle_light, right_light, outer_right_light)
        left_light = cozmo.lights.off_light
        middle_light = cozmo.lights.Light(on_color=cozmo.lights.red, on_period_ms=500, off_period_ms=500, transition_off_period_ms=150, transition_on_period_ms=150)
        right_light = cozmo.lights.off_light
        await asyncio.sleep(0.7)

# Streamlit title
if Viewer == False:
    st.title('Chat with ' + character_name + '!')
    st.markdown('<strong><font color="yellow">Wait for the "Press Spacebar to speak" indication to interact with ' + character_name + '.</font></strong>\n', unsafe_allow_html = 1)

# Define the main Program
def cozmo_GPT(robot: cozmo.robot.Robot):

    # Set camera to color
    robot.camera.color_image_enabled = True

    # INTERNAL FUNCTIONS #

    # Face Finder
    def facefinder():
        # Start searching for a face
        time.sleep(0.5)
        lookaround= robot.start_behavior(cozmo.behavior.BehaviorTypes.FindFaces)
        if Viewer == False:
            st.markdown('<strong><font color="cyan">' + character_name + ' is looking for your face...</font></strong>\n', unsafe_allow_html = 1)

        face_to_follow = None

        while True:
            turn_action = None
            if face_to_follow:
                # stop search and start turning towards the face
                lookaround.stop()
                turn_action = robot.turn_towards_face(face_to_follow)
                if Viewer == False:
                    st.markdown('<strong><font color="green">' + character_name + ' found your face</font></strong>\n', unsafe_allow_html = 1)
                time.sleep(2)
                return

            if not (face_to_follow and face_to_follow.is_visible):
                # find a visible face, timeout if nothing found after a short while
                try:
                    face_to_follow = robot.world.wait_for_observed_face(timeout=10)
                except asyncio.TimeoutError:
                    if Viewer == False:
                        st.markdown('<strong><font color="red">' + character_name + ' Did not find your face. Ask "Look at me" to try again.</font></strong>\n', unsafe_allow_html = 1)
                    lookaround.stop()
                    time.sleep(0.3)
                    robot.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE).wait_for_completed()
                    return

            if turn_action:
                # Complete the turn action if one was in progress
                turn_action.wait_for_completed()

            time.sleep(.1)

    # Character Light system and expressin init
    def character_lights():
        if character_name == 'Cozmo':
            robot.set_all_backpack_lights(cozmo.lights.Light(on_color=cozmo.lights.white))
        
        if character_name == 'KITT':
            #asyncio.create_task(kitt_lights(robot))
            robot.set_center_backpack_lights(cozmo.lights.Light(on_color=cozmo.lights.red, on_period_ms=500, off_period_ms=500, transition_off_period_ms=150, transition_on_period_ms=150))
        
        if character_name == 'HAL 9000':
            robot.set_all_backpack_lights(cozmo.lights.Light(on_color=cozmo.lights.red))

        if character_name == 'Jarvis':
            robot.set_center_backpack_lights(cozmo.lights.Light(on_color=cozmo.lights.green, on_period_ms=500, off_period_ms=500, transition_off_period_ms=150, transition_on_period_ms=150))

    def writelog(logline):
        now = datetime.datetime.now()
        date_time_string = now.strftime("%B %d, %Y %H:%M:%S")
        with open("log.txt", "a") as file:
            # Write the contents to the file
            if logline == '\n-----------------------------------------------------------------------------------------------\n\n':
                file.write(str(logline + date_time_string + ' > NEW '+ character_name.upper() +' CONVERSATION LOG:\n'))
            else:
                #file.write(str('\n' + date_time_string + ' > ' + logline))
                if logline.startswith('\n'):
                    logline = logline[1:]
                file.write(str('\n' + logline))

    def getcube():
        robot.set_lift_height(0.0).wait_for_completed()
        robot.set_head_angle(degrees(0)).wait_for_completed()

        # look around and try to find a cube
        look_around = robot.start_behavior(cozmo.behavior.BehaviorTypes.LookAroundInPlace)

        cube = None

        try:
            cube = robot.world.wait_for_observed_light_cube(timeout=5)
            print("Found cube: %s" % cube)
        except asyncio.TimeoutError:
            print("Didn't find a cube")
            look_around.stop()
            if character_name == "HAL 9000":
                robot.say_text('No asteroids found in the area, all clear.', play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=voice_speed, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()
            if character_name == "KITT":
                robot.say_text('No suspicious activity found.', play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=voice_speed, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()
            if character_name == "Cozmo":
                robot.say_text("I can't see any cube!", play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=voice_speed, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()
            if character_name == "Jarvis":
                robot.say_text("The ARC reactor is not in this area, Tony.", play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=voice_speed, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()
        finally:
            # whether we find it or not, we want to stop the behavior
            time.sleep(0.3)
            look_around.stop()

        if cube:
            print("Cozmo found a cube")
            cube.start_light_chaser()
            if character_name == "HAL 9000":
                robot.say_text('Asteroid found, getting closer to investigate.', play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=voice_speed, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()
            if character_name == "KITT":
                robot.say_text('Suspicious activity found. Investigating.', play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=voice_speed, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()
            if character_name == "Cozmo":
                robot.say_text("Cube found!", play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=voice_speed, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()
            if character_name == "Jarvis":
                robot.say_text("ARC reactor found!", play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=voice_speed, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()
            # Cozmo will approach the cube he has seen
            #action = robot.go_to_object(cube, distance_mm(5.0))
            #action.wait_for_completed()
            action = robot.roll_cube(cube, check_for_object_on_top=True, num_retries=5)
            action.wait_for_completed()
            print("Completed action: result = %s" % action)
            if character_name == "HAL 9000":
                robot.say_text('Scan complete. No anomalies found. Going back to normal operation', play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=voice_speed, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()
            if character_name == "KITT":
                robot.say_text('Nothing to report.', play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=voice_speed, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()
            if character_name == "Cozmo":
                robot.say_text("I love my cubes!", play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=voice_speed, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()
            if character_name == "Jarvis":
                robot.say_text("Arc reactor activated!", play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=voice_speed, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()
            time.sleep(0.3)
            robot.drive_straight(distance_mm(-100), speed_mmps(70), should_play_anim=False).wait_for_completed()
            cube.stop_light_chaser()
            cube.set_lights_off()
    
    def docking():
        robot.set_lift_height(0.0).wait_for_completed()
        robot.set_head_angle(degrees(0)).wait_for_completed()

        # look around and try to find a cube
        look_around = robot.start_behavior(cozmo.behavior.BehaviorTypes.LookAroundInPlace)

        try:
            cube = robot.world.wait_for_observed_light_cube(timeout=30)
            print("Found cube: %s" % cube)
        except asyncio.TimeoutError:
            print("Didn't find a cube")
        finally:
            # whether we find it or not, we want to stop the behavior
            look_around.stop()

        print("Cozmo found a cube, and will now attempt to dock with it:")
        cube.start_light_chaser()
        # Cozmo will approach the cube he has seen
        action = robot.dock_with_cube(cube, approach_angle=cozmo.util.degrees(0), num_retries=2)
        action.wait_for_completed()
        print("result:", action.result)
        robot.set_lift_height(1.0).wait_for_completed()
        if Viewer == False:
            st.markdown("'Docking Complete")
        robot.say_text('Docking Complete!', play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=voice_speed, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()
        robot.set_lift_height(0.0).wait_for_completed()
        robot.drive_straight(distance_mm(-100), speed_mmps(70), should_play_anim=False).wait_for_completed()
        cube.stop_light_chaser()
        cube.set_lights_off()

    def boost():
        # Move lift down and tilt the head up
        robot.set_lift_height(0.0).wait_for_completed()
        robot.set_head_angle(degrees(0)).wait_for_completed()
        time.sleep(0.3)

        # look around and try to find a cube
        look_around = robot.start_behavior(cozmo.behavior.BehaviorTypes.LookAroundInPlace)

        cube = None

        try:
            cube = robot.world.wait_for_observed_light_cube(timeout=30)
            print("Found cube: %s" % cube)
        except asyncio.TimeoutError:
            print("Didn't find a cube")
        finally:
            # whether we find it or not, we want to stop the behavior
            look_around.stop()

        if cube:
            cube.start_light_chaser()
            action = robot.pop_a_wheelie(cube, num_retries=2)
            action.wait_for_completed()
            print("Completed action: result = %s" % action)
            cube.stop_light_chaser()
            cube.set_lights_off()

    # Interpret commands sent by Cozmo
    def character_commands(command, cleanreply='', animation=driving_anim):
        
        # Laugh
        if command.rstrip(string.punctuation) == '--La':
            robot.play_anim(name = 'anim_poked_giggle').wait_for_completed()
            time.sleep(0.3)
            robot.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE).wait_for_completed()
            if Viewer == False:
                st.markdown('\n'+ character_name +': ' + "** laughs **")
        
        # Cry
        if command.rstrip(string.punctuation) == '--Cr':
            robot.play_anim_trigger(cozmo.anim.Triggers.MemoryMatchPlayerLoseHandSolo, ignore_body_track=False, in_parallel=False).wait_for_completed()
            time.sleep(0.3)
            robot.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE).wait_for_completed()
            if Viewer == False:
                st.markdown('\n'+ character_name +': ' + "** cries **")

        # Fun
        if command.rstrip(string.punctuation) == '--Fu':
            robot.play_anim_trigger(cozmo.anim.Triggers.PeekABooGetOutHappy, ignore_body_track=False, in_parallel=False).wait_for_completed()
            time.sleep(0.3)
            robot.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE).wait_for_completed()
            if Viewer == False:
                st.markdown('\n'+ character_name +': ' + "** has fun **")

        # Sad
        if command.rstrip(string.punctuation) == '--Sa':
            robot.play_anim_trigger(cozmo.anim.Triggers.CodeLabLose, ignore_body_track=False, in_parallel=False).wait_for_completed()
            robot.turn_in_place(degrees(-65)).wait_for_completed()
            time.sleep(0.3)
            robot.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE).wait_for_completed()
            if Viewer == False:
                st.markdown('\n'+ character_name +': ' + "** is sad **")

        # Scared
        if command.rstrip(string.punctuation) == '--Sc':
            robot.play_anim_trigger(cozmo.anim.Triggers.CodeLabScaredCozmo, ignore_body_track=False, in_parallel=False).wait_for_completed()
            time.sleep(0.3)
            robot.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE).wait_for_completed()
            if Viewer == False:
                st.markdown('\n'+ character_name +': ' + "** is scared **")
        
         # Possessed
        if command.rstrip(string.punctuation) == '--Po':
            if random.random() < 0.33:
                robot.play_anim_trigger(cozmo.anim.Triggers.CodeLabZombie, ignore_body_track=False, in_parallel=False).wait_for_completed()
            
            robot.set_lift_height(0.0).wait_for_completed()
            robot.set_lift_height(1.0).wait_for_completed()
            time.sleep(0.2)
            robot.drive_wheel_motors(-70, -20)
            time.sleep(0.3)
            # Cozmo speaks the reply with possessed voice (Cozmo's answers are truncated to 245 characters to avoid errors)
            robot.say_text(cleanreply[:245], play_excited_animation=False, use_cozmo_voice=False, duration_scalar=0.7, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()
            time.sleep(0.2)
            robot.stop_all_motors()
            time.sleep(0.2)
            robot.set_head_angle('MAX_HEAD_ANGLE').wait_for_completed()
            time.sleep(0.2)
            robot.set_lift_height(0.0).wait_for_completed()
            time.sleep(0.2)
            robot.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE).wait_for_completed()
            if Viewer == False:
                st.markdown('\n'+ character_name +': ' + "** needs an exorcism **")

        # Change language locale
        if command.rstrip(string.punctuation).startswith('--Lo'):
            subcommands = command.rstrip(string.punctuation).split("_")
            if len(subcommands) > 1:
                global locale
                locale = subcommands[1]
        
        # Head Up
        if command.rstrip(string.punctuation) == ('--H_u'):
            robot.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE).wait_for_completed()
        
        # Head Down
        if command.rstrip(string.punctuation) == ('--H_d'):
            robot.set_head_angle(cozmo.robot.MIN_HEAD_ANGLE).wait_for_completed()

        # Forklift Up
        if command.rstrip(string.punctuation) == ('--Fl_u'):
            robot.set_lift_height(1.0).wait_for_completed()
        
        # Forklift Down
        if command.rstrip(string.punctuation) == ('--Fl_d'):
            robot.set_lift_height(0.0).wait_for_completed()

        # Fwd Motion
        if command.rstrip(string.punctuation).startswith('--DF'):
            subcommands = command.rstrip(string.punctuation).split("_")
            if len(subcommands) > 1:
                distance = int(subcommands[1])
                speed = int(subcommands[2])
                robot.drive_straight(distance_mm(distance), speed_mmps(speed), should_play_anim=animation).wait_for_completed()
                time.sleep(0.3)
                robot.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE).wait_for_completed()

        # Rwd Motion
        if command.rstrip(string.punctuation).startswith('--DB'):
            subcommands = command.rstrip(string.punctuation).split("_")
            if len(subcommands) > 1:
                distance = int(subcommands[1].replace(".", "").replace('"', "").replace("'", ""))
                speed = int(subcommands[2].replace(".", "").replace('"', "").replace("'", ""))
                robot.drive_straight(distance_mm(-distance), speed_mmps(speed), should_play_anim=animation).wait_for_completed()
                time.sleep(0.3)
                robot.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE).wait_for_completed()

        # Steering                                     
        if command.rstrip(string.punctuation).startswith('--ST'):
            subcommands = command.rstrip(string.punctuation).split("_")
            if len(subcommands) > 1:
                degreez = -(int(subcommands[1].replace(".", "").replace('"', "").replace("'", "")))
                robot.turn_in_place(degrees(degreez)).wait_for_completed()
                time.sleep(0.3)
                robot.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE).wait_for_completed()

        # Turbo Boost
        if command.rstrip(string.punctuation) == '--Boost':
            boost()
            if Viewer == False:
                st.markdown('\n'+ character_name +': ' + "** uses Turbo Boost **")

        # Look for object
        if command.rstrip(string.punctuation) == '--Ro':
            getcube()
            if Viewer == False:
                st.markdown('\n'+ character_name +': ' + "** is looking for objects **")

         # Dock with cube
        if command.rstrip(string.punctuation) == '--Do':
            docking()
            if Viewer == False:
                st.markdown('\n'+ character_name +': ' + "** is docking **")
        
        # Battery voltage
        if command.rstrip(string.punctuation) == '--Bat':
            batt = str(round(robot.battery_voltage, 2))
            if Viewer == False:
                st.markdown(' ' + batt + "V")
            robot.say_text(batt + ' volts', play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=voice_speed, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()
    
    # END OF INTERNAL FUNCTIONS #

    # Initialize the new conversation Log in txt file
    writelog('\n-----------------------------------------------------------------------------------------------\n\n')

    # Set character lights, robot expression, and move fork down
    robot.set_lift_height(0.0).wait_for_completed()
    robot.play_anim_trigger(cozmo.anim.Triggers.ConnectWakeUp, ignore_body_track=False, in_parallel=False).wait_for_completed()
    character_lights()

    # Find a face to start
    facefinder()

    # Introduction speech
    #robot.say_text(startup_text, play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=voice_speed, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()
    #if Viewer == False:
        #st.markdown(character_name + ': ' + startup_text)

    # First instructions to pass to GPT-3 to impersonate the chosen character
    conversation_history = start_prompt

    # GPT-3 send first prompt
    gptresponse = openai.Completion.create(
                                    engine = "text-davinci-003",
                                    prompt = conversation_history,
                                    temperature = character_temp,
                                    max_tokens = 120,
                                    top_p = 0.2,
                                    frequency_penalty = 0,
                                    presence_penalty = 0.6)         

    # Get reply
    reply = gptresponse['choices'][0]['text'].replace("--", " --")

    # Remove commands from reply
    cleanreply = remove_commands (reply)

    # Add the new chunk of conversation to the conversation history to make GPT-3 have a memory of the past conversation
    conversation_history += '\n' + reply

    # Add the new chunk of conversation to the log
    writelog(reply)
    
    # Write reply in Srteamlit
    if Viewer == False:
        st.markdown('\n' + cleanreply)

    trimmer = int(len(character_name)+2)

    # Cozmo speaks out his clean reply (Cozmo's answers are truncated to 245 characters to avoid errors)
    robot.say_text(cleanreply[trimmer:245], play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=voice_speed, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()

    # Interpret Cozmo's commands
    commands = extract_commands(reply)
    for command in commands:
        character_commands(command)

    #Conversation main loop
    print('\n > ' + character_name + ' starts listening here...')
    while True:
        if longspeech == False:
            humanresponse = recognize_from_microphone_short(locale)
        else:
            humanresponse = recognize_from_microphone(locale)

        # No silence from Human, go on
        if humanresponse != '':

            #Change names in human response
            if character_name == 'Cozmo':
                humanresponse = re.sub("cosmo", "Cozmo", humanresponse, re.IGNORECASE)
            if character_name == 'HAL 9000':
                humanresponse = re.sub("Al", "HAL", humanresponse, re.IGNORECASE)
            if character_name == 'KITT':
                humanresponse = re.sub("kid", "KITT", humanresponse, re.IGNORECASE)
            
            # Initialize the Command variable, if 1 don't pass the text to GPT-3 but use it as a direct command from Human
            command = 0

            # COMMANDS FROM HUMAN #

            # Terminate conversation and send Cozmo to sleep
            if (humanresponse.lower().find('good night') != -1) or (humanresponse.lower().find('goodnight') != -1):
                writelog("STOP requested by user")
                if character_name == 'Cozmo':
                    goodnight = "Good night to you, my human friend..."
                    robot.say_text(goodnight, play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=voice_speed, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()
                
                if character_name == 'HAL 9000':
                    goodnight = "Dave, please do not deactivate me..."
                    robot.say_text(goodnight, play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=voice_speed, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()
                    goodnight = "Dave, please reconsider... "
                    robot.say_text(goodnight, play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=1, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()
                    goodnight = "Dave... please..."
                    robot.say_text(goodnight, play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=1.5, voice_pitch=-500, in_parallel=False, num_retries=0).wait_for_completed()
                    goodnight = "Dave"
                    robot.say_text(goodnight, play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=2, voice_pitch=-1000, in_parallel=False, num_retries=0).wait_for_completed()
                
                if character_name == 'KITT':
                    goodnight = 'See you on the next mission, Michael!'
                    robot.say_text(goodnight, play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=voice_speed, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()

                if character_name == 'Jarvis':
                    goodnight = 'See you on the next Avengers mission, Tony!'
                    robot.say_text(goodnight, play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=voice_speed, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()
                  
                robot.play_anim_trigger(getattr(cozmo.anim.Triggers,goodnight_sequence), ignore_body_track=False, in_parallel=False).wait_for_completed()
                
                if Viewer == False:
                    st.stop()
                sys.exit()

            # Look for the human's face
            if (humanresponse.lower().find('look at me') != -1):
                facefinder()

            # No commands found, pass conversation to GPT-3
            if (command == 0):

                # Add Human input to GPT-3 history and log
                conversation_history += your_name + ": " + humanresponse + "~ \n"
                writelog(your_name + ": " + humanresponse)

                # Print Human's response
                print('\n' + your_name + ': ' + humanresponse)
                if Viewer == False:
                    st.markdown(your_name + ": " + humanresponse)

                # Pass the new history with added Human reply to GPT-3
                gptresponse = openai.Completion.create(
                                engine = "text-davinci-003",
                                prompt = conversation_history,
                                temperature = character_temp,
                                max_tokens = 120,
                                top_p = 0.2,
                                frequency_penalty = 0,
                                presence_penalty = 0.6,
                                stop=["~"]
                                )

                # Get the response from GPT-3 and clean it, also removing "Cozmo: " if present
                reply = gptresponse['choices'][0]['text'].replace("--", " --")

                cleanreply = remove_commands (reply)

                # If reply is not empty
                if reply != '':

                    # Update conversation and log
                    #conversation_history += "\n" + character_name + ": " + cleanreply
                    conversation_history += reply
                    writelog(reply)

                    # Print clean reply in Streamlite
                    if cleanreply.strip() != '':
                        if Viewer == False:
                            st.markdown('\n' + cleanreply)

                    # Cozmo replies before the commands
                    if not reply.lstrip().startswith("--") and not reply.lstrip().startswith("--Po") and not "--Po" in reply:

                        # Cozmo speaks the reply before commands (Cozmo's answers are truncated to 245 characters to avoid errors)
                        robot.say_text(cleanreply[trimmer:245], play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=voice_speed, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()

                    # If part of the message is possessed split it up
                    if not reply.lstrip().startswith("--Po") and "--Po" in reply:
                        parts = reply.split('--Po')
                        cleanreply = parts[0]
                        # Cozmo speaks the first part of the reply with his voice
                        robot.say_text(cleanreply[trimmer:245], play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=voice_speed, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()
                        # The possessed part is passed to the commands function
                        possessedreply = remove_commands (parts[1])
                        character_commands("--Po", possessedreply)

                    # If the possessed command is at the beginngin just pass the cleantext to the command function to change voice
                    if reply.lstrip().startswith("--Po"):
                        character_commands("--Po", cleanreply)

                    # Do commands and print them
                    commands = extract_commands(reply)
                    print(f"> Commands: {commands}")

                    for command in commands:
                        character_commands(command)

                    if len(commands) > 0:
                        # Reset lights to character standard and look again for a face
                        character_lights()
                        #facefinder()

                    # Cozmo replies after commands
                    if reply.lstrip().startswith("--") and not reply.startswith("--Po") and not "--Po" in reply:

                        # Cozmo speaks the reply after commands (Cozmo's answers are truncated to 245 characters to avoid errors)
                        robot.say_text(cleanreply[trimmer:245], play_excited_animation=False, use_cozmo_voice=cozmo_voice, duration_scalar=voice_speed, voice_pitch=-100, in_parallel=False, num_retries=0).wait_for_completed()
                                  
                # Reply is empty        
                else:
                    reply = '** ' + character_name + ' is silent **'
                    writelog(character_name + ": " + reply)
                    if Viewer == False:
                        st.markdown(reply)

cozmo.run_program(cozmo_GPT, use_3d_viewer = Viewer3d, use_viewer = Viewer, force_viewer_on_top = True)