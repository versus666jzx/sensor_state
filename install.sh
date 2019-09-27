#!/bin/bash
#
declare_vars(){
  INSTALL_DIR=/mnt/sysimage/opt/zsensor/install/sensor_state
  BUILD_LOG=${INSTALL_DIR}/log/build.log
  BUILD_LOG_FULL=${INSTALL_DIR}/log/build.log.full

  HOME_DIR=/opt/zsensor/sensor_state
  ERR_MSG="empty"
}

create_dirs(){
  # создание каталога бд
  mkdir -p "${HOME_DIR}"/run/homenet_check/db/ >> ${BUILD_LOG_FULL} 2>${BUILD_LOG_FULL}

}

copy_files(){
  # копируем:
  # скрипты
  cp "${INSTALL_DIR}"/sensor_state.py "${HOME_DIR}"/bin/ >> ${BUILD_LOG_FULL} 2>${BUILD_LOG_FULL}
  cp "${INSTALL_DIR}"/configer.py "${HOME_DIR}"/bin/ >> ${BUILD_LOG_FULL} 2>${BUILD_LOG_FULL}
  cp "${INSTALL_DIR}"/tools.py "${HOME_DIR}"/bin/ >> ${BUILD_LOG_FULL} 2>${BUILD_LOG_FULL}

}

service_create(){
  cp "${INSTALL_DIR}"/sensor_state.service /etc/systemd/system/

}

write_to_log_file(){
    echo "(${1}):${2}:${4}:${3}" >> ${BUILD_LOG}
}

declare_vars

write_to_log_file count Info 2

create_dirs 2>$ERR_MSG
if [ $? -ne 0 ]
    then
            write_to_log_file "create_dirs" Error -1 $ERR_MSG
    else
            write_to_log_file "create_dirs" Info 0
fi

copy_files 2>$ERR_MSG
if [ $? -ne 0 ]
    then
            write_to_log_file "copy_files" Error -1 $ERR_MSG
    else
            write_to_log_file "copy_files" Info 0
fi

service_create 2>$ERR_MSG
if [ $? -ne 0 ]
    then
            write_to_log_file "copy_files" Error -1 $ERR_MSG
    else
            write_to_log_file "copy_files" Info 0
fi
