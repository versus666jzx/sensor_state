import configer as configer
import hashlib
import os
import subprocess
import threading
import sqlite3
import re


def create_paths():
    """ Создает необходимую структуру каталогов, файлов и БД для работы скрипта, если они
     не были созданы ранее

     """
    if os.path.exists(configer.get_setting('Paths', 'sensor_state_main_dir')):
        pass
    else:
        os.mkdir(configer.get_setting('Paths', 'sensor_state_main_dir'))

    if os.path.exists(configer.get_setting('Paths', 'sensor_state_traf_dir')):
        pass
    else:
        os.mkdir(configer.get_setting('Paths', 'sensor_state_traf_dir'))

    if os.path.exists(configer.get_setting('Paths', 'sensor_state_errlog_dir')):
        pass
    else:
        os.mkdir(configer.get_setting('Paths', 'sensor_state_errlog_dir'))
    if not os.path.exists(configer.get_setting('DB', 'db_path')):
        with sqlite3.connect(configer.get_setting('DB', 'db_path')) as conn:
            conn.executescript(""" 
            CREATE TABLE sensor_data (
            sensor_id,
            date,
            data_type,
            data,
            status,
            updated);
            """)
    try:
        open(configer.get_setting('Paths', 'sensor_state_log')).close()
    except FileNotFoundError:
        open(configer.get_setting('Paths', 'sensor_state_log'), 'tw').close()


def get_sensor_id():
    """ Получает sensor_id из файла os-release """
    param_1 = 'ZSENSOR_UNIQUE_ID'
    with open('/etc/os-release', 'r') as sensor_id:
        for line in sensor_id:
            if param_1 in line:
                line = line.split('=')
                return line[1].strip()


def md5_check():
    """ Создает эталонную контрольную сумму списка home_net, если она еще не была создана,
    иначе создает контрольную сумму списка home_net на момент запуска сприпта и
    сверяет с эталонной

    """
    if os.path.isfile(configer.get_setting("Paths", 'sensor_state_main_dir') + '/home_net.md5') == 1:
        with open(configer.get_setting("Paths", 'sensor_state_main_dir') + '/home_net.md5', 'r') as MD5:
            # Проверяем md5 homenet_list с эталонным
            compared_hash = hashlib.md5(str(homenet_list()).encode(encoding='utf-8')).hexdigest()
            list_hash = MD5.readlines()
            string = ''.join(list_hash)
            if string == compared_hash:
                return 'md5:ok'
            else:
                return 'md5:warn'
    else:
        # Формируем эталонный md5 и пишем его в файл
        main_hash = hashlib.md5(str(homenet_list()).encode(encoding='utf-8')).hexdigest()
        with open(configer.get_setting("Paths", 'sensor_state_main_dir') + '/home_net.md5', 'w') as hash_file:
            hash_file.write(main_hash)
            return 'md5:ok'


def path_to_snort_config():
    """ Получает путь к файлу snort.conf из файла конфигурации сенсора """
    param_name = 'snort-config-path'
    with open(configer.get_setting('Paths', 'zsensor_conf'), 'r') as config:
        for line in config:
            if param_name in line and '#' not in line:
                line = line[:-1].split()
                return line[2].strip()


def span_interfaces():
    """ Получает список интерфейсов с зеркалом трафика из файла zsensor.conf"""
    param_name = 'capture-interface'
    interface_list = []
    with open(configer.get_setting('Paths', 'zsensor_conf'), 'r') as config:
        for line in config:
            if param_name in line and '#' not in line:
                for index in line[:-1].split('=')[1].split(','):
                    interface_list.append(index.strip())
    return interface_list


def homenet_list():
    """ Получает список home_net из файла конфигурации snort.conf """
    param1_name = 'ipvar'
    param2_name = 'HOME_NET'
    homenet_list = []
    # Цикл возвращает список home_net из snort.conf
    with open(path_to_snort_config(), 'r') as snort_conf:
        for line in snort_conf:
            if param1_name and param2_name in line and '#' not in line:
                if '$' not in line:
                    homenet_list.append(re.findall('\d+\.\d+\.\d+\.\d+\/\d+', line))
    return homenet_list


def get_span_status(dev: str, traf_exist):
    """ Функция для запуска в потоке. Определяет есть ли трафик на сетевых интерфейсах с
    зеркалом трафика.

    """
    lock = threading.Lock()
    err_log = open(configer.get_setting('Paths', 'sensor_state_errlog_dir') + '/err_' + dev + '.err', "w")
    p = subprocess.Popen('timeout ' + configer.get_setting('Tcpdump', 'timeout') + ' tcpdump -n -nn -i ' + dev +
                         ' -w ' +
                         configer.get_setting('Paths', 'sensor_state_traf_dir') +
                         '/' + dev + '.dump 2>&-',
                         stdout=None,
                         stderr=err_log,
                         universal_newlines=True,
                         shell=True)
    p.wait()
    err_log.close()
    log = configer.get_setting('Paths', 'sensor_state_traf_dir') + '/' + dev + '.dump'
    with lock:
        if os.path.getsize(log) < 30:
            traf_exist.append(dev + '-warn')
        else:
            traf_exist.append(dev + '-ok')
    return traf_exist


