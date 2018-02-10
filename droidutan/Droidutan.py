#!/usr/bin/python

# Python modules
import os, glob, sys, time, subprocess, exceptions, json
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
        
    except exceptions.RuntimeError as rte:
        prettyPrint("UI Dump did not return anything. Assuming crash", "warning")
        return True
    except Exception as e:
        prettyPrintError(e)
        # Assume that the app crashed (better safe than sorry)
        return True 
   
    return False

def _appStopped(vc, appComponents):
    """
    Checks whether the app under test has been stopped/sent to the background
    :param vc: A handle to the ViewClient instance
    :type vc: com.dtmilano.android.viewclient.ViewClient
    :return: A boolean indiciating whether the app has been stopped (True) or not (False)
    """
    try:
        topLevelActivity = vc.device.getTopActivityName()
        # Check whether the top-level activity is the launcher's
        if not topLevelActivity:
            return True
        if topLevelActivity.lower().find("com.android.launcher") != -1:
            return True 
        # Check if the current activity belongs to any of the app's extracted activities
        if topLevelActivity.lower().find(appComponents["package_name"]) == -1:
            return True

    except Exception as e:
        prettyPrintError(e)
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
            if len(analysisSession.analyzed_apk.values()) < 1:
                prettyPrint("Could not retrieve an APK object", "warning")
                return None, None, None
            if len(analysisSession.analyzed_apk.values()) > 0:
                if type(analysisSession.analyzed_apk.values()[0]) == list:
                    # Androguard 2.0
                    apk = analysisSession.analyzed_apk.values()[0][0]
                else:
                    apk = analysisSession.analyzed_apk.values()[0]

            if len(analysisSession.analyzed_dex.values()) > 1:
                dx, vm = analysisSession.analyzed_dex.values()[0], analysisSession.analyzed_dex.values()[0]

    except Exception as e:
        prettyPrintError(e)
        return None, None, None

    return apk, dx, vm

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
       # Get activities
       components["activities"] = apk.get_activities()
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

