import copy
from typing import Tuple

class ToDict:
    def to_dict(self) -> dict:
        def attempt_map_privates_to_properties(data: dict) -> dict:
            mapped_data = {}

            for key, value in data.items():
                if (key.startswith('_')):
                    try:
                        prop = getattr(self, key[1:])
                    except AttributeError:
                        continue

                    if (prop is not None):
                        mapped_data[key[1:]] = prop
                else:
                    mapped_data[key] = value
            
            return mapped_data


        data = copy.deepcopy(self.__dict__)
        data = attempt_map_privates_to_properties(data)

        return data
