#!/bin/bash
java -cp /opt/nis2-legolas/.local/legolas/workspace/legolas-zk/conf-1:/opt/nis2-legolas/.local/legolas/driver/zookeeper/3.6.2/target/zk_3_6_2-1.0-jar-with-dependencies.jar edu.umich.order.legolas.zk_3_6_2.ZooKeeperGrayClientMain $@

