# CozmoGPT
 Giving a GPT-3 Brain to a little buddy robot

 # Notes
 This is a work in progress.
 This version of the program, with the actual Azure servcies configuration, works only on Windows.

 The program can be started from inside the relative folder with or without Streamlit support uning the Start_Streamlit.bat or Start.bat batch files respectively. Since I used an Android tablet during development, in the batch file there is a command to start the ADB server.

 If Streamlit is used, it's suggested to keep the Terminal also open somewhere on the screen to check for speech recognition accuracy and system messages.

# Instructions
 1) Install ADB if you are using a Android device to run the Cozmo app (https://developer.android.com/studio/command-line/adb)
 2) Create a Speech service in your Microsoft Azure control panel
 3) Add your OpenAI API key, Azure speech services API key and server region in api_secrets.py
 4) Choose the character you want to use in line 36 of Cozmo-to-ChatGPT.py (default character = 'Cozmo')
 5) Choose if you want to use the Cozmo 2D/3D viewer (requires the installation of the viewer separately and freeglut.dll 64 bit in the Windows/System32 folder). Default is Viewer = False and Viewer3d = False (lines 18 and 19). If using the viewer or 3D viewer start the program withtout Streamlit (using Start.bat)

# Speech recognition
 With the default options "ptt = False" and "longspeech = True" (lines 22, 23 of Cozmo-to-ChatGPT.py), after the first initialization and introduction message from Cozmo, the speech recognition system is constanlty listening and in the terminal the partial parts of the dialog are transcribed in real time. Pressing SPACEBAR, you close that part of the message and send it to the OpenAI API. If you change your mind, you can press BACKSPACE to reset the message and start over.

# Copyright
 Concept, code and prompts, and all the content of this repository are copyright Ⓒ 2023 Giuliano Golfieri, all rights reserved.
 Please do not share this code without written authorization by the owner.