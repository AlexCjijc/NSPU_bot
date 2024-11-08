import time
import subprocess
import gc  # Для управления сборкой мусора в Python
import schedule

def run_script(script_name):
    """Запускает указанный скрипт и возвращает его процесс."""
    print(f"Запуск {script_name}...")

    return subprocess.Popen(['python3', script_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def restart_scripts():
    """Функция для перезапуска скриптов bot\_main.py и newsletter.py."""
    processes = {
        'bot_main.py': run_script('bot_main.py'),
        'newsletter.py': run_script('newsletter.py')
    }
    print("Скрипты перезапущены.")

def monitor_processes(processes):
    """Мониторинг списка процессов и перезапуск в случае их падения."""
    last_clean_time = time.time()
    while True:
        # Очистка каждые 30 минут
        if time.time() - last_clean_time > 79200:
            clean_system()
            last_clean_time = time.time()

        for script_name, process in list(processes.items()):
            if process.poll() is not None:  # Процесс завершился
                out, err = process.communicate()
                print(f"{script_name} завершил работу. Вывод:\n{out.decode()}\nОшибки:\n{err.decode()}")
                processes[script_name] = run_script(script_name)
                print(f"{script_name} был перезапущен.")

        # Явное указание на выполнение сборки мусора
        gc.collect()
        time.sleep(3)


def clean_system():
    """Очищает систему от мусора, кэша и временных файлов с использованием bleachbit с пресетами."""
    print("Очистка системы...")
    subprocess.run(
        ['sudo', 'bleachbit', '--clean', 'apt.clean', 'apt.autoremove'])  # Использует заранее настроенные задания для очистки



clean_system()
schedule.every().day.at("06:00").do(restart_scripts)

if __name__ == "__main__":
    while True:
        schedule.run_pending()
        processes = {
            'bot_main.py': run_script('bot_main.py'),
            'newsletter.py': run_script('newsletter.py')
        }
        monitor_processes(processes)
