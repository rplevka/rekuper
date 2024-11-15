import json
import requests
import time
import urllib3
from config import settings
from requests.auth import HTTPBasicAuth
from log import setup_logger


urllib3.disable_warnings()
# setup logger
log = setup_logger()

# prepare the http session with auto-raising hook function
session = requests.Session()
session.hooks = {"response": lambda r, *args, **kwargs: r.raise_for_status()}

# cache to store the jenkins job details
jenkins_job_cache = {}


def parse_jenkins_job(correlation_id):
    """
    Parse the jenkins job url to extract the sat and snap versions.
    first, consults the cache to see if the job has already been processed.
    If not, fetches the job details from jenkins and extracts the sat and snap versions.
    """
    if jenkins_job_cache.get(correlation_id):
        return jenkins_job_cache[correlation_id]
    # assuming correlation_id format to be like: <jenkins_url>_[a-z0-9]{8}
    jenkins_url = "/".join(correlation_id.split("/")[:-1])
    # parse the jenkins job url to extract the sat and snap versions
    job_response = session.get(
        f"{jenkins_url}/{settings.jenkins.api_uri_suffix}",
        auth=HTTPBasicAuth(settings.jenkins.username, settings.jenkins.token),
        verify=settings.jenkins.ssl_verify,
    )

    # locate the ParametersAction in the job actions
    job_param_actions = [
        j
        for j in job_response.json()["actions"]
        if j.get("_class") == "hudson.model.ParametersAction"
    ]
    try:
        job_params = job_param_actions[0]["parameters"]
        umb_message_params = [
            i["value"] for i in job_params if i["name"] == "CI_MESSAGE"
        ]
    except IndexError():
        log.error(f"no action of parameter type found for the given job: {jenkins_url}")
        raise
    try:
        # gotta replace single quotes with double quotes to make it a valid json :(
        umb_message = json.loads(umb_message_params[0].replace("'", '"'))
    except IndexError():
        log.error(
            f"error: no CI_MESSAGE parameters found for the given job: {jenkins_url}"
        )
        raise
    sat_ver = f'{umb_message["satellite_version"]}-{umb_message["snap_version"]}'
    jenkins_job_cache[correlation_id] = sat_ver
    return sat_ver


# execute the range query in batches
timestamp_now = int(time.time())

# iterate over each - instances and containers
for resource in ["instances", "containers"]:
    log.info(f"processing data for resource type: {resource}")
    log = log.bind(resource=resource)
    range_start = timestamp_now - (settings.prometheus.lookback_hours * 3600)
    range_end = range_start + (settings.prometheus.batch_hours * 3600)

    while range_start <= timestamp_now:
        log.debug(f"processing batch for range: {range_start}-{range_end}")
        query_request = session.get(
            settings.prometheus.api_url,
            params={
                "query": settings.prometheus.query[resource],
                "start": range_start,
                "end": range_end,
                "step": settings.prometheus.step_seconds,
            },
            verify=settings.prometheus.ssl_verify,
        )
        range_start = range_end
        range_end = range_start + (settings.prometheus.batch_hours * 3600)

        if query_request.json()["data"]["result"]:
            # extract the first and last samples (will be used as first_seen and last_seen)
            timestamps = [
                (i["values"][0][0], i["values"][-1][0])
                for i in query_request.json()["data"]["result"]
            ]
            # extract the labels only
            metrics = zip(
                [i["metric"] for i in query_request.json()["data"]["result"]],
                timestamps,
            )

            log.info("pushing scraped data to RDB")

            payload_template = settings.rekuper[resource].payload.to_dict()
            for m in metrics:
                # try to fetch the sat ver params from jenkins first
                job_sat_version = parse_jenkins_job(
                    m[0][payload_template["jenkins_url"]]
                )
                payload = {
                    "job_sat_version": job_sat_version,
                    "first_seen": m[1][0],
                    "last_seen": m[1][1],
                }
                for k, v in payload_template.items():
                    payload[k] = m[0][v]
                r = session.post(
                    settings.rekuper.server + settings.rekuper[resource].endpoint,
                    json=payload,
                )
        else:
            log.info("no metric data for the given range: {range_start}-{range_end}")
            continue
