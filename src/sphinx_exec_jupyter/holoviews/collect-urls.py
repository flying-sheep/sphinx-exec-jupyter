# SPDX-License-Identifier: MPL-2.0
import json

from bokeh.model import Model
from panel.io.resources import set_resource_mode

# Simplified from https://github.com/holoviz-dev/nbsite/blob/e75708a28d9a4ab805753c0520b8eb8779c79d82/nbsite/pyodide/__init__.py#L108

models = Model.model_class_reverse_map.values()

with set_resource_mode("cdn"):
    js = {f for model in models for f in getattr(model, "__javascript__", [])}
    css = {f for model in models for f in getattr(model, "__css__", [])}

print(json.dumps(dict(js=list(js), css=list(css))))
