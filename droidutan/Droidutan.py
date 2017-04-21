#!/usr/bin/python

# Python modules
import os, glob, sys, time, subprocess
# Droidutan utils
from Graphics import *
from Common import *
# Androguard
try:
    from androguard.session import Session
except Exception as e:
    prettyPrint("Error encountered while importing \"androguard\". Hint: Make sure that it is installed on your system", "error")
    exit(1)
# AndroidViewClient
try:
    from com.dtmilano.android.viewclient import ViewClient
except Exception as e:
    prettyPrint("Error encountered while importing \"AndroidViewClient\". Hint: Make sure that it is installed on your system", "error")
    exit(1)
   
def _appCrashed(vc):
    """
    Checks whether the app under test has crashed via an exception message
    :param vc: A handle to the ViewClient instance
    :type vc: com.dtmilano.android.viewclient.ViewClient
    :return: A boolean indicating whether the app has crashed (True) or not (False)
    """
    try:
        uiElements = vc.dump()
        for element in uiElements:
            if element.getClass().split('.')[-1] == "TextView":
                if element.getText().lower().find("has stopped") != -1:
                    # Tap the "OK" button and return True to indicate crash
                    vc.findViewWithText("OK").touch()
                    return True
                
    except Exception as e:
        prettyPrintError(e)
        # Assume that the app crashed (better safe than sorry)
        return True 
   
    return False

def analyzeAPK(apkPath):
    """
    Uses Androguard to analyze an APK and retrieve the app's components
    :param apkPath: The path to the APK to be analyzed
    :type apkPath: str
    :return: A tuple of (androguard.core.bytecodes.apk.APK, androguard.core.bytecodes.dvm.DalvikVMFormat, androguard.core.analysis.analysis.newVMAnalysis)
    """
    try:
        apk, dx, vm = None, None, None
        if not os.path.exists(apkPath):
            prettyPrint("Could not find \"%s\"" % apkPath, "warning")
        else:
            analysisSession = Session()
            analysisSession.add(apkPath, open(apkPath).read())
            apk = analysisSession.analyzed_apk.values()[0]
            dx = analysisSession.analyzed_dex.values()[0][0]
            vm = analysisSession.analyzed_dex.values()[0][1]

    except Exception as e:
        prettyPrintError(e)
        return None, None, None

    return apk, dx, vm

def configureIntrospy(vc, packageName):
    """
    Configure Introspy to log API calls issued by the APK during testing
    :param vc: A handle to the ViewClient instance
    :type vc: com.dtmilano.android.viewclient.ViewClient
    :param packageName: The name of the package under test e.g. com.X.Y
    :type ackageName: str
    :return: A boolean depicting the success/failure of the operation
    """
    try:
        # Configure Introspy
        vc.device.shell("echo 'GENERAL CRYPTO,KEY,HASH,FS,IPC,PREF,URI,WEBVIEW,SSL' > /data/data/%s/introspy.config" % packageName)
        vc.device.shell("chmod 664 /data/data/%s/introspy.config" % packageName)

    except Exception as e:
        prettyPrintError(e)
        return False

    return True

def extractAppComponents(apk):
    """
    Extracts some basic app information necessary to launch the test e.g. main activity, intent filters, etc.
    :param apk: An object containing information about the app components
    :type apk: androguard.core.bytecodes.apk.APK
    :return: A dict containing the extracted app components
    """
    try:
       components = {}
       # Get app and package names
       components["app_name"] = apk.get_app_name()
       components["package_name"] = apk.package
       # Get the main activity
       components["main_activity"] = apk.get_main_activity()
       # Get (action android:name) of intent filters
       components["intent_filters"] = apk.get_elements("action", "name")
       # Get services
       components["services"] = apk.get_services()
       # Get content providers
       components["content_providers"] = apk.get_providers()

    except Exception as e:
        prettyPrintError(e)
        return {}

    return components

