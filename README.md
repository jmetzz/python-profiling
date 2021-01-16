# Profiling python code

There are mainly 2 types of profiling:

- **Deterministic** (or event-based) profiling is meant to reflect the fact that all function call, function return,
and exception events are monitored, and precise timings are made for the intervals between these events.
- **Statistical** profiling randomly samples the effective instruction pointer,
and deduces where time is being spent. This approach provides only relative indications
of where time is being spent.

For more details on them [see more here](https://docs.python.org/3/library/profile.html).

There are many profiling tools available for Python, either deterministic or statistical.
The official documentation describes the use of the Python profiling interface through two different implementations:

- [profile](https://docs.python.org/3/library/profile.html#module-profile),
- [cProfile](https://docs.python.org/3/library/profile.html#module-cProfile).

> NOTE: Check [How is it different to `profile` or `cProfile`](https://github.com/joerick/pyinstrument#how-is-it-different-to-profile-or-cprofile) for more details.

The former is a pure Python module and, as such, introduces more overhead than the latter,
which is a C extension that implements the same interface as profile.
They both fit into the category of deterministic profilers and make use of the
Python C API [PyEval_SetProfile](https://docs.python.org/3/c-api/init.html#profiling-and-tracing)
to register event hooks.

Other tools are:

- [line_profiler](https://github.com/pyutils/line_profiler) for line-by-line cpu usage.
- [memory_profiler](https://github.com/pythonprofilers/memory_profiler) for line-by-line memory usage.
- [pyinstrument](https://github.com/joerick/pyinstrument), a statistical profiler.
- [pyflame](https://github.com/uber-archive/pyflame), can take snapshots of the Python call stack without
explicit instrumentation, meaning you can profile a program without modifying its source code.
- [gprof2dot](https://github.com/jrfonseca/gprof2dot), turns the output of `cProfile` into a dot graph.
- [snakeviz](https://jiffyclub.github.io/snakeviz/) - a browser based graphical viewer for the output of
Python’s `cProfile` module.

Here I describe how to profile cpu and memory usage of functions in your python code base.

## Setup

In order to collect profiling information from a python application, you first need to install the supporting
python modules that will collect `cpu` and `memory` usage from the target running process.

This project uses `poetry` as a package/dependencies management tool.
Moreover, I've included some tasks via `Makefile` to simplify the environment creation,
dependencies update, code quality checks, linting, and cleaning the workspace.

Setup your python dependencies with `make deps`. This will install `poetry` and
all the python dependencies declared in the `pyproject.toml` file.

You can add extra dependencies as you go by running

```bash
poetry add <package-name>
```

You can also install extra dependencies in bulk via poetry, assuming you have them properly declared in the `pyproject.toml` file.

For example:

```toml
[tool.poetry.dependencies]
python = "3.9.1"
environs = "9.3.0"
numpy = "1.19.5"
pandas = "1.2.0"
psutil = {version = "5.8.0", optional = true}
line-profiler = {version = "3.1.0", optional = true}
memory-profiler = {version = "0.58.0", optional = true}
pyinstrument = {version = "^3.3.0", optinal = true}
jupyterlab = {version = "^3.0.1", optinal = true}

[tool.poetry.extras]
profiling = ["psutil", "line-profiler", "memory-profiler", "pyinstrument"]
jupyter = ["jupyterlab"]
```

```bash
poetry install --extras profiling
```

If jupyter lab is needed, run:

```bash
poetry install --extras jupyter
```

## Measure CPU usage

> NOTE: Make sure to start a poetry shell with by running `poetry shell`.
> You can also run all commands outside a poetry shell,
> as long as you specify `poetry run` before the command.

> NOTE: Make sure the `PYTHONPATH` variable includes the `src` directory. Run `export PYTHONPATH=./src`.

### Overall cpu usage

The evaluate the overall time based cpu usage of your application you can use either `cProfile` or `pyinstrument`.

I've wrapped both into a simple python script to allow choosing each based on arguments given.

Thus, use the `cli.py` commands available to get the cpu usage report.
The reports generated with `cProfile` are show graphically via `snakeviz`, directly in your default browser.
Alternatively, when `--pretty` flag is given, `pyinstrument` is used to show an interactive condensed list,
which can also be exported to a html file.

Examples:

Measure using `cProfile`:

```bash
cli.py cpu --save --vis
```

The `html` output files will be saved in the `.profile_data` directory.
You can use any browser to visualized the results.

If you prefer, you can run `cProfiler` directly from the command line:

```bash
python -m cProfile -o <full-path-to-output-file> <path-to-target-python-script> 
```

The result will be saved in the specified file.
Then you can visualize the results via `snakeviz`:

```bash
snakeviz <full-path-to-output-file>
```

You can also read the profiling statistics any time with `stats` option from the `cli` script.
Examples:

```bash
cli.py stats --file <full-path-to-output-file>
cli.py stats --file <full-path-to-output-file> --sortby TIME --limit 5
cli.py stats --file <full-path-to-output-file> --sortby TIME --limit 10 --callers
```

To get a more condensed view on the result while using a statistical profiler, run the evaluation via `pyInstrument`:

```bash
cli.py cpu --save --vis --pretty
```

### Line-by-line cpu usage

`LineProfiler` can be given specific functions to evaluate, and it will time the execution of each individual line inside those functions. In a typical workflow, one only cares about line timings of a few functions because wading through the results of timing every single line of code would be overwhelming. However, `LineProfiler` does need to be explicitly told what functions to evaluate.

> If the performance tests are executed from a `jupyter` notebook, you don't need to decorate the code.
> The `jupyter` extension simplifies the process allowing for the evaluation of a function without the decorator.

To check the cpu usage in target functions, you must **decorate** the functions with the built-in `@profile`
and run `kernprof` + `line_profiler`. For example:

Assuming `cli.py <task>` would trigger a time consuming task in your application script:

```bash
python -m kernprof -l -v cli.py <task>
```

By default `kernprof` saves the output in a file in the current directory and uses then input script name
as `<script-to-profile>.py.lprof`. Use `-o` option to change the output file name.

How it works?

`kernprof` will create an instance of `LineProfiler` and
insert it into the `__builtins__` namespace with the name profile.
It has been written to be used as a decorator, so in your script,
you have to decorate the functions you want to profile with `@profile`.

Then, verify the results with:

```bash
python -m line_profiler cli.py.lprof
```

## Measure Memory usage

### Overall time based memory usage

Overall time based memory usage can be checked via `cli.py`, via `mem` parameter and its options.
For example:

```bash
cli.py mem --exp <output-filename>.dat
```

This will generate a line chart for visualization and save the data into the desired file,
which can be later used to plot the chart again.

For more detailed information or more flexibility, use `mprof` directly on the command line.

> NOTES:
>
> - do not use `@click` commands while profiling with `mprof`. It breaks line-by-line decorators
> - avoid mixing `@profile` decorators (from `memory_profiler` & the built-in decorator), even if in different python modules.
> - if your python file imports the `memory_profiler` the individual target functions' timestamps will not be recorded.
> Thus, make sure to use built-in `@profile` (no import!).

### Function level memory usage

If you want to check **function level** memory usage, first decorate the target functions with `@profile` decorator.
**Do not import** any decorator otherwise the code breaks.

Then run:

```bash
python -m mprof run -o <path-to-output-file>.prof cli.py <task>
```

This command runs the python script and record memory usage along time, saving the results in a file in the current directory

The result can be plotted for better visualization when you
execute the following command:

```bash
python -m mprof plot -t "Recorded rule memory usage" <path-to-output-file>.prof --backend MacOSX
```

When generating the chart, the time boundaries for each decorated function will be shown in the chart
as different colored square brackets.

> TIP: check out `--flame` option for `mprof plot`

It is also possible to use `mprof` to evaluate memory usage of multiprocessing code. Check out the documentation. Spoiler, you need to use `include_children` flag in either the `@profile` decorator or as a command line argument to `mprof`.

### Line level memory usage

In order to evaluate the memory usage at a line level, you need to use the `memory_profiler` utility.
Also, it is necessary to decorate the target function the `@profile` **decorator provider by this package**.

Then you can load the `memory_profiler` `@profiler` decorator in 2 ways:

- either importing it from `memory_profiler` module in the python modules where the target functions are implemented; or
- passing `-m memory_profiler` to the python interpreter when running the target code.

> TIP: If the performance tests are executed from a `jupyter` notebook, you don't need to decorate the code.
> The `jupyter` extension simplifies the process allowing for the evaluation of a function without the decorator.

```bash
python -m memory_profiler <path-to-target-python-script>
```

The memory usage off all decorated functions will be reported in the stdout/console.

## Tracing memory

TBD!

> The idea is to explain how to use the built-in [tracemalloc](https://docs.python.org/3/library/tracemalloc.html) module.

## References

- [NumPy Docs](https://numpy.org/doc/stable/reference/index.html)
- [Learn Numpy](https://numpy.org/learn/)
- [NumPy Tutorials on Real Python](https://realpython.com/tutorials/numpy/)
- [Scipy Lecture Notes: Basic Numpy](https://scipy-lectures.org/intro/numpy/index.html)
- [Scipy Lecture Notes: Advanced Numpy](https://scipy-lectures.org/advanced/advanced_numpy/index.html)
- [The NumPy array: a structure for efficient numerical computation](https://hal.inria.fr/inria-00564007/document)
- [Broadcasting semantics](https://www.tensorflow.org/xla/broadcasting#principles)
- [Numerical Python Course](https://www.python-course.eu/numpy.php)
- [Array Broadcasting in numpy](https://scipy.github.io/old-wiki/pages/EricsBroadcastingDoc)
- [SciPy Cookbook: Views versus copies in NumPy](https://scipy-cookbook.readthedocs.io/items/ViewsVsCopies.html)

**Books**

- [Travis Oliphant: Guide to NumPy, 2nd ed.](https://www.amazon.de/dp/151730007X/)
- [Ivan Idris: Numpy Beginner’s Guide, 3rd ed.](https://www.amazon.de/dp/1785281968)
- [Jake VanderPlas: Python Data Science Handbook](https://www.amazon.de/dp/1491912057)
- [Wes McKinney: Python for Data Analysis, 2nd ed.](https://www.amazon.de/dp/B075X4LT6K)
- [François Chollet: Deep Learning with Python](https://www.amazon.de/dp/B07BF4C3LM)
- [Robert Johansson: Numerical Python](https://www.amazon.de/dp/1484205545)
- [Elegant SciPy: The Art of Scientific Python](https://www.amazon.com/Elegant-SciPy-Art-Scientific-Python/dp/1491922877)
- [From Python to Numpy](https://www.labri.fr/perso/nrougier/from-python-to-numpy/)
- [SciPy Cookbook](https://scipy-cookbook.readthedocs.io/index.html#scipy-cookbook)
