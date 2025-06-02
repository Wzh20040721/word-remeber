import sys
import os
import json
import hashlib
from datetime import datetime, timedelta
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import requests
from supabase import create_client, Client
import random
try:
    from translator_free import FreeTranslator
except ImportError:
    FreeTranslator = None

# 配置文件
CONFIG_FILE = "config.json"

class Config:
    """配置管理类"""
    def __init__(self):
        self.supabase_url = ""
        self.supabase_key = ""
        self.youdao_app_key = ""
        self.youdao_app_secret = ""
        self.load_config()
    
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.supabase_url = data.get('supabase_url', '')
                self.supabase_key = data.get('supabase_key', '')
                self.youdao_app_key = data.get('youdao_app_key', '')
                self.youdao_app_secret = data.get('youdao_app_secret', '')
    
    def save_config(self):
        data = {
            'supabase_url': self.supabase_url,
            'supabase_key': self.supabase_key,
            'youdao_app_key': self.youdao_app_key,
            'youdao_app_secret': self.youdao_app_secret
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

class DatabaseManager:
    """数据库管理类"""
    def __init__(self, config):
        self.config = config
        self.supabase = None
        self.user_id = None
        
    def connect(self):
        """连接到 Supabase"""
        if self.config.supabase_url and self.config.supabase_key:
            self.supabase = create_client(self.config.supabase_url, self.config.supabase_key)
            return True
        return False
    
    def login(self, username, password):
        """用户登录"""
        if not self.supabase:
            return False, "数据库未连接"
        
        try:
            # 查询用户
            result = self.supabase.table('users').select("*").eq('username', username).execute()
            
            if not result.data:
                return False, "用户不存在"
            
            user = result.data[0]
            # 简单的密码验证（实际应用中应使用更安全的方式）
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            if user['password_hash'] == password_hash:
                self.user_id = user['id']
                return True, "登录成功"
            else:
                return False, "密码错误"
                
        except Exception as e:
            return False, f"登录失败: {str(e)}"
    
    def register(self, username, password):
        """用户注册"""
        if not self.supabase:
            return False, "数据库未连接"
        
        try:
            # 检查用户名是否存在
            result = self.supabase.table('users').select("*").eq('username', username).execute()
            
            if result.data:
                return False, "用户名已存在"
            
            # 创建新用户
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            user_data = {
                'username': username,
                'password_hash': password_hash,
                'created_at': datetime.now().isoformat()
            }
            
            result = self.supabase.table('users').insert(user_data).execute()
            
            if result.data:
                return True, "注册成功"
            else:
                return False, "注册失败"
                
        except Exception as e:
            return False, f"注册失败: {str(e)}"
    
    def add_word(self, word, translation, word_type='word'):
        """添加单词或短语"""
        if not self.supabase or not self.user_id:
            return False, "请先登录"
        
        try:
            word_data = {
                'user_id': self.user_id,
                'word': word,
                'translation': translation,
                'type': word_type,
                'created_at': datetime.now().isoformat(),
                'review_count': 0,
                'last_review': None,
                'next_review': datetime.now().isoformat()
            }
            
            result = self.supabase.table('words').insert(word_data).execute()
            
            if result.data:
                return True, "添加成功"
            else:
                return False, "添加失败"
                
        except Exception as e:
            return False, f"添加失败: {str(e)}"
    
    def get_words_for_review(self):
        """获取需要复习的单词"""
        if not self.supabase or not self.user_id:
            return []
        
        try:
            # 获取今天需要复习的单词
            today = datetime.now().isoformat()
            result = self.supabase.table('words').select("*").eq('user_id', self.user_id).lte('next_review', today).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"获取复习单词失败: {str(e)}")
            return []
    
    def update_review(self, word_id, remembered):
        """更新复习记录"""
        if not self.supabase:
            return False
        
        try:
            # 获取当前单词信息
            result = self.supabase.table('words').select("*").eq('id', word_id).execute()
            
            if not result.data:
                return False
            
            word = result.data[0]
            review_count = word['review_count'] + 1
            
            # 根据记忆情况计算下次复习时间
            if remembered:
                # 记住了，增加间隔时间
                days = min(2 ** review_count, 30)  # 最多30天
            else:
                # 没记住，重置
                days = 1
                review_count = 0
            
            next_review = (datetime.now() + timedelta(days=days)).isoformat()
            
            # 更新数据
            update_data = {
                'review_count': review_count,
                'last_review': datetime.now().isoformat(),
                'next_review': next_review
            }
            
            self.supabase.table('words').update(update_data).eq('id', word_id).execute()
            
            return True
            
        except Exception as e:
            print(f"更新复习记录失败: {str(e)}")
            return False

