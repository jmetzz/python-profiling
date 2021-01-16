#!/usr/bin/env python3

import logging.config
import os
import pstats
import subprocess
import timeit
from tempfile import NamedTemporaryFile

import pandas as pd
from cProfile import Profile
from datetime import datetime
from json import JSONDecodeError
from pathlib import Path
from urllib.parse import urlencode

import click
import pyinstrument
from click import UsageError

from db import run_query
from queries import SALES_DATA, MOC_DATA
from utils import timed, get_retry_client

logger = logging.getLogger(__name__)
logging.getLogger("ce").setLevel(logging.DEBUG)

THIS_DIR = os.path.dirname(__file__)

HOSTS = {
    "LOCAL": "http://localhost:8000",
    "DEV": "https://DEV-URL/",
    "STABLE": "https://STABLE-URL/",
    "PROD": "https://PROD-URL/",
    "PERF": "https://PERFORMANCE-ENV-URL",
}

QUERIES = {
    "SALES_DATA": SALES_DATA,
    "MOC_DATA": MOC_DATA,
}

PARAMS_MAPPING = {}

SETUP_RULE_TEMPLATE = """
from ce.algo.rules import RULES
from ce.db import get_processed_data, get_data
from ce.algo.query import get_market_config
data = get_processed_data('$item_group', '$country_code', $period_seq)
market_config = get_data(get_market_config, {"item_group_code": "$item_group", "country_code": "$country_code"})
"""


@click.group()
def main():
    pass


@main.command()
@click.option("--rule", type=click.Choice(map(str, RULES.keys())), default=DEFAULT_RULE)
@click.option("--group", type=click.Choice(ITEM_GROUPS), default=DEFAULT_CELL)
@click.option("--country", type=click.Choice(["DE", "CN"]), default=DEFAULT_COUNTRY)
@click.option("--period", type=click.INT, default=DEFAULT_PERIOD)
@click.option("--n", type=click.INT, default=None)
@click.option("--r", type=click.INT, default=1)
def timeit_rule(rule, group, country, period, n, r):
    setup_code = Template(SETUP_RULE_TEMPLATE).substitute(
        item_group=group,
        country_code=country,
        period_seq=period,
    )

    stmt_code = Template("""RULES[int($rule)](data, market_config, $period_seq)""").substitute(
        period_seq=period, rule=rule
    )
    if r and n:
        outcome = timeit.repeat(setup=setup_code, stmt=stmt_code, repeat=r, number=n)
        print(f"Best rule '{rule}' execution time '{min(outcome)}' sec; '{n}' loops and {r} repeats per loop.")
    else:
        loops, outcome = timeit.Timer(setup=setup_code, stmt=stmt_code).autorange()
        print(f"Rule '{rule}' execution time '{outcome}' sec in '{loops}' loops")


@timed
@main.command()
@click.option("f", "--function", type=str, required=True)
@click.option("--output", type=str, default=None)
@click.option("--pretty", is_flag=True)
def run(function, output, pretty, *args, **kwargs):
    if pretty:
        use_pyinstrument(function, output, args, kwargs)
    else:
        use_cprofiler(function, output, args, kwargs)


@main.command()
@click.option("--file", type=str)
@click.option("--limit", type=click.INT, default=None)
@click.option("--callers", is_flag=True)
@click.option(
    "--sortby",
    type=click.Choice(pstats.SortKey.__members__.keys(), case_sensitive=False),
    default="CUMULATIVE",
)
def stats(file, limit, callers, sortby):
    stats = pstats.Stats(file)

    key = pstats.SortKey(sortby.lower())
    stats.strip_dirs().sort_stats(key).print_stats(limit)
    if callers:
        stats.print_callees(limit)


def use_cprofiler(target_function, output=None, *args, **kwargs):
    with Profile(builtins=False) as profiler:
        target_function(args, kwargs)

    if output:
        Path(THIS_DIR, ".profile_data").mkdir(parents=True, exist_ok=True)
        profiler.dump_stats(str(Path(THIS_DIR, ".profile_data", output)))
        print("\nYou can also visualise the profiling result with snakeviz:")
        print(f"    $ snakeviz {output}")
    else:
        with NamedTemporaryFile(delete=False) as tmp_file:
            profiler.dump_stats(tmp_file.name)
            filename = tmp_file.name

        subprocess.Popen(["snakeviz", filename])