def testApp(apkPath, avdSerialno="", testDuration=60, logTestcase=False, useIntrospy=False):
    """
    Use AndroidViewClient to test an app
    :param apkPath: The path to the APK to test
    :type apkPath: str
    :param avdSerialno: The serial number of the Android virtual device (in case multiple devices are running simultaneously)
    :type avdSerialno: str
    :param testDuration: The duration of the test (in seconds)
    :type testDuration: int
    :param logTestcase: Log the AndroidViewClient commands issued to the target AVD during the test
    :type logTestcase: bool
    :param useIntrospy: Whether to configure Introspy to monitor the API calls of the app under test
    :type useIntrospy: bool
    :return: A bool indicating the success/failure of the test
    """
    try:
        # 0. Analyze app and extract its components
        prettyPrint("Analyzing app using \"androguard\"", "debug")
        apk, dx, vm = analyzeAPK(apkPath)
        appComponents = extractAppComponents(apk)
        if len(appComponents) < 1:
            prettyPrint("Could not extract components from \"%s\"" % apkPath, "error")
            return False

        # 1. Connect to the virtual device
        prettyPrint("Connecting to device", "debug")
        if avdSerialno != "":
            vc = ViewClient(*ViewClient.connectToDeviceOrExit(ignoreversioncheck=True, serialno=avdSerialno))
        else:
            vc = ViewClient(*ViewClient.connectToDeviceOrExit(ignoreversioncheck=True))
        # 2. Install package and configure Introspy (if requested)
        prettyPrint("Installing package \"%s\"" % apkPath, "debug")
        #vc.installPackage(apkPath) # No parameter to specify device (no support for simultaneous instances) => Extend AndroidViewClient
        subprocess.call([vc.adb, "-s", avdSerialno, "install", "-r", apkPath]) 
        if useIntrospy:
            prettyPrint("Configuring \"Introspy\" before testing", "debug")
            if not configureIntrospy(vc, appComponents["package_name"]):
                prettyPrint("Configure \"Introspy\" failed. Proceeding with test", "warning")
        # 3. Start app via main activity
        prettyPrint("Starting app", "debug")
        vc.device.startActivity("%s/%s" % (appComponents["package_name"], appComponents["main_activity"]))
        # 4. Loop for the [testDuration] seconds and randomly perform the actions
        startTime = time.time() # Record start time
        currentTime = startTime
        while int(currentTime - startTime) < testDuration:
            # 4.1. Randomly choose an action to do
            currentAction = ["gui", "broadcast", "misc"][random.randint(0, 2)]
            if currentAction == "gui":
                # Retrieve the UI elements of the current view and interact with them
                prettyPrint("Retrieving UI elements on the screen", "debug")
                uiElements = vc.dump()
                # Select a random element and interact with it
                element = uiElements[random.randint(0, len(uiElements)-1)]
                # Get the element's class
                eClass = element.getClass().split('.')[-1]
                attempt = 1
                while eClass not in supportedUIElements and attempt < 10:
                    element = uiElements[random.randint(0, len(uiElements)-1)]
                    eClass = element.getClass().split('.')[-1]
                    attempt += 1

                # We tried 10 times and still could not get a supported element. Maybe it is a dummy activity with no interactive elements?
                if attempt == 10 and eClass not in supportedUIElements:
                    vc.device.press("KEYCODE_BACK") # Navigate back
                    continue

                if eClass == "CheckBox":
                    X, Y = element.getXY()
                    prettyPrint("Checking a checkbox at (%s,%s)" % (X, Y), "debug")
                    vc.touch(X, Y)
                elif eClass == "EditText":
                    text = getRandomString(random.randint(0, 50))
                    prettyPrint("Writing random text to EditText: %s" % element.getId(), "debug")
                    element.setText(text)
                elif eClass == "RadioButton":
                    X, Y = element.getXY()
                    prettyPrint("Toggling a radiobutton at (%s,%s)" % (X, Y), "debug")
                    vc.touch(X, Y)
                elif eClass == "RatingBar":
                    X, Y = element.getXY()
                    barWidth = element.getWidth()
                    ratingX = random.randint(0, barWidth-1)
                    prettyPrint("Touching a rating bar at (%s, %s)" % (X+ratingX, Y), "debug")
                    vc.touch(X+ratingX, Y)
                elif eClass == "Switch":
                    if element.isClickable:
                        X, Y = element.getXY()
                        prettyPrint("Flipping a switch at (%s,%s)" % (X, Y), "debug")
                        vc.touch(X, Y)
                elif eClass == "ToggleButon":
                    if element.isClickable:
                        X, Y = element.getXY()
                        prettyPrint("Toggling a button at (%s,%s)" % (X, Y), "debug")
                        vc.touch(X, Y)
                elif eClass == "Button":
                    if element.isClickable:
                        X, Y = element.getXY()
                        prettyPrint("Tapping a button at (%s,%s)" % (X, Y), "debug")
                        vc.touch(X, Y)
            
            elif currentAction == "broadcast":
                # Broadcast an intent
                numFilters = len(appComponents["intent_filters"])
                if numFilters < 1:
                    prettyPrint("No intent filters found to broadcast intents. Skipping", "warning")
                else:
                    targetFilter = appComponents["intent_filters"][random.randint(0, numFilters-1)]
                    # Make sure the intent filter is not the one used to launch the main activity
                    while targetFilter.lower().find("main") != -1:
                        targetFilter = appComponents["intent_filters"][random.randint(0, numFilters-1)]
                    prettyPrint("Broadcasting intent action: %s" % targetFilter, "debug")
                    vc.device.shell("am broadcast -a %s" % targetFilter)
                    
            elif currentAction == "misc":
                # Perform a miscellaneous action
                maxWidth, maxHeight = vc.display["width"], vc.display["height"]
                actions = ["touch", "swipeleft", "swiperight", "press"]
                selectedAction = actions[random.randint(0, len(actions)-1)]
                # Touch at random (X, Y)
                if selectedAction == "touch":
                    X, Y = random.randint(0, maxWidth), random.randint(0, maxHeight)
                    touchType = ["long", "normal"][random.randint(0,1)]
                    if touchType == "normal":
                        prettyPrint("Touching screen at (%s,%s)" % (X, Y), "debug")
                        vc.touch(X, Y)
                    else:
                        prettyPrint("Long touch screen at (%s,%s)" % (X, Y), "debug")
                        vc.longTouch(X, Y)
                # Swipe screen left/right
                elif selectedAction.find("swipe") != -1:
                    startX, startY = random.randint(0, maxWidth), random.randint(0, maxHeight)
                    endY = startY
                    endX = maxWidth if selectedAction == "swipeleft" else -maxWidth
                    prettyPrint("Swiping screen from (%s,%s) to (%s,%s)" % (startX, startY, endX, endY), "debug")
                    vc.swipe(startX, startY, endX, endY)
                # Press a random button
                elif selectedAction == "press":
                    selectedKeyCode = selectedKeyEvents[random.randint(0, len(selectedKeyEvents)-1)]
                    prettyPrint("Pressing \"%s\"" % selectedKeyCode, "debug")
                    vc.device.press(selectedKeyCode)

            # 4.2. Check whether the performed action crashed the app
            if _appCrashed(vc):
                prettyPrint("The previous action(s) caused the app to crash. Restarting", "warning")
                vc.device.startActivity("%s/%s" % (appComponents["package_name"], appComponents["main_activity"]))
                time.sleep(0.5) # Give time for the main activity to start

            # 4.3. Update the currentTime
            currentTime = time.time()

    except Exception as e:
        prettyPrintError(e)
        return False

    return True


