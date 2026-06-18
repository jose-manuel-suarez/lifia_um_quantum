import json
from typing import Union

from conversion.convert_2to3 import convert_2to3


def convert(circuit_spec: Union[dict, str], destination_file=None, ecosystem=None, logger=None):
    if isinstance(circuit_spec, str):
        spec = json.loads(circuit_spec)
    else:
        spec = circuit_spec

    result = convert_2to3(spec, destination_file=None)

    if destination_file:
        with open(destination_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

    return result

