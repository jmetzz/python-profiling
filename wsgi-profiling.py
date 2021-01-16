import os

from flask import g, make_response, request
from pyinstrument import Profiler



app = init()


@app.before_request
def before_request():
    if 'profile' in request.args:
        g.profiler = Profiler()
        g.profiler.start()


@app.after_request
def after_request(response):
    if not hasattr(g, 'profiler'):
        return response

    g.profiler.stop()
    output_html = g.profiler.output_html()
    return make_response(output_html)


"""
### Profiling

You can also profile the code by using `pyinstrument` library. First run local development server
which has profiling turned on.

```bash
pyinstrument wsgi_profiled.py
```

Now pass `profile` in get params to see execution time analysis dashboard.


```
    curl http://localhost:8001/consulting_engine?periodId=2647&itemGroupCode=PTV_FLAT&countryCode=CN&profile
```




"""
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8001)),
        debug=app.config["DEBUG"],
        use_reloader=False,
        threaded=True,
    )
