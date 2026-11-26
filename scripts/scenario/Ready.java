import java.util.concurrent.CountDownLatch;
import org.apache.zookeeper.*;
import org.apache.zookeeper.data.Stat;

/** Separate client JVM so the caller can bound connection and request time together. */
public final class Ready {
    public static void main(String[] args) throws Exception {
        CountDownLatch connected = new CountDownLatch(1);
        try (ZooKeeper zk = new ZooKeeper(args[0], 5000, event -> {
            if (event.getState() == Watcher.Event.KeeperState.SyncConnected) connected.countDown();
        })) {
            connected.await();
            zk.getData("/", false, new Stat());
            if (args.length == 2) {
                zk.create(args[1], new byte[0], ZooDefs.Ids.OPEN_ACL_UNSAFE, CreateMode.PERSISTENT);
            }
        }
    }
}
