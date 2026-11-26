import edu.umich.order.legolas.orchestrator.server.MegaServer;
import java.io.IOException;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.TimeUnit;

/** Owns the foreground server processes for one physical attempt. */
final class Ensemble implements AutoCloseable {
    private final Map<Integer, Process> processes = new LinkedHashMap<>();
    private final Path workspace, trial;
    private final MegaServer controller;
    private final Properties config;

    Ensemble(MegaServer controller, Properties config, Path workspace, Path trial) {
        this.controller = controller;
        this.config = config;
        this.workspace = workspace;
        this.trial = trial;
    }

    void start(String phase) throws Exception {
        int serverCount = Integer.parseInt(config.getProperty("serverCount"));
        for (int id = 1; id <= serverCount; id++) {
            Path conf = workspace.resolve("conf-" + id);
            Path logs = Files.createDirectories(trial.resolve(phase).resolve("node-" + id));
            ProcessBuilder server = new ProcessBuilder("bash",
                    config.getProperty("targetSystemPathName") + "/bin/zkServer.sh", "start-foreground");
            server.environment().put("ZOOCFGDIR", conf.toString());
            server.environment().put("ZOO_LOG_DIR", logs.toString());
            controller.prepareNodeStart(id);
            Process process = server.redirectErrorStream(true)
                    .redirectOutput(logs.resolve("server.log").toFile()).start();
            processes.put(id, process);
            if (controller.getRecentPid() <= 0 || !process.isAlive()) {
                throw new IOException("ZooKeeper node " + id + " failed to register in " + phase);
            }
            controller.setStart(id);
        }
    }

    @Override public void close() throws Exception {
        for (Process process : processes.values()) process.destroyForcibly();
        for (Map.Entry<Integer, Process> node : processes.entrySet()) {
            if (!node.getValue().waitFor(10, TimeUnit.SECONDS)) {
                throw new IOException("ZooKeeper node " + node.getKey() + " did not stop");
            }
            controller.setShutdown(node.getKey());
        }
        processes.clear();
    }
}