@main.command()
@click.option("--group", type=click.Choice(ITEM_GROUPS), default=DEFAULT_CELL)
@click.option("--country", type=click.Choice(["DE", "CN"]), default=DEFAULT_COUNTRY)
@click.option("--period", type=click.INT, default=DEFAULT_PERIOD)
def moc_profile(group, country, period):
    with Profile(builtins=False) as profiler:
        get_moc_threshold(group, country, period)

    with NamedTemporaryFile(delete=False) as tmp_file:
        profiler.dump_stats(tmp_file.name)
        filename = tmp_file.name

    subprocess.Popen(["snakeviz", filename])


def use_pyinstrument(target_function, output=None, *args, **kwargs):
    profiler = pyinstrument.Profiler()
    profiler.start()
    target_function(args, kwargs)
    profiler.stop()

    print(profiler.output_text(unicode=True, color=True))

    if output:
        Path(THIS_DIR, ".profile_data").mkdir(parents=True, exist_ok=True)
        filename = str(Path(THIS_DIR, ".profile_data", f"{output}.html"))
        with open(filename, "w") as file:
            file.write(profiler.output_html())


@timed
@main.command()
@click.option("--query", type=click.Choice(QUERIES.keys()), default="LOCAL")
@click.option("--env", type=click.Choice(HOSTS.keys()), default="LOCAL")
def timed_query(query, env, period):
    df = run_query(query, params)
    print(df.shape)


@timed
@main.command()
@click.option("--env", type=click.Choice(HOSTS.keys()), default="LOCAL")
def test_remote(group, country, period, env):
    host = HOSTS.get(env)
    qs_params = {"itemGroupCode": group, "countryCode": country, "periodId": period}
    url = f"{host}/consulting_engine?{urlencode(qs_params)}"
    session = get_retry_client()

    token = os.getenv("GFK_TOKEN", "")
    if not token and env != "LOCAL":
        raise UsageError("GFK_TOKEN not set in env vars")

    response = session.request(
        "GET",
        url,
        headers={
            "authorization": f"Bearer {token}",
            "content-type": "application/json",
        },
    )
    response.raise_for_status()

    print(f"item_group: {group}")
    print(f"country: {country}")
    print(f"period: {period}")
    print(f"env: {env}")
    print(f"time taken: {response.elapsed.total_seconds()}")
    print(f"recommendations: {len(response.json())}")


def get_content(response):
    try:
        return response.json()
    except JSONDecodeError:
        return []


@main.command()
@click.option("--env", type=click.Choice(HOSTS.keys()), default="LOCAL")
@click.option("--endpoint", type=str, requited=True)
@click.option("--sla", type=int, default=1)
def produce_stats(env, endpoint, sla):
    host = HOSTS.get(env)
    now = datetime.now()
    token = os.getenv("TOKEN", "")
    if not token and env != "LOCAL":
        raise UsageError("TOKEN not set in env vars")

    session = get_retry_client()
    data = []

    response = session.request(
        "GET",
        f"{host}/endpoint",
        headers={
            "authorization": f"Bearer {token}",
            "content-type": "application/json",
        },
    )
    response.raise_for_status()

    for params in PARAMS_MAPPING:
        url = f"{host}/consulting_engine?{urlencode(params)}"
        response = session.request(
            "GET",
            url,
            headers={
                "authorization": f"Bearer {token}",
                "content-type": "application/json",
            },
        )
        data.append(
            {
                "env": env,
                "params": params,
                "status_code": response.status_code,
                "time": response.elapsed.total_seconds(),
                "size": len(get_content(response)),
                "url": url,
                "current_time": now,
                "sla_met": response.elapsed.total_seconds() < sla,
            }
        )

    df = pd.DataFrame(data=data).sort_values("time")
    with open(os.path.join(THIS_DIR, "docs", f"{env.lower()}_timings.md"), "w") as fp:
        df.to_markdown(fp, index=False)


if __name__ == "__main__":
    main()
