import sys, time, threading, cv2
from PyQt5.QtCore import QTimer, QPoint, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QLabel, QPushButton
from PyQt5.QtWidgets import QWidget, QAction, QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout, QLineEdit, QCheckBox, QComboBox
from PyQt5.QtGui import QFont, QPainter, QImage, QTextCursor, QIcon, QIntValidator
import asyncio
from nats.aio.client import Client as NATS
from asyncqt import QEventLoop

try:
    import Queue as Queue
except:
    import queue as Queue

IMG_SIZE = 1280, 720  # 640,480 or 1280,720 or 1920,1080
IMG_FORMAT = QImage.Format_RGB888
DISP_SCALE = 1  # Scaling factor for display image
DISP_MSEC = 50  # Delay between display cycles
CAP_API = cv2.CAP_ANY  # API: CAP_ANY or CAP_DSHOW etc...
EXPOSURE = 0  # Zero for automatic exposure
TEXT_FONT = QFont("Courier", 10)

camera_num = 1  # Default camera (first in list)
image_queue = Queue.Queue()  # Queue to hold images
capturing = True  # Flag to indicate capturing


# Grab images from the camera (separate thread)
def grab_images(cam_num, queue):
    cap = cv2.VideoCapture('udp://10.10.10.199:3000')
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, IMG_SIZE[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, IMG_SIZE[1])
    if EXPOSURE:
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0)
        cap.set(cv2.CAP_PROP_EXPOSURE, EXPOSURE)
    else:
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
    while capturing:
        if cap.grab():
            retval, image = cap.retrieve(0)
            if image is not None and queue.qsize() < 2:
                queue.put(image)
            else:
                time.sleep(DISP_MSEC / 1000.0)
        else:
            print("Error: can't grab camera image")
            break
    cap.release()


# Image widget
class ImageWidget(QWidget):
    def __init__(self, parent=None):
        super(ImageWidget, self).__init__(parent)
        self.image = None

    def setImage(self, image):
        self.image = image
        self.setMinimumSize(image.size())
        self.update()

    def paintEvent(self, event):
        qp = QPainter()
        qp.begin(self)
        if self.image:
            qp.drawImage(QPoint(0, 0), self.image)
        qp.end()


