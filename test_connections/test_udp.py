import cv2


def run_udp():
    img_height = 720
    img_width = 1280
    cap = cv2.VideoCapture('udp://192.168.0.118:3000')
    if not cap.isOpened():
        print('VideoCapture not opened')
        exit(-1)

    while True:
        ret, frame = cap.read()

        if not ret:
            print('frame empty')
            break

        # cv2.imshow('image', frame)
        img_left = frame[0:img_height, 0:int(img_width / 2)]
        img_right = frame[0:img_height, int(img_width / 2):img_width]

        cv2.imshow("left", img_left)
        cv2.imshow("right", img_right)
        if cv2.waitKey(1) & 0XFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