def get_homenet_status(file, homenet, dictionary):
    """ Функция для запуска в потоке. Определяет есть ли контролируемые диапазоны IP-адресов в
    трафике на сетевых интерфейсах с зеркалом трафика.

    """
    filename_tmp = homenet.split('/')
    filename = filename_tmp[0]
    tmp = open(configer.get_setting('Paths', 'sensor_state_traf_dir') + '/' + filename + ' ' + file, "w")
    lock = threading.Lock()
    p = subprocess.Popen('tcpdump -n -nn -r ' + configer.get_setting('Paths', 'sensor_state_traf_dir') + '/' +
                         file + ' net ' + homenet + ' 2>&-',
                         stdout=tmp,
                         stderr=None,
                         universal_newlines=True,
                         shell=True)
    p.wait()
    tmp.close()
    if os.path.getsize(tmp.name) != 0:
        status = 'ok'
    else:
        status = 'warn'
    with lock:
        if dictionary.get(homenet, 0) == 0:
            dictionary.update({homenet: status})
        else:
            if dictionary.get(homenet) == 'warn':
                pass
            if status == 'ok':
                dictionary.update({homenet: status})
    os.remove(configer.get_setting('Paths', 'sensor_state_traf_dir') + '/' + filename + ' ' + file)


def insert(sql: tuple):
    """ Вставляет в БД новые записи """
    execute = "INSERT INTO sensor_data (sensor_id, date, data_type, data, status, updated) VALUES (?, ?, ?, ?, ?, ?)"
    with sqlite3.connect(configer.get_setting('DB', 'db_path')) as conn:
        cursor = conn.cursor()
        cursor.execute(execute, sql)


def select(data_type: str, data: str):
    """ Возвращает из БД записи по значениям полей data_type и data """
    args = [data_type, data]
    select = "SELECT * FROM sensor_data WHERE data_type = (?) AND data = (?)"
    with sqlite3.connect(configer.get_setting('DB', 'db_path')) as conn:
        cursor = conn.cursor()
        return cursor.execute(select, args).fetchall()


def select_non_updated():
    """ Возвращает из БД записи которые не обновлялись """
    select = "SELECT * FROM sensor_data WHERE updated = 0"
    with sqlite3.connect(configer.get_setting('DB', 'db_path')) as conn:
        cursor = conn.cursor()
        return cursor.execute(select).fetchall()


def select_all():
    """ Возвращает из БД все что есть """
    select_all = "SELECT * FROM sensor_data"
    with sqlite3.connect(configer.get_setting('DB', 'db_path')) as conn:
        cursor = conn.cursor()
        return cursor.execute(select_all).fetchall()


def update_status(data_type, update_data, data):
    """ Обновляет поле ststus записи в БД по значениям полей data_type и data"""
    args = [update_data, data_type, data]
    update = "UPDATE sensor_data SET status = (?) WHERE data_type = (?) AND data = (?)"
    with sqlite3.connect(configer.get_setting('DB', 'db_path')) as conn:
        cursor = conn.cursor()
        cursor.execute(update, args)


def update_updated(data_type, update_data, data):
    """ Обновляет поле updated записи в БД по значениям полей data_type и data"""
    args = [update_data, data_type, data]
    update = "UPDATE sensor_data SET updated = (?) WHERE data_type = (?) AND data = (?)"
    with sqlite3.connect(configer.get_setting('DB', 'db_path')) as conn:
        cursor = conn.cursor()
        cursor.execute(update, args)


def update_all_updated():
    """ Обновляет поле updated всех записей в БД """
    update = "UPDATE sensor_data SET updated = 0"
    with sqlite3.connect(configer.get_setting('DB', 'db_path')) as conn:
        cursor = conn.cursor()
        cursor.execute(update)


def update_time(data_type, update_data, data):
    """ Обновляет поле date записи в БД по значениям полей data_type и data"""
    args = [update_data, data_type, data]
    update = "UPDATE sensor_data SET date = (?) WHERE data_type = (?) AND data = (?)"
    with sqlite3.connect(configer.get_setting('DB', 'db_path')) as conn:
        cursor = conn.cursor()
        cursor.execute(update, args)


def delete(data_type, delete_data):
    """ Удаляет запись в БД по значениям полей data_type и data"""
    args = [data_type, delete_data]
    delete = "DELETE FROM sensor_data WHERE data_type = (?) AND data = (?)"
    with sqlite3.connect(configer.get_setting('DB', 'db_path')) as conn:
        cursor = conn.cursor()
        cursor.execute(delete, args)


if __name__ != '__main__':
    create_paths()
