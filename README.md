# CozmoGPT
 Giving a GPT-3 Brain to my little buddy robot.
 
 This software was developed as a personal project at the very early stages of ChatGPT (it uses GPT-3 API), mostly as a benchmark to put my prompting skills to test and understand the limits of the LLM technology. I was surprised by the outcome, so I created a TikTok channel about my smart little friend "CozmoGPT": https://www.tiktok.com/@cozmogpt
 
 As promised, when the main video of the channel reached 100K views and the account surpassed 1000 followers, I decided to publish the code.
 
 Lately, I have been very busy with a new drone startup, so I never took the time to update the code to move away from Microsoft Azure services (and use Whisper for voice recognition), give it vision (through the new GPT-4o model) and make it smarter. If you want to branch the repo and try it yourself please give it a go, I'll be happy to see the outcomes!

 # Notes
 This is a work in progress.
 This version of the program, with the actual Azure services configuration, works only on Windows.

The program can be started from inside the relative folder with or without Streamlit support using the Start_Streamlit.bat or Start.bat batch files respectively. Since I used an Android tablet during development, in the batch file there is a command to start the ADB server.

 If Streamlit is used, it's suggested to keep the Terminal also open somewhere on the screen to check for speech recognition accuracy and system messages.

# Instructions
 1) Install ADB if you are using an Android device to run the Cozmo app (https://developer.android.com/studio/command-line/adb)
 2) Create a Speech service in your Microsoft Azure control panel
 3) Add your OpenAI API key, Azure speech services API key, and server region in api_secrets.py
 4) Choose the character you want to use in line 36 of Cozmo-to-ChatGPT.py (default character = 'Cozmo')
 5) Choose if you want to use the Cozmo 2D/3D viewer (which requires the installation of the viewer separately and freeglut.dll 64 bit in the Windows/System32 folder). Default is Viewer = False and Viewer3d = False (lines 18 and 19). If using the viewer or 3D viewer start the program withtout Streamlit (using Start.bat)

# Speech recognition
 With the default options "ptt = False" and "longspeech = True" (lines 22, 23 of Cozmo-to-ChatGPT.py), after the first initialization and introduction message from Cozmo, the speech recognition system is constantly listening, and in the terminal the partial parts of the dialog are transcribed in real time. Pressing SPACEBAR, you acknowledge that part of the message and send it to the OpenAI API. If you change your mind, you can press BACKSPACE to reset the message and start over.

# Copyright
Concept, code and prompts, and all the content of this repository are copyright Ⓒ 2023-2024 Giuliano Golfieri.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
