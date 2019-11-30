import cv2


def run_rtsp():
    vcap = cv2.VideoCapture("rtsp://192.168.0.102:554/h264", cv2.CAP_FFMPEG)
    while True:
        ret, frame = vcap.read()
        if not ret:
            print("Frame is empty")
            break
        else:
            cv2.imshow('VIDEO', frame)

        if cv2.waitKey(1) & 0XFF == ord('q'):
            break

    vcap.release()
    cv2.destroyAllWindows()
