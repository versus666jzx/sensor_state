#!/usr/bin/python3.6

import math
import os
import threading
import time
import datetime

import configer as configer
import tools as tools

# Запускаем потоки функции get_span_status
traf_exist = []
thread_list = []
thread_count = len(tools.span_interfaces())
time_to_warn = configer.get_setting('Time', 'time_to_warn')
time_to_del = configer.get_setting('Time', 'time_to_del')


for i in range(thread_count):
    name = 'thread_{}'.format(tools.span_interfaces()[i])
    dev = tools.span_interfaces()[i]
    thread_list.append(threading.Thread(target=tools.get_span_status, name=name, args=[dev, traf_exist]))
    thread_list[len(thread_list)-1].start()

for thread_stop in thread_list:
    thread_stop.join()

# Запускаем потоки функции get_homenet_status
homenet_exist = []
dictionary = {}
dump_files = os.listdir(configer.get_setting('Paths', 'sensor_state_traf_dir'))
homenet_list_tmp = tools.homenet_list()[0]

for homenet in homenet_list_tmp:
    for file in dump_files:
        name = 'thread_{}_{}'.format(homenet, file)
        thread_list.append(
            threading.Thread(target=tools.get_homenet_status, name=name, args=(file, homenet, dictionary)))
        thread_list[len(thread_list)-1].start()

# Ждем завершения всех потоков
for thread_stop in thread_list:
    thread_stop.join()

# Конвертируем словарь в список
dict_to_list = []
for key in dictionary.keys():
    dict_to_list.append(key + " - " + dictionary.get(key))

main_list = [tools.get_sensor_id(), time.time(), tools.md5_check(), traf_exist, dict_to_list]

sensor_id = main_list[0]
date = main_list[1]
updated = [0, 1]
data_type_list = ('hash', 'net_interface', 'net')

# Если в БД есть записи, то поле updated заполняем нулями
if len(str(tools.select_all())) != 0:
    tools.update_all_updated()

# Запись в БД данных типа hash
for md5 in [main_list[2]]:

    data_md5 = md5.split(':')[0].strip()
    status_md5 = md5.split(':')[1].strip()
    data_type_md5 = data_type_list[0]

    # Если в БД нет записей типа hash, то добавляем ее
    if len(tools.select(data_type_md5, data_md5)) == 0:
        sql_md5 = (sensor_id, date, data_type_md5, data_md5, status_md5, updated[1])
        tools.insert(sql=sql_md5)

    # Если в БД уже есть запись с hash со значением ok\warn и новое значение равно значению в БД, то
    # обновляем поле updated и поле date
    elif len(tools.select(data_type_md5, data_md5)) != 0 and tools.select(data_type_md5, data_md5)[0][4] == status_md5:
        tools.update_updated(data_type_md5, updated[1], data_md5)
        tools.update_time(data_type_md5, date, data_md5)

    # Если в БД уже есть запись с hash и она отличается от нового значения, то
    # меняем старое значение на новое, обновляем поле date и поле updated
    elif len(tools.select(data_type_md5, data_md5)) != 0 and tools.select(data_type_md5, data_md5)[0][4] != status_md5:
        tools.update_status(data_type_md5, status_md5, data_md5)
        tools.update_time(data_type_md5, date, data_md5)
        tools.update_updated(data_type_md5, updated[1], data_md5)

    # Удаляем запись которая не обновлялась более суток (updated = 0, date_new - date_in_db > time_to_del)
    elif len(tools.select(data_type_md5, data_md5)) != 0 and tools.select(data_type_md5, data_md5)[0][5] == 0 \
                                                         and main_list[1] - tools.select(data_type_md5, data_md5)[0][1] > time_to_del:
        tools.delete(data_type_md5, data_md5)


