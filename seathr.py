
from PIL import Image

def make_background_transparent(image_path):
    img = Image.open(image_path).convert("RGBA")
    datas = img.getdata()
    new_data = []
    target_rgb = (255, 251, 240)
    tolerance = 10

    for item in datas:
        r, g, b, a = item
        if abs(r - target_rgb[0]) <= tolerance and abs(g - target_rgb[1]) <= tolerance and abs(b - target_rgb[2]) <= tolerance:
            new_data.append((r, g, b, 0))
        else:
            new_data.append(item)

    img.putdata(new_data)
    output_path = image_path.replace(".png", "_透過.png")
    img.save(output_path)
    return output_path

from PyQt6.QtWidgets import QApplication, QLabel, QFileDialog, QWidget
from PyQt6.QtGui import QPixmap, QImage, QMouseEvent, QPainter, QPen
from PyQt6.QtCore import Qt, QPoint
from PIL import Image
import sys

class TransparentImageViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)

        self.setGeometry(100, 100, 800, 600)

        self.label = QLabel(self)
        self.label.setStyleSheet("background: transparent;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        self.image_pixmap = None
        self.drag_pos = QPoint()
        self.resizing = False

        self.triangle_size = 40  # 右下三角のサイズ
        self.header_height = 40  # 上部帯の高さ

        self.load_image_dialog()

    def load_image_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "画像ファイルを選択", "", "画像 (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            self.process_and_show(file_path)
        else:
            self.close()

    def process_and_show(self, path):
        img = Image.open(path).convert("RGBA")
        datas = img.getdata()
        new_data = []
        for item in datas:
            if item[0] > 240 and item[1] > 240 and item[2] > 240:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        img.putdata(new_data)

        qimg = QImage(img.tobytes(), img.width, img.height, QImage.Format.Format_RGBA8888)
        self.image_pixmap = QPixmap.fromImage(qimg)
        self.update_display()

    def update_display(self):
        if self.image_pixmap:
            scaled = self.image_pixmap.scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            self.label.setPixmap(scaled)
        self.label.setGeometry(self.rect())

    def resizeEvent(self, event):
        self.label.setGeometry(self.rect())
        self.update_display()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._in_resize_corner(event.pos()):
                self.resizing = True
            elif self._in_drag_header(event.pos()):
                self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.resizing:
            delta = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.resize(max(delta.x(), 100), max(delta.y(), 100))
        elif event.buttons() & Qt.MouseButton.LeftButton and self._in_drag_header(event.pos()):
            self.move(event.globalPosition().toPoint() - self.drag_pos)
        else:
            if self._in_resize_corner(event.pos()):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif self._in_drag_header(event.pos()):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.resizing = False

    def _in_resize_corner(self, pos):
        return pos.x() >= self.width() - self.triangle_size and pos.y() >= self.height() - self.triangle_size

    def _in_drag_header(self, pos):
        return pos.y() <= self.header_height

    def paintEvent(self, event):
        painter = QPainter(self)
        pen = QPen(Qt.GlobalColor.white)
        pen.setWidth(2)
        painter.setPen(pen)

        # 外枠
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))

        # リサイズ三角（右下）
        points = [
            QPoint(self.width(), self.height()),
            QPoint(self.width() - self.triangle_size, self.height()),
            QPoint(self.width(), self.height() - self.triangle_size)
        ]
        painter.setBrush(Qt.GlobalColor.white)
        painter.drawPolygon(*points)

        # ヘッダー帯
        painter.drawRect(0, 0, self.width(), self.header_height)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = TransparentImageViewer()
    viewer.show()
    sys.exit(app.exec())

