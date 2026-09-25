[app]

# (str) Title of your application
title = Pharaoh Raider

# (str) Package name
package.name = pharaohraider

# (str) Package domain
package.domain = com.guy

# (int) Target Android API, should be as high as possible.
android.api = 34

# (int) Minimum API your APK will support
android.minapi = 21

# (str) Icon of the application
icon.filename = %(source.dir)s/images/icon.png

# (str) presplash
presplash.filename = %(source.dir)s/images/splash.png
android.presplash_color = #FFFFFF

# (str) Source code directory
source.dir = .

# (list) Source files to include
source.include_exts = py,kv,png,jpg,atlas,txt,ttf

# (str) Application version
version = 1.0.8
android.numeric_version = 10008

# (list) Requirements
requirements = python3,kivy,kivy_garden.mapview,pyjnius,requests

# (str) Supported orientation
orientation = portrait

# (bool) Fullscreen
fullscreen = 0

p4a.branch = develop
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,CHANGE_WIFI_MULTICAST_STATE,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION


[buildozer]

# (int) Log level
log_level = 2
