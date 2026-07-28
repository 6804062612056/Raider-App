name: Build APK

on:
  workflow_dispatch:
  push:
    branches:
      - main

jobs:
  build:
    runs-on: ubuntu-22.04

    steps:
    - name: Checkout
      uses: actions/checkout@v4

    - name: Install dependencies
      run: |
        sudo apt update
        sudo apt install -y \
          python3-pip \
          python3-setuptools \
          python3-venv \
          git \
          zip \
          unzip \
          openjdk-17-jdk

    - name: Install Buildozer
      run: |
        pip3 install --user buildozer cython==0.29.36

    - name: Accept Android licenses
      run: |
        mkdir -p ~/.buildozer/android/platform/android-sdk/licenses
        echo "24333f8a63b6825ea9c5514f83c2829b004d1fee" > ~/.buildozer/android/platform/android-sdk/licenses/android-sdk-license
        echo "84831b9409646a918e30573bab4c9c91346d8abd" >> ~/.buildozer/android/platform/android-sdk/licenses/android-sdk-license

    - name: Build APK
      run: |
        ~/.local/bin/buildozer android debug

    - name: Upload APK
      uses: actions/upload-artifact@v4
      with:
        name: apk
        path: bin/*.apk