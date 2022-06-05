"""Entry point for python -m tetratile"""

import argparse
import configparser
import os
import pathlib
import re
import sys
import tkinter as tk
import typing

from . import Grid, TetraTile


class Config:
    """
    Provide and save game configuration.
    """

    def __init__(self):
        """
        Setup game configuration.
        """
        self.defaults = {
            "config_file": self._get_xdg_config(),
            "debug": False,
            "board": {
                "scale": 32,
                "width": 10,
                "height": 22,
            },
            "epsilon": sys.float_info.epsilon * 3,
            "min_rate": 0,
            "initial_rate": 1,
            "remove_freq": 1,
            "constant": False,
            "shadow": "projection",
            "keys": {
                "pause": "p",
                "left": ",",
                "right": ".",
                "left_side": "z",
                "right_side": "/",
                "rotate_left": "m",
                "rotate_right": "v",
                "down": "x",
                "drop": "c",
            },
        }
        self.opts = self.get_opts()

    def _get_xdg_config(self) -> pathlib.Path:
        """
        Attempt to retrieve `$XDG_CONFIG_HOME`.
        """
        if "XDG_CONFIG_HOME" in os.environ:
            return pathlib.Path(os.environ["XDG_CONFIG_HOME"])
        elif "HOME" in os.environ:
            return pathlib.Path(os.environ["HOME"]) / ".config"
        else:
            return pathlib.Path(".config")

    def _config_file(self, arg: str) -> pathlib.Path:
        """
        Create the parent path of the config file if it does not exist and return the path to the file.
        """
        path = pathlib.Path(arg)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _size(self, arg: str) -> tuple[int, int]:
        """
        Validate size argument.
        """
        size_pattern = r"(?P<width>\d+)" r"(?P<mlt>[xX])" r"(?P<height>\d+)"
        match = re.match(size_pattern, arg)

        if match:
            width, height = int(match.group("width")), int(match.group("height"))
            if width > 0 and height > 0:
                return width, height
        raise argparse.ArgumentTypeError("Incorrect size")

    def _initial_rate(self, ir: str) -> float:
        """
        Verify that initial rate is >= minimum rate.
        """
        try:
            ir = float(ir)
        except ValueError:
            raise argparse.ArgumentTypeError("Initial rate is not a number: {}".format(ir))
        if ir < self.defaults["min_rate"]:
            raise argparse.ArgumentTypeError("Initial rate is too low: {}".format(ir))
        else:
            return ir

    def _get_config(self, config_file: pathlib.Path) -> dict:
        """
        Read configs from config file.
        """
        opts = {}
        config = configparser.ConfigParser()
        config.read(config_file)

        opts["epsilon"] = self.defaults["epsilon"]

        opts["board"] = {}
        if config.has_section("board"):
            opts["board"]["scale"] = config.get("board", "scale", vars=self.defaults)
            opts["board"]["width"] = config.get("board", "width", vars=self.defaults)
            opts["board"]["height"] = config.get("board", "height", vars=self.defaults)
        else:
            opts["board"]["scale"] = self.defaults["board"]["scale"]
            opts["board"]["width"] = self.defaults["board"]["width"]
            opts["board"]["height"] = self.defaults["board"]["height"]

        if config.has_section("game"):
            opts["debug"] = config.get("game", "debug", vars=self.defaults)
            opts["min_rate"] = config.get("game", "min_rate", vars=self.defaults)
            opts["initial_rate"] = config.get("game", "initial_rate", vars=self.defaults)
            opts["constant"] = config.get("game", "constant", vars=self.defaults)
            opts["remove_freq"] = config.get("game", "remove_freq", vars=self.defaults)
            opts["shadow"] = config.get("game", "shadow", vars=self.defaults)
        else:
            opts["debug"] = self.defaults["debug"]
            opts["min_rate"] = self.defaults["min_rate"]
            opts["initial_rate"] = self.defaults["initial_rate"]
            opts["constant"] = self.defaults["constant"]
            opts["remove_freq"] = self.defaults["remove_freq"]
            opts["shadow"] = self.defaults["shadow"]

        opts["keys"] = {}
        if config.has_section("keys"):
            for key in opts["keys"].keys():
                opts["keys"][key] = config.get("keys", key, vars=self.defaults["keys"])
        else:
            opts["keys"] = self.defaults["keys"]

        return opts

    def _get_args(self) -> dict:
        """
        Read configs from command line.
        """
        from . import _VERSION

        desc = "Polyomino tessellation game"
        arg_parser = argparse.ArgumentParser(description=desc, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        arg_parser.add_argument(
            "-V",
            "--version",
            action="version",
            version=f"%(prog)s {_VERSION}",
        )
        arg_parser.add_argument(
            "-c",
            "--config-file",
            default=self.defaults["config_file"],
            type=self._config_file,
            help="Specify location of the config file",
        )
        arg_parser.add_argument(
            "-d",
            "--debug",
            default=self.defaults["debug"],
            action="store_true",
            help="Run game in debug mode",
        )
        arg_parser.add_argument(
            "-s",
            "--size",
            default="{0[width]}x{0[height]}".format(self.defaults["board"]),
            type=self._size,
            help="Board size [blocks^2]",
        )
        arg_parser.add_argument(
            "-a",
            "--scale",
            default=self.defaults["board"]["scale"],
            type=int,
            help="Board scale [pixels/block]",
        )
        arg_parser.add_argument(
            "-r",
            "--initial-rate",
            default=self.defaults["initial_rate"],
            type=self._initial_rate,
            help="Initial rate: must be >= {} [blocks/second]".format(self.defaults["min_rate"]),
        )
        arg_parser.add_argument(
            "-o",
            "--constant",
            default=self.defaults["constant"],
            action="store_true",
            help="Do not increase game rate",
        )
        return vars(arg_parser.parse_args())

    def get_opts(self) -> dict:
        """
        Setup program options.
        """
        args = self.defaults if self.test else self._get_args()
        opts = self._get_config(args["config_file"])
        opts.update(args)
        return opts

    def write_opts(self, opts):
        """
        Save game configs to file when config dialog is closed.
        """
        raise NotImplementedError("Cannot save game preferences")


def main() -> int:
    """
    Execute the game.  Must return `int` type for `sys.exit()`.
    """
    try:
        TetraTile(Config(), master=tk.Tk(className="tetratile")).mainloop()
    except KeyboardInterrupt:
        exit(0)
    else:
        return 0


if __name__ == "__main__":
    main()
