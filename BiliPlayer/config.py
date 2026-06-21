DEBUG_FLG = True
with open("BiliPlayer/resources/stealth.js", "r", encoding="utf-8") as f:
    STEALTH_JS = f.read()

import os, json, pathlib
from .exceptions import ConfigException

class Config:
    originData = {
        "Player": {
            "sepPage": True,
            "defaultVolume": 30,
            "preference": {
                "BV1ti4y1K7uw": {
                    "p": 2
                },
                "BV1yV41177Xh": {
                    "p": 2
                },
                "BV1rV4y1G7Bw": {
                    "p": 2
                }
            }
        }
    }

    def __init__(self, config_path: str = os.path.join(pathlib.Path().cwd(), "config.json")) -> None:
        self.data = None
        self.configPath = config_path
        self.load()

    def load(self) -> bool:
        try:
            if not os.path.exists(self.configPath):
                with open(self.configPath, "w+", encoding="utf-8") as f:
                    f.write(json.dumps(self.originData, ensure_ascii=False))
                    self.data = self.originData
            else:
                with open(self.configPath, "r", encoding="utf-8") as f:
                    self.data = f.read()
                    self.data = json.loads(self.data) if self.data else self.originData
        except Exception as e:
            raise ConfigException(f"Error with init config.\n{e}")
        return True

    def get(self, key: str, defaultValue = None, passOnNotExists: bool = False):
        keyList = key.split(".")
        data = self.data
        originData = self.originData

        for item in keyList:
            data = data.get(item)
            originData = originData.get(item)
            if originData is None:
                if not passOnNotExists:
                    raise ConfigException(f"Unknown key {item} in {key}")
                else:
                    return defaultValue
            if data is None:
                if defaultValue is None:
                    data = originData
                else:
                    return defaultValue

        return data

    def set(self, key, value) -> bool:
        keyList = key.split(".")
        data = self.data

        for item in keyList[:-1]:
            if item not in data:
                data[item] = {}
            data = data[item]

        data[keyList[-1]] = value
        return True

    def save(self) -> bool:
        cfg_str = self.data
        try:
            with open(self.configPath, "w", encoding="utf-8") as f:
                f.write(json.dumps(cfg_str, ensure_ascii=False))
            return True
        except Exception as e:
            raise ConfigException(f"Error with saving config.\n{e}")

    def autoComplete(self) -> None:
        for key in self.originData:
            if key not in self.data:
                self.data[key] = self.originData[key]
            elif type(self.originData[key]) == dict:
                for subKey in self.originData[key]:
                    if subKey not in self.data[key]:
                        self.data[key][subKey] = self.originData[key][subKey]
        self.save()

    def __del__(self):
        # self.save()
        pass
