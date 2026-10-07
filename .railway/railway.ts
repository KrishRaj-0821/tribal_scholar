import { bucket, defineRailway, github, postgres, preserve, project, redis, service, volume } from "railway/iac";

export default defineRailway(() => {
  const tribal_scholar = github("KrishRaj-0821/tribal_scholar", { checkSuites: false });

  const docsBucket = bucket("tribal-scholar-docs", { region: "sjc" });

  const Redis = redis("Redis", { region: "us-west2" });
  Redis.deploy = { startCommand: "/bin/sh -c \"rm -rf $RAILWAY_VOLUME_MOUNT_PATH/lost+found/ && exec docker-entrypoint.sh redis-server --requirepass $REDIS_PASSWORD --save 60 1 --dir $RAILWAY_VOLUME_MOUNT_PATH\"" };
  Redis.networking = { privateNetworkEndpoint: "redis" };
  const Postgres = postgres("Postgres", { region: "us-west2" });
  Postgres.networking = { privateNetworkEndpoint: "postgres" };
  const redisVolume = volume("redis-volume", { alerts: { usage: { "100": {}, "80": {}, "95": {} } }, allowOnlineResize: true, region: "us-west2", sizeMB: 500 });
  const postgresVolume = volume("postgres-volume", { alerts: { usage: { "100": {}, "80": {}, "95": {} } }, allowOnlineResize: true, region: "us-west2", sizeMB: 500 });

  const frontend = service("frontend", {
    source: tribal_scholar,
    rootDirectory: "frontend",
    build: {
      builder: "DOCKERFILE",
      dockerfilePath: "Dockerfile",
    },
    deploy: {
      healthcheckPath: "/",
      restartPolicyType: "ON_FAILURE",
      restartPolicyMaxRetries: 5,
    },
    replicas: { "us-west2": 1 },
  });

  const backend = service("backend", {
    source: tribal_scholar,
    build: {
      builder: "DOCKERFILE",
      dockerfilePath: "Dockerfile.backend",
    },
    deploy: {
      startCommand: "/app/start.sh",
      healthcheckPath: "/health/live",
      healthcheckTimeout: 300,
      restartPolicyType: "ON_FAILURE",
      restartPolicyMaxRetries: 5,
    },
    replicas: { "us-west2": 1 },
    env: {
      CSRF_TRUSTED_ORIGINS: "https://*.railway.app,https://*.up.railway.app,https://tribalscholar.up.railway.app",
      DATABASE_URL: Postgres.env.DATABASE_URL,
      DATABASE_ENGINE: "postgresql",
      DJANGO_ALLOWED_HOSTS: "*",
      DJANGO_DEBUG: "False",
      DJANGO_SECRET_KEY: preserve(),
      REDIS_URL: Redis.env.REDIS_URL,
      STORAGE_BACKEND: "s3",
      AWS_S3_ENDPOINT_URL: "https://t3.storageapi.dev",
      AWS_ACCESS_KEY_ID: preserve(),
      AWS_SECRET_ACCESS_KEY: preserve(),
      AWS_STORAGE_BUCKET_NAME: "tribal-scholar-docs-lzidsm",
      AWS_S3_REGION_NAME: "sjc",
      MALWARE_SCANNER_BACKEND: "clamav",
      CLAMAV_HOST: "127.0.0.1",
      CLAMAV_PORT: "3310",
      FAST2SMS_API_KEY: preserve(),
      FAST2SMS_API_URL: "https://www.fast2sms.com/dev/bulkV2",
      FAST2SMS_ENABLED: "true",
      FAST2SMS_ROUTE: "q",
      FAST2SMS_OTP_URL: "https://www.fast2sms.com/dev/otp/send",
      FAST2SMS_OTP_RESEND_URL: "https://www.fast2sms.com/dev/otp/resend",
      FAST2SMS_OTP_TEMPLATE_ID: preserve(),
      FAST2SMS_SENDER_ID: preserve(),
      FAST2SMS_DLT_MESSAGE_ID: preserve(),
      FAST2SMS_ENTITY_ID: preserve(),
    },
  });

  const worker_scanner = service("worker-scanner", {
    source: tribal_scholar,
    build: {
      builder: "DOCKERFILE",
      dockerfilePath: "Dockerfile.backend",
    },
    deploy: {
      startCommand: "/app/start-worker.sh",
      restartPolicyType: "ON_FAILURE",
      restartPolicyMaxRetries: 5,
    },
    replicas: { "us-west2": 1 },
    env: {
      WORKER_ROLE: "scanner",
      DATABASE_URL: Postgres.env.DATABASE_URL,
      DATABASE_ENGINE: "postgresql",
      DJANGO_DEBUG: "False",
      DJANGO_SECRET_KEY: preserve(),
      REDIS_URL: Redis.env.REDIS_URL,
      STORAGE_BACKEND: "s3",
      AWS_S3_ENDPOINT_URL: "https://t3.storageapi.dev",
      AWS_ACCESS_KEY_ID: preserve(),
      AWS_SECRET_ACCESS_KEY: preserve(),
      AWS_STORAGE_BUCKET_NAME: "tribal-scholar-docs-lzidsm",
      AWS_S3_REGION_NAME: "sjc",
      MALWARE_SCANNER_BACKEND: "clamav",
      CLAMAV_HOST: "127.0.0.1",
      CLAMAV_PORT: "3310",
      FAST2SMS_API_KEY: preserve(),
      FAST2SMS_API_URL: "https://www.fast2sms.com/dev/bulkV2",
      FAST2SMS_ENABLED: "true",
      FAST2SMS_ROUTE: "q",
      FAST2SMS_OTP_URL: "https://www.fast2sms.com/dev/otp/send",
      FAST2SMS_OTP_RESEND_URL: "https://www.fast2sms.com/dev/otp/resend",
      FAST2SMS_OTP_TEMPLATE_ID: preserve(),
      FAST2SMS_SENDER_ID: preserve(),
      FAST2SMS_DLT_MESSAGE_ID: preserve(),
      FAST2SMS_ENTITY_ID: preserve(),
    },
  });

  const worker_ocr = service("worker-ocr", {
    source: tribal_scholar,
    build: {
      builder: "DOCKERFILE",
      dockerfilePath: "Dockerfile.backend",
    },
    deploy: {
      startCommand: "/app/start-worker.sh",
      restartPolicyType: "ON_FAILURE",
      restartPolicyMaxRetries: 5,
    },
    replicas: { "us-west2": 1 },
    env: {
      WORKER_ROLE: "ocr",
      DATABASE_URL: Postgres.env.DATABASE_URL,
      DATABASE_ENGINE: "postgresql",
      DJANGO_DEBUG: "False",
      DJANGO_SECRET_KEY: preserve(),
      REDIS_URL: Redis.env.REDIS_URL,
      STORAGE_BACKEND: "s3",
      AWS_S3_ENDPOINT_URL: "https://t3.storageapi.dev",
      AWS_ACCESS_KEY_ID: preserve(),
      AWS_SECRET_ACCESS_KEY: preserve(),
      AWS_STORAGE_BUCKET_NAME: "tribal-scholar-docs-lzidsm",
      AWS_S3_REGION_NAME: "sjc",
      MALWARE_SCANNER_BACKEND: "clamav",
      CLAMAV_HOST: "127.0.0.1",
      CLAMAV_PORT: "3310",
      FAST2SMS_API_KEY: preserve(),
      FAST2SMS_API_URL: "https://www.fast2sms.com/dev/bulkV2",
      FAST2SMS_ENABLED: "true",
      FAST2SMS_ROUTE: "q",
    },
  });

  return project("tribal-scholar", {
    resources: [frontend, backend, worker_scanner, worker_ocr, Redis, Postgres, redisVolume, postgresVolume, docsBucket],
  });
});
