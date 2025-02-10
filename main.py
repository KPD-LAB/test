import sys
import re
from PyQt5 import QtCore
from PyQt5.QtWidgets import (QApplication, QDialog, QTableWidgetItem,
                             QHeaderView, QCheckBox, QPushButton, QHBoxLayout, QFileDialog, QMenu, QLineEdit, QTextEdit, QVBoxLayout)
from PyQt5.QtCore import QTimer, Qt
from PyQt5 import QtGui
import serial
from serial.tools import list_ports
from form_ui import Ui_Dialog


class MyDialog(QDialog, Ui_Dialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # Настройка светлого стиля
        self.setStyleSheet("""
            QWidget {
                background-color: #F0F0F0;
                color: #333333;
            }
            QTableWidget {
                background-color: white;
                gridline-color: #CCCCCC;
            }
            QHeaderView::section {
                background-color: #E0E0E0;
            }
        """)

        # Добавляем новые элементы управления
        self.add_controls()

        # Инициализация Serial
        self.serial_port = None
        self.is_connected = False
        self.auto_scroll = True
        self.master_pressed = False
        self.slave_pressed = False

        # Настройка таблиц
        tables = [self.tableWidget_2, self.tableWidget_4, self.tableWidget_3]
        for table in tables:
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
            table.verticalHeader().setVisible(False)
            table.setAlternatingRowColors(True)
            table.verticalScrollBar().valueChanged.connect(self.sync_scroll)
            table.itemSelectionChanged.connect(self.sync_selection)
            table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            table.customContextMenuRequested.connect(self.show_context_menu)

        # Таймер для чтения данных
        self.read_timer = QTimer()
        self.read_timer.timeout.connect(self.read_data)

        # Подключение кнопок
        self.pushButton.clicked.connect(self.update_ports)
        self.pushButton_2.clicked.connect(self.toggle_connection)
        self.pushButton_3.clicked.connect(self.save_notepad)
        self.pushButton_4.clicked.connect(self.clear_textedit)  # Кнопка Clear
        self.pushButton_5.pressed.connect(self.master_press)  # Кнопка Master
        self.pushButton_5.released.connect(self.master_release)
        self.pushButton_6.pressed.connect(self.slave_press)  # Кнопка Slave
        self.pushButton_6.released.connect(self.slave_release)

        # Установка radiobutton_2 по умолчанию
        self.radioButton_2.setChecked(True)

        # Поиск и подсветка текста
        self.lineEdit.textChanged.connect(self.search_text)

        # Кнопки для навигации по результатам поиска
        self.search_prev_button.clicked.connect(self.search_previous)
        self.search_next_button.clicked.connect(self.search_next)

        self.update_ports()

    def add_controls(self):
        """Добавление новых элементов управления"""
        # Создаем горизонтальный layout для поиска
        search_layout = QHBoxLayout()

        # Поле для ввода текста поиска
        self.lineEdit = QLineEdit(self)
        search_layout.addWidget(self.lineEdit)

        # Кнопка для поиска предыдущего найденного варианта
        self.search_prev_button = QPushButton("<", self)
        search_layout.addWidget(self.search_prev_button)

        # Кнопка для поиска следующего найденного варианта
        self.search_next_button = QPushButton(">", self)
        search_layout.addWidget(self.search_next_button)

        # Добавляем layout в основной интерфейс
        self.verticalLayout.insertLayout(0, search_layout)

        # Создаем горизонтальный layout для управления таблицами
        control_layout = QHBoxLayout()

        # Кнопка очистки таблиц
        clear_button = QPushButton("Очистить таблицы")
        clear_button.clicked.connect(self.clear_tables)
        control_layout.addWidget(clear_button)

        # Чекбокс автопрокрутки
        self.auto_scroll_check = QCheckBox("Автопрокрутка")
        self.auto_scroll_check.setChecked(True)
        self.auto_scroll_check.stateChanged.connect(self.toggle_auto_scroll)
        control_layout.addWidget(self.auto_scroll_check)

        # Добавляем layout в основной интерфейс
        self.verticalLayout.insertLayout(1, control_layout)

    def update_controls_state(self):
        """Обновление состояния элементов управления"""
        self.pushButton.setEnabled(not self.is_connected)
        self.comboBox.setEnabled(not self.is_connected)

    def clear_tables(self):
        """Очистка таблиц"""
        self.tableWidget_2.setRowCount(0)
        self.tableWidget_4.setRowCount(0)
        self.tableWidget_3.setRowCount(0)
        print("Таблицы очищены")

    def clear_textedit(self):
        """Очистка textEdit2"""
        self.textEdit_2.clear()

    def master_press(self):
        """Обработка нажатия кнопки Master"""
        self.master_pressed = True

    def master_release(self):
        """Обработка отпускания кнопки Master"""
        self.master_pressed = False

    def slave_press(self):
        """Обработка нажатия кнопки Slave"""
        self.slave_pressed = True

    def slave_release(self):
        """Обработка отпускания кнопки Slave"""
        self.slave_pressed = False

    def toggle_auto_scroll(self, state):
        """Включение/выключение автопрокрутки"""
        self.auto_scroll = state == Qt.Checked
        print(f"Автопрокрутка {'включена' if self.auto_scroll else 'отключена'}")

    def update_ports(self):
        """Обновление списка портов"""
        self.comboBox.clear()
        ports = [port.device for port in list_ports.comports()]
        self.comboBox.addItems(ports)
        print("Список портов обновлен")

    def toggle_connection(self):
        """Подключение/отключение от порта"""
        if self.is_connected:
            self.disconnect_port()
        else:
            self.connect_to_port()
        self.update_controls_state()

    def connect_to_port(self):
        """Подключение к выбранному порту"""
        port = self.comboBox.currentText()
        try:
            self.serial_port = serial.Serial(
                port=port,
                baudrate=115200,
                timeout=0.1
            )
            self.is_connected = True
            self.pushButton_2.setText("Отключиться")
            self.read_timer.start(50)
            print(f"Подключено к {port}")
        except Exception as e:
            print(f"Ошибка подключения: {str(e)}")

    def disconnect_port(self):
        """Отключение от порта"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.is_connected = False
        self.pushButton_2.setText("Подключиться")
        self.read_timer.stop()
        print("Отключено")

    def read_data(self):
        """Чтение данных из порта"""
        if self.serial_port and self.serial_port.in_waiting:
            try:
                raw_data = self.serial_port.readline().decode('utf-8').strip()
                if raw_data:
                    self.parse_and_display_data(raw_data)
                    self.process_textedit_data(raw_data)
            except UnicodeDecodeError:
                print("Ошибка декодирования данных")

    def process_textedit_data(self, data):
        """Обработка данных для textEdit2"""
        pattern = r"\[(Master|Slave):(\d+) (\w+):(\d+)ms:(\d+)ms:(\d+)ms\]"
        match = re.match(pattern, data)
        if match:
            source = match.group(1)
            data_hex = match.group(3)
            millis = match.group(6)

            if (self.master_pressed and source == "Master") or (self.slave_pressed and source == "Slave"):
                if self.radioButton.isChecked():  # [Millis]
                    self.textEdit_2.append(f"[{millis}] {data_hex}")
                elif self.radioButton_4.isChecked():  # [0x]
                    self.textEdit_2.append(f"0x{data_hex}")
                elif self.radioButton_2.isChecked():  # [NONE]
                    self.textEdit_2.append(f"{data_hex}")
                elif self.radioButton_3.isChecked():  # [Source]
                    self.textEdit_2.append(f"[{source}] {data_hex}")

    def parse_and_display_data(self, data):
        """Парсинг и отображение данных"""
        pattern = r"\[(Master|Slave):(\d+) (\w+):(\d+)ms:(\d+)ms:(\d+)ms\]"
        match = re.match(pattern, data)
        if match:
            source = match.group(1)
            bit9 = match.group(2)
            data_hex = match.group(3)
            offset = match.group(4)
            offsetX = match.group(5)
            millis = match.group(6)

            # Определяем целевые таблицы
            if source == "Master":
                data_table = self.tableWidget_4
                offset_table = self.tableWidget_3
            else:
                data_table = self.tableWidget_2
                offset_table = self.tableWidget_3

            # Добавляем строки во все таблицы
            row_position = data_table.rowCount()
            for table in [self.tableWidget_2, self.tableWidget_4, self.tableWidget_3]:
                table.insertRow(row_position)

            # Заполняем таблицу данных
            target_table = self.tableWidget_4 if source == "Master" else self.tableWidget_2
            target_table.setItem(row_position, 0, QTableWidgetItem(bit9))
            target_table.setItem(row_position, 1, QTableWidgetItem(data_hex))

            # Заполняем таблицу временных меток
            if source == "Master":
                self.tableWidget_3.setItem(row_position, 2, QTableWidgetItem(offset))
            else:
                self.tableWidget_3.setItem(row_position, 3, QTableWidgetItem(offset))
            self.tableWidget_3.setItem(row_position, 0, QTableWidgetItem(millis))
            self.tableWidget_3.setItem(row_position, 1, QTableWidgetItem(offsetX))

            # Автопрокрутка
            if self.auto_scroll:
                for table in [self.tableWidget_2, self.tableWidget_4, self.tableWidget_3]:
                    table.scrollToBottom()

    def sync_scroll(self, value):
        """Синхронизация прокрутки таблиц"""
        tables = [self.tableWidget_2, self.tableWidget_4, self.tableWidget_3]
        for table in tables:
            if table.verticalScrollBar() != self.sender():
                table.verticalScrollBar().setValue(value)

    def sync_selection(self):
        """Синхронизация выбора строк"""
        tables = [self.tableWidget_2, self.tableWidget_4, self.tableWidget_3]
        current_table = self.sender()
        row = current_table.currentRow()

        for table in tables:
            if table != current_table:
                table.selectRow(row)

    def save_notepad(self):
        """Сохранение содержимого textEdit в файл"""
        options = QFileDialog.Options()  # Используем QFileDialog из PyQt5.QtWidgets
        file_name, _ = QFileDialog.getSaveFileName(self, "Сохранить файл", "", "Text Files (*.txt);;All Files (*)", options=options)
        if file_name:
            with open(file_name, 'w') as file:
                file.write(self.textEdit.toPlainText())

    def search_text(self):
        """Поиск и подсветка текста в textEdit_2"""
        search_text = self.lineEdit.text()
        print(f"Searching for: {search_text}")  # Debugging statement
        cursor = self.textEdit_2.textCursor()

        # Сбрасываем форматирование
        cursor.select(QtGui.QTextCursor.Document)
        cursor.setCharFormat(QtGui.QTextCharFormat())
        cursor.clearSelection()

        if search_text:
            format = QtGui.QTextCharFormat()
            format.setBackground(QtGui.QColor("yellow"))

            self.textEdit_2.moveCursor(QtGui.QTextCursor.Start)
            while self.textEdit_2.find(search_text):
                cursor.mergeCharFormat(format)

    def search_next(self):
        """Поиск следующего совпадения"""
        cursor = self.textEdit_2.textCursor()
        if cursor.hasSelection():
            cursor.movePosition(QtGui.QTextCursor.NextWord)
        self.search_text()

    def search_previous(self):
        """Поиск предыдущего совпадения"""
        cursor = self.textEdit_2.textCursor()
        if cursor.hasSelection():
            cursor.movePosition(QtGui.QTextCursor.PreviousWord)
        self.search_text()

    def show_context_menu(self, pos):
        """Контекстное меню для таблиц и текстовых полей"""
        menu = QMenu(self)
        send_to_notepad_action = menu.addAction("Отправить выбранный текст в Notepad")

        # Используем глобальные координаты через mapToGlobal
        global_pos = self.sender().mapToGlobal(pos)
        action = menu.exec_(global_pos)

        if action == send_to_notepad_action:
            selected_text = ""
            if self.sender() in [self.tableWidget_2, self.tableWidget_4, self.tableWidget_3]:
                selected_items = self.sender().selectedItems()
                if selected_items:
                    selected_text = selected_items[0].text()
            elif self.sender() == self.textEdit_2:
                selected_text = self.textEdit_2.textCursor().selectedText()

            if selected_text:
                self.textEdit.append(selected_text)

    def enterEvent(self, event):
        """Отключение auto_scroll при наведении мыши на таблицу"""
        self.auto_scroll = False
        self.auto_scroll_check.setChecked(False)

    def leaveEvent(self, event):
        """Включение auto_scroll при уходе мыши с таблицы"""
        self.auto_scroll = True
        self.auto_scroll_check.setChecked(True)

    def closeEvent(self, event):
        """Обработка закрытия окна"""
        self.disconnect_port()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    dialog = MyDialog()
    dialog.show()
    sys.exit(app.exec_())