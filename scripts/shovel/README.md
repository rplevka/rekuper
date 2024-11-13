# Shovel script
a simple bridge between Prometheus vm/container metrics and the `rekuper` relational database.

## How it works
It's a 3-stage script:
1. extracts information from Prometheus about existing VMs and Containers for a given `lookback` period. Uses the specific label to identify the corresponding jenkins job url of the parent test automation session.
2. Tries to extract satellite release and snap version the automation was trigerred for.
3. Pushes the relevant data about the instances to `rekuper` DB through `rekuper` API.

## How to use it
The script uses `Dynaconf` config file - `settings.yaml`. This file consists of 3 sections:
1. `prometheus` configuration and query configuration, `
2. rekuper API and payload mapping configuration
3. jenkins api credentials

### API endpoint mapping.
The structure under this config key reflects the payload dictionary of the resulting POST request to `rekuper` API.
The value is the name of the  corresponding label of the prometheus metric.
Please note, that the `jenkins_url` is a mandatory key as its value is going to be used to parse the corresponding Satellite version.