class Translator:
    """翻译类"""
    def __init__(self, config):
        self.config = config
        self.free_translator = FreeTranslator() if FreeTranslator else None
    
    def translate_youdao(self, text):
        """使用有道翻译API"""
        if not self.config.youdao_app_key or not self.config.youdao_app_secret:
            return None, "未配置有道翻译API"
        
        try:
            import uuid
            import time
            
            app_key = self.config.youdao_app_key
            app_secret = self.config.youdao_app_secret
            
            # 生成参数
            salt = str(uuid.uuid4())
            curtime = str(int(time.time()))
            
            # 生成签名
            sign_str = app_key + text + salt + curtime + app_secret
            sign = hashlib.sha256(sign_str.encode()).hexdigest()
            
            # 请求参数
            params = {
                'q': text,
                'from': 'auto',
                'to': 'zh-CHS',
                'appKey': app_key,
                'salt': salt,
                'sign': sign,
                'signType': 'v3',
                'curtime': curtime
            }
            
            # 发送请求
            response = requests.post('https://openapi.youdao.com/api', params=params, timeout=5)
            result = response.json()
            
            if result.get('errorCode') == '0':
                translation = result.get('translation', [''])[0]
                return translation, None
            else:
                return None, f"翻译失败: {result.get('errorCode')}"
                
        except Exception as e:
            return None, f"翻译失败: {str(e)}"
    
    def translate_simple(self, word):
        """简单的单词翻译（可以后续接入词典API）"""
        # 这里可以集成免费的词典API或者本地词典
        # 暂时返回示例
        return f"{word} 的中文翻译", None
    
    def translate(self, text):
        """统一的翻译接口"""
        # 优先使用免费翻译
        if self.free_translator:
            result, error = self.free_translator.translate(text)
            if result:
                return result, None
        
        # 如果免费翻译失败，尝试有道翻译
        if self.config.youdao_app_key:
            return self.translate_youdao(text)
        
        # 最后使用简单翻译
        return self.translate_simple(text)

