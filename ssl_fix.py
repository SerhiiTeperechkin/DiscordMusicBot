"""
Скрипт для исправления проблем с SSL сертификатами в Python
Запустите этот скрипт перед запуском основного бота, если возникают ошибки 
CERTIFICATE_VERIFY_FAILED при работе с YouTube.
"""

import os
import sys
import ssl
import certifi
import subprocess
import platform

def check_cert_path():
    """Проверяет пути к сертификатам SSL."""
    print("Проверка путей к SSL сертификатам:")
    try:
        cert_paths = ssl.get_default_verify_paths()
        print(f"- cafile: {cert_paths.cafile}")
        print(f"- capath: {cert_paths.capath}")
        print(f"- openssl_cafile: {cert_paths.openssl_cafile}")
        print(f"- openssl_capath: {cert_paths.openssl_capath}")
        
        certifi_path = certifi.where()
        print(f"\nПуть к сертификатам certifi: {certifi_path}")
        
        if os.path.exists(certifi_path):
            print("✅ Файл сертификатов certifi существует")
        else:
            print("❌ Файл сертификатов certifi НЕ существует")
    except Exception as e:
        print(f"Ошибка при проверке сертификатов: {e}")

def update_certificates():
    """Обновляет сертификаты certifi."""
    print("\nОбновление сертификатов...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "certifi"])
        print("✅ Сертификаты успешно обновлены")
    except Exception as e:
        print(f"❌ Ошибка при обновлении сертификатов: {e}")

def disable_ssl_verification():
    """Отключает проверку SSL сертификатов."""
    print("\nНастройка отключения проверки SSL...")
    try:
        # Сохраняем оригинальный контекст
        ssl._create_default_https_context_orig = ssl._create_default_https_context
        # Устанавливаем контекст без проверки
        ssl._create_default_https_context = ssl._create_unverified_context
        print("✅ Проверка SSL отключена для текущей сессии")
        
        # Проверяем, правильно ли применились настройки
        context = ssl._create_default_https_context()
        if context.verify_mode == ssl.CERT_NONE:
            print("✅ Подтверждено: проверка SSL сертификатов отключена")
        else:
            print("❌ Не удалось отключить проверку SSL сертификатов")
    except Exception as e:
        print(f"❌ Ошибка при настройке SSL: {e}")

def main():
    """Основная функция скрипта."""
    print(f"Скрипт исправления проблем с SSL для Python {sys.version}")
    print(f"Операционная система: {platform.system()} {platform.version()}")
    
    check_cert_path()
    
    choice = input("\nВыберите действие:\n1. Обновить сертификаты\n2. Отключить проверку SSL\n3. Выполнить оба действия\n4. Выйти\nВаш выбор (1-4): ")
    
    if choice == '1':
        update_certificates()
    elif choice == '2':
        disable_ssl_verification()
        print("\nДля отключения проверки SSL в основном скрипте, добавьте следующие строки в начало файла main.py:")
        print("import ssl")
        print("ssl._create_default_https_context = ssl._create_unverified_context")
    elif choice == '3':
        update_certificates()
        disable_ssl_verification()
        print("\nДля отключения проверки SSL в основном скрипте, добавьте следующие строки в начало файла main.py:")
        print("import ssl")
        print("ssl._create_default_https_context = ssl._create_unverified_context")
    else:
        print("Выход без изменений")
        return
    
    print("\nПроверка завершена. Если проблемы с SSL продолжаются, попробуйте исправить системное время или использовать VPN.")

if __name__ == "__main__":
    main()
