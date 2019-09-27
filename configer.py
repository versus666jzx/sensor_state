import configparser
import os


path = "config.ini"


def __create_config():
    """ Создает файл конфигурации, если его еще нет"""
    if not os.path.exists(path):
        config = configparser.ConfigParser()
        config.add_section("Paths")
        config.set("Paths", "zsensor_home", "/opt/zsensor")
        config.set("Paths", "zsensor_conf", config.get("Paths", "zsensor_home") + "/conf/zsensor.conf")
        config.set("Paths", "zsensor_stat", config.get("Paths", "zsensor_home") + "/log/zsensor.stat")
        config.set("Paths", "sensor_state_main_dir", config.get("Paths", "zsensor_home") + "/run/homenet_check")
        config.set("Paths", "sensor_state_traf_dir", config.get("Paths", "zsensor_home") + "/log/homenet_check/traff")
        config.set("Paths", "sensor_state_errlog_dir", config.get("Paths", "zsensor_home") + "/log/homenet_check/err")
        config.set("Paths", "sensor_state_log", config.get("Paths", "zsensor_home") + "/log/sensor_state.log")
        config.add_section("Tcpdump")
        config.set("Tcpdump", "Timeout", "10")
        config.add_section("DB")
        config.set("DB", "db_path", config.get("Paths", "zsensor_home") + "/run/homenet_check/db/sensor_state.db")
        config.add_section("Time")
        config.set("Time", "time_to_warn", "345600")
        config.set("Time", "time_to_del", "86400")

        # записываем параметры в файл настроек
        with open(path, "w") as config_file:
            config.write(config_file)


def get_setting(section, setting):
    """ Возвращает значение необходимого параметра из файла конфигурации"""
    __create_config()
    config = configparser.ConfigParser()
    config.read(path)
    value = config.get(section, setting)
    return value


if __name__ != "__main__":
    __create_config()
