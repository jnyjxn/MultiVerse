import re
import yaml
import json
from pathlib import Path
from typing import Any, Literal, TextIO


class ConfigError(Exception):
    """Base class for exceptions in this module."""

    pass


class ConfigKeyError(ConfigError, KeyError):
    """Exception raised for errors in the key."""

    def __init__(self, key: str, message: str = "Key not found"):
        self.key = key
        self.message = f"{message}: '{key}'"
        super().__init__(self.message)


class ConfigIndexError(ConfigError, IndexError):
    """Exception raised for errors in the list index."""

    def __init__(self, index: int, message: str = "List index out of range"):
        self.index = index
        self.message = f"{message}: Index [{index}]"
        super().__init__(self.message)


class ConfigFilterError(ConfigError, ValueError):
    """Exception raised when a filter does not match any items."""

    def __init__(
        self,
        key: str,
        prop: str,
        value: str,
        message: str = "No match found for filter",
    ):
        self.key = key
        self.prop = prop
        self.value = value
        self.message = f"{message}: '{key}' with '{prop}={value}'"
        super().__init__(self.message)


class Config:
    required_keys: list[str] = []
    default_values: dict[str, Any] = {}

    def __init__(self, config_dict_or_list: dict | list):
        self._raw_object = config_dict_or_list

        for key in self.required_keys:
            self.require(key)

    def _resolve_path(self, path: str):
        path_parts = re.split(r"(?<!\\)/", path)
        resolved_path = []
        for part in path_parts:
            if "[" in part and "]" in part:
                key, index = re.match(r"(.*)\[(\d+)\]", part).groups()
                resolved_path.append(key)
                resolved_path.append(int(index))
            elif "|" in part:
                key, filter_expression = part.split("|")
                prop, value = filter_expression.split(":")
                resolved_path.append((key, prop, value))
            else:
                resolved_path.append(part)
        return resolved_path

    def _navigate(self, d: dict, keys: list[str]):
        for key in keys:
            if isinstance(key, tuple):
                key, prop, value = key
                try:
                    d = next(item for item in d[key] if item.get(prop) == value)
                except KeyError:
                    raise ConfigKeyError(key)
                except StopIteration:
                    raise ConfigFilterError(key, prop, value)
            else:
                try:
                    d = d[key]
                except KeyError:
                    raise ConfigKeyError(key)
                except IndexError:
                    raise ConfigIndexError(key)
        return d

    def update(self, **kwargs):
        self._raw_object.update(kwargs)

    def remove(self, key):
        if isinstance(self._raw_object, dict):
            if key in self._raw_object:
                del self._raw_object[key]
        elif isinstance(self._raw_object, list):
            self._raw_object.remove(key)

    def get(self, path: str, default: Any | None = None):
        if default is None:
            default = self.default_values.get(path)

        try:
            result = self.require(path)
            return self._cast_if_dict_or_list(result)
        except (KeyError, IndexError, StopIteration):
            return default

    def require(self, path: str):
        keys = self._resolve_path(path)
        return self._navigate(self._raw_object, keys)

    def exists(self, path: str) -> bool:
        try:
            keys = self._resolve_path(path)
            self._navigate(self._raw_object, keys)
            return True
        except (KeyError, IndexError, StopIteration):
            return False

    def as_raw(self):
        return self._raw_object

    def __contains__(self, path: str) -> bool:
        return self.exists(path)

    def __iter__(self):
        if isinstance(self._raw_object, list):
            return iter([self._cast_if_dict_or_list(el) for el in self._raw_object])
        elif isinstance(self._raw_object, dict):
            return iter(
                {k: self._cast_if_dict_or_list(el) for k, v in self._raw_object.items()}
            )
        else:
            return iter(self._raw_object)

    def __str__(self):
        return str(self._raw_object)

    @classmethod
    def _cast_if_dict_or_list(cls, obj: Any):
        if type(obj) in [list, dict]:
            return Config(obj)
        return obj

    @classmethod
    def from_dict_or_list(cls, config_dict_or_list: dict | list):
        return cls(config_dict_or_list)

    @classmethod
    def from_config(cls, config: "Config"):
        return cls(config.as_raw())

    @classmethod
    def from_file(
        cls,
        filepath: str | Path | TextIO,
        filetype: Literal["json", ".json", "yaml", ".yaml"] | None = None,
    ):
        if type(filepath) is str:
            filepath = Path(filepath)

        if isinstance(filepath, Path):
            if not filepath.exists():
                raise FileNotFoundError(
                    f"File path {filepath.absolute()} does not exist."
                )

            filetype = filetype or filepath.suffix

            if not filetype:
                raise ValueError(
                    f"Could not infer filetype for config path '{filepath}'. Please specify the filetype."
                )
        else:
            if filetype is None:
                raise ValueError("`filetype` must be set if a file object is passed.")

        if filetype in [".json", "json"]:
            raw_config_object = json.load(filepath)
        elif filetype in [".yaml", "yaml"]:
            with open(filepath) as f:
                raw_config_object = yaml.safe_load(f)
        else:
            raise ValueError(
                f"Unrecognised file type: {filetype}. Must be '.yaml' or '.json'."
            )

        return cls(raw_config_object)


def use_config(config_class):
    if not issubclass(config_class, Config):
        raise ValueError(
            "The `use_config` decorator must be passed a subclass of Config."
        )

    def decorator(cls):
        def from_config(cls, config):
            if isinstance(config, dict):
                config = config_class.from_dict_or_list(config)

                return cls(**config.as_raw())
            elif not isinstance(config, config_class):
                config = config_class.from_config(config)

                return cls(**config.as_raw())

        setattr(cls, "from_config", classmethod(from_config))
        return cls

    return decorator