# Main window
class MyWindow(QMainWindow):
    text_update = pyqtSignal(str)

    # Create main window
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
        self.central = QWidget(self)
        self.textbox = QTextEdit(self.central)
        self.textbox.setFont(TEXT_FONT)
        self.textbox.setMinimumSize(300, 100)
        self.groupbox = QGroupBox()
        self.gridlayout = QGridLayout()
        self.combobox = QComboBox()
        self.combobox.addItems(['Led orange', 'Led green', 'Led blue'])
        self.led_checkbox = QCheckBox()
        self.led_button = QPushButton('On/off led', self)
        self.led_button.clicked.connect(self.on_click_led)
        self.groupbox.setLayout(self.gridlayout)
        self.button_turn = QPushButton('Turn body', self)
        self.button_turn.clicked.connect(self.on_click_turn)
        self.line_turn = QLineEdit()
        self.label_degree = QLabel('Step')
        self.checkDirection = QCheckBox('Direction')
        self.gridlayout.addWidget(self.button_turn, 0, 0)
        self.gridlayout.addWidget(self.label_degree, 0, 1)
        self.gridlayout.addWidget(self.line_turn, 0, 2)
        self.gridlayout.addWidget(self.checkDirection, 0, 3)
        self.gridlayout.addWidget(self.led_button, 1, 0)
        self.gridlayout.addWidget(self.combobox, 1, 1)
        self.gridlayout.addWidget(self.led_checkbox, 1, 2)
        self.text_update.connect(self.append_text)
        self.validator = QIntValidator(1, 99, self)
        self.line_turn.setValidator(self.validator)
        sys.stdout = self
        print("Camera number %u" % camera_num)
        print("Image size %u x %u" % IMG_SIZE)
        if DISP_SCALE > 1:
            print("Display scale %u:1" % DISP_SCALE)
        # self.button = QPushButton('Open', self)
        # self.button.clicked.connect(self.on_click)
        self.button_trace_face = QPushButton('Track face', self)
        self.button_trace_face.clicked.connect(self.on_click_trace_face)

        self.vlayout = QVBoxLayout()  # Window layout
        self.displays = QHBoxLayout()
        self.disp = ImageWidget(self)
        self.displays.addWidget(self.disp)
        self.vlayout.addLayout(self.displays)
        self.label = QLabel(self)
        self.vlayout.addWidget(self.groupbox)
        self.vlayout.addWidget(self.label)
        self.vlayout.addWidget(self.textbox)
        # self.vlayout.addWidget(self.button)
        self.vlayout.addWidget(self.button_trace_face)
        self.central.setLayout(self.vlayout)
        self.setCentralWidget(self.central)

        self.mainMenu = self.menuBar()  # Menu bar
        exitAction = QAction('&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self.close)
        self.fileMenu = self.mainMenu.addMenu('&File')
        self.fileMenu.addAction(exitAction)

    @pyqtSlot()
    def on_click(self):
        self.start()

    @pyqtSlot()
    def on_click_turn(self):
        step = self.line_turn.text()
        if self.checkDirection.isChecked():
            asyncio.run(nc.publish("Check", 'enturn:-{}'.format(step).encode()))
        else:
            asyncio.run(nc.publish("Check", 'enturn:{}'.format(step).encode()))

    @pyqtSlot()
    def on_click_led(self):
        led = self.combobox.currentIndex() + 1
        if self.led_checkbox.isChecked():
            asyncio.run(nc.publish("Check", 'led:on{}'.format(str(led)).encode()))
        else:
            asyncio.run(nc.publish("Check", 'led:off{}'.format(str(led)).encode()))



    @pyqtSlot()
    def on_click_trace_face(self):
        self.start_trace_face()

    # Start image capture & display
    def start(self):
        self.timer = QTimer(self)  # Timer to trigger display
        self.timer.timeout.connect(lambda:
                                   self.show_image(image_queue, self.disp, DISP_SCALE))
        self.timer.start(DISP_MSEC)
        self.capture_thread = threading.Thread(target=grab_images,
                                               args=(camera_num, image_queue))
        self.capture_thread.start()  # Thread to grab images

    def start_trace_face(self):
        self.timer = QTimer(self)  # Timer to trigger display
        self.timer.timeout.connect(lambda:
                                   self.show_image_trace_face(image_queue, self.disp, DISP_SCALE))
        self.timer.start(DISP_MSEC)
        self.capture_thread = threading.Thread(target=grab_images,
                                               args=(camera_num, image_queue))
        self.capture_thread.start()  # Thread to grab images

    # Fetch camera image from queue, and display it
    def show_image(self, imageq, display, scale):
        if not imageq.empty():
            image = imageq.get()
            if image is not None and len(image) > 0:
                img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                self.display_image(img, display, scale)

    def show_image_trace_face(self, imageq, display, scale):
        if not imageq.empty():
            image = imageq.get()
            if image is not None and len(image) > 0:
                img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
                for (x, y, w, h) in faces:
                    cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
                self.display_image(img, display, scale)

    # Display an image, reduce size if required
    def display_image(self, img, display, scale=1):
        disp_size = img.shape[1] // scale, img.shape[0] // scale
        disp_bpl = disp_size[0] * 3
        if scale > 1:
            img = cv2.resize(img, disp_size,
                             interpolation=cv2.INTER_CUBIC)
        qimg = QImage(img.data, disp_size[0], disp_size[1],
                      disp_bpl, IMG_FORMAT)
        display.setImage(qimg)

    # Handle sys.stdout.write: update text display
    def write(self, text):
        self.text_update.emit(str(text))

    def flush(self):
        pass

    # Append to text display
    def append_text(self, text):
        cur = self.textbox.textCursor()  # Move cursor to end of text
        cur.movePosition(QTextCursor.End)
        s = str(text)
        while s:
            head, sep, s = s.partition("\n")  # Split line at LF
            cur.insertText(head)  # Insert text at cursor
            if sep:  # New line if LF
                cur.insertBlock()
        self.textbox.setTextCursor(cur)  # Update visible cursor

    # Window is closing: stop video capture
    def closeEvent(self, event):
        global capturing
        capturing = False
        self.capture_thread.join()


nc = NATS()


async def run(loop):
    await nc.connect("10.10.10.10:4222", loop=loop)

    async def message_handler(msg):
        # subject = msg.subject
        # reply = msg.reply
        data = msg.data
        print((data[0] * 256 + data[1]) * 0.3515625)
        # print(msg.data[1])

    # Simple publisher and async subscriber via coroutine.
    sid = await nc.subscribe("Encoder", cb=message_handler)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    win = MyWindow()
    win.show()
    win.setWindowTitle('GUI')
    # loop = asyncio.get_event_loop()
    loop.run_until_complete(run(loop))
    # loop.run_forever()
    with loop:
        sys.exit(loop.run_forever())
