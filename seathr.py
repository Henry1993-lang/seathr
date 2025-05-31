from PyQt6.QtWidgets import (
    QApplication, QLabel, QFileDialog, QWidget, QColorDialog,
    QMenu, QSlider, QInputDialog, QMessageBox, QVBoxLayout,
    QListWidget, QListWidgetItem, QPushButton, QDialog, QHBoxLayout, QLineEdit
)
from PyQt6.QtGui import QPixmap, QImage, QMouseEvent, QPainter, QPen, QColor, QIcon
from PyQt6.QtCore import Qt, QPoint, QSize
from PIL import Image
import sys
import sqlite3
import os

class TransparentImageViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)

        self.setGeometry(100, 100, 800, 600)

        self.label = QLabel(self)
        self.label.setStyleSheet("background: transparent;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Header for controls and window buttons
        self.header_height = 40
        self.create_header_controls()

        self.slider_label = QLabel("透過範囲: 10", self)
        self.slider_label.setStyleSheet("color: white; background-color: rgba(0, 0, 0, 80%);")
        self.slider_label.move(10, 10)

        self.tolerance_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.tolerance_slider.setGeometry(120, 10, 150, 20)
        self.tolerance_slider.setMinimum(0)
        self.tolerance_slider.setMaximum(100)
        self.tolerance_slider.setValue(10)
        self.tolerance_slider.valueChanged.connect(self.slider_changed)

        # Image navigation elements
        self.prev_image_button = QPushButton("<", self)
        self.prev_image_button.setGeometry(10, 40, 30, 20)
        self.prev_image_button.clicked.connect(self.show_previous_image)
        self.prev_image_button.setStyleSheet("color: white; background-color: rgba(0, 0, 0, 80%);")

        self.next_image_button = QPushButton(">", self)
        self.next_image_button.setGeometry(50, 40, 30, 20)
        self.next_image_button.clicked.connect(self.show_next_image)
        self.next_image_button.setStyleSheet("color: white; background-color: rgba(0, 0, 0, 80%);")

        self.image_counter_label = QLabel("0/0", self)
        self.image_counter_label.setStyleSheet("color: white; background-color: rgba(0, 0, 0, 80%);")
        self.image_counter_label.setGeometry(90, 40, 80, 20)

        self.image_pixmap = None
        self.drag_pos = QPoint()
        self.resizing = False

        self.triangle_size = 40
        self.tolerance = 10
        self.target_rgb = (255, 255, 255)
        self.current_image_path = None

        self.db_name = "drugs.db"
        self._init_db()

        self.loaded_images_data = []  # Stores (id, drug_name, image_path, target_rgb, tolerance) for currently loaded drug
        self.current_image_index = -1

        self.load_image_dialog() # Initial image load or database load

    def create_header_controls(self):
        # Minimize button
        self.minimize_button = QPushButton("—", self) # Em dash character
        self.minimize_button.setStyleSheet(
            "background-color: rgba(0, 0, 0, 80%); color: white; border: none; font-weight: bold;"
        )
        self.minimize_button.setFixedSize(25, 25)
        self.minimize_button.clicked.connect(self.showMinimized)
        self.minimize_button.move(self.width() - 55, 5) # Position from right

        # Close button
        self.close_button = QPushButton("✕", self) # Multiplication x character
        self.close_button.setStyleSheet(
            "background-color: rgba(255, 0, 0, 80%); color: white; border: none; font-weight: bold;"
        )
        self.close_button.setFixedSize(25, 25)
        self.close_button.clicked.connect(self.close)
        self.close_button.move(self.width() - 30, 5) # Position from right

        # Ensure buttons are on top
        self.minimize_button.raise_()
        self.close_button.raise_()

    def _init_db(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drug_name TEXT NOT NULL,
                image_path TEXT NOT NULL,
                target_rgb_r INTEGER,
                target_rgb_g INTEGER,
                target_rgb_b INTEGER,
                tolerance INTEGER
            )
        ''')
        conn.commit()
        conn.close()

    def load_image_dialog(self):
        choice, ok = QInputDialog.getItem(
            self, "画像読み込み", "読み込み元を選択:",
            ["ファイルから読み込む", "データベースから読み込む"], 0, False
        )
        if ok and choice == "ファイルから読み込む":
            file_path, _ = QFileDialog.getOpenFileName(
                self, "画像ファイルを選択", "", "画像 (*.png *.jpg *.jpeg *.bmp)")
            if file_path:
                self.loaded_images_data = [] # Clear previously loaded DB images
                self.current_image_index = -1
                self.process_and_show(file_path, self.target_rgb, self.tolerance)
                self.update_image_counter()
            else:
                if not self.image_pixmap: # If no image was loaded at all
                    self.close()
        elif ok and choice == "データベースから読み込む":
            self.load_from_database()
        else:
            if not self.image_pixmap: # If no image was loaded at all
                self.close()

    def process_and_show(self, path, target_rgb, tolerance):
        self.current_image_path = path
        self.target_rgb = target_rgb
        self.tolerance = tolerance
        self.tolerance_slider.setValue(self.tolerance)
        self.slider_label.setText(f"透過範囲: {self.tolerance}") # Update label when loading from DB

        try:
            img = Image.open(path).convert("RGBA")
        except FileNotFoundError:
            QMessageBox.critical(self, "エラー", f"画像ファイルが見つかりません: {path}")
            return
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"画像の読み込み中にエラーが発生しました: {e}")
            return

        datas = img.getdata()
        new_data = []

        for item in datas:
            r, g, b, a = item
            if (
                abs(r - self.target_rgb[0]) <= self.tolerance and
                abs(g - self.target_rgb[1]) <= self.tolerance and
                abs(b - self.target_rgb[2]) <= self.tolerance
            ):
                new_data.append((r, g, b, 0))
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
        self.slider_label.move(10, 10)
        self.tolerance_slider.setGeometry(120, 10, 150, 20)
        self.prev_image_button.setGeometry(10, 40, 30, 20)
        self.next_image_button.setGeometry(50, 40, 30, 20)
        self.image_counter_label.setGeometry(90, 40, 80, 20)

        # Reposition minimize/close buttons
        self.minimize_button.move(self.width() - 55, 5)
        self.close_button.move(self.width() - 30, 5)

        self.update_display()

    def showEvent(self, event): # Added for re-display after minimize
        super().showEvent(event)
        self.update_display()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if clicked on minimize/close buttons, if so, don't drag/resize
            if self.close_button.geometry().contains(event.pos()) or \
               self.minimize_button.geometry().contains(event.pos()):
                event.ignore()
                return

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
            elif self._in_drag_header(event.pos()) and \
                 not self.close_button.geometry().contains(event.pos()) and \
                 not self.minimize_button.geometry().contains(event.pos()):
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

        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))

        points = [
            QPoint(self.width(), self.height()),
            QPoint(self.width() - self.triangle_size, self.height()),
            QPoint(self.width(), self.height() - self.triangle_size)
        ]
        painter.setBrush(Qt.GlobalColor.white)
        painter.drawPolygon(*points)

        painter.drawRect(0, 0, self.width(), self.header_height)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        change_color_action = menu.addAction("透過色を変更する")
        save_image_action = menu.addAction("画像を保存する (データベースへ)")
        load_drug_images_action = menu.addAction("薬剤の画像を読み込む (データベースから)")
        delete_image_action = menu.addAction("現在の画像を削除する (データベースから)")
        action = menu.exec(event.globalPos())
        if action == change_color_action:
            self.select_color_and_reprocess()
        elif action == save_image_action:
            self.save_image_to_database_dialog()
        elif action == load_drug_images_action:
            self.load_from_database()
        elif action == delete_image_action:
            self.confirm_and_delete_current_image()

    def select_color_and_reprocess(self):
        color = QColorDialog.getColor(initial=QColor(*self.target_rgb), parent=self)
        if color.isValid():
            self.target_rgb = (color.red(), color.green(), color.blue())
            if self.current_image_path:
                self.process_and_show(self.current_image_path, self.target_rgb, self.tolerance)

    def slider_changed(self, value):
        self.tolerance = value
        self.slider_label.setText(f"透過範囲: {value}")
        if self.current_image_path:
            # If currently displaying a DB image, update its in-memory tolerance
            if 0 <= self.current_image_index < len(self.loaded_images_data):
                # Update the tolerance in the loaded_images_data list for the current image
                current_image_entry = list(self.loaded_images_data[self.current_image_index])
                # Corrected line: Index 4 is for tolerance
                current_image_entry[4] = value
                self.loaded_images_data[self.current_image_index] = tuple(current_image_entry)

            self.process_and_show(self.current_image_path, self.target_rgb, self.tolerance)


    def save_image_to_database_dialog(self):
        if not self.current_image_path:
            QMessageBox.warning(self, "エラー", "表示されている画像がありません。")
            return

        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT drug_name FROM images ORDER BY drug_name")
        drug_names = [row[0] for row in cursor.fetchall()]
        conn.close()

        dialog = QDialog(self)
        dialog.setWindowTitle("薬剤名の選択または新規入力")
        layout = QVBoxLayout()

        list_label = QLabel("既存の薬剤名:")
        layout.addWidget(list_label)

        drug_list_widget = QListWidget()
        drug_list_widget.addItems(drug_names)
        drug_list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        layout.addWidget(drug_list_widget)

        new_drug_label = QLabel("または新しい薬剤名を入力:")
        layout.addWidget(new_drug_label)
        new_drug_input = QLineEdit()
        layout.addWidget(new_drug_input)

        buttons_layout = QHBoxLayout()
        ok_button = QPushButton("保存")
        cancel_button = QPushButton("キャンセル")
        buttons_layout.addWidget(ok_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)
        dialog.setLayout(layout)

        selected_drug_name = ""

        def on_ok_clicked():
            nonlocal selected_drug_name
            if new_drug_input.text().strip():
                selected_drug_name = new_drug_input.text().strip()
            elif drug_list_widget.currentItem():
                selected_drug_name = drug_list_widget.currentItem().text()
            dialog.accept()

        ok_button.clicked.connect(on_ok_clicked)
        cancel_button.clicked.connect(dialog.reject)

        # Corrected line: Use QDialog.DialogCode.Accepted
        if dialog.exec() == QDialog.DialogCode.Accepted and selected_drug_name:
            self._save_image_to_db(selected_drug_name)
        elif dialog.exec() == QDialog.DialogCode.Accepted and not selected_drug_name:
            QMessageBox.warning(self, "入力エラー", "薬剤名が選択または入力されていません。")


    def _save_image_to_db(self, drug_name):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO images (drug_name, image_path, target_rgb_r, target_rgb_g, target_rgb_b, tolerance)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                drug_name, self.current_image_path,
                self.target_rgb[0], self.target_rgb[1], self.target_rgb[2],
                self.tolerance
            ))
            conn.commit()
            QMessageBox.information(self, "保存完了", f"'{drug_name}' の画像を保存しました。")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "データベースエラー", f"画像の保存中にエラーが発生しました: {e}")
        finally:
            conn.close()

    def load_from_database(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT drug_name FROM images ORDER BY drug_name")
        drug_names = [row[0] for row in cursor.fetchall()]
        conn.close()

        if not drug_names:
            QMessageBox.information(self, "情報", "データベースに薬剤が登録されていません。")
            return

        drug_name, ok = QInputDialog.getItem(
            self, "薬剤を選択", "読み込む薬剤を選択してください:", drug_names, 0, False)

        if ok and drug_name:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, drug_name, image_path, target_rgb_r, target_rgb_g, target_rgb_b, tolerance
                FROM images WHERE drug_name = ?
                ORDER BY id
            ''', (drug_name,))
            self.loaded_images_data = []
            for row in cursor.fetchall():
                # Store (id, drug_name, image_path, (r,g,b), tolerance)
                self.loaded_images_data.append((row[0], row[1], row[2], (row[3], row[4], row[5]), row[6]))
            conn.close()

            if self.loaded_images_data:
                self.current_image_index = 0
                self.display_current_loaded_image()
            else:
                QMessageBox.information(self, "情報", f"'{drug_name}' に関連する画像が見つかりませんでした。")
        elif ok:
             QMessageBox.warning(self, "選択エラー", "薬剤が選択されていません。")

    def display_current_loaded_image(self):
        if 0 <= self.current_image_index < len(self.loaded_images_data):
            image_data = self.loaded_images_data[self.current_image_index]
            _id, drug_name, image_path, target_rgb, tolerance = image_data
            if os.path.exists(image_path):
                self.process_and_show(image_path, target_rgb, tolerance)
                self.update_image_counter()
            else:
                reply = QMessageBox.question(self, "ファイルが見つかりません",
                                    f"画像ファイル '{image_path}' が見つかりません。\nこの画像をデータベースから削除しますか？",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    self.delete_image_from_db(_id, prompt_user=False) # Delete without re-prompting
                    # Remove from in-memory list
                    self.loaded_images_data.pop(self.current_image_index)
                    # Try to display next image or re-load drug
                    if self.loaded_images_data:
                        self.current_image_index = min(self.current_image_index, len(self.loaded_images_data) - 1)
                        self.display_current_loaded_image()
                    else:
                        self.image_pixmap = None
                        self.label.clear()
                        self.current_image_path = None
                        self.update_image_counter()
                else:
                    # If user chooses not to delete, we need to handle this state.
                    # For simplicity, we can clear the display or stay on the broken entry.
                    # Clearing is safer to prevent endless loop on missing files.
                    self.image_pixmap = None
                    self.label.clear()
                    self.current_image_path = None
                    self.update_image_counter() # Update to 0/0 when no images

        else:
            self.image_pixmap = None
            self.label.clear()
            self.current_image_path = None
            self.update_image_counter() # Update to 0/0 when no images

    def show_next_image(self):
        if self.loaded_images_data:
            self.current_image_index = (self.current_image_index + 1) % len(self.loaded_images_data)
            self.display_current_loaded_image()

    def show_previous_image(self):
        if self.loaded_images_data:
            self.current_image_index = (self.current_image_index - 1 + len(self.loaded_images_data)) % len(self.loaded_images_data)
            self.display_current_loaded_image()

    def update_image_counter(self):
        total = len(self.loaded_images_data)
        current = self.current_image_index + 1 if total > 0 else 0
        self.image_counter_label.setText(f"{current}/{total}")

    def confirm_and_delete_current_image(self):
        if not self.loaded_images_data or self.current_image_index == -1:
            QMessageBox.information(self, "情報", "削除する画像が選択されていません。")
            return

        current_image_entry = self.loaded_images_data[self.current_image_index]
        image_id, drug_name, image_path, _, _ = current_image_entry

        reply = QMessageBox.question(self, "削除確認",
                                     f"現在の画像 (薬剤名: '{drug_name}', パス: '{os.path.basename(image_path)}') をデータベースから削除しますか？\nこの操作は元に戻せません。",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_image_from_db(image_id, prompt_user=True)
            # Remove from in-memory list
            self.loaded_images_data.pop(self.current_image_index)
            # Adjust index and display next image
            if self.loaded_images_data:
                self.current_image_index = min(self.current_image_index, len(self.loaded_images_data) - 1)
                self.display_current_loaded_image()
            else:
                self.image_pixmap = None
                self.label.clear()
                self.current_image_path = None
                self.update_image_counter()

    def delete_image_from_db(self, image_id, prompt_user=True):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM images WHERE id = ?", (image_id,))
            conn.commit()
            if prompt_user:
                QMessageBox.information(self, "削除完了", "画像をデータベースから削除しました。")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "データベースエラー", f"画像の削除中にエラーが発生しました: {e}")
        finally:
            conn.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = TransparentImageViewer()
    viewer.show()
    sys.exit(app.exec())
