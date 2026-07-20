#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

export AIRFLOW_HOME="${AIRFLOW_HOME:-$PROJECT_ROOT/.airflow}"
export AIRFLOW__CORE__DAGS_FOLDER="$PROJECT_ROOT/airflow/dags"
export AIRFLOW__CORE__LOAD_EXAMPLES="False"
export PHDBUDDY_PROJECT_ROOT="$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

exec uvx --from apache-airflow==3.3.0 airflow standalone
