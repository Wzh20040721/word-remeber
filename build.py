import PyInstaller.__main__
import platform
import os


def build_app():
    """构建应用程序"""

    # 基本参数
    args = [
        'main.py',  # 主程序文件
        '--name=WordMemory',  # 应用名称
        '--windowed',  # 不显示控制台窗口
        '--onefile',  # 打包成单个文件
        '--clean',  # 清理临时文件
        '--add-data=config.json:.',  # 包含配置文件（如果存在）
    ]

    # 根据操作系统添加图标
    system = platform.system()
    if system == 'Windows':
        # Windows 图标
        if os.path.exists('icon.ico'):
            args.append('--icon=icon.ico')
    elif system == 'Darwin':
        # macOS 图标
        if os.path.exists('icon.icns'):
            args.append('--icon=icon.icns')

    # 执行打包
    PyInstaller.__main__.run(args)

    print("\n打包完成！")
    print(f"可执行文件位于: dist/WordMemory{'.exe' if system == 'Windows' else ''}")


if __name__ == '__main__':
    build_app()