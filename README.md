# semmatch

semmatch is a tool to automate picking data acquisition points in SerialEM maps. It is meant to be used by SerialEM script to merge in externally defined navigator points.

## Requirements
- SerialEM 3.8 beta or higher
- [64-bit Python3](https://www.python.org/ftp/python/3.7.3/python-3.7.3-amd64.exe)

## Install
- Run Python3 installer
	- Check "Add Python to Path"
	- Click "Install Now"
	- If prompted, disable Windows path limit
- Open Command Prompt from Windows start menu
	- `py -m pip install -U semmatch`
- Copy [TemplateMatch_GUI.txt](TemplateMatch_GUI.txt) from this repository into a SerialEM script

## Usage
- Select a map from SerialEM navigator
- Run TemplateMatch_GUI script
	- Optionally crop out a hole/feature in SerialEM to use as a template (see TemplateMatch_GUI.txt for description)