# Запись в БД данных типа net_interface
for net_interface in main_list[3]:

    data_net_int = net_interface.split('-')[0].strip()
    status_net_int = net_interface.split('-')[1].strip()
    data_type_net_int = data_type_list[1]

    # Если в БД еще нет такой записи, то добавляем ее
    if len(tools.select(data_type_net_int, data_net_int)) == 0:
        sql_net_interface = (sensor_id, date, data_type_net_int, data_net_int, status_net_int, updated[1])
        tools.insert(sql=sql_net_interface)

    # Если в БД уже есть запись с net_interface со значением ok/warn и новое значение равно значению в БД, то
    # обновляем поле updated и поле date
    elif len(tools.select(data_type_net_int, data_net_int)) != 0 and tools.select(data_type_net_int, data_net_int)[0][4].strip() == status_net_int:
        tools.update_updated(data_type_net_int, updated[1], data_net_int)
        tools.update_time(data_type_net_int, date, data_net_int)

    # Если в БД уже есть запись типа net_interface со значением warn, а новое значение ok, то
    # апдейтим его до ok и обновляем время записи
    elif len(tools.select(data_type_net_int, data_net_int)) != 0 and tools.select(data_type_net_int, data_net_int)[0][4].strip() == 'warn' != status_net_int:
        tools.update_time(data_type_net_int, date, data_net_int)
        tools.update_status(data_type_net_int, status_net_int, data_net_int)
        tools.update_updated(data_type_net_int, updated[1], data_net_int)

    # Если в БД уже есть запись типа net_interface со значением ok, а новое значение warn и разница по времени между
    # новым статусом и статусом в БД более 345 600 сек, то меняем поле status на warn, обновляем поля date и updated
    elif len(tools.select(data_type_net_int, data_net_int)) != 0 and tools.select(data_type_net_int, data_net_int)[0][4].strip() == 'ok' != status_net_int \
                                                                 and main_list[1] - float(tools.select(data_type_net_int, data_net_int)[0][1]) > float(time_to_warn):
        tools.update_time(data_net_int, date, data_net_int)
        tools.update_status(data_type_net_int, status_net_int, data_net_int)
        tools.update_updated(data_type_net_int, updated[1], data_net_int)

    # Удаляем запись которая не обновлялась более суток (updated = 0, date_new - date_in_db > time_to_del)
    elif len(tools.select(data_type_net_int, data_net_int)) != 0 and tools.select(data_type_net_int, data_net_int)[0][5] == 0 \
                                                         and tools.select(data_type_net_int, data_net_int)[0][4] == 'warn'\
                                                         and main_list[1] - float(tools.select(data_type_net_int, data_net_int)[0][1]) > float(time_to_del):
        tools.delete(data_type_net_int, data_net_int)


# Запись в БД данных типа net
for net in main_list[4]:
    data_net = net.split('-')[0].strip()
    status_net = net.split('-')[1].strip()
    data_type_net = data_type_list[2]
    # Если в БД еще нет такой записи, то добавляем ее
    if len(tools.select(data_type_net, data_net)) == 0:
        sql_net = (sensor_id, date, data_type_net, data_net, status_net, updated[1])
        tools.insert(sql=sql_net)

    # Если в БД уже есть запись с net со значением ok/warn и новое значение равно значению в БД, то
    # обновляем поле updated и поле date
    elif len(tools.select(data_type_net, data_net)) != 0 and tools.select(data_type_net, data_net)[0][4].strip() == status_net:
        tools.update_updated(data_type_net, updated[1], data_net)
        tools.update_time(data_type_net, date, data_net)

    # Если в БД уже есть запись типа net со значением warn, а новое значение ok, то
    # апдейтим его до ok и обновляем время записи
    elif len(tools.select(data_type_net, data_net)) != 0 and tools.select(data_type_net, data_net)[0][4].strip() == 'warn' != status_net:
        tools.update_time(data_type_net, date, data_net)
        tools.update_status(data_type_net, status_net, data_net)
        tools.update_updated(data_type_net, updated[1], data_net)

    # Если в БД уже есть запись типа net со значением ok, а новое значение warn и разница по времени между
    # новым статусом и статусом в БД более 345 600 сек, то меняем поле status на warn, обновляем поля date и updated
    elif len(tools.select(data_type_net, data_net)) != 0 and tools.select(data_type_net, data_net)[0][4].strip() == 'ok' != status_net \
                                                         and main_list[1] - float(tools.select(data_type_net, data_net)[0][1]) > float(time_to_warn):
        tools.update_time(data_net, date, data_net)
        tools.update_status(data_type_net, status_net, data_net)
        tools.update_updated(data_type_net, updated[1], data_net)

    # Удаляем запись со статусом warn которая не обновлялась более суток
    # (updated = 0, date_new - date_in_db > time_to_del)
    elif len(tools.select(data_type_net, data_net)) != 0 and tools.select(data_type_net, data_net)[0][5] == 0 \
                                                         and tools.select(data_type_net, data_net)[0][4] == 'warn'\
                                                         and main_list[1] - float(tools.select(data_type_net, data_net)[0][1]) > float(time_to_del):
        tools.delete(data_type_net, data_net)

# Если есть не обновленные записи, то удаляем записи которые не обновлялась более суток
if tools.select_non_updated() != 0:
    for non_updated in tools.select_non_updated():
        if date - float(non_updated[1].strip()) > float(time_to_del):
            non_updated_data_type = non_updated[2].strip()
            non_updated_data = non_updated[3].strip()
            tools.delete(non_updated_data_type, non_updated_data)

db_data = tools.select_all()
with open('/opt/zsensor/log/sensor_state.log', 'w') as log:
    for line in db_data:
        log.write('[' + time.ctime(float(line[1])) + ']' + ' ' + line[0] + ' ' + line[2] + ' ' + line[3] + ' ' + line[4] + '\n')
