module.exports = {
  apps: [
    {
      name: "cast-llm-api",
      cwd: "/home/castalum/dev/cast-llm",
      script: "uv",
      args: "run cast-llm-api",
      interpreter: "none",
      exec_mode: "fork",
      instances: 1,
      autorestart: true,
      max_restarts: 20,
      min_uptime: "10s",
      restart_delay: 5000,
      time: true,
      merge_logs: true,
      out_file: "/home/castalum/dev/cast-llm/logs/cast-llm-api.out.log",
      error_file: "/home/castalum/dev/cast-llm/logs/cast-llm-api.err.log",
      env: {
        NODE_ENV: "production",
        PYTHONUNBUFFERED: "1",
        CAST_LLM_ENV: "production",
      },
    },
  ],
};
