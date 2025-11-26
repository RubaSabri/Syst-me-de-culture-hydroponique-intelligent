import cv2
from cv2 import aruco
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import os
import time


# let's define some constants
WORKDIR = "/home/alexis/repo/TelecomParis/Artefact/team1/calibration/"

CAM_ID = 4

# this was for a specific printed charuco board (maybe not perfect).
CHARUCO_SQUARE = 0.018       # square side length in meters (example: 4 cm)
CHARUCO_MARKER = 0.015       # marker side length in meters (<= square)
BOARD_COLS = 7              # number of squares in X (columns)
BOARD_ROWS = 5              # number of squares in Y (rows)


SQUARE_LENGTH = 30                   # Square side length (in pixels)
MARKER_LENGTH = 20                   # ArUco marker side length (in mm)
#MARGIN_PX =                        # Margins size (in pixels)

N_IMAGES = 50
count =  0
OUTPUT_DIR = WORKDIR + "out/"
# we are using the 50 dictionnary
ARUCO_DICT = aruco.DICT_6X6_50

# some configuration for using this script
DB_MAKER = False
SHOW_PREVIEW = 1

BOARD_MAKER = True

# generate the parameters we need to build a board.

aruco_dict = aruco.getPredefinedDictionary(ARUCO_DICT)
#board = aruco.CharucoBoard((BOARD_COLS, BOARD_ROWS), CHARUCO_SQUARE, CHARUCO_MARKER, aruco_dict)

myParams = aruco.DetectorParameters()
myDetector = aruco.ArucoDetector(aruco_dict, myParams)


if BOARD_MAKER:
    board2 = cv2.aruco.CharucoBoard((BOARD_COLS, BOARD_ROWS), SQUARE_LENGTH, MARKER_LENGTH, aruco_dict)
    # build board used to calibrate. We need to make sure this board will be printed with the right dimension, otherwise everything will be false.
    #imboard = board.generateImage((2000, 2000))

    #cv2.imwrite(WORKDIR + "charuco.png", imboard)

    #size_ratio = BOARD_ROWS / BOARD_COLS
    #IMG_SIZE = tuple(i * SQUARE_LENGTH + 2 * MARGIN_PX for i in ((BOARD_COLS, BOARD_ROWS)))

    #imboard2 = cv2.aruco.CharucoBoard.generateImage(board2, IMG_SIZE, marginSize=MARGIN_PX)
    imboard3 = board2.generateImage((1000, 1400))

    OUTPUT_NAME = "calibration-charuco.png"

    cv2.imwrite(WORKDIR + OUTPUT_NAME, imboard3)


if DB_MAKER:
    
    # this part is dedicated to making a database in order to create a database of images, which will be then used through the calibration algorithm to determine the intrinsecs parameters of the camera.

    
    # capture camera device 1.
    cap = cv2.VideoCapture(CAM_ID)

    if not cap.isOpened():
        print("[error] Unable to access camera /dev/video{CAM_ID}")
    else:
        print("[success] Camera opened successfully")


    while count < N_IMAGES:
        ret, frame = cap.read()

        # making a copy to avoid saving the annoted image with markers, corners and axis.
        to_save = frame.copy()
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = myDetector.detectMarkers(gray)

        if ids is not None and len(ids) > 0:
        # Interpolate ChArUco corners
            retval, charuco_corners, charuco_ids = aruco.interpolateCornersCharuco(
            markerCorners=corners, markerIds=ids, image=gray, board=board2)
        
            if retval is not None and retval >= 4:
                aruco.drawDetectedMarkers(frame, corners, ids)
                aruco.drawDetectedCornersCharuco(frame, charuco_corners, charuco_ids)
                info = f"Detected charuco corners: {int(retval)}"
            else:
                info = "Markers found but not enough charuco corners"
        else:
            info = "No markers"

        if SHOW_PREVIEW:
            #cv2.putText(frame, info, (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
            cv2.putText(frame, f"Saved: {count}/{N_IMAGES}", (10,60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,128,0), 2)
            cv2.imshow("Capture Charuco (SPACE to save)", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC - cancel
            print("ESC pressed, exit calibration")
            break
        if key == 32:  # SPACE: try to save if valid detection
            
            if ids is not None and len(ids) > 0 and retval is not None and retval >= 4:
                filename = (WORKDIR + f"imgs-cal/img_calib_{count}.png")
                cv2.imwrite(filename, to_save)
                print(f"Saved {filename} ({int(retval)} corners).")
                count += 1
            else:
                print("[error] Not enough corners detected to save this frame.")
                
    cap.release()
    cv2.destroyAllWindows()

# once this run, we grab a ton of images, no blur because we validate each, and the number we want. We should now be able to run a calibration algorithm on these images. 

else:
    print("entering calibration mode")

    # sorting images in an array (thanks to source :)
    datadir = WORKDIR + "imgs-cal/"
    images_arr = np.array([datadir + f for f in os.listdir(datadir) if f.endswith(".png") ])
    order = np.argsort([int(p.split(".")[-2].split("_")[-1]) for p in images_arr])
    images_arr = images_arr[order]

    # uncomment if you want to check the array. Be aware of image format in sorting algorithm... (here .png)
    print(images_arr)

    all_corners = []
    all_ids = []
    img_size = None

    # now parsing each line of the array, so parsing each image.
    for fname in images_arr:
        img = cv2.imread(fname)
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if img_size is None:
            img_size = img_gray.shape[::-1]
            # detecting markers on each image.
        corners, ids, _ = myDetector.detectMarkers(img_gray)
        if ids is not None and len(ids) > 0:
            
            retval, charuco_corners, charuco_ids = aruco.interpolateCornersCharuco(corners, ids, img_gray, board2)
            if charuco_ids is not None and charuco_corners is not None and len(charuco_ids) > 3:
                all_corners.append(charuco_corners)
                all_ids.append(charuco_ids)
                print(f"image {fname} is ok, added to list")
            else:
                print(f"Skipping {fname}: not enough charuco corners")
        else:
            print(f"Skipping {fname}: no markers")

    if len(all_corners) < 10:
        print("Warning: fewer than 10 valid views. Calibration may be poor.")

    # now running calibration function for aruco
    # Calibrate using charuco
    ret, camera_matrix, dist_coeffs, rvecs, tvecs = aruco.calibrateCameraCharuco(
        charucoCorners=all_corners,
        charucoIds=all_ids,
        board=board2,
        imageSize=img_size,
        cameraMatrix=None,
        distCoeffs=None
    )

    print("Calibration done:")
    print("RMS reprojection error:", ret)
    print("Camera matrix:\n", camera_matrix)
    print("Distortion coeffs:\n", dist_coeffs.ravel())

    print("job done --  saving matrixs")

    np.save(os.path.join(OUTPUT_DIR, "camera_matrix_new.npy"), camera_matrix)
    np.save(os.path.join(OUTPUT_DIR, "dist_coeffs_new.npy"), dist_coeffs)