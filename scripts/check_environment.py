import sys, importlib.util
print('Python:',sys.version)
for name in ['fastapi','sqlalchemy','PIL','ultralytics','torch','cv2']:
    print(name, 'installed' if importlib.util.find_spec(name) else 'NOT INSTALLED')