def testApp(apkPath, avdSerialno="", testDuration=60, logTestcase=False, preExtractedComponents={}, allowCrashes=False, uninstallApp=True):
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
    :param preExtractedComponents: A dictionary of pre-extracted app components e.g. in case analyzeAPK and extractComponents have been already used to analyze the app.
    :type preExtractedComponents: dict
    :param allowCrashes: Whether to allow the app under test to crash. If (by default) False, the app will be re-started and re-tested.
    :type allowCrashes: bool
    :param uninstallApp: Whether to uninstall the app under test before returning
    :type uninstallApp: bool
    :return: A bool indicating the success/failure of the test
    """
    try:
        # 0. Analyze app and extract its components
        if len(preExtractedComponents) > 0:
            prettyPrint("Using a pre-extracted dictionary of app components", "debug")
            appComponents = preExtractedComponents
        else:
            prettyPrint("Analyzing app using \"androguard\"", "debug")
            apk, dx, vm = analyzeAPK(apkPath)
            if not apk:
                prettyPrint("Unable to retrieve an androguard.core.bytecodes.apk.APK object from app. Exiting", "error")
                return False
            # Retrieve app components (i.e., activities, services, receivers, etc.)
            appComponents = extractAppComponents(apk)

        if len(appComponents) < 1:
            prettyPrint("Could not extract components from \"%s\"" % apkPath, "error")
            return False

        # 1. Connect to the virtual device
        prettyPrint("Connecting to device", "debug")
        if avdSerialno != "":
            vc = ViewClient(*ViewClient.connectToDeviceOrExit(ignoreversioncheck=True, verbose=True, serialno=avdSerialno))
        else:
            vc = ViewClient(*ViewClient.connectToDeviceOrExit(ignoreversioncheck=True, verbose=True))
        # 2. Install package and configure Introspy (if requested)
        prettyPrint("Installing package \"%s\"" % apkPath, "debug")
        subprocess.call([vc.adb, "-s", avdSerialno, "install", "-r", apkPath]) 
        # 3. Start app via main activity
        prettyPrint("Starting app", "debug")
        testEvents = []
        try:
            vc.device.startActivity("%s/%s" % (appComponents["package_name"], appComponents["main_activity"]))
        except exceptions.RuntimeError as rte:
            if len(appComponents["activities"]) > 1:
                randomActivity = appComponents["activities"][random.randint(0, len(appComponents["activities"])-1)]
                while randomActivity == appComponents["main_activity"]:
                    randomActivity = appComponents["activities"][random.randint(0, len(appComponents["activities"])-1)]
                prettyPrint("Unable to start main activity. Launching \"%s\" instead" % randomActivity, "warning")
                vc.device.startActivity("%s/%s" % (appComponents["package_name"], randomActivity))     
            else:
                prettyPrint("Unable to start main activity. No other activities to launch", "error")
                return False

        testEvents.append(str(Event("%s/%s" % (appComponents["package_name"], appComponents["main_activity"]), "activity")))
        # 4. Loop for the [testDuration] seconds and randomly perform the actions
        startTime = time.time() # Record start time
        currentTime = startTime
        while int(currentTime - startTime) < testDuration:
            # 4.1. Randomly choose an action to do
            currentAction = ["gui", "broadcast", "misc"][random.randint(0, 2)]
            if currentAction == "gui":
                # Retrieve the UI elements of the current view and interact with them
                prettyPrint("Retrieving clickable UI elements on the screen", "debug")
                try:
                    uiDump = vc.dump()
                except exceptions.RuntimeError:
                    prettyPrint("Nothing returned from the UI dump. Skipping UI action", "warning")
                    continue
                # Retrieve clickable UI elements
                uiElements = [e for e in uiDump if e.isClickable()]
                # Select a random element and interact with it
                if len(uiElements) < 1:
                    prettyPrint("No clickable UI elements found on the screen. Skipping", "warning")
                    continue
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
                    vc.device.startActivity("%s/%s" % (appComponents["package_name"], appComponents["main_activity"]))  # Restart from main activity
                    testEvents.append(str(Event("%s/%s" % (appComponents["package_name"], appComponents["main_activity"]), "activity")))
                    continue

                if eClass == "CheckBox":
                    X, Y = element.getCenter()
                    prettyPrint("Checking a checkbox at (%s,%s)" % (X, Y), "debug")
                    vc.touch(X, Y)
                    testEvents.append(str(GUIEvent(element.getId(), "CheckBox", X, Y)))
                elif eClass == "EditText":
                    text = getRandomString(random.randint(0, 10))
                    prettyPrint("Writing random text to EditText: %s" % element.getId(), "debug")
                    element.setText(text)
                    testEvents.append(str(TextEvent(element.getId(), "EditText", text)))
                elif eClass == "RadioButton":
                    X, Y = element.getCenter()
                    prettyPrint("Toggling a radiobutton at (%s,%s)" % (X, Y), "debug")
                    vc.touch(X, Y)
                    testEvents.append(str(GUIEvent(element.getId(), "RadioButton", X, Y)))
                elif eClass == "Switch":
                    X, Y = element.getCenter()
                    prettyPrint("Flipping a switch at (%s,%s)" % (X, Y), "debug")
                    vc.touch(X, Y)
                    testEvents.append(str(GUIEvent(element.getId(), "Switch", X, Y)))
                elif eClass == "ToggleButon":
                    X, Y = element.getCenter()
                    prettyPrint("Toggling a button at (%s,%s)" % (X, Y), "debug")
                    vc.touch(X, Y)
                    testEvents.append(str(GUIEvent(element.getId(), "ToggleButton", X, Y)))
                elif eClass == "Button":
                    X, Y = element.getCenter()
                    prettyPrint("Tapping a button at (%s,%s)" % (X, Y), "debug")
                    vc.touch(X, Y)
                    testEvents.append(str(GUIEvent(element.getId(), "Button", X, Y)))
            
            elif currentAction == "broadcast":
                # Broadcast an intent
                prettyPrint("Broadcasting an intent", "debug")
                numFilters = len(appComponents["intent_filters"])
                if numFilters < 2: # i.e. apart from the main activity's
                    prettyPrint("No intent filters found to broadcast intents. Skipping", "warning")
                else:
                    targetFilter = appComponents["intent_filters"][random.randint(0, numFilters-1)]
                    # Make sure the intent filter is not the one used to launch the main activity
                    while targetFilter.lower().find("main") != -1:
                        targetFilter = appComponents["intent_filters"][random.randint(0, numFilters-1)]
                    prettyPrint("Broadcasting intent action: %s" % targetFilter, "debug")
                    vc.device.shell("am broadcast -a %s" % targetFilter)
                    testEvents.append(str(BroadcastEvent("none", "broadcast", targetFilter)))
                    
            elif currentAction == "misc":
                # Perform a miscellaneous action
                maxWidth = vc.display["width"] if "width" in vc.display.keys() else 768
                maxHeight =  vc.display["height"] if "height" in vc.display.keys() else 1280
                actions = ["touch", "swipeleft", "swiperight", "press"]
                selectedAction = actions[random.randint(0, len(actions)-1)]
                # Touch at random (X, Y)
                if selectedAction == "touch":
                    X, Y = random.randint(0, maxWidth), random.randint(0, maxHeight)
                    touchType = ["long", "normal"][random.randint(0,1)]
                    if touchType == "normal":
                        prettyPrint("Touching screen at (%s,%s)" % (X, Y), "debug")
                        vc.touch(X, Y)
                        testEvents.append(str(GUIEvent("none", "touch", X, Y)))
                    else:
                        prettyPrint("Long touch screen at (%s,%s)" % (X, Y), "debug")
                        vc.longTouch(X, Y)
                        testEvents.append(str(GUIEvent("none", "longtouch", X, Y)))
                # Swipe screen left/right
                elif selectedAction.find("swipe") != -1:
                    startX, startY = random.randint(0, maxWidth), random.randint(0, maxHeight)
                    endY = startY
                    endX = maxWidth if selectedAction == "swipeleft" else -maxWidth
                    prettyPrint("Swiping screen from (%s,%s) to (%s,%s)" % (startX, startY, endX, endY), "debug")
                    vc.swipe(startX, startY, endX, endY)
                    testEvents.append(str(SwipeEvent("none", selectedAction, startX, startY, endX, endY)))
                # Press a random button
                elif selectedAction == "press":
                    selectedKeyCode = selectedKeyEvents[random.randint(0, len(selectedKeyEvents)-1)]
                    prettyPrint("Pressing \"%s\"" % selectedKeyCode, "debug")
                    vc.device.press(selectedKeyCode)
                    testEvents.append(str(PressEvent("none", "press", selectedKeyCode)))
            # 4.2. Check whether the performed action crashed or stopped (sent to background) the app
            if _appCrashed(vc):
                if not allowCrashes:
                    prettyPrint("The previous action(s) caused the app to crash. Exiting", "warning")
                    return False
                prettyPrint("The previous action(s) caused the app to crash. Restarting", "warning")
                vc.device.startActivity("%s/%s" % (appComponents["package_name"], appComponents["main_activity"]))
                testEvents.append(str(Event("%s/%s" % (appComponents["package_name"], appComponents["main_activity"]), "activity")))
                #time.sleep(1) # Give time for the main activity to start
            elif _appStopped(vc, appComponents):
                prettyPrint("The previous action(s) stopped the app. Restarting", "warning")
                vc.device.startActivity("%s/%s" % (appComponents["package_name"], appComponents["main_activity"]))
                testEvents.append(str(Event("%s/%s" % (appComponents["package_name"], appComponents["main_activity"]), "activity")))
                #time.sleep(1) # Give time for the main activity to start


            # 4.3. Update the currentTime
            currentTime = time.time()
        
        # 5. Save the test events, if requested
        if logTestcase:
            prettyPrint("Saving events to file")
            testcaseFile = open("%s_%s.testcase" % (appComponents["package_name"].replace('.','_'), str(int(time.time()))), "w")
            testcaseFile.write("{\n    \"events\":[\n")
            for e in range(len(testEvents)):
               if e == len(testEvents)-1:
                   testcaseFile.write("\t%s\n" % testEvents[e])
               else:
                   testcaseFile.write("\t%s,\n" % testEvents[e])
            testcaseFile.write("    ]\n}")
            testcaseFile.close()

        # 6. Uninstalling app under test
        if uninstallApp:
            prettyPrint("Uninstalling app \"%s\"" % appComponents["package_name"])
            subprocess.call([vc.adb, "-s", avdSerialno, "uninstall", appComponents["package_name"]])


    except Exception as e:
        prettyPrintError(e)
        return False

    return True


def testAppFromTestcase(apkPath, testCaseFile, avdSerialno="", waitInterval=1, uninstallApp=True):
    """
    Tests an app according to a specific test case loaded from a JSON file generated by a previous test
    :param apkPath: The path to the APK to test
    :type apkPath: str
    :param testCaseFile: The path to the test case file from whence the actions are loaded
    :type testCaseFile: str
    :param avdSerialno: The serial number of the Android virtual device (in case multiple devices are running simultaneously)
    :type avdSerialno: str
    :param waitInterval: The time (in seconds) to wait between actions
    :type waitInterval: int 
    :param uninstallApp: Whether to uninstall the app under test before returning
    :type uninstallApp: bool
    :return: A bool indicating the success/failure of the test
    """
    try:
        # 1. Connect to the virtual device
        prettyPrint("Connecting to device", "debug")
        if avdSerialno != "":
            vc = ViewClient(*ViewClient.connectToDeviceOrExit(ignoreversioncheck=True, verbose=True, serialno=avdSerialno))
        else:
            vc = ViewClient(*ViewClient.connectToDeviceOrExit(ignoreversioncheck=True, verbose=True))

        # 1.a. Analyzing app
        prettyPrint("Analyzing app using \"androguard\"", "debug")
        apk, dx, vm = analyzeAPK(apkPath)
        appComponents = extractAppComponents(apk)

        # 2. Install package and configure Introspy (if requested)
        prettyPrint("Installing package \"%s\"" % apkPath, "debug")
        subprocess.call([vc.adb, "-s", avdSerialno, "install", "-r", apkPath])

        # 3. Load and parse test case file
        prettyPrint("Loading the test case file \"%s\"" % testCaseFile, "debug")
        if not os.path.exists(testCaseFile):
            prettyPrint("Could not find the test case file", "error")
            return False
        content = json.loads(open(testCaseFile).read())
        if len(content["events"]) < 1:
            prettyPrint("Could not retrieve events to run", "error")

        # 4. Iterate over events and execute them
        tapEvents = ["Button", "CheckBox", "RadioButton", "Switch", "ToggleButton"]
        touchEvents = ["longtouch", "touch"]
        textEvents = ["EditText"]
        swipeEvents = ["swipeleft", "swiperight"]
        pressEvents = ["press"]
        for e in content["events"]:
            # 4.1. Parse and execute event
            if e["type"] == "activity":
                try:
                    prettyPrint("Starting activity \"%s\"" % e["id"], "debug")
                    vc.device.startActivity(e["id"])
                except exceptions.RuntimeError as rte:
                    prettyPrint("Unable to start activity \"%s\"" % e["id"], "warning")
            elif e["type"] == "broadcast":
                prettyPrint("Broadcasting intent action: %s" % e["intent"], "debug")
                vc.device.shell("am broadcast -a %s" % e["intent"])
            elif e["type"] in tapEvents:
                prettyPrint("Tapping %s at (%s, %s)" % (e["type"], e["x"], e["y"]), "debug")
                vc.touch(int(e["x"]), int(e["y"]))
            elif e["type"] in textEvents:
                prettyPrint("Writing \"%s\" to EditText field \"%s\"" % (e["text"], e["id"]), "debug")
                allviews = vc.getViewsById()
                if len(allviews) < 1 or e["id"] not in allviews.keys():
                    prettyPrint("Could not find EditText with id \"%s\". Skipping" % e["id"], "warning")
                else:
                    allviews[e["id"]].setText(e["text"])
            elif e["type"] in swipeEvents:
                prettyPrint("Swiping screen from (%s, %s) to (%s, %s)" % (e["x"], e["y"], e["xd"], e["yd"]), "debug")
                vc.swipe(int(e["x"]), int(e["y"]), int(e["xd"]), int(e["yd"]))
            elif e["type"] in pressEvents:
                prettyPrint("Pressing \"%s\"" % e["key"], "debug")
                vc.device.press(e["key"])
            elif e["type"].lower().find("touch") != -1:
                 if e["type"] == "longtouch":
                     prettyPrint("Long touching at (%s,%s)" % (e["x"], e["y"]), "debug")
                     vc.longTouch(int(e["x"]), int(e["y"]))
                 else:
                     prettyPrint("Touching at (%s,%s)" % (e["x"], e["y"]), "debug")
                     vc.touch(int(e["x"]), int(e["y"]))

            # 4.2. Check whether the performed action crashed or stopped (sent to background) the app
            if _appCrashed(vc):
                if not allowCrashes:
                    prettyPrint("The previous action(s) caused the app to crash. Exiting", "warning")
                    return False
                prettyPrint("The previous action(s) caused the app to crash. Restarting", "warning")
                vc.device.startActivity("%s/%s" % (appComponents["package_name"], appComponents["main_activity"]))
                testEvents.append(str(Event("%s/%s" % (appComponents["package_name"], appComponents["main_activity"]), "activity")))
                time.sleep(waitInterval) # Give time for the main activity to start
            elif _appStopped(vc, appComponents):
                prettyPrint("The previous action(s) stopped the app. Restarting", "warning")
                vc.device.startActivity("%s/%s" % (appComponents["package_name"], appComponents["main_activity"]))
                testEvents.append(str(Event("%s/%s" % (appComponents["package_name"], appComponents["main_activity"]), "activity")))
                time.sleep(waitInterval) # Give time for the main activity to start

        # 6. Uninstalling app under test
        if uninstallApp:
            prettyPrint("Uninstalling app \"%s\"" % appComponents["package_name"])
            subprocess.call([vc.adb, "-s", avdSerialno, "uninstall", appComponents["package_name"]])

    except Exception as e:
        prettyPrintError(e)
        return False

    return True



