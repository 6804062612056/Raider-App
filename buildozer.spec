[app]

# (str) Title of your application
title = Pharaoh Raider

# (str) Package name
package.name = pharaohraider

# (str) Package domain
package.domain = com.guy

# (str) Icon of the application
icon.filename = %(source.dir)s/images/icon.png

# (str) presplash
presplash.filename = %(source.dir)s/images/splash.png
android.presplash_color = #FFFFFF

# (str) Source code directory
source.dir = .

# (list) Source files to include
source.include_exts = py,kv,png,jpg,atlas

# (str) Application version
version = 1.0.1
android.numeric_version = 10001

# (list) Requirements
requirements = python3,kivy

# (str) Supported orientation
orientation = portrait

# (bool) Fullscreen
fullscreen = 0


[buildozer]

# (int) Log level
log_level = 2