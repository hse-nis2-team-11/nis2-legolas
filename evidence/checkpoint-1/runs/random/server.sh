#!/bin/bash
ZOOCFGDIR=/opt/nis2-legolas/.local/legolas/workspace/legolas-zk/conf-$2 ZOO_LOG_DIR=/opt/nis2-legolas/.local/legolas/workspace/legolas-zk/trials/$1/logs-$2 /opt/nis2-legolas/.local/zookeeper/bin/zkServer.sh start