class LoginDialog(QDialog):
    """登录对话框"""
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('登录')
        self.setFixedSize(300, 200)
        
        layout = QVBoxLayout()
        
        # 用户名
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('用户名')
        layout.addWidget(self.username_input)
        
        # 密码
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('密码')
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.login_button = QPushButton('登录')
        self.login_button.clicked.connect(self.login)
        button_layout.addWidget(self.login_button)
        
        self.register_button = QPushButton('注册')
        self.register_button.clicked.connect(self.register)
        button_layout.addWidget(self.register_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f0f0;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton {
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#login {
                background-color: #007AFF;
                color: white;
            }
            QPushButton#register {
                background-color: #e0e0e0;
                color: #333;
            }
            QPushButton:hover {
                opacity: 0.8;
            }
        """)
        
        self.login_button.setObjectName('login')
        self.register_button.setObjectName('register')
    
    def login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, '提示', '请输入用户名和密码')
            return
        
        success, message = self.db_manager.login(username, password)
        
        if success:
            self.accept()
        else:
            QMessageBox.warning(self, '登录失败', message)
    
    def register(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, '提示', '请输入用户名和密码')
            return
        
        success, message = self.db_manager.register(username, password)
        
        if success:
            QMessageBox.information(self, '注册成功', '注册成功，请登录')
        else:
            QMessageBox.warning(self, '注册失败', message)

class ConfigDialog(QDialog):
    """配置对话框"""
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('配置')
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        # Supabase 配置
        layout.addWidget(QLabel('Supabase URL:'))
        self.supabase_url_input = QLineEdit(self.config.supabase_url)
        layout.addWidget(self.supabase_url_input)
        
        layout.addWidget(QLabel('Supabase Key:'))
        self.supabase_key_input = QLineEdit(self.config.supabase_key)
        layout.addWidget(self.supabase_key_input)
        
        # 有道翻译配置
        layout.addWidget(QLabel('有道翻译 App Key:'))
        self.youdao_key_input = QLineEdit(self.config.youdao_app_key)
        layout.addWidget(self.youdao_key_input)
        
        layout.addWidget(QLabel('有道翻译 App Secret:'))
        self.youdao_secret_input = QLineEdit(self.config.youdao_app_secret)
        layout.addWidget(self.youdao_secret_input)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        save_button = QPushButton('保存')
        save_button.clicked.connect(self.save_config)
        button_layout.addWidget(save_button)
        
        cancel_button = QPushButton('取消')
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def save_config(self):
        self.config.supabase_url = self.supabase_url_input.text().strip()
        self.config.supabase_key = self.supabase_key_input.text().strip()
        self.config.youdao_app_key = self.youdao_key_input.text().strip()
        self.config.youdao_app_secret = self.youdao_secret_input.text().strip()
        
        self.config.save_config()
        self.accept()

class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.translator = Translator(self.config)
        self.init_ui()
        self.setup_database()
    
    def init_ui(self):
        self.setWindowTitle('单词记忆助手')
        self.setGeometry(100, 100, 800, 600)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 工具栏
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        config_action = QAction('配置', self)
        config_action.triggered.connect(self.show_config)
        toolbar.addAction(config_action)
        
        # 标签页
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # 添加单词页面
        self.add_word_tab = self.create_add_word_tab()
        self.tabs.addTab(self.add_word_tab, '添加单词')
        
        # 复习页面
        self.review_tab = self.create_review_tab()
        self.tabs.addTab(self.review_tab, '每日复习')
        
        # 设置样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTabWidget {
                background-color: white;
            }
            QTabBar::tab {
                padding: 10px 20px;
                margin-right: 5px;
                background-color: #e0e0e0;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
                color: #007AFF;
            }
            QPushButton {
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
                background-color: #007AFF;
                color: white;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QLineEdit, QTextEdit {
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-size: 16px;
            }
            QLabel {
                font-size: 14px;
                color: #666;
            }
        """)
    
    def create_add_word_tab(self):
        """创建添加单词标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 输入区域
        input_layout = QHBoxLayout()
        
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText('输入单词或短语')
        input_layout.addWidget(self.word_input)
        
        translate_button = QPushButton('翻译')
        translate_button.clicked.connect(self.translate_word)
        input_layout.addWidget(translate_button)
        
        layout.addLayout(input_layout)
        
        # 翻译结果
        self.translation_display = QTextEdit()
        self.translation_display.setPlaceholderText('翻译结果')
        self.translation_display.setMaximumHeight(100)
        layout.addWidget(self.translation_display)
        
        # 添加按钮
        add_button = QPushButton('添加到生词本')
        add_button.clicked.connect(self.add_word)
        layout.addWidget(add_button)
        
        layout.addStretch()
        widget.setLayout(layout)
        
        return widget
    
    def create_review_tab(self):
        """创建复习标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 单词显示区域
        self.review_word_label = QLabel('点击开始复习')
        self.review_word_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.review_word_label.setStyleSheet("""
            font-size: 32px;
            font-weight: bold;
            color: #333;
            padding: 40px;
            background-color: white;
            border-radius: 10px;
            border: 1px solid #ddd;
        """)
        layout.addWidget(self.review_word_label)
        
        # 翻译显示区域
        self.review_translation_label = QLabel('')
        self.review_translation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.review_translation_label.setStyleSheet("""
            font-size: 24px;
            color: #666;
            padding: 20px;
        """)
        layout.addWidget(self.review_translation_label)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.show_translation_button = QPushButton('显示翻译')
        self.show_translation_button.clicked.connect(self.show_translation)
        button_layout.addWidget(self.show_translation_button)
        
        self.remember_button = QPushButton('记住了')
        self.remember_button.clicked.connect(lambda: self.next_review_word(True))
        self.remember_button.setStyleSheet('background-color: #28a745;')
        button_layout.addWidget(self.remember_button)
        
        self.forget_button = QPushButton('没记住')
        self.forget_button.clicked.connect(lambda: self.next_review_word(False))
        self.forget_button.setStyleSheet('background-color: #dc3545;')
        button_layout.addWidget(self.forget_button)
        
        layout.addLayout(button_layout)
        
        # 开始复习按钮
        self.start_review_button = QPushButton('开始今日复习')
        self.start_review_button.clicked.connect(self.start_review)
        layout.addWidget(self.start_review_button)
        
        layout.addStretch()
        widget.setLayout(layout)
        
        return widget
    
    def setup_database(self):
        """设置数据库连接"""
        if not self.db_manager.connect():
            # 显示配置对话框
            dialog = ConfigDialog(self.config)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.db_manager.connect()
        
        # 显示登录对话框
        login_dialog = LoginDialog(self.db_manager)
        if login_dialog.exec() != QDialog.DialogCode.Accepted:
            sys.exit()
    
    def show_config(self):
        """显示配置对话框"""
        dialog = ConfigDialog(self.config)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 重新连接数据库
            self.db_manager.connect()
    
    def translate_word(self):
        """翻译单词"""
        word = self.word_input.text().strip()
        if not word:
            return
        
        # 使用统一的翻译接口
        translation, error = self.translator.translate(word)
        
        if translation:
            self.translation_display.setText(translation)
        else:
            self.translation_display.setText(f"翻译失败: {error}")
    
    def add_word(self):
        """添加单词到数据库"""
        word = self.word_input.text().strip()
        translation = self.translation_display.toPlainText().strip()
        
        if not word or not translation:
            QMessageBox.warning(self, '提示', '请输入单词并翻译')
            return
        
        word_type = 'phrase' if len(word.split()) > 1 else 'word'
        success, message = self.db_manager.add_word(word, translation, word_type)
        
        if success:
            QMessageBox.information(self, '成功', '已添加到生词本')
            self.word_input.clear()
            self.translation_display.clear()
        else:
            QMessageBox.warning(self, '失败', message)
    
    def start_review(self):
        """开始复习"""
        self.review_words = self.db_manager.get_words_for_review()
        
        if not self.review_words:
            QMessageBox.information(self, '提示', '今天没有需要复习的单词')
            return
        
        random.shuffle(self.review_words)
        self.current_review_index = 0
        self.show_review_word()
        
        # 隐藏开始按钮
        self.start_review_button.hide()
    
    def show_review_word(self):
        """显示当前复习单词"""
        if self.current_review_index < len(self.review_words):
            word = self.review_words[self.current_review_index]
            self.review_word_label.setText(word['word'])
            self.review_translation_label.setText('')
            self.current_word = word
        else:
            # 复习完成
            self.review_word_label.setText('今日复习完成！')
            self.review_translation_label.setText('')
            self.start_review_button.show()
    
    def show_translation(self):
        """显示翻译"""
        if hasattr(self, 'current_word'):
            self.review_translation_label.setText(self.current_word['translation'])
    
    def next_review_word(self, remembered):
        """下一个复习单词"""
        if hasattr(self, 'current_word'):
            self.db_manager.update_review(self.current_word['id'], remembered)
            self.current_review_index += 1
            self.show_review_word()

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
