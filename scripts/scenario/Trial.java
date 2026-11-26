import edu.umich.order.legolas.orchestrator.server.MegaServer;
import java.io.*;
import java.nio.file.*;
import java.time.Instant;
import java.util.*;

public final class Trial {
    private final Path dir, workspace, writer, checker;
    private final Properties props;
    private final MegaServer controller;
    private final String connect, namespace;
    private final int timeout;

    Trial(MegaServer controller, Properties props, Path workspace, Path dir,
          Path writer, Path checker, int timeout) {
        this.controller = controller;
        this.props = props;
        this.workspace = workspace;
        this.dir = dir;
        this.writer = writer;
        this.checker = checker;
        this.timeout = timeout;
        int serverCount = Integer.parseInt(props.getProperty("serverCount"));
        StringJoiner endpoints = new StringJoiner(",");
        for (int id = 1; id <= serverCount; id++) endpoints.add("127.0.0.1:" + props.getProperty("clientPort." + id));
        connect = endpoints.toString();
        namespace = "/trial-" + controller.getTrialId();
    }

    private void event(String value) throws IOException {
        Files.write(dir.resolve("phases.tsv"), Collections.singletonList(Instant.now() + "\t" + value),
                StandardOpenOption.CREATE, StandardOpenOption.APPEND);
    }

    private int run(String phase, String... command) throws Exception {
        event(phase + "_start");
        List<String> args = new ArrayList<>(Arrays.asList("python3", "scripts/scenario/bounded.py",
                Integer.toString(timeout)));
        args.addAll(Arrays.asList(command));
        ProcessBuilder pb = new ProcessBuilder(args);
        pb.environment().put("ZK_CONNECT", connect);
        pb.environment().put("TRIAL_DIR", dir.toString());
        pb.environment().put("ZK_NAMESPACE", namespace);
        pb.environment().put("CLIENT_JOURNAL", dir.resolve("client.jsonl").toString());
        int code = pb.redirectErrorStream(true).redirectOutput(dir.resolve(phase + ".log").toFile())
                .start().waitFor();
        event(phase + (code == 124 ? "_timeout" : "_exit_" + code));
        return code;
    }

    private void ready(boolean initial) throws Exception {
        List<String> cmd = new ArrayList<>(Arrays.asList("java", "-cp",
                System.getProperty("java.class.path"), "Ready", connect));
        if (initial) cmd.add(namespace);
        String phase = initial ? "prepare" : "recovery";
        if (run(phase, cmd.toArray(new String[0])) != 0) throw new IOException(phase + " probe failed");
    }

    void execute() throws Exception {
        try (Ensemble ensemble = new Ensemble(controller, props, workspace, dir)) {
            ensemble.start("initial");
            ready(true);
            int status;
            controller.setReady();
            try {
                status = run("write", writer.toString());
            } finally {
                controller.pauseInjections();
            }
            // A stalled or failed writer may already have received OK for earlier records.
            event("restart_start");
            ensemble.close();
            ensemble.start("restarted");
            ready(false);
            if (run("check", checker.toString()) != 0) throw new IOException("checker failed");
            if (status != 0 && status != 124) throw new IOException("writer failed: " + status);
            event("completed");
        }
    }

    public static void main(String[] args) {
        try {
            runAttempt(args);
        } catch (Exception e) {
            e.printStackTrace();
            System.exit(1);
        }
        System.exit(0);
    }

    private static void runAttempt(String[] args) throws Exception {
        Properties props = new Properties();
        Path config = Paths.get(args[0]).toAbsolutePath();
        try (InputStream in = Files.newInputStream(config)) { props.load(in); }
        Path results = Paths.get(args[1]).toAbsolutePath();
        Path writer = Paths.get(args[2]).toRealPath(), checker = Paths.get(args[3]).toRealPath();
        int timeout = Integer.parseInt(args[5]);
        if (timeout <= 0 || !Files.isExecutable(writer) || !Files.isExecutable(checker))
            throw new IllegalArgumentException("expected executable hooks and positive phase timeout");
        Files.createDirectory(results);
        Files.createDirectory(results.resolve("trials"));
        props.setProperty("workspacePathName", results.toString()); // destination of Legolas events
        props.setProperty("injectionPolicy", args[4]);
        props.setProperty("workload", "CreateRecoverCheck");
        props.setProperty("phaseTimeoutSeconds", Integer.toString(timeout));
        props.setProperty("recordStates", "true");
        props.setProperty("maxTrials", "1");
        try (OutputStream out = Files.newOutputStream(results.resolve("legolas.properties"))) {
            props.store(out, "Effective trial configuration");
        }
        try (MegaServer server = new MegaServer(props)) {
            server.start();
            server.setupNewTrial(true);
            server.initStats();
            Path dir = Files.createDirectory(results.resolve("trials/" + server.getTrialId()));
            Trial trial = new Trial(server, props, config.getParent(), dir, writer, checker, timeout);
            try {
                trial.execute();
            } catch (Exception e) {
                trial.event("failed\t" + e);
                throw e;
            } finally {
                server.dumpStats(props);
                server.onTrialStopped();
            }
        }
    }
}
