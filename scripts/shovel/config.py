from dynaconf import Dynaconf, Validator

settings = Dynaconf(
    envvar_prefix="SHOVEL",
    settings_files=["settings.yaml"],
    validators=[
        Validator("log.level", default="INFO"),
        Validator("prometheus.server", required=True),
        Validator("prometheus.api_path", required=True),
        Validator("prometheus.api_url", required=True),
        Validator("prometheus.query.instances", required=True),
        Validator("prometheus.query.containers", required=True),
        Validator("prometheus.lookback_hours", default=24),
        Validator("prometheus.step_seconds", default=30),
        Validator("rekuper.server", required=True),
        Validator("rekuper.instances.endpoint", default="/instances"),
        Validator("rekuper.containers.endpoint", default="/containers"),
        Validator("rekuper.instances.payload.jenkins_url", required=True),
        Validator("rekuper.containers.payload.jenkins_url", required=True),
        Validator("jenkins.username", "jenkins.token", required=True),
    ],
)

# `envvar_prefix` = export envvars with `export DYNACONF_FOO=bar`.
# `settings_files` = Load these files in the order.
