
# coding: utf-8

# In[3]:

import time
import win32con
import win32api
import win32gui
import win32process


_, cmd = win32api.FindExecutable('notepad')


  # In[4]:
print(_, cmd)

# In[5]:
_, _, pid, tid = win32process.CreateProcess(
    None,    # name
    cmd,     # command line
    None,    # process attributes
    None,    # thread attributes
    0,       # inheritance flag
    0,       # creation flag
    None,    # new environment
    None,    # current directory
    win32process.STARTUPINFO())

print(_, _, pid, tid)


# In[6]:

# wcallb is callback for EnumThreadWindows and 
# EnumChildWindows. It populates the dict 'handle' with 
# references by class name for each window and child 
# window of the given thread ID.

def wcallb(hwnd, handle):
    handle[win32gui.GetClassName(hwnd)] = hwnd
    win32gui.EnumChildWindows(hwnd, wcallb, handle)
    return True


# In[ ]:

handle = {}
while not handle:   # loop until the window is loaded
    time.sleep(0.1)
    win32gui.EnumThreadWindows(tid, wcallb, handle)


# In[ ]:

# Sending normal characters is a WM_CHAR message. 
# Function keys are sent as WM_KEYDOWN and WM_KEYUP 
# messages using the virtual keys defined in win32con, 
# such as VK_F5 for the f5 key.
#
# Notepad has a separate 'Edit' window to which you can 
# write, but function keys are processed by the main 
# window. 


# In[ ]:

for c in "Hello World\n":
    win32api.PostMessage(
        handle['Edit'], 
        win32con.WM_CHAR, 
        ord(c), 
        0)


# In[ ]:

win32api.PostMessage(
    handle['Notepad'], 
    win32con.WM_KEYDOWN, 
    win32con.VK_F5, 
    0)


# In[1]:

win32api.PostMessage(
    handle['Notepad'], 
    win32con.WM_KEYUP, 
    win32con.VK_F5, 
    0)


# In[ ]:



