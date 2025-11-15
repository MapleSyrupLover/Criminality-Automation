# MIT License
# Copyright (c) 2025 MapleSyrupLover
# Permission is hereby granted, free of charge, to use and distribute this software
# provided that this notice remains in all copies.

#AUTOPICK VERSION 2.3.0 - MapleSyrupLover

import time
import ctypes
import pyautogui


try:
    import mss
    import numpy as np
    HAVE_MSS = True
except Exception:
    HAVE_MSS = False

TARGET_COLORS = [(255, 255, 255), (143, 143, 143)]  
COLOR_TOLERANCE = 2          
NEAR_WHITE_THRESHOLD = 245  

# coordinates
SAFE_3_COORDS = [(825, 553), (960, 561), (1095, 553)]
SAFE_2_COORDS = [(890, 553), (1025, 561)]
SAFE_1_COORDS = [(960, 553)]

# keybinds
KEY_3SAFE = 'q'
KEY_2SAFE = 'v'
KEY_1SAFE = 'b'

# sampling region size (even number). Smaller = faster, less robust.
SAMPLE_SIZE = 2

# performance tuning
POLL_INTERVAL = 0.008  
WAIT_TIMEOUT = 0.40    # seconds to wait for next lock to appear

# pyautogui tweaks
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

_user32 = ctypes.windll.user32

def is_key_down(ch: str) -> bool:
    if not ch:
        return False
    vk = ord(ch.upper())
    return (_user32.GetAsyncKeyState(vk) & 0x8000) != 0

def _region_bbox(x: int, y: int, size: int):
  
    half = size // 2
    return (x - half + 1, y - half + 1, x + half + 1, y + half + 1) 

def _matches_color(px):
    r, g, b = px
   
    if r >= NEAR_WHITE_THRESHOLD and g >= NEAR_WHITE_THRESHOLD and b >= NEAR_WHITE_THRESHOLD:
        return True
    for c in TARGET_COLORS:
        if abs(r - c[0]) <= COLOR_TOLERANCE and abs(g - c[1]) <= COLOR_TOLERANCE and abs(b - c[2]) <= COLOR_TOLERANCE:
            return True
    return False

if HAVE_MSS:
    sct = mss.mss()
    def sample_region(x, y, size):
        l, t, r, b = _region_bbox(x, y, size)
        try:
            raw = sct.grab({'left': l, 'top': t, 'width': r - l, 'height': b - t})
            arr = np.frombuffer(raw.rgb, dtype=np.uint8)
            arr = arr.reshape((raw.height, raw.width, 3))
            return arr 
        except Exception:
            return None
else:
    # fallback to pyautogui screenshot
    from PIL import Image
    def sample_region(x, y, size):
        l, t, r, b = _region_bbox(x, y, size)
        try:
            img = pyautogui.screenshot(region=(l, t, r - l, b - t))
            return img  # PIL Image
        except Exception:
            return None

def region_has_target(x: int, y: int, size: int = SAMPLE_SIZE) -> bool:
    data = sample_region(x, y, size)
    if data is None:
        # best-effort single pixel read fallback (fast)
        try:
            px = pyautogui.pixel(x, y)
        except Exception:
            return False
        return _matches_color(px)

    # mss numpy path
    if HAVE_MSS and isinstance(data, np.ndarray):
        if np.any(np.all(data >= NEAR_WHITE_THRESHOLD, axis=2)):
            return True
        for c in TARGET_COLORS:
            if np.any(np.all(np.abs(data - c) <= COLOR_TOLERANCE, axis=2)):
                return True
        return False

    # PIL Image fallback
    if isinstance(data, Image.Image):
        for px in data.getdata():
            if _matches_color(px):
                return True
        return False

    return False

def wait_for_region(x: int, y: int, timeout: float = WAIT_TIMEOUT) -> bool:
    """Poll region until it matches or timeout."""
    end = time.time() + timeout
    while time.time() < end:
        if region_has_target(x, y):
            return True
        time.sleep(POLL_INTERVAL)
    return False

def do_click_if_region(x: int, y: int) -> bool:
    if region_has_target(x, y):
        pyautogui.click()  # click where the mouse currently is
        return True
    return False

_3safe_state = 0  
_3safe_start_time = 0

def run_3safe():
    global _3safe_state, _3safe_start_time
    
    # Reset if timeout exceeded (safety net - 1 second)
    if _3safe_state > 0 and time.time() - _3safe_start_time > 1.0:
        _3safe_state = 0
    
    if _3safe_state == 0:
        # Looking for Lock 1
        if do_click_if_region(*SAFE_3_COORDS[0]):
            print("3-Safe: Lock 1 done")
            _3safe_state = 1
            _3safe_start_time = time.time()
    
    elif _3safe_state == 1:
        # Looking for Lock 2
        if wait_for_region(*SAFE_3_COORDS[1]):
            if is_key_down(KEY_3SAFE):
                pyautogui.click()
                print("3-Safe: Lock 2 done")
                _3safe_state = 2
                _3safe_start_time = time.time()
    
    elif _3safe_state == 2:
        # Looking for Lock 3
        if wait_for_region(*SAFE_3_COORDS[2]):
            if is_key_down(KEY_3SAFE):
                pyautogui.click()
                print("3-Safe: Lock 3 done")
                _3safe_state = 0
                return
        # fallback
        start = time.time()
        while is_key_down(KEY_3SAFE) and time.time() - start < 0.16:
            if region_has_target(*SAFE_3_COORDS[2]):
                pyautogui.click()
                print("3-Safe: Lock 3 done (fallback)")
                _3safe_state = 0
                return
            time.sleep(POLL_INTERVAL)

def run_2safe():
    if do_click_if_region(*SAFE_2_COORDS[0]):
        print("2-Safe: Lock 1 done")
        if wait_for_region(*SAFE_2_COORDS[1]):
            if is_key_down(KEY_2SAFE):
                pyautogui.click()
                print("2-Safe: Lock 2 done")
                return
        # fallback
        if region_has_target(*SAFE_2_COORDS[1]):
            pyautogui.click()
            print("2-Safe: Lock 2 done (fallback)")

def run_1safe():
    if do_click_if_region(*SAFE_1_COORDS[0]):
        print("1-Safe: Lock done")

# -------- main loop --------
def main_loop():
    print(f"Hold '{KEY_3SAFE}' for 3-safe, '{KEY_2SAFE}' for 2-safe, '{KEY_1SAFE}' for 1-safe. Ctrl+C to exit.")
    try:
        while True:
            if is_key_down(KEY_3SAFE):
                run_3safe()
            elif is_key_down(KEY_2SAFE):
                run_2safe()
            elif is_key_down(KEY_1SAFE):
                run_1safe()
            else:
                time.sleep(0.006)
                continue
            time.sleep(0.002)
    except KeyboardInterrupt:
        print("Stopped by user.")

if __name__ == "__main__":
    main_loop()
