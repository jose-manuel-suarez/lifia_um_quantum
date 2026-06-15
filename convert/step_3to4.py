import json
from typing import Union

from convert._originals_adapter import delegate


def convert(circuit_spec: Union[dict, str], destination_file=None, ecosystem=None, logger=None):
    original_convert = delegate("convert_3to4", "convert_3to4")
    if isinstance(circuit_spec, str):
        spec = json.loads(circuit_spec)
    else:
        spec = circuit_spec

    if logger:
        logger.info("Invoking original convert_3to4 implementation")

    result = original_convert(spec, destination_file=None)

    if destination_file:
        with open(destination_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

    return result
