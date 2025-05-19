from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QFileDialog
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from PIL import Image
import sys
import os

def auto_transparent_by_corner(image_path, tolerance=30):
    """四隅の背景色を透過し、非透過部分だけをクロップして保存"""
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size
    pixels = img.load()

    # 四隅の平均色を背景色と仮定
    corners = [
        pixels[0, 0],
        pixels[width - 1, 0],
        pixels[0, height - 1],
        pixels[width - 1, height - 1]
    ]
    avg_color = tuple(sum(c[i] for c in corners) // 4 for i in range(3))
    print(f"推定背景色: {avg_color}")

    new_data = []
    for r, g, b, a in img.getdata():
        if all(abs(val - avg) <= tolerance for val, avg in zip((r, g, b), avg_color)):
            new_data.append((r, g, b, 0))  # 完全透過
        else:
            new_data.append((r, g, b, a))

    img.putdata(new_data)

    alpha = img.getchannel("A")
    bbox = alpha.getbbox()
    if bbox:
        img = img.crop(bbox)

    base, ext = os.path.splitext(image_path)
    output_path = base + "_transparent_cropped.png"
    img.save(output_path)
    print(f"保存完了: {output_path}")
    return output_path

class TransparentCropper(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("背景透過＆クロップツール")
        self.resize(400, 300)

        self.label = QLabel("画像を選択してください")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.select_button = QPushButton("画像を選択")
        self.select_button.clicked.connect(self.select_image)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.select_button)
        self.setLayout(layout)

    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "画像ファイルを選択", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            output_path = auto_transparent_by_corner(file_path)
            self.label.setText(f"保存完了: {os.path.basename(output_path)}")
            self.label.setPixmap(QPixmap(output_path).scaledToWidth(300, Qt.TransformationMode.SmoothTransformation))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TransparentCropper()
    window.show()
    sys.exit(app.exec())

